"""Deterministic dense ordering and independently checked RRF behavior."""

from __future__ import annotations

from sciscope.retrieval._ranking import BranchHit, fuse_ranked_candidates


def _independent_oracle(
    dense_ids: list[str], lexical_ids: list[str]
) -> list[tuple[str, float, int]]:
    scores: dict[str, float] = {}
    best_rank: dict[str, int] = {}
    for branch in (dense_ids, lexical_ids):
        for rank, chunk_id in enumerate(branch, 1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1 / (60 + rank)
            best_rank[chunk_id] = min(best_rank.get(chunk_id, rank), rank)
    return sorted(
        ((key, score, best_rank[key]) for key, score in scores.items()),
        key=lambda row: (-row[1], row[2], row[0]),
    )


def test_rrf_matches_independent_oracle_and_stable_ties() -> None:
    """Fusion scores, component ranks, and tie ordering are deterministic."""
    dense = ["b", "a", "c"]
    lexical = ["a", "b", "d"]
    expected = _independent_oracle(dense, lexical)

    actual = fuse_ranked_candidates(
        [
            BranchHit(chunk_id, 1.0 - rank / 10)
            for rank, chunk_id in enumerate(dense)
        ],
        [
            BranchHit(chunk_id, 1.0 / rank)
            for rank, chunk_id in enumerate(lexical, 1)
        ],
        constant=60,
        top_k=4,
    )

    assert [item.chunk_id for item in actual] == [row[0] for row in expected]
    assert [item.score for item in actual] == [row[1] for row in expected]
    assert [item.best_rank for item in actual] == [row[2] for row in expected]


def test_rrf_deduplicates_same_chunk_and_keeps_distinct_chunks() -> None:
    """Candidates merge by chunk ID only; one paper may retain many chunks."""
    actual = fuse_ranked_candidates(
        [BranchHit("same-paper-a", 0.9), BranchHit("same-paper-b", 0.8)],
        [BranchHit("same-paper-a", 0.5)],
        constant=60,
        top_k=10,
    )
    assert len(actual) == 2
    assert {item.chunk_id for item in actual} == {
        "same-paper-a",
        "same-paper-b",
    }


def test_rrf_is_empty_when_both_branches_are_empty() -> None:
    """No branch candidates produce an empty successful ranking."""
    assert fuse_ranked_candidates([], [], constant=60, top_k=5) == ()


def test_rrf_ties_use_best_component_rank_then_chunk_id() -> None:
    """Equal fusion scores have a total order independent of set iteration."""
    actual = fuse_ranked_candidates(
        [BranchHit("b", 0.9), BranchHit("a", 0.8)],
        [BranchHit("a", 0.4), BranchHit("b", 0.4)],
        constant=60,
        top_k=2,
    )
    assert [item.chunk_id for item in actual] == ["a", "b"]


def test_rrf_rejects_duplicate_branch_ids() -> None:
    """Each branch list must have a unique chunk ID before fusion."""
    import pytest

    with pytest.raises(ValueError, match="duplicate chunk IDs"):
        fuse_ranked_candidates(
            [BranchHit("duplicate", 0.9), BranchHit("duplicate", 0.8)],
            [],
            constant=60,
            top_k=2,
        )
