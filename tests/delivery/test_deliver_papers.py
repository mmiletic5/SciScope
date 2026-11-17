"""SYNTHETIC offline T002 RED tests for the pure paper builder."""

from __future__ import annotations

import builtins
import io
import socket
from copy import deepcopy
from pathlib import Path
from typing import Any, NoReturn

import pytest
from delivery_fixtures import (
    DOI,
    PAPER_FIELDS,
    acquisition_manifest,
    metadata,
    paper,
)

from sciscope.delivery.papers import (
    PaperBuildError,
    build_papers,
    derive_publication_year,
)


def test_build_papers_preserves_raw_values_order_and_exclusions() -> None:
    """Join normalized keys in DOI order and preserve raw allowlisted values."""
    first, source = metadata(), acquisition_manifest()
    second, other_source = metadata(), acquisition_manifest()
    second.update(
        doi="10.1234/synthetic.b",
        language="en",
        license="https://example.invalid/license",
    )
    other_source.update(
        doi="DOI:10.1234/SYNTHETIC.B", license=second["license"]
    )
    source["doi"] = "https://doi.org/10.1234/SYNTHETIC.A"
    # Excluded and misleading upstream keys must never override ownership.
    first.update(
        original_doi="SYNTHETIC excluded",
        raw_xml_path="SYNTHETIC",
        query_provenance=["SYNTHETIC"],
        publication_year=9999,
        source_url="SYNTHETIC wrong owner",
    )
    source["title"] = "SYNTHETIC wrong owner"
    inputs = ([second, first], [source, other_source])
    before = deepcopy(inputs)
    result = build_papers(*inputs)
    expected_second = paper()
    expected_second.update(
        doi=second["doi"], language="en", license=second["license"]
    )
    assert type(result) is tuple
    assert result == (paper(), expected_second)
    assert all(tuple(row) == PAPER_FIELDS for row in result)
    assert result[0]["subjects"] == [
        "Research Article",
        "SYNTHETIC Z",
        "SYNTHETIC A",
    ]
    assert result[0]["authors"] == [{"surname": "Synthetic", "given_names": ""}]
    assert inputs == before


@pytest.mark.parametrize(
    "date,year",
    [
        ("2024", 2024),
        ("2024-02", 2024),
        ("2024-02-29", 2024),
        ("1500", 1500),
        ("0001-01-01", 1),
    ],
)
def test_derive_publication_year_supported_precision(
    date: str, year: int
) -> None:
    """Derive leading digits without an unauthorized 1600 minimum."""
    result = derive_publication_year(date)
    assert type(result) is int and result == year


@pytest.mark.parametrize("date", ["2024", "2024-02", "2024-02-29"])
def test_builder_keeps_publication_date_precision(date: str) -> None:
    """Preserve source date text and derive only the integer year."""
    row = metadata()
    row["publication_date"] = date
    result = build_papers([row], [acquisition_manifest()])
    assert result[0]["publication_date"] == date
    assert result[0]["publication_year"] == 2024


BAD_DATES = (
    "",
    "SYNTHETIC-invalid",
    "0000",
    "24",
    "20240",
    "2024-00",
    "2024-13",
    "2024-1",
    "2024-02-30",
    "2023-02-29",
    "2024-01-00",
    "2024-01-32",
    "2024-01-01-extra",
    "2024\n",
    " 2024",
    "2024 ",
    "２０２４",
)


@pytest.mark.parametrize("date", BAD_DATES)
def test_derive_publication_year_rejects_invalid_dates(date: str) -> None:
    """Reject malformed precision and impossible calendar dates safely."""
    with pytest.raises(PaperBuildError) as caught:
        derive_publication_year(date)
    assert caught.value.codes == ("paper-invalid-publication-date",)
    assert str(caught.value) == "paper-invalid-publication-date"


def _failure_cases() -> tuple[
    tuple[str, list[Any], list[Any], tuple[str, ...]], ...
]:
    """Construct independent fresh SYNTHETIC join and validation failures."""
    cases: list[tuple[str, list[Any], list[Any], tuple[str, ...]]] = []
    for side in ("metadata", "manifest"):
        left, right = [metadata()], [acquisition_manifest()]
        rows = left if side == "metadata" else right
        duplicate = deepcopy(rows[0])
        duplicate["doi"] = "doi:10.1234/SYNTHETIC.A"
        rows.append(duplicate)
        cases.append(
            (f"duplicate-{side}", left, right, (f"paper-duplicate-{side}-doi",))
        )
    cases.extend(
        (
            (
                "missing-metadata",
                [],
                [acquisition_manifest()],
                ("paper-missing-metadata",),
            ),
            ("missing-manifest", [metadata()], [], ("paper-missing-manifest",)),
        )
    )
    for side in ("metadata", "manifest"):
        for label, field, value, code in (
            (
                "invalid-doi",
                "doi",
                "SYNTHETIC invalid DOI",
                "paper-invalid-doi",
            ),
            ("doi-type", "doi", True, "paper-malformed-record"),
            ("license-null", "license", None, "paper-malformed-record"),
        ):
            left, right = [metadata()], [acquisition_manifest()]
            (left if side == "metadata" else right)[0][field] = value
            codes = (code,)
            if field == "doi":
                missing = "metadata" if side == "metadata" else "manifest"
                codes = tuple(sorted((*codes, f"paper-missing-{missing}")))
            cases.append((f"{side}-{label}", left, right, codes))
        for bad in (None, [], "SYNTHETIC non-object"):
            left, right = [metadata()], [acquisition_manifest()]
            rows = left if side == "metadata" else right
            rows.append(bad)
            cases.append(
                (
                    f"{side}-non-object-{type(bad).__name__}",
                    left,
                    right,
                    ("paper-malformed-record",),
                )
            )
        for field in (
            metadata() if side == "metadata" else acquisition_manifest()
        ):
            if field in (
                "abstract",
                "original_doi",
                "raw_xml_path",
                "query_provenance",
            ):
                continue
            left, right = [metadata()], [acquisition_manifest()]
            del (left if side == "metadata" else right)[0][field]
            codes = ("paper-malformed-record",)
            if field == "doi":
                codes = tuple(sorted((*codes, f"paper-missing-{side}")))
            cases.append(
                (
                    f"{side}-missing-{field}",
                    left,
                    right,
                    codes,
                )
            )
    for date in BAD_DATES:
        row = metadata()
        row["publication_date"] = date
        cases.append(
            (
                f"date-{date!r}",
                [row],
                [acquisition_manifest()],
                ("paper-invalid-publication-date",),
            )
        )
    for field, value in (
        ("title", ""),
        ("journal", ""),
        ("authors", []),
        ("authors", [{"surname": "", "given_names": ""}]),
        ("authors", [{"surname": "SYNTHETIC", "given_names": None}]),
        ("subjects", "SYNTHETIC"),
        ("language", None),
        ("publication_date", 2024),
    ):
        row = metadata()
        row[field] = value
        cases.append(
            (
                f"malformed-{field}-{value!r}",
                [row],
                [acquisition_manifest()],
                ("paper-malformed-record",),
            )
        )
    source = acquisition_manifest()
    source["license"] = "SYNTHETIC different permission"
    cases.append(
        (
            "license-mismatch",
            [metadata()],
            [source],
            ("paper-license-mismatch",),
        )
    )
    return tuple(cases)


FAILURES = _failure_cases()


def test_paper_build_error_exposes_sorted_unique_codes() -> None:
    """Carry only a stable sorted tuple, with no input values in the message."""
    error = PaperBuildError(
        (
            "paper-missing-metadata",
            "paper-invalid-doi",
            "paper-invalid-doi",
        )
    )
    assert error.codes == ("paper-invalid-doi", "paper-missing-metadata")
    assert str(error) == "paper-invalid-doi, paper-missing-metadata"


@pytest.mark.parametrize(
    "name,left,right,codes", FAILURES, ids=[case[0] for case in FAILURES]
)
def test_build_papers_failure_matrix(
    name: str,
    left: list[Any],
    right: list[Any],
    codes: tuple[str, ...],
) -> None:
    """Reject each failure with exact sanitized codes and unchanged inputs."""
    before = deepcopy((left, right))
    with pytest.raises(PaperBuildError) as caught:
        build_papers(left, right)
    assert caught.value.codes == codes, name
    assert str(caught.value) == ", ".join(codes)
    assert (left, right) == before


def test_build_papers_collects_all_problems_before_raising() -> None:
    """Collect independent duplicate, join, license, date and shape issues."""
    row, source = metadata(), acquisition_manifest()
    row["publication_date"] = "SYNTHETIC invalid date"
    source["license"] = "SYNTHETIC mismatch"
    orphan = metadata()
    orphan["doi"] = "10.1234/synthetic.orphan-metadata"
    other_orphan = acquisition_manifest()
    other_orphan["doi"] = "10.1234/synthetic.orphan-manifest"
    invalid = metadata()
    invalid["doi"] = "SYNTHETIC invalid doi"
    left = [row, deepcopy(row), orphan, invalid, None]
    right = [source, deepcopy(source), other_orphan, []]
    before = deepcopy((left, right))
    with pytest.raises(PaperBuildError) as caught:
        build_papers(left, right)
    expected = tuple(
        sorted(
            (
                "paper-duplicate-metadata-doi",
                "paper-duplicate-manifest-doi",
                "paper-missing-metadata",
                "paper-missing-manifest",
                "paper-license-mismatch",
                "paper-invalid-publication-date",
                "paper-invalid-doi",
                "paper-malformed-record",
            )
        )
    )
    assert caught.value.codes == expected
    assert str(caught.value) == ", ".join(expected)
    assert (left, right) == before


def test_build_papers_requires_equal_doi_sets_even_with_equal_counts() -> None:
    """Reject distinct singleton DOI sets even when their lengths agree."""
    source = acquisition_manifest()
    source["doi"] = "10.1234/synthetic.other"
    with pytest.raises(PaperBuildError) as caught:
        build_papers([metadata()], [source])
    assert caught.value.codes == (
        "paper-missing-manifest",
        "paper-missing-metadata",
    )


def test_build_papers_does_no_io(monkeypatch: pytest.MonkeyPatch) -> None:
    """Build and reject records while filesystem and network are blocked."""
    left, right = metadata(), acquisition_manifest()

    def forbidden(*args: object, **kwargs: object) -> NoReturn:
        raise AssertionError("Pure paper builder attempted I/O")

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", forbidden)
        patch.setattr(io, "open", forbidden)
        patch.setattr(Path, "open", forbidden)
        patch.setattr(socket, "socket", forbidden)
        patch.setattr(socket, "create_connection", forbidden)
        assert build_papers([left], [right])[0]["doi"] == DOI
        left["publication_date"] = "SYNTHETIC invalid date"
        with pytest.raises(PaperBuildError):
            build_papers([left], [right])
