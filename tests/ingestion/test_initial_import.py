"""Real PostgreSQL initialization tests for the approved pilot snapshot."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Connection, text

from sciscope.database.models import Base
from sciscope.ingestion.contract import ImportMode, ImportRequest
from sciscope.ingestion.service import SnapshotImporter
from sciscope.ingestion.validate import validate_snapshot

ROOT = Path(__file__).parents[2]
PACKAGE = ROOT / "data" / "delivery" / "pilot"
REPORTS = ROOT / "data" / "pilot"


def _request() -> ImportRequest:
    """Build the current pilot initialization request."""
    return ImportRequest(
        PACKAGE,
        REPORTS / "parse_report.json",
        REPORTS / "chunk_report.json",
        REPORTS / "embedding_report.json",
        ImportMode.INITIALIZE,
    )


def test_pilot_import_or_identical_noop_has_complete_active_snapshot(
    ingestion_connection: Connection,
) -> None:
    """A pilot import stores the exact active records and vectors."""
    result = SnapshotImporter(ingestion_connection).import_snapshot(_request())
    assert result.outcome in ("imported", "unchanged")
    assert (result.papers, result.sections, result.chunks, result.vectors) == (
        17,
        319,
        728,
        728,
    )
    active_id = ingestion_connection.execute(
        text("SELECT id FROM delivery_imports WHERE is_active")
    ).scalar_one()
    assert (
        ingestion_connection.execute(
            text("SELECT count(*) FROM delivery_imports WHERE is_active")
        ).scalar_one()
        == 1
    )
    for table in ("papers", "sections", "chunks", "chunk_embeddings"):
        count = ingestion_connection.execute(
            text(f"SELECT count(*) FROM {table} WHERE delivery_import_id=:id"),
            {"id": active_id},
        ).scalar_one()
        expected = {
            "papers": 17,
            "sections": 319,
            "chunks": 728,
            "chunk_embeddings": 728,
        }[table]
        assert count == expected
    assert set(Base.metadata.tables) == {
        "delivery_imports",
        "embedding_sets",
        "papers",
        "sections",
        "chunks",
        "chunk_embeddings",
    }


def test_import_rows_preserve_manifest_chunk_ownership(
    ingestion_connection: Connection,
) -> None:
    """Stored vector input hashes remain bound to manifest chunk IDs."""
    snapshot = validate_snapshot(_request())
    SnapshotImporter(ingestion_connection).import_snapshot(_request())
    active_id = ingestion_connection.execute(
        text("SELECT id FROM delivery_imports WHERE is_active")
    ).scalar_one()
    stored = dict(
        ingestion_connection.execute(
            text(
                "SELECT chunk_id, input_sha256 FROM chunk_embeddings "
                "WHERE delivery_import_id=:id"
            ),
            {"id": active_id},
        ).all()
    )
    expected = {
        str(entry["chunk_id"]): str(entry["input_sha256"])
        for entry in snapshot.entries
    }
    assert stored == expected


def test_normalization_method_and_target_norm_are_stored_separately(
    ingestion_connection: Connection,
) -> None:
    """The method string and numeric unit norm retain distinct meanings."""
    SnapshotImporter(ingestion_connection).import_snapshot(_request())
    target, manifest = ingestion_connection.execute(
        text(
            "SELECT es.normalization_declared, es.embedding_manifest "
            "FROM embedding_sets es JOIN delivery_imports di "
            "ON di.id=es.delivery_import_id WHERE di.is_active"
        )
    ).one()
    assert target == 1.0
    assert manifest["normalization"]["declared"] == "l2"
