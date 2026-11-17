"""T004 file-validation interfaces; behavior intentionally awaits Phase 2."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from sciscope.chunking.validate import Finding


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
        raise NotImplementedError

    def add(self, code: str, identifier: str, unit: tuple[str, int]) -> None:
        """Record one failing file/index, sanitizing code and identifier."""
        raise NotImplementedError

    def findings(self) -> list[Finding]:
        """Return sorted codes with unit counts and at most three safe IDs."""
        raise NotImplementedError


def decode_json(data: bytes) -> tuple[object, tuple[str, ...]]:
    """Decode strict UTF-8/JSON; return None and safe codes on failure.

    A decoded JSON null also returns None, distinguished by its empty codes.
    Duplicate keys, BOM, nonfinite numbers and recursion failures are rejected.
    """
    raise NotImplementedError


def load_package(package_dir: Path) -> tuple[LoadedPackage, list[Finding]]:
    """Collect inventory/decoding findings independently without writing.

    Only fixed regular files are read; symbolic links are never followed.
    This loader does not inspect reports or apply record-structure checkers.
    """
    raise NotImplementedError


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
    raise NotImplementedError
