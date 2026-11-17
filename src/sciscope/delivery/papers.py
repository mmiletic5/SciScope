"""Pure, collect-all paper assembly from normalized F001 DOI joins."""

from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from datetime import date
from typing import cast

from sciscope.chunking.validate import is_json_string
from sciscope.delivery.contract import (
    PAPER_FIELDS,
    PUBLICATION_DATE_PATTERN,
    _paper_field_codes,
)
from sciscope.plos_pilot.doi import normalize_doi

_METADATA_FIELDS = (
    "title",
    "authors",
    "journal",
    "publication_date",
    "article_type",
    "subjects",
    "license",
    "language",
)
_MANIFEST_FIELDS = ("source_url", "retrieved_at", "xml_sha256", "license")
_ERROR_CODES = frozenset(
    {
        "paper-duplicate-metadata-doi",
        "paper-duplicate-manifest-doi",
        "paper-missing-metadata",
        "paper-missing-manifest",
        "paper-license-mismatch",
        "paper-invalid-publication-date",
        "paper-invalid-doi",
        "paper-malformed-record",
    }
)


class PaperBuildError(ValueError):
    """Collected paper problems containing only sorted sanitized codes.

    Attributes:
        codes: Sorted unique codes without input values or identifiers.
    """

    def __init__(self, codes: Sequence[str]) -> None:
        """Keep approved codes, replacing unknown values with a safe failure.

        Args:
            codes: Collected failure codes to deduplicate and sort.
        """
        self.codes = tuple(
            sorted(
                {
                    code
                    if type(code) is str and code in _ERROR_CODES
                    else "paper-malformed-record"
                    for code in codes
                }
            )
        )
        super().__init__(", ".join(self.codes))


def derive_publication_year(date_text: str) -> int:
    """Derive a calendar-exact year from supported ASCII F001 date precision.

    Args:
        date_text: Year, year-month or full-date text without whitespace.

    Returns:
        The leading year as an integer, with no 1600 minimum.

    Raises:
        PaperBuildError: If precision, calendar date or year is invalid.
    """
    year: int | None = None
    if is_json_string(date_text) and PUBLICATION_DATE_PATTERN.search(date_text):
        parts = [int(part) for part in date_text.split("-")]
        try:
            date(
                parts[0],
                parts[1] if len(parts) > 1 else 1,
                parts[2] if len(parts) > 2 else 1,
            )
        except ValueError:
            pass
        else:
            year = parts[0]
    if year is None:
        raise PaperBuildError(("paper-invalid-publication-date",))
    return year


def _index(
    records: Sequence[object],
    side: str,
    problems: set[str],
) -> dict[str, list[dict[str, object]]]:
    """Index valid DOI keys even when other fields are missing or malformed."""
    indexed: dict[str, list[dict[str, object]]] = {}
    fields = _METADATA_FIELDS if side == "metadata" else _MANIFEST_FIELDS
    for value in records:
        if not isinstance(value, dict):
            problems.add("paper-malformed-record")
            continue
        # Copy only retained fields; excluded values are never traversed.
        row = {field: value[field] for field in fields if field in value}
        raw_doi = value.get("doi")
        doi: str | None = None
        if not is_json_string(raw_doi):
            problems.add("paper-malformed-record")
        else:
            try:
                doi = normalize_doi(cast(str, raw_doi)).doi
            except ValueError:
                problems.add("paper-invalid-doi")
        _check_fields(row, fields, problems)
        if doi is not None:
            row["doi"] = doi
            indexed.setdefault(doi, []).append(row)
    if any(len(group) > 1 for group in indexed.values()):
        problems.add(f"paper-duplicate-{side}-doi")
    return indexed


def _check_fields(
    row: dict[str, object],
    fields: tuple[str, ...],
    problems: set[str],
) -> None:
    """Check each owned field independently, separating calendar errors."""
    for field in fields:
        if field not in row:
            problems.add("paper-malformed-record")
            continue
        value = row[field]
        if field == "publication_date":
            if not is_json_string(value):
                problems.add("paper-malformed-record")
            else:
                try:
                    row["publication_year"] = derive_publication_year(
                        cast(str, value)
                    )
                except PaperBuildError as error:
                    problems.update(error.codes)
            continue
        if _paper_field_codes(field, value):
            problems.add("paper-malformed-record")


def build_papers(
    metadata_records: Sequence[object],
    manifest_records: Sequence[object],
) -> tuple[dict[str, object], ...]:
    """Join equal unique normalized DOI sets while preserving raw field values.

    Args:
        metadata_records: Parsed F001 metadata records, never mutated.
        manifest_records: Parsed F001 acquisition records, never mutated.

    Returns:
        Fresh paper dictionaries in normalized DOI and exact field order.

    Raises:
        PaperBuildError: After collecting every safely detectable join and
            validation problem, without propagating source exception text.
    """
    problems: set[str] = set()
    metadata = _index(metadata_records, "metadata", problems)
    manifest = _index(manifest_records, "manifest", problems)
    if metadata.keys() - manifest.keys():
        problems.add("paper-missing-manifest")
    if manifest.keys() - metadata.keys():
        problems.add("paper-missing-metadata")
    shared = metadata.keys() & manifest.keys()
    for doi in shared:
        licenses = [
            row["license"]
            for row in (*metadata[doi], *manifest[doi])
            if is_json_string(row.get("license"))
        ]
        if licenses and any(value != licenses[0] for value in licenses[1:]):
            problems.add("paper-license-mismatch")
    if problems:
        raise PaperBuildError(tuple(problems))
    papers: list[dict[str, object]] = []
    for doi in sorted(shared):
        description, source = metadata[doi][0], manifest[doi][0]
        combined = {**description, **source}
        papers.append(
            {field: deepcopy(combined[field]) for field in PAPER_FIELDS}
        )
    return tuple(papers)
