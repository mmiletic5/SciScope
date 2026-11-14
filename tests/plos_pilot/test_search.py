"""Offline behavior checks for synthetic PLOS Solr responses."""

import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import pytest

from sciscope.plos_pilot import config
from sciscope.plos_pilot.search import search_candidates


class FakeClock:
    """Record virtual request starts without real sleeping."""

    def __init__(self) -> None:
        """Initialize virtual time and the request-start log."""
        self.time = 0.0
        self.starts: list[float] = []

    def __call__(self) -> float:
        """Return current virtual time."""
        return self.time

    def sleep(self, seconds: float) -> None:
        """Advance virtual time by a requested delay."""
        self.time += seconds


def _document(doi: str) -> dict[str, str]:
    return {
        "id": f"https://journals.plos.org/plosone/article?id={doi}",
        "title": "SYNTHETIC title",
        "journal": "SYNTHETIC journal",
        "publication_date": "2026-01-01",
        "abstract": "SYNTHETIC abstract",
    }


def test_paged_search_merges_arms_and_reports_hits(tmp_path: Path) -> None:
    """Six arms page independently and retain every matching query."""
    clock = FakeClock()
    seen: list[dict[str, list[str]]] = []

    def fetch(url: str, timeout: float) -> bytes:
        assert timeout >= 5.0
        clock.starts.append(clock.time)
        params = parse_qs(urlsplit(url).query)
        seen.append(params)
        assert params["sort"] == ["id asc"]
        assert params["fq"] == list(config.FILTER_QUERIES)
        assert params["fl"] == [",".join(config.SOLR_FIELDS)]
        assert int(params["rows"][0]) <= 100
        assert params["wt"] == ["json"]
        arm = params["q"][0]
        start = int(params["start"][0])
        docs = [_document("10.9999/SYNTHETIC")]
        if arm == config.QUERY_ARMS[0]:
            docs.append(_document("10.9999/SYNTHETIC-2"))
        payload = {
            "response": {"numFound": len(docs), "docs": docs[start : start + 1]}
        }
        return json.dumps(payload).encode()

    output = tmp_path / "candidates.jsonl"
    result = search_candidates(output, fetch, clock.sleep, clock, rows=1)
    records = [json.loads(line) for line in output.read_text().splitlines()]
    assert len(records) == 2
    assert len(records[0]["arms"]) == 6
    assert records[0]["doi"] == "10.9999/synthetic"
    assert (
        records[0]["original_doi"]
        == "https://journals.plos.org/plosone/article?id=10.9999/SYNTHETIC"
    )
    assert records[0]["title"] == "SYNTHETIC title"
    assert records[0]["journal"] == "SYNTHETIC journal"
    assert records[0]["publication_date"] == "2026-01-01"
    assert records[0]["abstract"] == "SYNTHETIC abstract"
    assert set(records[0]["arms"][0]) == {"q", "fq", "numFound", "date"}
    assert len(result.arm_hits) == 6
    assert result.arm_hits[config.QUERY_ARMS[0]] == 2
    assert result.hit_label == "hits"
    assert {params["q"][0] for params in seen} == set(config.QUERY_ARMS)
    assert all(
        b - a >= 6.0
        for a, b in zip(clock.starts, clock.starts[1:], strict=False)
    )


def test_retry_after_and_interrupted_output(tmp_path: Path) -> None:
    """Retry starts obey pacing and Retry-After; completed pages survive."""
    clock = FakeClock()
    calls = 0
    output = tmp_path / "candidates.jsonl"

    def fetch(url: str, timeout: float) -> bytes:
        nonlocal calls
        del timeout
        calls += 1
        clock.starts.append(clock.time)
        if calls == 1:
            raise HTTPError(url, 429, "busy", {"Retry-After": "9"}, None)
        params = parse_qs(urlsplit(url).query)
        if calls == 3:
            raise RuntimeError("SYNTHETIC interruption")
        docs = (
            [_document("10.9999/SYNTHETIC")]
            if params["q"][0] == config.QUERY_ARMS[0]
            else []
        )
        return json.dumps(
            {"response": {"numFound": len(docs), "docs": docs}}
        ).encode()

    with pytest.raises(RuntimeError, match="interruption"):
        search_candidates(output, fetch, clock.sleep, clock)
    assert clock.starts[:2] == [0.0, 9.0]
    assert output.exists()
    assert json.loads(output.read_text().strip())["doi"] == "10.9999/synthetic"
    assert list(tmp_path.glob("*.tmp")) == []


def test_request_cap_stops_before_next_fetch(tmp_path: Path) -> None:
    """The run cap is checked before request 301."""
    clock = FakeClock()
    calls = 0

    def fetch(url: str, timeout: float) -> bytes:
        nonlocal calls
        del url, timeout
        calls += 1
        return json.dumps(
            {
                "response": {
                    "numFound": 1000,
                    "docs": [_document("10.9999/SYNTHETIC")],
                }
            }
        ).encode()

    with pytest.raises(RuntimeError, match="300"):
        search_candidates(
            tmp_path / "candidates.jsonl", fetch, clock.sleep, clock, rows=1
        )
    assert calls == 300


def test_public_request_runner_forwards_xml_timeout() -> None:
    """The shared runner accepts the XML request's 30-second timeout."""
    from sciscope.plos_pilot.search import RequestRunner

    clock = FakeClock()
    seen: list[float] = []

    def fetch(url: str, timeout: float) -> bytes:
        del url
        seen.append(timeout)
        return b"SYNTHETIC"

    runner = RequestRunner(fetch, clock.sleep, clock)
    assert (
        runner.get(
            "https://journals.plos.org/plosone/article/file", timeout=30.0
        )
        == b"SYNTHETIC"
    )
    assert seen == [30.0]
