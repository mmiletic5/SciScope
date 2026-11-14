"""Behavior checks for the golden question schema."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "evals/golden_questions.schema.json"


def _question(relevant_papers: list[dict[str, object]], negative: bool) -> dict:
    """Build a schema-valid question except for the paper count under test."""
    return {
        "question_id": "example-question",
        "question": "What does the example corpus show?",
        "query_language": "en",
        "expected_findings": "Example fixture only.",
        "relevant_papers": relevant_papers,
        "expected_insufficient_evidence": negative,
        "reviewer": "test fixture",
        "verification_status": "unverified",
        "source_corpus_version": "example-corpus",
    }


def _validate(question: dict) -> None:
    """Validate one question against the golden dataset schema."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    dataset = {
        "dataset_version": "example-dataset",
        "corpus_version": "example-corpus",
        "questions": [question],
    }
    Draft202012Validator(schema).validate(dataset)


def test_negative_question_allows_no_relevant_papers() -> None:
    """An insufficient-evidence question can have no relevant papers."""
    _validate(_question([], negative=True))


def test_non_negative_question_requires_relevant_paper() -> None:
    """A question expecting evidence requires at least one paper."""
    with pytest.raises(ValidationError):
        _validate(_question([], negative=False))


def test_non_negative_question_accepts_relevant_paper() -> None:
    """A question expecting evidence accepts a valid paper entry."""
    paper = {
        "doi": "10.1234/example-fixture",
        "sections": ["Example section"],
        "evidence": [
            {
                "relevance_label": "example label",
                "source_locator": "Example section, paragraph 1",
            }
        ],
    }
    _validate(_question([paper], negative=False))
