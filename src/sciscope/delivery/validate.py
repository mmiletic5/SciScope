"""Offline, read-only delivery structure and per-file integrity validation."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import unicodedata
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Never, cast

from sciscope.chunking import output as chunk_output
from sciscope.chunking import validate as chunk_validate
from sciscope.chunking.core import ChunkSpan
from sciscope.chunking.counter import Utf8BytesDiv3Counter
from sciscope.chunking.loader import SourceInputError
from sciscope.chunking.validate import Finding
from sciscope.delivery import contract
from sciscope.embedding import validate as embedding_validate
from sciscope.jats import locator
from sciscope.plos_pilot import doi as doi_module

JSONL_ENTITIES = (
    ("papers.jsonl", "paper"),
    ("sections.jsonl", "section"),
    ("chunks.jsonl", "chunk"),
)
MANIFEST_ENTITIES = (
    ("embedding_manifest.json", "embedding_manifest"),
    ("delivery_manifest.json", "delivery_manifest"),
)
PAYLOAD_FILES = (
    "papers.jsonl",
    "sections.jsonl",
    "chunks.jsonl",
    "vectors.f32",
    "embedding_manifest.json",
)
PACKAGE_FILES = (*PAYLOAD_FILES, "delivery_manifest.json")
REPORT_FILES = (
    "parse_report.json",
    "chunk_report.json",
    "embedding_report.json",
)
SAFE_IDS = frozenset(
    (*PACKAGE_FILES, *REPORT_FILES, "manifest", "vectors", "report")
)
STRUCTURAL_CODES = frozenset(
    {
        "delivery-missing-file",
        "delivery-extra-file",
        "delivery-not-regular-file",
        "invalid-utf8",
        "invalid-json",
        "duplicate-json-key",
        "delivery-manifest-impure",
        "report-structure",
    }
    | {
        f"{entity}-{suffix}"
        for entity in (
            "paper",
            "section",
            "chunk",
            "embedding_manifest",
            "delivery_manifest",
            "embedding_set",
        )
        for suffix in (
            "missing-field",
            "extra-field",
            "bad-type",
            "bad-value",
            "bad-pattern",
        )
    }
)
SEMANTIC_CODES = frozenset(
    {
        "delivery-integrity-mismatch",
        "delivery-count-mismatch",
        "source-report-mismatch",
        "vectors-size",
        "partial-set",
        "delivery-duplicate-record",
        "delivery-orphan-record",
        "delivery-parent-invalid",
        "delivery-section-structure-mismatch",
        "delivery-xml-sha-mismatch",
        "delivery-locator-mismatch",
        "delivery-chunk-field-mismatch",
        "delivery-ordinal-gap",
        "delivery-text-hash-mismatch",
        "delivery-chunk-id-mismatch",
        "delivery-version-mismatch",
        "delivery-report-mismatch",
        "delivery-embedding-set-mismatch",
    }
)
FINDING_CODES = STRUCTURAL_CODES | SEMANTIC_CODES
_HASH_PATTERN = re.compile(r"[0-9a-f]{64}")
_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:")


@dataclass(frozen=True, slots=True)
class LoadedPackage:
    """Exact readable bytes and successfully decoded files for T005 reuse.

    JSONL records retain file order. Failed files are absent from records or
    manifests, never represented by fabricated empty successful parses.
    """

    raw_files: Mapping[str, bytes]
    records: Mapping[str, tuple[object, ...]]
    manifests: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class PackageReports:
    """Repository report paths, read as bytes only for descriptor comparison."""

    parse_report: Path
    chunk_report: Path
    embedding_report: Path


@dataclass(frozen=True, slots=True)
class StructureOutcome:
    """Collected file findings, structural precedence, and reusable parses."""

    findings: tuple[Finding, ...]
    structural: bool
    loaded: LoadedPackage


@dataclass(frozen=True, slots=True)
class ValidationOutcome:
    """Combined structural and semantic findings with reusable package data."""

    findings: tuple[Finding, ...]
    structural: bool
    loaded: LoadedPackage


def validate_package(
    package_dir: Path,
    reports: PackageReports,
    *,
    loaded: LoadedPackage | None = None,
    load_findings: tuple[Finding, ...] = (),
) -> ValidationOutcome:
    """Validate a received package offline without source XML or paragraphs.

    Args:
        package_dir: Directory containing the six delivery files.
        reports: Paths to the three matching repository reports.
        loaded: Optional prior loader result, preserved without reparsing.
        load_findings: Prior loader findings to retain in the combined result.

    Returns:
        All safely evaluable findings and their structural precedence.
    """
    structure = check_package_structure(
        package_dir, reports, loaded=loaded, load_findings=load_findings
    )
    findings = DeliveryFindingCollector()
    data = _semantic_data(structure)
    parsed_reports = _load_semantic_reports(reports, findings)
    _check_embedding_report(data, parsed_reports, findings)
    _check_record_semantics(data, findings)
    _check_versions(data, parsed_reports, findings)
    _check_report_semantics(data, parsed_reports, findings)
    _check_embedding_agreement(data, parsed_reports, findings)
    reused = _reuse_embedding_set(data, parsed_reports, findings)
    delivery_findings = findings.findings()
    return ValidationOutcome(
        _merge_validation_findings(
            structure.findings, delivery_findings, reused
        ),
        structure.structural
        or any(item.code in STRUCTURAL_CODES for item in delivery_findings),
        structure.loaded,
    )


class DeliveryFindingCollector:
    """Aggregate trusted codes by file/index with only fixed or digest IDs."""

    def __init__(self) -> None:
        """Start an empty delivery-specific collection."""
        self._items: dict[str, dict[tuple[str, int], str]] = {}

    def add(self, code: str, identifier: str, unit: tuple[str, int]) -> None:
        """Record one failing file/index, sanitizing code and identifier."""
        self._items.setdefault(_safe_code(code), {}).setdefault(
            unit, _safe_id(identifier)
        )

    def findings(self) -> list[Finding]:
        """Return sorted codes with unit counts and at most three safe IDs."""
        return [
            Finding(code, len(units), tuple(dict.fromkeys(units.values()))[:3])
            for code, units in sorted(self._items.items())
        ]


def _safe_code(code: str) -> str:
    """Replace an untrusted diagnostic code without retaining its value."""
    return code if code in FINDING_CODES else "invalid-json"


def _safe_id(identifier: str) -> str:
    """Keep only a fixed basename/token or a lowercase SHA-256 identifier."""
    return (
        identifier
        if identifier in SAFE_IDS or _HASH_PATTERN.fullmatch(identifier)
        else "report"
    )


class _DuplicateKey(ValueError):
    """Signal duplicate JSON keys without carrying their names or values."""


def _object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject duplicate object keys at every JSON nesting level."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey
        result[key] = value
    return result


def _reject_constant(value: str) -> Never:
    """Reject nonstandard nonfinite constants without retaining their text."""
    raise ValueError


def _finite_float(value: str) -> float:
    """Reject JSON numeric spellings that overflow to infinity."""
    number = float(value)
    if not math.isfinite(number):
        raise ValueError
    return number


def _decode_utf8(data: bytes) -> tuple[str | None, tuple[str, ...]]:
    """Decode a whole UTF-8 file, classifying an initial BOM explicitly."""
    if data.startswith(b"\xef\xbb\xbf"):
        return None, ("invalid-utf8",)
    try:
        return data.decode("utf-8"), ()
    except UnicodeError:
        return None, ("invalid-utf8",)


def _parse_json(text: str) -> tuple[object, tuple[str, ...]]:
    """Apply strict JSON hooks to already decoded text without raising."""
    try:
        value: object = json.loads(
            text,
            object_pairs_hook=_object_pairs,
            parse_constant=_reject_constant,
            parse_float=_finite_float,
        )
        return value, ()
    except _DuplicateKey:
        return None, ("duplicate-json-key",)
    except (ValueError, RecursionError):
        return None, ("invalid-json",)


def decode_json(data: bytes) -> tuple[object, tuple[str, ...]]:
    """Decode strict UTF-8/JSON; return None and safe codes on failure.

    A decoded JSON null also returns None, distinguished by its empty codes.
    Duplicate keys, BOM, nonfinite numbers and recursion failures are rejected.
    """
    text, codes = _decode_utf8(data)
    if text is None:
        return None, codes
    return _parse_json(text)


def _read_regular(
    path: Path,
    name: str,
    findings: DeliveryFindingCollector,
    *,
    nonregular_code: str,
) -> bytes | None:
    """Read a fixed regular file without following a final-component symlink."""
    try:
        mode = os.lstat(path).st_mode
    except (OSError, ValueError):
        findings.add("delivery-missing-file", name, (name, 0))
        return None
    if not stat.S_ISREG(mode):
        findings.add(nonregular_code, name, (name, 0))
        return None
    try:
        return path.read_bytes()
    except (OSError, ValueError):
        findings.add("delivery-missing-file", name, (name, 0))
        return None


def _extra_entries(
    package_dir: Path, findings: DeliveryFindingCollector
) -> None:
    """Count extra directory entries once each without opening or traversing."""
    try:
        with os.scandir(package_dir) as entries:
            for index, entry in enumerate(entries):
                if entry.name not in PACKAGE_FILES:
                    findings.add(
                        "delivery-extra-file", "report", ("report", index)
                    )
    except (OSError, ValueError):
        findings.add("delivery-missing-file", "report", ("report", 0))


def _load_jsonl(
    raw: bytes, name: str, findings: DeliveryFindingCollector
) -> tuple[object, ...] | None:
    """Decode UTF-8 once and collect all failing LF-delimited record units."""
    text, codes = _decode_utf8(raw)
    if text is None:
        for code in codes:
            findings.add(code, name, (name, 0))
        return None
    lines = text.split("\n") if text else []
    if lines and lines[-1] == "":
        lines.pop()
    records: list[object] = []
    failed = False
    for index, line in enumerate(lines):
        value, codes = _parse_json(line)
        for code in codes:
            findings.add(code, name, (name, index))
        failed = failed or bool(codes)
        records.append(value)
    return None if failed else tuple(records)


def load_package(package_dir: Path) -> tuple[LoadedPackage, list[Finding]]:
    """Collect inventory/decoding findings independently without writing.

    Only fixed regular files are read; symbolic links are never followed.
    This loader does not inspect reports or apply record-structure checkers.
    """
    findings = DeliveryFindingCollector()
    _extra_entries(package_dir, findings)
    raw_files: dict[str, bytes] = {}
    records: dict[str, tuple[object, ...]] = {}
    manifests: dict[str, object] = {}
    for name in PACKAGE_FILES:
        raw = _read_regular(
            package_dir / name,
            name,
            findings,
            nonregular_code="delivery-not-regular-file",
        )
        if raw is None:
            continue
        raw_files[name] = raw
        if name.endswith(".jsonl"):
            parsed = _load_jsonl(raw, name, findings)
            if parsed is not None:
                records[name] = parsed
        elif name.endswith(".json"):
            value, codes = decode_json(raw)
            for code in codes:
                findings.add(code, name, (name, 0))
            if not codes:
                manifests[name] = value
    return LoadedPackage(raw_files, records, manifests), findings.findings()


def _check_records(
    loaded: LoadedPackage, findings: DeliveryFindingCollector
) -> bool:
    """Call each public contract checker once per row; return S7 eligibility."""
    for name, entity in JSONL_ENTITIES:
        checker: Callable[[object], tuple[str, ...]] = getattr(
            contract, "check_" + entity
        )
        for index, record in enumerate(loaded.records.get(name, ())):
            for code in checker(record):
                findings.add(code, name, (name, index))
    delivery_valid = False
    for name, entity in MANIFEST_ENTITIES:
        if name not in loaded.manifests:
            continue
        checker = getattr(contract, "check_" + entity)
        codes = checker(loaded.manifests[name])
        for code in codes:
            findings.add(code, name, (name, 0))
        if entity == "delivery_manifest":
            delivery_valid = not codes
    return delivery_valid


def _read_reports(
    reports: PackageReports, findings: DeliveryFindingCollector
) -> dict[str, bytes]:
    """Always check report existence/type, retaining opaque bytes only."""
    result: dict[str, bytes] = {}
    for name in REPORT_FILES:
        raw = _read_regular(
            getattr(reports, name.removesuffix(".json")),
            name,
            findings,
            nonregular_code="delivery-missing-file",
        )
        if raw is not None:
            result[name] = raw
    return result


def _line_count(raw: bytes) -> int:
    """Count physical LF records, excluding exactly one final empty segment."""
    if not raw:
        return 0
    return raw.count(b"\n") + int(not raw.endswith(b"\n"))


def _check_file_facts(
    loaded: LoadedPackage,
    reports: Mapping[str, bytes],
    manifest: Mapping[str, object],
    findings: DeliveryFindingCollector,
) -> None:
    """Compare descriptors and per-file counts using a valid manifest only."""
    files = cast(Mapping[str, Mapping[str, object]], manifest["files"])
    embedding_set = cast(Mapping[str, object], manifest["embedding_set"])
    dimensions = cast(int, embedding_set["dimensions"])
    counts = cast(Mapping[str, int], manifest["counts"])
    for name in PAYLOAD_FILES:
        raw = loaded.raw_files.get(name)
        if raw is None:
            continue
        descriptor = files[name]
        record_count: int | None = 1
        if name.endswith(".jsonl"):
            record_count = _line_count(raw)
            if counts[name.removesuffix(".jsonl")] != record_count:
                findings.add("delivery-count-mismatch", name, (name, 0))
        elif name == "vectors.f32":
            width = dimensions * 4
            record_count = len(raw) // width if len(raw) % width == 0 else None
            if (
                len(raw) % 4
                or len(raw) != cast(int, descriptor["record_count"]) * width
            ):
                findings.add("vectors-size", "vectors", (name, 0))
        digest = hashlib.sha256(raw).hexdigest()
        if (
            descriptor["sha256"] != digest
            or descriptor["bytes"] != len(raw)
            or descriptor["record_count"] != record_count
        ):
            findings.add("delivery-integrity-mismatch", name, (name, 0))
        if name in ("chunks.jsonl", "vectors.f32"):
            field = (
                "chunks_sha256" if name == "chunks.jsonl" else "vectors_sha256"
            )
            if embedding_set[field] != digest:
                findings.add("delivery-integrity-mismatch", name, (name, 0))
    expected_reports = cast(
        Mapping[str, Mapping[str, object]], manifest["source_reports"]
    )
    for name, raw in reports.items():
        descriptor = expected_reports[name]
        if (
            descriptor["bytes"] != len(raw)
            or descriptor["sha256"] != hashlib.sha256(raw).hexdigest()
        ):
            findings.add("source-report-mismatch", name, (name, 0))


def _manifest_impure(manifest: Mapping[str, object]) -> bool:
    """Detect structural prose/path violations; this is not a secret scanner."""
    pending: list[tuple[object, str]] = [(manifest, "")]
    while pending:
        value, key = pending.pop()
        if isinstance(value, dict):
            pending.extend((item, field) for field, item in value.items())
        elif isinstance(value, list):
            pending.extend((item, key) for item in value)
        elif isinstance(value, str):
            if _HASH_PATTERN.fullmatch(value):
                continue
            if any(unicodedata.category(char) == "Cc" for char in value):
                return True
            if key in ("passage_prefix", "query_prefix"):
                if len(value) > 64:
                    return True
            elif (
                len(value) > 128
                or any(char.isspace() for char in value)
                or "\\" in value
                or value.startswith("/")
                or _DRIVE_PATTERN.match(value)
                or ".." in value
            ):
                return True
    return False


def _merge_findings(*groups: Sequence[Finding]) -> tuple[Finding, ...]:
    """Sum existing groups by safe code, preserving at most three unique IDs."""
    counts: dict[str, int] = {}
    identifiers: dict[str, list[str]] = {}
    for group in groups:
        for finding in group:
            code = _safe_code(finding.code)
            counts[code] = counts.get(code, 0) + finding.count
            selected = identifiers.setdefault(code, [])
            for identifier in finding.ids:
                safe = _safe_id(identifier)
                if safe not in selected and len(selected) < 3:
                    selected.append(safe)
    return tuple(
        Finding(code, count, tuple(identifiers[code]))
        for code, count in sorted(counts.items())
    )


def check_package_structure(
    package_dir: Path,
    reports: PackageReports,
    *,
    loaded: LoadedPackage | None = None,
    load_findings: tuple[Finding, ...] = (),
) -> StructureOutcome:
    """Collect T004 checks, reusing supplied loader results without rereading.

    If loaded is absent, load_package runs once. Supplied load_findings remain
    in the outcome. Reports are compared as bytes, never parsed. No F003 set
    validator or cross-record semantic checker is called here.
    """
    if loaded is None:
        loaded, loader_findings = load_package(package_dir)
        load_findings = _merge_findings(load_findings, loader_findings)
    findings = DeliveryFindingCollector()
    delivery_valid = _check_records(loaded, findings)
    report_bytes = _read_reports(reports, findings)
    delivery = loaded.manifests.get("delivery_manifest.json")
    if isinstance(delivery, dict):
        if _manifest_impure(delivery):
            findings.add(
                "delivery-manifest-impure", "manifest", ("manifest", 0)
            )
        if delivery_valid:
            _check_file_facts(loaded, report_bytes, delivery, findings)
    embedded = loaded.manifests.get("embedding_manifest.json")
    if isinstance(embedded, dict) and embedded.get("status") == "partial":
        findings.add("partial-set", "manifest", ("embedding_manifest.json", 0))
    merged = _merge_findings(load_findings, findings.findings())
    return StructureOutcome(
        merged, any(item.code in STRUCTURAL_CODES for item in merged), loaded
    )


type _Record = Mapping[str, Any]
type _Rows = tuple[_Record, ...]


@dataclass(frozen=True, slots=True)
class _SemanticData:
    """Only whole files that passed their T004 entity checks, plus bytes."""

    loaded: LoadedPackage
    records: Mapping[str, _Rows]
    manifests: Mapping[str, _Record]


def _semantic_data(structure: StructureOutcome) -> _SemanticData:
    """Retain original tuple/mapping identities while applying file gates."""
    records = {
        name: cast(_Rows, structure.loaded.records[name])
        for name, entity in JSONL_ENTITIES
        if name in structure.loaded.records
        and not any(
            item.code.startswith(entity + "-") for item in structure.findings
        )
    }
    manifests = {
        name: cast(_Record, structure.loaded.manifests[name])
        for name, entity in MANIFEST_ENTITIES
        if name in structure.loaded.manifests
        and not any(
            item.code.startswith(entity + "-") for item in structure.findings
        )
    }
    return _SemanticData(structure.loaded, records, manifests)


def _paper_report_shape(value: object, *, chunk: bool) -> bool:
    """Check required per-paper primitives, allowing extra diagnostics."""
    if not isinstance(value, dict) or not isinstance(value.get("papers"), list):
        return False
    counts = (
        ("section_count", "chunk_count", "sections_with_chunks")
        if chunk
        else ("section_count",)
    )
    for paper in value["papers"]:
        if not isinstance(paper, dict) or not all(
            chunk_validate.is_json_string(paper.get(field))
            for field in ("doi", "xml_sha256")
        ):
            return False
        if not all(
            chunk_validate.is_json_integer(paper.get(field)) for field in counts
        ):
            return False
    if chunk:
        return True
    summary = value.get("summary")
    return isinstance(summary, dict) and all(
        chunk_validate.is_json_integer(summary.get(field))
        for field in ("succeeded", "failed")
    )


def _load_semantic_reports(
    reports: PackageReports, findings: DeliveryFindingCollector
) -> dict[str, _Record]:
    """Read only regular reports and decode each exact byte string once."""
    parsed: dict[str, _Record] = {}
    for name, raw in _read_reports(reports, findings).items():
        value, codes = decode_json(raw)
        for code in codes:
            findings.add(code, name, (name, 0))
        if codes:
            continue
        valid = True
        if name == "parse_report.json":
            valid = _paper_report_shape(value, chunk=False)
        elif name == "chunk_report.json":
            valid = _paper_report_shape(value, chunk=True)
            try:
                chunk_validate.validate_chunk_report_structure(value)
            except (SourceInputError, ValueError, RecursionError):
                valid = False
        if valid:
            # The embedding validator checks its decoded value below, even
            # when it is not an object. A cast does not alter that value.
            parsed[name] = cast(_Record, value)
        else:
            findings.add("report-structure", name, (name, 0))
    return parsed


def _check_embedding_report(
    data: _SemanticData,
    reports: dict[str, _Record],
    findings: DeliveryFindingCollector,
) -> None:
    """Use the public F003 structure API once, before set delegation."""
    name = "embedding_report.json"
    manifest = data.manifests.get("embedding_manifest.json")
    if manifest is None or name not in reports:
        reports.pop(name, None)
        return
    try:
        embedding_validate.validate_embedding_structure(manifest, reports[name])
    except (SourceInputError, ValueError, RecursionError):
        findings.add("report-structure", "report", (name, 0))
        reports.pop(name)


def _record_key(record: _Record) -> tuple[str, str]:
    """Return the structurally checked DOI/section ownership pair."""
    return record["doi"], record["section_id"]


def _check_record_semantics(
    data: _SemanticData, findings: DeliveryFindingCollector
) -> None:
    """Check each available file without suppressing independent rules."""
    papers = data.records.get("papers.jsonl")
    sections = data.records.get("sections.jsonl")
    paper_index = (
        None if papers is None else {row["doi"]: row for row in papers}
    )
    section_index = (
        None
        if sections is None
        else {_record_key(row): row for row in sections}
    )
    for name, records in data.records.items():
        seen: set[object] = set()
        ordinals: set[tuple[str, str, int]] = set()
        running: Counter[tuple[str, str]] = Counter()
        for index, row in enumerate(records):
            identifier = row["chunk_id"] if name == "chunks.jsonl" else name
            unit = (name, index)
            key = (
                row["doi"]
                if name == "papers.jsonl"
                else (
                    _record_key(row)
                    if name == "sections.jsonl"
                    else row["chunk_id"]
                )
            )
            if key in seen:
                findings.add("delivery-duplicate-record", identifier, unit)
            seen.add(key)
            try:
                normalized = doi_module.normalize_doi(row["doi"]).doi
            except ValueError:
                normalized = None
            if normalized != row["doi"]:
                findings.add("delivery-orphan-record", identifier, unit)
            if name == "papers.jsonl":
                continue
            if not row["section_id"].startswith(row["doi"] + "#"):
                findings.add("delivery-orphan-record", identifier, unit)
            if paper_index is not None:
                paper = paper_index.get(row["doi"])
                if paper is None:
                    findings.add("delivery-orphan-record", identifier, unit)
                elif row["xml_sha256"] != paper["xml_sha256"]:
                    findings.add("delivery-xml-sha-mismatch", identifier, unit)
            _check_locator(
                row["source_locator"],
                row["xml_sha256"],
                identifier,
                unit,
                findings,
            )
            if name == "chunks.jsonl":
                section_key = _record_key(row)
                running[section_key] += 1
                ordinal_key = (*section_key, row["ordinal"])
                if ordinal_key in ordinals:
                    findings.add("delivery-duplicate-record", identifier, unit)
                ordinals.add(ordinal_key)
                if row["ordinal"] != running[section_key]:
                    findings.add("delivery-ordinal-gap", identifier, unit)
                _check_chunk_semantics(row, section_index, unit, findings)
    if sections is not None:
        _check_section_hierarchy(sections, findings)


def _check_locator(
    source: str,
    digest: str,
    identifier: str,
    unit: tuple[str, int],
    findings: DeliveryFindingCollector,
) -> None:
    """Check full grammar and call the digest helper for every locator."""
    try:
        matched = locator.locator_digest(source) == digest
    except ValueError:
        matched = False
    if contract.LOCATOR_PATTERN.fullmatch(source) is None or not matched:
        findings.add("delivery-locator-mismatch", identifier, unit)


def _check_section_hierarchy(
    sections: _Rows, findings: DeliveryFindingCollector
) -> None:
    """Enforce earlier same-paper parents, which excludes cycles iteratively."""
    earlier: dict[tuple[str, str], _Record] = {}
    for index, row in enumerate(sections):
        unit = ("sections.jsonl", index)
        label = (
            row["original_heading"]
            if row["original_heading"].strip()
            else "(untitled)"
        )
        parent_id = row["parent_section_id"]
        if parent_id is None:
            if row["depth"] != 1:
                findings.add("delivery-parent-invalid", "sections.jsonl", unit)
            mismatch = row["depth"] != 1 or row["section_path"] != [label]
        else:
            parent = earlier.get((row["doi"], parent_id))
            if parent is None or parent_id == row["section_id"]:
                findings.add("delivery-parent-invalid", "sections.jsonl", unit)
                mismatch = False
            else:
                mismatch = row["depth"] != parent["depth"] + 1 or row[
                    "section_path"
                ] != parent["section_path"] + [label]
        abstract = row["section_id"] == row["doi"] + "#abstract" or row[
            "section_id"
        ].startswith(row["doi"] + "#abstract.")
        if mismatch or abstract != (row["normalized_type"] == "abstract"):
            findings.add(
                "delivery-section-structure-mismatch", "sections.jsonl", unit
            )
        earlier.setdefault(_record_key(row), row)


def _check_chunk_semantics(
    row: _Record,
    sections: Mapping[tuple[str, str], _Record] | None,
    unit: tuple[str, int],
    findings: DeliveryFindingCollector,
) -> None:
    """Check section agreement, spans, exact text hash and existing ID API."""
    identifier = row["chunk_id"]
    if sections is not None:
        section = sections.get(_record_key(row))
        if section is None:
            findings.add("delivery-orphan-record", identifier, unit)
        elif any(
            row[field] != section[field]
            for field in ("normalized_type", "section_path")
        ):
            findings.add("delivery-chunk-field-mismatch", identifier, unit)
    spans = [ChunkSpan(**span) for span in row["spans"]]
    if not spans or any(span.end <= span.start for span in spans):
        findings.add("delivery-chunk-field-mismatch", identifier, unit)
    if spans and row["source_locator"] != spans[0].source_locator:
        findings.add("delivery-locator-mismatch", identifier, unit)
    for span in spans:
        _check_locator(
            span.source_locator, row["xml_sha256"], identifier, unit, findings
        )
    if (
        row["text_sha256"]
        != hashlib.sha256(row["text"].encode("utf-8")).hexdigest()
    ):
        findings.add("delivery-text-hash-mismatch", identifier, unit)
    try:
        expected = chunk_output.chunk_id(
            row["chunking_version"],
            row["doi"],
            row["section_id"],
            row["ordinal"],
            spans,
        )
    except ValueError:
        expected = None
    if expected != identifier:
        findings.add("delivery-chunk-id-mismatch", identifier, unit)


def _check_versions(
    data: _SemanticData,
    reports: Mapping[str, _Record],
    findings: DeliveryFindingCollector,
) -> None:
    """Compare real version identities only when every source is evaluable."""
    chunks = data.records.get("chunks.jsonl")
    delivery = data.manifests.get("delivery_manifest.json")
    embedded = data.manifests.get("embedding_manifest.json")
    report = reports.get("chunk_report.json")
    if chunks is None or delivery is None or embedded is None or report is None:
        return
    fields = ("chunking_version", "token_counter_id", "template_version")
    expected = delivery["processing_versions"]
    for index, row in enumerate(chunks):
        if any(row[field] != expected[field] for field in fields):
            findings.add(
                "delivery-version-mismatch",
                row["chunk_id"],
                ("chunks.jsonl", index),
            )
    if any(embedded[field] != expected[field] for field in fields):
        findings.add("delivery-version-mismatch", "manifest", ("manifest", 0))
    if any(report[field] != expected[field] for field in fields):
        findings.add(
            "delivery-version-mismatch",
            "chunk_report.json",
            ("chunk_report.json", 0),
        )


def _check_paper_report_semantics(
    name: str,
    report: _Record,
    data: _SemanticData,
    findings: DeliveryFindingCollector,
) -> None:
    """Compare each per-paper fact with its independently evaluable file."""
    papers = data.records.get("papers.jsonl")
    sections = data.records.get("sections.jsonl")
    chunks = data.records.get("chunks.jsonl")
    reported: list[_Record] = report["papers"]
    mismatch = False
    if papers is not None:
        paper_index = {row["doi"]: row for row in papers}
        mismatch = {row["doi"] for row in reported} != paper_index.keys()
        mismatch |= any(
            row["doi"] in paper_index
            and row["xml_sha256"] != paper_index[row["doi"]]["xml_sha256"]
            for row in reported
        )
    if sections is not None:
        section_counts = Counter(row["doi"] for row in sections)
        mismatch |= any(
            row["section_count"] != section_counts[row["doi"]]
            for row in reported
        )
    if name == "chunk_report.json" and chunks is not None:
        chunk_counts = Counter(row["doi"] for row in chunks)
        populated = Counter(
            doi for doi, _ in {_record_key(row) for row in chunks}
        )
        mismatch |= any(
            row["chunk_count"] != chunk_counts[row["doi"]]
            or row["sections_with_chunks"] != populated[row["doi"]]
            for row in reported
        )
    if mismatch:
        findings.add("delivery-report-mismatch", name, (name, 0))


def _compare_report_total(
    name: str,
    value: object,
    expected: Sequence[object],
    findings: DeliveryFindingCollector,
) -> None:
    """Count a report once when any independently known total disagrees."""
    if any(value != count for count in expected):
        findings.add("delivery-report-mismatch", name, (name, 0))


def _check_report_semantics(
    data: _SemanticData,
    reports: Mapping[str, _Record],
    findings: DeliveryFindingCollector,
) -> None:
    """Compare report sets, digests and counts using delivered facts only."""
    totals: dict[str, list[object]] = {
        "papers": [],
        "sections": [],
        "chunks": [],
    }
    for entity in totals:
        records = data.records.get(entity + ".jsonl")
        if records is not None:
            totals[entity].append(len(records))
    delivery = data.manifests.get("delivery_manifest.json")
    if delivery is not None:
        for entity in totals:
            totals[entity].append(delivery["counts"][entity])
    for name, report in reports.items():
        if name in ("parse_report.json", "chunk_report.json"):
            _check_paper_report_semantics(name, report, data, findings)
        if name == "parse_report.json":
            _compare_report_total(
                name, report["summary"]["succeeded"], totals["papers"], findings
            )
        else:
            summary = (
                report["summary"] if name == "chunk_report.json" else report
            )
            entities = (
                ("papers", "sections", "chunks")
                if name == "chunk_report.json"
                else ("papers", "chunks")
            )
            for entity in entities:
                field = {
                    "papers": "paper_count",
                    "sections": "section_count",
                    "chunks": "chunk_count",
                }[entity]
                _compare_report_total(
                    name, summary[field], totals[entity], findings
                )
            chunks = data.records.get("chunks.jsonl")
            if name == "chunk_report.json" and chunks is not None:
                _compare_report_total(
                    name,
                    summary["sections_with_chunks"],
                    [len({_record_key(row) for row in chunks})],
                    findings,
                )
    _check_report_vector_count(data, reports, findings)


def _check_report_vector_count(
    data: _SemanticData,
    reports: Mapping[str, _Record],
    findings: DeliveryFindingCollector,
) -> None:
    """Compare complete vector totals using only available validated facts."""
    name = "embedding_report.json"
    report = reports.get(name)
    embedded = data.manifests.get("embedding_manifest.json")
    if report is None or embedded is None:
        return
    expected: list[object] = [embedded["vector_count"]]
    vectors = data.loaded.raw_files.get("vectors.f32")
    width = 4 * embedded["returned_dimensions"]
    if vectors is not None:
        expected.append(
            len(vectors) // width if len(vectors) % width == 0 else None
        )
    delivery = data.manifests.get("delivery_manifest.json")
    if delivery is not None:
        expected.append(delivery["files"]["vectors.f32"]["record_count"])
    if embedded["status"] == "complete":
        chunks = data.records.get("chunks.jsonl")
        if chunks is not None:
            expected.append(len(chunks))
        if delivery is not None:
            expected.append(delivery["counts"]["chunks"])
    _compare_report_total(name, report["vector_count"], expected, findings)


def _check_embedding_agreement(
    data: _SemanticData,
    reports: Mapping[str, _Record],
    findings: DeliveryFindingCollector,
) -> None:
    """Compare every embedding-set field to F003 metadata or its fixed rule."""
    delivery = data.manifests.get("delivery_manifest.json")
    embedded = data.manifests.get("embedding_manifest.json")
    report = reports.get("embedding_report.json")
    if delivery is None or embedded is None or report is None:
        return
    embedding_set = delivery["embedding_set"]
    fields = (
        "provider",
        "model",
        "passage_prefix",
        "query_prefix",
        "chunks_sha256",
        "vectors_sha256",
    )
    mismatch = any(embedding_set[field] != embedded[field] for field in fields)
    mismatch |= any(
        embedding_set[field] != report[field]
        for field in ("provider", "model", "chunks_sha256")
    )
    mismatch |= any(
        artifact[field] != embedding_set["dimensions"]
        for artifact in (embedded, report)
        for field in ("requested_dimensions", "returned_dimensions")
    )
    mismatch |= embedding_set["dtype"] != embedded["vectors_dtype"]
    mismatch |= embedding_set["row_mapping"] != "embedding_manifest.entries"
    mismatch |= embedding_set["embedding_model_revision"] is not None
    mismatch |= any(
        embedding_set["normalization"][field]
        != embedded["normalization"][field]
        for field in ("declared", "observed_norm_min", "observed_norm_max")
    )
    mismatch |= embedding_set["normalization"]["tolerance"] != 0.01
    if mismatch:
        findings.add(
            "delivery-embedding-set-mismatch", "manifest", ("manifest", 0)
        )


def _reuse_embedding_set(
    data: _SemanticData,
    reports: Mapping[str, _Record],
    findings: DeliveryFindingCollector,
) -> Sequence[Finding]:
    """Delegate unchanged records/bytes and exact producer arguments to F003."""
    chunks = data.records.get("chunks.jsonl")
    manifest = data.manifests.get("embedding_manifest.json")
    report = reports.get("embedding_report.json")
    raw = data.loaded.raw_files
    if (
        chunks is None
        or manifest is None
        or report is None
        or "vectors.f32" not in raw
        or "chunks.jsonl" not in raw
    ):
        return ()
    try:
        return embedding_validate.validate_embedding_set(
            chunks,
            chunks_sha256=hashlib.sha256(raw["chunks.jsonl"]).hexdigest(),
            manifest=manifest,
            report=report,
            vectors=raw["vectors.f32"],
            counter=Utf8BytesDiv3Counter(),
            operational_cap_tokens=384,
            norm_tolerance=0.01,
            allow_partial=False,
        )
    except (SourceInputError, ValueError, ArithmeticError, RecursionError):
        findings.add("report-structure", "report", ("embedding_report.json", 0))
        return ()


def _merge_validation_findings(
    *groups: Sequence[Finding],
) -> tuple[Finding, ...]:
    """Merge trusted source aggregates by MAX, retaining encounter-order IDs."""
    counts: dict[str, int] = {}
    identifiers: dict[str, list[str]] = {}
    for group in groups:
        for finding in group:
            counts[finding.code] = max(
                counts.get(finding.code, 0), finding.count
            )
            selected = identifiers.setdefault(finding.code, [])
            for identifier in finding.ids:
                if identifier not in selected and len(selected) < 3:
                    selected.append(identifier)
    return tuple(
        Finding(code, counts[code], tuple(identifiers[code]))
        for code in sorted(counts)
    )
