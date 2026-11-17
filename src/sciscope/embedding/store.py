"""Deterministic float32 vector sets and durable set-level reports."""

from __future__ import annotations

import hashlib
import json
import math
import struct
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

from sciscope.chunking import output as chunk_output
from sciscope.embedding.cache import CacheEntry
from sciscope.embedding.config import (
    EMBEDDING_FORMAT_VERSION,
    PRICE_USD_PER_MILLION_TOKENS,
    EmbeddingCacheError,
    EmbeddingConfig,
    EmbeddingProviderError,
)
from sciscope.embedding.inputs import ChunkInput, LoadedChunks


def pack_vector(vector: Sequence[float]) -> bytes:
    """Convert finite API floats to bounded little-endian float32 bytes."""
    data: bytes | None = None
    try:
        if all(
            type(value) in (float, int) and math.isfinite(value)
            for value in vector
        ):
            data = struct.pack("<" + "f" * len(vector), *vector)
    except (OverflowError, struct.error, TypeError, ValueError):
        pass
    if data is None or any(
        not math.isfinite(value) for (value,) in struct.iter_unpack("<f", data)
    ):
        raise EmbeddingProviderError("response-nonfinite")
    return data


def unpack_vector(data: bytes, dimensions: int) -> tuple[float, ...]:
    """Validate dimensions and finite values in stored float32 bytes."""
    if len(data) != dimensions * 4 or dimensions < 1:
        raise EmbeddingCacheError("cache-entry-corrupt")
    values = cast(
        tuple[float, ...], struct.unpack("<" + "f" * dimensions, data)
    )
    if any(not math.isfinite(value) for value in values):
        raise EmbeddingCacheError("cache-entry-corrupt")
    return values


def vector_norm(vector: Sequence[float]) -> float:
    """Observe the L2 norm using math.fsum without enforcing tolerance."""
    return math.sqrt(math.fsum(value * value for value in vector))


def build_manifest(
    config: EmbeddingConfig,
    loaded: LoadedChunks,
    selected: Sequence[ChunkInput],
    entries: Mapping[str, CacheEntry],
    *,
    custom_base_url_used: bool = False,
) -> dict[str, object]:
    """Build an ordered manifest from entries keyed by selected chunk ID."""
    ordered = sorted(selected, key=lambda chunk: chunk.chunk_id)
    stored = [entries[chunk.chunk_id] for chunk in ordered]
    batches: dict[str, CacheEntry] = {}
    for entry in stored:
        previous = batches.get(entry.batch_id)
        if previous is not None and (
            previous.embedded_on,
            previous.batch_input_count,
            previous.batch_estimated_tokens,
            previous.batch_prompt_tokens,
            previous.batch_total_tokens,
        ) != (
            entry.embedded_on,
            entry.batch_input_count,
            entry.batch_estimated_tokens,
            entry.batch_prompt_tokens,
            entry.batch_total_tokens,
        ):
            raise EmbeddingCacheError("cache-entry-corrupt")
        batches[entry.batch_id] = entry
    norms = [
        vector_norm(unpack_vector(entry.vector_bytes, config.dimensions))
        for entry in stored
    ]
    vectors = b"".join(entry.vector_bytes for entry in stored)
    return {
        "format_version": EMBEDDING_FORMAT_VERSION,
        "status": "complete"
        if len(selected) == len(loaded.chunks)
        else "partial",
        "provider": config.provider,
        "model": config.model,
        "requested_dimensions": config.dimensions,
        "returned_dimensions": config.dimensions,
        "normalization": {
            "declared": "l2",
            "observed_norm_min": round(min(norms), 9),
            "observed_norm_max": round(max(norms), 9),
        },
        "passage_prefix": config.passage_prefix,
        "query_prefix": config.query_prefix,
        "template_version": loaded.template_version,
        "token_counter_id": loaded.token_counter_id,
        "chunking_version": loaded.chunking_version,
        "chunks_sha256": loaded.chunks_sha256,
        "chunk_count": len(loaded.chunks),
        "vector_count": len(selected),
        "creation_date": min(entry.embedded_on for entry in batches.values()),
        "usage": {
            "prompt_tokens": sum(
                entry.batch_prompt_tokens for entry in batches.values()
            ),
            "total_tokens": sum(
                entry.batch_total_tokens for entry in batches.values()
            ),
        },
        "estimated_input_tokens": sum(
            entry.batch_estimated_tokens for entry in batches.values()
        ),
        "provider_input_count": sum(
            entry.batch_input_count for entry in batches.values()
        ),
        "custom_base_url_used": custom_base_url_used,
        "vectors_file": "vectors.f32",
        "vectors_dtype": "float32-le",
        "vectors_sha256": hashlib.sha256(vectors).hexdigest(),
        "entries": [
            {
                "chunk_id": chunk.chunk_id,
                "input_sha256": entries[chunk.chunk_id].input_sha256,
            }
            for chunk in ordered
        ],
    }


def build_report(
    manifest: Mapping[str, object], *, paper_count: int
) -> dict[str, object]:
    """Build a set-level report from the same manifest accounting totals."""
    report = {
        name: manifest[name]
        for name in (
            "format_version",
            "status",
            "provider",
            "model",
            "requested_dimensions",
            "returned_dimensions",
            "chunks_sha256",
            "chunk_count",
            "vector_count",
        )
    }
    report["paper_count"] = paper_count
    for name in ("estimated_input_tokens", "usage", "provider_input_count"):
        report[name] = manifest[name]
    usage = cast(Mapping[str, object], manifest["usage"])
    report["approximate_cost"] = {
        "usd": round(
            cast(int, usage["total_tokens"])
            * PRICE_USD_PER_MILLION_TOKENS
            / 1_000_000,
            6,
        ),
        "label": "approximate",
        "basis": (
            "reported usage x USD 0.02 per 1M tokens; official model page; "
            "team billing not verified"
        ),
    }
    for name in (
        "template_version",
        "token_counter_id",
        "chunking_version",
        "creation_date",
        "custom_base_url_used",
    ):
        report[name] = manifest[name]
    return report


def render_json(value: Mapping[str, object]) -> bytes:
    """Render ordered UTF-8 JSON with two-space indent and final LF."""
    return (
        json.dumps(dict(value), ensure_ascii=False, indent=2, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def write_embedding_files(
    vectors: bytes,
    manifest: Mapping[str, object],
    report: Mapping[str, object],
    vectors_path: Path,
    manifest_path: Path,
    report_path: Path,
) -> None:
    """Publish all three files in one public chunking.write_outputs call."""
    chunk_output.write_outputs(
        {
            vectors_path: vectors,
            manifest_path: render_json(manifest),
            report_path: render_json(report),
        }
    )
