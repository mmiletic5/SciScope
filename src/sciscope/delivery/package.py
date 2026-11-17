"""Offline deterministic delivery of validated F001–F003 artifacts."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Never, cast

from sciscope.chunking import loader
from sciscope.chunking import validate as chunk_validate
from sciscope.chunking.config import TEMPLATE_VERSION
from sciscope.chunking.counter import Utf8BytesDiv3Counter
from sciscope.chunking.report import CHUNKING_VERSION
from sciscope.chunking.validate import Finding
from sciscope.delivery import contract, publish
from sciscope.delivery.papers import PaperBuildError, build_papers
from sciscope.embedding import validate as embedding_validate
from sciscope.embedding.store import render_json

DEFAULT_NORM_TOLERANCE = 0.01
_COPIED = {
    "sections.jsonl": "sections",
    "chunks.jsonl": "chunks",
    "vectors.f32": "vectors",
    "embedding_manifest.json": "embedding_manifest",
}
_REPORTS = ("parse_report", "chunk_report", "embedding_report")
_INPUT_FIELDS = (
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
    "parser_source",
    "taxonomy_source",
)
_INPUT_CODES = frozenset(
    {
        "invalid-usage",
        "missing-file",
        "invalid-utf8",
        "invalid-json",
        "duplicate-json-key",
        "wrong-type",
        "wrong-field-set",
    }
)
_ERROR_CODES = _INPUT_CODES | {
    "output-path-conflict",
    "output-write-failed",
    "delivery-integrity-mismatch",
    "delivery-failed",
}


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
    """Sanitized code/status with trusted Finding groups for CLI diagnostics."""

    code: str
    exit_code: int

    def __init__(self, code: str) -> None:
        """Initialize a sanitized code and its exit status."""
        self.code = (
            code
            if type(code) is str and code in _ERROR_CODES
            else "delivery-failed"
        )
        self.exit_code = (
            2 if self.code in _INPUT_CODES | {"output-path-conflict"} else 1
        )
        self.findings: tuple[Finding, ...] = (
            Finding(self.code, 1, ("report",)),
        )
        super().__init__(self.code)


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
    return {
        "schema_version": "0.3.0",
        "contract_version": "0.3.0",
        "status": "draft",
        "counts": dict(counts),
        "files": deepcopy(dict(files)),
        "processing_versions": {
            "parser": {"version": None, "source_sha256": parser_sha256},
            "taxonomy": {"version": "v0", "source_sha256": taxonomy_sha256},
            "locator": "jats:v1",
            "chunking_version": chunking_version,
            "token_counter_id": token_counter_id,
            "template_version": template_version,
        },
        "source_reports": deepcopy(dict(source_reports)),
        "embedding_set": {
            "provider": embedding_manifest["provider"],
            "model": embedding_manifest["model"],
            "dimensions": embedding_manifest["returned_dimensions"],
            "dtype": "float32-le",
            "row_mapping": "embedding_manifest.entries",
            "passage_prefix": embedding_manifest["passage_prefix"],
            "query_prefix": embedding_manifest["query_prefix"],
            "normalization": {
                **deepcopy(embedding_manifest["normalization"]),
                "tolerance": DEFAULT_NORM_TOLERANCE,
            },
            "chunks_sha256": embedding_manifest["chunks_sha256"],
            "vectors_sha256": embedding_manifest["vectors_sha256"],
            "embedding_model_revision": None,
        },
    }


def render_manifest(manifest: Mapping[str, object]) -> bytes:
    """Render ordered two-space JSON as strict UTF-8 with a final LF."""
    return render_json(manifest)


def render_papers(papers: Sequence[Mapping[str, object]]) -> bytes:
    """Render DOI-sorted PAPER_FIELDS-ordered strict UTF-8 JSONL."""
    return "".join(
        json.dumps(
            {field: row[field] for field in contract.PAPER_FIELDS},
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
        for row in sorted(papers, key=lambda row: cast(str, row["doi"]))
    ).encode("utf-8")


def validate_staged_inputs(
    inputs: DeliveryInputs, staged_dir: Path
) -> tuple[Finding, ...]:
    """Run existing complete-set validators on staged payloads and reports.

    Structural input errors retain SourceInputError; semantic findings are
    returned. Original paragraphs and parse report remain upstream inputs.
    """
    sources = loader.load_sources(
        staged_dir / "sections.jsonl", inputs.paragraphs, inputs.parse_report
    )
    loaded = chunk_validate.load_chunk_records(staged_dir / "chunks.jsonl")
    counter = Utf8BytesDiv3Counter()
    findings = chunk_validate.validate_chunks(
        sources,
        loaded.records,
        counter,
        operational_cap_tokens=384,
        chunk_report=chunk_validate.read_validation_json(inputs.chunk_report),
    )
    manifest = chunk_validate.read_validation_json(
        staged_dir / "embedding_manifest.json"
    )
    report = chunk_validate.read_validation_json(inputs.embedding_report)
    findings.extend(
        embedding_validate.validate_embedding_set(
            loaded.records,
            chunks_sha256=loaded.chunks_sha256,
            manifest=manifest,
            report=report,
            vectors=chunk_validate.read_validation_bytes(
                staged_dir / "vectors.f32"
            ),
            counter=counter,
            operational_cap_tokens=384,
            norm_tolerance=DEFAULT_NORM_TOLERANCE,
            allow_partial=False,
        )
    )
    try:
        embedding_validate.validate_embedding_structure(manifest, report)
    except loader.SourceInputError as error:
        _refuse((*findings, Finding(error.code, 1, ("report",))), 2)
    return tuple(findings)


def run_delivery(inputs: DeliveryInputs) -> DeliverySummary:
    """Stage, validate, assemble and publish both artifacts with rollback.

    Raises:
        DeliveryError: Sanitized failure with exit_code and Finding groups.
    """
    try:
        _guard_paths(inputs)
        with publish._staging(inputs.output_dir.parent) as staged:
            for filename, field in _COPIED.items():
                (staged / filename).write_bytes(
                    _read_bytes(getattr(inputs, field))
                )
            findings = validate_staged_inputs(inputs, staged)
            if findings:
                _refuse(findings, 1)
            papers = build_papers(
                _read_jsonl(inputs.metadata),
                _read_jsonl(inputs.acquisition_manifest),
            )
            (staged / "papers.jsonl").write_bytes(render_papers(papers))
            manifest, summary = _assemble(inputs, staged, papers)
            _check_produced(staged, manifest)
            encoded = render_manifest(manifest)
            (staged / "delivery_manifest.json").write_bytes(encoded)
            _check_integrity(inputs, staged, manifest, encoded)
            publish._publish(
                staged, encoded, inputs.output_dir, inputs.committed_manifest
            )
            return summary
    except DeliveryError:
        raise
    except loader.SourceInputError as error:
        _refuse((Finding(error.code, 1, ("report",)),), 2)
    except loader.SourceConsistencyError as error:
        _refuse((Finding(error.code, 1, ("report",)),), 1)
    except PaperBuildError as error:
        _refuse(tuple(Finding(code, 1, ("report",)) for code in error.codes), 1)
    except OSError:
        raise DeliveryError("output-write-failed") from None
    except Exception:
        raise DeliveryError("delivery-failed") from None


def _refuse(findings: Sequence[Finding], exit_code: int) -> Never:
    """Carry trusted upstream/checker findings without source exception text."""
    error = DeliveryError("delivery-failed")
    error.findings = tuple(findings)
    error.exit_code = exit_code
    raise error from None


def _overlap(left: Path, right: Path) -> bool:
    """Compare ancestry both ways without opening either path."""
    return left.is_relative_to(right) or right.is_relative_to(left)


def _guard_paths(inputs: DeliveryInputs) -> None:
    """Refuse aliases before reading inputs or creating output parents."""
    destinations = (inputs.output_dir, inputs.committed_manifest)
    if inputs.output_dir.is_symlink() or inputs.committed_manifest.is_symlink():
        raise DeliveryError("output-path-conflict")
    source_paths = [getattr(inputs, name) for name in _INPUT_FIELDS]
    source_paths.extend((inputs.cache_dir, DeliveryInputs().cache_dir))
    lexical = tuple(path.absolute() for path in destinations)
    if _overlap(*lexical) or any(
        _overlap(output, source.absolute())
        for output in lexical
        for source in source_paths
    ):
        raise DeliveryError("output-path-conflict")
    resolved = tuple(path.resolve() for path in destinations)
    protected = [path.resolve() for path in source_paths]
    all_paths = (*destinations, *source_paths, *resolved, *protected)
    if (
        any(
            part.startswith(
                (".sciscope-delivery-stage-", ".sciscope-delivery-backup-")
            )
            for path in all_paths
            for part in path.parts
        )
        or _overlap(*resolved)
        or any(
            _overlap(output, source)
            for output in resolved
            for source in protected
        )
    ):
        raise DeliveryError("output-path-conflict")
    if (inputs.output_dir.exists() and not inputs.output_dir.is_dir()) or (
        inputs.committed_manifest.exists()
        and not inputs.committed_manifest.is_file()
    ):
        raise DeliveryError("output-path-conflict")


def _read_bytes(path: Path) -> bytes:
    """Classify unreadable source paths without propagating OS messages."""
    return chunk_validate.read_validation_bytes(path)


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject duplicate JSON keys at every nesting level."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise DeliveryError("duplicate-json-key")
        result[key] = value
    return result


def _constant(value: str) -> Never:
    """Reject nonstandard nonfinite JSON numbers."""
    raise DeliveryError("invalid-json")


def _finite_float(value: str) -> float:
    """Reject finite-looking JSON spellings that overflow to infinity."""
    number = float(value)
    if not math.isfinite(number):
        raise DeliveryError("invalid-json")
    return number


def _decode_json(data: bytes) -> object:
    """Parse strict UTF-8/JSON without exposing decoder exception values."""
    try:
        text = data.decode("utf-8")
    except UnicodeError:
        raise DeliveryError("invalid-utf8") from None
    try:
        return json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_constant=_constant,
            parse_float=_finite_float,
        )
    except DeliveryError:
        raise
    except (ValueError, RecursionError):
        raise DeliveryError("invalid-json") from None


def _read_jsonl(path: Path) -> tuple[object, ...]:
    """Read LF-only JSONL, rejecting interior blank lines and malformed JSON."""
    raw = _read_bytes(path)
    lines = raw.split(b"\n") if raw else []
    if lines and lines[-1] == b"":
        lines.pop()
    return tuple(_decode_json(line) for line in lines)


def _descriptor(data: bytes, count: int | None = None) -> dict[str, object]:
    """Describe exact bytes, with record count only for package payloads."""
    result: dict[str, object] = {
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }
    if count is not None:
        result["record_count"] = count
    return result


def _line_count(data: bytes) -> int:
    """Count LF-delimited records, excluding one final empty segment."""
    return len(data.split(b"\n")) - int(data.endswith(b"\n")) if data else 0


def _assemble(
    inputs: DeliveryInputs, staged: Path, papers: Sequence[Mapping[str, object]]
) -> tuple[dict[str, object], DeliverySummary]:
    """Build metadata from staged bytes and validated F003 identifiers."""
    embedded = chunk_validate.read_validation_json(
        staged / "embedding_manifest.json"
    )
    identifiers = ("chunking_version", "token_counter_id", "template_version")
    expected = (
        CHUNKING_VERSION,
        Utf8BytesDiv3Counter.counter_id,
        TEMPLATE_VERSION,
    )
    if tuple(embedded[name] for name in identifiers) != expected:
        _refuse((Finding("set-version-mismatch", 1, ("manifest",)),), 1)
    counts = {
        "papers": len(papers),
        "sections": _line_count((staged / "sections.jsonl").read_bytes()),
        "chunks": _line_count((staged / "chunks.jsonl").read_bytes()),
    }
    records = (
        counts["papers"],
        counts["sections"],
        counts["chunks"],
        embedded["vector_count"],
        1,
    )
    files = {
        name: _descriptor((staged / name).read_bytes(), count)
        for name, count in zip(("papers.jsonl", *_COPIED), records, strict=True)
    }
    manifest = build_delivery_manifest(
        counts=counts,
        files=files,
        source_reports={
            name + ".json": _descriptor(_read_bytes(getattr(inputs, name)))
            for name in _REPORTS
        },
        parser_sha256=hashlib.sha256(
            _read_bytes(inputs.parser_source)
        ).hexdigest(),
        taxonomy_sha256=hashlib.sha256(
            _read_bytes(inputs.taxonomy_source)
        ).hexdigest(),
        chunking_version=embedded["chunking_version"],
        token_counter_id=embedded["token_counter_id"],
        template_version=embedded["template_version"],
        embedding_manifest=embedded,
    )
    return manifest, DeliverySummary(
        counts["papers"],
        counts["sections"],
        counts["chunks"],
        embedded["vector_count"],
        6,
    )


def _check_produced(staged: Path, manifest: Mapping[str, object]) -> None:
    """Check every produced record through the patchable Group A seams."""
    findings: list[Finding] = []
    for filename, checker in (
        ("papers.jsonl", contract.check_paper),
        ("sections.jsonl", contract.check_section),
        ("chunks.jsonl", contract.check_chunk),
    ):
        for record in _read_jsonl(staged / filename):
            findings.extend(
                Finding(code, 1, ("report",)) for code in checker(record)
            )
    findings.extend(
        Finding(code, 1, ("manifest",))
        for code in contract.check_delivery_manifest(manifest)
    )
    if findings:
        _refuse(findings, 1)


def _check_integrity(
    inputs: DeliveryInputs,
    staged: Path,
    manifest: Mapping[str, object],
    encoded: bytes,
) -> None:
    """Re-read the completed stage and refuse mismatched bytes or records."""
    files = cast(Mapping[str, Mapping[str, object]], manifest["files"])
    embedding_set = cast(Mapping[str, object], manifest["embedding_set"])
    if {path.name for path in staged.iterdir()} != {
        *files,
        "delivery_manifest.json",
    }:
        raise DeliveryError("delivery-integrity-mismatch")
    if any(
        files[name]["sha256"] != embedding_set[key]
        for name, key in (
            ("chunks.jsonl", "chunks_sha256"),
            ("vectors.f32", "vectors_sha256"),
        )
    ):
        raise DeliveryError("delivery-integrity-mismatch")
    for name, expected in files.items():
        data = (staged / name).read_bytes()
        count = _line_count(data) if name.endswith(".jsonl") else 1
        if name == "vectors.f32":
            width = cast(int, embedding_set["dimensions"]) * 4
            if width <= 0 or len(data) % width:
                raise DeliveryError("delivery-integrity-mismatch")
            count = len(data) // width
        if _descriptor(data, count) != expected:
            raise DeliveryError("delivery-integrity-mismatch")
    reports = cast(
        Mapping[str, Mapping[str, object]], manifest["source_reports"]
    )
    if any(
        _descriptor(_read_bytes(getattr(inputs, name)))
        != reports[name + ".json"]
        for name in _REPORTS
    ):
        raise DeliveryError("delivery-integrity-mismatch")
    data = (staged / "delivery_manifest.json").read_bytes()
    try:
        reread = _decode_json(data)
    except DeliveryError:
        raise DeliveryError("delivery-integrity-mismatch") from None
    if data != encoded or reread != manifest:
        raise DeliveryError("delivery-integrity-mismatch")
    _check_produced(staged, manifest)
