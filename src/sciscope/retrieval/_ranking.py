"""Deterministic ranking primitives for exact dense and hybrid retrieval."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BranchHit:
    """One unique chunk and its score in a deterministically ranked branch."""

    chunk_id: str
    score: float


@dataclass(frozen=True, slots=True)
class FusedHit:
    """One hybrid candidate with component rank/score provenance."""

    chunk_id: str
    dense_score: float | None
    dense_rank: int | None
    lexical_score: float | None
    lexical_rank: int | None
    score: float
    best_rank: int


def fuse_ranked_candidates(
    dense: Sequence[BranchHit],
    lexical: Sequence[BranchHit],
    *,
    constant: int,
    top_k: int,
) -> tuple[FusedHit, ...]:
    """Fuse ordered, unique branch hits with deterministic RRF.

    Args:
        dense: Dense candidates ordered by cosine distance then chunk ID.
        lexical: Lexical candidates ordered by score descending then chunk ID.
        constant: Positive RRF rank constant.
        top_k: Maximum number of candidates returned.

    Returns:
        The first ``top_k`` candidates in total deterministic order.
    """
    if constant < 1 or top_k < 1:
        raise ValueError("constant and top_k must be positive")
    dense_map = _branch_map(dense)
    lexical_map = _branch_map(lexical)
    candidates: list[FusedHit] = []
    for chunk_id in dense_map.keys() | lexical_map.keys():
        dense_value = dense_map.get(chunk_id)
        lexical_value = lexical_map.get(chunk_id)
        dense_rank = dense_value[1] if dense_value else None
        lexical_rank = lexical_value[1] if lexical_value else None
        ranks = [
            rank for rank in (dense_rank, lexical_rank) if rank is not None
        ]
        assert ranks
        fused = sum(1 / (constant + rank) for rank in ranks)
        candidates.append(
            FusedHit(
                chunk_id=chunk_id,
                dense_score=dense_value[0] if dense_value else None,
                dense_rank=dense_rank,
                lexical_score=lexical_value[0] if lexical_value else None,
                lexical_rank=lexical_rank,
                score=fused,
                best_rank=min(ranks),
            )
        )
    candidates.sort(
        key=lambda item: (-item.score, item.best_rank, item.chunk_id)
    )
    return tuple(candidates[:top_k])


def _branch_map(hits: Sequence[BranchHit]) -> dict[str, tuple[float, int]]:
    result: dict[str, tuple[float, int]] = {}
    for rank, hit in enumerate(hits, start=1):
        if hit.chunk_id in result:
            raise ValueError(
                "A ranked branch cannot contain duplicate chunk IDs"
            )
        result[hit.chunk_id] = (hit.score, rank)
    return result
