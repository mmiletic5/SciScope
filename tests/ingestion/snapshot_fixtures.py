"""Small complete-snapshot variants used by real database tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from sciscope.ingestion.contract import ImportMode, ImportRequest

ROOT = Path(__file__).parents[2]
PILOT_PACKAGE = ROOT / "data" / "delivery" / "pilot"
PILOT_REPORTS = ROOT / "data" / "pilot"
REPORT_NAMES = (
    "parse_report.json",
    "chunk_report.json",
    "embedding_report.json",
)


def pilot_request(
    mode: ImportMode = ImportMode.INITIALIZE,
    *,
    expected_active_digest: str | None = None,
    package_dir: Path = PILOT_PACKAGE,
    reports_dir: Path = PILOT_REPORTS,
) -> ImportRequest:
    """Return a request for the committed, fully validated pilot delivery."""
    return ImportRequest(
        package_dir,
        reports_dir / REPORT_NAMES[0],
        reports_dir / REPORT_NAMES[1],
        reports_dir / REPORT_NAMES[2],
        mode,
        expected_active_digest,
    )


def different_manifest_request(root: Path) -> ImportRequest:
    """Create a valid changed digest without changing delivered corpus rows."""
    package = root / "different-package"
    reports = root / "different-reports"
    shutil.copytree(PILOT_PACKAGE, package)
    reports.mkdir()
    for name in REPORT_NAMES:
        shutil.copyfile(PILOT_REPORTS / name, reports / name)
    manifest_path = package / "delivery_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["processing_versions"]["parser"]["version"] = "synthetic-v2"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return pilot_request(package_dir=package, reports_dir=reports)
