"""Create a complete, protected Phase D independent review archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = Path(
    "evals/protected/phase_d_final_review/phase_d_independent_review.zip"
)
SOURCE_DIRS = (
    "src/sciscope",
    "tests/evaluation",
    "tests/retrieval",
    "tests/database",
    "migrations",
)
STATIC_FILES = {
    "AGENTS.md",
    ".gitignore",
    ".python-version",
    ".specify/memory/constitution.md",
    "DEVELOPMENT_SETUP.md",
    "docs/DEVELOPMENT_WORKFLOW.md",
    "pyproject.toml",
    "uv.lock",
    "alembic.ini",
    "EVIDENCE.md",
    "PROJECT_TODO.md",
    "evals/golden_questions.schema.json",
    "evals/golden_functionality_annotations.schema.json",
    "data/pilot/manifest.jsonl",
    "data/delivery/pilot/delivery_manifest.json",
    "data/delivery/pilot/embedding_manifest.json",
    "data/delivery/pilot/papers.jsonl",
    "data/delivery/pilot/sections.jsonl",
    "data/delivery/pilot/chunks.jsonl",
    "data/delivery/pilot/vectors.f32",
    "specs/005-postgres-pgvector-foundation/spec.md",
    "specs/005-postgres-pgvector-foundation/plan.md",
    "specs/005-postgres-pgvector-foundation/research.md",
    "specs/005-postgres-pgvector-foundation/tasks.md",
    "specs/007-phase-b-retrieval-core/spec.md",
    "specs/007-phase-b-retrieval-core/plan.md",
    "specs/007-phase-b-retrieval-core/research.md",
    "specs/007-phase-b-retrieval-core/tasks.md",
    "specs/007-phase-b-retrieval-core/checklists/requirements.md",
    "specs/009-phase-d-retrieval-evaluation/spec.md",
    "specs/009-phase-d-retrieval-evaluation/plan.md",
    "specs/009-phase-d-retrieval-evaluation/research.md",
    "specs/009-phase-d-retrieval-evaluation/tasks.md",
    "specs/009-phase-d-retrieval-evaluation/quickstart.md",
    "specs/009-phase-d-retrieval-evaluation/checklists/acceptance.md",
    "docs/person2/MASTER_PLAN.md",
    "docs/person2/ARCHITECTURE.md",
    "docs/person2/ARCHITECTURE_DECISIONS.md",
    "docs/person2/RETRIEVAL_EVALUATION_PROTOCOL.md",
    "docs/person2/PHASE_D_BASELINE_FREEZE.md",
    "docs/person2/PHASE_D_IMPLEMENTATION_PLAN.md",
    "docs/person2/PHASE_D_T004_REVIEW_AND_VERIFICATION.md",
    "docs/person2/PHASE_D_T005_PREPARATION.md",
    "docs/person2/PHASE_D_RUNBOOK.md",
    "docs/person2/PHASE_D_RESULTS.md",
    "docs/person2/PHASE_D_EVIDENCE_SUMMARY.md",
    "docs/person2/PHASE_D_T008_ACCEPTANCE_SUMMARY.md",
    "docs/person2/PERSON1_HANDOFF.md",
    "docs/person2/PERSON3_HANDOFF.md",
    "docs/person2/PHASE_E_HANDOFF.md",
    "docs/person2/PHASE_D_INDEPENDENT_REPRODUCTION.md",
    "scripts/phase_d_run_retrieval_evaluation.py",
    "scripts/phase_d_retrieval_evaluation.py",
    "scripts/phase_d_generate_query_vectors.py",
    "scripts/phase_d_readonly_db_preflight.py",
    "scripts/phase_d_build_golden_v1.py",
    "scripts/phase_d_prepare_golden_v1.py",
    "scripts/phase_d_package_review_evidence.py",
    "scripts/phase_d_manual_verification.ps1",
    "scripts/phase_d_manual_verification_audit.py",
    "scripts/phase_d_package_independent_review.py",
    "scripts/phase_c_minilm_benchmark.py",
    "evals/golden_questions.v0.json",
    "evals/results/phase_d_readiness_status.json",
    "evals/results/phase_d_v1_functionality_summaries.json",
    "evals/protected/phase_d_t005_readiness_report.json",
    "evals/protected/phase_d_t005_embedding_generation_report.json",
    "evals/protected/phase_d_t006_run_manifest.json",
    "evals/protected/golden_v1_review/phase_d_baseline_freeze.json",
}
PROTECTED_AUTH_DIR = "evals/protected/phase_d_authorizations"
GOLDEN_V1_DIR = "evals/protected/golden_v1_review"
T006_RESULT_ROOTS = (
    "evals/results/phase_d_v0-held-out",
    "evals/results/phase_d_v1-held-out",
)
QUERY_CACHE_MANIFESTS = (
    "data/embeddings/phase-d-query/v0-held-out/manifest.json",
    "data/embeddings/phase-d-query/v1-held-out/manifest.json",
)
SECRET_PATTERNS = (
    re.compile(
        rb"(?i)(postgres(?:ql)?(?:\+[^:/@\s]+)?://[^:/@\s]+:)"
        rb"(?!\[REDACTED\])[^@/\s]+(@)"
    ),
    re.compile(rb"(?i)\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(rb"(?i)(authorization\s*:\s*bearer\s+)[A-Za-z0-9._-]{16,}"),
    re.compile(rb"(?i)[A-Z]:\\Users\\[^\\\r\n]+"),
)
FORBIDDEN_PATH_PARTS = {
    ".env",
    ".entry",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
}


def _relative_files(root: Path, directory: str, suffixes: set[str]) -> set[str]:
    base = root / directory
    if not base.is_dir():
        raise ValueError("required source directory is missing")
    return {
        path.relative_to(root).as_posix()
        for path in base.rglob("*")
        if path.is_file() and path.suffix.lower() in suffixes
    }


def _t006_files(root: Path) -> set[str]:
    manifest = json.loads(
        (root / "evals/protected/phase_d_t006_run_manifest.json").read_text(
            encoding="utf-8"
        )
    )
    outputs = manifest.get("result_artifacts")
    if not isinstance(outputs, dict) or len(outputs) != 7:
        raise ValueError("T006 result inventory is incomplete")
    selected = set(outputs)
    for relative in selected:
        if not (
            relative.startswith(T006_RESULT_ROOTS)
            or relative
            == "evals/results/phase_d_v1_functionality_summaries.json"
        ):
            raise ValueError("T006 artifact path is outside the approved scope")
        if ".." in Path(relative).parts:
            raise ValueError("T006 artifact path traversal is forbidden")
    return selected


def _manual_run_files(root: Path) -> set[str]:
    base = root / "evals/protected/phase_d_final_review/manual_verification"
    runs = (
        sorted(path for path in base.iterdir() if path.is_dir())
        if base.is_dir()
        else []
    )
    included: set[str] = set()
    for run in reversed(runs):
        summary = run / "summary.json"
        log = run / "verification.log"
        if summary.is_file() and log.is_file():
            report = json.loads(summary.read_text(encoding="utf-8-sig"))
            if report.get("overall_status") not in {"PASS", "FAIL"}:
                continue
            included.update(
                {
                    summary.relative_to(root).as_posix(),
                    log.relative_to(root).as_posix(),
                }
            )
            if run == runs[-1] and report.get("overall_status") != "PASS":
                raise ValueError("latest manual verification run did not pass")
    if not included:
        raise ValueError("completed manual verification logs are missing")
    return included


def package_members(root: Path = ROOT) -> list[str]:
    """Collect the explicit review scope and reject unsafe paths/files."""
    candidates = set(STATIC_FILES)
    for directory in SOURCE_DIRS:
        candidates.update(_relative_files(root, directory, {".py"}))
    candidates.update(_relative_files(root, "docs/person2", {".md"}))
    candidates.update(
        _relative_files(
            root, "evals/protected/phase_d_authorizations", {".json"}
        )
    )
    candidates.update(
        path.relative_to(root).as_posix()
        for path in (root / GOLDEN_V1_DIR).rglob("*")
        if path.is_file() and path.suffix.lower() in {".json", ".md", ".py"}
    )
    candidates.update(_t006_files(root))
    candidates.update(QUERY_CACHE_MANIFESTS)
    candidates.update(_manual_run_files(root))

    for relative in candidates:
        parts = set(Path(relative).parts)
        if parts & FORBIDDEN_PATH_PARTS:
            raise ValueError("package member path is forbidden")
        if relative.endswith((".pem", ".key", ".p12", ".pfx", ".env")):
            raise ValueError("credential-like file is forbidden")
        resolved = (root / relative).resolve(strict=True)
        if root.resolve() not in resolved.parents or not resolved.is_file():
            raise ValueError("package member is missing or outside workspace")
        if relative.endswith(".entry"):
            raise ValueError("query vector cache entries are excluded")
    return sorted(candidates)


def _redact(data: bytes) -> bytes:
    for pattern in SECRET_PATTERNS:
        data = pattern.sub(
            rb"\1[REDACTED]\2" if pattern.groups == 2 else b"[REDACTED_SECRET]",
            data,
        )
    return data


def _json_strings(value: Any) -> set[str]:
    if isinstance(value, str):
        return {value} if len(value) >= 24 else set()
    if isinstance(value, list):
        return set().union(*(_json_strings(item) for item in value))
    if isinstance(value, dict):
        return set().union(*(_json_strings(item) for item in value.values()))
    return set()


def _verify_manual_log_isolation(files: dict[str, bytes]) -> None:
    """Reject exact protected question/evidence/result strings in run logs."""
    protected_names = {
        name
        for name in files
        if name == "evals/golden_questions.v0.json"
        or name.startswith("evals/protected/golden_v1_review/")
        or name.startswith("evals/results/phase_d_v0-held-out/")
        or name.startswith("evals/results/phase_d_v1-held-out/")
        or name.startswith("data/embeddings/phase-d-query/")
    }
    protected_strings: set[str] = set()
    for name in protected_names:
        if name.endswith(".json"):
            try:
                protected_strings.update(
                    _json_strings(json.loads(files[name].decode("utf-8")))
                )
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise ValueError(
                    "protected source JSON could not be audited"
                ) from None
    logs = [
        data
        for name, data in files.items()
        if name.endswith(("verification.log", "summary.json"))
    ]
    if not logs:
        raise ValueError("manual verification logs are missing")
    if any(
        needle.encode("utf-8") in log
        for needle in protected_strings
        for log in logs
    ):
        raise ValueError("protected text or result string entered a manual log")


def _reproduction_guide() -> bytes:
    text = """# SciScope Phase D independent review package

This private package contains the Person 2 Phase D source, tests, schemas,
methodology, frozen v0/v1 Golden records and evidence, pilot delivery files,
T005/T006 manifests and approvals, six retrieval reports, lexical diagnostics,
acceptance evidence, handoffs, and the native Windows verification script and
logs. It is intended for independent review only. Protected questions and
results must not be used for retrieval development, debugging, tuning, or
ordinary logs.

## What can be reproduced offline

Use native Windows PowerShell, Python 3.12, the repository `.venv`, and the
locked dependencies. From the repository root, run:

```powershell
./scripts/phase_d_manual_verification.ps1
```

This executes the offline evaluation/retrieval tests, focused lexical/RRF
tests, Ruff, formatting, mypy, saved report aggregation and hash checks, safe
public/source-derived FTS diagnostics, and the read-only Phase D PostgreSQL
integration tests when their guarded preflight passes. It does not rerun T006.
The scripts emit statuses and counts only; they do not print Golden question
text, answers, vector values, credentials, or query-cache entry hashes.

The saved metric audit verifies the seven T006 report artifact hashes against
the frozen run manifest, checks cohort/arm/dataset/partition identity, and
independently recomputes each macro Recall@K, Evidence Hit@K, and MRR from the
saved eligible per-question values. It also checks the five frozen delivery
payload hashes. This is an audit of saved outputs, not an independent rerun of
retrieval.

## What requires PostgreSQL

The read-only integration suite and lexical probes require native local
PostgreSQL 17, pgvector 0.8.7, the `sciscope` read-only role, the existing
`sciscope_test_005` database, and its unchanged active pilot snapshot. The
preflight verifies the exact database, role, PostgreSQL major version,
read-only transaction mode, corpus version `pilot17-xml-1fff1573b610`, counts
of 17 papers / 319 sections / 728 chunks / 728 embeddings, and embedding set
115 before it starts. The only PostgreSQL tests run by the manual script were
reviewed: they issue reads, enforce read-only transactions, and do not invoke
Alembic, create/drop tables, or write corpus data. The broader `tests/database`
suite is included for review but is not run against this frozen database:
its shared fixture performs `alembic upgrade head` and several schema tests
write rows inside rollback transactions.

## Reproduction limits

The package includes Golden v0/v1 questions, v1 evidence passages, all frozen
delivery chunks/sections/papers, and document embeddings. Original raw XML was
not available locally. Query-cache manifests are included, but the 22 actual
query-vector entry files are intentionally excluded; rerunning dense/hybrid
T006 would therefore require separate authorized access to the protected
local cache. No query vectors are needed for source-packet review, the offline
suite, lexical probes, or the saved-metric/hash audit. Reproducing T006 also
requires the original frozen PostgreSQL snapshot and must not be performed
without a separate authorization.

ChatGPT's review is an AI scientific review, not human verification. It
approved all nine v1 records against the supplied evidence packet, but did not
independently search the complete 17-paper corpus or reproduce PostgreSQL.
The held-out cohorts are small; v1 supports scenario coverage rather than
functionality-specific significance. Q4/Q5 are false-conflict negative
controls; no genuine-conflict detection sensitivity is measured. AC-038
latency instrumentation remains partial (no cold/warm labels or separate
embedding/database/fusion timings). T008 and AC-038 remain open for independent
ChatGPT review and final owner decision.

## Package manifest

`package_manifest.json` records SHA-256 and byte length for every other ZIP
member. The detached `phase_d_independent_review.zip.manifest.json` records
every member, including the in-archive manifest, and the complete archive
SHA-256. Actual query vector values and API/database credentials are absent.
"""
    return text.encode("utf-8")


def build_package(root: Path = ROOT, output: Path | None = None) -> Path:
    """Build the private archive, redact secrets, and verify every member."""
    target = output or root / OUTPUT
    if root.resolve() not in target.resolve().parents:
        raise ValueError(
            "review archive must remain under the protected workspace"
        )
    files: dict[str, bytes] = {}
    for relative in package_members(root):
        path = root / relative
        content = path.read_bytes()
        files[relative] = (
            content if path.suffix.lower() == ".f32" else _redact(content)
        )
    files["INDEPENDENT_REPRODUCTION.md"] = _reproduction_guide()
    _verify_manual_log_isolation(files)
    package_manifest: dict[str, Any] = {
        "artifact_type": "sciscope-phase-d-person2-independent-review",
        "manifest_version": "phase-d-independent-review-v1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "phase_status": "T005-T007 evidence prepared; T008/AC-038 open",
        "protection": (
            "private review material; no retrieval tuning or development use"
        ),
        "query_vector_entries_included": False,
        "raw_xml_available": False,
        "members": {
            name: {
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            }
            for name, data in sorted(files.items())
        },
    }
    files["package_manifest.json"] = (
        json.dumps(
            package_manifest, ensure_ascii=False, sort_keys=True, indent=2
        )
        + "\n"
    ).encode("utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        target,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 20, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)
    _verify(target)
    _write_detached_manifest(target)
    return target


def _verify(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        corrupt = archive.testzip()
        if corrupt is not None:
            raise ValueError("archive CRC validation failed")
        names = set(archive.namelist())
        manifest = json.loads(archive.read("package_manifest.json"))
        declared = manifest.get("members")
        if not isinstance(declared, dict) or names != set(declared) | {
            "package_manifest.json"
        }:
            raise ValueError("archive member inventory mismatch")
        for name, record in declared.items():
            data = archive.read(name)
            if len(data) != record.get("bytes") or hashlib.sha256(
                data
            ).hexdigest() != record.get("sha256"):
                raise ValueError("archive member hash mismatch")
            lowered = name.lower()
            if any(part in lowered for part in (".env", ".entry")):
                raise ValueError("forbidden protected cache/secret path found")
            if not name.endswith(".f32") and any(
                pattern.search(data) for pattern in SECRET_PATTERNS[:3]
            ):
                raise ValueError("secret-like value remains after redaction")


def _write_detached_manifest(path: Path) -> Path:
    """Record hashes for every ZIP member, including its in-archive manifest."""
    members: dict[str, dict[str, Any]] = {}
    with zipfile.ZipFile(path) as archive:
        for name in sorted(archive.namelist()):
            data = archive.read(name)
            members[name] = {
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            }
    sidecar = path.with_suffix(path.suffix + ".manifest.json")
    sidecar_data = {
        "archive": path.name,
        "archive_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "member_count": len(members),
        "members": members,
    }
    sidecar.write_text(
        json.dumps(sidecar_data, ensure_ascii=False, sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )
    recorded = json.loads(sidecar.read_text(encoding="utf-8"))
    if (
        recorded.get("archive_sha256")
        != hashlib.sha256(path.read_bytes()).hexdigest()
        or recorded.get("member_count") != len(members)
        or recorded.get("members") != members
    ):
        raise ValueError("detached archive manifest verification failed")
    return sidecar


def main() -> int:
    """Build the package and print only its archive-level summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        package = build_package(output=args.output)
        digest = hashlib.sha256(package.read_bytes()).hexdigest()
        size = package.stat().st_size
        with zipfile.ZipFile(package) as archive:
            count = len(archive.namelist())
        sidecar = package.with_suffix(package.suffix + ".manifest.json")
        print(
            json.dumps(
                {
                    "status": "PASS",
                    "path": str(package.resolve()),
                    "sha256": digest,
                    "bytes": size,
                    "member_count": count,
                    "payload_hashes_verified": count - 1,
                    "all_members_manifested": count,
                    "detached_manifest": str(sidecar.resolve()),
                    "question_text_printed": False,
                },
                sort_keys=True,
            )
        )
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        print("PACKAGE=FAIL; details sanitized")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
