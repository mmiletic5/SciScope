"""SYNTHETIC file-based checks for the T006 parse command."""

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pytest

from sciscope.jats import cli, source

DOI_A = "10.9999/synthetic-a"
DOI_B = "10.9999/synthetic-b"
SECTION_KEYS = [
    "doi",
    "title",
    "xml_sha256",
    "section_id",
    "parent_section_id",
    "section_path",
    "original_heading",
    "normalized_type",
    "source_locator",
    "depth",
    "paragraph_count",
]
PARAGRAPH_KEYS = [
    "doi",
    "section_id",
    "paragraph_index",
    "text",
    "omitted",
    "source_locator",
]
REPORT_KEYS = [
    "doi",
    "xml_sha256",
    "section_count",
    "paragraph_count",
    "abstract_paragraph_count",
    "normalized_type_histogram",
    "unclassified_headings",
    "type_conflicts",
    "skipped_element_kinds",
    "back_matter_containers",
    "warnings",
    "errors",
]


def _xml(text: str = "SYNTHETIC café") -> bytes:
    """Return a small SYNTHETIC paper with abstract and body text."""
    return (
        "<article><front><article-meta><abstract><p>SYNTHETIC abstract"
        "</p></abstract></article-meta></front><body><sec><title>Results"
        f"</title><p>{text}</p></sec></body></article>"
    ).encode()


def _write_inputs(
    root: Path,
    papers: list[tuple[str, bytes]],
    *,
    bad_digests: set[str] | None = None,
    missing_files: set[str] | None = None,
    missing_metadata: set[str] | None = None,
) -> None:
    """Write only SYNTHETIC manifest, metadata, and raw XML under tmp_path."""
    raw = root / "raw"
    raw.mkdir(exist_ok=True)
    manifest = []
    metadata = []
    for index, (doi, xml_bytes) in enumerate(papers):
        name = f"paper-{index}.xml"
        if doi not in (missing_files or set()):
            (raw / name).write_bytes(xml_bytes)
        digest = hashlib.sha256(xml_bytes).hexdigest()
        if doi in (bad_digests or set()):
            digest = "0" * 64
        manifest.append(
            {"doi": doi, "xml_sha256": digest, "raw_xml_path": f"raw/{name}"}
        )
        if doi not in (missing_metadata or set()):
            metadata.append({"doi": doi, "title": f"SYNTHETIC title {index}"})
    for name, records in (
        ("manifest.jsonl", manifest),
        ("metadata.jsonl", metadata),
    ):
        (root / name).write_text(
            "".join(json.dumps(item) + "\n" for item in records),
            encoding="utf-8",
        )


def _run(root: Path) -> int:
    """Invoke the parse subcommand with all paths under tmp_path."""
    return cli.main(
        [
            "parse",
            "--repo-root",
            str(root),
            "--manifest",
            str(root / "manifest.jsonl"),
            "--metadata",
            str(root / "metadata.jsonl"),
            "--sections",
            str(root / "out" / "sections.jsonl"),
            "--paragraphs",
            str(root / "out" / "paragraphs.jsonl"),
            "--report",
            str(root / "out" / "parse_report.json"),
        ]
    )


def _outputs(
    root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Read the three SYNTHETIC output files."""
    out = root / "out"
    sections = [
        json.loads(line)
        for line in (out / "sections.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    paragraphs = [
        json.loads(line)
        for line in (out / "paragraphs.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    report = json.loads((out / "parse_report.json").read_text(encoding="utf-8"))
    return sections, paragraphs, report


def test_valid_run_writes_sorted_exact_records_and_report(
    tmp_path: Path,
) -> None:
    """SYNTHETIC papers emit complete records in DOI and key order."""
    _write_inputs(tmp_path, [(DOI_B, _xml("SYNTHETIC B")), (DOI_A, _xml())])
    assert _run(tmp_path) == 0
    sections, paragraphs, report = _outputs(tmp_path)
    assert [item["doi"] for item in report["papers"]] == [DOI_A, DOI_B]
    assert [item["doi"] for item in sections] == [DOI_A, DOI_A, DOI_B, DOI_B]
    assert [item["doi"] for item in paragraphs] == [DOI_A, DOI_A, DOI_B, DOI_B]
    assert all(list(item) == SECTION_KEYS for item in sections)
    assert all(list(item) == PARAGRAPH_KEYS for item in paragraphs)
    assert list(report) == ["papers", "summary"]
    assert all(list(item) == REPORT_KEYS for item in report["papers"])
    assert report["summary"] == {"succeeded": 2, "failed": 0}
    assert sections[0]["title"] == "SYNTHETIC title 1"
    assert sections[0]["section_path"] == ["(untitled)"]
    assert sections[0]["normalized_type"] == "abstract"
    assert sections[1]["section_id"] == f"{DOI_A}#sec-1"
    assert sections[1]["section_path"] == ["Results"]
    assert sections[1]["paragraph_count"] == 1
    assert paragraphs[1]["text"] == "SYNTHETIC café"
    assert paragraphs[1]["omitted"] == []
    assert report["papers"][0]["section_count"] == 2
    assert report["papers"][0]["paragraph_count"] == 2
    assert report["papers"][0]["abstract_paragraph_count"] == 1
    assert report["papers"][0]["normalized_type_histogram"] == {
        "abstract": 1,
        "results": 1,
    }


@pytest.mark.parametrize(
    ("bad_xml", "setup", "expected"),
    [
        (None, "digest", "digest-mismatch"),
        (None, "missing-file", "file-missing"),
        (
            b"<article><front/></article>",
            "",
            "parse-error: Article has no body",
        ),
        (None, "missing-metadata", "missing-metadata"),
        (b"<!ENTITY x 'a'>" + _xml(), "", "xml-unsafe"),
        (b"<!DOCTYPE article [ ]>" + _xml(), "", "xml-unsafe"),
        (
            b'<article xmlns:xi="http://www.w3.org/2001/XInclude"><body/></article>',
            "",
            "xml-unsafe",
        ),
        (b"\xff\xfe<\x00", "", "xml-unsafe"),
        (
            b'<?xml version="1.0" encoding="ISO-8859-1"?>' + _xml(),
            "",
            "xml-unsafe",
        ),
    ],
)
def test_one_bad_paper_does_not_block_good_paper(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    bad_xml: bytes | None,
    setup: str,
    expected: str,
) -> None:
    """SYNTHETIC per-paper failures leave good records available."""
    _write_inputs(
        tmp_path,
        [(DOI_B, _xml("SYNTHETIC good paragraph")), (DOI_A, bad_xml or _xml())],
        bad_digests={DOI_A} if setup == "digest" else None,
        missing_files={DOI_A} if setup == "missing-file" else None,
        missing_metadata={DOI_A} if setup == "missing-metadata" else None,
    )
    assert _run(tmp_path) == 1
    sections, paragraphs, report = _outputs(tmp_path)
    assert {item["doi"] for item in sections + paragraphs} == {DOI_B}
    assert report["summary"] == {"succeeded": 1, "failed": 1}
    failed = report["papers"][0]
    assert failed["doi"] == DOI_A
    assert failed["errors"] == [expected]
    assert failed["section_count"] == failed["paragraph_count"] == 0
    assert failed["abstract_paragraph_count"] == 0
    assert failed["normalized_type_histogram"] == {}
    assert failed["unclassified_headings"] == {}
    assert failed["type_conflicts"] == []
    assert failed["skipped_element_kinds"] == {}
    assert failed["back_matter_containers"] == []
    assert failed["warnings"] == []
    output = capsys.readouterr().out
    assert DOI_A in output and expected in output
    assert "SYNTHETIC good paragraph" not in output


def test_duplicate_manifest_doi_fails_every_entry(tmp_path: Path) -> None:
    """SYNTHETIC repeated DOI entries each fail without records."""
    _write_inputs(
        tmp_path, [(DOI_A, _xml()), (DOI_A, _xml("SYNTHETIC second"))]
    )
    assert _run(tmp_path) == 1
    sections, paragraphs, report = _outputs(tmp_path)
    assert sections == paragraphs == []
    assert report["summary"] == {"succeeded": 0, "failed": 2}
    assert [paper["errors"] for paper in report["papers"]] == [
        ["duplicate-manifest-doi"],
        ["duplicate-manifest-doi"],
    ]


@pytest.mark.parametrize(
    "prefix",
    [
        b'<!DOCTYPE article SYSTEM "synthetic.dtd">',
        b'<!DOCTYPE article PUBLIC "SYNTHETIC" "synthetic.dtd">',
        b'<!DOCTYPE article PUBLIC "SYNTHETIC" "synthetic[.dtd">',
    ],
)
def test_external_doctype_is_accepted(tmp_path: Path, prefix: bytes) -> None:
    """SYNTHETIC plain external DTD identifiers do not block parsing."""
    _write_inputs(tmp_path, [(DOI_A, prefix + _xml())])
    assert _run(tmp_path) == 0


def test_cli_uses_module_size_cap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SYNTHETIC size cap can be lowered for a focused offline test."""
    _write_inputs(tmp_path, [(DOI_A, _xml()), (DOI_B, _xml("SYNTHETIC " * 30))])
    monkeypatch.setattr(source, "MAX_XML_BYTES", len(_xml()))
    assert _run(tmp_path) == 1
    _, _, report = _outputs(tmp_path)
    assert report["summary"] == {"succeeded": 1, "failed": 1}
    assert report["papers"][1]["errors"] == ["xml-too-large"]


@pytest.mark.parametrize("file_name", ["manifest.jsonl", "metadata.jsonl"])
@pytest.mark.parametrize(
    "corruption", ["missing", "invalid-json", "missing-key"]
)
def test_invalid_input_exits_two_without_writing(
    tmp_path: Path, file_name: str, corruption: str
) -> None:
    """SYNTHETIC input-level errors leave outputs absent."""
    _write_inputs(tmp_path, [(DOI_A, _xml())])
    path = tmp_path / file_name
    if corruption == "missing":
        path.unlink()
    elif corruption == "invalid-json":
        path.write_text("{invalid}\n", encoding="utf-8")
    else:
        path.write_text('{"doi": "missing-fields"}\n', encoding="utf-8")
    assert _run(tmp_path) == 2
    assert not (tmp_path / "out").exists()


def test_repeated_runs_identical_utf8_lf_and_final_newline(
    tmp_path: Path,
) -> None:
    """SYNTHETIC non-ASCII output is stable UTF-8 with LF line endings."""
    _write_inputs(tmp_path, [(DOI_A, _xml())])
    assert _run(tmp_path) == 0
    out = tmp_path / "out"
    first = {path.name: path.read_bytes() for path in out.iterdir()}
    assert _run(tmp_path) == 0
    assert first == {path.name: path.read_bytes() for path in out.iterdir()}
    assert set(first) == {
        "sections.jsonl",
        "paragraphs.jsonl",
        "parse_report.json",
    }
    for content in first.values():
        assert content.endswith(b"\n")
        assert b"\r" not in content
        assert not content.startswith(b"\xef\xbb\xbf")
    assert "café".encode() in first["paragraphs.jsonl"]


def test_replace_error_preserves_existing_outputs_and_cleans_temporaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SYNTHETIC write failure preserves all previous output bytes."""
    _write_inputs(tmp_path, [(DOI_A, _xml())])
    assert _run(tmp_path) == 0
    out = tmp_path / "out"
    before = {path.name: path.read_bytes() for path in out.iterdir()}
    original_replace = os.replace

    def fail_replace(
        src: str | os.PathLike[str], dst: str | os.PathLike[str]
    ) -> None:
        raise OSError("SYNTHETIC replacement failure")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(OSError, match="SYNTHETIC replacement failure"):
        _run(tmp_path)
    monkeypatch.setattr(os, "replace", original_replace)
    assert before == {path.name: path.read_bytes() for path in out.iterdir()}
