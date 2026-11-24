"""Adapter behavior over the real public RetrievalService mapping.

The private core response is produced by an injected fake executor, so the
real ``_map_private_response`` runs without a database or network.
"""

from __future__ import annotations

from typing import Any

import pytest

from sciscope.question_service.contracts import ComponentMetadata
from sciscope.question_service.retrieval_adapter import (
    PublicRetrievalAdapter,
    RetrievalAdapterSettings,
)
from sciscope.question_service.validation import ResponseContractFailure
from sciscope.retrieval import RetrievalFilters, RetrievalService
from sciscope.retrieval._core import (
    _Corpus,
    _EmbeddingConfig,
    _Hit,
    _Response,
    _Score,
)
from sciscope.retrieval._validation import InternalFilters


class _PrivateExecutor:
    """Return one private-core response without any I/O."""

    def __init__(self, response: _Response) -> None:
        self._response = response

    def retrieve(self, request: Any) -> _Response:
        """Echo the request id into the canned private response."""
        return _Response(
            contract_version=self._response.contract_version,
            request_id=request.request_id,
            mode=self._response.mode,
            top_k=self._response.top_k,
            candidate_pool_size=self._response.candidate_pool_size,
            applied_filters=self._response.applied_filters,
            rrf_constant=self._response.rrf_constant,
            corpus=self._response.corpus,
            embedding=self._response.embedding,
            results=self._response.results,
            warnings=self._response.warnings,
        )


def _private_response(applied_filters: InternalFilters) -> _Response:
    """Build a lexical private response with the given applied filters."""
    config = _EmbeddingConfig(
        provider="openai",
        model="text-embedding-3-small",
        dimensions=1536,
        query_prefix="query: ",
    )
    corpus = _Corpus(
        import_id=1,
        embedding_set_id=2,
        delivery_digest="sha256:" + "c" * 64,
        source_contract_version="0.3.0",
        corpus_version="pilot17-xml-1fff1573b610",
        embedding_config=config,
        embedding_compatible=True,
    )
    hit = _Hit(
        rank=1,
        chunk_id="d" * 64,
        text="Exact persisted source passage.",
        doi="10.1371/journal.pone.0077354",
        source_locator="jats:v1:xml-sha256:/article[1]/body[1]/sec[2]/p[3]",
        section_id="10.1371/journal.pone.0077354#sec-2",
        section_path=("Results",),
        normalized_type="results",
        paper={
            "title": "Exact source title",
            "authors": ({"surname": "Alpha", "given_names": "A."},),
            "journal": "PLOS ONE",
            "publication_year": 2013,
            "language": "EN",
            "license": "CC BY 4.0",
            "source_url": "https://doi.org/10.1371/journal.pone.0077354",
        },
        scores=_Score(None, None, 0.125, 1, None),
    )
    return _Response(
        contract_version="retrieval.v2",
        request_id="placeholder",
        mode="lexical",
        top_k=5,
        candidate_pool_size=None,
        applied_filters=applied_filters,
        rrf_constant=None,
        corpus=corpus,
        embedding=None,
        results=(hit,),
        warnings=(),
    )


def _adapter(
    settings_filters: RetrievalFilters | None,
    applied_filters: InternalFilters,
) -> PublicRetrievalAdapter:
    """Compose the adapter over the real public service mapping."""
    service = RetrievalService(
        executor=_PrivateExecutor(_private_response(applied_filters))
    )
    return PublicRetrievalAdapter(
        service=service,
        settings=RetrievalAdapterSettings(
            contract_version="retrieval.v2",
            mode="lexical",
            top_k=5,
            filters=settings_filters,
            ranking=None,
            retrieval_metadata=ComponentMetadata(
                configured_origin="real",
                executed=False,
                is_test_data=False,
            ),
        ),
    )


def test_none_filters_accept_real_service_all_empty_applied_filters() -> None:
    """Server settings use filters=None; the real mapper reports empty ones."""
    outcome = _adapter(None, InternalFilters()).retrieve("q", "req-1")

    assert outcome.evidence[0].chunk_id == "d" * 64


def test_empty_filters_accept_empty_applied_filters() -> None:
    """An explicit all-empty filter object equals an all-empty response."""
    outcome = _adapter(RetrievalFilters(), InternalFilters()).retrieve(
        "q", "req-1"
    )

    assert len(outcome.evidence) == 1


def test_non_empty_settings_filters_reject_empty_applied_filters() -> None:
    """A requested filter that the response did not apply is rejected."""
    adapter = _adapter(
        RetrievalFilters(journals=("PLOS ONE",)), InternalFilters()
    )

    with pytest.raises(ResponseContractFailure):
        adapter.retrieve("q", "req-1")


def test_none_settings_reject_non_empty_applied_filters() -> None:
    """A filter applied although none was requested is rejected."""
    adapter = _adapter(None, InternalFilters(journals=("PLOS ONE",)))

    with pytest.raises(ResponseContractFailure):
        adapter.retrieve("q", "req-1")


def test_equal_non_empty_filters_are_accepted() -> None:
    """Identical real filters pass."""
    adapter = _adapter(
        RetrievalFilters(journals=("PLOS ONE",)),
        InternalFilters(journals=("PLOS ONE",)),
    )

    assert len(adapter.retrieve("q", "req-1").evidence) == 1


def test_different_non_empty_filters_are_rejected() -> None:
    """A real filter mismatch still fails closed."""
    adapter = _adapter(
        RetrievalFilters(journals=("PLOS ONE",)),
        InternalFilters(journals=("Nature",)),
    )

    with pytest.raises(ResponseContractFailure):
        adapter.retrieve("q", "req-1")
