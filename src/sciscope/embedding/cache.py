"""Atomic exact-input float32 cache with durable batch accounting."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import struct
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import cast

from sciscope.embedding.config import CACHE_FORMAT_VERSION, EmbeddingCacheError

_METADATA_FIELDS = (
    "format",
    "model",
    "dimensions",
    "input_sha256",
    "vector_sha256",
    "estimated_tokens",
    "counter_id",
    "embedded_on",
    "batch_id",
    "batch_input_count",
    "batch_estimated_tokens",
    "batch_prompt_tokens",
    "batch_total_tokens",
)


@dataclass(frozen=True, slots=True)
class CacheEntry:
    """One vector with integrity, provenance, and durable batch accounting."""

    format: str
    model: str
    dimensions: int
    input_sha256: str
    vector_sha256: str
    estimated_tokens: int
    counter_id: str
    embedded_on: str
    batch_id: str
    batch_input_count: int
    batch_estimated_tokens: int
    batch_prompt_tokens: int
    batch_total_tokens: int
    vector_bytes: bytes


def cache_key(model: str, dimensions: int, input_sha256: str) -> str:
    """Hash canonical length-delimited model, dimensions, and input digest."""
    fields = (model, str(dimensions), input_sha256)
    data = bytearray(len(fields).to_bytes(8, "big"))
    for value in fields:
        encoded = value.encode("utf-8")
        data.extend(len(encoded).to_bytes(8, "big"))
        data.extend(encoded)
    return hashlib.sha256(data).hexdigest()


def encode_entry(entry: CacheEntry) -> bytes:
    """Encode one compact ASCII metadata line and little-endian vector."""
    metadata: dict[str, object] = {
        name: cast(object, getattr(entry, name)) for name in _METADATA_FIELDS
    }
    return (
        json.dumps(
            metadata, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        + b"\n"
        + entry.vector_bytes
    )


def decode_entry(
    data: bytes, *, model: str, dimensions: int, input_sha256: str
) -> CacheEntry:
    """Validate stored metadata, expected identity, checksum, and float32."""
    entry: CacheEntry | None = None
    try:
        entry = _decode_entry(data, model, dimensions, input_sha256)
    except (
        ValueError,
        UnicodeError,
        KeyError,
        TypeError,
        struct.error,
        RecursionError,
        OverflowError,
    ):
        pass
    if entry is None:
        raise EmbeddingCacheError(
            "cache-entry-corrupt", cache_key(model, dimensions, input_sha256)
        )
    return entry


def _reject_constant(value: str) -> object:
    """Reject nonstandard JSON numbers in cache metadata."""
    raise ValueError("invalid-json-constant")


def _decode_entry(
    data: bytes, model: str, dimensions: int, input_sha256: str
) -> CacheEntry:
    """Decode metadata using private failures without raw output."""
    header, vector = data.split(b"\n", 1)
    obj: object = json.loads(
        header.decode("utf-8"), parse_constant=_reject_constant
    )
    if not isinstance(obj, dict) or set(obj) != set(_METADATA_FIELDS):
        raise ValueError("fields")
    metadata = cast(dict[str, object], obj)
    for name in (
        "format",
        "model",
        "input_sha256",
        "vector_sha256",
        "counter_id",
        "embedded_on",
        "batch_id",
    ):
        if (
            not isinstance(metadata[name], str)
            or not cast(str, metadata[name]).strip()
        ):
            raise ValueError("string")
    for name in (
        "dimensions",
        "estimated_tokens",
        "batch_input_count",
        "batch_estimated_tokens",
        "batch_prompt_tokens",
        "batch_total_tokens",
    ):
        value = metadata[name]
        minimum = 1 if name in ("dimensions", "batch_input_count") else 0
        if type(value) is not int or value < minimum:
            raise ValueError("integer")
    for name in ("input_sha256", "vector_sha256", "batch_id"):
        if re.fullmatch("[0-9a-f]{64}", cast(str, metadata[name])) is None:
            raise ValueError("digest")
    embedded_on = cast(str, metadata["embedded_on"])
    if date.fromisoformat(embedded_on).isoformat() != embedded_on:
        raise ValueError("date")
    if (
        metadata["format"] != CACHE_FORMAT_VERSION
        or metadata["model"] != model
        or metadata["dimensions"] != dimensions
        or metadata["input_sha256"] != input_sha256
        or len(vector) != dimensions * 4
        or hashlib.sha256(vector).hexdigest() != metadata["vector_sha256"]
        or any(
            not math.isfinite(value)
            for (value,) in struct.iter_unpack("<f", vector)
        )
    ):
        raise ValueError("integrity")
    return CacheEntry(
        metadata["format"],
        model,
        dimensions,
        input_sha256,
        metadata["vector_sha256"],
        cast(int, metadata["estimated_tokens"]),
        cast(str, metadata["counter_id"]),
        embedded_on,
        cast(str, metadata["batch_id"]),
        cast(int, metadata["batch_input_count"]),
        cast(int, metadata["batch_estimated_tokens"]),
        cast(int, metadata["batch_prompt_tokens"]),
        cast(int, metadata["batch_total_tokens"]),
        vector,
    )


def _batch_fields(entry: CacheEntry) -> tuple[object, ...]:
    """Return the accounting fields that must agree within one batch."""
    return (
        entry.embedded_on,
        entry.batch_input_count,
        entry.batch_estimated_tokens,
        entry.batch_prompt_tokens,
        entry.batch_total_tokens,
    )


@dataclass(frozen=True, slots=True)
class EmbeddingCache:
    """A directory of atomic entries, with consistent metadata per batch."""

    directory: Path
    _batches: dict[tuple[str, int, str], tuple[object, ...]] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    def get(
        self, model: str, dimensions: int, input_sha256: str
    ) -> CacheEntry | None:
        """Return a validated entry, fail on corruption, or return a miss."""
        key = cache_key(model, dimensions, input_sha256)
        data: bytes | None = None
        failed = False
        try:
            data = (self.directory / (key + ".entry")).read_bytes()
        except FileNotFoundError:
            return None
        except OSError:
            failed = True
        if failed or data is None:
            raise EmbeddingCacheError("cache-entry-corrupt", key)
        entry = decode_entry(
            data, model=model, dimensions=dimensions, input_sha256=input_sha256
        )
        self._check_batch(entry)
        return entry

    def put_batch(self, entries: Sequence[CacheEntry]) -> None:
        """Persist each validated entry atomically before the next request."""
        encoded = [(entry, encode_entry(entry)) for entry in entries]
        previous_batches = self._batches.copy()
        try:
            self._put_entries(encoded)
        except (OSError, EmbeddingCacheError):
            self._batches.clear()
            self._batches.update(previous_batches)
            raise

    def _put_entries(self, encoded: Sequence[tuple[CacheEntry, bytes]]) -> None:
        """Validate the complete batch before atomically writing its entries."""
        for entry, data in encoded:
            decode_entry(
                data,
                model=entry.model,
                dimensions=entry.dimensions,
                input_sha256=entry.input_sha256,
            )
            self._check_batch(entry)
        self.directory.mkdir(parents=True, exist_ok=True)
        for entry, data in encoded:
            temporary: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode="wb", dir=self.directory, suffix=".tmp", delete=False
                ) as file:
                    temporary = Path(file.name)
                    file.write(data)
                    file.flush()
                    os.fsync(file.fileno())
                key = cache_key(
                    entry.model, entry.dimensions, entry.input_sha256
                )
                os.replace(temporary, self.directory / (key + ".entry"))
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)

    def _check_batch(self, entry: CacheEntry) -> None:
        """Reject inconsistent accounting across referenced entries."""
        group = (entry.model, entry.dimensions, entry.batch_id)
        fields = _batch_fields(entry)
        if group in self._batches and self._batches[group] != fields:
            raise EmbeddingCacheError(
                "cache-entry-corrupt",
                cache_key(entry.model, entry.dimensions, entry.input_sha256),
            )
        self._batches[group] = fields
