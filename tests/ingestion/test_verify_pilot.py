"""Independent source/database reconciliation tests against PostgreSQL."""

from __future__ import annotations

import struct

from snapshot_fixtures import pilot_request
from sqlalchemy import Connection

from sciscope.ingestion.service import SnapshotImporter
from sciscope.ingestion.verify_pilot import (
    VerificationResult,
    _compare_vector_bytes,
    verify_snapshot,
)


def test_independent_verifier_reconciles_all_pilot_ids_and_vectors(
    ingestion_connection: Connection,
) -> None:
    """All source IDs, provenance, vector dimensions, and bytes reconcile."""
    request = pilot_request()
    SnapshotImporter(ingestion_connection).import_snapshot(request)
    result = verify_snapshot(ingestion_connection, request)
    assert result.passed is True
    assert (result.papers, result.sections, result.chunks, result.vectors) == (
        17,
        319,
        728,
        728,
    )
    assert result.missing_ids == result.extra_ids == 0
    assert result.provenance_mismatches == 0
    assert result.dimension_mismatches == result.vector_byte_mismatches == 0
    assert result.orphans == 0


def test_verifier_result_passes_only_with_zero_mismatches() -> None:
    """A nonzero integrity counter cannot produce a passing summary."""
    passed = VerificationResult(17, 319, 728, 728, 0, 0, 0, 0, 0, 0)
    failed = VerificationResult(17, 319, 728, 728, 0, 0, 0, 0, 1, 0)
    assert passed.passed is True
    assert failed.passed is False


def test_verifier_repacks_vectors_using_manifest_chunk_ids() -> None:
    """Each raw vector row is checked against its manifest-owned chunk ID."""
    entries = ({"chunk_id": "b" * 64}, {"chunk_id": "a" * 64})
    first = (0.25,) + (0.0,) * 1535
    second = (0.75,) + (0.0,) * 1535
    raw = struct.pack("<1536f", *first) + struct.pack("<1536f", *second)
    stored = {"b" * 64: {"embedding": first}, "a" * 64: {"embedding": second}}
    assert _compare_vector_bytes(entries, raw, stored) == 0
    swapped = {"b" * 64: {"embedding": second}, "a" * 64: {"embedding": first}}
    assert _compare_vector_bytes(entries, raw, swapped) == 2
