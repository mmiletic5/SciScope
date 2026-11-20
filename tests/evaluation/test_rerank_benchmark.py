"""Tests for the offline, fixed-partition reranking benchmark."""

from __future__ import annotations

import pytest

from sciscope.evaluation.rerank import (
    APPROVED_QUESTION_IDS,
    BenchmarkCandidate,
    BenchmarkQuestion,
    BenchmarkResult,
    RankingMetrics,
    assess_diagnostic,
    compare_reranker,
)


def _questions() -> tuple[BenchmarkQuestion, ...]:
    ids = sorted(APPROVED_QUESTION_IDS)
    cases = []
    for index, question_id in enumerate(ids):
        relevant = () if question_id == "gq-ins-001" else (f"e{index}",)
        question_type = {
            "gq-sp-001": "single_paper",
            "gq-cmp-001": "comparison",
            "gq-conf-001": "conflict",
            "gq-gap-001": "gap",
            "gq-ins-001": "insufficient",
        }[question_id]
        candidates = (
            BenchmarkCandidate("a" * 64, "passage one", ()),
            BenchmarkCandidate("b" * 64, "passage two", relevant),
        )
        cases.append(
            BenchmarkQuestion(
                question_id=question_id,
                question_type=question_type,
                query_text=f"query {index}",
                candidates=candidates,
                relevant_evidence_ids=relevant,
                rrf_latency_ms=80.0,
            )
        )
    return tuple(cases)


class FakeBenchmarkReranker:
    """Return fixed passage scores without external inference."""

    model_id = "fake-reranker"
    model_revision = "test-revision"
    model_sha256 = "0" * 64
    cold_start_ms = None

    def rerank(self, query_text, candidates):
        """Score candidates by their stable input positions."""
        del query_text
        return [
            (candidate.chunk_id, float(index))
            for index, candidate in enumerate(candidates)
        ]


def test_benchmark_uses_exact_five_allowlisted_questions_and_repeats() -> None:
    """The offline benchmark evaluates fixed questions and reports metrics."""
    result = compare_reranker(
        _questions(),
        FakeBenchmarkReranker(),
        repetitions=2,
        environment={"python": "3.12"},
    )

    assert result.question_ids == tuple(sorted(APPROVED_QUESTION_IDS))
    assert len(result.per_question) == 5
    assert result.per_question["gq-ins-001"].baseline.mrr_at_k[10] is None
    assert result.per_question["gq-ins-001"].reranked.recall_at_k[10] is None
    assert result.run_manifest["model_id"] == "fake-reranker"
    assert result.run_manifest["question_ids"] == list(
        sorted(APPROVED_QUESTION_IDS)
    )
    assert result.warm_p95_ms >= 0


def test_benchmark_rejects_heldout_or_missing_question_ids() -> None:
    """Only the full fixed five-question allowlist is accepted."""
    cases = list(_questions())
    cases[0] = BenchmarkQuestion(
        question_id="heldout-question",
        question_type="positive",
        query_text="not used",
        candidates=(),
        relevant_evidence_ids=("evidence",),
        rrf_latency_ms=80.0,
    )
    with pytest.raises(ValueError, match="approved five-question set"):
        compare_reranker(
            cases,
            FakeBenchmarkReranker(),
            repetitions=1,
            environment={},
        )


def test_benchmark_requires_matching_candidate_order_and_positive_latency() -> (
    None
):
    """Malformed offline inputs fail before metric or latency claims."""
    cases = list(_questions())
    cases[0] = BenchmarkQuestion(
        question_id=cases[0].question_id,
        question_type=cases[0].question_type,
        query_text=cases[0].query_text,
        candidates=cases[0].candidates,
        relevant_evidence_ids=cases[0].relevant_evidence_ids,
        rrf_latency_ms=0.0,
    )
    with pytest.raises(ValueError, match="RRF latency"):
        compare_reranker(
            cases,
            FakeBenchmarkReranker(),
            repetitions=1,
            environment={},
        )


def test_diagnostic_assessment_gates() -> None:
    """A passing screen remains advisory and never enables production."""
    baseline = RankingMetrics(
        recall_at_k={1: 0.2, 3: 0.4, 5: 0.5, 10: 0.6, 20: 0.8},
        evidence_hit_at_k={1: 0.2, 3: 0.4, 5: 0.6, 10: 0.7, 20: 0.9},
        mrr_at_k={1: 0.2, 3: 0.4, 5: 0.5, 10: 0.6, 20: 0.7},
    )
    reranked = RankingMetrics(
        recall_at_k={1: 0.2, 3: 0.4, 5: 0.5, 10: 0.6, 20: 0.8},
        evidence_hit_at_k={1: 0.2, 3: 0.4, 5: 0.6, 10: 0.7, 20: 0.9},
        mrr_at_k={1: 0.2, 3: 0.4, 5: 0.5, 10: 0.66, 20: 0.7},
    )
    result = BenchmarkResult(
        question_ids=tuple(sorted(APPROVED_QUESTION_IDS)),
        per_question={},
        baseline_macro=baseline,
        reranked_macro=reranked,
        rrf_p95_ms=100.0,
        warm_p95_ms=190.0,
        reranker_p95_ms=90.0,
        cold_start_ms=400.0,
        run_manifest={},
    )

    assessment = assess_diagnostic(result)

    assert assessment.diagnostic_passed
    assert not assessment.production_enabled


def test_diagnostic_assessment_fails_warm_latency_and_regression() -> None:
    """A large quality gain cannot mask a material regression or slow cost."""
    baseline = RankingMetrics(
        recall_at_k={1: 0.2, 3: 0.4, 5: 0.5, 10: 0.6, 20: 0.8},
        evidence_hit_at_k={1: 0.2, 3: 0.4, 5: 0.6, 10: 0.7, 20: 0.9},
        mrr_at_k={1: 0.2, 3: 0.4, 5: 0.5, 10: 0.6, 20: 0.7},
    )
    reranked = RankingMetrics(
        recall_at_k={1: 0.1, 3: 0.4, 5: 0.5, 10: 0.6, 20: 0.8},
        evidence_hit_at_k={1: 0.2, 3: 0.4, 5: 0.6, 10: 0.7, 20: 0.9},
        mrr_at_k={1: 0.2, 3: 0.4, 5: 0.5, 10: 0.7, 20: 0.7},
    )
    result = BenchmarkResult(
        question_ids=tuple(sorted(APPROVED_QUESTION_IDS)),
        per_question={},
        baseline_macro=baseline,
        reranked_macro=reranked,
        rrf_p95_ms=100.0,
        warm_p95_ms=1001.0,
        reranker_p95_ms=901.0,
        cold_start_ms=None,
        run_manifest={},
    )

    assessment = assess_diagnostic(result)

    assert assessment.quality_gate_passed
    assert not assessment.regression_gate_passed
    assert not assessment.latency_gate_passed
    assert not assessment.diagnostic_passed
    assert not assessment.production_enabled
