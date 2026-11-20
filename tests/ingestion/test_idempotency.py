"""Real PostgreSQL no-op and initialize-state behavior."""

from __future__ import annotations

import pytest
from snapshot_fixtures import different_manifest_request, pilot_request
from sqlalchemy import Connection, text

from sciscope.ingestion.contract import ImportMode
from sciscope.ingestion.errors import ImportErrorCode, SnapshotImportError
from sciscope.ingestion.service import SnapshotImporter


def test_identical_import_is_a_true_noop(
    ingestion_connection: Connection,
) -> None:
    """Repeated import keeps audit identity and committed timestamps stable."""
    importer = SnapshotImporter(ingestion_connection)
    first = importer.import_snapshot(pilot_request())
    before = ingestion_connection.execute(
        text("SELECT id, imported_at FROM delivery_imports WHERE is_active")
    ).one()
    second = importer.import_snapshot(
        pilot_request(
            ImportMode.REPLACE, expected_active_digest=first.delivery_digest
        )
    )
    after = ingestion_connection.execute(
        text("SELECT id, imported_at FROM delivery_imports WHERE is_active")
    ).one()
    assert second.outcome == "unchanged"
    assert second.import_id == first.import_id
    assert second.previous_delivery_digest == first.delivery_digest
    assert before == after
    assert (
        ingestion_connection.execute(
            text("SELECT count(*) FROM delivery_imports WHERE is_active")
        ).scalar_one()
        == 1
    )


def test_initialize_rejects_a_different_active_digest(
    ingestion_connection: Connection,
    tmp_path,
) -> None:
    """Initialize cannot silently replace a different active snapshot."""
    importer = SnapshotImporter(ingestion_connection)
    first = importer.import_snapshot(pilot_request())
    different = different_manifest_request(tmp_path)
    with pytest.raises(SnapshotImportError) as caught:
        importer.import_snapshot(different)
    assert caught.value.code is ImportErrorCode.REPLACEMENT_REQUIRED
    assert (
        ingestion_connection.execute(
            text("SELECT delivery_digest FROM delivery_imports WHERE is_active")
        ).scalar_one()
        == first.delivery_digest
    )
