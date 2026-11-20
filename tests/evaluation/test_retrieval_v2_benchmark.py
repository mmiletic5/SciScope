"""Independent oracles for Retrieval v2 development evaluation."""

from __future__ import annotations

import math

from sciscope.evaluation.matching import EvidenceReference, RetrievedEvidence
from sciscope.evaluation.v2_benchmark import (
    compute_v2_question_metrics,
    verify_doi_attribution,
)


def test_ndcg_uses_ir_measures_and_preserves_irrelevant_rank_positions() -> (
    None
):
    """A relevant unit at rank two has binary nDCG 1/log2(3)."""
    reference = EvidenceReference(
        doi="10.1000/pilot",
        section="Results",
        source_locator="locator:gold",
        relevance_label=3,
    )
    retrieved = (
        RetrievedEvidence(
            "a" * 64,
            "10.1000/other",
            ("Results",),
            "locator:noise",
            (),
            "irrelevant passage",
        ),
        RetrievedEvidence(
            "b" * 64,
            "10.1000/pilot",
            ("Results",),
            "locator:gold",
            (),
            "relevant passage",
        ),
    )

    result = compute_v2_question_metrics(
        question_id="dev-q1",
        references=(reference,),
        retrieved=retrieved,
        expected_insufficient_evidence=False,
    )

    assert result.question.recall_at_k[5] == 1.0
    assert result.question.mrr_at_k[10] == 0.5
    assert math.isclose(result.ndcg_at_10 or 0.0, 1 / math.log2(3))


def test_insufficient_metrics_are_undefined() -> None:
    """Insufficient cases do not enter positive metric denominators."""
    result = compute_v2_question_metrics(
        question_id="dev-insufficient",
        references=(),
        retrieved=(),
        expected_insufficient_evidence=True,
    )

    assert result.question.recall_at_k == {5: None, 10: None, 20: None}
    assert result.question.mrr_at_k == {5: None, 10: None, 20: None}
    assert result.ndcg_at_10 is None


def test_doi_attribution_requires_exact_source_identity() -> None:
    """A DOI is correct only when active lookup confirms DOI/locator/text."""
    retrieved = RetrievedEvidence(
        "a" * 64,
        "10.1000/pilot",
        ("Results",),
        "locator:gold",
        (),
        "exact source text",
    )
    exact = RetrievedEvidence(
        retrieved.chunk_id,
        "10.1000/pilot",
        retrieved.section_path,
        retrieved.source_locator,
        (),
        retrieved.text,
    )
    wrong_locator = RetrievedEvidence(
        retrieved.chunk_id,
        "10.1000/pilot",
        retrieved.section_path,
        "locator:wrong",
        (),
        retrieved.text,
    )

    assert verify_doi_attribution(retrieved, exact)
    assert not verify_doi_attribution(retrieved, wrong_locator)
