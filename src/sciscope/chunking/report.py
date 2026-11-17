"""Option A omission policy and per-paper counting interfaces."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

CHUNKING_VERSION = "chunking-v1"
CHUNK_KIND_PARAGRAPH = "paragraph"


@dataclass(frozen=True, slots=True)
class ExclusionPolicy:
    """Public decision for an omitted F002 element kind."""

    category: str
    decision: str
    reason: str
    follow_up: str | None = None


EXCLUDED_CATEGORIES: Mapping[str, ExclusionPolicy] = {
    "fig": ExclusionPolicy(
        "figure",
        "excluded",
        "Not an F002 paragraph",
        "caption chunks after Golden v0",
    ),
    "table-wrap": ExclusionPolicy(
        "table",
        "excluded",
        "Caption and body are not F002 paragraphs",
        "caption chunks after Golden v0",
    ),
    "supplementary-material": ExclusionPolicy(
        "supplementary_material", "excluded", "Not an F002 paragraph"
    ),
    "disp-formula": ExclusionPolicy(
        "formula", "excluded", "Formula content omitted by F002"
    ),
    "inline-formula": ExclusionPolicy(
        "formula", "excluded", "Formula content omitted by F002"
    ),
    "list": ExclusionPolicy("list", "excluded", "List content omitted by F002"),
    "boxed-text": ExclusionPolicy(
        "boxed_text", "excluded", "Not an F002 paragraph"
    ),
}

BACK_MATTER_CATEGORIES: Mapping[str, str] = {
    "ref-list": "references",
    "ack": "acknowledgments",
    "app": "back_matter_other",
    "notes": "back_matter_other",
    "fn-group": "back_matter_other",
    "glossary": "back_matter_other",
}

EXCLUDED_CATEGORY_NAMES = (
    "figure",
    "table",
    "supplementary_material",
    "formula",
    "list",
    "boxed_text",
    "other_omitted",
)
BACK_MATTER_CATEGORY_NAMES = (
    "references",
    "acknowledgments",
    "back_matter_other",
)


@dataclass(frozen=True, slots=True)
class ExcludedCounts:
    """Numeric omissions without source text or headings."""

    excluded_elements: Mapping[str, int]
    unlisted_kinds: Mapping[str, int]
    back_matter_excluded: Mapping[str, int]


def count_excluded(paper_report: Mapping[str, Any]) -> ExcludedCounts:
    """Count F002 outer skips and back-container presence by policy category."""
    excluded = dict.fromkeys(EXCLUDED_CATEGORY_NAMES, 0)
    unlisted: dict[str, int] = {}
    skipped: Mapping[str, int] = paper_report["skipped_element_kinds"]
    for kind, count in sorted(skipped.items()):
        policy = EXCLUDED_CATEGORIES.get(kind)
        category = policy.category if policy is not None else "other_omitted"
        excluded[category] += count
        if policy is None:
            unlisted[kind] = count

    back = dict.fromkeys(BACK_MATTER_CATEGORY_NAMES, 0)
    containers: Sequence[str] = paper_report["back_matter_containers"]
    for kind in sorted(set(containers)):
        back_category = BACK_MATTER_CATEGORIES.get(kind)
        if back_category is not None:
            back[back_category] += 1
    return ExcludedCounts(excluded, unlisted, back)


def count_paragraphs_with_omitted(
    paragraphs: Sequence[Mapping[str, Any]],
) -> int:
    """Count paragraph records whose omitted-kind list is nonempty."""
    return sum(bool(paragraph["omitted"]) for paragraph in paragraphs)
