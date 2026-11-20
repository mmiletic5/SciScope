"""Bounded, manifest-entry-owned float32 little-endian vector streaming."""

from __future__ import annotations

import hashlib
import math
import struct
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import cast

from sciscope.ingestion.errors import ImportErrorCode, SnapshotImportError


def iter_vector_rows(
    vectors_path: Path,
    entries: Sequence[Mapping[str, object]],
    *,
    dimensions: int,
    expected_sha256: str | None = None,
) -> Iterator[tuple[str, str, list[float]]]:
    """Yield one validated vector row for each authoritative manifest entry.

    Args:
        vectors_path: Raw float32-le file from the validated delivery.
        entries: Ordered embedding-manifest entries.
        dimensions: Exact vector width required by the embedding configuration.
        expected_sha256: Optional digest from the validated delivery manifest.

    Yields:
        Chunk ID, input text SHA-256, and widened row values.

    Raises:
        SnapshotImportError: If ownership, file size, or float data is invalid.
    """
    if dimensions != 1536 or not entries:
        raise SnapshotImportError(ImportErrorCode.DELIVERY_INVALID)
    owners: list[tuple[str, str]] = []
    seen: set[str] = set()
    for entry in entries:
        chunk_id = entry.get("chunk_id")
        input_sha256 = entry.get("input_sha256")
        if (
            not isinstance(chunk_id, str)
            or not isinstance(input_sha256, str)
            or chunk_id in seen
        ):
            raise SnapshotImportError(ImportErrorCode.DELIVERY_INVALID)
        seen.add(chunk_id)
        owners.append((chunk_id, input_sha256))
    expected_size = len(owners) * dimensions * 4
    try:
        actual_size = vectors_path.stat().st_size
    except OSError:
        raise SnapshotImportError(ImportErrorCode.DELIVERY_INVALID) from None
    if actual_size != expected_size:
        raise SnapshotImportError(ImportErrorCode.DELIVERY_INVALID)
    format_string = "<" + "f" * dimensions
    digest = hashlib.sha256()
    try:
        with vectors_path.open("rb") as stream:
            for chunk_id, input_sha256 in owners:
                raw = stream.read(dimensions * 4)
                if len(raw) != dimensions * 4:
                    raise SnapshotImportError(ImportErrorCode.DELIVERY_INVALID)
                digest.update(raw)
                values = list(
                    cast(tuple[float, ...], struct.unpack(format_string, raw))
                )
                if any(not math.isfinite(value) for value in values):
                    raise SnapshotImportError(ImportErrorCode.DELIVERY_INVALID)
                yield chunk_id, input_sha256, values
            if stream.read(1):
                raise SnapshotImportError(ImportErrorCode.DELIVERY_INVALID)
            if (
                expected_sha256 is not None
                and digest.hexdigest() != expected_sha256
            ):
                raise SnapshotImportError(ImportErrorCode.DELIVERY_INVALID)
    except OSError:
        raise SnapshotImportError(ImportErrorCode.DELIVERY_INVALID) from None
