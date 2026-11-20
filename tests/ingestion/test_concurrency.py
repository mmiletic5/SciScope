"""Real two-connection advisory lock behavior for importer serialization."""

from __future__ import annotations

from snapshot_fixtures import pilot_request
from sqlalchemy import Connection, Engine, text

from sciscope.ingestion.errors import ImportErrorCode, SnapshotImportError
from sciscope.ingestion.service import SnapshotImporter


def test_advisory_lock_contention_fails_without_mutation(
    ingestion_connection: Connection,
    database_engine: Engine,
) -> None:
    """A second real connection fails fast while the first holds the lock."""
    acquired = ingestion_connection.execute(
        text("SELECT pg_try_advisory_xact_lock(:key1, :key2)"),
        {"key1": 1396918611, "key2": 1229803604},
    ).scalar_one()
    assert acquired is True
    before = ingestion_connection.execute(
        text("SELECT count(*) FROM delivery_imports")
    ).scalar_one()
    try:
        SnapshotImporter(database_engine).import_snapshot(pilot_request())
    except SnapshotImportError as error:
        assert error.code is ImportErrorCode.IMPORT_IN_PROGRESS
    else:
        raise AssertionError("contending import unexpectedly acquired the lock")
    after = ingestion_connection.execute(
        text("SELECT count(*) FROM delivery_imports")
    ).scalar_one()
    assert after == before
