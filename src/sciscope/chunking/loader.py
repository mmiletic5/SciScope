"""Strict F002 source loading interfaces for chunk generation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sciscope.chunking.core import SourceParagraph, SourceSection
from sciscope.jats.locator import MalformedLocatorError, locator_digest

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
    section_bytes = _read_bytes(sections_path)
    section_records = _read_jsonl(section_bytes, SECTION_FIELDS, "section")
    paragraph_bytes = _read_bytes(paragraphs_path)
    paragraph_records = _read_jsonl(
        paragraph_bytes, PARAGRAPH_FIELDS, "paragraph"
    )
    report_bytes = _read_bytes(parse_report_path)
    report = _read_report(report_bytes)
    papers: list[dict[str, Any]] = report["papers"]
    _check_consistency(section_records, paragraph_records, papers)

    sections = tuple(
        SourceSection(
            row["doi"],
            row["section_id"],
            tuple(row["section_path"]),
            row["normalized_type"],
        )
        for row in section_records
    )
    paragraphs = tuple(
        SourceParagraph(
            row["doi"],
            row["section_id"],
            row["paragraph_index"],
            row["text"],
            row["source_locator"],
        )
        for row in paragraph_records
    )
    return SourceBundle(
        sections,
        paragraphs,
        tuple(section_records),
        tuple(paragraph_records),
        tuple(papers),
        {paper["doi"]: paper["xml_sha256"] for paper in papers},
        {
            row["source_locator"]: tuple(row["omitted"])
            for row in paragraph_records
        },
        {
            "sections": hashlib.sha256(section_bytes).hexdigest(),
            "paragraphs": hashlib.sha256(paragraph_bytes).hexdigest(),
            "parse_report": hashlib.sha256(report_bytes).hexdigest(),
        },
    )


def _read_bytes(path: Path) -> bytes:
    """Read source bytes without allowing an OS path into an error."""
    try:
        return path.read_bytes()
    except OSError:
        raise SourceInputError("missing-file") from None


def _decode(data: bytes) -> str:
    """Decode strict UTF-8 without exposing invalid source bytes."""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise SourceInputError("invalid-utf8") from None


def _parse_json(text: str) -> Any:
    """Parse JSON without echoing content on failure."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise SourceInputError("invalid-json") from None


def _fields(
    row: Any, expected: tuple[str, ...], *, report: bool
) -> dict[str, Any]:
    """Validate an exact object field set before validating value types."""
    if not isinstance(row, dict) or any(not isinstance(k, str) for k in row):
        raise SourceInputError("wrong-type")
    missing = set(expected) - row.keys()
    extra = row.keys() - set(expected)
    if missing:
        raise SourceInputError("missing-field")
    if extra:
        raise SourceInputError(
            "report-extra-field" if report else "extra-field"
        )
    return row


def _string(value: Any) -> bool:
    """Return whether a value is a string."""
    return isinstance(value, str)


def _integer(value: Any) -> bool:
    """Return whether a value is a JSON integer rather than a boolean."""
    return type(value) is int


def _strings(value: Any) -> bool:
    """Return whether a value is a list of strings."""
    return isinstance(value, list) and all(map(_string, value))


def _str_int_map(value: Any) -> bool:
    """Return whether a value is an integer-valued string-key map."""
    return isinstance(value, dict) and all(
        _string(key) and _integer(item) for key, item in value.items()
    )


def _check_row_types(row: dict[str, Any], kind: str) -> None:
    """Check F002 primitive and collection types without coercion."""
    common = ("doi", "section_id", "source_locator")
    if not all(_string(row[field]) for field in common):
        raise SourceInputError("wrong-type")
    if kind == "section":
        string_fields = (
            "title",
            "xml_sha256",
            "original_heading",
            "normalized_type",
        )
        valid = (
            all(_string(row[field]) for field in string_fields)
            and (
                row["parent_section_id"] is None
                or _string(row["parent_section_id"])
            )
            and _strings(row["section_path"])
            and _integer(row["depth"])
            and _integer(row["paragraph_count"])
        )
    else:
        valid = (
            _integer(row["paragraph_index"])
            and _string(row["text"])
            and _strings(row["omitted"])
        )
    if not valid:
        raise SourceInputError("wrong-type")


def _read_jsonl(
    data: bytes, fields: tuple[str, ...], kind: str
) -> list[dict[str, Any]]:
    """Parse one strict JSONL file and validate each record."""
    decoded = _decode(data)
    if not decoded:
        return []
    lines = decoded.split("\n")
    if lines[-1] == "":
        lines.pop()
    rows = [_parse_json(line) for line in lines]
    checked = [_fields(row, fields, report=False) for row in rows]
    for row in checked:
        _check_row_types(row, kind)
    return checked


def _read_report(data: bytes) -> dict[str, Any]:
    """Parse the F002 report and validate its nested public schema."""
    report = _fields(
        _parse_json(_decode(data)), ("papers", "summary"), report=True
    )
    if not isinstance(report["papers"], list):
        raise SourceInputError("wrong-type")
    papers = [
        _fields(paper, PAPER_REPORT_FIELDS, report=True)
        for paper in report["papers"]
    ]
    for paper in papers:
        string_fields = ("doi", "xml_sha256")
        integer_fields = (
            "section_count",
            "paragraph_count",
            "abstract_paragraph_count",
        )
        valid = (
            all(_string(paper[field]) for field in string_fields)
            and all(_integer(paper[field]) for field in integer_fields)
            and _str_int_map(paper["normalized_type_histogram"])
            and _str_int_map(paper["unclassified_headings"])
            and _str_int_map(paper["skipped_element_kinds"])
            and _strings(paper["back_matter_containers"])
            and _strings(paper["warnings"])
            and _strings(paper["errors"])
            and isinstance(paper["type_conflicts"], list)
        )
        if not valid:
            raise SourceInputError("wrong-type")
        for conflict in paper["type_conflicts"]:
            item = _fields(
                conflict, ("section_id", "sec_type", "heading"), report=True
            )
            if not all(map(_string, item.values())):
                raise SourceInputError("wrong-type")
    summary = _fields(report["summary"], ("succeeded", "failed"), report=True)
    if not all(map(_integer, summary.values())):
        raise SourceInputError("wrong-type")
    return report


def _in_doi_order(rows: list[dict[str, Any]]) -> bool:
    """Check ascending DOI groups without changing F002 file order."""
    dois = [row["doi"] for row in rows]
    return dois == sorted(dois)


def _matches_digest(locator: str, digest: str) -> bool:
    """Check a public F002 locator digest without exposing the locator."""
    try:
        return locator_digest(locator) == digest
    except MalformedLocatorError:
        return False


def _check_consistency(
    sections: list[dict[str, Any]],
    paragraphs: list[dict[str, Any]],
    papers: list[dict[str, Any]],
) -> None:
    """Apply the approved first-failure consistency precedence."""
    if not all(_in_doi_order(rows) for rows in (sections, paragraphs, papers)):
        raise SourceConsistencyError("doi-order")
    failed = {paper["doi"] for paper in papers if paper["errors"]}
    if any(row["doi"] in failed for row in sections + paragraphs):
        raise SourceConsistencyError("failed-paper-records")
    section_dois = {row["doi"] for row in sections}
    successful = {paper["doi"] for paper in papers if not paper["errors"]}
    if section_dois != successful:
        raise SourceConsistencyError("doi-set")
    seen: set[tuple[str, str]] = set()
    for row in sections:
        key = (row["doi"], row["section_id"])
        if key in seen:
            raise SourceConsistencyError("duplicate-section")
        seen.add(key)
    section_names = {row["section_id"] for row in sections}
    for row in paragraphs:
        key = (row["doi"], row["section_id"])
        if key not in seen:
            code = (
                "cross-doi-section"
                if row["section_id"] in section_names
                else "unknown-section"
            )
            raise SourceConsistencyError(code)
    last: dict[tuple[str, str], int] = {}
    counts: dict[tuple[str, str], int] = {}
    for row in paragraphs:
        key = (row["doi"], row["section_id"])
        index = row["paragraph_index"]
        if key in last and index <= last[key]:
            raise SourceConsistencyError("paragraph-order")
        last[key] = index
        counts[key] = counts.get(key, 0) + 1
    for row in sections:
        key = (row["doi"], row["section_id"])
        if row["paragraph_count"] != counts.get(key, 0):
            raise SourceConsistencyError("section-paragraph-count")
    for row in sections:
        if not _matches_digest(row["source_locator"], row["xml_sha256"]):
            raise SourceConsistencyError("section-locator-digest")
    section_digest_by_doi = {row["doi"]: row["xml_sha256"] for row in sections}
    for row in paragraphs:
        expected = section_digest_by_doi[row["doi"]]
        if not _matches_digest(row["source_locator"], expected):
            raise SourceConsistencyError("paragraph-locator-digest")
    report_by_doi = {paper["doi"]: paper for paper in papers}
    for row in sections:
        if row["xml_sha256"] != report_by_doi[row["doi"]]["xml_sha256"]:
            raise SourceConsistencyError("xml-report-digest")
