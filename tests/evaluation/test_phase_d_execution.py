"""Synthetic oracles for the authorized read-only T006 execution adapter."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from sciscope.evaluation.execution import (
    build_gold_references,
    build_retrieval_request,
    calculate_question_metrics,
    response_signature,
    run_reproducible_retrieval,
)


def _hit(chunk_id: str, locator: str) -> Any:
    return SimpleNamespace(
        rank=1,
        chunk_id=chunk_id,
        doi="10.1234/example",
        source_locator=locator,
        section_path=("Results",),
        text="The source passage supports the expected result.",
    )


def test_build_retrieval_request_uses_fixed_cutoff_and_default_pool() -> None:
    """Requests keep the preregistered cutoff and default RRF pool."""
    question = {"question_id": "q-safe", "question": "synthetic query"}
    request = build_retrieval_request(
        question, cohort="v1-held-out", arm="hybrid", repetition=1
    )
    assert request["mode"] == "hybrid"
    assert request["top_k"] == 20
    assert request["request_id"].endswith("hybrid-r1")
    assert "ranking" not in request
    assert request["query_text"] == "synthetic query"


def test_gold_reference_uses_exact_locator_section_and_relevance() -> None:
    """Gold labels retain exact source location and integer relevance."""
    question = {
        "question_id": "q-safe",
        "question_type": "single_paper_factual",
        "expected_insufficient_evidence": False,
        "relevant_papers": [
            {
                "doi": "10.1234/example",
                "sections": ["Results"],
                "evidence": [
                    {
                        "relevance_label": "3",
                        "source_locator": "jats:v1:/p/1",
                        "quotation": "supporting sentence",
                    }
                ],
            }
        ],
    }
    references = build_gold_references(
        question, section_by_locator={"jats:v1:/p/1": "Results"}
    )
    assert len(references) == 1
    assert references[0].relevance_label == 3
    assert references[0].section == "Results"


def test_v0_insufficient_answerability_is_derived_from_frozen_category() -> (
    None
):
    """Golden v0 answerability follows its frozen insufficient category."""
    question = {
        "question_id": "q-negative",
        "question_type": "insufficient_evidence",
        "relevant_papers": [],
    }
    metrics = calculate_question_metrics(question, ())
    assert metrics.expected_insufficient_evidence is True
    assert metrics.gold_unit_count == 0
    assert metrics.recall_at_k[1] is None
    assert metrics.mrr_at_k[1] is None


def test_repeated_retrieval_must_return_identical_ranked_evidence() -> None:
    """Nondeterministic repeated results fail without exposing query text."""

    class _Core:
        def __init__(self) -> None:
            self.calls = 0

        def retrieve(self, request: dict[str, object]) -> Any:
            self.calls += 1
            return SimpleNamespace(
                mode=request["mode"],
                results=(_hit(f"chunk-{self.calls}", "loc"),),
            )

    core = _Core()
    question = {"question_id": "q-safe", "question": "synthetic query"}
    with pytest.raises(ValueError, match="not reproducible"):
        run_reproducible_retrieval(
            core,
            question,
            cohort="v1-held-out",
            arm="lexical",
            clock=lambda: 1.0,
        )
    assert core.calls == 2


def test_response_signature_ignores_unranked_internal_metadata() -> None:
    """Stable evidence signatures ignore request-specific metadata."""
    first = SimpleNamespace(results=(_hit("same", "loc"),), request_id="a")
    second = SimpleNamespace(results=(_hit("same", "loc"),), request_id="b")
    assert response_signature(first) == response_signature(second)
