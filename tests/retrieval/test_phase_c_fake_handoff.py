"""Contract checks for the proposed integration example using fakes only."""

from __future__ import annotations

from examples.phase_c_fake_handoff import build_example_response


def test_fake_handoff_carries_citation_scores_and_tokenizer_identity() -> None:
    """Synthetic response keeps evidence IDs and selection metadata linked."""
    response = build_example_response()
    evidence = response["evidence"]
    assert isinstance(evidence, list) and len(evidence) == 1
    item = evidence[0]
    assert item["chunk_id"] == item["citation"]["chunk_id"]
    assert item["doi"] == item["citation"]["doi"]
    assert item["source_locator"] == item["citation"]["source_locator"]
    assert (
        response["corpus"]["delivery_digest"]
        == item["citation"]["delivery_digest"]
    )
    assert set(item["scores"]) == {
        "dense_similarity",
        "dense_rank",
        "lexical_score",
        "lexical_rank",
        "fusion_score",
    }
    assert response["selection"]["token_counter_id"] == (
        "example:whitespace-v1"
    )
    assert (
        response["selection"]["total_tokens"]
        <= response["selection"]["budget_tokens"]
    )
