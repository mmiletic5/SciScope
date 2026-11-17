"""Deterministic chunk serialization and atomic output interfaces."""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from sciscope.chunking.config import (
    TEMPLATE_VERSION,
    ChunkConfig,
    build_embedding_text,
)
from sciscope.chunking.core import Chunk, ChunkSpan
from sciscope.chunking.counter import Utf8BytesDiv3Counter
from sciscope.chunking.loader import SourceBundle
from sciscope.chunking.report import (
    BACK_MATTER_CATEGORIES,
    CHUNK_KIND_PARAGRAPH,
    CHUNKING_VERSION,
    EXCLUDED_CATEGORIES,
    count_excluded,
    count_paragraphs_with_omitted,
)

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
    fields = [chunking_version, doi, section_id, str(ordinal)]
    for span in spans:
        fields.extend((span.source_locator, str(span.start), str(span.end)))
    canonical = bytearray(len(fields).to_bytes(8, "big"))
    for field in fields:
        encoded = field.encode("utf-8")
        canonical.extend(len(encoded).to_bytes(8, "big"))
        canonical.extend(encoded)
    return hashlib.sha256(canonical).hexdigest()


def chunk_record(
    chunk: Chunk, bundle: SourceBundle, token_counter_id: str
) -> dict[str, Any]:
    """Serialize one paragraph chunk in the public field order."""
    sections = {
        (row["doi"], row["section_id"]): row for row in bundle.section_records
    }
    section = sections[(chunk.doi, chunk.section_id)]
    omitted = sorted(
        {
            kind
            for span in chunk.spans
            for kind in bundle.omitted_by_locator[span.source_locator]
        }
    )
    spans = [
        {
            "source_locator": span.source_locator,
            "paragraph_index": span.paragraph_index,
            "start": span.start,
            "end": span.end,
        }
        for span in chunk.spans
    ]
    return {
        "chunk_id": chunk_id(
            CHUNKING_VERSION,
            chunk.doi,
            chunk.section_id,
            chunk.ordinal,
            chunk.spans,
        ),
        "doi": chunk.doi,
        "xml_sha256": bundle.xml_sha256_by_doi[chunk.doi],
        "section_id": chunk.section_id,
        "ordinal": chunk.ordinal,
        "chunk_kind": CHUNK_KIND_PARAGRAPH,
        "normalized_type": chunk.normalized_type,
        "section_path": list(section["section_path"]),
        "text": chunk.text,
        "text_sha256": hashlib.sha256(chunk.text.encode("utf-8")).hexdigest(),
        "spans": spans,
        "source_locator": chunk.spans[0].source_locator,
        "content_tokens": chunk.content_tokens,
        "hard_split": chunk.hard_split,
        "omitted": omitted,
        "chunking_version": CHUNKING_VERSION,
        "token_counter_id": token_counter_id,
        "template_version": TEMPLATE_VERSION,
    }


def _token_stats(values: Sequence[int]) -> dict[str, int]:
    """Return deterministic nearest-rank integer statistics."""
    if not values:
        return {"min": 0, "median": 0, "p95": 0, "max": 0}
    ordered = sorted(values)
    return {
        "min": ordered[0],
        "median": ordered[math.ceil(len(ordered) * 0.50) - 1],
        "p95": ordered[math.ceil(len(ordered) * 0.95) - 1],
        "max": ordered[-1],
    }


def chunk_report(
    chunks: Sequence[Chunk],
    bundle: SourceBundle,
    config: ChunkConfig,
    token_counter_id: str,
) -> dict[str, Any]:
    """Summarize source counts and token statistics without source prose."""
    counter = Utf8BytesDiv3Counter()
    sections_by_doi: dict[str, list[dict[str, Any]]] = {}
    paragraphs_by_doi: dict[str, list[dict[str, Any]]] = {}
    chunks_by_doi: dict[str, list[Chunk]] = {}
    for section in bundle.section_records:
        sections_by_doi.setdefault(section["doi"], []).append(section)
    for paragraph in bundle.paragraph_records:
        paragraphs_by_doi.setdefault(paragraph["doi"], []).append(paragraph)
    for chunk in chunks:
        chunks_by_doi.setdefault(chunk.doi, []).append(chunk)
    papers = []
    for paper in sorted(bundle.parse_report_papers, key=lambda row: row["doi"]):
        doi = paper["doi"]
        source_paragraphs = paragraphs_by_doi.get(doi, [])
        paper_chunks = chunks_by_doi.get(doi, [])
        excluded = count_excluded(paper)
        papers.append(
            {
                "doi": doi,
                "xml_sha256": paper["xml_sha256"],
                "section_count": len(sections_by_doi.get(doi, [])),
                "sections_with_chunks": len(
                    {chunk.section_id for chunk in paper_chunks}
                ),
                "chunk_count": len(paper_chunks),
                "paragraph_count": len(source_paragraphs),
                "blank_paragraph_count": sum(
                    not row["text"].strip() for row in source_paragraphs
                ),
                "paragraphs_with_omitted": count_paragraphs_with_omitted(
                    source_paragraphs
                ),
                "hard_split_chunks": sum(
                    chunk.hard_split for chunk in paper_chunks
                ),
                "excluded_elements": excluded.excluded_elements,
                "unlisted_kinds": excluded.unlisted_kinds,
                "back_matter_excluded": excluded.back_matter_excluded,
            }
        )
    type_counts: dict[str, int] = {}
    for chunk in chunks:
        type_counts[chunk.normalized_type] = (
            type_counts.get(chunk.normalized_type, 0) + 1
        )
    summary = {
        "paper_count": len(papers),
        "section_count": sum(paper["section_count"] for paper in papers),
        "sections_with_chunks": sum(
            paper["sections_with_chunks"] for paper in papers
        ),
        "chunk_count": len(chunks),
        "paragraph_count": sum(paper["paragraph_count"] for paper in papers),
        "blank_paragraph_count": sum(
            paper["blank_paragraph_count"] for paper in papers
        ),
        "paragraphs_with_omitted": sum(
            paper["paragraphs_with_omitted"] for paper in papers
        ),
        "excluded_elements": sum(
            sum(paper["excluded_elements"].values()) for paper in papers
        ),
        "back_matter_excluded": sum(
            sum(paper["back_matter_excluded"].values()) for paper in papers
        ),
        "chunks_by_normalized_type": dict(sorted(type_counts.items())),
        "content_tokens": _token_stats(
            [chunk.content_tokens for chunk in chunks]
        ),
        "final_input_estimated_tokens": _token_stats(
            [
                counter.count(
                    build_embedding_text(chunk.heading_path, chunk.text, "")
                )
                for chunk in chunks
            ]
        ),
        "below_soft_min_chunks": sum(
            chunk.content_tokens < config.soft_min_tokens for chunk in chunks
        ),
        "hard_split_chunks": sum(chunk.hard_split for chunk in chunks),
    }
    return {
        "chunking_version": CHUNKING_VERSION,
        "token_counter_id": token_counter_id,
        "template_version": TEMPLATE_VERSION,
        "config": asdict(config),
        "input_sha256": bundle.input_sha256,
        "policy": {
            "skipped_element_kinds": {
                kind: asdict(policy)
                for kind, policy in sorted(EXCLUDED_CATEGORIES.items())
            },
            "back_matter_containers": dict(
                sorted(BACK_MATTER_CATEGORIES.items())
            ),
        },
        "papers": papers,
        "summary": summary,
    }


def write_outputs(outputs: Mapping[Path, bytes]) -> None:
    """Stage all output bytes and publish them without partial replacement."""
    staged: dict[Path, Path] = {}
    previous: dict[Path, bytes | None] = {}
    replaced: list[Path] = []
    try:
        for target, content in outputs.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            previous[target] = target.read_bytes() if target.exists() else None
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=target.parent, suffix=".tmp", delete=False
            ) as file:
                staged[target] = Path(file.name)
                file.write(content)
                file.flush()
                os.fsync(file.fileno())
        for target, temporary in staged.items():
            os.replace(temporary, target)
            replaced.append(target)
    except Exception:
        for target in reversed(replaced):
            old = previous[target]
            if old is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(old)
        raise
    finally:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)


def write_chunk_files(
    chunks: Sequence[Chunk],
    bundle: SourceBundle,
    config: ChunkConfig,
    token_counter_id: str,
    chunks_path: Path,
    report_path: Path,
) -> None:
    """Write deterministic UTF-8 JSONL and JSON artifacts atomically."""
    section_order = {
        (row["doi"], row["section_id"]): index
        for index, row in enumerate(bundle.section_records)
    }
    ordered_chunks = sorted(
        chunks,
        key=lambda chunk: (
            section_order[(chunk.doi, chunk.section_id)],
            chunk.ordinal,
        ),
    )
    records = [
        chunk_record(chunk, bundle, token_counter_id)
        for chunk in ordered_chunks
    ]
    report = chunk_report(ordered_chunks, bundle, config, token_counter_id)
    chunks_bytes = "".join(
        json.dumps(record, ensure_ascii=False) + "\n" for record in records
    ).encode("utf-8")
    report_bytes = (
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
    write_outputs({chunks_path: chunks_bytes, report_path: report_bytes})
