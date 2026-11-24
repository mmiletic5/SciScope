"""HTTP-level checks for evaluation cases EV-11, EV-12, EV-13 and EV-15.

The cases are defined in ``docs/mvp/EVAL_CASES.md``. Most of their behaviour
is already covered by unit tests of the provider and the service; these tests
add only what was missing: the same failures observed through
``POST /api/v2/questions`` with the real ``OpenAIAnswerProvider`` bound to a
scripted transport (no network, no paid call).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from fastapi.testclient import TestClient

from backend import test_openai_provider as base
from sciscope.api.app import create_app
from sciscope.embedding.openai_client import (
    TransportResponse,
    TransportTimeout,
)
from sciscope.question_service.contracts import (
    ComponentMetadata,
    QuestionMetadata,
    RetrievalOutcome,
)

REQUEST = {
    "workflow": "research_question",
    "question": base.QUESTION,
    "request_id": "eval-req-001",
}
RETRIEVAL_METADATA = ComponentMetadata(
    configured_origin="real", executed=True, is_test_data=False
)


@dataclass
class CountingRetrieval:
    """Return fixed real-looking evidence and count the calls."""

    calls: int = 0
    outcome: RetrievalOutcome = field(
        default_factory=lambda: RetrievalOutcome(
            evidence=base.EVIDENCE,
            corpus=base.CORPUS,
            metadata=RETRIEVAL_METADATA,
        )
    )

    def retrieve(self, question: str, request_id: str) -> RetrievalOutcome:
        """Count the call and return the fixed outcome."""
        del question, request_id
        self.calls += 1
        return self.outcome


def _client(
    script: list[TransportResponse | Exception],
) -> tuple[TestClient, CountingRetrieval, base.ScriptedTransport, base.Clock]:
    """Build the v2 app around the real provider and a scripted transport."""
    instance, transport, clock = base.provider(script)
    retrieval = CountingRetrieval()
    app = create_app(
        retrieval=retrieval,
        provider=instance,
        v2_metadata=QuestionMetadata(
            retrieval=ComponentMetadata("real", False, False),
            answer_provider=ComponentMetadata("real", False, False),
        ),
        request_id_factory=lambda: "generated-eval-id",
    )
    return (
        TestClient(app, raise_server_exceptions=False),
        retrieval,
        (transport),
        clock,
    )


# EV-11 (and the request-field part of EV-14 d): invalid API requests.


@pytest.mark.parametrize(
    "extra",
    [
        {"filters": {"journals": ["PLOS ONE"]}},
        {"top_k": 100},
        {"mode": "dense"},
        {"conversation_id": "previous-flow-1"},
    ],
    ids=("filters", "top_k", "mode", "conversation-id"),
)
def test_ev11_fields_that_would_widen_scope_are_rejected(
    extra: dict[str, object],
) -> None:
    """Retrieval settings and continuation fields never reach the services."""
    client, retrieval, transport, _ = _client([])

    response = client.post("/api/v2/questions", json={**REQUEST, **extra})

    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "invalid_request",
        "message": response.json()["error"]["message"],
        "retryable": False,
    }
    assert retrieval.calls == 0
    assert transport.calls == []


@pytest.mark.parametrize(
    "payload",
    [
        {**REQUEST, "question": "x" * 2001},
        {"workflow": "research_question"},
        {**REQUEST, "question": 5},
        {**REQUEST, "request_id": "has space"},
    ],
    ids=("question-too-long", "question-missing", "question-type", "bad-id"),
)
def test_ev11_invalid_values_get_a_sanitized_422(
    payload: dict[str, object],
) -> None:
    """Invalid values give invalid_request without echoing the input."""
    client, retrieval, transport, _ = _client([])

    response = client.post("/api/v2/questions", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert response.json()["error"]["retryable"] is False
    assert "xxxxxxxxxx" not in response.text
    assert "has space" not in response.text
    assert retrieval.calls == 0
    assert transport.calls == []


# EV-12: invalid structured model output fails closed over HTTP.


@pytest.mark.parametrize(
    "model_response",
    [
        base.completion("{not json"),
        base.completion({**base.INSUFFICIENT, "extra": 1}),
        base.completion(base.INSUFFICIENT, finish_reason="length"),
        base.completion(
            base.INSUFFICIENT, refusal="Private refusal text from the model."
        ),
    ],
    ids=("not-json", "extra-key", "truncated", "refusal"),
)
def test_ev12_invalid_model_output_is_a_contract_failure(
    model_response: TransportResponse,
) -> None:
    """One attempt, HTTP 500, no model or passage text in the body."""
    client, retrieval, transport, _ = _client([model_response])

    response = client.post("/api/v2/questions", json=REQUEST)

    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "response_contract_failure"
    assert error["retryable"] is False
    assert len(transport.calls) == 1
    assert retrieval.calls == 1
    assert "Private refusal text" not in response.text
    assert "First passage about longevity" not in response.text


# EV-13: a cited source that was not supplied is never returned.


def test_ev13_unsupplied_citation_twice_is_a_contract_failure() -> None:
    """Retry once with the same prompt, then fail without the answer text."""
    invented = base.answered(("Invented fact.", ["chunk-zzz"]))
    client, _, transport, _ = _client(
        [base.completion(invented), base.completion(invented)]
    )

    response = client.post("/api/v2/questions", json=REQUEST)

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "response_contract_failure"
    assert len(transport.calls) == 2
    assert transport.calls[0].payload == transport.calls[1].payload
    assert "Invented fact." not in response.text
    assert "chunk-zzz" not in response.text


def test_ev13_grounded_second_attempt_cites_only_supplied_ids() -> None:
    """A grounded retry is answered and cites only supplied chunk ids."""
    client, _, transport, _ = _client(
        [
            base.completion(base.answered(("Invented.", ["chunk-zzz"]))),
            base.completion(base.answered(("Real.", ["chunk-a"]))),
        ]
    )

    response = client.post("/api/v2/questions", json=REQUEST)

    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "answered"
    supplied = {item["chunk_id"] for item in body["evidence"]}
    cited = {c for claim in body["claims"] for c in claim["citation_chunk_ids"]}
    assert cited == {"chunk-a"} <= supplied
    assert len(transport.calls) == 2


# EV-15: timeout and AI-service rate limit through HTTP.


def test_ev15_timeout_is_504_without_retry() -> None:
    """A transport timeout maps to dependency_timeout, retryable."""
    client, _, transport, clock = _client([TransportTimeout()])

    response = client.post("/api/v2/questions", json=REQUEST)

    assert response.status_code == 504
    assert response.json()["error"] == {
        "code": "dependency_timeout",
        "message": "The requested dependency timed out.",
        "retryable": True,
    }
    assert len(transport.calls) == 1
    assert clock.sleeps == []


def test_ev15_rate_limit_retries_twice_then_503() -> None:
    """429 rate limit: two backoff retries, then provider_unavailable."""
    limited = base.error(429, code="rate_limit_exceeded")
    client, _, transport, clock = _client([limited, limited, limited])

    response = client.post("/api/v2/questions", json=REQUEST)

    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "provider_unavailable"
    assert error["retryable"] is True
    assert len(transport.calls) == 3
    assert clock.sleeps == [1.0, 2.0]
    assert base.FAKE_KEY not in response.text
    assert "rate_limit_exceeded" not in response.text


def test_ev15_insufficient_quota_is_not_retried() -> None:
    """429 insufficient_quota is permanent: one call, then 503."""
    client, _, transport, clock = _client(
        [base.error(429, code="insufficient_quota", type="insufficient_quota")]
    )

    response = client.post("/api/v2/questions", json=REQUEST)

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "provider_unavailable"
    assert len(transport.calls) == 1
    assert clock.sleeps == []
