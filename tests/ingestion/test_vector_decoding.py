"""Manifest-owned streaming float32 vector decoding tests."""

from __future__ import annotations

import hashlib
import math
import struct
from pathlib import Path

import pytest

from sciscope.ingestion.errors import ImportErrorCode, SnapshotImportError
from sciscope.ingestion.vectors import iter_vector_rows


def _entries() -> tuple[dict[str, object], ...]:
    """Return deliberately reordered manifest ownership metadata."""
    return (
        {"chunk_id": "b" * 64, "input_sha256": "2" * 64},
        {"chunk_id": "a" * 64, "input_sha256": "1" * 64},
    )


def _row(first: float) -> bytes:
    """Make one exact 1536-dimensional little-endian row."""
    values = [first] + [0.0] * 1535
    return struct.pack("<1536f", *values)


def test_vectors_follow_manifest_ids_not_chunk_positions(
    tmp_path: Path,
) -> None:
    """Each raw vector row is owned by its corresponding manifest entry."""
    vectors = tmp_path / "vectors.f32"
    vectors.write_bytes(_row(0.25) + _row(0.75))
    rows = list(iter_vector_rows(vectors, _entries(), dimensions=1536))
    assert [row[0] for row in rows] == ["b" * 64, "a" * 64]
    assert [row[2][0] for row in rows] == [0.25, 0.75]
    assert rows[0][1] == "2" * 64


@pytest.mark.parametrize("suffix", [b"x", b"\x00\x00\x00\x00"])
def test_truncated_or_trailing_bytes_are_rejected(
    tmp_path: Path, suffix: bytes
) -> None:
    """The decoder rejects non-row-aligned input without partial success."""
    vectors = tmp_path / "vectors.f32"
    vectors.write_bytes(_row(0.25) + suffix)
    with pytest.raises(SnapshotImportError) as caught:
        list(iter_vector_rows(vectors, _entries()[:1], dimensions=1536))
    assert caught.value.code is ImportErrorCode.DELIVERY_INVALID


def test_nonfinite_values_and_duplicate_ids_are_rejected(
    tmp_path: Path,
) -> None:
    """Nonfinite rows and ambiguous manifest ownership cannot be decoded."""
    vectors = tmp_path / "vectors.f32"
    vectors.write_bytes(_row(math.inf) + _row(0.5))
    with pytest.raises(SnapshotImportError):
        list(iter_vector_rows(vectors, _entries(), dimensions=1536))
    with pytest.raises(SnapshotImportError):
        list(
            iter_vector_rows(
                vectors,
                (_entries()[0], _entries()[0]),
                dimensions=1536,
            )
        )


def test_vector_stream_checks_the_manifest_digest(tmp_path: Path) -> None:
    """Bytes changed after package validation fail before transaction commit."""
    vectors = tmp_path / "vectors.f32"
    raw = _row(0.25) + _row(0.75)
    vectors.write_bytes(raw)
    decoded = list(
        iter_vector_rows(
            vectors,
            _entries(),
            dimensions=1536,
            expected_sha256=hashlib.sha256(raw).hexdigest(),
        )
    )
    assert len(decoded) == 2
    with pytest.raises(SnapshotImportError):
        list(
            iter_vector_rows(
                vectors,
                _entries(),
                dimensions=1536,
                expected_sha256="0" * 64,
            )
        )
