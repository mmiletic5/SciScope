"""Behavior tests for the minimal rank-bm25 adapter and v2 ordering."""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass
from types import SimpleNamespace
from typing import cast

import pytest
from sqlalchemy import Engine

from sciscope.retrieval._bm25 import BM25Document, BM25OkapiRetriever
from sciscope.retrieval._context import select_context
from sciscope.retrieval._core import (
    _Corpus,
    _EmbeddingConfig,
    _RetrievalCore,
    _select_v2_hybrid_candidate_ids,
)
from sciscope.retrieval._quality import RankedCandidate
from sciscope.retrieval._ranking import BranchHit


@dataclass(frozen=True)
class _Candidate:
    chunk_id: str
    doi: str
    source_locator: str
    text: str


class _RecordingReranker:
    model_id = "recording-test"
    model_revision = "test-v1"
    model_sha256 = "0" * 64

    def __init__(self) -> None:
        self.candidate_ids: tuple[str, ...] = ()

    def rerank(self, query_text, candidates):
        assert query_text == "bee disease"
        self.candidate_ids = tuple(item.chunk_id for item in candidates)
        return [
            (item.chunk_id, float(index))
            for index, item in enumerate(candidates)
        ]


def test_bm25_returns_exact_term_match_and_stable_chunk_ids() -> None:
    """BM25Okapi ranks matching passages and uses IDs to break score ties."""
    retriever = BM25OkapiRetriever(
        [
            BM25Document("b", "Varroa mites affect honey bee colonies"),
            BM25Document("a", "Varroa mites affect honey bee colonies"),
            BM25Document("c", "A separate unrelated passage"),
        ]
    )

    results = retriever.search("Varroa mites", limit=3)

    assert [item.chunk_id for item in results] == ["a", "b"]
    assert results[0].score == results[1].score


def test_bm25_empty_query_and_no_match_return_no_candidates() -> None:
    """Empty or out-of-vocabulary terms never return zero-score rows."""
    retriever = BM25OkapiRetriever([BM25Document("a", "honey bee homing")])

    assert retriever.search("   ", limit=5) == ()
    assert retriever.search("xylophone", limit=5) == ()


@pytest.mark.parametrize(
    "documents",
    [
        [BM25Document("", "text")],
        [BM25Document("a", "")],
        [BM25Document("a", "one"), BM25Document("a", "two")],
    ],
)
def test_bm25_rejects_invalid_document_identity(documents) -> None:
    """Invalid and duplicated corpus identities fail before scoring."""
    with pytest.raises(ValueError):
        BM25OkapiRetriever(documents)


def test_v2_reranks_full_union_before_top_k() -> None:
    """A reranker sees and may promote a candidate beyond initial top-k."""
    candidates = tuple(
        _Candidate(
            chunk_id=chunk_id,
            doi=f"10.1000/{index}",
            source_locator=f"loc-{index}",
            text=f"evidence {index}",
        )
        for index, chunk_id in enumerate(("first", "second", "third"))
    )
    reranker = _RecordingReranker()

    selected = _select_v2_hybrid_candidate_ids(
        candidates,
        query_text="bee disease",
        top_k=1,
        reranker=reranker,
    )

    assert reranker.candidate_ids == ("first", "second", "third")
    assert selected == ("third",)


def test_v2_without_reranker_keeps_rrf_order_before_top_k() -> None:
    """BM25+RRF remains independently usable without MiniLM reranking."""
    candidates = tuple(
        _Candidate(
            chunk_id=item, doi=f"10.1000/{item}", source_locator=item, text=item
        )
        for item in ("first", "second", "third")
    )

    selected = _select_v2_hybrid_candidate_ids(
        candidates,
        query_text="bee disease",
        top_k=2,
        reranker=None,
    )

    assert selected == ("first", "second")


def test_reranked_evidence_order_flows_into_token_budget_selection() -> None:
    """Downstream context selection consumes final reranked whole passages."""
    candidates = tuple(
        _Candidate(chunk_id, f"10.1000/{chunk_id}", chunk_id, text)
        for chunk_id, text in (
            ("rrf-first", "long passage"),
            ("rerank-winner", "short passage"),
        )
    )

    class _PromoteSecond:
        model_id = "test-model"
        model_revision = "test-revision"
        model_sha256 = "0" * 64

        def rerank(self, query_text, ranked_candidates):
            return [
                (candidate.chunk_id, float(index))
                for index, candidate in enumerate(ranked_candidates)
            ]

    selected_ids = _select_v2_hybrid_candidate_ids(
        candidates,
        query_text="bee disease",
        top_k=2,
        reranker=_PromoteSecond(),
    )
    by_id = {candidate.chunk_id: candidate for candidate in candidates}
    final_ranked = tuple(
        RankedCandidate(by_id[chunk_id], rank, 1.0 / rank)
        for rank, chunk_id in enumerate(selected_ids, start=1)
    )

    class _Counter:
        counter_id = "test-counter-v1"

        def count(self, text: str) -> int:
            return 3 if text == "short passage" else 8

    context = select_context(
        final_ranked,
        budget_tokens=4,
        token_counter=_Counter(),
        expected_counter_id="test-counter-v1",
    )

    assert selected_ids == ("rerank-winner", "rrf-first")
    assert [candidate.hit.chunk_id for candidate in context.selected] == [
        "rerank-winner"
    ]
    assert context.total_tokens == 3
    assert context.omissions[0].chunk_id == "rrf-first"


def test_v2_core_fuses_bm25_with_dense_and_reranks_full_union(
    monkeypatch,
) -> None:
    """The v2 core applies its distinct branch and reranks before top-k."""
    from sciscope.retrieval import _core

    corpus = _Corpus(
        import_id=1,
        embedding_set_id=115,
        delivery_digest="sha256:" + "0" * 64,
        source_contract_version="0.3.0",
        corpus_version="pilot17-xml-" + "0" * 12,
        embedding_config=_EmbeddingConfig(),
        embedding_compatible=True,
    )
    rows = {
        chunk_id: SimpleNamespace(
            chunk_id=chunk_id,
            text=f"evidence {chunk_id}",
            doi=f"10.1000/{chunk_id}",
            chunk_locator=f"loc-{chunk_id}",
            section_id="section",
            section_path=["Results"],
            normalized_type="results",
            authors=[],
            title="Pilot paper",
            journal="Journal",
            publication_year=2020,
            language="en",
            license="CC-BY",
            source_url="https://example.test/source",
        )
        for chunk_id in ("dense-only", "shared", "lexical-only")
    }

    class _Connection:
        def begin(self):
            return nullcontext(self)

        def exec_driver_sql(self, statement):
            assert "READ ONLY" in statement

    class _Engine:
        def connect(self):
            return nullcontext(_Connection())

    class _TopPromoter:
        model_id = "test"
        model_revision = "test-revision"
        model_sha256 = "0" * 64

        def __init__(self):
            self.ids = ()

        def rerank(self, query_text, candidates):
            self.ids = tuple(item.chunk_id for item in candidates)
            return [
                (item.chunk_id, float(index))
                for index, item in enumerate(candidates)
            ]

    fake_reranker = _TopPromoter()
    embedder = SimpleNamespace(
        embed_query=lambda query, config: (1.0,) + (0.0,) * 1535
    )
    core = _RetrievalCore(
        cast(Engine, _Engine()),
        embedder,
        reranker=fake_reranker,
    )
    monkeypatch.setattr(core, "_read_preflight", lambda request_id: corpus)
    monkeypatch.setattr(
        _core, "_set_read_only_repeatable_read", lambda conn: None
    )
    monkeypatch.setattr(_core, "_read_corpus", lambda conn, request_id: corpus)
    monkeypatch.setattr(_core, "_eligible_count", lambda *args: 3)
    monkeypatch.setattr(
        _core,
        "_dense_branch",
        lambda *args: (BranchHit("dense-only", 0.9), BranchHit("shared", 0.8)),
    )
    bm25_calls = []

    def bm25_branch(*args, require_vectors):
        bm25_calls.append(require_vectors)
        return (BranchHit("lexical-only", 2.0), BranchHit("shared", 1.0))

    monkeypatch.setattr(_core, "_bm25_branch", bm25_branch)
    monkeypatch.setattr(
        _core,
        "_load_result_rows",
        lambda connection, corpus, filters, chunk_ids: rows,
    )

    response = core.retrieve(
        {
            "contract_version": "retrieval.v2",
            "request_id": "v2-core-test",
            "query_text": "bee disease",
            "mode": "hybrid",
            "top_k": 1,
        }
    )

    assert bm25_calls == [True]
    assert len(fake_reranker.ids) == 3
    assert response.contract_version == "retrieval.v2"
    assert [hit.chunk_id for hit in response.results] == [fake_reranker.ids[-1]]
    assert response.results[0].rank == 1
