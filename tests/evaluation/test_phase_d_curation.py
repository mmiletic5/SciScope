"""Source provenance checks for synthetic Golden v1 curation fixtures."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from sciscope.evaluation.curation import (
    CurationValidationError,
    validate_evidence_reference,
    validate_sidecar_schema,
)

ROOT_SCHEMA = (
    Path(__file__).resolve().parents[2]
    / "evals"
    / "golden_functionality_annotations.schema.json"
)


def _reference() -> dict[str, Any]:
    return {
        "evidence_reference_id": "q1-e1",
        "doi": "10.1234/synthetic",
        "section": "Results",
        "chunk_id": "chunk-1",
        "source_locator": "jats:test:/article/body/sec[1]/p[1]",
        "source_xml_sha256": "a" * 64,
        "source_url": "https://example.org/source.xml",
        "source_passage": (
            "Synthetic source passage with sufficient exact text."
        ),
        "quotation": "sufficient exact text",
        "relevance_label": "3",
        "relevance_rationale": (
            "Directly reports the requested synthetic result."
        ),
        "claim_ids": ["claim-1"],
        "role": "supports",
    }


def _chunk() -> dict[str, Any]:
    return {
        "doi": "10.1234/synthetic",
        "chunk_id": "chunk-1",
        "source_locator": "jats:test:/article/body/sec[1]/p[1]",
        "spans": [{"source_locator": "jats:test:/article/body/sec[1]/p[1]"}],
        "section_path": ["Results"],
        "xml_sha256": "a" * 64,
        "text": "Synthetic source passage with sufficient exact text.",
    }


def _papers() -> dict[str, dict[str, str]]:
    return {
        "10.1234/synthetic": {
            "xml_sha256": "a" * 64,
            "source_url": "https://example.org/source.xml",
        }
    }


def test_evidence_reference_requires_exact_source_mapping() -> None:
    """DOI, chunk, section, locator, passage, and quote bind to one source."""
    validate_evidence_reference(_reference(), {"chunk-1": _chunk()}, _papers())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("doi", "10.5678/wrong"),
        ("source_locator", "not-the-source-locator"),
        ("source_passage", "altered source passage with sufficient length."),
        ("source_xml_sha256", "b" * 64),
        ("source_url", "https://example.org/other.xml"),
        ("quotation", "not present in source text"),
        ("section", "Discussion"),
    ],
)
def test_evidence_reference_rejects_mismatched_source(
    field: str, value: str
) -> None:
    """Source or locator substitution fails without echoing source text."""
    reference = _reference()
    reference[field] = value
    with pytest.raises(CurationValidationError):
        validate_evidence_reference(reference, {"chunk-1": _chunk()}, _papers())


def test_sidecar_schema_is_valid_and_requires_source_provenance() -> None:
    """The private sidecar schema is valid and includes evidence provenance."""
    schema = __import__("json").loads(ROOT_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    with pytest.raises(CurationValidationError, match="schema"):
        validate_sidecar_schema({}, ROOT_SCHEMA, expected_ids=frozenset())
