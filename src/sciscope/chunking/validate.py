"""Independent offline validation of chunk structure and source coverage."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from sciscope.chunking.config import TEMPLATE_VERSION, build_embedding_text
from sciscope.chunking.core import ChunkSpan
from sciscope.chunking.counter import TokenCounter
from sciscope.chunking.loader import SourceBundle, SourceInputError
from sciscope.chunking.output import CHUNK_RECORD_FIELDS, chunk_id
from sciscope.chunking.report import (
    BACK_MATTER_CATEGORIES,
    BACK_MATTER_CATEGORY_NAMES,
    CHUNKING_VERSION,
    EXCLUDED_CATEGORIES,
    EXCLUDED_CATEGORY_NAMES,
)

type Record = Mapping[str, Any]
type FieldCheck = Callable[[object], bool]


@dataclass(frozen=True, slots=True)
class Finding:
    """One aggregated semantic code with a count and up to three safe IDs."""

    code: str
    count: int
    ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LoadedChunkRecords:
    """Full structurally checked records and the exact file-byte digest."""

    records: tuple[Mapping[str, object], ...]
    chunks_sha256: str


def load_chunk_records(path: Path) -> LoadedChunkRecords:
    """Read exact-schema UTF-8 JSONL with LF-only record splitting.

    Semantic defects remain available to the collect-all validators. Structural
    failures use sanitized SourceInputError codes and never echo file content.
    """
    raw = read_validation_bytes(path)
    text = _decode(raw)
    lines = text.split("\n") if text else []
    if lines and lines[-1] == "":
        lines.pop()
    records = tuple(_check_chunk(_parse_json(line)) for line in lines)
    return LoadedChunkRecords(records, hashlib.sha256(raw).hexdigest())


def read_validation_bytes(path: Path) -> bytes:
    """Read an artifact without disclosing paths in an OS failure."""
    raw: bytes | None = None
    try:
        raw = path.read_bytes()
    except OSError:
        pass
    if raw is None:
        raise SourceInputError("missing-file")
    return raw


def read_validation_json(path: Path) -> dict[str, Any]:
    """Read a strict UTF-8 JSON object with sanitized structural failures."""
    value = _parse_json(_decode(read_validation_bytes(path)))
    if not isinstance(value, dict):
        raise SourceInputError("wrong-type")
    return cast(dict[str, Any], value)


def _decode(raw: bytes) -> str:
    """Decode strict UTF-8 without exposing input bytes."""
    text: str | None = None
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        pass
    if text is None:
        raise SourceInputError("invalid-utf8")
    return text


def _reject_constant(value: str) -> object:
    """Reject nonstandard JSON numbers without echoing their spelling."""
    raise ValueError("invalid-json")


def _parse_json(text: str) -> object:
    """Parse one strict JSON value, retaining LF-only record semantics."""
    value: object = None
    valid = False
    try:
        value = json.loads(text, parse_constant=_reject_constant)
        valid = True
    except (ValueError, RecursionError):
        pass
    if not valid:
        raise SourceInputError("invalid-json")
    return value


def is_json_string(value: object) -> bool:
    """Check a UTF-8 encodable JSON string, excluding escaped surrogates."""
    return isinstance(value, str) and not any(
        0xD800 <= ord(char) <= 0xDFFF for char in value
    )


def is_json_integer(value: object) -> bool:
    """Check a JSON integer without accepting a boolean."""
    return type(value) is int


def is_json_number(value: object) -> bool:
    """Check a finite JSON number without accepting a boolean."""
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(cast(int | float, value))
    except OverflowError:
        return False


def is_string_array(value: object) -> bool:
    """Check an array of strict UTF-8 strings."""
    return isinstance(value, list) and all(map(is_json_string, value))


def is_count_mapping(value: object) -> bool:
    """Check string keys and integer counts without accepting booleans."""
    return isinstance(value, dict) and all(
        is_json_string(key) and is_json_integer(item)
        for key, item in value.items()
    )


def check_record(
    value: object, fields: Mapping[str, FieldCheck], *, exact: bool = True
) -> dict[str, Any]:
    """Check an object's required field set and primitive/nested types."""
    if not isinstance(value, dict):
        raise SourceInputError("wrong-type")
    if not set(fields) <= value.keys() or (exact and set(value) != set(fields)):
        raise SourceInputError("wrong-field-set")
    if any(not check(value[name]) for name, check in fields.items()):
        raise SourceInputError("wrong-type")
    return cast(dict[str, Any], value)


def _check_chunk(value: object) -> dict[str, Any]:
    """Check every public chunk and span primitive before semantic checks."""
    fields: dict[str, FieldCheck] = dict.fromkeys(
        CHUNK_RECORD_FIELDS, is_json_string
    )
    for name in ("ordinal", "content_tokens"):
        fields[name] = is_json_integer
    for name in ("section_path", "omitted"):
        fields[name] = is_string_array
    fields["hard_split"] = lambda item: type(item) is bool
    fields["spans"] = lambda item: isinstance(item, list)
    row = check_record(value, fields)
    span_fields = {
        "source_locator": is_json_string,
        "paragraph_index": is_json_integer,
        "start": is_json_integer,
        "end": is_json_integer,
    }
    for span in row["spans"]:
        check_record(span, span_fields)
    return row


class FindingCollector:
    """Aggregate distinct failing units with bounded, sanitized identifiers."""

    def __init__(self) -> None:
        """Start an empty collection of semantic failures."""
        self._items: dict[str, dict[object, str]] = {}

    def add(self, code: str, identifier: str, unit: object = None) -> None:
        """Count a unit once per code while preserving first-seen ID order."""
        safe = (
            identifier
            if (
                identifier in ("manifest", "vectors", "report")
                or re.fullmatch("[0-9a-f]{64}", identifier)
            )
            else "report"
        )
        self._items.setdefault(code, {}).setdefault(
            identifier if unit is None else unit, safe
        )

    def findings(self) -> list[Finding]:
        """Return sorted findings and at most three distinct IDs per code."""
        return [
            Finding(code, len(units), tuple(dict.fromkeys(units.values()))[:3])
            for code, units in sorted(self._items.items())
        ]


def validate_chunks(
    sources: SourceBundle,
    records: Sequence[Mapping[str, object]],
    counter: TokenCounter,
    *,
    operational_cap_tokens: int,
    chunk_report: Mapping[str, object],
) -> list[Finding]:
    """Collect independent source, identity, coverage, cap and report findings.

    Args:
        sources: F002 sources already checked by load_sources.
        records: Full structurally checked chunks in persisted file order.
        counter: Versioned final-input estimator.
        operational_cap_tokens: Configured cap, also bounded by 512.
        chunk_report: Committed exact-schema chunk report.

    Returns:
        Findings aggregated by code, with safe IDs in deterministic order.
    """
    rows = [_check_chunk(row) for row in records]
    validate_chunk_report_structure(chunk_report)
    findings = FindingCollector()
    sections = {
        (row["doi"], row["section_id"]): row for row in sources.section_records
    }
    section_order = {key: index for index, key in enumerate(sections)}
    paragraphs = {
        row["source_locator"]: row for row in sources.paragraph_records
    }
    by_section: dict[tuple[str, str], list[Record]] = defaultdict(list)
    coverage: dict[str, list[tuple[int, int, int, int, str]]] = defaultdict(
        list
    )
    last_section = -1
    for index, row in enumerate(rows):
        spans = [ChunkSpan(**span) for span in row["spans"]]
        expected_id = chunk_id(
            row["chunking_version"],
            row["doi"],
            row["section_id"],
            row["ordinal"],
            spans,
        )
        identifier = row["chunk_id"]
        if re.fullmatch("[0-9a-f]{64}", identifier) is None:
            identifier = expected_id
        checks = {
            "chunk-kind-mismatch": row["chunk_kind"] == "paragraph",
            "chunk-id-mismatch": row["chunk_id"] == expected_id,
            "chunk-hash-mismatch": row["text_sha256"]
            == hashlib.sha256(row["text"].encode("utf-8")).hexdigest(),
            "chunk-version-mismatch": (
                row["chunking_version"],
                row["token_counter_id"],
                row["template_version"],
            )
            == (CHUNKING_VERSION, counter.counter_id, TEMPLATE_VERSION),
            "chunk-token-mismatch": row["content_tokens"]
            == counter.count(row["text"]),
            "chunk-over-cap": counter.count(
                build_embedding_text(
                    tuple(row["section_path"]), row["text"], ""
                )
            )
            <= min(operational_cap_tokens, 512),
            "chunk-source-mismatch": bool(spans)
            and (row["source_locator"] == spans[0].source_locator),
        }
        key = (row["doi"], row["section_id"])
        by_section[key].append(row)
        section = sections.get(key)
        checks["chunk-unknown-section"] = section is not None
        if section is not None:
            checks["chunk-section-mismatch"] = all(
                row[name] == section[name]
                for name in ("xml_sha256", "normalized_type", "section_path")
            )
            order = section_order[key]
            checks["chunk-order"] = (
                row["ordinal"] == len(by_section[key]) and order >= last_section
            )
            last_section = order
            if not any(
                paragraph["text"].strip()
                for paragraph in sources.paragraph_records
                if (paragraph["doi"], paragraph["section_id"]) == key
            ):
                findings.add("chunk-in-empty-section", identifier, index)
        for code, passed in checks.items():
            if not passed:
                findings.add(code, identifier, index)
        _check_spans(
            row, spans, paragraphs, index, identifier, coverage, findings
        )
    _check_coverage(sources, by_section, coverage, findings)
    _check_report_counts(rows, sections, chunk_report, findings)
    return findings.findings()


def _check_spans(
    row: Record,
    spans: Sequence[ChunkSpan],
    paragraphs: Mapping[str, Record],
    index: int,
    identifier: str,
    coverage: dict[str, list[tuple[int, int, int, int, str]]],
    findings: FindingCollector,
) -> None:
    """Resolve owned spans and reconstruct text independently of the chunker."""
    pieces: list[str] = []
    omitted: set[str] = set()
    previous: ChunkSpan | None = None
    reconstructable = True
    for span in spans:
        paragraph = paragraphs.get(span.source_locator)
        if paragraph is None or (
            paragraph["doi"],
            paragraph["section_id"],
            paragraph["paragraph_index"],
        ) != (row["doi"], row["section_id"], span.paragraph_index):
            findings.add("section-isolation", identifier, index)
            reconstructable = False
            continue
        text: str = paragraph["text"]
        omitted.update(paragraph["omitted"])
        if not text.strip():
            findings.add("chunk-in-empty-section", identifier, index)
        if not 0 <= span.start < span.end <= len(text):
            findings.add("span-bounds", identifier, index)
            reconstructable = False
            continue
        coverage[span.source_locator].append(
            (
                row["ordinal"],
                index,
                span.start,
                span.end,
                identifier,
            )
        )
        if previous is not None:
            pieces.append(
                text[previous.end : span.start]
                if previous.source_locator == span.source_locator
                else "\n\n"
            )
        pieces.append(text[span.start : span.end])
        previous = span
    if row["omitted"] != sorted(omitted):
        findings.add("chunk-omitted-mismatch", identifier, index)
    if (reconstructable and row["text"] != "".join(pieces)) or (
        row["text"] != row["text"].strip()
    ):
        findings.add("chunk-text-mismatch", identifier, index)


def _check_coverage(
    sources: SourceBundle,
    by_section: Mapping[tuple[str, str], Sequence[Record]],
    coverage: Mapping[str, Sequence[tuple[int, int, int, int, str]]],
    findings: FindingCollector,
) -> None:
    """Check every source paragraph in ordinal order, including other types."""
    for paragraph in sources.paragraph_records:
        text = paragraph["text"]
        if not text.strip():
            continue
        locator = paragraph["source_locator"]
        spans = sorted(coverage.get(locator, ()), key=lambda span: span[:2])
        if not spans:
            owning = by_section.get(
                (paragraph["doi"], paragraph["section_id"]), ()
            )
            identifier = owning[0]["chunk_id"] if owning else "report"
            findings.add("coverage-missing", identifier, locator)
            continue
        end = 0
        for _, index, start, stop, identifier in spans:
            if start < end:
                findings.add("span-overlap", identifier, index)
            elif text[end:start].strip():
                findings.add("coverage-gap", identifier, locator)
            end = max(end, stop)
        if text[end:].strip():
            findings.add("coverage-gap", spans[-1][-1], locator)


def _check_report_counts(
    rows: Sequence[Record],
    sections: Mapping[tuple[str, str], Record],
    report: Mapping[str, Any],
    findings: FindingCollector,
) -> None:
    """Recompute counts using authoritative section types and file records."""
    types: Counter[str] = Counter()
    for row in rows:
        section = sections.get((row["doi"], row["section_id"]))
        types[
            section["normalized_type"] if section else row["normalized_type"]
        ] += 1
    summary = report["summary"]
    mismatch = (
        summary["chunk_count"] != len(rows)
        or summary["hard_split_chunks"]
        != sum(row["hard_split"] for row in rows)
        or summary["chunks_by_normalized_type"] != dict(types)
    )
    for paper in report["papers"]:
        selected = [row for row in rows if row["doi"] == paper["doi"]]
        mismatch |= paper["chunk_count"] != len(selected) or paper[
            "hard_split_chunks"
        ] != sum(row["hard_split"] for row in selected)
    if {row["doi"] for row in rows} - {p["doi"] for p in report["papers"]}:
        mismatch = True
    if mismatch:
        findings.add("chunk-report-mismatch", "report")


def validate_chunk_report_structure(value: object) -> None:
    """Check the exact public chunk report shape, including nested records."""
    report = check_record(
        value,
        {
            "chunking_version": is_json_string,
            "token_counter_id": is_json_string,
            "template_version": is_json_string,
            "config": lambda item: isinstance(item, dict),
            "input_sha256": lambda item: isinstance(item, dict),
            "policy": lambda item: isinstance(item, dict),
            "papers": lambda item: isinstance(item, list),
            "summary": lambda item: isinstance(item, dict),
        },
    )
    check_record(
        report["config"],
        dict.fromkeys(
            (
                "operational_cap_tokens",
                "content_target_min_tokens",
                "content_target_max_tokens",
                "soft_min_tokens",
                "prefix_reserve_tokens",
                "min_content_budget_tokens",
            ),
            is_json_integer,
        ),
    )
    check_record(
        report["input_sha256"],
        dict.fromkeys(
            ("sections", "paragraphs", "parse_report"), is_json_string
        ),
    )
    policy = check_record(
        report["policy"],
        {
            "skipped_element_kinds": lambda item: isinstance(item, dict),
            "back_matter_containers": lambda item: isinstance(item, dict),
        },
    )
    if set(policy["skipped_element_kinds"]) != set(EXCLUDED_CATEGORIES) or set(
        policy["back_matter_containers"]
    ) != set(BACK_MATTER_CATEGORIES):
        raise SourceInputError("wrong-field-set")
    for kind, entry in policy["skipped_element_kinds"].items():
        if not is_json_string(kind):
            raise SourceInputError("wrong-type")
        check_record(
            entry,
            {
                "category": is_json_string,
                "decision": is_json_string,
                "reason": is_json_string,
                "follow_up": lambda item: item is None or is_json_string(item),
            },
        )
    if not all(
        is_json_string(key) and is_json_string(item)
        for key, item in policy["back_matter_containers"].items()
    ):
        raise SourceInputError("wrong-type")
    fields: dict[str, FieldCheck] = dict.fromkeys(
        (
            "paper_count",
            "section_count",
            "sections_with_chunks",
            "chunk_count",
            "paragraph_count",
            "blank_paragraph_count",
            "paragraphs_with_omitted",
            "excluded_elements",
            "back_matter_excluded",
            "below_soft_min_chunks",
            "hard_split_chunks",
        ),
        is_json_integer,
    )
    fields["chunks_by_normalized_type"] = is_count_mapping
    for name in ("content_tokens", "final_input_estimated_tokens"):
        fields[name] = lambda item: isinstance(item, dict)
    summary = check_record(report["summary"], fields)
    for name in ("content_tokens", "final_input_estimated_tokens"):
        check_record(
            summary[name],
            dict.fromkeys(("min", "median", "p95", "max"), is_json_integer),
        )
    paper_fields: dict[str, FieldCheck] = dict.fromkeys(
        (
            "section_count",
            "sections_with_chunks",
            "chunk_count",
            "paragraph_count",
            "blank_paragraph_count",
            "paragraphs_with_omitted",
            "hard_split_chunks",
        ),
        is_json_integer,
    )
    paper_fields.update(
        {
            "doi": is_json_string,
            "xml_sha256": is_json_string,
            "excluded_elements": is_count_mapping,
            "unlisted_kinds": is_count_mapping,
            "back_matter_excluded": is_count_mapping,
        }
    )
    for paper in report["papers"]:
        checked = check_record(paper, paper_fields)
        if set(checked["excluded_elements"]) != set(
            EXCLUDED_CATEGORY_NAMES
        ) or set(checked["back_matter_excluded"]) != set(
            BACK_MATTER_CATEGORY_NAMES
        ):
            raise SourceInputError("wrong-field-set")
