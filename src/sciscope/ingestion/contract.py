"""Typed importer request and result contract."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal, Protocol


class ImportMode(StrEnum):
    """Permitted complete-snapshot operations."""

    INITIALIZE = "initialize"
    REPLACE = "replace"


@dataclass(frozen=True, slots=True)
class ImportRequest:
    """Paths and explicit operation intent for one snapshot import."""

    package_dir: Path
    parse_report: Path
    chunk_report: Path
    embedding_report: Path
    mode: ImportMode
    expected_active_digest: str | None = None


@dataclass(frozen=True, slots=True)
class ImportResult:
    """Committed snapshot identity and exact imported record counts."""

    import_id: int
    delivery_digest: str
    outcome: Literal["imported", "replaced", "unchanged"]
    previous_delivery_digest: str | None
    papers: int
    sections: int
    chunks: int
    vectors: int


class SnapshotImporter(Protocol):
    """Stable synchronous import API."""

    def import_snapshot(self, request: ImportRequest) -> ImportResult:
        """Validate and atomically import one complete snapshot."""
