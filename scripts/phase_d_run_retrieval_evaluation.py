"""Run explicitly authorized Phase D retrieval on the read-only frozen pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import struct
import subprocess
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from sciscope.database.config import DatabaseSettings
from sciscope.database.session import create_database_engine
from sciscope.embedding.cache import decode_entry
from sciscope.evaluation.embeddings import verify_query_cache_manifest
from sciscope.evaluation.execution import (
    METRIC_CUTOFFS,
    RetrievalCore,
    build_gold_references,
    question_metrics_for_response,
    run_reproducible_retrieval,
)
from sciscope.evaluation.golden import (
    load_allowlisted_records,
    partition_sha256,
)
from sciscope.evaluation.report import build_result_report
from sciscope.evaluation.runner import require_evaluation_authorizations
from sciscope.retrieval._core import _RetrievalCore

ROOT = Path(__file__).resolve().parents[1]
PROTECTED = ROOT / "evals" / "protected"
V0_PATH = ROOT / "evals" / "golden_questions.v0.json"
V1_BASE = PROTECTED / "golden_v1_review"
READINESS_PATH = PROTECTED / "phase_d_t005_readiness_report.json"
APPROVALS = PROTECTED / "phase_d_authorizations"
CORPUS_VERSION = "pilot17-xml-1fff1573b610"
CORPUS_SHA256 = (
    "1fff1573b610c27e2e8016343d2f6429df294db974db4af898c4a0f82ffc26bd"
)
EMBEDDING_SET_ID = 115
V0_DEV_IDS = {
    "gq-sp-001",
    "gq-cmp-001",
    "gq-conf-001",
    "gq-gap-001",
    "gq-ins-001",
}
V0_ALL_IDS = {
    *(f"gq-sp-{n:03}" for n in range(1, 9)),
    *(f"gq-cmp-{n:03}" for n in range(1, 5)),
    *(f"gq-conf-{n:03}" for n in range(1, 4)),
    *(f"gq-gap-{n:03}" for n in range(1, 4)),
    *(f"gq-ins-{n:03}" for n in range(1, 4)),
}
V1_HO_IDS = {
    "golden-v1-q2",
    "golden-v1-q3",
    "golden-v1-q5",
    "golden-v1-q7",
    "golden-v1-q8",
    "golden-v1-q9",
}
EXPECTED_CONFIG = {
    "provider": "openai",
    "model": "text-embedding-3-small",
    "response_model_id": "text-embedding-3-small",
    "dimensions": 1536,
    "query_prefix": "",
    "passage_prefix": "",
    "dtype": "float32-le",
}
ARMS = ("dense", "lexical", "hybrid")


class CachedQueryEmbedder:
    """Serve preverified query vectors without invoking an embedding API."""

    def __init__(self, vectors: dict[str, tuple[float, ...]]) -> None:
        """Store query vectors indexed by their exact normalized text."""
        self._vectors = vectors

    def embed_query(self, text: str, *, config: Any) -> tuple[float, ...]:
        """Return only the verified vector associated with this query."""
        del config
        vector = self._vectors.get(text.strip())
        if vector is None:
            raise ValueError("verified query vector is unavailable")
        return vector


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _cohort_identity(cohort: str) -> dict[str, Any]:
    if cohort == "v0-held-out":
        ids = frozenset(V0_ALL_IDS - V0_DEV_IDS)
        digest = _sha256(V0_PATH.read_bytes())
        dataset_version = "v0"
    elif cohort == "v1-held-out":
        ids = frozenset(V1_HO_IDS)
        freeze = json.loads(
            (V1_BASE / "phase_d_baseline_freeze.json").read_text(
                encoding="utf-8"
            )
        )
        partitions = freeze.get("golden_v1_partitions", {})
        if (
            partitions.get("assignment_frozen_before_question_generation")
            is not True
            or set(partitions.get("development", [])) != {"Q1", "Q4", "Q6"}
            or set(partitions.get("held_out", []))
            != {"Q2", "Q3", "Q5", "Q7", "Q8", "Q9"}
        ):
            raise ValueError("frozen v1 slot assignment mismatch")
        digest = _sha256(
            (V1_BASE / "golden_questions.v1.candidates.json").read_bytes()
        )
        dataset_version = "golden-v1"
    else:
        raise ValueError("unsupported cohort")
    expected_count = 16 if cohort == "v0-held-out" else 6
    return {
        "dataset_version": dataset_version,
        "dataset_sha256": digest,
        "partition": cohort,
        "partition_sha256": partition_sha256(sorted(ids)),
        "expected_ids": ids,
        "expected_question_count": expected_count,
    }


def _load_cohort(cohort: str, identity: dict[str, Any]) -> list[dict[str, Any]]:
    """Load text only after its exact dataset/cohort identity is authorized."""
    if cohort == "v0-held-out":
        questions = load_allowlisted_records(V0_PATH, identity["expected_ids"])
    elif cohort == "v1-held-out":
        path = V1_BASE / "held_out" / "golden_questions.v1.held_out.json"
        questions = json.loads(path.read_text(encoding="utf-8"))["questions"]
    else:
        raise ValueError("unsupported cohort")
    if (
        len(questions) != identity["expected_question_count"]
        or {q.get("question_id") for q in questions} != identity["expected_ids"]
    ):
        raise ValueError("frozen cohort membership mismatch")
    return questions


def _validate_approvals(
    cohort: str, dataset: dict[str, Any], readiness: dict[str, Any]
) -> None:
    t005, t006 = require_evaluation_authorizations(
        APPROVALS / f"t005_{cohort}_approval.json",
        APPROVALS / f"t006_{cohort}_approval.json",
    )
    item = next(
        (entry for entry in readiness["cohorts"] if entry["cohort"] == cohort),
        None,
    )
    if item is None or readiness.get("status") != "PASS":
        raise ValueError("T005 readiness is unavailable")
    for record in (t005, t006):
        for field in ("dataset_version", "dataset_sha256", "partition_sha256"):
            if record.get(field) != dataset.get(field):
                raise ValueError("authorization dataset identity mismatch")
        if (
            record.get("corpus_version") != CORPUS_VERSION
            or record.get("corpus_sha256") != CORPUS_SHA256
        ):
            raise ValueError("authorization corpus identity mismatch")
    if t006.get("embedding_set_id") != EMBEDDING_SET_ID:
        raise ValueError("T006 embedding-set identity mismatch")
    if (
        item.get("dataset_sha256") != dataset["dataset_sha256"]
        or item.get("partition_sha256") != dataset["partition_sha256"]
        or item.get("expected_question_count")
        != dataset["expected_question_count"]
    ):
        raise ValueError("T005 cohort identity mismatch")
    receipt_path = APPROVALS / "t006_user_approval_source.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt_copy = dict(receipt)
    digest = receipt_copy.pop("approval_evidence_sha256", None)
    if digest != _sha256(_canonical(receipt_copy)):
        raise ValueError("T006 approval receipt integrity mismatch")
    if (
        t006.get("approval_evidence_sha256") != digest
        or receipt.get("purpose") != "T006 protected held-out retrieval only"
        or receipt.get("scope")
        != {
            "cohorts": ["v0-held-out", "v1-held-out"],
            "database": "sciscope_test_005",
            "database_access": "read-only",
            "modes": ["dense", "lexical", "hybrid"],
            "tuning": False,
            "database_writes": False,
            "migrations": False,
            "paid_apis": False,
            "dataset_changes": False,
        }
    ):
        raise ValueError("T006 approval source mismatch")


def _load_vectors(
    cohort: str,
    questions: list[dict[str, Any]],
    dataset: dict[str, Any],
) -> tuple[dict[str, tuple[float, ...]], str]:
    cache = ROOT / "data" / "embeddings" / "phase-d-query" / cohort
    manifest = json.loads((cache / "manifest.json").read_text(encoding="utf-8"))
    manifest_sha = _sha256(_canonical(manifest))
    expected = {
        **dataset,
        "corpus_version": CORPUS_VERSION,
        "corpus_sha256": CORPUS_SHA256,
        "embedding_set_id": EMBEDDING_SET_ID,
        "config": EXPECTED_CONFIG,
        "manifest_sha256": manifest_sha,
    }
    verify_query_cache_manifest(cache, manifest, questions, expected=expected)
    questions_by_id = {q["question_id"]: q for q in questions}
    by_query: dict[str, tuple[float, ...]] = {}
    for record in manifest["vectors"]:
        question = questions_by_id[record["question_id"]]
        entry = decode_entry(
            (cache / record["entry_path"]).read_bytes(),
            model="text-embedding-3-small",
            dimensions=1536,
            input_sha256=record["provider_input_sha256"],
        )
        vector = tuple(
            number for (number,) in struct.iter_unpack("<f", entry.vector_bytes)
        )
        query = question["question"].strip()
        if query in by_query and by_query[query] != vector:
            raise ValueError("duplicate query cache mapping is inconsistent")
        by_query[query] = vector
    return by_query, manifest_sha


def _locator_sections() -> dict[str, str]:
    path = ROOT / "data" / "delivery" / "pilot" / "chunks.jsonl"
    sections_by_locator: dict[str, set[str]] = defaultdict(set)
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            chunk = json.loads(line)
            section = " > ".join(chunk["section_path"])
            locators = [chunk["source_locator"]]
            locators.extend(span["source_locator"] for span in chunk["spans"])
            for locator in locators:
                sections_by_locator[locator].add(section)
    return {
        locator: next(iter(sections))
        for locator, sections in sections_by_locator.items()
        if len(sections) == 1
    }


def _preflight() -> dict[str, Any]:
    from scripts.phase_d_readonly_db_preflight import (
        _load_source_url,
        run_read_only_preflight,
    )

    result = run_read_only_preflight(_load_source_url())
    if (
        result.get("status") != "PASS"
        or result.get("database") != "sciscope_test_005"
        or result.get("role") != "sciscope"
        or result.get("transaction_read_only") is not True
        or result.get("corpus_version") != CORPUS_VERSION
        or result.get("embedding_set_id") != EMBEDDING_SET_ID
        or result.get("counts")
        != {"papers": 17, "sections": 319, "chunks": 728, "embeddings": 728}
    ):
        raise ValueError("read-only database/corpus preflight failed")
    return result


def _config_hash() -> str:
    freeze = json.loads(
        (V1_BASE / "phase_d_baseline_freeze.json").read_text(encoding="utf-8")
    )
    retrieval = freeze.get("retrieval")
    if not isinstance(retrieval, dict):
        raise ValueError("frozen retrieval settings are missing")
    config = {
        "retrieval": retrieval,
        "modes": list(ARMS),
        "top_k": 20,
        "metric_cutoffs": list(METRIC_CUTOFFS),
        "repetitions": 2,
        "query_model": "text-embedding-3-small",
        "query_dimensions": 1536,
    }
    return _sha256(_canonical(config))


def _environment() -> dict[str, str | int | bool]:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )
    return {
        "os": platform.platform(),
        "windows_build": platform.version(),
        "python_version": platform.python_version(),
        "dependency_lock_sha256": _sha256((ROOT / "uv.lock").read_bytes()),
        "git_revision": revision,
        "git_dirty": dirty,
    }


def _run_one(cohort: str) -> dict[str, Any]:
    readiness = json.loads(READINESS_PATH.read_text(encoding="utf-8"))
    dataset = _cohort_identity(cohort)
    _validate_approvals(cohort, dataset, readiness)
    questions = _load_cohort(cohort, dataset)
    dataset = {
        key: value
        for key, value in dataset.items()
        if key not in {"expected_ids", "expected_question_count"}
    }
    vectors, cache_manifest_sha = _load_vectors(cohort, questions, dataset)
    before = _preflight()
    from scripts.phase_d_readonly_db_preflight import (
        _load_source_url,
        derive_test_database_url,
    )

    db_url = derive_test_database_url(_load_source_url())
    engine = create_database_engine(DatabaseSettings(url=db_url))
    try:
        core = _RetrievalCore(engine, CachedQueryEmbedder(vectors))
        section_map = _locator_sections()
        references = {
            question["question_id"]: build_gold_references(
                question, section_by_locator=section_map
            )
            for question in questions
        }
        metrics: dict[str, dict[str, Any]] = {arm: {} for arm in ARMS}
        latency: dict[str, dict[str, list[float]]] = {
            arm: defaultdict(list) for arm in ARMS
        }
        snapshot_ids: set[tuple[int, int]] = set()
        for arm in ARMS:
            for question in questions:
                first, elapsed = run_reproducible_retrieval(
                    cast(RetrievalCore, core),
                    question,
                    cohort=cohort,
                    arm=arm,
                    clock=time.perf_counter,
                )
                for value in elapsed:
                    latency[arm]["retrieval_total"].append(value)
                if (
                    first.corpus.corpus_version != CORPUS_VERSION
                    or first.corpus.embedding_set_id != EMBEDDING_SET_ID
                ):
                    raise ValueError("retrieval corpus identity changed")
                snapshot_ids.add(
                    (first.corpus.import_id, first.corpus.embedding_set_id)
                )
                question_id = question["question_id"]
                metrics[arm][question_id] = question_metrics_for_response(
                    question, references[question_id], first
                )
        if len(snapshot_ids) != 1:
            raise ValueError("active corpus snapshot changed during run")
    finally:
        engine.dispose()
    after = _preflight()
    if before != after:
        raise ValueError("database/corpus postflight mismatch")
    config_sha = _config_hash()
    environment = _environment()
    output_dir = ROOT / "evals" / "results" / f"phase_d_{cohort}"
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    files: dict[str, str] = {}
    for arm in ARMS:
        report = build_result_report(
            dataset_version=dataset["dataset_version"],
            dataset_sha256=dataset["dataset_sha256"],
            cohort=cohort,
            partition_sha256=dataset["partition_sha256"],
            corpus_version=CORPUS_VERSION,
            corpus_sha256=CORPUS_SHA256,
            arm="hybrid_rrf" if arm == "hybrid" else arm,
            config_sha256=config_sha,
            question_metrics=metrics[arm],
            latency_ms=latency[arm],
            environment=environment,
        ).to_dict()
        output = output_dir / f"{run_id}_{arm}.json"
        if output.exists():
            raise ValueError("evaluation output already exists")
        output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        files[arm] = output.relative_to(ROOT).as_posix()
    return {
        "cohort": cohort,
        "dataset_version": dataset["dataset_version"],
        "dataset_sha256": dataset["dataset_sha256"],
        "partition_sha256": dataset["partition_sha256"],
        "question_count": len(questions),
        "query_cache_manifest_sha256": cache_manifest_sha,
        "corpus_version": CORPUS_VERSION,
        "embedding_set_id": EMBEDDING_SET_ID,
        "modes": list(ARMS),
        "top_k": 20,
        "metric_cutoffs": list(METRIC_CUTOFFS),
        "repetitions": 2,
        "database_preflight": "PASS_READ_ONLY",
        "database_postflight": "PASS_READ_ONLY",
        "result_files": files,
        "question_text_logged": False,
        "retrieval_tuning_performed": False,
    }


def run_all() -> dict[str, Any]:
    """Run both separately authorized held-out cohorts."""
    return {
        "report_version": "phase-d-authorized-retrieval-run-v1",
        "run_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "cohorts": [
            _run_one("v0-held-out"),
            _run_one("v1-held-out"),
        ],
        "overall_status": "PASS",
        "held_out_questions_logged": False,
        "database_mutations": 0,
        "paid_api_calls": 0,
    }


def main() -> int:
    """Execute after checking both separate cohort-specific authorizations."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-authorized", action="store_true", required=True)
    parser.parse_args()
    try:
        # Validate T005/T006 records before protected question/cache loading.
        readiness = json.loads(READINESS_PATH.read_text(encoding="utf-8"))
        for cohort in ("v0-held-out", "v1-held-out"):
            next(x for x in readiness["cohorts"] if x["cohort"] == cohort)
            dataset = _cohort_identity(cohort)
            _validate_approvals(cohort, dataset, readiness)
        output = PROTECTED / "phase_d_t006_run_manifest.json"
        if output.exists():
            raise ValueError("T006 run manifest already exists")
        result = run_all()
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    except Exception:
        print("T006_RETRIEVAL=FAIL; details sanitized")
        return 1
    print(
        json.dumps(
            {
                "status": "PASS",
                "cohorts": len(result["cohorts"]),
                "questions": sum(
                    item["question_count"] for item in result["cohorts"]
                ),
                "modes_per_cohort": len(ARMS),
                "result_manifest": (
                    "evals/protected/phase_d_t006_run_manifest.json"
                ),
                "retrieval_results": "evals/results (Git-ignored)",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
