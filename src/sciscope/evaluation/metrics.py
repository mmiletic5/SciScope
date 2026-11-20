"""Question-level retrieval metrics with explicit eligible populations."""

from __future__ import annotations

import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QuestionMetrics:
    """Retrieval metrics and denominator metadata for one question."""

    question_id: str
    expected_insufficient_evidence: bool
    gold_unit_count: int
    recall_at_k: Mapping[int, float | None]
    evidence_hit_at_k: Mapping[int, float | None]
    mrr_at_k: Mapping[int, float | None]
    positive_metric_eligible: bool


@dataclass(frozen=True, slots=True)
class MacroMetrics:
    """Macro-by-question aggregates and population counts."""

    question_count: int
    positive_question_count: int
    insufficient_question_count: int
    recall_at_k: Mapping[int, float | None]
    evidence_hit_at_k: Mapping[int, float | None]
    mrr_at_k: Mapping[int, float | None]


def compute_question_metrics(
    *,
    gold_unit_ids: frozenset[str],
    first_rank_by_unit: Mapping[str, int],
    expected_insufficient_evidence: bool,
    cutoffs: Sequence[int] = (1, 3, 5, 10, 20),
    question_id: str = "synthetic-question",
) -> QuestionMetrics:
    """Compute Recall@K, Evidence Hit@K, and MRR@K for one question.

    Cutoffs beyond the retrieved list are interpreted at the available list
    length, so an empty list is a miss (zero) for answerable questions.

    Args:
        gold_unit_ids: Unique relevant gold evidence-unit IDs.
        first_rank_by_unit: Earliest one-based rank for each matched gold ID.
        expected_insufficient_evidence: Whether the question has no positive
            evidence reference by definition.
        cutoffs: Positive integer retrieval cutoffs.
        question_id: Stable question identifier for aggregation.

    Returns:
        Per-question metric values and eligibility metadata.

    Raises:
        ValueError: If ground truth, matched IDs, ranks, or cutoffs are invalid.
    """
    if not question_id.strip():
        raise ValueError("question ID must be nonempty")
    if not cutoffs or any(
        isinstance(k, bool) or not isinstance(k, int) or k < 1 for k in cutoffs
    ):
        raise ValueError("cutoffs must be positive integers")
    if len(cutoffs) != len(set(cutoffs)):
        raise ValueError("cutoffs must be unique")
    if expected_insufficient_evidence:
        if gold_unit_ids:
            raise ValueError(
                "insufficient case cannot have positive ground truth"
            )
        empty = {k: None for k in cutoffs}
        return QuestionMetrics(
            question_id,
            True,
            0,
            empty,
            dict(empty),
            dict(empty),
            False,
        )
    if not gold_unit_ids:
        raise ValueError("answerable question has no positive ground truth")
    if not set(first_rank_by_unit) <= gold_unit_ids:
        raise ValueError("matched ranks contain unknown gold IDs")
    if any(
        isinstance(rank, bool) or not isinstance(rank, int) or rank < 1
        for rank in first_rank_by_unit.values()
    ):
        raise ValueError("matching ranks must be positive one-based integers")

    recall: dict[int, float] = {}
    hit: dict[int, float] = {}
    mrr: dict[int, float] = {}
    for cutoff in cutoffs:
        ranks = [rank for rank in first_rank_by_unit.values() if rank <= cutoff]
        recall[cutoff] = len(ranks) / len(gold_unit_ids)
        hit[cutoff] = float(bool(ranks))
        mrr[cutoff] = 1.0 / min(ranks) if ranks else 0.0
    return QuestionMetrics(
        question_id,
        False,
        len(gold_unit_ids),
        recall,
        hit,
        mrr,
        True,
    )


def aggregate_macro(questions: Sequence[QuestionMetrics]) -> MacroMetrics:
    """Macro-average per-question metrics, excluding negative cases.

    Args:
        questions: One record per unique question in the same cohort/arm.

    Returns:
        Per-question macro means and explicit cohort population counts.

    Raises:
        ValueError: If IDs repeat or cutoff sets differ.
    """
    ids = [item.question_id for item in questions]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate question ID in metric aggregation")
    cutoffs = set(questions[0].recall_at_k) if questions else set()
    if any(
        set(item.recall_at_k) != cutoffs
        or set(item.evidence_hit_at_k) != cutoffs
        or set(item.mrr_at_k) != cutoffs
        for item in questions
    ):
        raise ValueError("question metric cutoff sets do not match")
    positives = [item for item in questions if item.positive_metric_eligible]

    def mean(metric: str) -> dict[int, float | None]:
        values = {
            cutoff: [
                cast_value
                for item in positives
                if (cast_value := getattr(item, metric).get(cutoff)) is not None
            ]
            for cutoff in cutoffs
        }
        return {
            cutoff: statistics.fmean(items) if items else None
            for cutoff, items in values.items()
        }

    return MacroMetrics(
        question_count=len(questions),
        positive_question_count=len(positives),
        insufficient_question_count=sum(
            item.expected_insufficient_evidence for item in questions
        ),
        recall_at_k=mean("recall_at_k"),
        evidence_hit_at_k=mean("evidence_hit_at_k"),
        mrr_at_k=mean("mrr_at_k"),
    )
