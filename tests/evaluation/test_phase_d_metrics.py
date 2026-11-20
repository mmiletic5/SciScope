"""Hand-calculated synthetic metric oracles and denominator checks."""

from __future__ import annotations

import pytest

from sciscope.evaluation.metrics import (
    QuestionMetrics,
    aggregate_macro,
    compute_question_metrics,
)


def test_recall_hit_and_mrr_match_independent_hand_calculation() -> None:
    """Two of four gold units appear, first at rank two."""
    result = compute_question_metrics(
        gold_unit_ids=frozenset({"g1", "g2", "g3", "g4"}),
        first_rank_by_unit={"g1": 2, "g3": 4},
        expected_insufficient_evidence=False,
        cutoffs=(1, 3, 5),
    )

    assert result.recall_at_k == {1: 0.0, 3: 0.25, 5: 0.5}
    assert result.evidence_hit_at_k == {1: 0.0, 3: 1.0, 5: 1.0}
    assert result.mrr_at_k == {1: 0.0, 3: 0.5, 5: 0.5}
    assert all(0.0 <= value <= 1.0 for value in result.recall_at_k.values())


def test_insufficient_question_has_undefined_positive_metrics() -> None:
    """Insufficient-evidence cases are not scored as zero-recall positives."""
    result = compute_question_metrics(
        gold_unit_ids=frozenset(),
        first_rank_by_unit={},
        expected_insufficient_evidence=True,
        cutoffs=(1, 3),
    )

    assert result.recall_at_k == {1: None, 3: None}
    assert result.mrr_at_k == {1: None, 3: None}
    assert result.evidence_hit_at_k == {1: None, 3: None}
    assert not result.positive_metric_eligible


def test_missing_ground_truth_and_rank_outside_gold_fail_closed() -> None:
    """Positive cases need evidence and every counted rank must be valid."""
    with pytest.raises(ValueError, match="ground truth"):
        compute_question_metrics(
            gold_unit_ids=frozenset(),
            first_rank_by_unit={},
            expected_insufficient_evidence=False,
            cutoffs=(1,),
        )
    with pytest.raises(ValueError, match="unknown"):
        compute_question_metrics(
            gold_unit_ids=frozenset({"g1"}),
            first_rank_by_unit={"other": 1},
            expected_insufficient_evidence=False,
            cutoffs=(1,),
        )


def test_zero_results_is_zero_for_answerable_question() -> None:
    """No candidates is a miss, not a missing denominator."""
    result = compute_question_metrics(
        gold_unit_ids=frozenset({"g1"}),
        first_rank_by_unit={},
        expected_insufficient_evidence=False,
        cutoffs=(1, 5),
    )

    assert result.recall_at_k == {1: 0.0, 5: 0.0}
    assert result.evidence_hit_at_k == {1: 0.0, 5: 0.0}
    assert result.mrr_at_k == {1: 0.0, 5: 0.0}


def test_macro_uses_questions_not_pooled_evidence_units() -> None:
    """Each answerable question has equal macro weight despite unequal gold."""
    first = compute_question_metrics(
        question_id="q1",
        gold_unit_ids=frozenset({"g1"}),
        first_rank_by_unit={"g1": 1},
        expected_insufficient_evidence=False,
        cutoffs=(1,),
    )
    second = compute_question_metrics(
        question_id="q2",
        gold_unit_ids=frozenset({"g1", "g2", "g3", "g4"}),
        first_rank_by_unit={},
        expected_insufficient_evidence=False,
        cutoffs=(1,),
    )
    negative = compute_question_metrics(
        question_id="q3",
        gold_unit_ids=frozenset(),
        first_rank_by_unit={},
        expected_insufficient_evidence=True,
        cutoffs=(1,),
    )

    result = aggregate_macro((first, second, negative))

    assert result.question_count == 3
    assert result.positive_question_count == 2
    assert result.insufficient_question_count == 1
    assert result.recall_at_k == {1: 0.5}


def test_duplicate_metric_records_do_not_change_macro() -> None:
    """Metric aggregation rejects repeated question IDs."""
    record = QuestionMetrics(
        question_id="q1",
        expected_insufficient_evidence=False,
        gold_unit_count=1,
        recall_at_k={1: 1.0},
        evidence_hit_at_k={1: 1.0},
        mrr_at_k={1: 1.0},
        positive_metric_eligible=True,
    )

    with pytest.raises(ValueError, match="duplicate"):
        aggregate_macro((record, record))
