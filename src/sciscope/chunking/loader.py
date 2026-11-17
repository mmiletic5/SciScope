"""Strict F002 source loading interfaces for chunk generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sciscope.chunking.core import SourceParagraph, SourceSection

SECTION_FIELDS = (
    "doi",
    "title",
    "xml_sha256",
    "section_id",
    "parent_section_id",
    "section_path",
    "original_heading",
    "normalized_type",
    "source_locator",
    "depth",
    "paragraph_count",
)
PARAGRAPH_FIELDS = (
    "doi",
    "section_id",
    "paragraph_index",
    "text",
    "omitted",
    "source_locator",
)
PAPER_REPORT_FIELDS = (
    "doi",
    "xml_sha256",
    "section_count",
    "paragraph_count",
    "abstract_paragraph_count",
    "normalized_type_histogram",
    "unclassified_headings",
    "type_conflicts",
    "skipped_element_kinds",
    "back_matter_containers",
    "warnings",
    "errors",
)


class SourceInputError(ValueError):
    """Malformed or unreadable source input, with a sanitized code."""

    def __init__(self, code: str) -> None:
        """Store a stable error code without source content or paths."""
        self.code = code
        super().__init__(code)


class SourceConsistencyError(ValueError):
    """Well-formed F002 inputs disagree, with a sanitized code."""

    def __init__(self, code: str) -> None:
        """Store a stable error code without source content or paths."""
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class SourceBundle:
    """Ordered sources, provenance and reports after validation."""

    sections: tuple[SourceSection, ...]
    paragraphs: tuple[SourceParagraph, ...]
    section_records: tuple[dict[str, Any], ...]
    paragraph_records: tuple[dict[str, Any], ...]
    parse_report_papers: tuple[dict[str, Any], ...]
    xml_sha256_by_doi: dict[str, str]
    omitted_by_locator: dict[str, tuple[str, ...]]
    input_sha256: dict[str, str]


def load_sources(
    sections_path: Path,
    paragraphs_path: Path,
    parse_report_path: Path,
) -> SourceBundle:
    """Read and validate exact F002 records in their original file order."""
    raise NotImplementedError("T004")
