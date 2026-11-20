"""Exact-tokenizer, whole-passage evidence context selection."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from sciscope.retrieval._quality import (
    EvidenceCandidate,
    RankedCandidate,
)


class TokenCounter(Protocol):
    """Count text using a stable tokenizer identity."""

    counter_id: str

    def count(self, text: str) -> int: ...


@dataclass(frozen=True, slots=True)
class ContextOmission:
    """A ranked passage omitted from the context with its measured cost."""

    chunk_id: str
    reason: str
    token_count: int


@dataclass(frozen=True, slots=True)
class ContextSelection[CandidateT: EvidenceCandidate]:
    """Selected whole passages and exact budget accounting."""

    selected: tuple[RankedCandidate[CandidateT], ...]
    omissions: tuple[ContextOmission, ...]
    budget_tokens: int
    total_tokens: int
    counter_id: str


def select_context[CandidateT: EvidenceCandidate](
    candidates: Sequence[RankedCandidate[CandidateT]],
    *,
    budget_tokens: int,
    token_counter: TokenCounter,
    expected_counter_id: str,
) -> ContextSelection[CandidateT]:
    """Select complete evidence items in ranked order under a token budget.

    Args:
        candidates: Final ranked and diversified evidence sequence.
        budget_tokens: Evidence-only token budget after caller-reserved prompt
            and system overhead.
        token_counter: Deterministic counter configured for the downstream
            generation model.
        expected_counter_id: Counter identity required by the caller.

    Returns:
        Selected candidates, omissions, and exact counter accounting.

    Raises:
        ValueError: If budget, tokenizer identity, candidate identity, or
            token counts are invalid.
    """
    if (
        isinstance(budget_tokens, bool)
        or not isinstance(budget_tokens, int)
        or budget_tokens < 0
    ):
        raise ValueError("budget_tokens must be a nonnegative integer")
    if (
        not isinstance(token_counter.counter_id, str)
        or not token_counter.counter_id
        or token_counter.counter_id != expected_counter_id
    ):
        raise ValueError("token counter identity does not match configuration")

    seen_ids: set[str] = set()
    selected: list[RankedCandidate[CandidateT]] = []
    omissions: list[ContextOmission] = []
    total_tokens = 0
    for candidate in candidates:
        hit = candidate.hit
        if not hit.chunk_id or not hit.text:
            raise ValueError("context candidates require ID and exact text")
        if hit.chunk_id in seen_ids:
            raise ValueError("duplicate chunk_id in context candidates")
        seen_ids.add(hit.chunk_id)
        count = token_counter.count(hit.text)
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            raise ValueError("token counter must return a positive integer")
        if count <= budget_tokens - total_tokens:
            selected.append(candidate)
            total_tokens += count
        else:
            omissions.append(
                ContextOmission(
                    hit.chunk_id,
                    "exceeds_remaining_budget",
                    count,
                )
            )
    return ContextSelection(
        selected=tuple(selected),
        omissions=tuple(omissions),
        budget_tokens=budget_tokens,
        total_tokens=total_tokens,
        counter_id=token_counter.counter_id,
    )
