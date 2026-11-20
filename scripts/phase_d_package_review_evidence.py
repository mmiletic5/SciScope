"""Build an allowlisted, deterministic, text-free Phase D review package."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path(
    "evals/protected/phase_d_final_review/phase_d_final_evidence_review.zip"
)
PROTECTED_ALLOWLIST = {
    "evals/protected/golden_v1_review/phase_d_baseline_freeze.json",
    "evals/protected/phase_d_authorizations/t005_user_approval_source.json",
    "evals/protected/phase_d_authorizations/t005_v0-held-out_approval.json",
    "evals/protected/phase_d_authorizations/t005_v1-held-out_approval.json",
    "evals/protected/phase_d_authorizations/t005_embedding_generation_user_approval.json",
    "evals/protected/phase_d_authorizations/t006_user_approval_source.json",
    "evals/protected/phase_d_authorizations/t006_v0-held-out_approval.json",
    "evals/protected/phase_d_authorizations/t006_v1-held-out_approval.json",
    "evals/protected/phase_d_t005_readiness_report.json",
    "evals/protected/phase_d_t005_embedding_generation_report.json",
    "evals/protected/phase_d_t006_run_manifest.json",
}
STATIC_FILES = {
    ".gitignore",
    "pyproject.toml",
    "uv.lock",
    "DEVELOPMENT_SETUP.md",
    "evals/golden_questions.schema.json",
    "evals/golden_functionality_annotations.schema.json",
    "data/pilot/manifest.jsonl",
    "data/delivery/pilot/delivery_manifest.json",
    "specs/009-phase-d-retrieval-evaluation/spec.md",
    "specs/009-phase-d-retrieval-evaluation/plan.md",
    "specs/009-phase-d-retrieval-evaluation/research.md",
    "specs/009-phase-d-retrieval-evaluation/tasks.md",
    "specs/009-phase-d-retrieval-evaluation/quickstart.md",
    "specs/009-phase-d-retrieval-evaluation/checklists/acceptance.md",
    "docs/person2/PHASE_D_BASELINE_FREEZE.md",
    "docs/person2/PHASE_D_IMPLEMENTATION_PLAN.md",
    "docs/person2/RETRIEVAL_EVALUATION_PROTOCOL.md",
    "docs/person2/PHASE_D_T004_REVIEW_AND_VERIFICATION.md",
    "docs/person2/PHASE_D_T005_PREPARATION.md",
    "docs/person2/PHASE_D_RESULTS.md",
    "docs/person2/PHASE_D_RUNBOOK.md",
    "docs/person2/PHASE_D_EVIDENCE_SUMMARY.md",
    "docs/person2/PHASE_D_T008_ACCEPTANCE_SUMMARY.md",
    "docs/person2/PERSON1_HANDOFF.md",
    "docs/person2/PERSON3_HANDOFF.md",
    "docs/person2/PHASE_E_HANDOFF.md",
    "EVIDENCE.md",
    "PROJECT_TODO.md",
    "evals/results/phase_d_readiness_status.json",
    "scripts/phase_d_retrieval_evaluation.py",
    "scripts/phase_d_run_retrieval_evaluation.py",
    "scripts/phase_d_generate_query_vectors.py",
    "scripts/phase_d_readonly_db_preflight.py",
    "scripts/phase_d_build_golden_v1.py",
    "scripts/phase_d_prepare_golden_v1.py",
    "scripts/phase_d_package_review_evidence.py",
}
FORBIDDEN_PARTS = {
    ".env",
    "data/embeddings",
    "evals/golden_questions.v0.json",
    "golden_questions.v1",
    "source_passages.v1.json",
    "query-cache",
    ".entry",
    "vectors.f32",
}
FUNCTIONALITY_SUMMARY = "evals/results/phase_d_v1_functionality_summaries.json"


def _evaluation_outputs(root: Path) -> set[str]:
    """Select only the six result files named by the protected T006 manifest."""
    manifest_path = root / "evals/protected/phase_d_t006_run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    outputs = {FUNCTIONALITY_SUMMARY}
    for cohort in manifest.get("cohorts", []):
        for relative in cohort.get("result_files", {}).values():
            if (
                not isinstance(relative, str)
                or not relative.endswith(".json")
                or not (
                    relative.startswith("evals/results/phase_d_v0-held-out/")
                    or relative.startswith("evals/results/phase_d_v1-held-out/")
                )
                or ".." in Path(relative).parts
            ):
                raise ValueError(
                    "T006 result path is outside the approved scope"
                )
            outputs.add(relative)
    if len(outputs) != 7:
        raise ValueError("T006 result artifact inventory is incomplete")
    return outputs


def package_members(root: Path = ROOT) -> list[Path]:
    """Return the exact source allowlist, rejecting protected content paths."""
    candidates = set(STATIC_FILES)
    candidates.update(_evaluation_outputs(root))
    candidates.update(
        str(path.relative_to(root)).replace("\\", "/")
        for directory in (
            root / "src/sciscope/evaluation",
            root / "tests/evaluation",
        )
        for path in directory.glob("*.py")
    )
    candidates.update(PROTECTED_ALLOWLIST)
    normalized = sorted(candidates)
    for relative in normalized:
        if any(part in relative for part in FORBIDDEN_PARTS):
            raise ValueError("package allowlist includes a forbidden path")
        path = (root / relative).resolve(strict=True)
        if not path.is_file() or root.resolve() not in path.parents:
            raise ValueError(
                "package member is missing or outside the workspace"
            )
        if (
            relative.startswith("evals/protected/")
            and relative not in PROTECTED_ALLOWLIST
        ):
            raise ValueError("unapproved protected artifact in package")
    return [root / name for name in normalized]


def _readme() -> bytes:
    """Describe package scope and explicitly disclose missing results."""
    content = """# Phase D Person 2 Evidence Review Package

This package contains evaluation source code, synthetic tests, schemas,
frozen methodology/configuration manifests, T005/T006 approval receipts,
readiness and usage evidence, six protected cohort/arm result reports, and
current handoffs, lexical/hybrid diagnostics, and a criterion-by-criterion
T008 acceptance summary. T004 is accepted; T005 readiness and authorized T006
retrieval completed. The owner reports independent ChatGPT package/hash/metric
review. Final owner decision and acceptance remain pending.

The package excludes Golden v0/v1 question text, source passages, query-cache
entries, document vectors, database contents, credentials, and local caches.
Held-out retrieval results are included only for the explicitly requested
independent final review. The reviewer copy remains protected and must not be
used for retrieval development, debugging, or tuning. Golden v1 has six
held-out questions and functionality summaries are descriptive only. Q4/Q5
are false-conflict negative controls; no genuine-conflict sensitivity claim
is supported.

T007 reporting and handoffs are prepared. The owner reports independent
ChatGPT package/hash/metric review; T008 lexical diagnostics and acceptance
summary are included. The owner still must decide whether a separate
versioned lexical/hybrid diagnostic cycle is needed and provide final
acceptance. Run offline checks on native Windows PowerShell from the repository
root with the supplied Python 3.12 environment. See the evidence summary for
exact commands and recorded limitations.
"""
    return content.encode("utf-8")


def build_package(root: Path = ROOT, output: Path | None = None) -> Path:
    """Create and verify the deterministic allowlisted review ZIP."""
    target = output or root / OUTPUT
    members = package_members(root)
    files: dict[str, bytes] = {
        path.relative_to(root).as_posix(): path.read_bytes() for path in members
    }
    files["README.md"] = _readme()
    manifest: dict[str, Any] = {
        "artifact_type": "phase-d-person2-technical-evidence-review",
        "manifest_version": "phase-d-review-evidence-v1",
        "phase_status": "T005 ready; T006 evaluated; T007/T008 review pending",
        "members": {
            name: {
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            }
            for name, data in sorted(files.items())
        },
    }
    files["package_manifest.json"] = (
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2)
        + "\n"
    ).encode("utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        target, mode="w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 20, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)
    _verify_package(target)
    return target


def _verify_package(path: Path) -> None:
    """Verify member hashes and forbidden names without extracting files."""
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        if any(any(part in name for part in FORBIDDEN_PARTS) for name in names):
            raise ValueError("package contains a forbidden member")
        manifest = json.loads(archive.read("package_manifest.json"))
        declared = manifest.get("members")
        if not isinstance(declared, dict) or names != set(declared) | {
            "package_manifest.json"
        }:
            raise ValueError("package member manifest mismatch")
        for name, record in declared.items():
            data = archive.read(name)
            if hashlib.sha256(data).hexdigest() != record.get("sha256") or len(
                data
            ) != record.get("bytes"):
                raise ValueError("package member integrity mismatch")


def main() -> int:
    """Build the protected review package and print its checksum only."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        package = build_package(output=args.output)
        digest = hashlib.sha256(package.read_bytes()).hexdigest()
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        print("PACKAGE=FAIL; details sanitized")
        return 1
    print(f"PACKAGE=PASS; path={package}; sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
