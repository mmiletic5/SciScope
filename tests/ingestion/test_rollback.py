"""Transaction rollback and safe retry tests against real PostgreSQL."""

from __future__ import annotations

from pathlib import Path

import pytest
from snapshot_fixtures import different_manifest_request, pilot_request
from sqlalchemy import Connection, text

from sciscope.ingestion.contract import ImportMode
from sciscope.ingestion.errors import ImportErrorCode, SnapshotImportError
from sciscope.ingestion.service import SnapshotImporter

FAILURE_STAGES = (
    "after_audit",
    "after_papers",
    "after_sections",
    "after_chunks",
    "after_vectors",
    "after_verify",
    "after_prune",
    "before_commit",
)


def _fingerprint(connection: Connection) -> tuple[tuple[object, ...], ...]:
    """Return an identity/count fingerprint of all corpus tables."""
    return tuple(
        connection.execute(text(query)).all()
        for query in (
            "SELECT id, delivery_digest, is_active FROM delivery_imports "
            "ORDER BY id",
            "SELECT delivery_import_id, doi FROM papers "
            "ORDER BY delivery_import_id, doi",
            "SELECT delivery_import_id, doi, section_id FROM sections "
            "ORDER BY delivery_import_id, doi, section_id",
            "SELECT delivery_import_id, chunk_id FROM chunks "
            "ORDER BY delivery_import_id, chunk_id",
            "SELECT delivery_import_id, chunk_id FROM chunk_embeddings "
            "ORDER BY delivery_import_id, chunk_id",
        )
    )


@pytest.mark.parametrize("stage", FAILURE_STAGES)
def test_replacement_failure_rolls_back_to_old_fingerprint(
    ingestion_connection: Connection,
    tmp_path: Path,
    stage: str,
) -> None:
    """An exception at every import stage leaves the prior snapshot intact."""
    original = SnapshotImporter(ingestion_connection).import_snapshot(
        pilot_request()
    )
    before = _fingerprint(ingestion_connection)
    changed = different_manifest_request(tmp_path)
    request = pilot_request(
        ImportMode.REPLACE,
        expected_active_digest=original.delivery_digest,
        package_dir=changed.package_dir,
        reports_dir=changed.parse_report.parent,
    )

    def fail_at_current_stage(current: str) -> None:
        """Inject a test-only interruption at the selected transaction stage."""
        if current == stage:
            raise RuntimeError("test interruption")

    importer = SnapshotImporter(
        ingestion_connection, failure_hook=fail_at_current_stage
    )
    with pytest.raises(SnapshotImportError) as caught:
        importer.import_snapshot(request)
    assert caught.value.code is ImportErrorCode.IMPORT_TRANSACTION_FAILED
    assert _fingerprint(ingestion_connection) == before

    retried = SnapshotImporter(ingestion_connection).import_snapshot(request)
    assert retried.outcome == "replaced"
