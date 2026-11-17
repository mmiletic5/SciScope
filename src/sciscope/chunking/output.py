"""Deterministic chunk serialization and atomic output interfaces."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from sciscope.chunking.config import ChunkConfig
from sciscope.chunking.core import Chunk, ChunkSpan
from sciscope.chunking.loader import SourceBundle

CHUNK_RECORD_FIELDS = (
    "chunk_id",
    "doi",
    "xml_sha256",
    "section_id",
    "ordinal",
    "chunk_kind",
    "normalized_type",
    "section_path",
    "text",
    "text_sha256",
    "spans",
    "source_locator",
    "content_tokens",
    "hard_split",
    "omitted",
    "chunking_version",
    "token_counter_id",
    "template_version",
)


def chunk_id(
    chunking_version: str,
    doi: str,
    section_id: str,
    ordinal: int,
    spans: Sequence[ChunkSpan],
) -> str:
    """Hash canonical length-delimited identity fields and ordered spans."""
    raise NotImplementedError("T004")


def chunk_record(
    chunk: Chunk, bundle: SourceBundle, token_counter_id: str
) -> dict[str, Any]:
    """Serialize one paragraph chunk in the public field order."""
    raise NotImplementedError("T004")


def chunk_report(
    chunks: Sequence[Chunk],
    bundle: SourceBundle,
    config: ChunkConfig,
    token_counter_id: str,
) -> dict[str, Any]:
    """Summarize source counts and token statistics without source prose."""
    raise NotImplementedError("T004")


def write_outputs(outputs: Mapping[Path, bytes]) -> None:
    """Stage all output bytes and publish them without partial replacement."""
    raise NotImplementedError("T004")


def write_chunk_files(
    chunks: Sequence[Chunk],
    bundle: SourceBundle,
    config: ChunkConfig,
    token_counter_id: str,
    chunks_path: Path,
    report_path: Path,
) -> None:
    """Write deterministic UTF-8 JSONL and JSON artifacts atomically."""
    raise NotImplementedError("T004")
