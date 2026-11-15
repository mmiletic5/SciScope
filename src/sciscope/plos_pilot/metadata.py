"""Extract JATS front matter and write verified metadata JSONL."""

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

_XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
_XLINK_HREF = "{http://www.w3.org/1999/xlink}href"


def _local_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _find(parent: ET.Element | None, name: str) -> ET.Element | None:
    if parent is None:
        return None
    return next(
        (element for element in parent.iter() if _local_name(element) == name),
        None,
    )


def _text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return " ".join("".join(element.itertext()).split())


def _date(pub_date: ET.Element | None) -> str:
    year = _text(_find(pub_date, "year"))
    if not year:
        return ""
    month = _text(_find(pub_date, "month"))
    day = _text(_find(pub_date, "day"))
    if not month:
        return year
    if month.isdigit():
        month = f"{int(month):02d}"
    if not day:
        return f"{year}-{month}"
    if day.isdigit():
        day = f"{int(day):02d}"
    return f"{year}-{month}-{day}"


def parse_article(xml: bytes) -> tuple[ET.Element, dict[str, Any]]:
    """Parse XML once and return its root plus required front matter.

    Args:
        xml: Source JATS bytes.

    Returns:
        Parsed root and the nine approved front-matter fields.

    Raises:
        ValueError: If XML is malformed or required front matter is absent.
    """
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as error:
        raise ValueError(f"Invalid XML: {error}") from error
    front = _find(root, "front")
    journal_meta = _find(front, "journal-meta")
    article_meta = _find(front, "article-meta")
    journal = _text(_find(journal_meta, "journal-title"))
    title = _text(_find(article_meta, "article-title"))
    authors: list[dict[str, str]] = []
    if article_meta is not None:
        for contrib in article_meta.iter():
            if _local_name(contrib) != "contrib":
                continue
            if contrib.get("contrib-type") not in (None, "author"):
                continue
            surname = _text(_find(contrib, "surname"))
            given_names = _text(_find(contrib, "given-names"))
            if not surname:
                surname = _text(_find(contrib, "collab"))
            if surname:
                authors.append({"surname": surname, "given_names": given_names})
    pub_dates = (
        [
            element
            for element in article_meta.iter()
            if _local_name(element) == "pub-date"
        ]
        if article_meta is not None
        else []
    )
    preferred_date = next(
        (date for date in pub_dates if date.get("pub-type") == "epub"),
        pub_dates[0] if pub_dates else None,
    )
    subjects: list[str] = []
    categories = _find(article_meta, "article-categories")
    if categories is not None:
        for element in categories.iter():
            if _local_name(element) == "subject":
                subject = _text(element)
                if subject and subject not in subjects:
                    subjects.append(subject)
    abstract = ""
    if article_meta is not None:
        for element in article_meta.iter():
            if (
                _local_name(element) == "abstract"
                and "abstract-type" not in element.attrib
            ):
                abstract = _text(element)
                break
    license_element = _find(article_meta, "license")
    license_value = (
        license_element.get(_XLINK_HREF, "").strip() or _text(license_element)
        if license_element is not None
        else ""
    )
    result: dict[str, Any] = {
        "title": title,
        "authors": authors,
        "journal": journal,
        "publication_date": _date(preferred_date),
        "article_type": root.get("article-type", "").strip(),
        "subjects": subjects,
        "abstract": abstract,
        "license": license_value,
        "language": root.get(_XML_LANG, "").strip(),
    }
    missing = [
        field
        for field in (
            "title",
            "authors",
            "journal",
            "publication_date",
            "article_type",
            "license",
            "language",
        )
        if not result[field]
    ]
    if missing:
        raise ValueError("Missing front matter: " + ", ".join(missing))
    return root, result


def extract_front_matter(xml: bytes) -> dict[str, Any]:
    """Extract exactly nine front-matter fields from JATS XML.

    Args:
        xml: Source JATS bytes.

    Returns:
        Title, authors, journal, date, article type, subjects, abstract,
        license, and language. Body, sections, and references are excluded.

    Raises:
        ValueError: If XML is malformed or required fields are absent.
    """
    return parse_article(xml)[1]


def write_metadata(
    manifest_path: Path, output_path: Path, repo_root: Path
) -> None:
    """Verify manifest XML digests and atomically replace metadata JSONL.

    Args:
        manifest_path: Source manifest JSONL.
        output_path: Destination metadata JSONL.
        repo_root: Root used to resolve manifest-relative raw XML paths.

    Raises:
        ValueError: If a raw path escapes the root or its digest differs.
    """
    records: list[dict[str, Any]] = []
    if manifest_path.exists():
        with manifest_path.open(encoding="utf-8") as source:
            for line in source:
                if not line.strip():
                    continue
                entry = json.loads(line)
                raw_path = (repo_root / entry["raw_xml_path"]).resolve()
                if not raw_path.is_relative_to(repo_root.resolve()):
                    raise ValueError(
                        f"Raw XML path escapes repository: {raw_path}"
                    )
                try:
                    xml = raw_path.read_bytes()
                except FileNotFoundError as error:
                    raise ValueError(
                        f"Raw XML missing for DOI {entry['doi']}; "
                        "re-run the download command to restore raw XML"
                    ) from error
                digest = hashlib.sha256(xml).hexdigest()
                if digest != entry["xml_sha256"]:
                    raise ValueError(
                        f"SHA256 digest mismatch for {entry['doi']}"
                    )
                records.append(
                    {"doi": entry["doi"], **extract_front_matter(xml)}
                )
    records.sort(key=lambda record: record["doi"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=output_path.parent,
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_name = temporary.name
            for record in records:
                temporary.write(json.dumps(record, ensure_ascii=False) + "\n")
        os.replace(temporary_name, output_path)
    finally:
        if temporary_name is not None and os.path.exists(temporary_name):
            os.unlink(temporary_name)
