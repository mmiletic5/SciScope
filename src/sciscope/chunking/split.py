"""Sentence and bounded hard-split interfaces."""

from __future__ import annotations

from sciscope.chunking.config import ChunkingError
from sciscope.chunking.counter import TokenCounter

_ABBREVIATIONS = frozenset(
    {
        "fig.",
        "figs.",
        "tab.",
        "eq.",
        "ref.",
        "e.g.",
        "i.e.",
        "vs.",
        "cf.",
        "ca.",
        "approx.",
        "no.",
        "sp.",
        "spp.",
        "var.",
        "subsp.",
        "dr.",
    }
)
_OPENING = "([{\"'“‘"
_CLOSING = ")]}\"'”’"


def _protected_period(text: str, period_index: int) -> bool:
    """Identify an approved abbreviation or single-letter initial."""
    start = period_index
    while start > 0 and not text[start - 1].isspace():
        start -= 1
    token = text[start : period_index + 1].lstrip(_OPENING)
    if token.lower() in _ABBREVIATIONS:
        return True
    if token.lower() == "al.":
        preceding = text[:start].split()
        if preceding and preceding[-1].lower() == "et":
            return True
    return len(token) == 2 and token[0].isupper()


def _trimmed_span(text: str, start: int, end: int) -> tuple[int, int] | None:
    """Trim only outer whitespace from a source range."""
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return (start, end) if start < end else None


def sentence_spans(text: str) -> list[tuple[int, int]]:
    """Return ordered, trimmed sentence spans in source text."""
    spans: list[tuple[int, int]] = []
    sentence_start = 0
    index = 0
    while index < len(text):
        mark = text[index]
        if mark not in ".?!":
            index += 1
            continue
        if mark == "." and _protected_period(text, index):
            index += 1
            continue
        punctuation_end = index + 1
        while punctuation_end < len(text) and text[punctuation_end] in _CLOSING:
            punctuation_end += 1
        next_start = punctuation_end
        while next_start < len(text) and text[next_start].isspace():
            next_start += 1
        if (
            next_start > punctuation_end
            and next_start < len(text)
            and (
                text[next_start].isupper()
                or text[next_start].isdigit()
                or text[next_start] in _OPENING
            )
        ):
            span = _trimmed_span(text, sentence_start, punctuation_end)
            if span is not None:
                spans.append(span)
            sentence_start = next_start
            index = next_start
        else:
            index = punctuation_end
    span = _trimmed_span(text, sentence_start, len(text))
    if span is not None:
        spans.append(span)
    return spans


def largest_end_within_limit(
    text: str, start: int, limit: int, counter: TokenCounter
) -> int:
    """Find the longest source prefix within a token limit."""
    if start < 0 or start >= len(text) or limit < 1:
        raise ChunkingError("invalid-hard-split-range")
    if counter.count(text[start : start + 1]) > limit:
        raise ChunkingError("single-code-point-exceeds-budget")
    low = start + 1
    high = len(text)
    while low < high:
        middle = (low + high + 1) // 2
        if counter.count(text[start:middle]) <= limit:
            low = middle
        else:
            high = middle - 1
    return low
