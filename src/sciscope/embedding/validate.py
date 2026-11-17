"""Offline embedding-set integrity, normalization and report validation."""

from __future__ import annotations

import hashlib
import math
import re
import struct
from collections.abc import Mapping, Sequence
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any, cast

from sciscope.chunking.counter import TokenCounter
from sciscope.chunking.validate import (
    FieldCheck,
    Finding,
    FindingCollector,
    check_record,
    is_json_integer,
    is_json_number,
    is_json_string,
)
from sciscope.embedding.config import (
    EMBEDDING_FORMAT_VERSION,
    PRICE_USD_PER_MILLION_TOKENS,
    EmbeddingConfig,
    build_passage_input,
)

type Record = Mapping[str, Any]


def validate_embedding_structure(
    manifest: Mapping[str, object],
    report: Mapping[str, object],
    *,
    exact: bool = True,
) -> None:
    """Check public manifest/report schemas, optionally retaining extra keys.

    Extra keys may be inspected for purity before the CLI applies exact field
    checks. Required fields and nested types are always checked first.
    """
    strings = (
        "format_version",
        "status",
        "provider",
        "model",
        "passage_prefix",
        "query_prefix",
        "template_version",
        "token_counter_id",
        "chunking_version",
        "chunks_sha256",
        "creation_date",
        "vectors_file",
        "vectors_dtype",
        "vectors_sha256",
    )
    integers = (
        "requested_dimensions",
        "returned_dimensions",
        "chunk_count",
        "vector_count",
        "estimated_input_tokens",
        "provider_input_count",
    )
    fields: dict[str, FieldCheck] = dict.fromkeys(strings, is_json_string)
    fields.update(dict.fromkeys(integers, is_json_integer))
    fields.update(
        {
            "custom_base_url_used": lambda item: type(item) is bool,
            "normalization": lambda item: isinstance(item, dict),
            "entries": lambda item: isinstance(item, list),
            "usage": lambda item: isinstance(item, dict),
        }
    )
    checked = check_record(manifest, fields, exact=exact)
    check_record(
        checked["normalization"],
        {
            "declared": is_json_string,
            "observed_norm_min": is_json_number,
            "observed_norm_max": is_json_number,
        },
    )
    usage_fields = dict.fromkeys(
        ("prompt_tokens", "total_tokens"), is_json_integer
    )
    check_record(checked["usage"], usage_fields)
    for entry in checked["entries"]:
        check_record(
            entry, dict.fromkeys(("chunk_id", "input_sha256"), is_json_string)
        )
    report_fields = {
        name: check
        for name, check in fields.items()
        if name
        not in (
            "passage_prefix",
            "query_prefix",
            "normalization",
            "entries",
            "vectors_file",
            "vectors_dtype",
            "vectors_sha256",
        )
    }
    report_fields.update(
        {
            "paper_count": is_json_integer,
            "approximate_cost": lambda item: isinstance(item, dict),
        }
    )
    checked_report = check_record(report, report_fields, exact=exact)
    check_record(checked_report["usage"], usage_fields)
    check_record(
        checked_report["approximate_cost"],
        {
            "usd": is_json_number,
            "label": is_json_string,
            "basis": is_json_string,
        },
    )


def validate_embedding_set(
    records: Sequence[Mapping[str, object]],
    *,
    chunks_sha256: str,
    manifest: Mapping[str, object],
    report: Mapping[str, object],
    vectors: bytes,
    counter: TokenCounter,
    operational_cap_tokens: int = 384,
    norm_tolerance: float = 0.01,
    allow_partial: bool = False,
) -> list[Finding]:
    """Collect set, input, vector, normalization, report and purity findings.

    Args:
        records: Full structurally checked chunk records in file order.
        chunks_sha256: SHA256 of the current exact chunks file bytes.
        manifest: Parsed manifest mapping, including ordered vector entries.
        report: Parsed committed embedding report mapping.
        vectors: Raw float32-le file bytes, without cache access.
        counter: Versioned final-input estimator.
        operational_cap_tokens: Configured cap, also bounded by 512.
        norm_tolerance: Finite positive maximum L2 deviation, at most one.
        allow_partial: Accept a nonempty subset explicitly marked partial.

    Returns:
        Findings aggregated by code, with safe IDs in deterministic order.
    """
    validate_embedding_structure(manifest, report, exact=False)
    state = cast(Record, manifest)
    summary = cast(Record, report)
    chunks = {cast(str, row["chunk_id"]): cast(Record, row) for row in records}
    findings = FindingCollector()
    if state["status"] == "partial" and not allow_partial:
        findings.add("partial-set", "manifest")
    if state["chunks_sha256"] != chunks_sha256:
        findings.add("chunks-sha-mismatch", "manifest")
    if state["format_version"] != EMBEDDING_FORMAT_VERSION or any(
        any(
            row[name] != state[name]
            for name in (
                "template_version",
                "token_counter_id",
                "chunking_version",
            )
        )
        for row in chunks.values()
    ):
        findings.add("set-version-mismatch", "manifest")
    if (
        state["requested_dimensions"] != state["returned_dimensions"]
        or state["returned_dimensions"] < 1
        or state["vectors_dtype"] != "float32-le"
    ):
        findings.add("set-dimensions", "manifest")
    entries: list[Record] = state["entries"]
    ids = [entry["chunk_id"] for entry in entries]
    selected = set(ids)
    if (
        ids != sorted(selected)
        or not selected <= chunks.keys()
        or state["vector_count"] != len(entries)
        or state["chunk_count"] != len(records)
        or state["status"] not in ("complete", "partial")
        or (state["status"] == "complete" and selected != chunks.keys())
        or (state["status"] == "partial" and not selected)
    ):
        findings.add("set-chunk-mismatch", "manifest")
    config = EmbeddingConfig(passage_prefix=state["passage_prefix"])
    for index, entry in enumerate(entries):
        row = chunks.get(entry["chunk_id"])
        if row is None:
            continue
        text = build_passage_input(
            config, tuple(row["section_path"]), row["text"]
        )
        if (
            hashlib.sha256(text.encode("utf-8")).hexdigest()
            != entry["input_sha256"]
        ):
            findings.add("set-input-mismatch", entry["chunk_id"], index)
        if counter.count(text) > min(operational_cap_tokens, 512):
            findings.add("set-input-over-cap", entry["chunk_id"], index)
    _check_vectors(state, vectors, entries, norm_tolerance, findings)
    _check_report(state, summary, chunks, entries, findings)
    if state["usage"]["total_tokens"] > state["estimated_input_tokens"]:
        findings.add("calibration-exceeded", "manifest")
    for identifier, artifact in (("manifest", manifest), ("report", report)):
        if _impure(artifact):
            findings.add("report-impure", identifier)
    return findings.findings()


def _check_vectors(
    manifest: Record,
    vectors: bytes,
    entries: Sequence[Record],
    tolerance: float,
    findings: FindingCollector,
) -> None:
    """Check vector bytes and L2 norms while avoiding malformed-row cascades."""
    dims: int = manifest["returned_dimensions"]
    count: int = manifest["vector_count"]
    size_valid = dims > 0 and count >= 0 and len(vectors) == count * dims * 4
    if not size_valid:
        findings.add("vectors-size", "vectors")
    if hashlib.sha256(vectors).hexdigest() != manifest["vectors_sha256"]:
        findings.add("vectors-sha-mismatch", "vectors")
    normalization = manifest["normalization"]
    if normalization["declared"] != "l2":
        findings.add("normalization-unsupported", "manifest")
    aligned = vectors[: len(vectors) // 4 * 4]
    values = [value for (value,) in struct.iter_unpack("<f", aligned)]
    finite = all(math.isfinite(value) for value in values)
    if not finite:
        findings.add("vectors-nonfinite", "vectors")
    if not size_valid or not finite or normalization["declared"] != "l2":
        return
    norms = [
        math.sqrt(
            math.fsum(value * value for value in values[start : start + dims])
        )
        for start in range(0, len(values), dims)
    ]
    for index, (entry, norm) in enumerate(zip(entries, norms, strict=False)):
        if abs(norm - 1.0) > tolerance:
            findings.add(
                "vector-norm-out-of-tolerance", entry["chunk_id"], index
            )
    if normalization["observed_norm_min"] != round(
        min(norms, default=0.0), 9
    ) or normalization["observed_norm_max"] != round(
        max(norms, default=0.0), 9
    ):
        findings.add("normalization-mismatch", "manifest")


def _check_report(
    manifest: Record,
    report: Record,
    chunks: Mapping[str, Record],
    entries: Sequence[Record],
    findings: FindingCollector,
) -> None:
    """Compare shared facts, selected DOI count and reported-usage cost."""
    shared = manifest.keys() & report.keys()
    papers = {
        chunks[entry["chunk_id"]]["doi"]
        for entry in entries
        if entry["chunk_id"] in chunks
    }
    expected_cost = round(
        manifest["usage"]["total_tokens"]
        * PRICE_USD_PER_MILLION_TOKENS
        / 1_000_000,
        6,
    )
    if (
        any(manifest[name] != report[name] for name in shared)
        or report["paper_count"] != len(papers)
        or report["approximate_cost"]["usd"] != expected_cost
        or report["approximate_cost"]["label"] != "approximate"
    ):
        findings.add("report-manifest-mismatch", "report")


def _impure(value: object) -> bool:
    """Inspect recursive JSON keys/values for runtime metrics and locations."""
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key == "custom_base_url_used" and type(item) is bool:
                continue
            if _impure(str(key)) or _impure(item):
                return True
    elif isinstance(value, list):
        return any(_impure(item) for item in value)
    elif isinstance(value, str):
        normalized = value.lower().replace("-", "_")
        return bool(
            re.search(
                r"cache.*(?:hits?|miss)|api_?calls?|retr(?:y|ies)|"
                r"rate_?limit|base_?url|absolute_?path",
                normalized,
            )
            or "://" in value
            or PurePosixPath(value).is_absolute()
            or PureWindowsPath(value).is_absolute()
            or value.startswith("\\")
        )
    return False
