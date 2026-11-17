"""T007 synthetic offline RED contracts for embedding validation/dry-run."""

from __future__ import annotations

import hashlib
import inspect
import math
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

import pytest
from embed_validate_fixtures import (
    COUNTER,
    TEXT,
    RecordingEnvironment,
    UnreadableEnvironment,
    ValidationFiles,
    embed_set,
    failure_line,
    forbidden_transport,
    make_chunks,
    read_json,
    records,
    refresh_text,
    replace_vectors,
    sync_report,
    tree_snapshot,
    write_json,
    write_records,
)

from sciscope.chunking import validate as chunk_validate
from sciscope.chunking.validate import Finding
from sciscope.embedding import pipeline, validate
from sciscope.embedding.cache import EmbeddingCache, cache_key
from sciscope.embedding.config import (
    PRICE_USD_PER_MILLION_TOKENS,
    EmbeddingConfig,
    build_passage_input,
)
from sciscope.embedding.pipeline import DryRunStats, run_dry_run
from sciscope.embedding.validate import validate_embedding_set
from sciscope.pipeline import cli
from sciscope.pipeline.cli import main


def _set_findings(
    files: ValidationFiles,
    *,
    allow_partial: bool = False,
    norm_tolerance: float = 0.01,
    operational_cap_tokens: int = 384,
) -> list[Finding]:
    """Call set validation without any cache, transport or environment seam."""
    return validate_embedding_set(
        records(files.path("chunks.jsonl")),
        chunks_sha256=hashlib.sha256(
            files.path("chunks.jsonl").read_bytes()
        ).hexdigest(),
        manifest=read_json(files.path("manifest.json")),
        report=read_json(files.path("embedding_report.json")),
        vectors=files.path("vectors.f32").read_bytes(),
        counter=COUNTER,
        operational_cap_tokens=operational_cap_tokens,
        norm_tolerance=norm_tolerance,
        allow_partial=allow_partial,
    )


def test_complete_set_exact_success(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T007-V20: generated fake embedding set validates with exact output."""
    files = make_chunks(tmp_path)
    embed_set(files)
    manifest = read_json(files.path("manifest.json"))
    norms = manifest["normalization"]
    capsys.readouterr()
    assert main(files.validate_args()) == 0
    assert capsys.readouterr() == (
        "validated chunks: 3 sections: 4 papers: 1 vectors: 3 "
        f"status: complete norm-min: {norms['observed_norm_min']:.9f} "
        f"norm-max: {norms['observed_norm_max']:.9f}\n",
        "",
    )


@pytest.mark.parametrize("allowed", [False, True])
def test_partial_requires_explicit_allowance(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], allowed: bool
) -> None:
    """T007-V21: an authentic nonempty subset needs --allow-partial."""
    files = make_chunks(tmp_path)
    embed_set(files, limit=1)
    capsys.readouterr()
    assert main(
        files.validate_args(*(["--allow-partial"] if allowed else []))
    ) == (0 if allowed else 1)
    console = capsys.readouterr()
    if allowed:
        assert "vectors: 1 status: partial" in console.out
        assert console.err == ""
    else:
        assert console == (
            "",
            failure_line("partial-set", "manifest") + "failures: 1\n",
        )


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("chunks_sha256", "0" * 64, "chunks-sha-mismatch"),
        ("template_version", "wrong", "set-version-mismatch"),
        ("token_counter_id", "wrong", "set-version-mismatch"),
        ("chunking_version", "wrong", "set-version-mismatch"),
        ("requested_dimensions", 3, "set-dimensions"),
        ("vectors_dtype", "float64-le", "set-dimensions"),
        ("vectors_sha256", "0" * 64, "vectors-sha-mismatch"),
    ],
)
def test_manifest_semantic_defects(
    tmp_path: Path, field: str, value: Any, code: str
) -> None:
    """T007-V22: each well-typed manifest mutation has an isolated finding."""
    files = make_chunks(tmp_path)
    embed_set(files)
    manifest = read_json(files.path("manifest.json"))
    manifest[field] = value
    write_json(files.path("manifest.json"), manifest)
    sync_report(files, manifest)
    owner = "vectors" if code.startswith("vectors-") else "manifest"
    assert _set_findings(files) == [Finding(code, 1, (owner,))]


@pytest.mark.parametrize(
    "defect", ["missing", "extra", "unsorted", "duplicate"]
)
def test_entry_set_corruptions(tmp_path: Path, defect: str) -> None:
    """T007-V23: complete entries must be sorted, unique and exactly equal."""
    files = make_chunks(tmp_path)
    embed_set(files)
    manifest = read_json(files.path("manifest.json"))
    entries = manifest["entries"]
    if defect == "missing":
        entries.pop()
    elif defect == "extra":
        entries.append({"chunk_id": "f" * 64, "input_sha256": "0" * 64})
    elif defect == "unsorted":
        entries.reverse()
    else:
        entries[1] = dict(entries[0])
    write_json(files.path("manifest.json"), manifest)
    assert Finding("set-chunk-mismatch", 1, ("manifest",)) in _set_findings(
        files
    )


@pytest.mark.parametrize("defect", ["empty", "wrong-count", "foreign-id"])
def test_allowed_partial_still_checks_subset_and_count(
    tmp_path: Path, defect: str
) -> None:
    """T007-V24: --allow-partial never bypasses subset/count validation."""
    files = make_chunks(tmp_path)
    embed_set(files, limit=1)
    manifest = read_json(files.path("manifest.json"))
    if defect == "empty":
        manifest["entries"] = []
    elif defect == "wrong-count":
        manifest["vector_count"] = 2
    else:
        manifest["entries"][0]["chunk_id"] = "f" * 64
    write_json(files.path("manifest.json"), manifest)
    sync_report(files, manifest)
    assert Finding("set-chunk-mismatch", 1, ("manifest",)) in _set_findings(
        files, allow_partial=True
    )


@pytest.mark.parametrize("defect", ["text", "prefix", "entry-hash"])
def test_changed_final_input(tmp_path: Path, defect: str) -> None:
    """T007-V25: rebuilt input hashes detect changed text, prefix or digest."""
    files = make_chunks(tmp_path)
    embed_set(files)
    manifest = read_json(files.path("manifest.json"))
    rows = records(files.path("chunks.jsonl"))
    if defect == "text":
        refresh_text(rows[0], TEXT.replace("amber", "umber"))
        write_records(files.path("chunks.jsonl"), rows)
        affected = (rows[0]["chunk_id"],)
    elif defect == "prefix":
        manifest["passage_prefix"] = "Synthetic prefix: "
        affected = tuple(entry["chunk_id"] for entry in manifest["entries"])
    else:
        manifest["entries"][0]["input_sha256"] = "0" * 64
        affected = (manifest["entries"][0]["chunk_id"],)
    write_json(files.path("manifest.json"), manifest)
    findings = _set_findings(files)
    assert Finding("set-input-mismatch", len(affected), affected) in findings
    if defect == "text":
        assert Finding("chunks-sha-mismatch", 1, ("manifest",)) in findings


def test_full_validation_collects_chunk_and_set_defects(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T007-V26: a chunk text defect cannot suppress embedding-set checks."""
    files = make_chunks(tmp_path)
    embed_set(files)
    rows = records(files.path("chunks.jsonl"))
    refresh_text(rows[0], TEXT.replace("amber", "umber"))
    write_records(files.path("chunks.jsonl"), rows)
    capsys.readouterr()
    assert main(files.validate_args()) == 1
    assert capsys.readouterr() == (
        "",
        failure_line("chunk-text-mismatch", rows[0]["chunk_id"])
        + failure_line("chunks-sha-mismatch", "manifest")
        + failure_line("set-input-mismatch", rows[0]["chunk_id"])
        + "failures: 3\n",
    )


def test_set_recomputes_input_cap(tmp_path: Path) -> None:
    """T007-V27: rebuilt final passage estimates enforce the requested cap."""
    files = make_chunks(tmp_path)
    embed_set(files)
    manifest = read_json(files.path("manifest.json"))
    ids = tuple(entry["chunk_id"] for entry in manifest["entries"])
    assert _set_findings(files, operational_cap_tokens=1) == [
        Finding("set-input-over-cap", 3, ids)
    ]


@pytest.mark.parametrize("defect", ["truncated", "flipped"])
def test_vector_bytes_integrity(tmp_path: Path, defect: str) -> None:
    """T007-V28: vector size and checksum are independently recomputed."""
    files = make_chunks(tmp_path)
    embed_set(files)
    path = files.path("vectors.f32")
    raw = path.read_bytes()
    if defect == "truncated":
        path.write_bytes(raw[:-1])
        assert Finding("vectors-size", 1, ("vectors",)) in _set_findings(files)
    else:
        path.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
    assert Finding("vectors-sha-mismatch", 1, ("vectors",)) in _set_findings(
        files
    )


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_float32_must_be_finite(tmp_path: Path, value: float) -> None:
    """T007-V29: checksum-correct NaN/Infinity rows are semantic failures."""
    files = make_chunks(tmp_path)
    embed_set(files)
    values = [1.0, 0.0] * 3
    values[0] = value
    replace_vectors(files, values)
    assert Finding("vectors-nonfinite", 1, ("vectors",)) in _set_findings(files)


@pytest.mark.parametrize(
    ("norm", "tolerance", "valid"),
    [
        (1.009, 0.01, True),
        (1.011, 0.01, False),
        (1.011, 0.02, True),
        (1.009, 0.005, False),
    ],
)
def test_empirical_norm_tolerance(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    norm: float,
    tolerance: float,
    valid: bool,
) -> None:
    """T007-V30: float32 row norms obey default and explicit tolerance."""
    files = make_chunks(tmp_path)
    embed_set(files)
    replace_vectors(files, [norm, 0.0, 1.0, 0.0, 1.0, 0.0])
    manifest = read_json(files.path("manifest.json"))
    findings = _set_findings(files, norm_tolerance=tolerance)
    expected = (
        []
        if valid
        else [
            Finding(
                "vector-norm-out-of-tolerance",
                1,
                (manifest["entries"][0]["chunk_id"],),
            )
        ]
    )
    assert findings == expected
    capsys.readouterr()
    assert main(files.validate_args("--norm-tolerance", str(tolerance))) == (
        0 if valid else 1
    )


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("observed_norm_min", 0.5, "normalization-mismatch"),
        ("observed_norm_max", 1.5, "normalization-mismatch"),
        ("declared", "none", "normalization-unsupported"),
    ],
)
def test_normalization_observations(
    tmp_path: Path, field: str, value: Any, code: str
) -> None:
    """T007-V31: declared mode and rounded observations are checked."""
    files = make_chunks(tmp_path)
    embed_set(files)
    manifest = read_json(files.path("manifest.json"))
    manifest["normalization"][field] = value
    write_json(files.path("manifest.json"), manifest)
    assert _set_findings(files) == [Finding(code, 1, ("manifest",))]


@pytest.mark.parametrize("defect", ["shared-key", "papers", "cost", "label"])
def test_report_manifest_consistency(tmp_path: Path, defect: str) -> None:
    """T007-V32: report shares manifest facts and recomputed paper/cost data."""
    files = make_chunks(tmp_path)
    embed_set(files)
    path = files.path("embedding_report.json")
    report = read_json(path)
    if defect == "shared-key":
        report["model"] = "synthetic-wrong-model"
    elif defect == "papers":
        report["paper_count"] += 1
    elif defect == "cost":
        report["approximate_cost"]["usd"] = 1.0
    else:
        report["approximate_cost"]["label"] = "exact"
    write_json(path, report)
    assert _set_findings(files) == [
        Finding("report-manifest-mismatch", 1, ("report",))
    ]


def test_calibration_aggregate_failure(tmp_path: Path) -> None:
    """T007-V33: usage beyond aggregate estimate rejects calibration."""
    files = make_chunks(tmp_path)
    embed_set(files)
    manifest = read_json(files.path("manifest.json"))
    manifest["estimated_input_tokens"] = manifest["usage"]["total_tokens"] - 1
    write_json(files.path("manifest.json"), manifest)
    sync_report(files, manifest)
    assert _set_findings(files) == [
        Finding("calibration-exceeded", 1, ("manifest",))
    ]


@pytest.mark.parametrize("artifact", ["manifest.json", "embedding_report.json"])
@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("cache_hits", 1),
        ("cache_misses", 1),
        ("api_calls", 1),
        ("retries", 1),
        ("x-ratelimit-limit-tokens", 42),
        ("base_url", "https://synthetic.invalid"),
        ("absolute_path", "C:\\synthetic\\secret"),
        ("notes", "/synthetic/private/path"),
    ],
)
def test_report_purity(
    tmp_path: Path, artifact: str, key: str, value: Any
) -> None:
    """T007-V34: forbidden runtime/URL/path keys and values are detected."""
    files = make_chunks(tmp_path)
    embed_set(files)
    row = read_json(files.path(artifact))
    row[key] = value
    write_json(files.path(artifact), row)
    owner = "manifest" if artifact == "manifest.json" else "report"
    assert Finding("report-impure", 1, (owner,)) in _set_findings(files)


@pytest.mark.parametrize(
    "artifact", ["manifest.json", "embedding_report.json", "chunk_report.json"]
)
@pytest.mark.parametrize(
    "defect", ["missing", "json", "utf8", "fields", "types"]
)
def test_set_structural_failures(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    artifact: str,
    defect: str,
) -> None:
    """T007-V35: malformed/unreadable exact-schema artifacts return 2."""
    files = make_chunks(tmp_path)
    embed_set(files)
    path = files.path(artifact)
    if defect == "missing":
        path.unlink()
    elif defect == "json":
        path.write_bytes(b"{bad}")
    elif defect == "utf8":
        path.write_bytes(b"\xff")
    else:
        row = read_json(path)
        if defect == "fields":
            row["unexpected"] = 0
        elif artifact == "chunk_report.json":
            row["summary"]["chunk_count"] = False
        else:
            row["vector_count"] = False
        write_json(path, row)
    capsys.readouterr()
    assert main(files.validate_args()) == 2
    console = capsys.readouterr()
    assert console.out == ""
    assert console.err.startswith("error: ")
    for forbidden in (TEXT, str(tmp_path), "https://"):
        assert forbidden not in console.err


def test_validate_has_no_environment_transport_or_cache_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T007-V36: complete validation works after cache deletion with spies."""
    files = make_chunks(tmp_path)
    embed_set(files)
    shutil.rmtree(files.path("cache"))

    def forbidden_cache(*args: object, **kwargs: object) -> None:
        raise AssertionError("Cache used by validate")

    monkeypatch.setattr(EmbeddingCache, "get", forbidden_cache)
    monkeypatch.setattr(EmbeddingCache, "__init__", forbidden_cache)
    before = tree_snapshot(tmp_path)
    recording = RecordingEnvironment()
    with monkeypatch.context() as guard:
        guard.setattr(os, "environ", recording)
        assert (
            main(
                files.validate_args(),
                environ=UnreadableEnvironment(),
                transport_factory=forbidden_transport,
            )
            == 0
        )
    assert not any(
        key.upper().startswith("OPENAI") for key in recording.accessed_keys
    )
    assert tree_snapshot(tmp_path) == before


@pytest.mark.parametrize(
    "value", ["0", "-0.01", "1.5", "NaN", "Infinity", "text"]
)
def test_invalid_norm_tolerance(
    capsys: pytest.CaptureFixture[str], value: str
) -> None:
    """T007-V37: reject invalid tolerance before reading input/environment."""
    assert (
        main(
            ["validate", "--norm-tolerance", value],
            environ=UnreadableEnvironment(),
            transport_factory=forbidden_transport,
        )
        == 2
    )
    assert capsys.readouterr() == ("", "error: invalid-norm-tolerance\n")


def _expected_dry_line(
    files: ValidationFiles, *, limit: int | None, cached: set[str]
) -> tuple[str, tuple[int, int, int, int, int, int, int, float]]:
    """Compute preview oracle independently from exact final input bytes."""
    rows = records(files.path("chunks.jsonl"))
    selected = rows[:limit]
    unique = {}
    for row in selected:
        text = build_passage_input(
            EmbeddingConfig(dimensions=2),
            tuple(row["section_path"]),
            row["text"],
        )
        unique[hashlib.sha256(text.encode()).hexdigest()] = COUNTER.count(text)
    hits = len(unique.keys() & cached)
    estimate = sum(unique.values())
    send = sum(value for key, value in unique.items() if key not in cached)
    cost = send * PRICE_USD_PER_MILLION_TOKENS / 1_000_000
    values = (
        len(rows),
        len(selected),
        len(unique),
        hits,
        len(unique) - hits,
        estimate,
        send,
        cost,
    )
    return (
        f"dry-run chunks: {len(rows)} selected: {len(selected)} "
        f"unique-inputs: {len(unique)} cache-hits: {hits} "
        f"cache-misses: {len(unique) - hits} "
        f"estimated-input-tokens: {estimate} "
        f"estimated-tokens-to-send: {send} approximate-cost-usd: {cost:.6f} "
        "basis: estimator-based approximate\n",
        values,
    )


@pytest.mark.parametrize("warmth", ["cold", "partial", "warm"])
@pytest.mark.parametrize("limit", [None, 1, 2])
def test_dry_run_exact_cost_cache_and_zero_writes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    warmth: str,
    limit: int | None,
) -> None:
    """T007-V38: preview deduplicates and prices only misses without writes."""
    files = make_chunks(tmp_path)
    if warmth != "cold":
        embed_set(files, limit=1 if warmth == "partial" else None)
    cached = (
        {
            read_json(files.path("manifest.json"))["entries"][i]["input_sha256"]
            for i in range(1 if warmth == "partial" else 3)
        }
        if warmth != "cold"
        else set()
    )
    expected, values = _expected_dry_line(files, limit=limit, cached=cached)
    before = tree_snapshot(tmp_path)

    def forbidden_write(*args: object, **kwargs: object) -> Any:
        raise AssertionError("Dry-run attempted a write")

    capsys.readouterr()
    extra = ["--dry-run"]
    if limit is not None:
        extra.extend(["--limit", str(limit)])
    recording = RecordingEnvironment()
    with monkeypatch.context() as guard:
        guard.setattr(os, "environ", recording)
        guard.setattr(Path, "write_bytes", forbidden_write)
        guard.setattr(Path, "write_text", forbidden_write)
        guard.setattr(Path, "mkdir", forbidden_write)
        guard.setattr(EmbeddingCache, "put_batch", forbidden_write)
        guard.setattr(tempfile, "NamedTemporaryFile", forbidden_write)
        guard.setattr(os, "replace", forbidden_write)
        assert (
            main(
                files.embed_args(*extra),
                environ=UnreadableEnvironment(),
                transport_factory=forbidden_transport,
            )
            == 0
        )
        assert capsys.readouterr() == (expected, "")
        assert run_dry_run(
            files.options(limit), EmbeddingConfig(dimensions=2), COUNTER
        ) == DryRunStats(*values)
    assert not any(
        key.upper().startswith("OPENAI") for key in recording.accessed_keys
    )
    assert tree_snapshot(tmp_path) == before
    if warmth == "cold":
        assert not files.path("cache").exists()
    if warmth == "warm":
        assert "estimated-tokens-to-send: 0" in expected
        assert "approximate-cost-usd: 0.000000" in expected


def test_corrupt_cache_dry_run_is_read_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T007-V39: corrupt read-only cache reports its key without repair."""
    files = make_chunks(tmp_path)
    embed_set(files)
    row = records(files.path("chunks.jsonl"))[0]
    config = EmbeddingConfig(dimensions=2)
    text = build_passage_input(config, tuple(row["section_path"]), row["text"])
    key = cache_key(config.model, 2, hashlib.sha256(text.encode()).hexdigest())
    files.path("cache").joinpath(key + ".entry").write_bytes(b"corrupt")
    before = tree_snapshot(tmp_path)
    capsys.readouterr()
    assert (
        main(
            files.embed_args("--dry-run"),
            environ=UnreadableEnvironment(),
            transport_factory=forbidden_transport,
        )
        == 1
    )
    assert capsys.readouterr() == (
        "",
        f"error: cache-entry-corrupt\nentry: {key}\n",
    )
    assert tree_snapshot(tmp_path) == before


@pytest.mark.parametrize(
    "cap_flag", ["--operational-cap-tokens", "--max-tokens-per-request"]
)
def test_over_cap_dry_run_has_no_side_effects(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    cap_flag: str,
) -> None:
    """T007-V40: either overflow check fails before cache reads or writes."""
    files = make_chunks(tmp_path)
    before = tree_snapshot(tmp_path)

    def forbidden_cache(*args: object, **kwargs: object) -> None:
        raise AssertionError("Overflow accessed cache")

    monkeypatch.setattr(EmbeddingCache, "get", forbidden_cache)
    capsys.readouterr()
    assert (
        main(
            files.embed_args("--dry-run", cap_flag, "1"),
            environ=UnreadableEnvironment(),
            transport_factory=forbidden_transport,
        )
        == 2
    )
    assert capsys.readouterr() == ("", "error: input-over-cap\n")
    assert tree_snapshot(tmp_path) == before
    assert not files.path("cache").exists()


@pytest.mark.parametrize(
    ("flags", "code"),
    [(["--dry-run", "--live"], "dry-run-with-live"), ([], "live-not-selected")],
)
def test_offline_selection_guards(
    capsys: pytest.CaptureFixture[str], flags: list[str], code: str
) -> None:
    """T007-V41: selection conflicts and absent selection need no key."""
    assert (
        main(
            ["embed", *flags],
            environ=UnreadableEnvironment(),
            transport_factory=forbidden_transport,
        )
        == 2
    )
    assert capsys.readouterr() == ("", f"error: {code}\n")


def test_dry_run_rebuilds_configured_prefix(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T007-V42: prefix changes estimates and makes prior exact-inputs miss."""
    files = make_chunks(tmp_path)
    embed_set(files)
    prefix = "Synthetic passage: "
    config = EmbeddingConfig(dimensions=2, passage_prefix=prefix)
    rows = records(files.path("chunks.jsonl"))
    unique = {
        build_passage_input(config, tuple(row["section_path"]), row["text"])
        for row in rows
    }
    estimate = sum(COUNTER.count(text) for text in unique)
    cost = estimate * PRICE_USD_PER_MILLION_TOKENS / 1_000_000
    before = tree_snapshot(tmp_path)
    capsys.readouterr()
    assert (
        main(
            files.embed_args("--dry-run", "--passage-prefix", prefix),
            environ=UnreadableEnvironment(),
            transport_factory=forbidden_transport,
        )
        == 0
    )
    assert capsys.readouterr() == (
        "dry-run chunks: 3 selected: 3 unique-inputs: 2 cache-hits: 0 "
        f"cache-misses: 2 estimated-input-tokens: {estimate} "
        f"estimated-tokens-to-send: {estimate} "
        f"approximate-cost-usd: {cost:.6f} "
        "basis: estimator-based approximate\n",
        "",
    )
    assert tree_snapshot(tmp_path) == before


@pytest.mark.parametrize("defect", ["missing", "unreadable"])
def test_vector_file_read_failures(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    defect: str,
) -> None:
    """T007-V43: missing or unreadable binary input returns sanitized 2."""
    files = make_chunks(tmp_path)
    embed_set(files)
    original = Path.read_bytes

    def read(path: Path) -> bytes:
        if path == files.path("vectors.f32"):
            if defect == "missing":
                raise FileNotFoundError(str(tmp_path))
            raise PermissionError(str(tmp_path))
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", read)
    capsys.readouterr()
    assert main(files.validate_args()) == 2
    console = capsys.readouterr()
    assert console.out == ""
    assert console.err.startswith("error: ")
    assert str(tmp_path) not in console.err


def test_validation_failure_output_is_deterministic_and_sanitized(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T007-V44: set findings are sorted, aggregated and repeatably safe."""
    files = make_chunks(tmp_path)
    embed_set(files)
    manifest = read_json(files.path("manifest.json"))
    manifest["vectors_sha256"] = "0" * 64
    manifest["normalization"]["declared"] = "none"
    write_json(files.path("manifest.json"), manifest)
    capsys.readouterr()
    output = []
    for _ in range(2):
        assert main(files.validate_args()) == 1
        output.append(capsys.readouterr())
    assert (
        output[0]
        == output[1]
        == (
            "",
            failure_line("normalization-unsupported", "manifest")
            + failure_line("vectors-sha-mismatch", "vectors")
            + "failures: 2\n",
        )
    )
    for forbidden in (TEXT, str(tmp_path), "https://", "jats:"):
        assert forbidden not in output[0].err


def test_offline_functions_have_no_environment_access() -> None:
    """T007-V45: offline function sources exclude environment access seams."""
    for function in (
        cli._validate,
        cli._dry_run,
        pipeline.run_dry_run,
        validate.validate_embedding_set,
        chunk_validate.validate_chunks,
    ):
        assert (
            re.search(
                r"\benviron\b|os\.environ|getenv", inspect.getsource(function)
            )
            is None
        )
