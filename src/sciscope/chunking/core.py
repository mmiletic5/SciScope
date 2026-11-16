"""Source-preserving section chunking interfaces."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sciscope.chunking.config import ChunkConfig
from sciscope.chunking.counter import TokenCounter


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


def chunk_section(
    section: SourceSection,
    paragraphs: Sequence[SourceParagraph],
    config: ChunkConfig,
    counter: TokenCounter,
) -> list[Chunk]:
    """Chunk one section's own nonblank paragraphs."""
    raise NotImplementedError("T002")


def chunk_sections(
    sections: Sequence[SourceSection],
    paragraphs: Sequence[SourceParagraph],
    config: ChunkConfig,
    counter: TokenCounter,
) -> list[Chunk]:
    """Validate and chunk sections in source order."""
    raise NotImplementedError("T002")
