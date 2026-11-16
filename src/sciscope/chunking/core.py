"""Source-preserving section chunking interfaces."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sciscope.chunking.config import (
    UNTITLED_LABEL,
    ChunkConfig,
    ChunkingError,
    content_budget,
)
from sciscope.chunking.counter import TokenCounter
from sciscope.chunking.split import largest_end_within_limit, sentence_spans


@dataclass(frozen=True, slots=True)
class SourceSection:
    """One DOI-bearing F002 section for chunking."""

    doi: str
    section_id: str
    section_path: tuple[str, ...]
    normalized_type: str


@dataclass(frozen=True, slots=True)
class SourceParagraph:
    """One DOI-bearing F002 paragraph for chunking."""

    doi: str
    section_id: str
    paragraph_index: int
    text: str
    source_locator: str


@dataclass(frozen=True, slots=True)
class ChunkSpan:
    """A half-open Unicode code-point range in a source paragraph."""

    source_locator: str
    paragraph_index: int
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class Chunk:
    """Ordered source text and provenance for one section chunk."""

    doi: str
    section_id: str
    normalized_type: str
    heading_path: tuple[str, ...]
    ordinal: int
    text: str
    spans: tuple[ChunkSpan, ...]
    content_tokens: int
    hard_split: bool


@dataclass(frozen=True, slots=True)
class _Piece:
    """An ordered group of source spans before chunk numbering."""

    text: str
    spans: tuple[ChunkSpan, ...]
    hard_split: bool


def _source_piece(
    paragraph: SourceParagraph, start: int, end: int, *, hard: bool
) -> _Piece:
    """Make one trimmed source span without changing its text."""
    span = ChunkSpan(
        paragraph.source_locator, paragraph.paragraph_index, start, end
    )
    return _Piece(paragraph.text[start:end], (span,), hard)


def _join_pieces(left: _Piece, right: _Piece) -> _Piece:
    """Join pieces using their source relationship."""
    previous = left.spans[-1]
    following = right.spans[0]
    adjacent = (
        previous.source_locator == following.source_locator
        and previous.paragraph_index == following.paragraph_index
        and previous.end == following.start
    )
    separator = "" if adjacent else "\n\n"
    return _Piece(
        left.text + separator + right.text,
        left.spans + right.spans,
        left.hard_split or right.hard_split,
    )


def _hard_sentence_pieces(
    paragraph: SourceParagraph,
    start: int,
    end: int,
    limit: int,
    counter: TokenCounter,
) -> list[_Piece]:
    """Split one oversize sentence at bounded source offsets."""
    pieces: list[_Piece] = []
    while start < end:
        fitting_end = largest_end_within_limit(
            paragraph.text[:end], start, limit, counter
        )
        cut = fitting_end
        if fitting_end < end:
            for position in range(fitting_end - 1, start, -1):
                if (
                    paragraph.text[position].isspace()
                    and paragraph.text[start:position].strip()
                ):
                    cut = position
                    break
        while cut > start and paragraph.text[cut - 1].isspace():
            cut -= 1
        if cut <= start:
            raise ChunkingError("empty-hard-split-piece")
        pieces.append(_source_piece(paragraph, start, cut, hard=True))
        start = cut
        while start < end and paragraph.text[start].isspace():
            start += 1
    return pieces


def _paragraph_units(
    paragraph: SourceParagraph, limit: int, counter: TokenCounter
) -> list[_Piece]:
    """Create whole-paragraph or sentence-aligned units in source order."""
    text = paragraph.text
    start = len(text) - len(text.lstrip())
    end = len(text.rstrip())
    if start >= end:
        return []
    if counter.count(text[start:end]) <= limit:
        return [_source_piece(paragraph, start, end, hard=False)]

    units: list[_Piece] = []
    current_start: int | None = None
    current_end = 0
    for sentence_start, sentence_end in sentence_spans(text):
        if counter.count(text[sentence_start:sentence_end]) > limit:
            if current_start is not None:
                units.append(
                    _source_piece(
                        paragraph, current_start, current_end, hard=False
                    )
                )
                current_start = None
            units.extend(
                _hard_sentence_pieces(
                    paragraph, sentence_start, sentence_end, limit, counter
                )
            )
            continue
        if current_start is None:
            current_start = sentence_start
            current_end = sentence_end
        elif counter.count(text[current_start:sentence_end]) <= limit:
            current_end = sentence_end
        else:
            units.append(
                _source_piece(paragraph, current_start, current_end, hard=False)
            )
            current_start = sentence_start
            current_end = sentence_end
    if current_start is not None:
        units.append(
            _source_piece(paragraph, current_start, current_end, hard=False)
        )
    return units


def _merge_orphans(
    pieces: list[_Piece], budget: int, soft_min: int, counter: TokenCounter
) -> list[_Piece]:
    """Merge short chunks left to right until a pass changes nothing."""
    while len(pieces) > 1:
        changed = False
        index = 0
        while index < len(pieces) and len(pieces) > 1:
            if counter.count(pieces[index].text) >= soft_min:
                index += 1
                continue
            neighbor = index - 1 if index > 0 else 1
            if neighbor < index:
                merged = _join_pieces(pieces[neighbor], pieces[index])
                first = neighbor
            else:
                merged = _join_pieces(pieces[index], pieces[neighbor])
                first = index
            if counter.count(merged.text) <= budget:
                pieces[first : first + 2] = [merged]
                changed = True
                index = first + 1
            else:
                index += 1
        if not changed:
            break
    return pieces


def chunk_section(
    section: SourceSection,
    paragraphs: Sequence[SourceParagraph],
    config: ChunkConfig,
    counter: TokenCounter,
) -> list[Chunk]:
    """Chunk one section's own nonblank paragraphs."""
    for paragraph in paragraphs:
        if paragraph.section_id != section.section_id:
            raise ChunkingError("paragraph-section-mismatch")
        if paragraph.doi != section.doi:
            raise ChunkingError("paragraph-doi-mismatch")
    nonblank = [paragraph for paragraph in paragraphs if paragraph.text.strip()]
    if not nonblank:
        return []

    budget = content_budget(config, counter, section.section_path)
    effective_max = min(config.content_target_max_tokens, budget)
    units = [
        unit
        for paragraph in nonblank
        for unit in _paragraph_units(paragraph, effective_max, counter)
    ]
    packed: list[_Piece] = []
    current: _Piece | None = None
    for unit in units:
        if current is None:
            current = unit
            continue
        joined = _join_pieces(current, unit)
        if counter.count(joined.text) <= effective_max:
            current = joined
        else:
            packed.append(current)
            current = unit
    if current is not None:
        packed.append(current)
    packed = _merge_orphans(packed, budget, config.soft_min_tokens, counter)
    heading_path = tuple(
        heading
        for heading in section.section_path
        if heading.strip() and heading != UNTITLED_LABEL
    )
    return [
        Chunk(
            doi=section.doi,
            section_id=section.section_id,
            normalized_type=section.normalized_type,
            heading_path=heading_path,
            ordinal=index,
            text=piece.text,
            spans=piece.spans,
            content_tokens=counter.count(piece.text),
            hard_split=piece.hard_split,
        )
        for index, piece in enumerate(packed, start=1)
    ]


def chunk_sections(
    sections: Sequence[SourceSection],
    paragraphs: Sequence[SourceParagraph],
    config: ChunkConfig,
    counter: TokenCounter,
) -> list[Chunk]:
    """Validate and chunk sections in source order."""
    by_id: dict[str, SourceSection] = {}
    grouped: dict[str, list[SourceParagraph]] = {}
    last_index: dict[str, int] = {}
    for section in sections:
        if section.section_id in by_id:
            raise ChunkingError("duplicate-section-id")
        by_id[section.section_id] = section
        grouped[section.section_id] = []
    for paragraph in paragraphs:
        owner = by_id.get(paragraph.section_id)
        if owner is None:
            raise ChunkingError("unknown-section-id")
        if paragraph.doi != owner.doi:
            raise ChunkingError("paragraph-doi-mismatch")
        previous = last_index.get(paragraph.section_id)
        if previous is not None and paragraph.paragraph_index <= previous:
            raise ChunkingError("paragraph-index-not-increasing")
        last_index[paragraph.section_id] = paragraph.paragraph_index
        grouped[paragraph.section_id].append(paragraph)
    return [
        chunk
        for section in sections
        for chunk in chunk_section(
            section, grouped[section.section_id], config, counter
        )
    ]
