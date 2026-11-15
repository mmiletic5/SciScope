"""Source input and XML safety interfaces for the JATS parser."""

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from sciscope.jats.locator import SourceDocument

# Largest pilot XML: 223,133 bytes; smallest power-of-two MiB >= 16 times it.
MAX_XML_BYTES: int = 4 * 1024 * 1024
_DECLARATION = re.compile(rb"^\s*<\?xml\b[^?]*\?>", re.IGNORECASE)
_ENCODING = re.compile(rb"\bencoding\s*=\s*(['\"])(.*?)\1", re.IGNORECASE)
_XINCLUDE_URI = b"http://www.w3.org/2001/XInclude"


class UnsafeXmlError(ValueError):
    """XML fails the byte-level safety policy."""

    reason: str

    def __init__(self, reason: str) -> None:
        """Store the approved safety reason."""
        super().__init__(reason)
        self.reason = reason


def check_xml_safety(xml_bytes: bytes) -> None:
    """Reject source bytes that violate the approved XML safety policy."""
    if xml_bytes.startswith((b"\xff\xfe", b"\xfe\xff", b"\x00\x00\xfe\xff")):
        raise UnsafeXmlError("bad-encoding")
    if b"\x00" in xml_bytes[:4]:
        raise UnsafeXmlError("bad-encoding")

    without_bom = xml_bytes.removeprefix(b"\xef\xbb\xbf")
    declaration = _DECLARATION.match(without_bom)
    if declaration is not None:
        encoding = _ENCODING.search(declaration.group())
        if encoding is not None and encoding.group(2).lower() != b"utf-8":
            raise UnsafeXmlError("bad-encoding")
    if b"<!ENTITY" in xml_bytes:
        raise UnsafeXmlError("entity")

    start = 0
    while (start := xml_bytes.find(b"<!DOCTYPE", start)) != -1:
        quote: int | None = None
        for byte in xml_bytes[start + len(b"<!DOCTYPE") :]:
            if byte in (ord("'"), ord('"')):
                if quote is None:
                    quote = byte
                elif quote == byte:
                    quote = None
            elif quote is None and byte == ord("["):
                raise UnsafeXmlError("internal-subset")
            elif quote is None and byte == ord(">"):
                break
        start += len(b"<!DOCTYPE")

    if _XINCLUDE_URI in xml_bytes:
        raise UnsafeXmlError("xinclude")


class SourceError(Exception):
    """One manifest paper cannot be loaded."""

    code: str

    def __init__(self, code: str) -> None:
        """Store the approved per-paper error code."""
        super().__init__(code)
        self.code = code


class InputFileError(ValueError):
    """A manifest or metadata file is unreadable or invalid."""


@dataclass(frozen=True, slots=True)
class ManifestEntry:
    """The three F001 manifest values needed to load a paper."""

    doi: str
    xml_sha256: str
    raw_xml_path: str


def _read_json_lines(
    path: Path, required: tuple[str, ...]
) -> list[dict[str, Any]]:
    """Read valid JSON objects with the required string fields."""
    records: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as source:
            for line_number, line in enumerate(source, start=1):
                if not line.strip():
                    continue
                try:
                    value: Any = json.loads(line)
                except json.JSONDecodeError as error:
                    raise InputFileError(
                        f"Invalid JSON at line {line_number}"
                    ) from error
                if not isinstance(value, dict) or any(
                    not isinstance(value.get(key), str) for key in required
                ):
                    raise InputFileError(
                        f"Missing or invalid field at line {line_number}"
                    )
                records.append(value)
    except (OSError, UnicodeError) as error:
        raise InputFileError(f"Cannot read input file: {path}") from error
    return records


def read_manifest(path: Path) -> list[ManifestEntry]:
    """Read manifest entries in file order, preserving duplicate DOIs."""
    return [
        ManifestEntry(
            record["doi"], record["xml_sha256"], record["raw_xml_path"]
        )
        for record in _read_json_lines(
            path, ("doi", "xml_sha256", "raw_xml_path")
        )
    ]


def read_metadata_titles(path: Path) -> dict[str, str]:
    """Read the exact DOI-to-title mapping from F001 metadata."""
    return {
        record["doi"]: record["title"]
        for record in _read_json_lines(path, ("doi", "title"))
    }


def load_source(
    entry: ManifestEntry,
    repo_root: Path,
    max_bytes: int = MAX_XML_BYTES,
) -> SourceDocument:
    """Load one digest-verified, safe, confined XML source document."""
    root = repo_root.resolve()
    raw_path = Path(entry.raw_xml_path)
    path = (root / raw_path).resolve()
    if not path.is_relative_to(root):
        raise SourceError("path-outside-repo")
    if not path.is_file():
        raise SourceError("file-missing")
    try:
        with path.open("rb") as source:
            xml_bytes = source.read(max_bytes + 1)
    except OSError as error:
        raise SourceError("file-missing") from error
    if len(xml_bytes) > max_bytes:
        raise SourceError("xml-too-large")
    if hashlib.sha256(xml_bytes).hexdigest() != entry.xml_sha256.lower():
        raise SourceError("digest-mismatch")
    try:
        check_xml_safety(xml_bytes)
    except UnsafeXmlError as error:
        raise SourceError("xml-unsafe") from error
    try:
        return SourceDocument.from_bytes(xml_bytes)
    except ET.ParseError as error:
        raise SourceError("xml-invalid") from error
