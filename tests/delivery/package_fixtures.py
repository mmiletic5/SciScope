"""Complete SYNTHETIC offline tree with invented text and fake vectors."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, overload

from delivery_fixtures import acquisition_manifest, metadata, paper

from sciscope.chunking.config import ChunkConfig
from sciscope.chunking.core import chunk_sections
from sciscope.chunking.counter import Utf8BytesDiv3Counter
from sciscope.chunking.loader import load_sources
from sciscope.chunking.output import write_chunk_files
from sciscope.delivery.package import DeliveryInputs
from sciscope.embedding.config import EmbeddingConfig
from sciscope.embedding.pipeline import EmbedOptions, run_embedding
from sciscope.embedding.provider import FakeEmbedder

REPO = Path(__file__).resolve().parents[2]
PAYLOADS = (
    "papers.jsonl",
    "sections.jsonl",
    "chunks.jsonl",
    "vectors.f32",
    "embedding_manifest.json",
)
PACKAGE_FILES = (*PAYLOADS, "delivery_manifest.json")
COPIED = ("sections", "chunks", "vectors", "embedding_manifest")


def write_json(path: Path, value: object) -> None:
    """Write SYNTHETIC JSON with the F003 JSON convention."""
    path.write_bytes(
        (
            json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)
            + "\n"
        ).encode("utf-8")
    )


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    """Write SYNTHETIC LF-only JSONL with F002 separators."""
    path.write_bytes(
        "".join(
            json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n"
            for row in rows
        ).encode("utf-8")
    )


def read_json(path: Path) -> Any:
    """Read controlled fixture JSON for assertions or mutation."""
    return json.loads(path.read_bytes())


def rows(path: Path) -> list[dict[str, Any]]:
    """Read controlled JSONL using LF alone."""
    return [
        json.loads(line)
        for line in path.read_bytes().decode().split("\n")
        if line
    ]


def snapshot(root: Path) -> dict[str, bytes | None]:
    """Record files and empty directories to detect mutation and leftovers."""
    return {
        item.relative_to(root).as_posix(): (
            None if item.is_dir() else item.read_bytes()
        )
        for item in sorted(root.rglob("*"))
    }


def descriptor(path: Path, record_count: int | None = None) -> dict[str, Any]:
    """Independently calculate a descriptor from exact fixture bytes."""
    data = path.read_bytes()
    result: dict[str, Any] = {
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }
    if record_count is not None:
        result["record_count"] = record_count
    return result


@dataclass(frozen=True)
class PackageTree:
    """Paths and independent expectations for one tiny complete upstream set."""

    root: Path
    inputs: DeliveryInputs
    expected_papers: tuple[dict[str, Any], ...]

    def args(self) -> list[str]:
        """Build all twelve proposed CLI options with explicit fixture paths."""
        names = (
            "metadata",
            "acquisition_manifest",
            "sections",
            "paragraphs",
            "parse_report",
            "chunks",
            "chunk_report",
            "vectors",
            "embedding_manifest",
            "embedding_report",
            "output_dir",
            "committed_manifest",
        )
        return [
            "deliver",
            *[
                token
                for name in names
                for token in (
                    "--" + name.replace("_", "-"),
                    str(getattr(self.inputs, name)),
                )
            ],
        ]

    def seed_previous(self) -> None:
        """Seed recognizable previous artifacts for rollback assertions."""
        self.inputs.output_dir.mkdir(parents=True)
        for name in PACKAGE_FILES:
            (self.inputs.output_dir / name).write_bytes(
                b"SYNTHETIC previous " + name.encode()
            )
        self.inputs.committed_manifest.parent.mkdir(parents=True, exist_ok=True)
        self.inputs.committed_manifest.write_bytes(
            b"SYNTHETIC previous committed copy\n"
        )


def make_tree(root: Path) -> PackageTree:
    """Build two papers and one empty section with real upstream writers."""
    upstream = root / "upstream"
    upstream.mkdir()
    paths = {
        name: upstream / filename
        for name, filename in (
            ("metadata", "metadata.jsonl"),
            ("acquisition_manifest", "manifest.jsonl"),
            ("sections", "sections.jsonl"),
            ("paragraphs", "paragraphs.jsonl"),
            ("parse_report", "parse_report.json"),
            ("chunks", "chunks.jsonl"),
            ("chunk_report", "chunk_report.json"),
            ("vectors", "vectors.f32"),
            ("embedding_manifest", "embedding_manifest.json"),
            ("embedding_report", "embedding_report.json"),
        )
    }
    inputs = DeliveryInputs(
        **paths,
        cache_dir=upstream / "cache",
        output_dir=root / "delivery" / "pilot",
        committed_manifest=root / "committed" / "delivery_manifest.json",
        parser_source=REPO / "src/sciscope/jats/parser.py",
        taxonomy_source=REPO / "src/sciscope/jats/classify.py",
    )
    metadata_rows, acquisitions, expected = [], [], []
    sections, paragraphs, reports = [], [], []
    for index, suffix in enumerate(("a", "b")):
        doi = f"10.1234/synthetic.{suffix}"
        digest = suffix * 64
        description, acquisition, expected_paper = (
            metadata(),
            acquisition_manifest(),
            paper(),
        )
        updates = {
            "doi": doi,
            "title": "SYNTHETIC Δ\u0085\u2028\u2029 " + suffix,
            "language": "EN" if index == 0 else "en",
        }
        description.update(updates)
        acquisition.update(doi=doi, xml_sha256=digest)
        expected_paper.update(**updates, xml_sha256=digest)
        metadata_rows.append(description)
        acquisitions.append(acquisition)
        expected.append(expected_paper)
        count = 2 if index == 0 else 1
        for number in range(1, count + 1):
            empty = index == 0 and number == 1
            locator = f"jats:v1:{digest}:/article[1]/body[1]/sec[{number}]"
            section_id = f"{doi}#s{number}"
            sections.append(
                {
                    "doi": doi,
                    "title": description["title"],
                    "xml_sha256": digest,
                    "section_id": section_id,
                    "parent_section_id": None,
                    "section_path": ["SYNTHETIC heading"],
                    "original_heading": "SYNTHETIC heading",
                    "normalized_type": "other",
                    "source_locator": locator,
                    "depth": 1,
                    "paragraph_count": 0 if empty else 1,
                }
            )
            if not empty:
                paragraphs.append(
                    {
                        "doi": doi,
                        "section_id": section_id,
                        "paragraph_index": 1,
                        "text": "SYNTHETIC amber Δ\u0085\u2028\u2029 "
                        + suffix
                        + ".",
                        "omitted": [],
                        "source_locator": locator + "/p[1]",
                    }
                )
        reports.append(
            {
                "doi": doi,
                "xml_sha256": digest,
                "section_count": count,
                "paragraph_count": 1,
                "abstract_paragraph_count": 0,
                "normalized_type_histogram": {"other": count},
                "unclassified_headings": {},
                "type_conflicts": [],
                "skipped_element_kinds": {},
                "back_matter_containers": [],
                "warnings": [],
                "errors": [],
            }
        )
    write_rows(inputs.metadata, list(reversed(metadata_rows)))
    write_rows(inputs.acquisition_manifest, acquisitions)
    write_rows(inputs.sections, sections)
    write_rows(inputs.paragraphs, paragraphs)
    write_json(
        inputs.parse_report,
        {"papers": reports, "summary": {"succeeded": 2, "failed": 0}},
    )
    bundle = load_sources(
        inputs.sections, inputs.paragraphs, inputs.parse_report
    )
    counter, config = Utf8BytesDiv3Counter(), ChunkConfig()
    chunks = chunk_sections(bundle.sections, bundle.paragraphs, config, counter)
    write_chunk_files(
        chunks,
        bundle,
        config,
        counter.counter_id,
        inputs.chunks,
        inputs.chunk_report,
    )
    embedding_config = EmbeddingConfig(dimensions=2)
    run_embedding(
        EmbedOptions(
            inputs.chunks,
            inputs.cache_dir,
            inputs.vectors,
            inputs.embedding_manifest,
            inputs.embedding_report,
        ),
        embedding_config,
        counter,
        embedder_factory=lambda: FakeEmbedder(embedding_config),
        utc_date=lambda: "2026-11-17",
    )
    return PackageTree(root, inputs, tuple(expected))


class RecordingEnvironment(dict[str, str]):
    """Track every key lookup without reading real credentials."""

    def __init__(self) -> None:
        """Use invented keys only; avoid copying the host environment."""
        super().__init__(OPENAI_API_KEY="SYNTHETIC-KEY")
        self.accessed_keys: list[str] = []

    def __getitem__(self, key: str) -> str:
        """Record indexed reads."""
        self.accessed_keys.append(key)
        return super().__getitem__(key)

    @overload
    def get(self, key: str, default: None = None, /) -> str | None: ...

    @overload
    def get(self, key: str, default: str, /) -> str: ...

    @overload
    def get[Default](self, key: str, default: Default, /) -> str | Default: ...

    def get(self, key: str, default: object = None, /) -> object:
        """Record get because dict.get bypasses indexed reads."""
        self.accessed_keys.append(key)
        return super().get(key, default)

    def __contains__(self, key: object) -> bool:
        """Record membership probes."""
        self.accessed_keys.append(str(key))
        return super().__contains__(key)

    def __iter__(self) -> Any:
        """Record enumeration."""
        self.accessed_keys.append("<iteration>")
        return super().__iter__()


def symlinks_supported() -> bool:
    """Probe symlink privilege in a disposable workspace-local directory."""
    import tempfile

    try:
        with tempfile.TemporaryDirectory(
            prefix="synthetic-symlink-", dir=REPO
        ) as directory:
            target = Path(directory) / "target"
            target.mkdir()
            link = Path(directory) / "link"
            link.symlink_to(target, target_is_directory=True)
            return link.is_symlink()
    except OSError:
        return False
