"""Read delivery records and manifest-owned vectors using only the stdlib."""

from __future__ import annotations

import json
import math
import os
import struct
from collections.abc import Iterator
from pathlib import Path
from typing import Never, cast


class DeliveryReadError(ValueError):
    """Expose a sanitized reader code without paths or record content."""

    code: str

    def __init__(self, code: str) -> None:
        """Retain only the caller's reader error code as the message."""
        super().__init__(code)
        self.code = code


def _read_bytes(path: str | os.PathLike[str]) -> bytes:
    """Translate unreadable paths, including embedded NUL, to a safe code."""
    try:
        return Path(path).read_bytes()
    except (OSError, ValueError):
        raise DeliveryReadError("reader-io") from None


def _decode_utf8(data: bytes, code: str) -> str:
    """Decode strict UTF-8 while explicitly rejecting a leading BOM."""
    if data.startswith(b"\xef\xbb\xbf"):
        raise DeliveryReadError(code)
    try:
        return data.decode("utf-8")
    except UnicodeError:
        raise DeliveryReadError(code) from None


def _reject_constant(value: str) -> Never:
    """Reject JSON's nonstandard nonfinite constants without echoing them."""
    raise ValueError


def _finite_float(value: str) -> float:
    """Reject finite-looking JSON numbers that overflow Python floats."""
    number = float(value)
    if not math.isfinite(number):
        raise ValueError
    return number


def _parse_json(text: str, code: str) -> object:
    """Parse JSON with finite numbers, accepting duplicate keys last-wins."""
    try:
        value: object = json.loads(
            text, parse_constant=_reject_constant, parse_float=_finite_float
        )
        return value
    except (ValueError, RecursionError):
        raise DeliveryReadError(code) from None


def iter_jsonl(path: str | os.PathLike[str]) -> Iterator[dict[str, object]]:
    """Yield JSON objects in LF-only file order, preserving Unicode strings.

    Read bytes and check whole-file UTF-8/BOM/CR on first iteration. Parse
    each line only when reached, so a later JSON error may follow valid rows.
    Empty files and one terminal LF are allowed; blank records are rejected.

    Raises:
        DeliveryReadError: With a safe I/O, decoding, JSON or line code.
    """
    text = _decode_utf8(_read_bytes(path), "reader-decoding")
    if "\r" in text:
        raise DeliveryReadError("reader-json")
    lines = text.split("\n")
    for index, line in enumerate(lines):
        if line == "" and index == len(lines) - 1:
            return
        if not line.strip(" \t"):
            raise DeliveryReadError("reader-line")
        value = _parse_json(line, "reader-json")
        if not isinstance(value, dict):
            raise DeliveryReadError("reader-line")
        yield cast(dict[str, object], value)


def load_vectors(
    path: str | os.PathLike[str], *, dimensions: int, count: int
) -> tuple[tuple[float, ...], ...]:
    """Return an immutable matrix of exactly widened little-endian floats.

    Check arguments, I/O, exact size and finiteness in that order.

    Raises:
        DeliveryReadError: With reader-argument, reader-io, reader-size or
            reader-nonfinite when the corresponding check fails.
    """
    if (
        type(dimensions) is not int
        or dimensions <= 0
        or type(count) is not int
        or count <= 0
    ):
        raise DeliveryReadError("reader-argument")
    data = _read_bytes(path)
    size = count * dimensions
    if len(data) != size * 4:
        raise DeliveryReadError("reader-size")
    values = cast(tuple[float, ...], struct.unpack("<" + "f" * size, data))
    if any(not math.isfinite(value) for value in values):
        raise DeliveryReadError("reader-nonfinite")
    return tuple(
        values[offset : offset + dimensions]
        for offset in range(0, size, dimensions)
    )


def vectors_by_chunk_id(
    manifest_path: str | os.PathLike[str],
    vectors_path: str | os.PathLike[str],
    *,
    dimensions: int,
) -> dict[str, tuple[float, ...]]:
    """Associate rows with manifest entry IDs, preserving their order.

    Check dimensions before manifest I/O and manifest shape/duplicate IDs
    before vector I/O. Ignore extra manifest fields, including dimensions
    and hashes. Never consult chunks.jsonl; validate the package separately.

    Raises:
        DeliveryReadError: With a safe argument, I/O, manifest, duplicate-ID,
            size or nonfinite code.
    """
    if type(dimensions) is not int or dimensions <= 0:
        raise DeliveryReadError("reader-argument")
    text = _decode_utf8(_read_bytes(manifest_path), "reader-manifest")
    manifest = _parse_json(text, "reader-manifest")
    if not isinstance(manifest, dict):
        raise DeliveryReadError("reader-manifest")
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        raise DeliveryReadError("reader-manifest")
    ids: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise DeliveryReadError("reader-manifest")
        chunk_id = entry.get("chunk_id")
        if not isinstance(chunk_id, str):
            raise DeliveryReadError("reader-manifest")
        ids.append(chunk_id)
    if len(set(ids)) != len(ids):
        raise DeliveryReadError("reader-duplicate-id")
    rows = load_vectors(vectors_path, dimensions=dimensions, count=len(ids))
    return dict(zip(ids, rows, strict=True))
