"""RED behavior tests for the public retrieval question-service adapter."""

from __future__ import annotations

import importlib
from dataclasses import replace
from typing import Any

import pytest

from sciscope.question_service.contracts import ComponentMetadata
from sciscope.question_service.validation import ResponseContractFailure
from sciscope.retrieval import (
    Author,
    CorpusIdentity,
    PaperMetadata,
    RankingOptions,
    RetrievalFilters,
    RetrievalMetadata,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
    RetrievalScore,
)


class _PublicServiceSpy:
    """Record one public request and return an explicitly supplied response."""

    def __init__(self, response: object) -> None:
        self.response = response
        self.requests: list[RetrievalRequest] = []

    def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        """Record one request without accessing a resource or network."""
        self.requests.append(request)
        return self.response  # type: ignore[return-value]


def _adapter_types() -> tuple[type[Any], type[Any]]:
    """Load the planned public-boundary adapter contracts at test runtime.

    The module is intentionally loaded in individual test execution so pytest
    can report every specified behavior while T012-C is absent.
    """
    module = importlib.import_module(
        "sciscope.question_service.retrieval_adapter"
    )
    return module.PublicRetrievalAdapter, module.RetrievalAdapterSettings


def _settings(**updates: object) -> Any:
    """Return explicit offline settings without selecting a runtime default."""
    _, settings_type = _adapter_types()
    values: dict[str, object] = {
        "contract_version": "retrieval.v1",
        "mode": "hybrid",
        "top_k": 3,
        "filters": RetrievalFilters(
            publication_year_from=2011,
            publication_year_to=2015,
            normalized_types=("results",),
            journals=("PLOS ONE",),
        ),
        "ranking": RankingOptions(candidate_pool_size=8),
        "retrieval_metadata": ComponentMetadata(
            configured_origin="real",
            executed=False,
            is_test_data=True,
        ),
    }
    values.update(updates)
    return settings_type(**values)


def _response(**updates: object) -> RetrievalResponse:
    """Return a public response with deliberately distinctive provenance."""
    result = RetrievalResult(
        rank=1,
        chunk_id="chunk:distinctive-001",
        text="Exact passage: α-synuclein remained unchanged.",
        doi="10.1371/journal.pone.0123456",
        source_locator="jats:v1:/article/body/sec[4]/p[2]",
        section_id="section:results-4",
        section_path=("Results", "Subgroup analysis"),
        normalized_type="results",
        paper=PaperMetadata(
            title="Distinctive paper title: no normalization allowed",
            authors=(Author(surname="Researcher", given_names="R."),),
            journal="PLOS ONE",
            publication_year=2014,
            language="en",
            license="CC BY 4.0",
            source_url="https://doi.org/10.1371/journal.pone.0123456",
        ),
        scores=RetrievalScore(0.99, 1, 7.5, 1, 0.123),
    )
    values: dict[str, object] = {
        "contract_version": "retrieval.v1",
        "request_id": "adapter-request-001",
        "corpus": CorpusIdentity(
            delivery_digest="sha256:delivery-distinctive-001",
            source_contract_version="source-contract.v7",
            corpus_version="pilot-distinctive-2026-11-22",
        ),
        "embedding": None,
        "retrieval": RetrievalMetadata(
            mode="hybrid",
            top_k=3,
            candidate_pool_size=8,
            applied_filters=RetrievalFilters(
                publication_year_from=2011,
                publication_year_to=2015,
                normalized_types=("results",),
                journals=("PLOS ONE",),
            ),
            rrf_constant=60,
        ),
        "results": (result,),
        "warnings": (),
    }
    values.update(updates)
    return RetrievalResponse(**values)  # type: ignore[arg-type]


def _adapter(response: object, **setting_updates: object) -> _PublicServiceSpy:
    """Create the planned adapter around only an injected public-service spy."""
    adapter_type, _ = _adapter_types()
    service = _PublicServiceSpy(response)
    adapter_type(service=service, settings=_settings(**setting_updates))
    return service


def _retrieve(
    response: object, **setting_updates: object
) -> tuple[Any, _PublicServiceSpy]:
    """Run one call and retain the injected facade spy for assertions."""
    adapter_type, _ = _adapter_types()
    service = _PublicServiceSpy(response)
    adapter = adapter_type(
        service=service, settings=_settings(**setting_updates)
    )
    return adapter.retrieve(
        "Which results were reproduced?", "adapter-request-001"
    ), service


def test_adapter_constructs_one_explicit_public_request() -> None:
    """Forward one question and ID through the explicit public settings."""
    outcome, service = _retrieve(_response())

    assert len(service.requests) == 1
    request = service.requests[0]
    assert request.query_text == "Which results were reproduced?"
    assert request.request_id == "adapter-request-001"
    assert request.contract_version == "retrieval.v1"
    assert request.mode == "hybrid"
    assert request.top_k == 3
    assert request.filters == _settings().filters
    assert request.ranking == _settings().ranking
    assert outcome.metadata.configured_origin == "real"
    assert outcome.metadata.executed is True
    assert outcome.metadata.is_test_data is True


def test_adapter_preserves_exact_evidence_and_corpus_provenance() -> None:
    """Map source identity exactly without rewriting retrieved content."""
    outcome, _ = _retrieve(_response())
    evidence = outcome.evidence[0]

    assert evidence.chunk_id == "chunk:distinctive-001"
    assert evidence.doi == "10.1371/journal.pone.0123456"
    assert evidence.source_locator == "jats:v1:/article/body/sec[4]/p[2]"
    assert evidence.passage == "Exact passage: α-synuclein remained unchanged."
    assert (
        evidence.paper_title
        == "Distinctive paper title: no normalization allowed"
    )
    assert outcome.corpus.delivery_digest == "sha256:delivery-distinctive-001"
    assert outcome.corpus.source_contract_version == "source-contract.v7"
    assert outcome.corpus.corpus_version == "pilot-distinctive-2026-11-22"


def test_adapter_rejects_a_mismatched_response_request_id() -> None:
    """Fail closed instead of replacing a public response correlation ID."""
    with pytest.raises(ResponseContractFailure):
        _retrieve(_response(request_id="different-request-id"))


@pytest.mark.parametrize(
    "response",
    [
        lambda: _response(contract_version="retrieval.v2"),
        lambda: _response(
            retrieval=RetrievalMetadata(
                mode="dense",
                top_k=3,
                candidate_pool_size=None,
                applied_filters=None,
                rrf_constant=None,
            )
        ),
    ],
    ids=("unexpected-version", "unexpected-mode"),
)
def test_adapter_rejects_an_unexpected_response_configuration(
    response: Any,
) -> None:
    """Fail closed when the facade reports a different version or mode."""
    with pytest.raises(ResponseContractFailure):
        _retrieve(response())


def test_adapter_preserves_empty_results_and_real_retrieval_metadata() -> None:
    """Return no evidence without fabricating answer-provider metadata."""
    empty = _response(results=(), warnings=("EMPTY_RESULT",))
    outcome, service = _retrieve(empty)

    assert len(service.requests) == 1
    assert outcome.evidence == ()
    assert outcome.corpus.delivery_digest == empty.corpus.delivery_digest
    assert (
        outcome.corpus.source_contract_version
        == empty.corpus.source_contract_version
    )
    assert outcome.corpus.corpus_version == empty.corpus.corpus_version
    assert outcome.metadata.configured_origin == "real"
    assert outcome.metadata.executed is True
    assert outcome.metadata.is_test_data is True


@pytest.mark.parametrize(
    "response",
    [
        lambda: _response(
            results=(
                _response().results[0],
                _response().results[0],
            )
        ),
        lambda: _response(results=(replace(_response().results[0], doi=""),)),
        lambda: _response(
            corpus=CorpusIdentity(
                delivery_digest="",
                source_contract_version="source-contract.v7",
                corpus_version="pilot-distinctive-2026-11-22",
            )
        ),
    ],
    ids=("duplicate-chunk-id", "empty-doi", "empty-delivery-digest"),
)
def test_adapter_rejects_malformed_public_response_data(response: Any) -> None:
    """Reject duplicate or incomplete public data instead of partial mapping."""
    with pytest.raises(ResponseContractFailure):
        _retrieve(response())


def test_adapter_rejects_a_wrong_runtime_public_response_type() -> None:
    """Reject a facade result that is not the approved immutable DTO."""
    with pytest.raises(ResponseContractFailure):
        _retrieve(object())


@pytest.mark.parametrize(
    "settings_updates",
    [
        {"contract_version": None},
        {"mode": None},
        {"contract_version": "retrieval.v999"},
        {"mode": "unapproved-mode"},
        {"top_k": 0},
        {"filters": object()},
        {"ranking": RankingOptions(candidate_pool_size=2)},
    ],
    ids=(
        "missing-version",
        "missing-mode",
        "invalid-version",
        "invalid-mode",
        "invalid-top-k",
        "invalid-filters",
        "invalid-ranking",
    ),
)
def test_adapter_settings_fail_closed_without_mode_fallback(
    settings_updates: dict[str, object],
) -> None:
    """Require every server-owned retrieval setting before facade invocation."""
    with pytest.raises((ResponseContractFailure, ValueError, TypeError)):
        _retrieve(_response(), **settings_updates)


def test_adapter_is_constructed_only_with_an_injected_public_facade() -> None:
    """Keep adapter creation inert and independent of resource composition."""
    service = _adapter(_response())

    assert service.requests == []
