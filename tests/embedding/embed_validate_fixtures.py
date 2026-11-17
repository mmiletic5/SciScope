"""Synthetic offline F002 sources and artifact helpers for T007 RED tests."""

from __future__ import annotations

import hashlib
import json
import math
import struct
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sciscope.chunking.core import ChunkSpan
from sciscope.chunking.counter import Utf8BytesDiv3Counter
from sciscope.chunking.output import chunk_id
from sciscope.embedding.config import EmbeddingConfig
from sciscope.embedding.pipeline import EmbedOptions, run_embedding
from sciscope.embedding.provider import FakeEmbedder
from sciscope.pipeline.cli import main

DOI = "10.0000/synthetic-a"
DIGEST = "a" * 64
SECTION_LOCATOR = f"jats:v1:{DIGEST}:/article[1]/body[1]/sec[1]"
LOCATOR = SECTION_LOCATOR + "/p[1]"
TEXT = "Synthetic amber turns. Synthetic violet waits."
HEADING = "Synthetic heading"
FIXED_DATE = "2026-11-17"
COUNTER = Utf8BytesDiv3Counter()


def source_records() -> tuple[
    list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]
]:
    """Build minimal synthetic F002 records copied from T004's builder."""
    sections = [
        {
            "doi": DOI,
            "title": "Invented title",
            "xml_sha256": DIGEST,
            "section_id": "s1",
            "parent_section_id": None,
            "section_path": [HEADING],
            "original_heading": HEADING,
            "normalized_type": "methods",
            "source_locator": SECTION_LOCATOR,
            "depth": 1,
            "paragraph_count": 1,
        }
    ]
    paragraphs = [
        {
            "doi": DOI,
            "section_id": "s1",
            "paragraph_index": 1,
            "text": TEXT,
            "omitted": ["inline-formula"],
            "source_locator": LOCATOR,
        }
    ]
    report = {
        "papers": [
            {
                "doi": DOI,
                "xml_sha256": DIGEST,
                "section_count": 1,
                "paragraph_count": 1,
                "abstract_paragraph_count": 0,
                "normalized_type_histogram": {"methods": 1},
                "unclassified_headings": {},
                "type_conflicts": [],
                "skipped_element_kinds": {"inline-formula": 1},
                "back_matter_containers": ["ref-list"],
                "warnings": [],
                "errors": [],
            }
        ],
        "summary": {"succeeded": 1, "failed": 0},
    }
    return sections, paragraphs, report


def write_json(path: Path, value: object) -> None:
    """Write deterministic synthetic JSON without ASCII escaping."""
    path.write_bytes((json.dumps(value, ensure_ascii=False) + "\n").encode())


def read_json(path: Path) -> Any:
    """Read a synthetic JSON artifact for controlled mutation."""
    return json.loads(path.read_bytes())


def write_records(path: Path, records: list[dict[str, Any]]) -> None:
    """Write UTF-8 records separated only by LF."""
    path.write_bytes(
        "".join(
            json.dumps(row, ensure_ascii=False) + "\n" for row in records
        ).encode("utf-8")
    )


def records(path: Path) -> list[dict[str, Any]]:
    """Read raw Unicode separators as JSON content, never delimiters."""
    return [
        json.loads(line)
        for line in path.read_bytes().decode("utf-8").split("\n")
        if line
    ]


@dataclass(frozen=True)
class ValidationFiles:
    """Keep synthetic sources and generated outputs in one isolated root."""

    root: Path

    def path(self, name: str) -> Path:
        """Resolve a named synthetic artifact inside this fixture."""
        return self.root / name

    def chunk_args(self) -> list[str]:
        """Select the real chunk CLI with synthetic inputs and outputs."""
        return [
            "chunk",
            "--sections",
            str(self.path("sections.jsonl")),
            "--paragraphs",
            str(self.path("paragraphs.jsonl")),
            "--parse-report",
            str(self.path("parse_report.json")),
            "--chunks",
            str(self.path("chunks.jsonl")),
            "--report",
            str(self.path("chunk_report.json")),
        ]

    def validate_args(self, *extra: str) -> list[str]:
        """Select every validate input explicitly without cache options."""
        return [
            "validate",
            "--sections",
            str(self.path("sections.jsonl")),
            "--paragraphs",
            str(self.path("paragraphs.jsonl")),
            "--parse-report",
            str(self.path("parse_report.json")),
            "--chunks",
            str(self.path("chunks.jsonl")),
            "--chunk-report",
            str(self.path("chunk_report.json")),
            "--vectors",
            str(self.path("vectors.f32")),
            "--manifest",
            str(self.path("manifest.json")),
            "--report",
            str(self.path("embedding_report.json")),
            *extra,
        ]

    def options(self, limit: int | None = None) -> EmbedOptions:
        """Build exact paths for fake embedding or read-only preview."""
        return EmbedOptions(
            self.path("chunks.jsonl"),
            self.path("cache"),
            self.path("vectors.f32"),
            self.path("manifest.json"),
            self.path("embedding_report.json"),
            limit,
        )

    def embed_args(self, *extra: str) -> list[str]:
        """Build existing embed arguments with two synthetic dimensions."""
        return [
            "embed",
            "--chunks",
            str(self.path("chunks.jsonl")),
            "--cache-dir",
            str(self.path("cache")),
            "--vectors",
            str(self.path("vectors.f32")),
            "--manifest",
            str(self.path("manifest.json")),
            "--report",
            str(self.path("embedding_report.json")),
            "--dimensions",
            "2",
            *extra,
        ]


def make_chunks(root: Path, *, text: str = TEXT) -> ValidationFiles:
    """Run real chunking on three own-text sections and one blank section."""
    files = ValidationFiles(root)
    sections, paragraphs, report = source_records()
    paragraphs[0]["text"] = text
    for index, kind in ((2, "other"), (3, "methods"), (4, "methods")):
        locator = SECTION_LOCATOR.replace("sec[1]", f"sec[{index}]")
        sections.append(
            {
                **sections[0],
                "section_id": f"s{index}",
                "source_locator": locator,
                "normalized_type": kind,
            }
        )
        paragraphs.append(
            {
                **paragraphs[0],
                "section_id": f"s{index}",
                "source_locator": locator + "/p[1]",
                "text": "   "
                if index == 4
                else ("Synthetic cobalt rests." if index == 2 else text),
            }
        )
    paper = report["papers"][0]
    paper.update(section_count=4, paragraph_count=4)
    paper["normalized_type_histogram"] = {"methods": 3, "other": 1}
    write_records(files.path("sections.jsonl"), sections)
    write_records(files.path("paragraphs.jsonl"), paragraphs)
    write_json(files.path("parse_report.json"), report)
    assert main(files.chunk_args()) == 0
    return files


def embed_set(files: ValidationFiles, limit: int | None = None) -> None:
    """Generate authentic artifacts through run_embedding and FakeEmbedder."""
    config = EmbeddingConfig(dimensions=2)
    run_embedding(
        files.options(limit),
        config,
        COUNTER,
        embedder_factory=lambda: FakeEmbedder(config),
        utc_date=lambda: FIXED_DATE,
    )


def refresh_identity(row: dict[str, Any]) -> None:
    """Repair identity after an intentional span/ordinal/version mutation."""
    row["chunk_id"] = chunk_id(
        row["chunking_version"],
        row["doi"],
        row["section_id"],
        row["ordinal"],
        [ChunkSpan(**span) for span in row["spans"]],
    )


def refresh_text(row: dict[str, Any], text: str) -> None:
    """Repair text-derived metadata to isolate another intentional defect."""
    row["text"] = text
    row["text_sha256"] = hashlib.sha256(text.encode()).hexdigest()
    row["content_tokens"] = COUNTER.count(text)


def sync_report(files: ValidationFiles, manifest: Mapping[str, Any]) -> None:
    """Synchronize shared fields without repairing independent cost/counts."""
    report = read_json(files.path("embedding_report.json"))
    for name in report.keys() & manifest.keys():
        report[name] = manifest[name]
    write_json(files.path("embedding_report.json"), report)


def replace_vectors(files: ValidationFiles, values: list[float]) -> None:
    """Repair vector checksum and finite norm observations after mutation."""
    data = struct.pack("<" + "f" * len(values), *values)
    files.path("vectors.f32").write_bytes(data)
    manifest = read_json(files.path("manifest.json"))
    manifest["vectors_sha256"] = hashlib.sha256(data).hexdigest()
    rounded = struct.unpack("<" + "f" * len(values), data)
    norms = [
        math.sqrt(math.fsum(value * value for value in rounded[i : i + 2]))
        for i in range(0, len(values), 2)
    ]
    if all(math.isfinite(norm) for norm in norms):
        manifest["normalization"]["observed_norm_min"] = round(min(norms), 9)
        manifest["normalization"]["observed_norm_max"] = round(max(norms), 9)
    write_json(files.path("manifest.json"), manifest)


def tree_snapshot(root: Path) -> dict[str, bytes | None]:
    """Capture directories and bytes, including otherwise empty directories."""
    return {
        path.relative_to(root).as_posix(): (
            None if path.is_dir() else path.read_bytes()
        )
        for path in sorted(root.rglob("*"))
    }


class UnreadableEnvironment(Mapping[str, str]):
    """Fail every mapping access, including get, membership and iteration."""

    def __getitem__(self, key: str) -> str:
        """Reject key lookup."""
        raise AssertionError("Environment read")

    def __iter__(self) -> Iterator[str]:
        """Reject key enumeration."""
        raise AssertionError("Environment iteration")

    def __len__(self) -> int:
        """Reject environment sizing."""
        raise AssertionError("Environment size")


def forbidden_transport(*args: object, **kwargs: object) -> Any:
    """Fail at construction time, before any transport could make a call."""
    raise AssertionError("Transport constructed")


def failure_line(code: str, *ids: str, count: int | None = None) -> str:
    """Render an independently specified diagnostic expectation."""
    number = len(ids) if count is None else count
    return f"error: {code} count: {number} first: {','.join(ids[:3])}\n"
