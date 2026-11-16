"""Sentence and bounded hard-split interfaces."""

from __future__ import annotations

from sciscope.chunking.counter import TokenCounter


def sentence_spans(text: str) -> list[tuple[int, int]]:
    """Return ordered, trimmed sentence spans in source text."""
    raise NotImplementedError("T002")


def largest_end_within_limit(
    text: str, start: int, limit: int, counter: TokenCounter
) -> int:
    """Find the longest source prefix within a token limit."""
    raise NotImplementedError("T002")
