"""SYNTHETIC behavior checks for confined, safe JATS source loading."""

import hashlib
import json
from collections.abc import Callable
from pathlib import Path

import pytest

from sciscope.jats.locator import SourceDocument
from sciscope.jats.source import (
    InputFileError,
    ManifestEntry,
    SourceError,
    UnsafeXmlError,
    check_xml_safety,
    load_source,
    read_manifest,
    read_metadata_titles,
)

XML = b"<article><body><sec><p>SYNTHETIC text</p></sec></body></article>"


@pytest.mark.parametrize(
    "xml_bytes",
    [
        b'<?xml version="1.0" encoding="UTF-8"?><article/>',
        b'<?xml version="1.0" encoding="utf-8"?><article/>',
        XML,
        b"\xef\xbb\xbf<article/>",
        b'<!DOCTYPE article SYSTEM "synthetic.dtd"><article/>',
        b'<!DOCTYPE article PUBLIC "SYNTHETIC" "synthetic.dtd"><article/>',
        b'<!DOCTYPE article PUBLIC "SYNTHETIC [ id" "synthetic.dtd"><article/>',
    ],
)
def test_safety_accepts_supported_xml(xml_bytes: bytes) -> None:
    """SYNTHETIC UTF-8 and external DTD forms pass the gate."""
    check_xml_safety(xml_bytes)


@pytest.mark.parametrize(
    ("xml_bytes", "reason"),
    [
        (b"\xff\xfe<\x00", "bad-encoding"),
        (b"\xfe\xff\x00<", "bad-encoding"),
        (b"\xff\xfe\x00\x00", "bad-encoding"),
        (b"\x00\x00\xfe\xff", "bad-encoding"),
        (b"<a\x00/>", "bad-encoding"),
        (
            b'<?xml version="1.0" encoding="ISO-8859-1"?><article/>',
            "bad-encoding",
        ),
        (b"<!ENTITY synthetic 'x'><article/>", "entity"),
        (b"<!DOCTYPE article [ ]><article/>", "internal-subset"),
        (b'<article xmlns:xi="http://www.w3.org/2001/XInclude"/>', "xinclude"),
    ],
)
def test_safety_rejects_with_exact_reason(
    xml_bytes: bytes, reason: str
) -> None:
    """SYNTHETIC unsafe bytes report the approved reason."""
    with pytest.raises(UnsafeXmlError) as error:
        check_xml_safety(xml_bytes)
    assert error.value.reason == reason


def test_read_manifest_preserves_order_and_duplicates(tmp_path: Path) -> None:
    """SYNTHETIC duplicate DOI entries remain available to the CLI."""
    path = tmp_path / "manifest.jsonl"
    entries = [
        {"doi": "b", "xml_sha256": "2", "raw_xml_path": "b.xml"},
        {"doi": "a", "xml_sha256": "1", "raw_xml_path": "a.xml"},
        {"doi": "b", "xml_sha256": "3", "raw_xml_path": "c.xml"},
    ]
    path.write_text(
        "".join(json.dumps(item) + "\n" for item in entries), encoding="utf-8"
    )
    assert read_manifest(path) == [ManifestEntry(**item) for item in entries]


def test_read_metadata_titles(tmp_path: Path) -> None:
    """SYNTHETIC metadata joins only DOI and title."""
    path = tmp_path / "metadata.jsonl"
    path.write_text(
        json.dumps({"doi": "a", "title": "SYNTHETIC café", "ignored": 1})
        + "\n",
        encoding="utf-8",
    )
    assert read_metadata_titles(path) == {"a": "SYNTHETIC café"}


@pytest.mark.parametrize("reader", [read_manifest, read_metadata_titles])
@pytest.mark.parametrize("content", ["{bad json}\n", '{"doi": "a"}\n'])
def test_bad_input_files_raise_input_file_error(
    tmp_path: Path, reader: Callable[[Path], object], content: str
) -> None:
    """SYNTHETIC malformed JSON and missing required fields fail cleanly."""
    path = tmp_path / "input.jsonl"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(InputFileError):
        reader(path)


def test_missing_input_files_raise_input_file_error(tmp_path: Path) -> None:
    """SYNTHETIC absent input files are input-level errors."""
    for reader in (read_manifest, read_metadata_titles):
        with pytest.raises(InputFileError):
            reader(tmp_path / "missing.jsonl")


def _entry(
    path: str, xml_bytes: bytes, digest: str | None = None
) -> ManifestEntry:
    """Build a SYNTHETIC manifest entry."""
    return ManifestEntry(
        "10.9999/synthetic",
        digest or hashlib.sha256(xml_bytes).hexdigest(),
        path,
    )


def test_load_source_success_and_uppercase_digest(tmp_path: Path) -> None:
    """SYNTHETIC matching bytes produce a digest-bound document."""
    (tmp_path / "paper.xml").write_bytes(XML)
    entry = _entry("paper.xml", XML)
    for digest in (entry.xml_sha256, entry.xml_sha256.upper()):
        document = load_source(
            ManifestEntry(entry.doi, digest, entry.raw_xml_path), tmp_path
        )
        assert isinstance(document, SourceDocument)
        assert document.sha256 == entry.xml_sha256


@pytest.mark.parametrize("path", ["../outside.xml", "ABSOLUTE"])
def test_load_source_rejects_paths_outside_repo(
    tmp_path: Path, path: str
) -> None:
    """SYNTHETIC relative escapes and absolute paths are confined."""
    raw_path = (
        str((tmp_path.parent / "outside.xml").resolve())
        if path == "ABSOLUTE"
        else path
    )
    with pytest.raises(SourceError) as error:
        load_source(_entry(raw_path, XML), tmp_path)
    assert error.value.code == "path-outside-repo"


@pytest.mark.parametrize(
    ("xml_bytes", "digest", "max_bytes", "code"),
    [
        (None, None, None, "file-missing"),
        (XML, None, len(XML) - 1, "xml-too-large"),
        (XML, "0" * 64, None, "digest-mismatch"),
        (b"<!ENTITY x 'a'><article/>", None, None, "xml-unsafe"),
        (b"<article>", None, None, "xml-invalid"),
    ],
)
def test_load_source_failure_codes(
    tmp_path: Path,
    xml_bytes: bytes | None,
    digest: str | None,
    max_bytes: int | None,
    code: str,
) -> None:
    """SYNTHETIC source failures have stable per-paper codes."""
    if xml_bytes is not None:
        (tmp_path / "paper.xml").write_bytes(xml_bytes)
    entry = _entry("paper.xml", xml_bytes or XML, digest)
    with pytest.raises(SourceError) as error:
        load_source(entry, tmp_path, max_bytes=max_bytes or 4 * 1024 * 1024)
    assert error.value.code == code


def test_load_source_size_boundary(tmp_path: Path) -> None:
    """SYNTHETIC exactly-at-cap bytes pass and one extra byte fails."""
    (tmp_path / "paper.xml").write_bytes(XML)
    assert load_source(
        _entry("paper.xml", XML), tmp_path, max_bytes=len(XML)
    ).sha256
    with pytest.raises(SourceError) as error:
        load_source(_entry("paper.xml", XML), tmp_path, max_bytes=len(XML) - 1)
    assert error.value.code == "xml-too-large"


def test_load_source_checks_digest_before_safety_gate(tmp_path: Path) -> None:
    """SYNTHETIC unsafe bytes with a bad digest report digest mismatch."""
    unsafe = b"<!ENTITY x 'a'><article/>"
    (tmp_path / "paper.xml").write_bytes(unsafe)
    with pytest.raises(SourceError) as error:
        load_source(_entry("paper.xml", unsafe, "0" * 64), tmp_path)
    assert error.value.code == "digest-mismatch"
