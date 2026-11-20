"""Pre-write compatibility validation for complete delivery snapshots."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from sciscope.ingestion.contract import ImportMode, ImportRequest
from sciscope.ingestion.errors import ImportErrorCode, SnapshotImportError
from sciscope.ingestion.validate import validate_snapshot

ROOT = Path(__file__).parents[2]
PACKAGE = ROOT / "data" / "delivery" / "pilot"
REPORTS = ROOT / "data" / "pilot"


def _request(package: Path = PACKAGE, reports: Path = REPORTS) -> ImportRequest:
    return ImportRequest(
        package,
        reports / "parse_report.json",
        reports / "chunk_report.json",
        reports / "embedding_report.json",
        ImportMode.INITIALIZE,
    )


def test_pilot_is_accepted_with_exact_counts_and_compatibility() -> None:
    """The current delivery is fully validated without rewriting its files."""
    snapshot = validate_snapshot(_request())
    assert (
        len(snapshot.papers),
        len(snapshot.sections),
        len(snapshot.chunks),
    ) == (
        17,
        319,
        728,
    )
    assert snapshot.dimensions == 1536
    assert snapshot.delivery_digest.startswith("sha256:")
    assert len(snapshot.entries) == 728


def test_mismatched_report_is_rejected_with_sanitized_code(
    tmp_path: Path,
) -> None:
    """A report from another snapshot fails without revealing its path."""
    reports = tmp_path / "reports"
    reports.mkdir()
    names = ("parse_report.json", "chunk_report.json", "embedding_report.json")
    for name in names:
        shutil.copyfile(REPORTS / name, reports / name)
    (reports / "parse_report.json").write_text("{}", encoding="utf-8")
    with pytest.raises(SnapshotImportError) as caught:
        validate_snapshot(_request(reports=reports))
    assert caught.value.code is ImportErrorCode.DELIVERY_INVALID
    assert str(tmp_path) not in str(caught.value)


def test_partial_embedding_status_is_rejected_before_database_access(
    tmp_path: Path,
) -> None:
    """An incomplete set cannot produce a validated snapshot."""
    package = tmp_path / "package"
    shutil.copytree(PACKAGE, package)
    manifest = package / "embedding_manifest.json"
    manifest.write_bytes(
        manifest.read_bytes().replace(
            b'"status": "complete"', b'"status": "partial"'
        )
    )
    with pytest.raises(SnapshotImportError) as caught:
        validate_snapshot(_request(package=package))
    assert caught.value.code is ImportErrorCode.DELIVERY_INVALID
