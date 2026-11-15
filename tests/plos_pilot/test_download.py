"""Offline acquisition behavior with SYNTHETIC JATS and DOI records."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, quote, urlsplit

import pytest

from sciscope.plos_pilot import config
from sciscope.plos_pilot.download import download_selected
from sciscope.plos_pilot.selection import write_screening, write_selection

DOIS = [f"10.9999/synthetic-{index:02d}" for index in range(15)]
NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
ARMS = [
    {
        "q": "title:honeybee",
        "fq": list(config.FILTER_QUERIES),
        "numFound": 2,
        "date": "2026-01-01",
    },
    {
        "q": "abstract:honeybee",
        "fq": list(config.FILTER_QUERIES),
        "numFound": 3,
        "date": "2026-01-01",
    },
]


def synthetic_xml(
    doi: str,
    *,
    journal: str = "PLoS ONE",
    article_type: str = "research-article",
    language: str = "en-US",
    license_href: str = "https://creativecommons.org/licenses/by/4.0/",
    title: str = "SYNTHETIC title",
) -> bytes:
    """Build a small SYNTHETIC JATS article without scientific claims."""
    return f"""<article xmlns:xml="http://www.w3.org/XML/1998/namespace"
        xmlns:xlink="http://www.w3.org/1999/xlink" xml:lang="{language}"
        article-type="{article_type}"><front><journal-meta><journal-title-group>
        <journal-title>{journal}</journal-title></journal-title-group></journal-meta>
        <article-meta><article-id pub-id-type="doi">{doi}</article-id>
        <title-group><article-title>{title}</article-title></title-group>
        <contrib-group><contrib contrib-type="author"><name>
        <surname>Example</surname>
        <given-names>Synthetic</given-names></name></contrib></contrib-group>
        <pub-date pub-type="epub"><day>02</day><month>01</month>
        <year>2026</year></pub-date>
        <permissions><license xlink:href="{license_href}"/></permissions>
        </article-meta></front></article>""".encode()


def setup_inputs(
    root: Path, *, journal: str = "PLOS ONE"
) -> tuple[Path, Path, Path, Path, Path]:
    """Write only SYNTHETIC input records beneath a pytest temporary root."""
    pilot = root / "data" / "pilot"
    pilot.mkdir(parents=True, exist_ok=True)
    screening = pilot / "screening.tsv"
    selection = pilot / "selection.tsv"
    candidates = pilot / "candidates.jsonl"
    manifest = pilot / "manifest.jsonl"
    raw_dir = root / "data" / "raw" / "plos"
    rows = [
        {
            "doi": doi.upper(),
            "class": "measured_mellifera",
            "reason": "SYNTHETIC review",
            "topic": f"SYNTHETIC topic {index % 3}",
            "methods_checked": "",
        }
        for index, doi in enumerate(DOIS)
    ]
    write_screening(
        screening,
        [
            {
                key: value
                for key, value in row.items()
                if key != "methods_checked"
            }
            for row in rows
        ],
    )
    write_selection(selection, rows)
    records = [
        {
            "doi": doi,
            "journal": journal,
            "arms": ARMS,
            "title": "SYNTHETIC candidate",
        }
        for doi in [*DOIS, "10.9999/synthetic-unselected"]
    ]
    candidates.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )
    return screening, selection, candidates, manifest, raw_dir


def run_download(
    root: Path,
    fetch: object,
    *,
    journal: str = "PLOS ONE",
) -> object:
    """Call acquisition with injected I/O and a virtual monotonic clock."""
    screening, selection, candidates, manifest, raw_dir = setup_inputs(
        root, journal=journal
    )
    clock_time = [0.0]

    def clock() -> float:
        return clock_time[0]

    def sleep(seconds: float) -> None:
        clock_time[0] += seconds

    return download_selected(
        screening_path=screening,
        selection_path=selection,
        candidate_path=candidates,
        manifest_path=manifest,
        raw_dir=raw_dir,
        repo_root=root,
        fetch=fetch,
        sleep=sleep,
        clock=clock,
        now=lambda: NOW,
    )


def test_only_selected_verified_route_and_manifest(tmp_path: Path) -> None:
    """Accepted XML preserves bytes, provenance, original DOI, and UTC time."""
    requested: list[str] = []

    def fetch(url: str, timeout: float) -> bytes:
        requested.append(url)
        assert timeout == 30.0
        parsed = urlsplit(url)
        assert parsed.scheme == "https"
        assert parsed.netloc == config.JOURNAL_HOST
        assert parsed.path == "/plosone/article/file"
        params = parse_qs(parsed.query)
        assert params["type"] == ["manuscript"]
        return synthetic_xml(params["id"][0], journal="PLoS ONE")

    summary = run_download(tmp_path, fetch)
    assert summary.accepted == DOIS
    assert summary.duplicate == []
    assert summary.conflict == {}
    assert summary.failed == {}
    assert summary.pending == []
    assert len(requested) == 15
    assert all("synthetic-unselected" not in url for url in requested)
    manifest = tmp_path / "data/pilot/manifest.jsonl"
    records = [
        json.loads(line)
        for line in manifest.read_text(encoding="utf-8").splitlines()
    ]
    assert len(records) == 15
    first = records[0]
    assert set(first) == {
        "doi",
        "original_doi",
        "source_url",
        "retrieved_at",
        "xml_sha256",
        "license",
        "raw_xml_path",
        "query_provenance",
    }
    assert first["original_doi"] == DOIS[0].upper()
    assert first["retrieved_at"] == NOW.isoformat()
    assert first["query_provenance"] == ARMS
    assert (
        first["raw_xml_path"] == f"data/raw/plos/{quote(DOIS[0], safe='')}.xml"
    )
    raw = (tmp_path / first["raw_xml_path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == first["xml_sha256"]
    assert first["license"] == "https://creativecommons.org/licenses/by/4.0/"
    assert b"\r\n" not in manifest.read_bytes()


def test_validation_aborts_before_request_and_lists_errors(
    tmp_path: Path,
) -> None:
    """Invalid selection prevents every HTTP request and reports all errors."""
    screening, selection, candidates, manifest, raw_dir = setup_inputs(tmp_path)
    content = selection.read_text(encoding="utf-8")
    selection.write_text(
        content.replace("SYNTHETIC review", "", 1).replace(
            "SYNTHETIC topic 0", "", 1
        ),
        encoding="utf-8",
    )

    def fetch(url: str, timeout: float) -> bytes:
        raise AssertionError("Validation must precede HTTP")

    with pytest.raises(ValueError) as error:
        download_selected(
            screening_path=screening,
            selection_path=selection,
            candidate_path=candidates,
            manifest_path=manifest,
            raw_dir=raw_dir,
            repo_root=tmp_path,
            fetch=fetch,
            sleep=lambda _: None,
            clock=lambda: 0.0,
            now=lambda: NOW,
        )
    assert "reason" in str(error.value)
    assert "topic" in str(error.value)
    assert not manifest.exists()


def test_unverified_journal_never_requests(tmp_path: Path) -> None:
    """Unknown journal routes fail each selected DOI without HTTP."""

    def fetch(url: str, timeout: float) -> bytes:
        raise AssertionError("Unverified route must not be fetched")

    summary = run_download(tmp_path, fetch, journal="SYNTHETIC unknown journal")
    assert summary.accepted == []
    assert summary.failed == {
        doi: "journal route not verified: SYNTHETIC unknown journal"
        for doi in DOIS
    }


@pytest.mark.parametrize(
    ("bad_xml", "reason"),
    [
        (b"<article>", "XML"),
        (
            synthetic_xml(DOIS[0], article_type="review-article"),
            "research-article",
        ),
        (synthetic_xml(DOIS[0], language="fr"), "language"),
        (synthetic_xml(DOIS[0], license_href=""), "license"),
        (synthetic_xml("10.9999/synthetic-wrong"), "DOI"),
        (synthetic_xml(DOIS[0], journal="SYNTHETIC other journal"), "journal"),
        (
            synthetic_xml(DOIS[0]).replace(
                b"<article-title>SYNTHETIC title</article-title>",
                b"<article-title/>",
            ),
            "title",
        ),
    ],
)
def test_xml_gate_rejects_without_storage(
    tmp_path: Path, bad_xml: bytes, reason: str
) -> None:
    """Each JATS gate fails visibly and leaves no article artifact."""

    def fetch(url: str, timeout: float) -> bytes:
        doi = parse_qs(urlsplit(url).query)["id"][0]
        return bad_xml if doi == DOIS[0] else synthetic_xml(doi)

    summary = run_download(tmp_path, fetch)
    assert reason.lower() in summary.failed[DOIS[0]].lower()
    assert DOIS[0] not in summary.accepted
    assert not (
        tmp_path / "data/raw/plos" / f"{quote(DOIS[0], safe='')}.xml"
    ).exists()
    records = [
        json.loads(line)
        for line in (tmp_path / "data/pilot/manifest.jsonl")
        .read_text()
        .splitlines()
    ]
    assert DOIS[0] not in {record["doi"] for record in records}


def test_duplicate_conflict_and_interrupted_run(tmp_path: Path) -> None:
    """Reruns refetch, preserve conflicts, and repair an orphan raw file."""
    screening, selection, candidates, manifest, raw_dir = setup_inputs(tmp_path)
    versions = ["SYNTHETIC original", "SYNTHETIC changed"]

    def fetch(url: str, timeout: float) -> bytes:
        doi = parse_qs(urlsplit(url).query)["id"][0]
        return synthetic_xml(
            doi, title=versions[0] if doi == DOIS[0] else "SYNTHETIC title"
        )

    def acquire() -> object:
        return download_selected(
            screening_path=screening,
            selection_path=selection,
            candidate_path=candidates,
            manifest_path=manifest,
            raw_dir=raw_dir,
            repo_root=tmp_path,
            fetch=fetch,
            sleep=lambda _: None,
            clock=lambda: 0.0,
            now=lambda: NOW,
        )

    first = acquire()
    assert first.accepted == DOIS
    old_manifest = manifest.read_bytes()
    raw_path = raw_dir / f"{quote(DOIS[0], safe='')}.xml"
    old_raw = raw_path.read_bytes()
    second = acquire()
    assert second.duplicate == DOIS
    assert manifest.read_bytes() == old_manifest
    versions[0] = "SYNTHETIC changed"
    third = acquire()
    new_raw = synthetic_xml(DOIS[0], title=versions[0])
    assert DOIS[0] in third.conflict
    assert hashlib.sha256(old_raw).hexdigest() in third.conflict[DOIS[0]]
    assert hashlib.sha256(new_raw).hexdigest() in third.conflict[DOIS[0]]
    assert raw_path.read_bytes() == old_raw
    assert manifest.read_bytes() == old_manifest
    digest_prefix = hashlib.sha256(new_raw).hexdigest()[:12]
    conflict_path = (
        raw_dir / "conflicts" / f"{quote(DOIS[0], safe='')}.{digest_prefix}.xml"
    )
    assert conflict_path.read_bytes() == new_raw
    manifest.write_text(
        "".join(
            line + "\n"
            for line in old_manifest.decode().splitlines()
            if json.loads(line)["doi"] != DOIS[0]
        ),
        encoding="utf-8",
    )
    fourth = acquire()
    assert DOIS[0] in fourth.accepted
    assert raw_path.read_bytes() == new_raw
    assert (
        sum(
            json.loads(line)["doi"] == DOIS[0]
            for line in manifest.read_text().splitlines()
        )
        == 1
    )


def test_duplicate_restores_missing_raw_xml_without_changing_manifest(
    tmp_path: Path,
) -> None:
    """A matching refetch restores gitignored raw XML on a fresh clone."""

    def fetch(url: str, timeout: float) -> bytes:
        assert timeout == 30.0
        doi = parse_qs(urlsplit(url).query)["id"][0]
        return synthetic_xml(doi)

    first = run_download(tmp_path, fetch)
    assert first.accepted == DOIS
    manifest = tmp_path / "data/pilot/manifest.jsonl"
    manifest_before = manifest.read_bytes()
    raw_path = tmp_path / "data/raw/plos" / f"{quote(DOIS[0], safe='')}.xml"
    expected_bytes = raw_path.read_bytes()
    raw_path.unlink()

    second = run_download(tmp_path, fetch)

    assert second.duplicate == DOIS
    assert second.failed == {}
    assert raw_path.read_bytes() == expected_bytes
    record = json.loads(manifest_before.splitlines()[0])
    assert (
        hashlib.sha256(raw_path.read_bytes()).hexdigest()
        == record["xml_sha256"]
    )
    assert manifest.read_bytes() == manifest_before


def test_duplicate_preserves_raw_xml_with_wrong_local_digest(
    tmp_path: Path,
) -> None:
    """A corrupt local raw file is reported, never silently overwritten."""

    def fetch(url: str, timeout: float) -> bytes:
        assert timeout == 30.0
        doi = parse_qs(urlsplit(url).query)["id"][0]
        return synthetic_xml(doi)

    first = run_download(tmp_path, fetch)
    assert first.accepted == DOIS
    manifest = tmp_path / "data/pilot/manifest.jsonl"
    manifest_before = manifest.read_bytes()
    raw_path = tmp_path / "data/raw/plos" / f"{quote(DOIS[0], safe='')}.xml"
    corrupt_bytes = b"SYNTHETIC local corruption"
    raw_path.write_bytes(corrupt_bytes)

    second = run_download(tmp_path, fetch)

    assert DOIS[0] not in second.duplicate
    assert DOIS[0] in second.failed
    assert (
        "local raw XML does not match manifest SHA256" in second.failed[DOIS[0]]
    )
    assert raw_path.read_bytes() == corrupt_bytes
    assert manifest.read_bytes() == manifest_before


def test_conflict_still_preserves_raw_and_saves_fetched_bytes(
    tmp_path: Path,
) -> None:
    """A different fetched digest remains a conflict with separate evidence."""
    title = ["SYNTHETIC original"]

    def fetch(url: str, timeout: float) -> bytes:
        assert timeout == 30.0
        doi = parse_qs(urlsplit(url).query)["id"][0]
        return synthetic_xml(
            doi, title=title[0] if doi == DOIS[0] else "SYNTHETIC title"
        )

    first = run_download(tmp_path, fetch)
    assert first.accepted == DOIS
    manifest = tmp_path / "data/pilot/manifest.jsonl"
    manifest_before = manifest.read_bytes()
    raw_path = tmp_path / "data/raw/plos" / f"{quote(DOIS[0], safe='')}.xml"
    raw_before = raw_path.read_bytes()
    title[0] = "SYNTHETIC changed"
    fetched = synthetic_xml(DOIS[0], title=title[0])

    second = run_download(tmp_path, fetch)

    assert DOIS[0] in second.conflict
    assert raw_path.read_bytes() == raw_before
    assert manifest.read_bytes() == manifest_before
    digest_prefix = hashlib.sha256(fetched).hexdigest()[:12]
    conflict_name = f"{quote(DOIS[0], safe='')}.{digest_prefix}.xml"
    conflict_path = raw_path.parent / "conflicts" / conflict_name
    assert conflict_path.read_bytes() == fetched


def test_cap_marks_remaining_selected_dois_pending(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The request cap leaves untouched selected articles pending."""
    monkeypatch.setattr(config, "MAX_REQUESTS_PER_RUN", 2)
    screening, selection, candidates, manifest, raw_dir = setup_inputs(tmp_path)
    calls = 0

    def fetch(url: str, timeout: float) -> bytes:
        nonlocal calls
        calls += 1
        return synthetic_xml(parse_qs(urlsplit(url).query)["id"][0])

    summary = download_selected(
        screening_path=screening,
        selection_path=selection,
        candidate_path=candidates,
        manifest_path=manifest,
        raw_dir=raw_dir,
        repo_root=tmp_path,
        fetch=fetch,
        sleep=lambda _: None,
        clock=lambda: 0.0,
        now=lambda: NOW,
    )
    assert calls == 2
    assert summary.accepted == DOIS[:2]
    assert summary.pending == DOIS[2:]
