"""T003 package interfaces; Phase 1 stubs, deliberately unimplemented."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sciscope.chunking.validate import Finding

DEFAULT_NORM_TOLERANCE = 0.01


@dataclass(frozen=True, slots=True)
class DeliveryInputs:
    """Producer paths; cache_dir is guarded but never opened."""

    metadata: Path = Path("data/pilot/metadata.jsonl")
    acquisition_manifest: Path = Path("data/pilot/manifest.jsonl")
    sections: Path = Path("data/processed/pilot/sections.jsonl")
    paragraphs: Path = Path("data/processed/pilot/paragraphs.jsonl")
    parse_report: Path = Path("data/pilot/parse_report.json")
    chunks: Path = Path("data/processed/pilot/chunks.jsonl")
    chunk_report: Path = Path("data/pilot/chunk_report.json")
    vectors: Path = Path("data/embeddings/pilot/vectors.f32")
    embedding_manifest: Path = Path("data/embeddings/pilot/manifest.json")
    embedding_report: Path = Path("data/pilot/embedding_report.json")
    output_dir: Path = Path("data/delivery/pilot")
    committed_manifest: Path = Path("data/pilot/delivery_manifest.json")
    cache_dir: Path = Path("data/embeddings/pilot/cache")
    parser_source: Path = Path("src/sciscope/jats/parser.py")
    taxonomy_source: Path = Path("src/sciscope/jats/classify.py")


@dataclass(frozen=True, slots=True)
class DeliverySummary:
    """Numeric success counts, with no paths or source values."""

    papers: int
    sections: int
    chunks: int
    vectors: int
    files: int


class DeliveryError(ValueError):
    """Sanitized delivery failure; code and exit_code are public attributes."""

    code: str
    exit_code: int

    def __init__(self, code: str) -> None:
        """Initialize a sanitized code and its exit status."""
        raise NotImplementedError


def build_delivery_manifest(
    *,
    counts: Mapping[str, int],
    files: Mapping[str, Mapping[str, object]],
    source_reports: Mapping[str, Mapping[str, object]],
    parser_sha256: str,
    taxonomy_sha256: str,
    chunking_version: str,
    token_counter_id: str,
    template_version: str,
    embedding_manifest: Mapping[str, Any],
) -> dict[str, object]:
    """Build ordered metadata purely from validated facts, without I/O."""
    raise NotImplementedError


def render_manifest(manifest: Mapping[str, object]) -> bytes:
    """Render ordered two-space JSON as strict UTF-8 with a final LF."""
    raise NotImplementedError


def render_papers(papers: Sequence[Mapping[str, object]]) -> bytes:
    """Render DOI-sorted PAPER_FIELDS-ordered strict UTF-8 JSONL."""
    raise NotImplementedError


def validate_staged_inputs(
    inputs: DeliveryInputs, staged_dir: Path
) -> tuple[Finding, ...]:
    """Run existing complete-set validators on staged payloads and reports.

    Structural input errors retain SourceInputError; semantic findings are
    returned. Original paragraphs and parse report remain upstream inputs.
    """
    raise NotImplementedError


def run_delivery(inputs: DeliveryInputs) -> DeliverySummary:
    """Stage, validate, assemble and publish both artifacts with rollback."""
    raise NotImplementedError
