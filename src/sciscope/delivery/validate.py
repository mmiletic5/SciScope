"""Offline, read-only delivery structure and per-file integrity validation."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Never, cast

from sciscope.chunking.validate import Finding
from sciscope.delivery import contract

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
