"""Read, write, and validate human PLOS pilot screening decisions.

The TSV contracts have exact column order and use UTF-8 with LF line endings.
Selection is a reviewed, included-class subset of the candidate corpus.
"""

import csv
import json
from collections.abc import Iterable, Mapping
from pathlib import Path

from sciscope.plos_pilot.doi import normalize_doi

SCREENING_HEADER = ("doi", "class", "reason", "topic")
SELECTION_HEADER = (*SCREENING_HEADER, "methods_checked")
INCLUDED_CLASSES = frozenset(("measured_mellifera", "honey_bee_unqualified"))
CODEBOOK_CLASSES = INCLUDED_CLASSES | frozenset(
    (
        "comparative_mellifera",
        "species_ambiguous",
        "background_only",
        "other_species_only",
    )
)


def _write_tsv(
    path: Path, header: tuple[str, ...], rows: Iterable[Mapping[str, str]]
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.writer(destination, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        for row in rows:
            writer.writerow([row.get(field, "") for field in header])


def write_screening(path: Path, rows: Iterable[Mapping[str, str]]) -> None:
    """Write reviewed candidate decisions using the exact screening header.

    Args:
        path: Output TSV path.
        rows: Human-entered screening rows.
    """
    _write_tsv(path, SCREENING_HEADER, rows)


def write_selection(path: Path, rows: Iterable[Mapping[str, str]]) -> None:
    """Write selected DOI decisions using the exact selection header.

    Args:
        path: Output TSV path.
        rows: Human-entered selection rows.
    """
    _write_tsv(path, SELECTION_HEADER, rows)


def _read_tsv(
    path: Path, header: tuple[str, ...]
) -> tuple[list[dict[str, str]], list[str], list[int]]:
    rows: list[dict[str, str]] = []
    errors: list[str] = []
    line_numbers: list[int] = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.reader(source, delimiter="\t")
            actual_header = next(reader, None)
            if actual_header != list(header):
                errors.append(
                    f"{path}: header must be exactly {', '.join(header)}"
                )
            previous_line = reader.line_num
            for values in reader:
                row_number = previous_line + 1
                previous_line = reader.line_num
                if not values:
                    continue
                if len(values) != len(header):
                    expected_columns = len(header)
                    errors.append(
                        f"{path}: row {row_number}: expected "
                        f"{expected_columns} columns, "
                        f"found {len(values)}"
                    )
                padded = values[: len(header)] + [""] * max(
                    0, len(header) - len(values)
                )
                rows.append(dict(zip(header, padded, strict=True)))
                line_numbers.append(row_number)
    except (OSError, UnicodeError, csv.Error) as error:
        errors.append(f"{path}: cannot read TSV: {error}")
    return rows, errors, line_numbers


def read_screening(path: Path) -> list[dict[str, str]]:
    """Read a screening TSV, rejecting an incorrect header or row width.

    Args:
        path: Input screening TSV path.

    Returns:
        Screening rows in file order.

    Raises:
        ValueError: If the file structure is invalid.
    """
    rows, errors, _ = _read_tsv(path, SCREENING_HEADER)
    if errors:
        raise ValueError("\n".join(errors))
    return rows


def read_selection(path: Path) -> list[dict[str, str]]:
    """Read a selection TSV, rejecting an incorrect header or row width.

    Args:
        path: Input selection TSV path.

    Returns:
        Selection rows in file order.

    Raises:
        ValueError: If the file structure is invalid.
    """
    rows, errors, _ = _read_tsv(path, SELECTION_HEADER)
    if errors:
        raise ValueError("\n".join(errors))
    return rows


def _candidate_dois(path: Path) -> tuple[set[str], list[str]]:
    dois: set[str] = set()
    errors: list[str] = []
    try:
        with path.open("r", encoding="utf-8") as source:
            for row_number, line in enumerate(source, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                    if not isinstance(record, dict):
                        raise ValueError("candidate must be a JSON object")
                    value = record["doi"]
                    if not isinstance(value, str):
                        raise ValueError("candidate DOI must be a string")
                    dois.add(normalize_doi(value).doi)
                except (json.JSONDecodeError, KeyError, ValueError) as error:
                    errors.append(
                        f"{path}: row {row_number}: invalid candidate: {error}"
                    )
    except (OSError, UnicodeError) as error:
        errors.append(f"{path}: cannot read candidates: {error}")
    return dois, errors


def _validate_review_rows(
    rows: list[dict[str, str]],
    line_numbers: list[int],
    source: Path,
    candidates: set[str],
    errors: list[str],
    *,
    selected: bool,
) -> set[str]:
    dois: set[str] = set()
    for row_number, row in zip(line_numbers, rows, strict=True):
        label = f"{source}: row {row_number}"
        try:
            doi = normalize_doi(row["doi"]).doi
        except ValueError as error:
            errors.append(f"{label}: {error}")
        else:
            if doi in dois:
                errors.append(f"{label}: duplicate normalized DOI {doi}")
            dois.add(doi)
            if doi not in candidates:
                errors.append(
                    f"{label}: DOI {doi} is absent from candidates.jsonl"
                )
        class_code = row["class"].strip()
        if class_code not in CODEBOOK_CLASSES:
            errors.append(f"{label}: unknown screening class {class_code!r}")
        elif selected and class_code not in INCLUDED_CLASSES:
            errors.append(
                f"{label}: excluded or borderline class cannot be selected"
            )
        if not row["reason"].strip():
            errors.append(f"{label}: reason is required")
        if not row["topic"].strip():
            errors.append(f"{label}: topic is required")
        if selected and class_code == "honey_bee_unqualified":
            if row["methods_checked"].strip() != "yes":
                errors.append(f"{label}: methods_checked must be yes")
        elif selected and row["methods_checked"].strip() not in ("", "yes"):
            errors.append(f"{label}: methods_checked must be yes or empty")
    return dois


def validate_selection(
    screening_path: Path = Path("data/pilot/screening.tsv"),
    selection_path: Path = Path("data/pilot/selection.tsv"),
    candidate_path: Path = Path("data/pilot/candidates.jsonl"),
) -> list[str]:
    """Collect all structural and human-selection errors with row numbers.

    Args:
        screening_path: Reviewed candidate decisions.
        selection_path: Included-class selection decisions.
        candidate_path: Committed candidate JSONL.

    Returns:
        Every detected validation error; an empty list means valid input.
    """
    candidates, errors = _candidate_dois(candidate_path)
    screening, screening_errors, screening_lines = _read_tsv(
        screening_path, SCREENING_HEADER
    )
    selection, selection_errors, selection_lines = _read_tsv(
        selection_path, SELECTION_HEADER
    )
    errors.extend(screening_errors)
    errors.extend(selection_errors)
    reviewed_dois = _validate_review_rows(
        screening,
        screening_lines,
        screening_path,
        candidates,
        errors,
        selected=False,
    )
    reviewed_classes: dict[str, str] = {}
    for row in screening:
        try:
            reviewed_classes[normalize_doi(row["doi"]).doi] = row[
                "class"
            ].strip()
        except ValueError:
            continue
    selected_dois = _validate_review_rows(
        selection,
        selection_lines,
        selection_path,
        candidates,
        errors,
        selected=True,
    )
    for row_number, row in zip(selection_lines, selection, strict=True):
        try:
            doi = normalize_doi(row["doi"]).doi
        except ValueError:
            continue
        if doi not in reviewed_dois:
            errors.append(
                f"{selection_path}: row {row_number}: DOI {doi} was "
                "not reviewed "
                "in screening.tsv"
            )
        elif row["class"].strip() != reviewed_classes[doi]:
            errors.append(
                f"{selection_path}: row {row_number}: class differs from "
                "screening.tsv"
            )
    if not 15 <= len(selected_dois) <= 20:
        errors.append(
            f"{selection_path}: selection needs 15-20 unique normalized DOIs; "
            f"found {len(selected_dois)}"
        )
    topics = {
        row["topic"].strip().casefold()
        for row in selection
        if row["topic"].strip()
    }
    if len(topics) < 3:
        errors.append(
            f"{selection_path}: selection needs at least 3 distinct topics; "
            f"found {len(topics)}"
        )
    return errors
