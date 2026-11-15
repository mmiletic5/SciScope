"""Behavior tests for synthetic JATS section classification."""

import pytest

from sciscope.jats.classify import (
    HEADING_TYPES,
    SEC_TYPE_TYPES,
    ClassificationResult,
    classify_section,
    normalize_heading,
)


@pytest.mark.parametrize(
    ("heading", "expected"),
    [
        ("1. Introduction", "introduction"),
        ("2.1 Methods", "methods"),
        ("3) Results", "results"),
        ("4 Discussion", "discussion"),
        ("1.Introduction", "introduction"),
        ("Methods:", "methods"),
        ("RESULTS  AND DISCUSSION", "results and discussion"),
        ("  ...Methods:  ", "methods"),
        ("2019 Results", "2019 results"),
        ("", ""),
    ],
)
def test_normalize_heading(heading: str, expected: str) -> None:
    """Numbering and surrounding punctuation do not change exact labels."""
    assert normalize_heading(heading) == expected


@pytest.mark.parametrize(("source", "expected"), tuple(SEC_TYPE_TYPES.items()))
def test_every_sec_type_row(source: str, expected: str) -> None:
    """Each approved sec-type value is explicitly classified."""
    assert classify_section(source, "", None) == ClassificationResult(
        expected, True
    )


@pytest.mark.parametrize(("source", "expected"), tuple(HEADING_TYPES.items()))
def test_every_heading_row(source: str, expected: str) -> None:
    """Each approved heading value is explicitly classified."""
    assert classify_section("", source, None) == ClassificationResult(
        expected, True
    )


def test_sec_type_is_trimmed_and_lowercased() -> None:
    """A sec-type match ignores surrounding whitespace and case."""
    assert classify_section(" Intro ", "", None) == ClassificationResult(
        "introduction", True
    )


def test_heading_wins_when_tables_disagree() -> None:
    """A conflicting sec-type is reported while heading takes precedence."""
    assert classify_section("results", "Methods", None) == (
        ClassificationResult("methods", True, True)
    )


def test_sec_type_is_used_when_heading_is_unmatched() -> None:
    """An unmatched heading leaves an explicit sec-type match in effect."""
    assert classify_section(
        "conclusions", "Conclusions and next steps", None
    ) == (ClassificationResult("conclusions", True, False))


def test_matching_tables_with_same_type_do_not_conflict() -> None:
    """Two explicit matches of one type are not a conflict."""
    assert classify_section("methods", "Materials and Methods", None) == (
        ClassificationResult("methods", True, False)
    )


@pytest.mark.parametrize(
    "heading", ["Methods and results", "Introduction to bees", "Conclusion"]
)
def test_unlisted_headings_do_not_match_partially(heading: str) -> None:
    """Near matches remain unmatched under the exact table rule."""
    assert classify_section("", heading, None) == ClassificationResult(
        "other", False
    )


def test_unknown_sec_type_falls_through_to_heading() -> None:
    """An unmapped sec-type does not block a mapped heading."""
    assert classify_section("unmapped", "Results", None) == (
        ClassificationResult("results", True)
    )


def test_unmatched_section_inherits_explicit_ancestor() -> None:
    """Inherited classification does not become explicit."""
    assert classify_section("", "Local detail", "methods") == (
        ClassificationResult("methods", False)
    )


def test_unmatched_section_without_ancestor_defaults_to_other() -> None:
    """An unmatched root section has the default type and flag."""
    assert classify_section("", "Local detail", None) == (
        ClassificationResult("other", False)
    )


@pytest.mark.parametrize(
    ("sec_type", "heading"),
    [
        ("supplementary-material", "Local detail"),
        ("", "Supporting Information"),
    ],
)
def test_explicit_other_does_not_inherit(sec_type: str, heading: str) -> None:
    """The explicit other table result overrides an ancestor's type."""
    assert classify_section(sec_type, heading, "methods") == (
        ClassificationResult("other", True)
    )


@pytest.mark.parametrize(
    ("sec_type", "heading", "ancestor"),
    [(source, "", None) for source in SEC_TYPE_TYPES]
    + [("", source, None) for source in HEADING_TYPES]
    + [("", "Unknown", "discussion"), ("", "Unknown", None)],
)
def test_classification_returns_only_v0_types(
    sec_type: str, heading: str, ancestor: str | None
) -> None:
    """All approved table and fallback paths stay in the v0 taxonomy."""
    assert classify_section(sec_type, heading, ancestor).normalized_type in {
        "abstract",
        "introduction",
        "methods",
        "results",
        "results_discussion",
        "discussion",
        "conclusions",
        "other",
    }


def test_taxonomy_tables_are_immutable() -> None:
    """The mapping constants cannot change during a parse."""
    with pytest.raises(TypeError):
        SEC_TYPE_TYPES["new"] = "other"  # type: ignore[index]
    with pytest.raises(TypeError):
        HEADING_TYPES["new"] = "other"  # type: ignore[index]
