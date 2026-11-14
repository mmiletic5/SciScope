"""Acquire only human-selected PLOS JATS XML with source provenance."""

import hashlib
import json
import os
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote
from xml.etree import ElementTree as ET

from sciscope.plos_pilot import config
from sciscope.plos_pilot.doi import normalize_doi
from sciscope.plos_pilot.metadata import parse_article
from sciscope.plos_pilot.search import (
    Clock,
    Fetch,
    RequestCapReached,
    RequestRunner,
    Sleep,
    _http_fetch,
)
from sciscope.plos_pilot.selection import read_selection, validate_selection

Now = Callable[[], datetime]


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class DownloadSummary:
    """Selected DOI outcomes for a single download run."""

    accepted: list[str] = field(default_factory=list)
    duplicate: list[str] = field(default_factory=list)
    conflict: dict[str, str] = field(default_factory=dict)
    failed: dict[str, str] = field(default_factory=dict)
    pending: list[str] = field(default_factory=list)


def _atomic_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, suffix=".tmp", delete=False
        ) as temporary:
            temporary_name = temporary.name
            temporary.write(content)
        os.replace(temporary_name, path)
    finally:
        if temporary_name is not None and os.path.exists(temporary_name):
            os.unlink(temporary_name)


def _records(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]


def _candidate_index(path: Path) -> dict[str, dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    for record in _records(path):
        doi = normalize_doi(record["doi"]).doi
        if doi not in candidates:
            candidates[doi] = {**record, "arms": list(record.get("arms", []))}
        else:
            candidates[doi]["arms"].extend(record.get("arms", []))
    return candidates


def _journal_key(journal: str) -> str:
    return "".join(
        character for character in journal.casefold() if character.isalnum()
    )


def _verify_xml(xml: bytes, doi: str, journal: str) -> str:
    root, front_matter = parse_article(xml)
    if front_matter["article_type"] != "research-article":
        raise ValueError("article-type must be research-article")
    language = front_matter["language"].casefold()
    if language != "en" and not language.startswith("en-"):
        raise ValueError(
            f"language must be English: {front_matter['language']}"
        )
    if _journal_key(front_matter["journal"]) != _journal_key(journal):
        raise ValueError(
            f"XML journal {front_matter['journal']!r} "
            f"differs from candidate {journal!r}"
        )
    xml_doi = ""
    for element in root.iter():
        if (
            element.tag.rsplit("}", 1)[-1] == "article-id"
            and element.get("pub-id-type") == "doi"
        ):
            xml_doi = "".join(element.itertext()).strip()
            break
    if not xml_doi:
        raise ValueError("XML article-id DOI is missing")
    try:
        normalized_xml_doi = normalize_doi(xml_doi).doi
    except ValueError as error:
        raise ValueError(f"XML article-id DOI is invalid: {xml_doi}") from error
    if normalized_xml_doi != doi:
        raise ValueError(f"XML DOI {xml_doi} differs from selected DOI {doi}")
    return str(front_matter["license"])


def _append_manifest(path: Path, entry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as destination:
        destination.write(json.dumps(entry, ensure_ascii=False) + "\n")


def download_selected(
    screening_path: Path = Path("data/pilot/screening.tsv"),
    selection_path: Path = Path("data/pilot/selection.tsv"),
    candidate_path: Path = Path("data/pilot/candidates.jsonl"),
    manifest_path: Path = Path("data/pilot/manifest.jsonl"),
    raw_dir: Path = Path("data/raw/plos"),
    repo_root: Path = Path("."),
    fetch: Fetch = _http_fetch,
    sleep: Sleep = time.sleep,
    clock: Clock = time.monotonic,
    now: Now = _utc_now,
) -> DownloadSummary:
    """Refetch selected DOIs and preserve accepted or conflicting source bytes.

    Selection validation finishes before HTTP. An orphan raw XML file without a
    manifest entry is an interrupted run: equal fetched bytes complete its
    manifest entry; different fetched bytes replace it atomically before the
    entry is appended. Existing manifest entries never change on conflict.

    Args:
        screening_path: Reviewed decisions TSV.
        selection_path: Selected DOI TSV and sole download DOI source.
        candidate_path: Candidate journal and query-arm JSONL.
        manifest_path: Acquired source manifest JSONL.
        raw_dir: Raw XML output directory.
        repo_root: Root for repo-relative manifest paths.
        fetch: Injected HTTP fetch callable.
        sleep: Injected delay callable.
        clock: Injected monotonic clock callable.
        now: Injected UTC wall-clock callable.

    Returns:
        Accepted, duplicate, conflict, failed, and pending DOI outcomes.

    Raises:
        ValueError: If selection validation has any errors.
    """
    errors = validate_selection(screening_path, selection_path, candidate_path)
    if errors:
        raise ValueError("\n".join(errors))
    selection = read_selection(selection_path)
    candidates = _candidate_index(candidate_path)
    existing = (
        {record["doi"]: record for record in _records(manifest_path)}
        if manifest_path.exists()
        else {}
    )
    runner = RequestRunner(fetch, sleep, clock)
    summary = DownloadSummary()
    for index, row in enumerate(selection):
        doi = normalize_doi(row["doi"]).doi
        candidate = candidates[doi]
        journal = str(candidate.get("journal") or "")
        route = config.JOURNAL_ROUTES.get(journal.strip().upper())
        if route is None:
            summary.failed[doi] = f"journal route not verified: {journal}"
            continue
        url = (
            f"https://{config.JOURNAL_HOST}/{route}/article/file"
            f"?id={quote(doi, safe='')}&type=manuscript"
        )
        try:
            xml = runner.get(url, timeout=30.0)
        except RequestCapReached:
            summary.pending = [
                normalize_doi(remaining["doi"]).doi
                for remaining in selection[index:]
            ]
            break
        except RuntimeError as error:
            summary.failed[doi] = str(error)
            continue
        try:
            license_value = _verify_xml(xml, doi, journal)
            digest = hashlib.sha256(xml).hexdigest()
            name = quote(doi, safe="")
            raw_path = raw_dir / f"{name}.xml"
            old = existing.get(doi)
            if old is not None:
                old_digest = str(old["xml_sha256"])
                if old_digest == digest:
                    summary.duplicate.append(doi)
                else:
                    conflict_path = (
                        raw_dir / "conflicts" / f"{name}.{digest[:12]}.xml"
                    )
                    _atomic_bytes(conflict_path, xml)
                    summary.conflict[doi] = (
                        f"existing SHA256 {old_digest}; fetched SHA256 {digest}"
                    )
                continue
            if not raw_path.exists() or raw_path.read_bytes() != xml:
                _atomic_bytes(raw_path, xml)
            retrieved_at = now()
            if retrieved_at.tzinfo is None:
                raise ValueError("retrieved_at clock must be timezone aware")
            entry = {
                "doi": doi,
                "original_doi": row["doi"],
                "source_url": url,
                "retrieved_at": retrieved_at.astimezone(UTC).isoformat(),
                "xml_sha256": digest,
                "license": license_value,
                "raw_xml_path": raw_path.resolve()
                .relative_to(repo_root.resolve())
                .as_posix(),
                "query_provenance": [
                    {key: arm[key] for key in ("q", "fq", "numFound", "date")}
                    for arm in candidate["arms"]
                ],
            }
            _append_manifest(manifest_path, entry)
            existing[doi] = entry
            summary.accepted.append(doi)
        except (ValueError, OSError, KeyError, ET.ParseError) as error:
            summary.failed[doi] = str(error)
    return summary
