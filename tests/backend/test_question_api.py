"""HTTP behavior tests for the Feature 011 fake-only question endpoint."""

from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient

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
