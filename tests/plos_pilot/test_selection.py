"""Validation checks using only synthetic candidate and review records."""

import json
from pathlib import Path

from sciscope.plos_pilot.selection import (
    read_screening,
    read_selection,
    validate_selection,
    write_screening,
    write_selection,
)


def _doi(index: int) -> str:
    return f"10.9999/SYNTHETIC-{index:02d}"


def _review(index: int) -> dict[str, str]:
    return {
        "doi": _doi(index),
        "class": "measured_mellifera",
        "reason": "SYNTHETIC review reason",
        "topic": f"SYNTHETIC topic {index % 3}",
        "methods_checked": "",
    }


def _candidate_file(path: Path, count: int = 15) -> None:
    lines = [json.dumps({"doi": _doi(index).lower()}) for index in range(count)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def test_tsv_round_trip_and_valid_selection(tmp_path: Path) -> None:
    """Exact TSV headers, UTF-8/LF, and reviewed inclusion pass validation."""
    screening_path = tmp_path / "screening.tsv"
    selection_path = tmp_path / "selection.tsv"
    candidate_path = tmp_path / "candidates.jsonl"
    rows = [_review(index) for index in range(15)]
    rows[0]["class"] = "honey_bee_unqualified"
    rows[0]["methods_checked"] = "yes"
    screening = [
        {key: value for key, value in row.items() if key != "methods_checked"}
        for row in rows
    ]
    screening.append(
        {
            "doi": _doi(15),
            "class": "background_only",
            "reason": "SYNTHETIC exclusion",
            "topic": "SYNTHETIC topic 0",
        }
    )
    _candidate_file(candidate_path, 16)
    write_screening(screening_path, screening)
    write_selection(selection_path, rows)
    assert screening_path.read_bytes().startswith(
        b"doi\tclass\treason\ttopic\n"
    )
    assert selection_path.read_bytes().startswith(
        b"doi\tclass\treason\ttopic\tmethods_checked\n"
    )
    assert b"\r\n" not in selection_path.read_bytes()
    assert read_screening(screening_path) == screening
    assert read_selection(selection_path) == rows
    assert (
        validate_selection(screening_path, selection_path, candidate_path) == []
    )


def test_validator_collects_all_row_numbered_errors(tmp_path: Path) -> None:
    """All invalid review decisions are reported in one validation pass."""
    screening_path = tmp_path / "screening.tsv"
    selection_path = tmp_path / "selection.tsv"
    candidate_path = tmp_path / "candidates.jsonl"
    _candidate_file(candidate_path)
    screening = [
        {
            key: value
            for key, value in _review(index).items()
            if key != "methods_checked"
        }
        for index in range(15)
    ]
    screening[0]["class"] = "invented_class"
    screening[1]["reason"] = ""
    screening[2]["doi"] = _doi(99)
    rows = [_review(index) for index in range(15)]
    rows[0]["class"] = "background_only"
    rows[1]["class"] = "honey_bee_unqualified"
    rows[2]["doi"] = _doi(99)
    rows[3]["reason"] = ""
    rows[4]["topic"] = ""
    rows[5]["doi"] = rows[6]["doi"].lower()
    for row in rows:
        row["topic"] = "SYNTHETIC topic 0" if row["topic"] else ""
    write_screening(screening_path, screening)
    write_selection(selection_path, rows)
    errors = validate_selection(screening_path, selection_path, candidate_path)
    combined = "\n".join(errors)
    for row_number in (2, 3, 4, 5, 6, 8):
        assert f"row {row_number}" in combined
    assert "at least 3" in combined
    assert "15" in combined
    assert "candidate" in combined.lower()


def test_rejects_wrong_header_and_unreviewed_selection(tmp_path: Path) -> None:
    """Selection columns are exact and every selected DOI must be reviewed."""
    screening_path = tmp_path / "screening.tsv"
    selection_path = tmp_path / "selection.tsv"
    candidate_path = tmp_path / "candidates.jsonl"
    _candidate_file(candidate_path)
    write_screening(screening_path, [])
    write_selection(selection_path, [_review(index) for index in range(15)])
    selection_path.write_text(
        selection_path.read_text(encoding="utf-8").replace(
            "methods_checked", "checked", 1
        ),
        encoding="utf-8",
        newline="\n",
    )
    errors = validate_selection(screening_path, selection_path, candidate_path)
    assert any("header" in error.lower() for error in errors)
    assert any("review" in error.lower() for error in errors)
