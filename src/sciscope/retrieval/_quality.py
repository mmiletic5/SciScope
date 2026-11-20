"""Deterministic post-processing for accepted Phase B retrieval results."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol


class EvidenceCandidate(Protocol):
    """Fields required to apply duplicate and diversity policies."""

    chunk_id: str
    doi: str
    source_locator: str
    text: str


@dataclass(frozen=True, slots=True)
class RankedCandidate[CandidateT: EvidenceCandidate]:
    """Candidate plus its immutable Phase B rank and optional local score."""

    hit: CandidateT
    base_rank: int
    reranker_score: float | None


@dataclass(frozen=True, slots=True)
class CandidateExclusion:
    """A candidate omitted by an explicit Phase C ranking policy."""

    chunk_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class RankingResult[CandidateT: EvidenceCandidate]:
    """Ranked unique evidence and deterministic exclusion reasons."""

    candidates: tuple[RankedCandidate[CandidateT], ...]
    exclusions: tuple[CandidateExclusion, ...]


def rank_evidence[CandidateT: EvidenceCandidate](
    results: Sequence[CandidateT],
    *,
    max_per_doi: int | None = 2,
    reranker_scores: Mapping[str, float] | None = None,
) -> RankingResult[CandidateT]:
    """Deduplicate, optionally rerank, and apply a per-DOI diversity cap.

    Phase B's order and scores remain authoritative when no reranker scores are
    supplied. Exact evidence deduplication uses the fields already returned by
    Phase B, so this module does not change or query the accepted retrieval
    core.

    Args:
        results: Unique ordered Phase B results.
        max_per_doi: Maximum retained candidates for one DOI. ``None`` disables
            the cap; integer values from 1 through 50 are accepted.
        reranker_scores: Optional finite score for each deduplicated candidate.

    Returns:
        A stable candidate sequence and exclusions in deterministic order.

    Raises:
        ValueError: If a cap, candidate identity, or reranker score mapping is
            invalid.
    """
    _validate_limit(max_per_doi)
    unique, exclusions = _deduplicate(results)
    scored = _attach_scores(unique, reranker_scores)
    ordered = _order_candidates(scored, reranker_scores is not None)
    selected, diversity_exclusions = _apply_diversity(ordered, max_per_doi)
    return RankingResult(
        candidates=tuple(selected),
        exclusions=tuple(exclusions + diversity_exclusions),
    )


def _validate_limit(value: int | None) -> None:
    if value is None:
        return
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= 50
    ):
        raise ValueError("max_per_doi must be None or an integer from 1 to 50")


def _deduplicate[CandidateT: EvidenceCandidate](
    results: Sequence[CandidateT],
) -> tuple[list[RankedCandidate[CandidateT]], list[CandidateExclusion]]:
    selected: list[RankedCandidate[CandidateT]] = []
    exclusions: list[CandidateExclusion] = []
    seen_ids: set[str] = set()
    seen_evidence: set[tuple[str, str, str]] = set()

    for base_rank, hit in enumerate(results, start=1):
        _validate_candidate(hit)
        if hit.chunk_id in seen_ids:
            raise ValueError("duplicate chunk_id in Phase B results")
        seen_ids.add(hit.chunk_id)
        key = (hit.doi, hit.source_locator, hit.text)
        if key in seen_evidence:
            exclusions.append(
                CandidateExclusion(hit.chunk_id, "duplicate_evidence")
            )
            continue
        seen_evidence.add(key)
        selected.append(RankedCandidate(hit, base_rank, None))
    return selected, exclusions


def _validate_candidate(hit: EvidenceCandidate) -> None:
    values = (hit.chunk_id, hit.doi, hit.source_locator, hit.text)
    if any(not isinstance(value, str) or not value for value in values):
        raise ValueError("candidate identity and provenance must be nonempty")


def _attach_scores[CandidateT: EvidenceCandidate](
    candidates: Sequence[RankedCandidate[CandidateT]],
    scores: Mapping[str, float] | None,
) -> list[RankedCandidate[CandidateT]]:
    if scores is None:
        return list(candidates)
    expected_ids = {candidate.hit.chunk_id for candidate in candidates}
    if set(scores) != expected_ids:
        raise ValueError(
            "reranker scores must match deduplicated candidate IDs"
        )
    attached: list[RankedCandidate[CandidateT]] = []
    for candidate in candidates:
        value = scores[candidate.hit.chunk_id]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("reranker scores must be finite numbers")
        score = float(value)
        if not math.isfinite(score):
            raise ValueError("reranker scores must be finite numbers")
        attached.append(
            RankedCandidate(candidate.hit, candidate.base_rank, score)
        )
    return attached


def _order_candidates[CandidateT: EvidenceCandidate](
    candidates: Sequence[RankedCandidate[CandidateT]], reranked: bool
) -> list[RankedCandidate[CandidateT]]:
    if not reranked:
        return list(candidates)

    def reranker_key(
        candidate: RankedCandidate[CandidateT],
    ) -> tuple[float, int, str]:
        score = candidate.reranker_score
        if score is None:
            raise ValueError("reranker score missing after validation")
        return (-score, candidate.base_rank, candidate.hit.chunk_id.lower())

    return sorted(candidates, key=reranker_key)


def _apply_diversity[CandidateT: EvidenceCandidate](
    candidates: Sequence[RankedCandidate[CandidateT]], max_per_doi: int | None
) -> tuple[list[RankedCandidate[CandidateT]], list[CandidateExclusion]]:
    if max_per_doi is None:
        return list(candidates), []
    selected: list[RankedCandidate[CandidateT]] = []
    exclusions: list[CandidateExclusion] = []
    counts: dict[str, int] = {}
    for candidate in candidates:
        doi = candidate.hit.doi
        count = counts.get(doi, 0)
        if count >= max_per_doi:
            exclusions.append(
                CandidateExclusion(candidate.hit.chunk_id, "doi_cap")
            )
            continue
        counts[doi] = count + 1
        selected.append(candidate)
    return selected, exclusions
