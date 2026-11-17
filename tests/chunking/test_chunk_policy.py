"""T003 RED tests for Option A omission policy and numeric counts."""

from __future__ import annotations

from typing import Any

import pytest

from sciscope.chunking.config import ChunkConfig
from sciscope.chunking.core import (
    SourceParagraph,
    SourceSection,
    chunk_sections,
)
from sciscope.chunking.counter import Utf8BytesDiv3Counter
from sciscope.chunking.report import (
    BACK_MATTER_CATEGORIES,
    BACK_MATTER_CATEGORY_NAMES,
    EXCLUDED_CATEGORIES,
    EXCLUDED_CATEGORY_NAMES,
    count_excluded,
    count_paragraphs_with_omitted,
)


def paper_report(
    skipped: dict[str, int] | None = None,
    back: list[str] | None = None,
) -> dict[str, object]:
    """Create synthetic F002 omission fields without article text."""
    return {
        "skipped_element_kinds": skipped or {},
        "back_matter_containers": back or [],
    }


@pytest.mark.parametrize(
    ("kind", "category"),
    [
        pytest.param("fig", "figure", id="figure"),
        pytest.param("table-wrap", "table", id="table"),
        pytest.param(
            "supplementary-material", "supplementary_material", id="supplement"
        ),
        pytest.param("disp-formula", "formula", id="display-formula"),
        pytest.param("inline-formula", "formula", id="inline-formula"),
        pytest.param("list", "list", id="list"),
        pytest.param("boxed-text", "boxed_text", id="boxed-text"),
    ],
)
def test_each_skipped_kind_is_counted(kind: str, category: str) -> None:
    """T003 RED: each F002 skipped kind maps to its public category."""
    counts = count_excluded(paper_report({kind: 2}))
    assert counts.excluded_elements[category] == 2


def test_absent_categories_have_explicit_zeros() -> None:
    """T003 RED: every omission category is present even when absent."""
    counts = count_excluded(paper_report())
    assert counts.excluded_elements == dict.fromkeys(EXCLUDED_CATEGORY_NAMES, 0)
    assert counts.back_matter_excluded == dict.fromkeys(
        BACK_MATTER_CATEGORY_NAMES, 0
    )
    assert counts.unlisted_kinds == {}


def test_unlisted_kind_retains_name_and_aggregate_count() -> None:
    """T003 RED: unknown F002 kinds remain auditable by kind name."""
    counts = count_excluded(paper_report({"invented-kind": 3}))
    assert counts.excluded_elements["other_omitted"] == 3
    assert counts.unlisted_kinds == {"invented-kind": 3}


@pytest.mark.parametrize(
    ("container", "category"),
    [
        pytest.param("ref-list", "references", id="references"),
        pytest.param("ack", "acknowledgments", id="acknowledgments"),
        pytest.param("app", "back_matter_other", id="appendix"),
        pytest.param("notes", "back_matter_other", id="notes"),
        pytest.param("fn-group", "back_matter_other", id="footnotes"),
        pytest.param("glossary", "back_matter_other", id="glossary"),
    ],
)
def test_back_container_counts_presence(container: str, category: str) -> None:
    """T003 RED: F002 back-container presence contributes one count."""
    counts = count_excluded(paper_report(back=[container]))
    assert counts.back_matter_excluded[category] == 1


def test_multiple_formula_kinds_sum_in_one_category() -> None:
    """T003 RED: display and inline formulas share a count."""
    counts = count_excluded(
        paper_report({"disp-formula": 2, "inline-formula": 1})
    )
    assert counts.excluded_elements["formula"] == 3


def test_policy_follow_up_is_limited_to_figures_and_tables() -> None:
    """T003 RED: only captions have a named future follow-up."""
    assert {
        kind
        for kind, policy in EXCLUDED_CATEGORIES.items()
        if policy.follow_up is not None
    } == {"fig", "table-wrap"}
    assert all(
        policy.decision == "excluded" for policy in EXCLUDED_CATEGORIES.values()
    )
    assert set(BACK_MATTER_CATEGORIES) == {
        "ref-list",
        "ack",
        "app",
        "notes",
        "fn-group",
        "glossary",
    }


def test_counts_are_deterministic_across_input_map_order() -> None:
    """T003 RED: source map insertion order does not change counts."""
    first = count_excluded(paper_report({"fig": 1, "unknown": 2}))
    second = count_excluded(paper_report({"unknown": 2, "fig": 1}))
    assert first == second


def test_paragraphs_with_omitted_counts_records_not_kinds() -> None:
    """T003 RED: one paragraph with two omissions counts once."""
    paragraphs: list[dict[str, Any]] = [
        {"omitted": ["disp-formula", "inline-formula"]},
        {"omitted": []},
        {"omitted": ["list"]},
    ]
    assert count_paragraphs_with_omitted(paragraphs) == 2


def test_excluded_fixture_text_never_enters_paragraph_chunks() -> None:
    """T003 RED: caption, table and reference fixtures stay excluded."""
    excluded_text = ("caption zarnix", "table belvix", "reference mordix")
    counts = count_excluded(
        paper_report({"fig": 1, "table-wrap": 1}, ["ref-list"])
    )
    section = SourceSection("10.0000/synthetic", "s1", (), "methods")
    paragraph = SourceParagraph(
        "10.0000/synthetic", "s1", 1, "pelvix norvix", "loc-p1"
    )
    chunks = chunk_sections(
        [section],
        [paragraph],
        ChunkConfig(
            operational_cap_tokens=96,
            content_target_min_tokens=2,
            content_target_max_tokens=20,
            soft_min_tokens=0,
            min_content_budget_tokens=1,
        ),
        Utf8BytesDiv3Counter(),
    )
    assert chunks
    assert all(
        text not in chunk.text for chunk in chunks for text in excluded_text
    )
    assert counts.excluded_elements["figure"] == 1
    assert counts.excluded_elements["table"] == 1
    assert counts.back_matter_excluded["references"] == 1
