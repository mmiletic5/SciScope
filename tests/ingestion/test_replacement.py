"""Compare-and-swap replacement tests against real PostgreSQL."""

from __future__ import annotations

from pathlib import Path

import pytest
from snapshot_fixtures import different_manifest_request, pilot_request
from sqlalchemy import Connection, text

from sciscope.ingestion.contract import ImportMode
from sciscope.ingestion.errors import ImportErrorCode, SnapshotImportError
from sciscope.ingestion.service import SnapshotImporter
from sciscope.ingestion.validate import validate_snapshot


def test_replace_requires_matching_expected_active_digest(
    ingestion_connection: Connection,
    tmp_path: Path,
) -> None:
    """Missing and stale compare-and-swap tokens preserve the active corpus."""
    importer = SnapshotImporter(ingestion_connection)
    first = importer.import_snapshot(pilot_request())
    changed = different_manifest_request(tmp_path)
    for expected in (None, "sha256:" + "0" * 64):
        request = pilot_request(
            ImportMode.REPLACE,
            expected_active_digest=expected,
            package_dir=changed.package_dir,
            reports_dir=changed.parse_report.parent,
        )
        with pytest.raises(SnapshotImportError) as caught:
            importer.import_snapshot(request)
        assert caught.value.code is ImportErrorCode.ACTIVE_CORPUS_CONFLICT
    assert (
        ingestion_connection.execute(
            text("SELECT delivery_digest FROM delivery_imports WHERE is_active")
        ).scalar_one()
        == first.delivery_digest
    )


def test_valid_replacement_prunes_old_corpus_and_keeps_audit(
    ingestion_connection: Connection,
    tmp_path: Path,
) -> None:
    """Replacement activates a new digest while preserving audit history."""
    importer = SnapshotImporter(ingestion_connection)
    first = importer.import_snapshot(pilot_request())
    changed = different_manifest_request(tmp_path)
    changed_snapshot = validate_snapshot(changed)
    replacement = pilot_request(
        ImportMode.REPLACE,
        expected_active_digest=first.delivery_digest,
        package_dir=changed.package_dir,
        reports_dir=changed.parse_report.parent,
    )
    result = importer.import_snapshot(replacement)
    assert result.outcome == "replaced"
    assert result.previous_delivery_digest == first.delivery_digest
    assert result.delivery_digest == changed_snapshot.delivery_digest
    assert (
        ingestion_connection.execute(
            text("SELECT count(*) FROM delivery_imports WHERE is_active")
        ).scalar_one()
        == 1
    )
    assert (
        ingestion_connection.execute(
            text("SELECT count(*) FROM chunks WHERE delivery_import_id=:id"),
            {"id": first.import_id},
        ).scalar_one()
        == 0
    )
    assert (
        ingestion_connection.execute(
            text("SELECT count(*) FROM delivery_imports")
        ).scalar_one()
        == 3
    )  # Existing inactive fixture plus both successful audits.
    assert (
        ingestion_connection.execute(
            text("SELECT is_active FROM delivery_imports WHERE id=:id"),
            {"id": first.import_id},
        ).scalar_one()
        is False
    )


def test_historical_digest_can_be_reactivated(
    ingestion_connection: Connection,
    tmp_path: Path,
) -> None:
    """Reactivation adds an audit row instead of reusing history."""
    importer = SnapshotImporter(ingestion_connection)
    original = importer.import_snapshot(pilot_request())
    changed = different_manifest_request(tmp_path)
    changed_snapshot = validate_snapshot(changed)
    importer.import_snapshot(
        pilot_request(
            ImportMode.REPLACE,
            expected_active_digest=original.delivery_digest,
            package_dir=changed.package_dir,
            reports_dir=changed.parse_report.parent,
        )
    )
    reactivated = importer.import_snapshot(
        pilot_request(
            ImportMode.REPLACE,
            expected_active_digest=changed_snapshot.delivery_digest,
        )
    )
    assert reactivated.outcome == "replaced"
    assert reactivated.delivery_digest == original.delivery_digest
    assert reactivated.import_id != original.import_id
    assert (
        ingestion_connection.execute(
            text(
                "SELECT count(*) FROM delivery_imports "
                "WHERE delivery_digest=:digest"
            ),
            {"digest": original.delivery_digest},
        ).scalar_one()
        == 2
    )
