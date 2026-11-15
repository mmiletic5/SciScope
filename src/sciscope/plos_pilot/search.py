"""Search PLOS Solr and atomically write candidate JSONL.

Each JSONL candidate has ``doi``, ``original_doi``, ``id``, ``title``,
``journal``, ``publication_date``, ``abstract``, and ``arms``. Each arm has
``q``, ``fq``, ``numFound``, and ``date``. ``numFound`` is a hit count.
"""

import json
import os
import tempfile
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from http.client import HTTPException
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode

from sciscope.plos_pilot import config
from sciscope.plos_pilot.doi import normalize_doi

Fetch = Callable[[str, float], bytes]
Sleep = Callable[[float], None]
Clock = Callable[[], float]


@dataclass(frozen=True)
class SearchResult:
    """Per-arm Solr hit counts and the total unique candidate count."""

    arm_hits: dict[str, int]
    candidate_count: int
    request_count: int
    hit_label: str = "hits"


def _http_fetch(url: str, timeout: float) -> bytes:
    """Fetch one Solr response with the standard library."""
    with urllib.request.urlopen(url, timeout=timeout) as response:
        body: bytes = response.read()
        return body


class RequestCapReached(RuntimeError):
    """The shared per-run HTTP request cap was reached."""


class RequestRunner:
    """Enforce one paced request stream and its shared run cap."""

    def __init__(self, fetch: Fetch, sleep: Sleep, clock: Clock) -> None:
        """Store injected request and timing callables."""
        self.fetch = fetch
        self.sleep = sleep
        self.clock = clock
        self.last_start: float | None = None
        self.count = 0

    def _start(self, url: str, timeout: float) -> bytes:
        if self.count >= config.MAX_REQUESTS_PER_RUN:
            raise RequestCapReached("PLOS 300-request per-run cap reached")
        now = self.clock()
        if self.last_start is not None:
            wait = config.MIN_REQUEST_SPACING_SECONDS - (now - self.last_start)
            if wait > 0:
                self.sleep(wait)
        self.last_start = self.clock()
        self.count += 1
        return self.fetch(url, timeout)

    def get(self, url: str, timeout: float = 10.0) -> bytes:
        """Retry transient failures with bounded backoff and pacing.

        Args:
            url: Fixed-host PLOS request URL.
            timeout: Seconds allowed for each fetch attempt.

        Returns:
            Response bytes.
        """
        label = (
            "Solr"
            if url == config.SEARCH_URL
            or url.startswith(config.SEARCH_URL + "?")
            else "PLOS"
        )
        for attempt in range(3):
            try:
                return self._start(url, timeout)
            except HTTPError as error:
                if error.code != 429 and not 500 <= error.code <= 599:
                    raise RuntimeError(
                        f"Permanent {label} HTTP {error.code}: {url}"
                    ) from error
                if attempt == 2:
                    raise RuntimeError(
                        f"{label} HTTP {error.code} after retries: {url}"
                    ) from error
                retry_after = (
                    error.headers.get("Retry-After") if error.headers else None
                )
                try:
                    delay = float(retry_after) if retry_after else 0.0
                except ValueError:
                    delay = 0.0
                self.sleep(min(max(2.0**attempt, delay), 60.0))
            except (OSError, HTTPException) as error:
                if attempt == 2:
                    raise RuntimeError(
                        f"{label} request failed after retries: {url}"
                    ) from error
                self.sleep(2.0**attempt)
        raise AssertionError("Unreachable retry state")


def _write_candidates(
    path: Path, candidates: dict[str, dict[str, Any]]
) -> None:
    """Replace the complete JSONL file atomically after each successful page."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as temporary:
            temporary_name = temporary.name
            for doi in sorted(candidates):
                temporary.write(
                    json.dumps(candidates[doi], ensure_ascii=False) + "\n"
                )
        os.replace(temporary_name, path)
    finally:
        if temporary_name is not None and os.path.exists(temporary_name):
            os.unlink(temporary_name)


def _existing_candidates(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as source:
        records = (json.loads(line) for line in source if line.strip())
        return {record["doi"]: record for record in records}


def search_candidates(
    output_path: Path = Path("data/pilot/candidates.jsonl"),
    fetch: Fetch = _http_fetch,
    sleep: Sleep = time.sleep,
    clock: Clock = time.monotonic,
    *,
    rows: int = config.MAX_ROWS,
) -> SearchResult:
    """Page through six query arms and preserve completed candidate pages.

    Args:
        output_path: Candidate JSONL destination.
        fetch: Injected HTTP fetch callable taking URL and timeout.
        sleep: Injected sleep callable.
        clock: Injected monotonic clock callable.
        rows: Requested page size, from 1 through 100.

    Returns:
        Search hit counts and unique candidate count.

    Raises:
        ValueError: If the page size or a Solr response is invalid.
        RuntimeError: If requests fail or the per-run cap is reached.
    """
    if not 1 <= rows <= config.MAX_ROWS:
        raise ValueError("Solr rows must be between 1 and 100")
    candidates = _existing_candidates(output_path)
    runner = RequestRunner(fetch, sleep, clock)
    arm_hits: dict[str, int] = {}
    for query in config.QUERY_ARMS:
        start = 0
        while True:
            params: list[tuple[str, str | int]] = [
                ("q", query),
                *(
                    ("fq", filter_query)
                    for filter_query in config.FILTER_QUERIES
                ),
                ("fl", ",".join(config.SOLR_FIELDS)),
                ("rows", rows),
                ("start", start),
                ("sort", "id asc"),
                ("wt", "json"),
            ]
            url = config.SEARCH_URL + "?" + urlencode(params)
            try:
                response = json.loads(runner.get(url))
                result = response["response"]
                total = result["numFound"]
                documents = result["docs"]
                if (
                    not isinstance(total, int)
                    or total < 0
                    or not isinstance(documents, list)
                ):
                    raise ValueError("Invalid Solr response fields")
            except (json.JSONDecodeError, KeyError, TypeError) as error:
                raise ValueError(
                    f"Invalid Solr JSON response for {query}"
                ) from error
            arm_hits[query] = total
            date = datetime.now(UTC).date().isoformat()
            for document in documents:
                original_id = document["id"]
                normalized = normalize_doi(original_id)
                doi = normalized.doi
                if doi not in candidates:
                    candidates[doi] = {
                        "doi": doi,
                        "original_doi": normalized.original_doi,
                        "id": original_id,
                        "title": document.get("title"),
                        "journal": document.get("journal"),
                        "publication_date": document.get("publication_date"),
                        "abstract": document.get("abstract"),
                        "arms": [],
                    }
                arms: list[dict[str, Any]] = candidates[doi]["arms"]
                if not any(arm["q"] == query for arm in arms):
                    arms.append(
                        {
                            "q": query,
                            "fq": list(config.FILTER_QUERIES),
                            "numFound": total,
                            "date": date,
                        }
                    )
            _write_candidates(output_path, candidates)
            start += len(documents)
            if start >= total:
                break
            if not documents:
                raise ValueError(
                    f"Solr returned an empty page before {total} hits"
                )
    return SearchResult(arm_hits, len(candidates), runner.count)
