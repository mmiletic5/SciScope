"""Read-only composition check for Phase B and Phase C components."""

from __future__ import annotations

from dataclasses import dataclass

from sciscope.retrieval._context import select_context
from sciscope.retrieval._core import _RetrievalCore
from sciscope.retrieval._lookup import EvidenceLookup
from sciscope.retrieval._quality import rank_evidence
from sciscope.retrieval._reranking import (
    DeterministicFakeReranker,
    NoOpReranker,
    rank_with_reranker,
)


@dataclass(frozen=True)
class _Counter:
    counter_id: str = "test:whitespace-v1"

    def count(self, text: str) -> int:
        return len(text.split())


def test_lookup_ranking_and_context_keep_exact_snapshot_evidence(
    retrieval_engine,
) -> None:
    """A looked-up pilot chunk flows unchanged through selection stages."""
    lookup = EvidenceLookup(retrieval_engine)
    phase_b = _RetrievalCore(retrieval_engine, None).retrieve(
        {
            "contract_version": "retrieval.v1",
            "request_id": "phase-c-pipeline",
            "query_text": "honey bee",
            "mode": "lexical",
            "top_k": 5,
        }
    )
    assert phase_b.results
    baseline = rank_evidence(phase_b.results)
    assert baseline.candidates[0].base_rank == 1
    candidate = baseline.candidates[0].hit
    looked_up = lookup.get_chunk(candidate.chunk_id)
    assert looked_up.chunk.chunk_id == candidate.chunk_id
    assert looked_up.chunk.text == candidate.text
    assert looked_up.chunk.source_locator == candidate.source_locator

    no_op = rank_with_reranker(
        (candidate,), query_text="offline smoke", reranker=NoOpReranker()
    )
    fake = DeterministicFakeReranker({candidate.chunk_id: 0.5})
    reranked = rank_with_reranker(
        (candidate,), query_text="offline smoke", reranker=fake
    )
    selected = select_context(
        reranked.candidates,
        budget_tokens=_Counter().count(candidate.text),
        token_counter=_Counter(),
        expected_counter_id="test:whitespace-v1",
    )

    assert no_op.candidates[0].hit.text == candidate.text
    assert reranked.candidates[0].hit.source_locator == candidate.source_locator
    assert selected.selected[0].hit.chunk_id == candidate.chunk_id
    assert selected.total_tokens <= selected.budget_tokens
    assert looked_up.corpus.import_id > 0
    assert looked_up.corpus.delivery_digest.startswith("sha256:")
