"""Import audit consistency tests against real PostgreSQL."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Connection, text

from sciscope.ingestion.contract import ImportMode, ImportRequest
from sciscope.ingestion.service import SnapshotImporter

ROOT = Path(__file__).parents[2]


def test_activation_audit_records_exact_counts_and_manifest(
    ingestion_connection: Connection,
) -> None:
    """Successful activation writes one immutable summary for the snapshot."""
    request = ImportRequest(
        ROOT / "data/delivery/pilot",
        ROOT / "data/pilot/parse_report.json",
        ROOT / "data/pilot/chunk_report.json",
        ROOT / "data/pilot/embedding_report.json",
        ImportMode.INITIALIZE,
    )
    result = SnapshotImporter(ingestion_connection).import_snapshot(request)
    audit = ingestion_connection.execute(
        text(
            "SELECT delivery_digest, is_active, paper_count, section_count, "
            "chunk_count, vector_count, delivery_manifest "
            "FROM delivery_imports "
            "WHERE id=:id"
        ),
        {"id": result.import_id},
    ).one()
    assert audit.delivery_digest == result.delivery_digest
    assert audit.is_active is True
    assert (
        audit.paper_count,
        audit.section_count,
        audit.chunk_count,
        audit.vector_count,
    ) == (
        17,
        319,
        728,
        728,
    )
    assert audit.delivery_manifest["schema_version"] == "0.3.0"
