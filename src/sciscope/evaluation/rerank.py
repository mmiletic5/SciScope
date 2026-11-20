"""Reproducible offline comparison of Phase B RRF and a local reranker."""

from __future__ import annotations

import hashlib
import math
import statistics
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from sciscope.retrieval._reranking import Reranker, RerankerCandidate

APPROVED_QUESTION_IDS = frozenset(
    {"gq-sp-001", "gq-cmp-001", "gq-conf-001", "gq-gap-001", "gq-ins-001"}
)
_QUESTION_TYPES = {
    "gq-sp-001": "single_paper",
    "gq-cmp-001": "comparison",
    "gq-conf-001": "conflict",
    "gq-gap-001": "gap",
    "gq-ins-001": "insufficient",
}
_CUTOFFS = (1, 3, 5, 10, 20)


@dataclass(frozen=True, slots=True)
class BenchmarkCandidate:
    """One fixed RRF candidate and its precomputed evidence matches."""

    chunk_id: str
    text: str
    matched_evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BenchmarkQuestion:
    """One allowlisted smoke question with a saved Phase B candidate list."""

    question_id: str
    question_type: str
    query_text: str
    candidates: tuple[BenchmarkCandidate, ...]
    relevant_evidence_ids: tuple[str, ...]
    rrf_latency_ms: float


@dataclass(frozen=True, slots=True)
class RankingMetrics:
    """Per-question retrieval metrics at valid candidate cutoffs."""

    recall_at_k: Mapping[int, float | None]
    evidence_hit_at_k: Mapping[int, float | None]
    mrr_at_k: Mapping[int, float | None]


@dataclass(frozen=True, slots=True)
class QuestionComparison:
    """Baseline and reranked metrics for one smoke question."""

    baseline: RankingMetrics
    reranked: RankingMetrics


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    """Reproducible comparison results and observed warm latency."""

    question_ids: tuple[str, ...]
    per_question: Mapping[str, QuestionComparison]
    baseline_macro: RankingMetrics
    reranked_macro: RankingMetrics
    rrf_p95_ms: float
    warm_p95_ms: float
    reranker_p95_ms: float
    cold_start_ms: float | None
    run_manifest: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class DiagnosticAssessment:
    """Objective screening result; never enables production by itself."""

    quality_gate_passed: bool
    regression_gate_passed: bool
    latency_gate_passed: bool
    diagnostic_passed: bool
    production_enabled: bool
    reasons: tuple[str, ...]


def compare_reranker(
    questions: Sequence[BenchmarkQuestion],
    reranker: Reranker,
    *,
    repetitions: int = 5,
    environment: Mapping[str, str],
    run_metadata: Mapping[str, str] | None = None,
) -> BenchmarkResult:
    """Compare the same saved RRF candidate lists with a local reranker.

    Question text, source passages, and evidence references remain in memory;
    the returned run manifest stores only allowlisted IDs and hashes.

    Args:
        questions: Exactly the five approved development smoke records.
        reranker: A deterministic fake or pinned local scorer.
        repetitions: Number of measured warm passes per question.
        environment: Non-secret execution environment metadata.
        run_metadata: Non-secret corpus, embedding, retrieval, revision, and
            dataset identities needed to reproduce the saved candidates.

    Returns:
        Per-question and macro metrics, p95 latency measurements, and a
        secret-free run manifest.

    Raises:
        ValueError: If question partition, evidence labels, candidate inputs,
            repetitions, or manifest metadata are invalid.
        Exception: Reranker errors are propagated without a fallback.
    """
    cases = _validate_inputs(questions, repetitions, environment, run_metadata)
    baseline_metrics = {
        case.question_id: _metrics(case.candidates, case.relevant_evidence_ids)
        for case in cases
    }
    reranked_orders: dict[str, tuple[BenchmarkCandidate, ...]] = {}
    reranker_latencies: list[float] = []
    rrf_latencies: list[float] = []
    warm_latencies: list[float] = []

    for case in cases:
        inputs = tuple(
            RerankerCandidate(candidate.chunk_id, candidate.text)
            for candidate in case.candidates
        )
        reranker.rerank(case.query_text, inputs)

    for case in cases:
        inputs = tuple(
            RerankerCandidate(candidate.chunk_id, candidate.text)
            for candidate in case.candidates
        )
        stable_order: tuple[str, ...] | None = None
        base_rank = {
            candidate.chunk_id: index
            for index, candidate in enumerate(case.candidates)
        }
        final_order: tuple[BenchmarkCandidate, ...] = ()
        for _ in range(repetitions):
            started = time.perf_counter()
            raw_scores = reranker.rerank(case.query_text, inputs)
            scores = _validated_scores(inputs, raw_scores)
            reranked_ids = tuple(
                candidate.chunk_id
                for candidate in sorted(
                    case.candidates,
                    key=lambda candidate: (
                        -scores[candidate.chunk_id],
                        base_rank[candidate.chunk_id],
                        candidate.chunk_id,
                    ),
                )
            )
            elapsed_ms = (time.perf_counter() - started) * 1000
            if stable_order is not None and reranked_ids != stable_order:
                raise ValueError(
                    "reranker output order is unstable across repeats"
                )
            stable_order = reranked_ids
            final_order = tuple(
                sorted(
                    case.candidates,
                    key=lambda candidate: (
                        -scores[candidate.chunk_id],
                        base_rank[candidate.chunk_id],
                        candidate.chunk_id,
                    ),
                )
            )
            reranker_latencies.append(elapsed_ms)
            rrf_latencies.append(case.rrf_latency_ms)
            warm_latencies.append(case.rrf_latency_ms + elapsed_ms)
        reranked_orders[case.question_id] = final_order

    comparisons: dict[str, QuestionComparison] = {}
    for case in cases:
        comparisons[case.question_id] = QuestionComparison(
            baseline=baseline_metrics[case.question_id],
            reranked=_metrics(
                reranked_orders[case.question_id], case.relevant_evidence_ids
            ),
        )

    question_ids = tuple(sorted(APPROVED_QUESTION_IDS))
    cold_start_ms = getattr(reranker, "cold_start_ms", None)
    candidate_hashes = {
        case.question_id: _candidate_hash(case.candidates) for case in cases
    }
    manifest: dict[str, object] = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "question_ids": list(question_ids),
        "question_hashes": {
            case.question_id: _sha256(case.query_text.encode("utf-8"))
            for case in cases
        },
        "candidate_pool_hashes": candidate_hashes,
        "model_id": reranker.model_id,
        "model_revision": reranker.model_revision,
        "model_sha256": reranker.model_sha256,
        "repetitions": repetitions,
        "environment": dict(environment),
        "run_metadata": dict(run_metadata or {}),
        "network_access": "disabled-by-adapter-local-files-only",
    }
    return BenchmarkResult(
        question_ids=question_ids,
        per_question=comparisons,
        baseline_macro=_macro_metrics(
            [item.baseline for item in comparisons.values()]
        ),
        reranked_macro=_macro_metrics(
            [item.reranked for item in comparisons.values()]
        ),
        rrf_p95_ms=_percentile95(rrf_latencies),
        warm_p95_ms=_percentile95(warm_latencies),
        reranker_p95_ms=_percentile95(reranker_latencies),
        cold_start_ms=cold_start_ms,
        run_manifest=manifest,
    )


def assess_diagnostic(result: BenchmarkResult) -> DiagnosticAssessment:
    """Apply the predeclared quality and bounded-latency screening criteria.

    A diagnostic pass is only a recommendation for owner review. It never
    switches the production reranker setting.
    """
    baseline_mrr = result.baseline_macro.mrr_at_k[10]
    reranked_mrr = result.reranked_macro.mrr_at_k[10]
    baseline_hit = result.baseline_macro.evidence_hit_at_k[5]
    reranked_hit = result.reranked_macro.evidence_hit_at_k[5]
    mrr_gain = _absolute_gain(baseline_mrr, reranked_mrr)
    hit_gain = _absolute_gain(baseline_hit, reranked_hit)
    quality_passed = mrr_gain >= 0.05 or hit_gain >= 0.10

    regressions = tuple(
        f"{metric}@{cutoff} regressed by more than 0.05"
        for metric in ("recall_at_k", "evidence_hit_at_k", "mrr_at_k")
        for cutoff in _CUTOFFS
        if _exceeds_regression(
            getattr(result.baseline_macro, metric)[cutoff],
            getattr(result.reranked_macro, metric)[cutoff],
        )
    )
    regression_passed = not regressions
    latency_passed = (
        result.warm_p95_ms <= 2.0 * result.rrf_p95_ms
        and result.warm_p95_ms <= 1000.0
    )
    reasons = list(regressions)
    if not quality_passed:
        reasons.append(
            "neither predeclared quality improvement threshold passed"
        )
    if not latency_passed:
        reasons.append("warm p95 latency exceeded a screening bound")
    return DiagnosticAssessment(
        quality_gate_passed=quality_passed,
        regression_gate_passed=regression_passed,
        latency_gate_passed=latency_passed,
        diagnostic_passed=(
            quality_passed and regression_passed and latency_passed
        ),
        production_enabled=False,
        reasons=tuple(reasons),
    )


def _absolute_gain(baseline: float | None, reranked: float | None) -> float:
    if baseline is None or reranked is None:
        return float("-inf")
    return reranked - baseline


def _exceeds_regression(baseline: float | None, reranked: float | None) -> bool:
    if baseline is None or reranked is None:
        return False
    return reranked - baseline < -0.05


def _validate_inputs(
    questions: Sequence[BenchmarkQuestion],
    repetitions: int,
    environment: Mapping[str, str],
    run_metadata: Mapping[str, str] | None,
) -> tuple[BenchmarkQuestion, ...]:
    if isinstance(repetitions, bool) or not 1 <= repetitions <= 100:
        raise ValueError("repetitions must be from 1 to 100")
    ids = [question.question_id for question in questions]
    if len(ids) != len(set(ids)) or set(ids) != APPROVED_QUESTION_IDS:
        raise ValueError("benchmark requires the approved five-question set")
    if any(
        key.lower().endswith(("key", "token", "secret", "password"))
        for key in environment
    ):
        raise ValueError("environment metadata cannot contain secrets")
    if run_metadata and any(
        key.lower().endswith(("key", "token", "secret", "password"))
        for key in run_metadata
    ):
        raise ValueError("run metadata cannot contain secrets")
    for question in questions:
        if question.question_type != _QUESTION_TYPES[question.question_id]:
            raise ValueError("question type does not match the approved ID")
        if not question.query_text.strip():
            raise ValueError("query text must be nonempty")
        if (
            not math.isfinite(question.rrf_latency_ms)
            or question.rrf_latency_ms <= 0
        ):
            raise ValueError(
                "RRF latency must be a positive finite measurement"
            )
        if len(question.candidates) > 50:
            raise ValueError("candidate pool must contain at most 50 records")
        chunk_ids = [candidate.chunk_id for candidate in question.candidates]
        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("candidate chunk IDs must be unique")
        if any(not candidate.text for candidate in question.candidates):
            raise ValueError("candidate text must be nonempty")
        if (
            not question.relevant_evidence_ids
            and question.question_id != "gq-ins-001"
        ):
            raise ValueError("positive smoke questions require evidence labels")
        known = set(question.relevant_evidence_ids)
        if any(
            not set(candidate.matched_evidence_ids) <= known
            for candidate in question.candidates
        ):
            raise ValueError("candidate evidence matches must be labeled")
    return tuple(sorted(questions, key=lambda item: item.question_id))


def _validated_scores(
    candidates: Sequence[RerankerCandidate],
    output: Sequence[tuple[str, float]],
) -> dict[str, float]:
    expected = {candidate.chunk_id for candidate in candidates}
    scores: dict[str, float] = {}
    for chunk_id, value in output:
        if chunk_id not in expected or chunk_id in scores:
            raise ValueError(
                "reranker output IDs are missing, extra, or duplicated"
            )
        if isinstance(value, bool) or not isinstance(value, (float, int)):
            raise ValueError("reranker output scores must be finite numbers")
        score = float(value)
        if not math.isfinite(score):
            raise ValueError("reranker output scores must be finite numbers")
        scores[chunk_id] = score
    if set(scores) != expected:
        raise ValueError(
            "reranker output IDs are missing, extra, or duplicated"
        )
    return scores


def _metrics(
    candidates: Sequence[BenchmarkCandidate],
    relevant_evidence_ids: Sequence[str],
) -> RankingMetrics:
    if not relevant_evidence_ids:
        empty = {cutoff: None for cutoff in _CUTOFFS}
        return RankingMetrics(empty, dict(empty), dict(empty))
    relevant = set(relevant_evidence_ids)
    recall: dict[int, float | None] = {}
    hit: dict[int, float | None] = {}
    mrr: dict[int, float | None] = {}
    for cutoff in _CUTOFFS:
        if cutoff > len(candidates):
            recall[cutoff] = hit[cutoff] = mrr[cutoff] = None
            continue
        found: set[str] = set()
        first_rank: int | None = None
        for rank, candidate in enumerate(candidates[:cutoff], start=1):
            matched = set(candidate.matched_evidence_ids) & relevant
            found.update(matched)
            if matched and first_rank is None:
                first_rank = rank
        recall[cutoff] = len(found) / len(relevant)
        hit[cutoff] = float(bool(found))
        mrr[cutoff] = 1 / first_rank if first_rank is not None else 0.0
    return RankingMetrics(recall, hit, mrr)


def _macro_metrics(metrics: Sequence[RankingMetrics]) -> RankingMetrics:
    def average(values: Sequence[float | None]) -> float | None:
        valid = [value for value in values if value is not None]
        return statistics.fmean(valid) if valid else None

    return RankingMetrics(
        recall_at_k={
            cutoff: average([item.recall_at_k[cutoff] for item in metrics])
            for cutoff in _CUTOFFS
        },
        evidence_hit_at_k={
            cutoff: average(
                [item.evidence_hit_at_k[cutoff] for item in metrics]
            )
            for cutoff in _CUTOFFS
        },
        mrr_at_k={
            cutoff: average([item.mrr_at_k[cutoff] for item in metrics])
            for cutoff in _CUTOFFS
        },
    )


def _candidate_hash(candidates: Sequence[BenchmarkCandidate]) -> str:
    content = "\n".join(
        f"{candidate.chunk_id}\t{_sha256(candidate.text.encode('utf-8'))}\t"
        f"{','.join(candidate.matched_evidence_ids)}"
        for candidate in candidates
    )
    return _sha256(content.encode("utf-8"))


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _percentile95(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return ordered[index]
