"""T004 RED tests for F002 loading, IDs, files, reports and CLI."""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

import pytest

from sciscope.chunking.config import ChunkConfig
from sciscope.chunking.core import Chunk, ChunkSpan
from sciscope.chunking.loader import (
    SourceConsistencyError,
    SourceInputError,
    load_sources,
)
from sciscope.chunking.output import (
    CHUNK_RECORD_FIELDS,
    chunk_id,
    chunk_record,
    chunk_report,
    write_chunk_files,
    write_outputs,
)
from sciscope.pipeline.cli import main

DOI = "10.0000/synthetic-a"
OTHER_DOI = "10.0000/synthetic-b"
DIGEST = "a" * 64
OTHER_DIGEST = "b" * 64
LOCATOR = f"jats:v1:{DIGEST}:/article[1]/body[1]/sec[1]/p[1]"
SECTION_LOCATOR = f"jats:v1:{DIGEST}:/article[1]/body[1]/sec[1]"
TEXT = "velnix zorvax"
HEADING = "Synthetic Velnix Heading"


def source_records() -> tuple[
    list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]
]:
    """Build one invented F002-like successful paper."""
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


def write_sources(
    tmp_path: Path,
    sections: list[dict[str, Any]],
    paragraphs: list[dict[str, Any]],
    report: dict[str, Any],
) -> tuple[Path, Path, Path]:
    """Write strict UTF-8 synthetic input files under pytest's temp root."""
    paths = (
        tmp_path / "synthetic-sections.jsonl",
        tmp_path / "synthetic-paragraphs.jsonl",
        tmp_path / "synthetic-parse-report.json",
    )
    for path, records in zip(paths[:2], (sections, paragraphs), strict=True):
        path.write_text(
            "".join(
                json.dumps(row, ensure_ascii=False) + "\n" for row in records
            ),
            encoding="utf-8",
            newline="\n",
        )
    paths[2].write_text(
        json.dumps(report, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return paths


def sample_chunk(
    *,
    spans: tuple[ChunkSpan, ...] | None = None,
    text: str = TEXT,
) -> Chunk:
    """Build a chunk aligned to the synthetic source fixture."""
    return Chunk(
        DOI,
        "s1",
        "methods",
        (HEADING,),
        1,
        text,
        spans or (ChunkSpan(LOCATOR, 1, 0, len(TEXT)),),
        5,
        False,
    )


def cli_args(paths: tuple[Path, Path, Path], tmp_path: Path) -> list[str]:
    """Select synthetic files for the chunk command."""
    return [
        "chunk",
        "--sections",
        str(paths[0]),
        "--paragraphs",
        str(paths[1]),
        "--parse-report",
        str(paths[2]),
        "--chunks",
        str(tmp_path / "synthetic-chunks.jsonl"),
        "--report",
        str(tmp_path / "synthetic-chunk-report.json"),
    ]


def test_chunk_id_is_unique_and_stable() -> None:
    """T004 RED: identical spans rerun identically; distinct spans do not."""
    spans = (ChunkSpan(LOCATOR, 1, 0, 5),)
    first = chunk_id("chunking-v1", DOI, "s1", 1, spans)
    assert first == chunk_id("chunking-v1", DOI, "s1", 1, spans)
    assert len(first) == 64 and first == first.lower()
    assert first != chunk_id(
        "chunking-v1", DOI, "s1", 1, (ChunkSpan(LOCATOR, 1, 6, 12),)
    )


@pytest.mark.parametrize(
    ("version", "doi", "section", "ordinal", "spans"),
    [
        pytest.param("chunking-v2", DOI, "s1", 1, (), id="version"),
        pytest.param("chunking-v1", OTHER_DOI, "s1", 1, (), id="doi"),
        pytest.param("chunking-v1", DOI, "s2", 1, (), id="section"),
        pytest.param("chunking-v1", DOI, "s1", 2, (), id="ordinal"),
        pytest.param(
            "chunking-v1",
            DOI,
            "s1",
            1,
            (ChunkSpan(LOCATOR, 1, 0, 6),),
            id="span-end",
        ),
        pytest.param(
            "chunking-v1",
            DOI,
            "s1",
            1,
            (ChunkSpan(LOCATOR, 1, 1, 5),),
            id="span-start",
        ),
        pytest.param(
            "chunking-v1",
            DOI,
            "s1",
            1,
            (ChunkSpan(LOCATOR + "-other", 1, 0, 5),),
            id="span-locator",
        ),
    ],
)
def test_chunk_id_changes_with_identity_field(
    version: str,
    doi: str,
    section: str,
    ordinal: int,
    spans: tuple[ChunkSpan, ...],
) -> None:
    """T004 RED: each canonical identity component affects the hash."""
    base_spans = (ChunkSpan(LOCATOR, 1, 0, 5),)
    baseline = chunk_id("chunking-v1", DOI, "s1", 1, base_spans)
    assert baseline != chunk_id(
        version, doi, section, ordinal, spans or base_spans
    )


def test_chunk_id_is_insensitive_to_text(tmp_path: Path) -> None:
    """T004 RED: chunk text changes its text hash, not its ID."""
    bundle = load_sources(*write_sources(tmp_path, *source_records()))
    spans = (ChunkSpan(LOCATOR, 1, 0, 5),)
    first = sample_chunk(spans=spans, text="velni")
    second = sample_chunk(spans=spans, text="zorva")
    first_record = chunk_record(first, bundle, "utf8-bytes-div3-v1")
    second_record = chunk_record(second, bundle, "utf8-bytes-div3-v1")
    assert first_record["chunk_id"] == second_record["chunk_id"]
    assert first_record["text_sha256"] != second_record["text_sha256"]


@pytest.mark.parametrize(
    "defect",
    [
        "duplicate-section",
        "unknown-section",
        "cross-doi-section",
        "paragraph-order",
        "section-paragraph-count",
        "section-locator-digest",
        "paragraph-locator-digest",
        "xml-report-digest",
        "doi-set",
        "failed-paper-records",
        "doi-order",
    ],
)
def test_loader_rejects_inconsistent_sources(
    tmp_path: Path, defect: str
) -> None:
    """T004 RED: each consistency defect has a sanitized distinct code."""
    sections, paragraphs, report = source_records()
    if defect == "duplicate-section":
        sections.append(copy.deepcopy(sections[0]))
    elif defect == "unknown-section":
        paragraphs[0]["section_id"] = "missing"
    elif defect == "cross-doi-section":
        paragraphs[0]["doi"] = OTHER_DOI
    elif defect == "paragraph-order":
        sections[0]["paragraph_count"] = 2
        paragraphs.append({**paragraphs[0], "paragraph_index": 0})
    elif defect == "section-paragraph-count":
        sections[0]["paragraph_count"] = 2
    elif defect == "section-locator-digest":
        sections[0]["source_locator"] = SECTION_LOCATOR.replace(
            DIGEST, OTHER_DIGEST
        )
    elif defect == "paragraph-locator-digest":
        paragraphs[0]["source_locator"] = LOCATOR.replace(DIGEST, OTHER_DIGEST)
    elif defect == "xml-report-digest":
        report["papers"][0]["xml_sha256"] = OTHER_DIGEST
    elif defect == "doi-set":
        report["papers"][0]["doi"] = OTHER_DOI
    elif defect == "failed-paper-records":
        report["papers"][0]["errors"] = ["synthetic-error"]
    elif defect == "doi-order":
        extra = copy.deepcopy(sections[0])
        extra["doi"] = OTHER_DOI
        extra["xml_sha256"] = OTHER_DIGEST
        extra["section_id"] = "s2"
        extra["source_locator"] = SECTION_LOCATOR.replace(DIGEST, OTHER_DIGEST)
        extra["paragraph_count"] = 0
        sections.insert(0, extra)
        extra_report = copy.deepcopy(report["papers"][0])
        extra_report.update(
            {
                "doi": OTHER_DOI,
                "xml_sha256": OTHER_DIGEST,
                "section_count": 1,
                "paragraph_count": 0,
            }
        )
        report["papers"].append(extra_report)
    paths = write_sources(tmp_path, sections, paragraphs, report)
    with pytest.raises(SourceConsistencyError) as error:
        load_sources(*paths)
    assert error.value.code == defect
    assert TEXT not in str(error.value)
    assert str(tmp_path) not in str(error.value)


@pytest.mark.parametrize(
    "defect",
    [
        "missing-file",
        "invalid-utf8",
        "invalid-json",
        "extra-field",
        "missing-field",
        "wrong-type",
        "report-extra-field",
    ],
)
def test_loader_rejects_invalid_input(tmp_path: Path, defect: str) -> None:
    """T004 RED: unreadable, malformed or wrong-schema input is code 2."""
    sections, paragraphs, report = source_records()
    if defect == "extra-field":
        sections[0]["unexpected"] = 1
    elif defect == "missing-field":
        del paragraphs[0]["omitted"]
    elif defect == "wrong-type":
        paragraphs[0]["paragraph_index"] = "one"
    elif defect == "report-extra-field":
        report["papers"][0]["unexpected"] = 1
    paths = write_sources(tmp_path, sections, paragraphs, report)
    if defect == "missing-file":
        paths[0].unlink()
    elif defect == "invalid-utf8":
        paths[0].write_bytes(b"\xff\n")
    elif defect == "invalid-json":
        paths[0].write_text("{bad}\n", encoding="utf-8")
    with pytest.raises(SourceInputError) as error:
        load_sources(*paths)
    assert error.value.code == defect
    assert TEXT not in str(error.value)
    assert str(tmp_path) not in str(error.value)


def test_record_field_order_and_provenance(tmp_path: Path) -> None:
    """T004 RED: chunk fields and the original F002 path have exact order."""
    bundle = load_sources(*write_sources(tmp_path, *source_records()))
    record = chunk_record(sample_chunk(), bundle, "utf8-bytes-div3-v1")
    assert tuple(record) == CHUNK_RECORD_FIELDS
    assert record["section_path"] == [HEADING]
    assert record["source_locator"] == record["spans"][0]["source_locator"]
    assert record["omitted"] == ["inline-formula"]


def test_omitted_union_across_spans(tmp_path: Path) -> None:
    """T004 RED: every contributing paragraph supplies omitted kinds."""
    sections, paragraphs, report = source_records()
    sections[0]["paragraph_count"] = 2
    paragraphs.append(
        {
            **paragraphs[0],
            "paragraph_index": 2,
            "source_locator": LOCATOR[:-2] + "2]",
            "omitted": ["disp-formula", "inline-formula"],
        }
    )
    report["papers"][0]["paragraph_count"] = 2
    bundle = load_sources(
        *write_sources(tmp_path, sections, paragraphs, report)
    )
    spans = (
        ChunkSpan(LOCATOR, 1, 0, 3),
        ChunkSpan(paragraphs[1]["source_locator"], 2, 0, 3),
    )
    record = chunk_record(
        sample_chunk(spans=spans), bundle, "utf8-bytes-div3-v1"
    )
    assert record["omitted"] == ["disp-formula", "inline-formula"]
    assert record["source_locator"] == LOCATOR


def test_rerun_bytes_are_deterministic_and_report_is_pure(
    tmp_path: Path,
) -> None:
    """T004 RED: two runs match and report excludes source content/paths."""
    bundle = load_sources(*write_sources(tmp_path, *source_records()))
    chunks_path = tmp_path / "synthetic-chunks.jsonl"
    report_path = tmp_path / "synthetic-chunk-report.json"
    args = (
        [sample_chunk()],
        bundle,
        ChunkConfig(),
        "utf8-bytes-div3-v1",
        chunks_path,
        report_path,
    )
    write_chunk_files(*args)
    first = (chunks_path.read_bytes(), report_path.read_bytes())
    write_chunk_files(*args)
    assert first == (chunks_path.read_bytes(), report_path.read_bytes())
    report_bytes = report_path.read_bytes()
    for forbidden in (TEXT, HEADING, str(tmp_path), "Invented title"):
        assert forbidden.encode() not in report_bytes
    assert report_bytes.endswith(b"\n")


def test_report_has_required_counts_and_token_statistics(
    tmp_path: Path,
) -> None:
    """T004 RED: per-paper counts and nearest-rank summary are present."""
    bundle = load_sources(*write_sources(tmp_path, *source_records()))
    report = chunk_report(
        [sample_chunk()], bundle, ChunkConfig(), "utf8-bytes-div3-v1"
    )
    paper = report["papers"][0]
    assert paper["paragraphs_with_omitted"] == 1
    assert paper["back_matter_excluded"]["references"] == 1
    assert paper["excluded_elements"]["formula"] == 1
    assert report["summary"]["content_tokens"]["p95"] == 5
    assert "final_input_estimated_tokens" in report["summary"]


def test_atomic_write_failure_keeps_previous_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T004 RED: second replacement failure restores both old files."""
    first = tmp_path / "synthetic-chunks.jsonl"
    second = tmp_path / "synthetic-report.json"
    first.write_bytes(b"old-chunks\n")
    second.write_bytes(b"old-report\n")
    original_replace = os.replace

    def fail_second_replace(source: str | Path, target: str | Path) -> None:
        if Path(target) == second:
            raise OSError("synthetic-replace-failure")
        original_replace(source, target)

    monkeypatch.setattr(os, "replace", fail_second_replace)
    with pytest.raises(OSError):
        write_outputs({first: b"new-chunks\n", second: b"new-report\n"})
    assert first.read_bytes() == b"old-chunks\n"
    assert second.read_bytes() == b"old-report\n"
    assert not list(tmp_path.glob("*.tmp"))


def test_processed_data_is_ignored_but_chunk_report_is_not() -> None:
    """T004 RED: the existing repository ignore contract is correct."""
    gitignore = (Path(__file__).resolve().parents[2] / ".gitignore").read_text(
        encoding="utf-8"
    )
    assert "data/processed/" in gitignore.splitlines()
    assert "data/pilot/chunk_report.json" not in gitignore


@pytest.mark.parametrize(
    ("defect", "exit_code"),
    [
        pytest.param("valid", 0, id="success"),
        pytest.param("inconsistent", 1, id="consistency"),
        pytest.param("chunking", 1, id="chunking-failure"),
        pytest.param("missing", 2, id="missing-file"),
        pytest.param("invalid-json", 2, id="invalid-json"),
        pytest.param("config", 2, id="invalid-config"),
    ],
)
def test_chunk_cli_exit_codes_and_sanitized_console(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    defect: str,
    exit_code: int,
) -> None:
    """T004 RED: chunk CLI uses 0/1/2 and never echoes source text."""
    sections, paragraphs, report = source_records()
    if defect == "inconsistent":
        sections[0]["paragraph_count"] = 2
    paths = write_sources(tmp_path, sections, paragraphs, report)
    if defect == "missing":
        paths[0].unlink()
    elif defect == "invalid-json":
        paths[0].write_text("{bad}\n", encoding="utf-8")
    args = cli_args(paths, tmp_path)
    if defect == "config":
        args.extend(["--operational-cap-tokens", "0"])
    elif defect == "chunking":
        args.extend(["--operational-cap-tokens", "1"])
    assert main(args) == exit_code
    console = capsys.readouterr()
    for forbidden in (TEXT, HEADING, str(tmp_path)):
        assert forbidden not in console.out + console.err
    if exit_code:
        assert console.err.startswith("error: ")
        assert not (tmp_path / "synthetic-chunks.jsonl").exists()
        assert not (tmp_path / "synthetic-chunk-report.json").exists()


def test_synthetic_end_to_end_spans_cover_nonblank_paragraphs(
    tmp_path: Path,
) -> None:
    """T004 RED: emitted spans cover source characters exactly once."""
    sections, paragraphs, report = source_records()
    sections[0]["paragraph_count"] = 2
    paragraphs.append(
        {
            **paragraphs[0],
            "paragraph_index": 2,
            "text": "  nolvix tendar  ",
            "source_locator": LOCATOR[:-2] + "2]",
            "omitted": [],
        }
    )
    report["papers"][0]["paragraph_count"] = 2
    paths = write_sources(tmp_path, sections, paragraphs, report)
    assert main(cli_args(paths, tmp_path)) == 0
    records = [
        json.loads(line)
        for line in (tmp_path / "synthetic-chunks.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    for paragraph in paragraphs:
        spans = [
            span
            for record in records
            for span in record["spans"]
            if span["source_locator"] == paragraph["source_locator"]
        ]
        covered = [
            index
            for span in spans
            for index in range(span["start"], span["end"])
            if not paragraph["text"][index].isspace()
        ]
        expected = [
            index
            for index, char in enumerate(paragraph["text"])
            if not char.isspace()
        ]
        assert covered == expected


def test_jsonl_preserves_raw_unicode_line_separators(tmp_path: Path) -> None:
    """T004 Phase 2b RED: JSON string separators remain paragraph text."""
    sections, paragraphs, report = source_records()
    text = "velnix\u2028zorvax\u2029nolvix\u0085tendar"
    paragraphs[0]["text"] = text
    bundle = load_sources(
        *write_sources(tmp_path, sections, paragraphs, report)
    )
    assert bundle.paragraphs[0].text == text


def test_chunk_cli_preserves_unicode_and_deterministic_bytes(
    tmp_path: Path,
) -> None:
    """T004 Phase 2b RED: raw separators survive chunking and reruns."""
    sections, paragraphs, report = source_records()
    paragraphs[0]["text"] = "velnix\u2028zorvax\u2029nolvix\u0085tendar"
    paths = write_sources(tmp_path, sections, paragraphs, report)
    args = cli_args(paths, tmp_path)
    assert main(args) == 0
    chunks_path = tmp_path / "synthetic-chunks.jsonl"
    report_path = tmp_path / "synthetic-chunk-report.json"
    first = (chunks_path.read_bytes(), report_path.read_bytes())
    records = [
        json.loads(line)
        for line in first[0].decode("utf-8").split("\n")
        if line
    ]
    covered = [
        index
        for record in records
        for span in record["spans"]
        for index in range(span["start"], span["end"])
        if not paragraphs[0]["text"][index].isspace()
    ]
    expected = [
        index
        for index, char in enumerate(paragraphs[0]["text"])
        if not char.isspace()
    ]
    assert covered == expected
    assert main(args) == 0
    assert first == (chunks_path.read_bytes(), report_path.read_bytes())


def test_jsonl_blank_middle_line_is_invalid(tmp_path: Path) -> None:
    """T004 Phase 2b RED: a blank record between records is invalid JSON."""
    sections, paragraphs, report = source_records()
    paths = write_sources(tmp_path, sections, paragraphs, report)
    raw = paths[1].read_bytes()
    paths[1].write_bytes(raw + b"\n" + raw)
    with pytest.raises(SourceInputError) as error:
        load_sources(*paths)
    assert error.value.code == "invalid-json"


def test_empty_jsonl_file_has_zero_records(tmp_path: Path) -> None:
    """T004 Phase 2b RED: an empty JSONL input represents no records."""
    _, _, report = source_records()
    report["papers"] = []
    report["summary"] = {"succeeded": 0, "failed": 0}
    paths = write_sources(tmp_path, [], [], report)
    bundle = load_sources(*paths)
    assert bundle.sections == ()
    assert bundle.paragraphs == ()


@pytest.mark.parametrize("line_ending", ["crlf", "no-final-lf"])
def test_jsonl_accepts_crlf_and_missing_final_lf(
    tmp_path: Path, line_ending: str
) -> None:
    """T004 Phase 2b RED: common line-ending variants still parse."""
    paths = write_sources(tmp_path, *source_records())
    for path in paths[:2]:
        raw = path.read_bytes()
        if line_ending == "crlf":
            path.write_bytes(raw.replace(b"\n", b"\r\n"))
        else:
            path.write_bytes(raw.removesuffix(b"\n"))
    bundle = load_sources(*paths)
    assert len(bundle.sections) == 1
    assert len(bundle.paragraphs) == 1


@pytest.mark.parametrize(
    "conflict", ["chunks-report", "chunks-sections", "report-parse-report"]
)
def test_chunk_cli_rejects_output_path_conflicts(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    conflict: str,
) -> None:
    """T004 Phase 2b RED: conflicting paths fail before source loading."""
    paths = write_sources(tmp_path, *source_records())
    original = tuple(path.read_bytes() for path in paths)
    chunks_path = tmp_path / "synthetic-chunks.jsonl"
    report_path = tmp_path / "synthetic-chunk-report.json"
    args = cli_args(paths, tmp_path)
    if conflict == "chunks-report":
        args[args.index("--report") + 1] = str(chunks_path)
    elif conflict == "chunks-sections":
        args[args.index("--chunks") + 1] = str(paths[0])
    else:
        args[args.index("--report") + 1] = str(paths[2])

    def unexpected_load(*_args: object) -> None:
        raise AssertionError("source files were read")

    monkeypatch.setattr("sciscope.pipeline.cli.load_sources", unexpected_load)
    assert main(args) == 2
    assert capsys.readouterr().err == "error: output-path-conflict\n"
    assert tuple(path.read_bytes() for path in paths) == original
    if conflict != "chunks-sections":
        assert not chunks_path.exists()
    if conflict != "report-parse-report":
        assert not report_path.exists()
