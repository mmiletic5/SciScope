"""Behavior tests for Phase C deterministic ranking and source diversity."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from sciscope.retrieval._quality import rank_evidence


def _hit(
    chunk_id: str,
    doi: str,
    locator: str,
    text: str,
) -> SimpleNamespace:
    return SimpleNamespace(
        chunk_id=chunk_id,
        doi=doi,
        source_locator=locator,
        text=text,
    )


def _ids(result) -> list[str]:
    return [candidate.hit.chunk_id for candidate in result.candidates]


def test_exact_duplicate_key_keeps_first_phase_b_candidate() -> None:
    """Only identical DOI, primary locator and exact text are duplicates."""
    candidates = [
        _hit("b" * 64, "10.1234/a", "loc-1", "same passage"),
        _hit("a" * 64, "10.1234/a", "loc-1", "same passage"),
        _hit("c" * 64, "10.1234/a", "loc-1", "different passage"),
        _hit("d" * 64, "10.1234/b", "loc-1", "same passage"),
    ]

    result = rank_evidence(candidates, max_per_doi=None)

    assert _ids(result) == ["b" * 64, "c" * 64, "d" * 64]
    assert [(item.chunk_id, item.reason) for item in result.exclusions] == [
        ("a" * 64, "duplicate_evidence")
    ]


def test_ranking_does_not_interpret_malformed_spans() -> None:
    """The approved duplicate key uses Phase B primary fields only."""
    candidate = _hit("a" * 64, "10.1234/a", "loc-1", "exact text")
    candidate.spans = {"malformed": object()}

    result = rank_evidence([candidate], max_per_doi=None)

    assert result.candidates[0].hit is candidate
    assert result.candidates[0].hit.spans == candidate.spans


def test_default_diversity_cap_is_two_and_runs_after_reranking() -> None:
    """Reranker order is honored before the configured DOI cap is applied."""
    candidates = [
        _hit("a" * 64, "10.1234/a", "loc-a", "first"),
        _hit("b" * 64, "10.1234/a", "loc-b", "second"),
        _hit("c" * 64, "10.1234/b", "loc-c", "third"),
        _hit("d" * 64, "10.1234/a", "loc-d", "fourth"),
    ]
    scores = {
        "a" * 64: 1.0,
        "b" * 64: 3.0,
        "c" * 64: 2.0,
        "d" * 64: 4.0,
    }

    result = rank_evidence(candidates, reranker_scores=scores)

    assert _ids(result) == ["d" * 64, "b" * 64, "c" * 64]
    assert [(item.chunk_id, item.reason) for item in result.exclusions] == [
        ("a" * 64, "doi_cap")
    ]


def test_none_disables_diversity_and_preserves_phase_b_order() -> None:
    """The explicit no-cap option preserves unique candidates in base order."""
    candidates = [
        _hit("b" * 64, "10.1234/a", "loc-b", "second"),
        _hit("a" * 64, "10.1234/a", "loc-a", "first"),
        _hit("c" * 64, "10.1234/a", "loc-c", "third"),
    ]

    first = rank_evidence(candidates, max_per_doi=None)
    second = rank_evidence(candidates, max_per_doi=None)

    assert _ids(first) == ["b" * 64, "a" * 64, "c" * 64]
    assert _ids(second) == _ids(first)
    assert first.exclusions == ()


@pytest.mark.parametrize("limit", [0, -1, 51, True])
def test_invalid_diversity_cap_is_rejected(limit: object) -> None:
    """Only None or integer limits from 1 through 50 are accepted."""
    with pytest.raises(ValueError, match="max_per_doi"):
        rank_evidence([], max_per_doi=limit)


def test_duplicate_chunk_ids_are_rejected() -> None:
    """Candidate identity remains unique independently of evidence dedupe."""
    hit = _hit("a" * 64, "10.1234/a", "loc-1", "passage")
    with pytest.raises(ValueError, match="duplicate chunk_id"):
        rank_evidence([hit, hit])


def test_reranker_ties_use_original_phase_b_rank() -> None:
    """Equal reranker scores preserve the original deterministic base order."""
    candidates = [
        _hit("b" * 64, "10.1234/a", "loc-b", "second"),
        _hit("a" * 64, "10.1234/a", "loc-a", "first"),
    ]
    scores = {candidate.chunk_id: 1.0 for candidate in candidates}

    result = rank_evidence(candidates, max_per_doi=None, reranker_scores=scores)

    assert _ids(result) == ["b" * 64, "a" * 64]
