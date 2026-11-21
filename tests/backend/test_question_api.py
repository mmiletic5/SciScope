"""HTTP behavior tests for the Feature 011 fake-only question endpoint."""

from dataclasses import dataclass, field, replace

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from sciscope.api.app import create_app
from sciscope.question_service.contracts import (
    ProviderOutcome,
    RetrievalOutcome,
)
from sciscope.question_service.fakes import FakeAnswerProvider, FakeRetrieval


@dataclass
class _CountingProvider:
    """Counts provider calls while delegating to a configured fake provider."""

    delegate: FakeAnswerProvider
    calls: int = 0

    def answer(
        self,
        question: str,
        evidence: tuple[object, ...],
        corpus: object,
        request_id: str,
    ) -> ProviderOutcome:
        self.calls += 1
        return self.delegate.answer(
            question,
            evidence,  # type: ignore[arg-type]
            corpus,  # type: ignore[arg-type]
            request_id,
        )


@dataclass
class _FixedRetrieval:
    """Returns a supplied retrieval fixture without external access."""

    outcome: RetrievalOutcome
    calls: list[tuple[str, str]] = field(default_factory=list)

    def retrieve(self, question: str, request_id: str) -> RetrievalOutcome:
        self.calls.append((question, request_id))
        return self.outcome


@dataclass
class _FixedProvider:
    """Returns a supplied provider fixture without external access."""

    outcome: ProviderOutcome

    def answer(
        self,
        question: str,
        evidence: tuple[object, ...],
        corpus: object,
        request_id: str,
    ) -> ProviderOutcome:
        del question, evidence, corpus, request_id
        return self.outcome


class _UnexpectedRetrieval:
    """Raises a private defect to exercise the public error boundary."""

    def retrieve(self, question: str, request_id: str) -> RetrievalOutcome:
        del question, request_id
        raise RuntimeError("private unexpected retrieval detail")


@pytest.mark.parametrize(
    ("retrieval", "provider", "expected_status"),
    [
        (FakeRetrieval(), FakeAnswerProvider(), "answered"),
        (FakeRetrieval(mode="empty"), FakeAnswerProvider(), "no_results"),
        (
            FakeRetrieval(),
            FakeAnswerProvider(mode="insufficient_evidence"),
            "insufficient_evidence",
        ),
    ],
)
def test_question_endpoint_returns_each_approved_success_state(
    retrieval: FakeRetrieval,
    provider: FakeAnswerProvider,
    expected_status: str,
) -> None:
    """Return only the approved closed synthetic success states."""
    app = create_app(
        retrieval=retrieval,
        provider=provider,
        request_id_factory=lambda: "generated-request-id",
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/questions",
            json={
                "workflow": "research_question",
                "question": "  fixture question  ",
                "request_id": "caller-request-7",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["api_version"] == "v1"
    assert body["request_id"] == "caller-request-7"
    assert body["workflow"] == "research_question"
    assert body["status"] == expected_status
    assert body["metadata"] == {"is_mock": True, "is_test_data": True}
    assert body["corpus"]["delivery_digest"]
    assert body["corpus"]["source_contract_version"]
    assert body["corpus"]["corpus_version"]
    assert set(body) == {
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
    if expected_status == "answered":
        assert body["answer"]
        assert body["claims"][0]["citation_chunk_ids"] == [
            body["evidence"][0]["chunk_id"]
        ]
    elif expected_status == "no_results":
        assert body["answer"] is None
        assert body["claims"] == []
        assert body["evidence"] == []
    else:
        assert body["answer"] is None
        assert body["claims"] == []
        assert body["evidence"]


def test_question_endpoint_skips_provider_for_empty_retrieval() -> None:
    """Use injected dependencies and skip generation when retrieval is empty."""
    retrieval = _FixedRetrieval(
        FakeRetrieval(mode="empty").retrieve("fixture question", "request-8")
    )
    provider = _CountingProvider(FakeAnswerProvider())
    app = create_app(
        retrieval=retrieval,
        provider=provider,
        request_id_factory=lambda: "generated-request-id",
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/questions",
            json={
                "workflow": "research_question",
                "question": "fixture question",
            },
        )

    assert response.status_code == 200
    assert response.json()["request_id"] == "generated-request-id"
    assert retrieval.calls == [("fixture question", "generated-request-id")]
    assert provider.calls == 0


@pytest.mark.parametrize(
    ("retrieval", "provider", "status_code", "error_code"),
    [
        (
            FakeRetrieval(mode="unavailable"),
            FakeAnswerProvider(),
            503,
            "retrieval_unavailable",
        ),
        (
            FakeRetrieval(mode="timeout"),
            FakeAnswerProvider(),
            504,
            "dependency_timeout",
        ),
        (
            FakeRetrieval(),
            FakeAnswerProvider(mode="unavailable"),
            503,
            "provider_unavailable",
        ),
        (
            FakeRetrieval(),
            FakeAnswerProvider(mode="timeout"),
            504,
            "dependency_timeout",
        ),
    ],
)
def test_question_endpoint_maps_controlled_dependency_failures(
    retrieval: FakeRetrieval,
    provider: FakeAnswerProvider,
    status_code: int,
    error_code: str,
) -> None:
    """Return the approved sanitized envelope for declared fake failures."""
    app = create_app(
        retrieval=retrieval,
        provider=provider,
        request_id_factory=lambda: "generated-error-id",
    )
    private_question = "Private question that must not be exposed"

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/questions",
            json={
                "workflow": "research_question",
                "question": private_question,
                "request_id": "caller-error-id",
            },
        )

    _assert_sanitized_error(
        response,
        status_code=status_code,
        error_code=error_code,
        request_id="caller-error-id",
        retryable=True,
        private_value=private_question,
    )


def test_question_endpoint_maps_invalid_output_to_contract_failure() -> None:
    """Discard invalid fake output behind the approved contract-failure code."""
    retrieval_outcome = FakeRetrieval().retrieve(
        "fixture question", "fixture-request"
    )
    provider_outcome = FakeAnswerProvider().answer(
        "fixture question",
        retrieval_outcome.evidence,
        retrieval_outcome.corpus,
        "fixture-request",
    )
    invalid_provider_outcome = replace(
        provider_outcome,
        claims=(
            replace(
                provider_outcome.claims[0],
                citation_chunk_ids=("private-invalid-citation",),
            ),
        ),
    )
    app = create_app(
        retrieval=_FixedRetrieval(retrieval_outcome),
        provider=_FixedProvider(invalid_provider_outcome),
        request_id_factory=lambda: "generated-contract-id",
    )
    private_question = "Private question that must not be exposed"

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/questions",
            json={
                "workflow": "research_question",
                "question": private_question,
            },
        )

    _assert_sanitized_error(
        response,
        status_code=500,
        error_code="response_contract_failure",
        request_id="generated-contract-id",
        retryable=False,
        private_value="private-invalid-citation",
    )
    assert private_question not in response.text


def test_question_endpoint_maps_unexpected_errors_without_hiding_them() -> None:
    """Return a sanitized error publicly while preserving test observability."""
    app = create_app(
        retrieval=_UnexpectedRetrieval(),
        provider=FakeAnswerProvider(),
        request_id_factory=lambda: "generated-internal-id",
    )
    payload = {
        "workflow": "research_question",
        "question": "Private question that must not be exposed",
    }

    with pytest.raises(
        RuntimeError, match="private unexpected retrieval detail"
    ):
        with TestClient(app) as client:
            client.post("/api/v1/questions", json=payload)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/v1/questions", json=payload)

    _assert_sanitized_error(
        response,
        status_code=500,
        error_code="internal_error",
        request_id="generated-internal-id",
        retryable=False,
        private_value="private unexpected retrieval detail",
    )
    assert payload["question"] not in response.text


def _assert_sanitized_error(
    response: Response,
    *,
    status_code: int,
    error_code: str,
    request_id: str,
    retryable: bool,
    private_value: str,
) -> None:
    """Assert a closed error shape without private implementation data."""
    assert response.status_code == status_code
    body = response.json()
    assert body == {
        "api_version": "v1",
        "request_id": request_id,
        "error": {
            "code": error_code,
            "message": body["error"]["message"],
            "retryable": retryable,
        },
        "metadata": {"is_mock": True, "is_test_data": True},
    }
    assert body["error"]["message"].strip()
    assert private_value not in response.text
