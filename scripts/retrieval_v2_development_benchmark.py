"""Compare approved development retrieval arms against the read-only pilot."""

from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import re
import statistics
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.engine import make_url

from sciscope.database.config import DatabaseSettings
from sciscope.database.session import create_database_engine
from sciscope.evaluation.golden import load_allowlisted_records
from sciscope.evaluation.matching import EvidenceReference, RetrievedEvidence
from sciscope.evaluation.metrics import aggregate_macro
from sciscope.evaluation.rerank import APPROVED_QUESTION_IDS
from sciscope.evaluation.v2_benchmark import (
    V2QuestionMetrics,
    compute_v2_question_metrics,
    verify_doi_attribution,
)
from sciscope.retrieval import _core
from sciscope.retrieval._core import _RetrievalCore
from sciscope.retrieval._lookup import EvidenceLookup
from sciscope.retrieval._reranking import (
    MiniLMCrossEncoderReranker,
    Reranker,
    RerankerCandidate,
)

ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = ROOT / ".cache" / "phase_c_rerank" / "benchmark-inputs.json"
GOLDEN_V0_PATH = ROOT / "evals" / "golden_questions.v0.json"
OUTPUT_PATH = ROOT / ".cache" / "retrieval_v2" / "development-comparison.json"
MODEL_REVISION = "233902d25c440f23af6f7d6e94d2946bac0bee0a"
MODEL_SHA256 = (
    "402c3a69514c2ccb83898cef29bdf468ec79da80fa091d9967b2de03e7e4adc0"
)
EXPECTED_CORPUS_VERSION = "pilot17-xml-1fff1573b610"
EXPECTED_COUNTS = (17, 319, 728, 728)
EXPECTED_DATABASE = "sciscope_test_005"
EXPECTED_ROLE = "sciscope"
EXPECTED_EMBEDDING_SET_ID = 115
TOP_K = 50
REPETITIONS = 5


class _SavedVectorEmbedder:
    """Return only exact vectors mapped to the approved development IDs."""

    def __init__(
        self,
        questions: Mapping[str, Mapping[str, Any]],
        vectors: Mapping[str, Any],
    ) -> None:
        self._questions = questions
        self._vectors = vectors

    def embed_query(self, query: str, *, config: object) -> Sequence[float]:
        del config
        matches = [
            question_id
            for question_id, question in self._questions.items()
            if question["question"] == query
        ]
        if len(matches) != 1:
            raise ValueError("query is not uniquely mapped to a development ID")
        return self._vectors[matches[0]]


class _TimedReranker:
    """Record local inference latency without exposing input text."""

    def __init__(self, inner: Reranker) -> None:
        self._inner = inner
        self.model_id = inner.model_id
        self.model_revision = inner.model_revision
        self.model_sha256 = inner.model_sha256
        self.cold_start_ms: float | None = None
        self.latencies_ms: list[float] = []

    def rerank(
        self,
        query_text: str,
        candidates: Sequence[RerankerCandidate],
    ) -> Sequence[tuple[str, float]]:
        started = time.perf_counter()
        result = self._inner.rerank(query_text, candidates)
        self.latencies_ms.append((time.perf_counter() - started) * 1000)
        self.cold_start_ms = self._inner.cold_start_ms
        return result


def _read_database_url() -> str:
    value = os.environ.get("SCISCOPE_TEST_DATABASE_URL", "").strip()
    if value:
        return value
    env_path = ROOT / ".env"
    if not env_path.is_file():
        raise RuntimeError("read-only test database configuration is missing")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*SCISCOPE_TEST_DATABASE_URL\s*=(.*)$", line)
        if match:
            return match.group(1).strip().strip("\"'")
    raise RuntimeError("read-only test database configuration is missing")


def _load_development_data() -> tuple[dict[str, Any], dict[str, Any]]:
    if not INPUT_PATH.is_file() or not GOLDEN_V0_PATH.is_file():
        raise RuntimeError("approved development benchmark inputs are missing")
    cache = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    if cache.get("input_schema") != "phase-c-rerank-input-v1":
        raise RuntimeError("development vector artifact version mismatch")
    if set(cache.get("approved_question_ids", ())) != APPROVED_QUESTION_IDS:
        raise RuntimeError("development vector artifact ID allowlist mismatch")
    question_items = cache.get("questions")
    vectors = cache.get("vectors")
    if not isinstance(question_items, list) or not isinstance(vectors, dict):
        raise RuntimeError("development vector artifact shape is invalid")
    questions = {
        item["question_id"]: item
        for item in question_items
        if isinstance(item, dict) and isinstance(item.get("question_id"), str)
    }
    if (
        set(questions) != APPROVED_QUESTION_IDS
        or set(vectors) != APPROVED_QUESTION_IDS
    ):
        raise RuntimeError("development question/vector mapping is incomplete")
    embedding = cache.get("embedding", {})
    if (
        embedding.get("provider") != "openai"
        or embedding.get("model") != "text-embedding-3-small"
        or embedding.get("dimensions") != 1536
        or embedding.get("query_prefix") != ""
    ):
        raise RuntimeError("saved development vector identity is incompatible")
    for question_id, question in questions.items():
        query = question.get("question")
        vector = vectors[question_id]
        if (
            not isinstance(query, str)
            or not isinstance(question.get("question_sha256"), str)
            or hashlib.sha256(query.encode("utf-8")).hexdigest()
            != question["question_sha256"]
            or not isinstance(vector, list)
            or len(vector) != 1536
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                for value in vector
            )
            or math.hypot(*vector) == 0.0
        ):
            raise RuntimeError("development query/vector identity is invalid")

    records = load_allowlisted_records(GOLDEN_V0_PATH, APPROVED_QUESTION_IDS)
    gold = {item["question_id"]: item for item in records}
    if set(gold) != APPROVED_QUESTION_IDS:
        raise RuntimeError("development Golden allowlist is incomplete")
    for question_id in APPROVED_QUESTION_IDS:
        query = gold[question_id].get("question")
        if (
            query != questions[question_id]["question"]
            or hashlib.sha256(query.encode("utf-8")).hexdigest()
            != questions[question_id]["question_sha256"]
        ):
            raise RuntimeError(
                "development question/vector association mismatch"
            )
    return cache, gold


def _preflight_database(engine: Any, saved_corpus: Mapping[str, Any]) -> None:
    with engine.connect() as connection, connection.begin():
        connection.exec_driver_sql(
            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
        )
        row = connection.execute(
            text(
                "SELECT current_database(), current_user, "
                "current_setting('server_version_num'), "
                "(SELECT extversion FROM pg_extension WHERE extname='vector'), "
                "(SELECT count(*) FROM delivery_imports WHERE is_active), "
                "(SELECT id FROM delivery_imports WHERE is_active), "
                "(SELECT delivery_digest FROM delivery_imports "
                "WHERE is_active), "
                "(SELECT contract_version FROM delivery_imports "
                "WHERE is_active), "
                "(SELECT id FROM embedding_sets WHERE delivery_import_id = "
                "(SELECT id FROM delivery_imports WHERE is_active)), "
                "(SELECT count(*) FROM papers WHERE delivery_import_id = "
                "(SELECT id FROM delivery_imports WHERE is_active)), "
                "(SELECT count(*) FROM sections WHERE delivery_import_id = "
                "(SELECT id FROM delivery_imports WHERE is_active)), "
                "(SELECT count(*) FROM chunks WHERE delivery_import_id = "
                "(SELECT id FROM delivery_imports WHERE is_active)), "
                "(SELECT count(*) FROM chunk_embeddings "
                "WHERE delivery_import_id = "
                "(SELECT id FROM delivery_imports WHERE is_active))"
            )
        ).one()
        if (
            row[0] != EXPECTED_DATABASE
            or row[1] != EXPECTED_ROLE
            or not str(row[2]).startswith("17")
            or row[3] != "0.8.7"
            or row[4] != 1
            or row[5] != saved_corpus.get("active_import_id")
            or row[6] != saved_corpus.get("delivery_digest")
            or row[7] != "0.3.0"
            or row[8] != EXPECTED_EMBEDDING_SET_ID
            or tuple(row[9:13]) != EXPECTED_COUNTS
        ):
            raise RuntimeError("read-only pilot identity preflight failed")
        transaction_read_only = connection.execute(
            text("SELECT current_setting('transaction_read_only')")
        ).scalar_one()
        if transaction_read_only != "on":
            raise RuntimeError("database transaction is not read-only")


def _references(question: Mapping[str, Any]) -> tuple[EvidenceReference, ...]:
    values: list[EvidenceReference] = []
    for paper in question.get("relevant_papers", []):
        sections = paper.get("sections", [])
        if not sections:
            raise RuntimeError("development gold section is missing")
        for evidence in paper.get("evidence", []):
            values.append(
                EvidenceReference(
                    doi=paper["doi"],
                    section=sections[0],
                    source_locator=evidence["source_locator"],
                    relevance_label=int(evidence["relevance_label"]),
                    quotation=evidence["quotation"],
                )
            )
    return tuple(values)


def _result_evidence(
    hit: Any,
    lookup: EvidenceLookup,
    resolved_cache: dict[str, RetrievedEvidence],
) -> tuple[RetrievedEvidence, bool]:
    resolved = resolved_cache.get(hit.chunk_id)
    if resolved is None:
        chunk = lookup.get_chunk(hit.chunk_id).chunk
        resolved = RetrievedEvidence(
            chunk_id=chunk.chunk_id,
            doi=chunk.doi,
            section_path=tuple(str(item) for item in chunk.section_path),
            source_locator=chunk.source_locator,
            span_locators=tuple(
                str(span["source_locator"])
                for span in chunk.spans
                if isinstance(span.get("source_locator"), str)
            ),
            text=chunk.text,
        )
        resolved_cache[hit.chunk_id] = resolved
    returned = RetrievedEvidence(
        chunk_id=hit.chunk_id,
        doi=hit.doi,
        section_path=hit.section_path,
        source_locator=hit.source_locator,
        span_locators=resolved.span_locators,
        text=hit.text,
    )
    return returned, verify_doi_attribution(returned, resolved)


def _percentile95(values: Sequence[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return ordered[index]


def _macro_payload(values: Sequence[V2QuestionMetrics]) -> dict[str, Any]:
    macro = aggregate_macro([item.question for item in values])
    positive = [item for item in values if item.ndcg_at_10 is not None]
    ndcg_values = cast(list[float], [item.ndcg_at_10 for item in positive])
    ndcg = statistics.fmean(ndcg_values) if ndcg_values else None
    return {
        "question_count": macro.question_count,
        "positive_question_count": macro.positive_question_count,
        "insufficient_question_count": macro.insufficient_question_count,
        "recall_at_k": {str(k): v for k, v in macro.recall_at_k.items()},
        "mrr_at_k": {str(k): v for k, v in macro.mrr_at_k.items()},
        "ndcg_at_10": ndcg,
        "ndcg_denominator": len(positive),
    }


def _serialize_question_metrics(value: V2QuestionMetrics) -> dict[str, Any]:
    return {
        "expected_insufficient_evidence": (
            value.question.expected_insufficient_evidence
        ),
        "gold_unit_count": value.question.gold_unit_count,
        "positive_metric_eligible": value.question.positive_metric_eligible,
        "recall_at_k": {
            str(k): v for k, v in value.question.recall_at_k.items()
        },
        "mrr_at_k": {str(k): v for k, v in value.question.mrr_at_k.items()},
        "ndcg_at_10": value.ndcg_at_10,
        "source_coverage_at_k": {
            str(k): v for k, v in value.source_coverage_at_k.items()
        },
    }


def run_benchmark() -> dict[str, Any]:
    """Run a fixed, read-only comparison on the five approved v0 dev queries."""
    cache, gold_questions = _load_development_data()
    saved_corpus = cache.get("corpus", {})
    if saved_corpus.get("corpus_version") != EXPECTED_CORPUS_VERSION:
        raise RuntimeError("saved development corpus identity is unexpected")
    raw_url = _read_database_url()
    if make_url(raw_url).database != EXPECTED_DATABASE:
        raise RuntimeError("read-only database target is not the test pilot")
    database_url = DatabaseSettings.from_environment(
        {"DATABASE_URL": raw_url}
    ).url
    engine = create_database_engine(DatabaseSettings(url=database_url))
    try:
        _preflight_database(engine, saved_corpus)
        print("READ_ONLY_PREFLIGHT=PASS", flush=True)
        lookup = EvidenceLookup(engine)
        vectors = cache["vectors"]
        query_items = {item["question_id"]: item for item in cache["questions"]}
        embedder = _SavedVectorEmbedder(query_items, vectors)
        model = MiniLMCrossEncoderReranker(
            ROOT / ".cache" / "phase_c_rerank" / "model" / MODEL_REVISION,
            model_revision=MODEL_REVISION,
            expected_sha256=MODEL_SHA256,
        )
        timed_reranker = _TimedReranker(model)
        timed_reranker.rerank(
            "synthetic warmup query",
            (RerankerCandidate("0" * 64, "synthetic warmup passage"),),
        )

        arms: dict[str, tuple[str, _RetrievalCore, str]] = {
            "dense": (
                "retrieval.v1",
                _RetrievalCore(engine, embedder),
                "dense",
            ),
            "postgres_fts": (
                "retrieval.v1",
                _RetrievalCore(engine, None),
                "lexical",
            ),
            "v1_hybrid": (
                "retrieval.v1",
                _RetrievalCore(engine, embedder),
                "hybrid",
            ),
            "bm25": ("retrieval.v2", _RetrievalCore(engine, None), "lexical"),
            "dense_bm25_rrf": (
                "retrieval.v2",
                _RetrievalCore(engine, embedder),
                "hybrid",
            ),
            "dense_bm25_rrf_minilm": (
                "retrieval.v2",
                _RetrievalCore(engine, embedder, reranker=timed_reranker),
                "hybrid",
            ),
        }
        latencies: dict[str, list[float]] = {name: [] for name in arms}
        stage_ms: dict[str, dict[str, list[float]]] = {
            name: {"bm25": [], "rrf": [], "reranker": []} for name in arms
        }
        outputs: dict[str, dict[str, tuple[Any, ...]]] = {
            name: {} for name in arms
        }
        corpus_identity: dict[str, Any] | None = None
        for question_id in sorted(APPROVED_QUESTION_IDS):
            question = gold_questions[question_id]
            query = question["question"]
            for arm_name, (contract, core, mode) in arms.items():
                repeated_ids: tuple[str, ...] | None = None
                final_hits: tuple[Any, ...] = ()
                print(f"ARM_QUERY_START={arm_name}", flush=True)
                for _ in range(REPETITIONS):
                    stage_start = time.perf_counter()
                    before_bm25 = len(_BM25_TIMINGS)
                    before_rrf = len(_RRF_TIMINGS)
                    before_reranker = len(timed_reranker.latencies_ms)
                    request: dict[str, object] = {
                        "contract_version": contract,
                        "request_id": f"v2-dev-{question_id}",
                        "query_text": query,
                        "mode": mode,
                        "top_k": TOP_K,
                    }
                    if mode == "hybrid":
                        request["ranking"] = {"candidate_pool_size": TOP_K}
                    response = core.retrieve(request)
                    latencies[arm_name].append(
                        (time.perf_counter() - stage_start) * 1000
                    )
                    stage_ms[arm_name]["bm25"].extend(
                        _BM25_TIMINGS[before_bm25:]
                    )
                    stage_ms[arm_name]["rrf"].extend(_RRF_TIMINGS[before_rrf:])
                    stage_ms[arm_name]["reranker"].extend(
                        timed_reranker.latencies_ms[before_reranker:]
                    )
                    observed_ids = tuple(
                        item.chunk_id for item in response.results
                    )
                    if (
                        repeated_ids is not None
                        and observed_ids != repeated_ids
                    ):
                        raise RuntimeError(
                            "retrieval ordering changed across repeats"
                        )
                    repeated_ids = observed_ids
                    final_hits = response.results
                    if (
                        response.corpus.corpus_version
                        != EXPECTED_CORPUS_VERSION
                    ):
                        raise RuntimeError(
                            "retrieval returned a different corpus"
                        )
                    current_identity = {
                        "corpus_version": response.corpus.corpus_version,
                        "delivery_digest": response.corpus.delivery_digest,
                        "embedding_set_id": response.corpus.embedding_set_id,
                        "active_import_id": response.corpus.import_id,
                    }
                    if corpus_identity is None:
                        corpus_identity = current_identity
                    elif current_identity != corpus_identity:
                        raise RuntimeError(
                            "retrieval snapshot identity changed"
                        )
                outputs[arm_name][question_id] = final_hits
                print(f"ARM_QUERY_DONE={arm_name}", flush=True)

        evidence_cache: dict[str, RetrievedEvidence] = {}
        arm_reports: dict[str, Any] = {}
        total_citation_failures = 0
        for arm_name, arm_questions in outputs.items():
            print(f"CITATION_CHECK_START={arm_name}", flush=True)
            per_question: dict[str, Any] = {}
            question_metrics: list[V2QuestionMetrics] = []
            attribution_correct = 0
            attribution_total = 0
            citation_failures = 0
            for question_id in sorted(APPROVED_QUESTION_IDS):
                question = gold_questions[question_id]
                refs = _references(question)
                resolved_results: list[RetrievedEvidence] = []
                for hit in arm_questions[question_id]:
                    result, correct = _result_evidence(
                        hit, lookup, evidence_cache
                    )
                    resolved_results.append(result)
                    attribution_total += 1
                    attribution_correct += int(correct)
                    citation_failures += int(not correct)
                    total_citation_failures += int(not correct)
                metrics = compute_v2_question_metrics(
                    question_id=question_id,
                    references=refs,
                    retrieved=resolved_results,
                    expected_insufficient_evidence=(
                        question.get("expected_insufficient_evidence") is True
                        or question.get("question_type")
                        == "insufficient_evidence"
                    ),
                )
                question_metrics.append(metrics)
                per_question[question_id] = {
                    **_serialize_question_metrics(metrics),
                    "retrieved_count": len(resolved_results),
                }
            arm_reports[arm_name] = {
                "per_question": per_question,
                "macro": _macro_payload(question_metrics),
                "doi_attribution": {
                    "correct": attribution_correct,
                    "count": attribution_total,
                    "rate": (
                        attribution_correct / attribution_total
                        if attribution_total
                        else None
                    ),
                    "citation_identity_failures": citation_failures,
                },
                "latency_ms": {
                    "samples": len(latencies[arm_name]),
                    "median": statistics.median(latencies[arm_name]),
                    "p95": _percentile95(latencies[arm_name]),
                    "max": max(latencies[arm_name]),
                    "stage_samples": {
                        stage: len(values)
                        for stage, values in stage_ms[arm_name].items()
                    },
                    "stage_median_ms": {
                        stage: (statistics.median(values) if values else None)
                        for stage, values in stage_ms[arm_name].items()
                    },
                },
            }
            print(f"CITATION_CHECK_DONE={arm_name}", flush=True)

        if total_citation_failures:
            raise RuntimeError("retrieved citation failed active source lookup")
        return {
            "status": "PASS",
            "created_at_utc": datetime.now(UTC).isoformat(),
            "question_ids": sorted(APPROVED_QUESTION_IDS),
            "question_count": len(APPROVED_QUESTION_IDS),
            "dataset": "golden-v0-development-only",
            "query_vector_source": (
                "saved Phase C development artifact; no generation"
            ),
            "query_vector_count": len(vectors),
            "query_vector_dimensions": 1536,
            "query_vector_model": "text-embedding-3-small",
            "corpus": corpus_identity,
            "arms": arm_reports,
            "minilm": {
                "model_id": model.model_id,
                "revision": model.model_revision,
                "directory_sha256": model.model_sha256,
                "cold_start_ms": model.cold_start_ms,
                "inference_device": "cpu",
            },
            "environment": {
                "python": sys.version.split()[0],
                "platform": platform.platform(),
                "torch_cuda": "not used by benchmark; local model is CPU",
            },
            "metric_policy": {
                "recall_mrr": "existing evidence-unit matcher and metrics",
                "ndcg": (
                    "ir-measures nDCG@10 over unique positive evidence units; "
                    "zero-relevance placeholders preserve nonrelevant ranks"
                ),
                "insufficient_evidence": (
                    "excluded from positive metric denominators; "
                    "reported per question"
                ),
                "scores": (
                    "ranking scores are not calibrated confidence probabilities"
                ),
                "statistical_claim": (
                    "descriptive only; five previously exposed "
                    "development questions"
                ),
            },
            "limitations": [
                "Five development questions are a small diagnostic sample.",
                "No protected held-out question or result was accessed.",
                "No new query embedding was generated.",
                "Person 3 application integration needs their approval.",
            ],
        }
    finally:
        engine.dispose()


_BM25_TIMINGS: list[float] = []
_RRF_TIMINGS: list[float] = []


def _install_timing_wrappers() -> None:
    original_bm25 = _core._bm25_branch
    original_rrf = _core.fuse_ranked_candidates

    def timed_bm25(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        result = original_bm25(*args, **kwargs)
        _BM25_TIMINGS.append((time.perf_counter() - started) * 1000)
        return result

    def timed_rrf(*args: Any, **kwargs: Any) -> Any:
        started = time.perf_counter()
        result = original_rrf(*args, **kwargs)
        _RRF_TIMINGS.append((time.perf_counter() - started) * 1000)
        return result

    _core._bm25_branch = timed_bm25
    _core.fuse_ranked_candidates = timed_rrf


def main() -> int:
    """Run, safely summarize, and persist the development-only benchmark."""
    try:
        _install_timing_wrappers()
        report = run_benchmark()
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(report, indent=2, sort_keys=True).encode("utf-8")
        temporary = OUTPUT_PATH.with_suffix(".tmp")
        temporary.write_bytes(payload)
        temporary.replace(OUTPUT_PATH)
        print("STATUS=PASS")
        print(f"REPORT={OUTPUT_PATH.relative_to(ROOT).as_posix()}")
        print(f"REPORT_SHA256={hashlib.sha256(payload).hexdigest()}")
        print(f"QUESTION_COUNT={report['question_count']}")
        for name, result in report["arms"].items():
            macro = result["macro"]
            print(
                f"ARM={name} R5={macro['recall_at_k']['5']} "
                f"R10={macro['recall_at_k']['10']} "
                f"R20={macro['recall_at_k']['20']} "
                f"MRR10={macro['mrr_at_k']['10']} "
                f"NDCG10={macro['ndcg_at_10']} "
                f"LATENCY_P95_MS={result['latency_ms']['p95']}"
            )
        return 0
    except Exception as error:
        print(f"STATUS=FAIL ERROR={type(error).__name__}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
