"""Behavior tests for deterministic evidence context budgeting."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from sciscope.retrieval._context import select_context
from sciscope.retrieval._quality import RankedCandidate


class FakeTokenCounter:
    """Count configured text tokens and record exact input strings."""

    counter_id = "fake-tokenizer-v1"

    def __init__(self, counts: dict[str, int]) -> None:
        """Store deterministic counts for the selected fixture strings."""
        self.counts = counts
        self.calls: list[str] = []

    def count(self, text: str) -> int:
        """Return the configured count and record exact source text."""
        self.calls.append(text)
        return self.counts[text]


def _candidate(chunk_id: str, text: str, base_rank: int):
    hit = SimpleNamespace(
        chunk_id=chunk_id,
        doi="10.1234/example",
        source_locator=f"loc-{base_rank}",
        text=text,
    )
    return RankedCandidate(hit, base_rank, None)


def test_context_selects_whole_candidates_and_continues_after_overflow() -> (
    None
):
    """Greedy selection preserves order and can fit later shorter evidence."""
    candidates = (
        _candidate("a" * 64, "first", 1),
        _candidate("b" * 64, "too long", 2),
        _candidate("c" * 64, "last", 3),
    )
    counter = FakeTokenCounter({"first": 3, "too long": 5, "last": 2})

    result = select_context(
        candidates,
        budget_tokens=5,
        token_counter=counter,
        expected_counter_id="fake-tokenizer-v1",
    )

    assert [item.hit.chunk_id for item in result.selected] == [
        "a" * 64,
        "c" * 64,
    ]
    assert result.total_tokens == 5
    assert result.budget_tokens == 5
    assert result.counter_id == "fake-tokenizer-v1"
    assert [
        (item.chunk_id, item.reason, item.token_count)
        for item in result.omissions
    ] == [("b" * 64, "exceeds_remaining_budget", 5)]
    assert [item.hit.text for item in result.selected] == ["first", "last"]


def test_exact_fit_and_zero_budget_are_deterministic() -> None:
    """Exact-fit evidence is included; no candidate fits a zero budget."""
    candidates = (_candidate("a" * 64, "text", 1),)
    counter = FakeTokenCounter({"text": 4})

    exact_fit = select_context(
        candidates,
        budget_tokens=4,
        token_counter=counter,
        expected_counter_id="fake-tokenizer-v1",
    )
    zero = select_context(
        candidates,
        budget_tokens=0,
        token_counter=counter,
        expected_counter_id="fake-tokenizer-v1",
    )

    assert len(exact_fit.selected) == 1
    assert exact_fit.total_tokens == 4
    assert zero.selected == ()
    assert zero.total_tokens == 0
    assert zero.omissions[0].reason == "exceeds_remaining_budget"


def test_tokenizer_identity_mismatch_fails_before_counting() -> None:
    """A generator/counter mismatch cannot claim an exact context budget."""
    counter = FakeTokenCounter({"text": 2})
    with pytest.raises(ValueError, match="counter identity"):
        select_context(
            (_candidate("a" * 64, "text", 1),),
            budget_tokens=10,
            token_counter=counter,
            expected_counter_id="openai-gpt-tokenizer-v1",
        )
    assert counter.calls == []


@pytest.mark.parametrize("budget", [-1, True, 1.0])
def test_invalid_token_budget_is_rejected(budget: object) -> None:
    """Budgets are explicit nonnegative integers and booleans are invalid."""
    with pytest.raises(ValueError, match="budget_tokens"):
        select_context(
            (),
            budget_tokens=budget,
            token_counter=FakeTokenCounter({}),
            expected_counter_id="fake-tokenizer-v1",
        )


@pytest.mark.parametrize("count", [0, -1, True, 1.5])
def test_invalid_token_counter_result_is_rejected(count: object) -> None:
    """The counter must return a positive integer for nonempty text."""
    with pytest.raises(ValueError, match="positive integer"):
        select_context(
            (_candidate("a" * 64, "text", 1),),
            budget_tokens=10,
            token_counter=FakeTokenCounter({"text": count}),
            expected_counter_id="fake-tokenizer-v1",
        )
