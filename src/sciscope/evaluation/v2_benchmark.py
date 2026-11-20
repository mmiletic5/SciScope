"""Metrics for source-grounded, development-only Retrieval v2 comparisons."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

import ir_measures
from ir_measures import nDCG

from sciscope.evaluation.matching import (
    EvidenceReference,
    MatchingResult,
    RetrievedEvidence,
    match_evidence_units,
)
from sciscope.evaluation.metrics import (
    QuestionMetrics,
    compute_question_metrics,
)
from sciscope.plos_pilot.doi import normalize_doi

_CUTOFFS = (5, 10, 20)
_NDCG_AT_10 = nDCG @ 10


@dataclass(frozen=True, slots=True)
class V2QuestionMetrics:
    """Per-question retrieval metrics and evidence-source coverage."""

    question: QuestionMetrics
    ndcg_at_10: float | None
    source_coverage_at_k: Mapping[int, float | None]


def compute_v2_question_metrics(
    *,
    question_id: str,
    references: Sequence[EvidenceReference],
    retrieved: Sequence[RetrievedEvidence],
    expected_insufficient_evidence: bool,
) -> V2QuestionMetrics:
    """Measure one ranking with existing evidence matching and IR measures.

    Recall and MRR retain the project's canonical unique evidence-unit
    definitions. nDCG@10 is computed by ``ir-measures`` over unique positive
    evidence units ordered by their first retrieved rank; irrelevant chunks
    remain as zero-relevance run entries so they retain their rank positions.

    Args:
        question_id: Stable, non-sensitive development question identifier.
        references: Source-grounded DOI/locator/quotation annotations.
        retrieved: Ranked, exact returned evidence records.
        expected_insufficient_evidence: Whether positive retrieval metrics are
            undefined for this question.

    Returns:
        Per-question Recall@K, MRR@K, nDCG@10, and source DOI coverage.

    Raises:
        ValueError: If gold references or returned evidence are invalid.
    """
    matches = match_evidence_units(references, retrieved)
    question_metrics = compute_question_metrics(
        gold_unit_ids=matches.relevant_unit_ids,
        first_rank_by_unit=matches.first_rank_by_unit,
        expected_insufficient_evidence=expected_insufficient_evidence,
        cutoffs=_CUTOFFS,
        question_id=question_id,
    )
    if expected_insufficient_evidence:
        return V2QuestionMetrics(question_metrics, None, _empty_coverage())

    ndcg_value = _compute_ndcg_at_10(
        question_id, references, retrieved, matches
    )
    source_coverage = _source_coverage(references, retrieved)
    return V2QuestionMetrics(question_metrics, ndcg_value, source_coverage)


def verify_doi_attribution(
    retrieved: RetrievedEvidence,
    resolved: RetrievedEvidence,
) -> bool:
    """Check a returned citation against an active-snapshot chunk lookup.

    Args:
        retrieved: Candidate returned by retrieval.
        resolved: Same chunk loaded by stable ID through the evidence lookup.

    Returns:
        Whether ID, normalized DOI, primary locator, and exact text all match.
    """
    return (
        retrieved.chunk_id == resolved.chunk_id
        and normalize_doi(retrieved.doi).doi == normalize_doi(resolved.doi).doi
        and retrieved.source_locator == resolved.source_locator
        and retrieved.text == resolved.text
    )


def _compute_ndcg_at_10(
    question_id: str,
    references: Sequence[EvidenceReference],
    retrieved: Sequence[RetrievedEvidence],
    all_matches: MatchingResult,
) -> float:
    qrels: dict[str, dict[str, int]] = {
        question_id: {
            f"unit:{unit_id}": 1
            for unit_id in sorted(all_matches.relevant_unit_ids)
        }
    }
    run: dict[str, dict[str, float]] = {question_id: {}}
    seen_units: set[str] = set()
    seen_chunk_ids: set[str] = set()
    for rank, candidate in enumerate(retrieved, start=1):
        single = match_evidence_units(references, (candidate,))
        new_units = set(single.first_rank_by_unit) - seen_units
        seen_units.update(new_units)
        if candidate.chunk_id in seen_chunk_ids:
            new_units.clear()
        seen_chunk_ids.add(candidate.chunk_id)
        if new_units:
            for unit_id in sorted(new_units):
                run[question_id][f"unit:{unit_id}"] = 1.0 / rank
        else:
            noise_id = f"noise:{rank}:{candidate.chunk_id}"
            run[question_id][noise_id] = 1.0 / rank
            qrels[question_id][noise_id] = 0

    aggregate = ir_measures.calc_aggregate([_NDCG_AT_10], qrels, run)
    value = aggregate.get(_NDCG_AT_10)
    if value is None:
        return 0.0
    return float(cast(Any, value))


def _source_coverage(
    references: Sequence[EvidenceReference],
    retrieved: Sequence[RetrievedEvidence],
) -> dict[int, float | None]:
    unit_dois = {
        reference.unit_id: normalize_doi(reference.doi).doi
        for reference in references
        if reference.relevance_label in (2, 3)
    }
    expected_dois = set(unit_dois.values())
    if not expected_dois:
        return _empty_coverage()
    result: dict[int, float | None] = {}
    for cutoff in _CUTOFFS:
        found: set[str] = set()
        for candidate in retrieved[:cutoff]:
            matches = match_evidence_units(references, (candidate,))
            found.update(
                unit_dois[unit_id]
                for unit_id in matches.first_rank_by_unit
                if unit_id in unit_dois
            )
        result[cutoff] = len(found) / len(expected_dois)
    return result


def _empty_coverage() -> dict[int, float | None]:
    return {cutoff: None for cutoff in _CUTOFFS}
