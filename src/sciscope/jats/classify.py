"""Approved JATS section taxonomy interfaces for T005."""

import re
import string
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

_LEADING_SECTION_NUMBER = re.compile(
    r"^[0-9]{1,2}(?:\.[0-9]{1,2})*(?:\.(?![0-9])|[):]|\s+)"
)

SEC_TYPE_TYPES: Mapping[str, str] = MappingProxyType(
    {
        "intro": "introduction",
        "introduction": "introduction",
        "materials|methods": "methods",
        "methods": "methods",
        "results": "results",
        "discussion": "discussion",
        "conclusions": "conclusions",
        "supplementary-material": "other",
    }
)
HEADING_TYPES: Mapping[str, str] = MappingProxyType(
    {
        "introduction": "introduction",
        "material and methods": "methods",
        "materials and methods": "methods",
        "methods and materials": "methods",
        "methods": "methods",
        "results": "results",
        "results and discussion": "results_discussion",
        "discussion": "discussion",
        "conclusions": "conclusions",
        "supporting information": "other",
    }
)


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    """A normalized section type and its classification provenance."""

    normalized_type: str
    explicit: bool
    conflict: bool = False


def normalize_heading(heading: str) -> str:
    """Return the approved lookup form of a JATS heading."""
    lowered = heading.lower().strip()
    without_number = _LEADING_SECTION_NUMBER.sub("", lowered, count=1)
    return " ".join(
        without_number.strip(string.punctuation + string.whitespace).split()
    )


def classify_section(
    sec_type: str,
    heading: str,
    nearest_explicit_ancestor_type: str | None,
) -> ClassificationResult:
    """Classify a body section by the approved taxonomy precedence."""
    sec_type_match = SEC_TYPE_TYPES.get(sec_type.strip().lower())
    heading_match = HEADING_TYPES.get(normalize_heading(heading))
    if heading_match is not None:
        return ClassificationResult(
            normalized_type=heading_match,
            explicit=True,
            conflict=(
                sec_type_match is not None and sec_type_match != heading_match
            ),
        )
    if sec_type_match is not None:
        return ClassificationResult(sec_type_match, True)
    return ClassificationResult(
        nearest_explicit_ancestor_type or "other", False
    )
