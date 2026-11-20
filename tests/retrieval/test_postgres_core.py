"""Read-only PostgreSQL integration tests against the accepted pilot."""

from __future__ import annotations

import math
from collections.abc import Sequence

import pytest
from sqlalchemy import select, text

from sciscope.database.models import (
    Chunk,
    ChunkEmbedding,
    DeliveryImport,
    EmbeddingSet,
)
from sciscope.retrieval._core import _RetrievalCore
from sciscope.retrieval._errors import RetrievalErrorCode, RetrievalFailure

from .conftest import FakeEmbedder, independent_rrf_oracle


def _request(
    mode: str,
    *,
    top_k: int = 5,
    filters: dict[str, object] | None = None,
    contract_version: str = "retrieval.v1",
) -> dict[str, object]:
    request: dict[str, object] = {
        "contract_version": contract_version,
        "request_id": "phase-b-integration",
        "query_text": "honey bee",
        "mode": mode,
        "top_k": top_k,
    }
    if filters is not None:
        request["filters"] = filters
    return request


def test_v2_bm25_returns_directly_usable_source_evidence(retrieval_engine):
    """The opt-in BM25 mode returns stable, fully attributed passages."""
    result = _RetrievalCore(retrieval_engine, None).retrieve(
        _request("lexical", top_k=5, contract_version="retrieval.v2")
    )

    assert result.contract_version == "retrieval.v2"
    assert result.mode == "lexical"
    assert result.results
    assert [hit.rank for hit in result.results] == list(
        range(1, len(result.results) + 1)
    )
    for hit in result.results:
        assert len(hit.chunk_id) == 64
        assert hit.text.strip()
        assert hit.doi.startswith("10.")
        assert hit.source_locator.startswith("jats:v1:")
        assert hit.paper["title"]
        assert hit.scores.lexical_rank is not None
        assert hit.scores.lexical_score is not None
        assert hit.scores.dense_rank is None
        assert hit.scores.fusion_score is None


def test_v2_hybrid_fuses_dense_and_bm25_with_large_candidate_pool(
    retrieval_engine,
):
    """The v2 response preserves both branch ranks and source identity."""
    with retrieval_engine.connect() as connection:
        active_id = connection.execute(
            select(DeliveryImport.id).where(DeliveryImport.is_active.is_(True))
        ).scalar_one()
        embedding_set_id = connection.execute(
            select(EmbeddingSet.id).where(
                EmbeddingSet.delivery_import_id == active_id
            )
        ).scalar_one()
        vector = connection.execute(
            select(ChunkEmbedding.embedding)
            .where(ChunkEmbedding.embedding_set_id == embedding_set_id)
            .order_by(ChunkEmbedding.chunk_id)
            .limit(1)
        ).scalar_one()
    query = _unit_vector(tuple(float(value) for value in vector))
    request = _request("hybrid", top_k=5, contract_version="retrieval.v2")
    request["ranking"] = {"candidate_pool_size": 20}

    result = _RetrievalCore(retrieval_engine, FakeEmbedder(query, [])).retrieve(
        request
    )

    assert result.contract_version == "retrieval.v2"
    assert result.candidate_pool_size == 20
    assert result.rrf_constant == 60
    assert result.results
    assert len(result.results) <= 5
    assert all(hit.scores.fusion_score is not None for hit in result.results)
    assert any(
        hit.scores.dense_rank is not None
        and hit.scores.lexical_rank is not None
        for hit in result.results
    )
    for hit in result.results:
        assert hit.text.strip()
        assert hit.doi.startswith("10.")
        assert hit.source_locator.startswith("jats:v1:")
        assert hit.paper["title"]
        assert hit.scores.fusion_score is not None
        assert (
            hit.scores.dense_rank is not None
            or hit.scores.lexical_rank is not None
        )


def _unit_vector(values: Sequence[float]) -> tuple[float, ...]:
    norm = math.hypot(*values)
    return tuple(value / norm for value in values)


def test_exact_dense_scores_match_python_oracle_and_keep_provenance(
    retrieval_engine,
) -> None:
    """Dense results match an independent cosine oracle on active vectors."""
    with retrieval_engine.connect() as connection:
        active_id = connection.execute(
            select(DeliveryImport.id).where(DeliveryImport.is_active.is_(True))
        ).scalar_one()
        embedding_set_id = connection.execute(
            select(EmbeddingSet.id).where(
                EmbeddingSet.delivery_import_id == active_id
            )
        ).scalar_one()
        vectors = connection.execute(
            select(ChunkEmbedding.chunk_id, ChunkEmbedding.embedding)
            .where(ChunkEmbedding.embedding_set_id == embedding_set_id)
            .order_by(ChunkEmbedding.chunk_id)
        ).all()
    if len(vectors) != 728:
        pytest.fail("Expected the preserved Phase A 728-vector pilot")
    query = _unit_vector(tuple(float(value) for value in vectors[0].embedding))
    query_norm = math.hypot(*query)
    expected = sorted(
        (
            (
                str(chunk_id),
                sum(
                    query[index] * float(vector[index])
                    for index in range(len(query))
                )
                / (
                    query_norm * math.hypot(*(float(value) for value in vector))
                ),
            )
            for chunk_id, vector in vectors
        ),
        key=lambda item: (-item[1], item[0]),
    )[:5]
    fake = FakeEmbedder(query, [])
    result = _RetrievalCore(retrieval_engine, fake).retrieve(_request("dense"))

    assert [hit.chunk_id for hit in result.results] == [
        item[0] for item in expected
    ]
    for hit, (_, similarity) in zip(result.results, expected, strict=True):
        assert hit.scores.dense_similarity == pytest.approx(
            similarity, abs=2e-5
        )
        assert hit.scores.dense_rank is not None
        assert hit.scores.lexical_rank is None
        assert hit.text
        assert hit.source_locator.startswith("jats:v1:")
        assert hit.doi.startswith("10.")
    assert result.corpus.delivery_digest.startswith("sha256:")
    assert result.corpus.corpus_version.startswith("pilot17-xml-")
    assert len(fake.calls) == 1


def test_english_fts_is_repeatable_and_uses_chunk_text_only(retrieval_engine):
    """The requested English lexical branch returns stable scored chunks."""
    core = _RetrievalCore(retrieval_engine, None)
    request = _request("lexical", top_k=20)
    request["query_text"] = "bee"
    first = core.retrieve(request)
    second = core.retrieve(request)
    assert first.results
    assert [hit.chunk_id for hit in first.results] == [
        hit.chunk_id for hit in second.results
    ]
    scores = [hit.scores.lexical_score for hit in first.results]
    assert all(score is not None for score in scores)
    assert scores == sorted(scores, reverse=True)
    tied_ids: dict[float, list[str]] = {}
    for hit in first.results:
        assert hit.scores.lexical_score is not None
        tied_ids.setdefault(hit.scores.lexical_score, []).append(hit.chunk_id)
    tied_groups = [ids for ids in tied_ids.values() if len(ids) > 1]
    assert tied_groups
    assert all(ids == sorted(ids) for ids in tied_groups)
    assert all(hit.scores.dense_rank is None for hit in first.results)


def test_filters_are_shared_across_all_modes(retrieval_engine):
    """Identical canonical filters constrain dense, lexical, and hybrid."""
    with retrieval_engine.connect() as connection:
        row = connection.execute(
            select(
                Chunk.doi,
                Chunk.normalized_type,
                Chunk.delivery_import_id,
            )
            .join(DeliveryImport, DeliveryImport.id == Chunk.delivery_import_id)
            .where(DeliveryImport.is_active.is_(True))
            .order_by(Chunk.chunk_id)
            .limit(1)
        ).one()
    filters: dict[str, object] = {
        "dois": [row.doi.upper()],
        "normalized_types": [row.normalized_type],
    }
    fake = FakeEmbedder((1.0,) + (0.0,) * 1535, [])
    core = _RetrievalCore(retrieval_engine, fake)
    for mode in ("dense", "lexical", "hybrid"):
        result = core.retrieve(_request(mode, top_k=10, filters=filters))
        assert all(hit.doi == row.doi for hit in result.results)
        assert all(
            hit.normalized_type == row.normalized_type for hit in result.results
        )


def test_hybrid_matches_independent_rrf_oracle(retrieval_engine):
    """Fusion agrees with an independently ranked branch oracle."""
    with retrieval_engine.connect() as connection:
        active_id = connection.execute(
            select(DeliveryImport.id).where(DeliveryImport.is_active.is_(True))
        ).scalar_one()
        embedding_set_id = connection.execute(
            select(EmbeddingSet.id).where(
                EmbeddingSet.delivery_import_id == active_id
            )
        ).scalar_one()
        vector = connection.execute(
            select(ChunkEmbedding.embedding)
            .where(ChunkEmbedding.embedding_set_id == embedding_set_id)
            .order_by(ChunkEmbedding.chunk_id)
            .limit(1)
        ).scalar_one()
    query = _unit_vector(tuple(float(value) for value in vector))
    pool = 10
    fake = FakeEmbedder(query, [])
    core = _RetrievalCore(retrieval_engine, fake)
    dense = core.retrieve(_request("dense", top_k=pool))
    lexical = core.retrieve(_request("lexical", top_k=pool))
    hybrid_request = _request("hybrid", top_k=5)
    hybrid_request["ranking"] = {"candidate_pool_size": pool}
    hybrid = core.retrieve(hybrid_request)
    expected = independent_rrf_oracle(
        [hit.chunk_id for hit in dense.results],
        [hit.chunk_id for hit in lexical.results],
    )[:5]
    assert [hit.chunk_id for hit in hybrid.results] == [
        row[0] for row in expected
    ]
    assert [hit.scores.fusion_score for hit in hybrid.results] == [
        row[1] for row in expected
    ]
    dense_ranks = {
        hit.chunk_id: rank for rank, hit in enumerate(dense.results, start=1)
    }
    lexical_ranks = {
        hit.chunk_id: rank for rank, hit in enumerate(lexical.results, start=1)
    }
    for hit in hybrid.results:
        assert hit.scores.dense_rank == dense_ranks.get(hit.chunk_id)
        assert hit.scores.lexical_rank == lexical_ranks.get(hit.chunk_id)


def test_empty_lexical_query_is_successful_and_does_not_embed(retrieval_engine):
    """Stop-word-only English query produces an empty lexical success."""
    fake = FakeEmbedder((1.0,) + (0.0,) * 1535, [])
    core = _RetrievalCore(retrieval_engine, fake)
    request = _request("lexical")
    request["query_text"] = "the and of"
    result = core.retrieve(request)
    assert result.results == ()
    assert result.warnings == ("EMPTY_RESULT",)
    assert fake.calls == []


def test_incompatible_query_configuration_fails_without_fallback(
    retrieval_engine,
):
    """Unexpected vector output produces a typed error and no lexical branch."""
    fake = FakeEmbedder((0.0,) * 1536, [])
    request = _request("hybrid")
    with pytest.raises(RetrievalFailure) as raised:
        _RetrievalCore(retrieval_engine, fake).retrieve(request)
    assert (
        raised.value.code == RetrievalErrorCode.EMBEDDING_CONFIGURATION_MISMATCH
    )


def test_dense_preflight_and_result_reads_use_read_only_repeatable_read(
    retrieval_engine, monkeypatch
):
    """Both DB phases establish the promised read-only snapshot isolation."""
    from sciscope.retrieval import _core

    original = _core._read_corpus
    transaction_modes: list[tuple[str, str]] = []

    def inspect_transaction(connection, request_id):
        isolation, read_only = connection.execute(
            text(
                "SELECT current_setting('transaction_isolation'), "
                "current_setting('transaction_read_only')"
            )
        ).one()
        transaction_modes.append((isolation, read_only))
        return original(connection, request_id)

    monkeypatch.setattr(_core, "_read_corpus", inspect_transaction)
    with retrieval_engine.connect() as connection:
        active_id = connection.execute(
            select(DeliveryImport.id).where(DeliveryImport.is_active.is_(True))
        ).scalar_one()
        embedding_set_id = connection.execute(
            select(EmbeddingSet.id).where(
                EmbeddingSet.delivery_import_id == active_id
            )
        ).scalar_one()
        vector = connection.execute(
            select(ChunkEmbedding.embedding)
            .where(ChunkEmbedding.embedding_set_id == embedding_set_id)
            .order_by(ChunkEmbedding.chunk_id)
            .limit(1)
        ).scalar_one()
    query = _unit_vector(tuple(float(value) for value in vector))
    _RetrievalCore(retrieval_engine, FakeEmbedder(query, [])).retrieve(
        _request("dense")
    )
    assert transaction_modes == [
        ("repeatable read", "on"),
        ("repeatable read", "on"),
    ]
