"""RED contract tests for the proposed Feature 012 v2 question endpoint.

The endpoint and its closed models do not exist yet. These tests record the
approved planning proposal without changing the accepted Feature 011 v1 API.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from sciscope.api.app import create_app
from sciscope.question_service.contracts import (
    Claim,
    ComponentMetadata,
    CorpusProvenance,
    DependencyFailure,
    DependencyFailureCode,
    Evidence,
    ProviderOutcome,
    ProviderOutcomeStatus,
    QuestionMetadata,
    RetrievalOutcome,
)
from sciscope.question_service.fakes import FakeAnswerProvider, FakeRetrieval
from sciscope.retrieval import RetrievalErrorCode, RetrievalException


@dataclass(frozen=True, slots=True)
class _FixedRetrieval:
    """Return one explicit offline retrieval outcome."""

    outcome: RetrievalOutcome

    def retrieve(self, question: str, request_id: str) -> RetrievalOutcome:
        del question, request_id
        return self.outcome


@dataclass(frozen=True, slots=True)
class _RaisingRetrieval:
    """Raise one public retrieval error without any external dependency."""

    exception: RetrievalException

    def retrieve(self, question: str, request_id: str) -> RetrievalOutcome:
        del question, request_id
        raise self.exception


@dataclass(slots=True)
class _CountingProvider:
    """Count calls while returning a fixed offline provider outcome."""

    outcome: ProviderOutcome
    calls: int = 0

    def answer(
        self,
        question: str,
        evidence: tuple[Evidence, ...],
        corpus: CorpusProvenance,
        request_id: str,
    ) -> ProviderOutcome:
        del question, evidence, corpus, request_id
        self.calls += 1
        return self.outcome


_REQUEST = {
    "workflow": "research_question",
    "question": "Which result was reproduced?",
    "request_id": "v2-request-001",
}
_RETRIEVAL_METADATA = ComponentMetadata(
    configured_origin="real", executed=True, is_test_data=True
)
_PROVIDER_METADATA = ComponentMetadata(
    configured_origin="fake", executed=True, is_test_data=True
)
_CORPUS = CorpusProvenance(
    delivery_digest="sha256:v2-fixture-digest",
    source_contract_version="source-contract.v2-fixture",
    corpus_version="v2-fixture-corpus",
)
_EVIDENCE = Evidence(
    chunk_id="v2-chunk-001",
    doi="10.0000/v2.fixture.001",
    source_locator="fixture:results:1",
    passage="Exact fixture passage for the v2 contract.",
    paper_title="V2 Fixture Paper",
)


def _app(
    retrieval: object = FakeRetrieval(),
    provider: object = FakeAnswerProvider(),
) -> TestClient:
    """Return an inert in-process app with only explicit fake dependencies."""
    return TestClient(
        create_app(
            retrieval=retrieval,
            provider=provider,
            v2_metadata=QuestionMetadata(
                retrieval=ComponentMetadata(
                    configured_origin="real",
                    executed=False,
                    is_test_data=True,
                ),
                answer_provider=ComponentMetadata(
                    configured_origin="fake",
                    executed=False,
                    is_test_data=True,
                ),
            ),
            request_id_factory=lambda: "generated-v2-request-id",
        ),
        raise_server_exceptions=False,
    )


def _answered_retrieval() -> RetrievalOutcome:
    """Return an offline real-retrieval fixture with exact provenance."""
    return RetrievalOutcome(
        evidence=(_EVIDENCE,),
        corpus=_CORPUS,
        metadata=_RETRIEVAL_METADATA,
    )


def _answered_provider() -> ProviderOutcome:
    """Return an offline fake-provider fixture with local citations only."""
    return ProviderOutcome(
        status=ProviderOutcomeStatus.ANSWERED,
        answer="Fixture answer derived from the configured fake provider.",
        claims=(
            Claim(
                claim_id="v2-claim-001",
                text="Fixture claim linked to v2 response evidence.",
                citation_chunk_ids=("v2-chunk-001",),
            ),
        ),
        metadata=_PROVIDER_METADATA,
    )


def test_v2_returns_the_proposed_closed_answered_response() -> None:
    """Expose response-local evidence and both truthful component states."""
    retrieval = _FixedRetrieval(_answered_retrieval())
    provider = _CountingProvider(_answered_provider())
    with _app(retrieval, provider) as client:
        response = client.post("/api/v2/questions", json=_REQUEST)

    assert response.status_code == 200
    assert response.json() == {
        "api_version": "v2",
        "request_id": "v2-request-001",
        "workflow": "research_question",
        "status": "answered",
        "answer": "Fixture answer derived from the configured fake provider.",
        "claims": [
            {
                "claim_id": "v2-claim-001",
                "text": "Fixture claim linked to v2 response evidence.",
                "citation_chunk_ids": ["v2-chunk-001"],
            }
        ],
        "evidence": [
            {
                "chunk_id": "v2-chunk-001",
                "doi": "10.0000/v2.fixture.001",
                "source_locator": "fixture:results:1",
                "passage": "Exact fixture passage for the v2 contract.",
                "paper_title": "V2 Fixture Paper",
            }
        ],
        "corpus": {
            "delivery_digest": "sha256:v2-fixture-digest",
            "source_contract_version": "source-contract.v2-fixture",
            "corpus_version": "v2-fixture-corpus",
        },
        "metadata": {
            "retrieval": {
                "configured_origin": "real",
                "executed": True,
                "is_test_data": True,
            },
            "answer_provider": {
                "configured_origin": "fake",
                "executed": True,
                "is_test_data": True,
            },
        },
    }


@pytest.mark.parametrize(
    "payload",
    [
        {"workflow": "research_question", "question": "   "},
        {"workflow": "research_question", "question": "valid", "mode": "dense"},
        {"workflow": "unsupported", "question": "valid"},
    ],
    ids=("blank-question", "caller-mode-is-forbidden", "invalid-workflow"),
)
def test_v2_rejects_invalid_or_unsupported_request_values(
    payload: dict[str, object],
) -> None:
    """Keep retrieval settings server-owned and request validation closed."""
    with _app() as client:
        response = client.post("/api/v2/questions", json=payload)

    assert response.status_code == 422


def test_v2_no_results_preserves_corpus_and_skips_the_provider() -> None:
    """Represent empty retrieval without inventing an answer or provider call.

    The configured provider remains visible but has not run.
    """
    provider = _CountingProvider(_answered_provider())
    retrieval = RetrievalOutcome(
        evidence=(),
        corpus=_CORPUS,
        metadata=QuestionMetadata(
            retrieval=_RETRIEVAL_METADATA,
            answer_provider=ComponentMetadata(
                configured_origin="fake", executed=False, is_test_data=True
            ),
        ),
    )

    with _app(_FixedRetrieval(retrieval), provider) as client:
        response = client.post("/api/v2/questions", json=_REQUEST)

    assert response.status_code == 200
    assert response.json()["status"] == "no_results"
    assert response.json()["answer"] is None
    assert response.json()["claims"] == []
    assert response.json()["evidence"] == []
    assert response.json()["corpus"] == {
        "delivery_digest": "sha256:v2-fixture-digest",
        "source_contract_version": "source-contract.v2-fixture",
        "corpus_version": "v2-fixture-corpus",
    }
    assert response.json()["metadata"]["answer_provider"] == {
        "configured_origin": "fake",
        "executed": False,
        "is_test_data": True,
    }
    assert provider.calls == 0


def test_v2_insufficient_evidence_returns_no_answer_or_claims() -> None:
    """Refuse to answer without converting a provider decision into an error."""
    provider = _CountingProvider(
        ProviderOutcome(
            status=ProviderOutcomeStatus.INSUFFICIENT_EVIDENCE,
            answer=None,
            claims=(),
            metadata=_PROVIDER_METADATA,
        )
    )

    with _app(_FixedRetrieval(_answered_retrieval()), provider) as client:
        response = client.post("/api/v2/questions", json=_REQUEST)

    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_evidence"
    assert response.json()["answer"] is None
    assert response.json()["claims"] == []
    assert response.json()["evidence"][0]["chunk_id"] == "v2-chunk-001"
    assert provider.calls == 1


@pytest.mark.parametrize(
    ("code", "retryable", "status_code", "error_code", "message"),
    [
        (
            RetrievalErrorCode.INVALID_REQUEST,
            False,
            500,
            "internal_error",
            "An internal error occurred.",
        ),
        (
            RetrievalErrorCode.UNSUPPORTED_CONTRACT_VERSION,
            False,
            500,
            "internal_error",
            "An internal error occurred.",
        ),
        (
            RetrievalErrorCode.CORPUS_NOT_LOADED,
            False,
            503,
            "retrieval_unavailable",
            "The requested dependency is currently unavailable.",
        ),
        (
            RetrievalErrorCode.EMBEDDING_CONFIGURATION_MISMATCH,
            False,
            503,
            "retrieval_unavailable",
            "The requested dependency is currently unavailable.",
        ),
        (
            RetrievalErrorCode.EMBEDDING_UNAVAILABLE,
            True,
            503,
            "retrieval_unavailable",
            "The requested dependency is currently unavailable.",
        ),
        (
            RetrievalErrorCode.DATABASE_UNAVAILABLE,
            True,
            503,
            "retrieval_unavailable",
            "The requested dependency is currently unavailable.",
        ),
        (
            RetrievalErrorCode.RETRIEVAL_INTERNAL_ERROR,
            False,
            500,
            "internal_error",
            "An internal error occurred.",
        ),
    ],
)
def test_v2_maps_each_public_retrieval_error_without_private_details(
    code: RetrievalErrorCode,
    retryable: bool,
    status_code: int,
    error_code: str,
    message: str,
) -> None:
    """Preserve typed retryability in the proposed sanitized v2 envelope."""
    exception = RetrievalException(
        code=code,
        request_id="v2-request-001",
        retryable=retryable,
        public_message="private implementation details must not be exposed",
    )

    with _app(_RaisingRetrieval(exception)) as client:
        response = client.post("/api/v2/questions", json=_REQUEST)

    assert response.status_code == status_code
    assert response.json() == {
        "api_version": "v2",
        "request_id": "v2-request-001",
        "error": {
            "code": error_code,
            "message": message,
            "retryable": retryable,
        },
        "metadata": {
            "retrieval": {
                "configured_origin": "real",
                "executed": True,
                "is_test_data": True,
            },
            "answer_provider": {
                "configured_origin": "fake",
                "executed": False,
                "is_test_data": True,
            },
        },
    }
    assert exception.public_message not in response.text


def test_v2_error_uses_the_route_request_id_not_a_downstream_id() -> None:
    """Keep the HTTP correlation ID authoritative at the public boundary."""
    exception = RetrievalException(
        code=RetrievalErrorCode.DATABASE_UNAVAILABLE,
        request_id="different-downstream-request-id",
        retryable=True,
        public_message="private downstream correlation must not be exposed",
    )

    with _app(_RaisingRetrieval(exception)) as client:
        response = client.post("/api/v2/questions", json=_REQUEST)

    assert response.status_code == 503
    assert response.json()["request_id"] == "v2-request-001"
    assert "different-downstream-request-id" not in response.text


def test_v2_retrieval_failure_marks_only_retrieval_as_executed() -> None:
    """Report the real attempted retrieval without inventing provider use."""
    exception = RetrievalException(
        code=RetrievalErrorCode.CORPUS_NOT_LOADED,
        request_id="v2-request-001",
        retryable=False,
        public_message="No active corpus is available.",
    )

    with _app(_RaisingRetrieval(exception)) as client:
        response = client.post("/api/v2/questions", json=_REQUEST)

    assert response.status_code == 503
    assert response.json()["metadata"] == {
        "retrieval": {
            "configured_origin": "real",
            "executed": True,
            "is_test_data": True,
        },
        "answer_provider": {
            "configured_origin": "fake",
            "executed": False,
            "is_test_data": True,
        },
    }


def test_v2_provider_failure_marks_both_components_as_executed() -> None:
    """Preserve a provider invocation that fails after valid retrieval."""

    class _UnavailableProvider:
        def answer(
            self,
            question: str,
            evidence: tuple[Evidence, ...],
            corpus: CorpusProvenance,
            request_id: str,
        ) -> ProviderOutcome:
            del question, evidence, corpus, request_id
            raise DependencyFailure(DependencyFailureCode.PROVIDER_UNAVAILABLE)

    retrieval = _FixedRetrieval(_answered_retrieval())
    with _app(retrieval, _UnavailableProvider()) as client:
        response = client.post("/api/v2/questions", json=_REQUEST)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "provider_unavailable"
    assert response.json()["metadata"] == {
        "retrieval": {
            "configured_origin": "real",
            "executed": True,
            "is_test_data": True,
        },
        "answer_provider": {
            "configured_origin": "fake",
            "executed": True,
            "is_test_data": True,
        },
    }


def test_v2_rejects_nonlocal_citations_without_returning_an_answer() -> None:
    """Fail closed when provider output cites evidence outside this response."""
    provider = _CountingProvider(
        ProviderOutcome(
            status=ProviderOutcomeStatus.ANSWERED,
            answer="An answer that must not be returned.",
            claims=(
                Claim(
                    claim_id="invalid-claim",
                    text="Claim with an invalid citation.",
                    citation_chunk_ids=("not-in-this-response",),
                ),
            ),
            metadata=_PROVIDER_METADATA,
        )
    )

    with _app(_FixedRetrieval(_answered_retrieval()), provider) as client:
        response = client.post("/api/v2/questions", json=_REQUEST)

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "response_contract_failure"
    assert "An answer that must not be returned." not in response.text
    assert provider.calls == 1


def test_v2_preserves_the_controlled_timeout_contract() -> None:
    """Retain approved timeout status, code, retryability, and request ID."""
    with _app(FakeRetrieval(mode="timeout")) as client:
        response = client.post("/api/v2/questions", json=_REQUEST)

    assert response.status_code == 504
    assert response.json()["request_id"] == "v2-request-001"
    assert response.json()["error"] == {
        "code": "dependency_timeout",
        "message": "The requested dependency timed out.",
        "retryable": True,
    }


def test_v2_work_does_not_change_the_accepted_v1_success_shape() -> None:
    """Keep the accepted fake-only v1 response keys and literal metadata."""
    with _app() as client:
        response = client.post("/api/v1/questions", json=_REQUEST)

    assert response.status_code == 200
    assert set(response.json()) == {
        "api_version",
        "request_id",
        "workflow",
        "status",
        "answer",
        "claims",
        "evidence",
        "corpus",
        "metadata",
    }
    assert response.json()["metadata"] == {
        "is_mock": True,
        "is_test_data": True,
    }
