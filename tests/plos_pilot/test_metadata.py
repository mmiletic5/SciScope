"""Front-matter-only checks using SYNTHETIC JATS fixtures."""

import hashlib
import json
from pathlib import Path

import pytest

from sciscope.plos_pilot.metadata import extract_front_matter, write_metadata


def synthetic_article(doi: str = "10.9999/synthetic-a") -> bytes:
    """Provide SYNTHETIC metadata and forbidden body text."""
    return f"""<article xmlns:xml="http://www.w3.org/XML/1998/namespace"
        xmlns:xlink="http://www.w3.org/1999/xlink"
        article-type="research-article" xml:lang="en"><front>
        <journal-meta><journal-title-group><journal-title>PLoS ONE
        </journal-title></journal-title-group></journal-meta><article-meta>
        <article-id pub-id-type="doi">{doi}</article-id>
        <article-categories><subj-group><subject>SYNTHETIC bees</subject>
        <subject>SYNTHETIC methods</subject><subject>SYNTHETIC bees</subject>
        </subj-group></article-categories>
        <title-group><article-title>SYNTHETIC <italic>inline</italic>
        title</article-title>
        </title-group><contrib-group><contrib contrib-type="author"><name>
        <surname>Example</surname><given-names>Alpha</given-names></name></contrib>
        <contrib contrib-type="author"><name><surname>Tester</surname>
        <given-names>Beta</given-names></name></contrib>
        <contrib contrib-type="author"><collab>SYNTHETIC Team</collab></contrib>
        </contrib-group><pub-date><year>2025</year></pub-date>
        <pub-date pub-type="epub"><day>02</day><month>01</month>
        <year>2026</year></pub-date>
        <abstract abstract-type="summary"><p>IGNORE SYNTHETIC SUMMARY</p>
        </abstract>
        <abstract><p>SYNTHETIC <italic>inline</italic> abstract.</p>
        <p>Second paragraph.</p></abstract>
        <permissions><license xlink:href="https://creativecommons.org/licenses/by/4.0/"/>
        </permissions></article-meta></front>
        <body><sec><title>FORBIDDEN BODY</title>
        <p>FORBIDDEN SECTION</p></sec></body>
        <back><ref-list><ref>FORBIDDEN REFERENCE</ref></ref-list></back>
        </article>""".encode()


def test_extracts_exact_nine_front_matter_fields() -> None:
    """Inline text and authors preserve order; body material is excluded."""
    result = extract_front_matter(synthetic_article())
    assert result == {
        "title": "SYNTHETIC inline title",
        "authors": [
            {"surname": "Example", "given_names": "Alpha"},
            {"surname": "Tester", "given_names": "Beta"},
            {"surname": "SYNTHETIC Team", "given_names": ""},
        ],
        "journal": "PLoS ONE",
        "publication_date": "2026-01-02",
        "article_type": "research-article",
        "subjects": ["SYNTHETIC bees", "SYNTHETIC methods"],
        "abstract": "SYNTHETIC inline abstract. Second paragraph.",
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "language": "en",
    }
    assert "FORBIDDEN" not in json.dumps(result)


@pytest.mark.parametrize(
    ("date_xml", "expected"),
    [
        ("<year>2026</year><month>03</month>", "2026-03"),
        ("<year>2026</year>", "2026"),
    ],
)
def test_partial_publication_dates(date_xml: str, expected: str) -> None:
    """Absent day or month yields the available ISO date precision."""
    xml = synthetic_article().replace(
        b'<pub-date pub-type="epub"><day>02</day><month>01</month>\n'
        b"        <year>2026</year>",
        f'<pub-date pub-type="epub">{date_xml}'.encode(),
    )
    assert extract_front_matter(xml)["publication_date"] == expected


def test_missing_required_fields_are_reported_together() -> None:
    """One error lists every missing required front matter field."""
    xml = b"<article><front><article-meta/></front></article>"
    with pytest.raises(ValueError) as error:
        extract_front_matter(xml)
    for field in (
        "title",
        "authors",
        "journal",
        "publication_date",
        "article_type",
        "license",
        "language",
    ):
        assert field in str(error.value)


def test_license_text_fallback_and_empty_optional_fields() -> None:
    """License text is valid; optional fields may be empty."""
    xml = synthetic_article().replace(
        b'<license xlink:href="https://creativecommons.org/licenses/by/4.0/"/>',
        b"<license>SYNTHETIC license text</license>",
    )
    xml = xml.replace(b"<article-categories>", b"<unused-categories>").replace(
        b"</article-categories>", b"</unused-categories>"
    )
    xml = xml.replace(
        b"<abstract><p>SYNTHETIC", b"<unused-abstract><p>SYNTHETIC"
    ).replace(
        b"<p>Second paragraph.</p></abstract>",
        b"<p>Second paragraph.</p></unused-abstract>",
    )
    result = extract_front_matter(xml)
    assert result["license"] == "SYNTHETIC license text"
    assert result["subjects"] == []
    assert result["abstract"] == ""


def test_write_metadata_checks_digest_sorts_and_replaces_atomically(
    tmp_path: Path,
) -> None:
    """Manifest XML becomes sorted DOI JSONL after digest verification."""
    raw_dir = tmp_path / "data/raw/plos"
    raw_dir.mkdir(parents=True)
    manifest = tmp_path / "data/pilot/manifest.jsonl"
    manifest.parent.mkdir(parents=True)
    records = []
    for doi in ("10.9999/synthetic-z", "10.9999/synthetic-a"):
        xml = synthetic_article(doi)
        path = raw_dir / f"{doi.replace('/', '%2F')}.xml"
        path.write_bytes(xml)
        records.append(
            {
                "doi": doi,
                "raw_xml_path": path.relative_to(tmp_path).as_posix(),
                "xml_sha256": hashlib.sha256(xml).hexdigest(),
            }
        )
    manifest.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )
    output = tmp_path / "data/pilot/metadata.jsonl"
    write_metadata(manifest, output, tmp_path)
    metadata = [
        json.loads(line)
        for line in output.read_text(encoding="utf-8").splitlines()
    ]
    assert [record["doi"] for record in metadata] == [
        "10.9999/synthetic-a",
        "10.9999/synthetic-z",
    ]
    assert all(
        set(record)
        == {
            "doi",
            "title",
            "authors",
            "journal",
            "publication_date",
            "article_type",
            "subjects",
            "abstract",
            "license",
            "language",
        }
        for record in metadata
    )
    assert b"\r\n" not in output.read_bytes()
    assert list(output.parent.glob("*.tmp")) == []
    before = output.read_bytes()
    records[0]["xml_sha256"] = "0" * 64
    manifest.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="SHA256|digest|hash"):
        write_metadata(manifest, output, tmp_path)
    assert output.read_bytes() == before
