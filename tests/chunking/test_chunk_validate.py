"""T007 synthetic offline RED contracts for independent chunk validation."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from sciscope.chunking.loader import load_sources
from sciscope.chunking.validate import (
    Finding,
    load_chunk_records,
    validate_chunks,
)
from sciscope.pipeline.cli import main
from tests.embedding.embed_validate_fixtures import (
    COUNTER,
    TEXT,
    ValidationFiles,
    failure_line,
    make_chunks,
    read_json,
    records,
    refresh_identity,
    refresh_text,
    write_json,
    write_records,
)


def _validate(files: ValidationFiles) -> list[Finding]:
    """Call the independent validator with loaded sources and raw records."""
    sources = load_sources(
        files.path("sections.jsonl"),
        files.path("paragraphs.jsonl"),
        files.path("parse_report.json"),
    )
    return validate_chunks(
        sources,
        records(files.path("chunks.jsonl")),
        COUNTER,
        operational_cap_tokens=384,
        chunk_report=read_json(files.path("chunk_report.json")),
    )


def test_valid_chunks_exact_console(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T007-V01: authentic synthetic chunks pass with one exact line."""
    files = make_chunks(tmp_path)
    capsys.readouterr()
    assert main(files.validate_args("--chunks-only")) == 0
    assert capsys.readouterr() == (
        "validated chunks: 3 sections: 4 papers: 1\n",
        "",
    )


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("chunk_kind", "caption", "chunk-kind-mismatch"),
        ("chunk_id", "0" * 64, "chunk-id-mismatch"),
        ("text_sha256", "0" * 64, "chunk-hash-mismatch"),
        ("chunking_version", "wrong", "chunk-version-mismatch"),
        ("token_counter_id", "wrong", "chunk-version-mismatch"),
        ("template_version", "wrong", "chunk-version-mismatch"),
        ("xml_sha256", "b" * 64, "chunk-section-mismatch"),
        ("normalized_type", "other", "chunk-section-mismatch"),
        ("section_path", ["Invented wrong heading"], "chunk-section-mismatch"),
        ("source_locator", "wrong", "chunk-source-mismatch"),
        ("omitted", [], "chunk-omitted-mismatch"),
        ("content_tokens", 999, "chunk-token-mismatch"),
    ],
)
def test_chunk_record_defects_are_isolated(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    field: str,
    value: Any,
    code: str,
) -> None:
    """T007-V02: each record mutation yields exactly one code and ID."""
    files = make_chunks(tmp_path)
    rows = records(files.path("chunks.jsonl"))
    rows[0][field] = value
    if field == "chunking_version":
        refresh_identity(rows[0])
    write_records(files.path("chunks.jsonl"), rows)
    assert _validate(files) == [Finding(code, 1, (rows[0]["chunk_id"],))]
    capsys.readouterr()
    assert main(files.validate_args("--chunks-only")) == 1
    assert capsys.readouterr() == (
        "",
        failure_line(code, rows[0]["chunk_id"]) + "failures: 1\n",
    )


@pytest.mark.parametrize("defect", ["character", "swapped", "edge-space"])
def test_chunk_text_must_equal_source(tmp_path: Path, defect: str) -> None:
    """T007-V03: hash-correct changed/swapped/untrimmed text is rejected."""
    files = make_chunks(tmp_path)
    rows = records(files.path("chunks.jsonl"))
    text = {
        "character": TEXT.replace("amber", "umber"),
        "swapped": rows[1]["text"],
        "edge-space": " " + TEXT,
    }[defect]
    refresh_text(rows[0], text)
    write_records(files.path("chunks.jsonl"), rows)
    assert _validate(files) == [
        Finding("chunk-text-mismatch", 1, (rows[0]["chunk_id"],))
    ]


@pytest.mark.parametrize("field", ["summary", "paper", "hard-split", "type"])
def test_stale_chunk_report(tmp_path: Path, field: str) -> None:
    """T007-V04: public report totals are independently recomputed."""
    files = make_chunks(tmp_path)
    report = read_json(files.path("chunk_report.json"))
    if field == "summary":
        report["summary"]["chunk_count"] += 1
    elif field == "paper":
        report["papers"][0]["chunk_count"] += 1
    elif field == "hard-split":
        report["summary"]["hard_split_chunks"] += 1
    else:
        report["summary"]["chunks_by_normalized_type"]["other"] += 1
    write_json(files.path("chunk_report.json"), report)
    assert _validate(files) == [
        Finding("chunk-report-mismatch", 1, ("report",))
    ]


@pytest.mark.parametrize("defect", ["ordinal-gap", "reordered-file"])
def test_chunk_order(tmp_path: Path, defect: str) -> None:
    """T007-V05: check ordinals and F002 section order independently."""
    files = make_chunks(tmp_path)
    rows = records(files.path("chunks.jsonl"))
    if defect == "ordinal-gap":
        rows[0]["ordinal"] = 2
        refresh_identity(rows[0])
        expected_id = rows[0]["chunk_id"]
    else:
        rows[0], rows[1] = rows[1], rows[0]
        expected_id = rows[1]["chunk_id"]
    write_records(files.path("chunks.jsonl"), rows)
    findings = _validate(files)
    assert findings == [Finding("chunk-order", 1, (expected_id,))]


@pytest.mark.parametrize("edge", ["negative", "past-end", "empty"])
def test_span_bounds(tmp_path: Path, edge: str) -> None:
    """T007-V06: source offsets are bounded nonempty code-point ranges."""
    files = make_chunks(tmp_path)
    rows = records(files.path("chunks.jsonl"))
    span = rows[0]["spans"][0]
    if edge == "negative":
        span["start"] = -1
    elif edge == "past-end":
        span["end"] += 1
    else:
        span["end"] = span["start"]
    refresh_identity(rows[0])
    write_records(files.path("chunks.jsonl"), rows)
    findings = _validate(files)
    assert Finding("span-bounds", 1, (rows[0]["chunk_id"],)) in findings


@pytest.mark.parametrize(
    ("defect", "code"),
    [
        ("dropped-span", "coverage-missing"),
        ("nonblank-gap", "coverage-gap"),
        ("trailing-gap", "coverage-gap"),
        ("other-type-gap", "coverage-gap"),
        ("overlap", "span-overlap"),
        ("other-section", "section-isolation"),
        ("wrong-index", "section-isolation"),
        ("unknown-section", "chunk-unknown-section"),
        ("blank-span", "chunk-in-empty-section"),
        ("empty-section", "chunk-in-empty-section"),
    ],
)
def test_coverage_and_ownership_defects(
    tmp_path: Path, defect: str, code: str
) -> None:
    """T007-V07: coverage and ownership failures survive collect-all checks."""
    files = make_chunks(tmp_path)
    rows = records(files.path("chunks.jsonl"))
    row = rows[1] if defect == "other-type-gap" else rows[0]
    if defect == "dropped-span":
        row["spans"] = []
    elif defect in ("nonblank-gap", "other-type-gap"):
        row["spans"][0]["start"] = 1
        refresh_text(row, row["text"][1:])
    elif defect == "trailing-gap":
        row["spans"][0]["end"] -= 1
        refresh_text(row, row["text"][:-1])
    elif defect == "overlap":
        row["spans"].append(copy.deepcopy(row["spans"][0]))
    elif defect == "other-section":
        row["spans"][0] = copy.deepcopy(rows[1]["spans"][0])
        row["source_locator"] = row["spans"][0]["source_locator"]
    elif defect == "unknown-section":
        row["section_id"] = "unknown"
    elif defect == "wrong-index":
        row["spans"][0]["paragraph_index"] = 2
    else:
        row["section_id"] = "s4"
        locator = row["source_locator"].replace("sec[1]", "sec[4]")
        row["source_locator"] = locator
        row["spans"][0]["source_locator"] = locator
        row["spans"][0]["end"] = 1
        if defect == "empty-section":
            sources = records(files.path("sections.jsonl"))
            paragraphs = records(files.path("paragraphs.jsonl"))
            sources[-1]["paragraph_count"] = 0
            write_records(files.path("sections.jsonl"), sources)
            write_records(files.path("paragraphs.jsonl"), paragraphs[:-1])
            report = read_json(files.path("parse_report.json"))
            report["papers"][0]["paragraph_count"] -= 1
            write_json(files.path("parse_report.json"), report)
    refresh_identity(row)
    write_records(files.path("chunks.jsonl"), rows)
    matching = [finding for finding in _validate(files) if finding.code == code]
    assert matching == [Finding(code, 1, (row["chunk_id"],))]


def test_chunk_input_cap(tmp_path: Path) -> None:
    """T007-V08: final heading input, rather than stored tokens, sets cap."""
    files = make_chunks(tmp_path)
    sources = load_sources(
        files.path("sections.jsonl"),
        files.path("paragraphs.jsonl"),
        files.path("parse_report.json"),
    )
    rows = records(files.path("chunks.jsonl"))
    findings = validate_chunks(
        sources,
        rows,
        COUNTER,
        operational_cap_tokens=1,
        chunk_report=read_json(files.path("chunk_report.json")),
    )
    assert findings == [
        Finding("chunk-over-cap", 3, tuple(row["chunk_id"] for row in rows))
    ]


def test_collect_all_sorted_deterministic_sanitized(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T007-V09: simultaneous defects produce sorted safe repeatable lines."""
    files = make_chunks(tmp_path)
    rows = records(files.path("chunks.jsonl"))
    rows[0]["text_sha256"] = "0" * 64
    rows[1]["content_tokens"] += 1
    write_records(files.path("chunks.jsonl"), rows)
    capsys.readouterr()
    outputs = []
    for _ in range(2):
        assert main(files.validate_args("--chunks-only")) == 1
        outputs.append(capsys.readouterr())
    assert (
        outputs[0]
        == outputs[1]
        == (
            "",
            failure_line("chunk-hash-mismatch", rows[0]["chunk_id"])
            + failure_line("chunk-token-mismatch", rows[1]["chunk_id"])
            + "failures: 2\n",
        )
    )
    for forbidden in (TEXT, str(tmp_path), "https://", "jats:"):
        assert forbidden not in outputs[0].out + outputs[0].err


@pytest.mark.parametrize(
    "defect",
    [
        "bad-json",
        "field-set",
        "field-type",
        "span-type",
        "invalid-utf8",
        "missing",
        "source-input",
        "source-consistency",
    ],
)
def test_chunk_structural_and_f002_statuses(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], defect: str
) -> None:
    """T007-V10: malformed input is status 2; F002 inconsistency is 1."""
    files = make_chunks(tmp_path)
    path = files.path("chunks.jsonl")
    if defect == "bad-json":
        path.write_bytes(b"{bad}\n")
    elif defect == "invalid-utf8":
        path.write_bytes(b"\xff\n")
    elif defect == "missing":
        path.unlink()
    elif defect.startswith("source-"):
        source = files.path("sections.jsonl")
        if defect == "source-input":
            source.write_bytes(b"{bad}\n")
        else:
            rows = records(source)
            rows[0]["paragraph_count"] += 1
            write_records(source, rows)
    else:
        rows = records(path)
        if defect == "field-set":
            rows[0].pop("hard_split")
        elif defect == "field-type":
            rows[0]["hard_split"] = 1
        else:
            rows[0]["spans"][0]["start"] = False
        write_records(path, rows)
    capsys.readouterr()
    expected = 1 if defect == "source-consistency" else 2
    assert main(files.validate_args("--chunks-only")) == expected
    console = capsys.readouterr()
    assert console.out == ""
    assert console.err.startswith("error: ")
    assert TEXT not in console.err
    assert str(tmp_path) not in console.err


@pytest.mark.parametrize("ending", ["lf", "crlf", "no-final-lf"])
def test_unicode_lf_only_full_reader(tmp_path: Path, ending: str) -> None:
    """T007-V11: raw U+2028/U+2029/U+0085 remain in each JSON record."""
    text = "Synthetic\u2028amber\u2029waits\u0085quietly."
    files = make_chunks(tmp_path, text=text)
    path = files.path("chunks.jsonl")
    raw = path.read_bytes()
    if ending == "crlf":
        raw = raw.replace(b"\n", b"\r\n")
    elif ending == "no-final-lf":
        raw = raw.removesuffix(b"\n")
    path.write_bytes(raw)
    loaded = load_chunk_records(path)
    assert loaded.records[0]["text"] == text
    assert len(loaded.records) == 3
    assert main(files.validate_args("--chunks-only")) == 0


def test_validator_does_not_call_chunker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T007-V12: validation independently checks the persisted file."""
    files = make_chunks(tmp_path)

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Chunker used by validator")

    monkeypatch.setattr("sciscope.chunking.core.chunk_sections", forbidden)
    monkeypatch.setattr("sciscope.pipeline.cli.chunk_sections", forbidden)
    assert _validate(files) == []


@pytest.mark.parametrize("gap", ["   ", " amber "])
def test_internal_source_gap_is_reconstructed_exactly(
    tmp_path: Path, gap: str
) -> None:
    """T007-V13: exact text reconstruction cannot conceal a coverage gap."""
    text = "Synthetic turns." + gap + "Synthetic waits."
    files = make_chunks(tmp_path, text=text)
    rows = records(files.path("chunks.jsonl"))
    row = rows[0]
    first = row["spans"][0]
    first["end"] = len("Synthetic turns.")
    row["spans"].append(
        {
            **first,
            "start": first["end"] + len(gap),
            "end": len(text),
        }
    )
    refresh_identity(row)
    write_records(files.path("chunks.jsonl"), rows)
    expected = (
        []
        if gap.isspace()
        else [Finding("coverage-gap", 1, (row["chunk_id"],))]
    )
    assert _validate(files) == expected


@pytest.mark.parametrize("separator", ["\n\n", " "])
def test_different_paragraphs_require_double_lf(
    tmp_path: Path, separator: str
) -> None:
    """T007-V14: paragraph joins use exactly two LF characters."""
    files = make_chunks(tmp_path)
    paragraphs = records(files.path("paragraphs.jsonl"))
    paragraphs.insert(
        1,
        {
            **paragraphs[0],
            "paragraph_index": 2,
            "source_locator": paragraphs[0]["source_locator"][:-2] + "2]",
            "text": "Synthetic silver pauses.",
        },
    )
    sections = records(files.path("sections.jsonl"))
    sections[0]["paragraph_count"] = 2
    report = read_json(files.path("parse_report.json"))
    report["papers"][0]["paragraph_count"] += 1
    write_records(files.path("sections.jsonl"), sections)
    write_records(files.path("paragraphs.jsonl"), paragraphs)
    write_json(files.path("parse_report.json"), report)
    assert main(files.chunk_args()) == 0
    rows = records(files.path("chunks.jsonl"))
    assert len(rows[0]["spans"]) == 2
    refresh_text(rows[0], separator.join(p["text"] for p in paragraphs[:2]))
    write_records(files.path("chunks.jsonl"), rows)
    assert _validate(files) == (
        []
        if separator == "\n\n"
        else [Finding("chunk-text-mismatch", 1, (rows[0]["chunk_id"],))]
    )


def test_hard_split_flag_is_not_a_boundary_quality_claim(
    tmp_path: Path,
) -> None:
    """T007-V15: type-correct hard_split changes only recomputed counts."""
    files = make_chunks(tmp_path)
    rows = records(files.path("chunks.jsonl"))
    rows[0]["hard_split"] = True
    report = read_json(files.path("chunk_report.json"))
    report["summary"]["hard_split_chunks"] = 1
    report["papers"][0]["hard_split_chunks"] = 1
    write_records(files.path("chunks.jsonl"), rows)
    write_json(files.path("chunk_report.json"), report)
    assert _validate(files) == []


def test_unreadable_chunk_file_is_sanitized(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """T007-V16: a permission failure returns 2 without echoing its path."""
    files = make_chunks(tmp_path)
    original = Path.read_bytes

    def read(path: Path) -> bytes:
        if path == files.path("chunks.jsonl"):
            raise PermissionError(str(tmp_path))
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", read)
    capsys.readouterr()
    assert main(files.validate_args("--chunks-only")) == 2
    console = capsys.readouterr()
    assert console.out == ""
    assert console.err.startswith("error: ")
    assert str(tmp_path) not in console.err


def test_aggregated_count_keeps_only_first_three_ids(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T007-V17: total count includes failures after the first three IDs."""
    files = make_chunks(tmp_path)
    sections = records(files.path("sections.jsonl"))
    paragraphs = records(files.path("paragraphs.jsonl"))
    locator = sections[0]["source_locator"].replace("sec[1]", "sec[5]")
    sections.append(
        {
            **sections[0],
            "section_id": "s5",
            "source_locator": locator,
        }
    )
    paragraphs.append(
        {
            **paragraphs[0],
            "section_id": "s5",
            "source_locator": locator + "/p[1]",
        }
    )
    report = read_json(files.path("parse_report.json"))
    paper = report["papers"][0]
    paper["section_count"] += 1
    paper["paragraph_count"] += 1
    paper["normalized_type_histogram"]["methods"] += 1
    write_records(files.path("sections.jsonl"), sections)
    write_records(files.path("paragraphs.jsonl"), paragraphs)
    write_json(files.path("parse_report.json"), report)
    assert main(files.chunk_args()) == 0
    rows = records(files.path("chunks.jsonl"))
    assert len(rows) == 4
    for row in rows:
        row["text_sha256"] = "0" * 64
    write_records(files.path("chunks.jsonl"), rows)
    capsys.readouterr()
    assert main(files.validate_args("--chunks-only")) == 1
    assert capsys.readouterr() == (
        "",
        failure_line(
            "chunk-hash-mismatch", *(row["chunk_id"] for row in rows), count=4
        )
        + "failures: 4\n",
    )
