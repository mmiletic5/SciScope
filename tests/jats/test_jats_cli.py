"""SYNTHETIC file-based checks for the T006 parse command."""

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from sciscope.jats import cli, source
from sciscope.jats.locator import SourceDocument

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


def _helper_args(root: Path, command: str, *values: str) -> list[str]:
    """Build a SYNTHETIC helper invocation using only temporary inputs."""
    return [
        command,
        *values,
        "--repo-root",
        str(root),
        "--manifest",
        str(root / "manifest.jsonl"),
        "--metadata",
        str(root / "metadata.jsonl"),
    ]


def _snapshot(root: Path) -> dict[str, bytes]:
    """Capture all SYNTHETIC temporary files for read-only assertions."""
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def _helper_call(root: Path, command: str, *values: str) -> int:
    """Run a helper and check that its input tree remains byte-identical."""
    before = _snapshot(root)
    try:
        return cli.main(_helper_args(root, command, *values))
    finally:
        assert _snapshot(root) == before


def _rich_xml() -> bytes:
    """Build a SYNTHETIC paper with nested body and abstract sections."""
    return (
        b"<article><front><article-meta><abstract>"
        b"<sec><title>Purpose</title><p>alpha abstract one.</p></sec>"
        b"<sec><title>Summary</title><p>alpha abstract two.</p></sec>"
        b"</abstract></article-meta></front><body>"
        b"<sec><title>Results</title><p>alpha body one.</p>"
        b"<sec><title>  Local <italic>detail</italic>  </title>"
        b"<p>alpha <fig>hidden</fig><unknown>hidden</unknown>body two.</p>"
        b"</sec></sec><sec><p>last body.</p></sec></body></article>"
    )


def _locator(xml_bytes: bytes, path: str) -> str:
    """Find a locator in a SYNTHETIC document by its XML path."""
    document = SourceDocument.from_bytes(xml_bytes)
    element = document.root.find(path)
    assert element is not None
    return document.locator_for(element)


def test_show_outline_has_exact_header_order_indent_and_untitled(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """SYNTHETIC show prints a preorder outline with display headings."""
    xml_bytes = _rich_xml()
    _write_inputs(tmp_path, [(DOI_A, xml_bytes)])
    assert _helper_call(tmp_path, "show", DOI_A) == 0
    digest = hashlib.sha256(xml_bytes).hexdigest()
    assert capsys.readouterr().out == (
        f"doi: {DOI_A}\n"
        "title: SYNTHETIC title 0\n"
        f"xml_sha256: {digest}\n\n"
        f"{DOI_A}#abstract | abstract | 0 | (untitled)\n"
        f"{DOI_A}#abstract.1 | abstract | 1 |   Purpose\n"
        f"{DOI_A}#abstract.2 | abstract | 1 |   Summary\n"
        f"{DOI_A}#sec-1 | results | 1 | Results\n"
        f"{DOI_A}#sec-1.1 | results | 1 |   Local detail\n"
        f"{DOI_A}#sec-2 | other | 1 | (untitled)\n"
    )


def test_show_section_includes_nested_paragraphs_and_omissions(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """SYNTHETIC section selection prints owners, locators, and omissions."""
    xml_bytes = _rich_xml()
    _write_inputs(tmp_path, [(DOI_A, xml_bytes)])
    assert (
        _helper_call(tmp_path, "show", DOI_A, "--section", f"{DOI_A}#sec-1")
        == 0
    )
    output = capsys.readouterr().out
    first = _locator(xml_bytes, "./body/sec[1]/p")
    nested = _locator(xml_bytes, "./body/sec[1]/sec/p")
    assert output.endswith(
        f"section: {DOI_A}#sec-1 | results | Results\n\n"
        f"[{DOI_A}#sec-1 #1] {first}\nalpha body one.\n\n"
        f"[{DOI_A}#sec-1.1 #1] {nested}\nalpha body two.\n"
        "[omitted: fig, unknown]\n\n"
    )


def test_show_abstract_includes_structured_children(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """SYNTHETIC abstract selection follows nested section document order."""
    xml_bytes = _rich_xml()
    _write_inputs(tmp_path, [(DOI_A, xml_bytes)])
    assert _helper_call(tmp_path, "show", DOI_A, "--abstract") == 0
    output = capsys.readouterr().out
    first = _locator(xml_bytes, "./front/article-meta/abstract/sec[1]/p")
    second = _locator(xml_bytes, "./front/article-meta/abstract/sec[2]/p")
    assert output.endswith(
        f"section: {DOI_A}#abstract | abstract | (untitled)\n\n"
        f"[{DOI_A}#abstract.1 #1] {first}\nalpha abstract one.\n\n"
        f"[{DOI_A}#abstract.2 #1] {second}\nalpha abstract two.\n\n"
    )


@pytest.mark.parametrize("selection", ["--section", "--abstract"])
def test_show_unknown_doi_exits_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], selection: str
) -> None:
    """SYNTHETIC missing DOI produces a stable input error."""
    _write_inputs(tmp_path, [(DOI_A, _rich_xml())])
    values = (
        ("--section", f"{DOI_A}#sec-1")
        if selection == "--section"
        else ("--abstract",)
    )
    assert _helper_call(tmp_path, "show", DOI_B, *values) == 2
    assert capsys.readouterr().err == "error: unknown-doi\n"


def test_show_unknown_section_exits_two(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """SYNTHETIC missing section has a distinct error."""
    _write_inputs(tmp_path, [(DOI_A, _rich_xml())])
    assert (
        _helper_call(tmp_path, "show", DOI_A, "--section", f"{DOI_A}#sec-99")
        == 2
    )
    assert capsys.readouterr().err == "error: unknown-section\n"


def test_show_rejects_both_selection_flags(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """SYNTHETIC mutually exclusive selection is rejected by argparse."""
    _write_inputs(tmp_path, [(DOI_A, _rich_xml())])
    before = _snapshot(tmp_path)
    with pytest.raises(SystemExit) as error:
        cli.main(
            _helper_args(
                tmp_path,
                "show",
                DOI_A,
                "--section",
                f"{DOI_A}#sec-1",
                "--abstract",
            )
        )
    assert error.value.code == 2
    assert "not allowed with argument" in capsys.readouterr().err
    assert _snapshot(tmp_path) == before


@pytest.mark.parametrize(
    ("path", "quote", "expected_first", "matches", "owner"),
    [
        (
            "./body/sec[1]/p",
            "alpha   body\tone.",
            "./body/sec[1]/p",
            1,
            "#sec-1",
        ),
        ("./body/sec[1]", "alpha", "./body/sec[1]/p", 2, "#sec-1"),
        (
            "./front/article-meta/abstract",
            "alpha",
            "./front/article-meta/abstract/sec[1]/p",
            2,
            "#abstract.1",
        ),
    ],
)
def test_check_quote_reports_first_matching_paragraph_and_count(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    path: str,
    quote: str,
    expected_first: str,
    matches: int,
    owner: str,
) -> None:
    """SYNTHETIC matching uses paragraph boundaries and document order."""
    xml_bytes = _rich_xml()
    _write_inputs(tmp_path, [(DOI_A, xml_bytes)])
    locator = _locator(xml_bytes, path)
    assert (
        _helper_call(
            tmp_path, "check-quote", "--locator", locator, "--quote", quote
        )
        == 0
    )
    expected_locator = _locator(xml_bytes, expected_first)
    assert capsys.readouterr().out == (
        f"OK: quote found in {expected_locator}\n"
        f"matches: {matches}\n"
        f"section: {DOI_A}{owner} paragraph: 1\n"
    )


@pytest.mark.parametrize(
    ("quote", "expected_code", "exit_code"),
    [
        ("ALPHA", "quote-absent", 1),
        ("body one. alpha body two.", "quote-absent", 1),
        ("SYNTHETIC absent", "quote-absent", 1),
        (" \t\n ", "quote-empty", 2),
    ],
)
def test_check_quote_absence_case_and_empty_input(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    quote: str,
    expected_code: str,
    exit_code: int,
) -> None:
    """SYNTHETIC quote failures have distinct codes and exit statuses."""
    xml_bytes = _rich_xml()
    _write_inputs(tmp_path, [(DOI_A, xml_bytes)])
    locator = _locator(xml_bytes, "./body/sec[1]")
    assert (
        _helper_call(
            tmp_path, "check-quote", "--locator", locator, "--quote", quote
        )
        == exit_code
    )
    assert capsys.readouterr().err == f"error: {expected_code}\n"


@pytest.mark.parametrize(
    ("path", "change", "expected"),
    [
        ("./body/sec[1]/p", "prefix", "locator-malformed"),
        ("./body/sec[1]/p", "digest", "digest-mismatch"),
        ("./body/sec[1]/p", "missing-path", "path-not-found"),
        ("./body/sec[1]/p", "wrong-target", "invalid-target"),
    ],
)
def test_check_quote_locator_errors(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    path: str,
    change: str,
    expected: str,
) -> None:
    """SYNTHETIC malformed, foreign, absent, and unsupported targets differ."""
    xml_bytes = _rich_xml()
    _write_inputs(tmp_path, [(DOI_A, xml_bytes)])
    locator = _locator(xml_bytes, path)
    if change == "prefix":
        locator = locator.replace("jats:v1:", "jats:v2:", 1)
    elif change == "digest":
        locator = locator.replace(
            hashlib.sha256(xml_bytes).hexdigest(), "0" * 64
        )
    elif change == "missing-path":
        locator = locator.replace("/p[1]", "/p[99]")
    else:
        locator = locator.replace("/p[1]", "/title[1]")
    assert (
        _helper_call(
            tmp_path, "check-quote", "--locator", locator, "--quote", "alpha"
        )
        == 2
    )
    assert capsys.readouterr().err == f"error: {expected}\n"


def test_check_quote_digest_must_be_in_manifest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """SYNTHETIC unknown source digest fails before source loading."""
    xml_bytes = _rich_xml()
    _write_inputs(tmp_path, [(DOI_A, xml_bytes)])
    locator = _locator(xml_bytes, "./body/sec[1]/p")
    locator = locator.replace(hashlib.sha256(xml_bytes).hexdigest(), "f" * 64)
    assert (
        _helper_call(
            tmp_path, "check-quote", "--locator", locator, "--quote", "alpha"
        )
        == 2
    )
    assert capsys.readouterr().err == "error: digest-mismatch\n"


def test_verify_roundtrip_reports_all_counts_and_implicit_group(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """SYNTHETIC verification checks both regular and implicit sections."""
    implicit = b"<article><body><p>SYNTHETIC loose.</p></body></article>"
    _write_inputs(tmp_path, [(DOI_B, implicit), (DOI_A, _rich_xml())])
    assert _helper_call(tmp_path, "verify-roundtrip") == 0
    assert capsys.readouterr().out == (
        f"{DOI_A}: sections 6 paragraphs 5 OK\n"
        f"{DOI_B}: sections 1 paragraphs 1 OK\n"
        "Checked: 7 sections, 6 paragraphs across 2 papers; mismatches: 0\n"
    )


def test_verify_roundtrip_lists_failed_paper(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """SYNTHETIC bad digest makes the full verification exit nonzero."""
    _write_inputs(
        tmp_path,
        [(DOI_A, _rich_xml()), (DOI_B, _xml())],
        bad_digests={DOI_B},
    )
    assert _helper_call(tmp_path, "verify-roundtrip") == 1
    output = capsys.readouterr().out
    assert f"{DOI_B}: digest-mismatch\n" in output
    assert "mismatches: " in output


def test_verify_roundtrip_reports_stored_text_mismatch(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SYNTHETIC changed parse record is visible as a locator mismatch."""
    _write_inputs(tmp_path, [(DOI_A, _rich_xml())])
    original_parse = cli.parse_paper

    def changed_parse(*args: Any, **kwargs: Any) -> Any:
        result = original_parse(*args, **kwargs)
        paragraphs = (replace(result.paragraphs[0], text="changed"),) + (
            result.paragraphs[1:]
        )
        return replace(result, paragraphs=paragraphs)

    monkeypatch.setattr(cli, "parse_paper", changed_parse)
    assert _helper_call(tmp_path, "verify-roundtrip") == 1
    output = capsys.readouterr().out
    assert "mismatches: 1" in output
    first = _locator(_rich_xml(), "./front/article-meta/abstract/sec[1]/p")
    assert f"{DOI_A}#abstract.1: " in output or f"{first}: " in output


def test_show_subprocess_forces_utf8_on_cp1252_console(tmp_path: Path) -> None:
    """SYNTHETIC non-cp1252 heading is emitted as UTF-8 bytes."""
    xml_bytes = _rich_xml().replace(b"Results", "α Results".encode())
    _write_inputs(tmp_path, [(DOI_A, xml_bytes)])
    args = _helper_args(tmp_path, "show", DOI_A)
    environment = os.environ.copy()
    environment["PYTHONPATH"] = "src"
    environment["PYTHONIOENCODING"] = "cp1252"
    before = _snapshot(tmp_path)
    completed = subprocess.run(
        [sys.executable, "-m", "sciscope.jats.cli", *args],
        capture_output=True,
        check=False,
        env=environment,
    )
    assert _snapshot(tmp_path) == before
    assert completed.returncode == 0
    assert completed.stdout.decode("utf-8") == (
        f"doi: {DOI_A}\n"
        "title: SYNTHETIC title 0\n"
        f"xml_sha256: {hashlib.sha256(xml_bytes).hexdigest()}\n\n"
        f"{DOI_A}#abstract | abstract | 0 | (untitled)\n"
        f"{DOI_A}#abstract.1 | abstract | 1 |   Purpose\n"
        f"{DOI_A}#abstract.2 | abstract | 1 |   Summary\n"
        f"{DOI_A}#sec-1 | other | 1 | α Results\n"
        f"{DOI_A}#sec-1.1 | other | 1 |   Local detail\n"
        f"{DOI_A}#sec-2 | other | 1 | (untitled)\n"
    )
