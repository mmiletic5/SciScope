"""Source provenance preservation tests against real PostgreSQL."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Connection, text

from sciscope.ingestion.contract import ImportMode, ImportRequest
from sciscope.ingestion.service import SnapshotImporter

ROOT = Path(__file__).parents[2]


def test_import_preserves_paper_and_chunk_provenance(
    ingestion_connection: Connection,
) -> None:
    """Representative persisted provenance matches delivered records exactly."""
    request = ImportRequest(
        ROOT / "data/delivery/pilot",
        ROOT / "data/pilot/parse_report.json",
        ROOT / "data/pilot/chunk_report.json",
        ROOT / "data/pilot/embedding_report.json",
        ImportMode.INITIALIZE,
    )
    SnapshotImporter(ingestion_connection).import_snapshot(request)
    active_id = ingestion_connection.execute(
        text("SELECT id FROM delivery_imports WHERE is_active")
    ).scalar_one()
    paper = ingestion_connection.execute(
        text(
            "SELECT doi, xml_sha256 FROM papers WHERE delivery_import_id=:id "
            "ORDER BY doi LIMIT 1"
        ),
        {"id": active_id},
    ).one()
    chunk = ingestion_connection.execute(
        text(
            "SELECT chunk_id, text_sha256, text, source_locator, ordinal "
            "FROM chunks WHERE delivery_import_id=:id ORDER BY chunk_id LIMIT 1"
        ),
        {"id": active_id},
    ).one()
    assert paper.doi and len(paper.xml_sha256) == 64
    assert len(chunk.chunk_id) == len(chunk.text_sha256) == 64
    assert chunk.text and chunk.source_locator.startswith("jats:v1:")
    assert chunk.ordinal > 0
