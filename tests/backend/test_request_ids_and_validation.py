"""Behavior tests for Feature 011 request IDs and validation envelopes."""

from collections.abc import Callable, Iterator

from fastapi.testclient import TestClient

from backend.validation_asgi import create_validation_app
from sciscope.question_service.ids import (
    generate_request_id,
    is_valid_request_id,
)


def _request_id_factory(*request_ids: str) -> Callable[[], str]:
    """Return deterministic request IDs for validation-envelope tests."""
    request_id_iterator: Iterator[str] = iter(request_ids)
    return lambda: next(request_id_iterator)


def test_generated_request_ids_match_the_approved_pattern() -> None:
    """Generate opaque IDs that match the public request-ID policy."""
    assert is_valid_request_id("ui-42")
    assert not is_valid_request_id("invalid request ID")
    assert is_valid_request_id(generate_request_id())


def test_valid_caller_request_id_is_preserved_in_a_sanitized_error() -> None:
    """Preserve a valid supplied ID without exposing validation details."""
    app = create_validation_app(
        request_id_factory=_request_id_factory("unused")
    )

    with TestClient(app) as client:
        response = client.post(
            "/__test__/validation",
            json={
                "workflow": "research_question",
                "question": "   ",
                "request_id": "ui-42",
            },
        )

    assert response.status_code == 422
    assert response.json() == {
        "api_version": "v1",
        "request_id": "ui-42",
        "error": {
            "code": "invalid_request",
            "message": (
                "The request does not meet this API version's validation rules."
            ),
            "retryable": False,
        },
        "metadata": {"is_mock": True, "is_test_data": True},
    }


def test_missing_or_invalid_request_ids_receive_generated_error_ids() -> None:
    """Generate safe IDs when validation prevents a supplied ID from use."""
    app = create_validation_app(
        request_id_factory=_request_id_factory(
            "generated-missing", "generated-bad"
        ),
    )

    with TestClient(app) as client:
        missing_id_response = client.post(
            "/__test__/validation",
            json={"workflow": "research_question", "question": "   "},
        )
        invalid_id_response = client.post(
            "/__test__/validation",
            json={
                "workflow": "research_question",
                "question": "Synthetic question",
                "request_id": "invalid request ID",
            },
        )

    assert missing_id_response.status_code == 422
    assert missing_id_response.json()["request_id"] == "generated-missing"
    assert invalid_id_response.status_code == 422
    assert invalid_id_response.json()["request_id"] == "generated-bad"
    assert "invalid request ID" not in invalid_id_response.text


def test_invalid_json_returns_a_sanitized_versioned_error() -> None:
    """Hide parser and framework details for an invalid JSON body."""
    app = create_validation_app(
        request_id_factory=_request_id_factory("generated-json")
    )

    with TestClient(app) as client:
        response = client.post(
            "/__test__/validation",
            content="{not-json",
            headers={"content-type": "application/json"},
        )

    body = response.json()
    assert response.status_code == 422
    assert body["request_id"] == "generated-json"
    assert body["error"]["code"] == "invalid_request"
    assert body["metadata"] == {"is_mock": True, "is_test_data": True}
    assert "{not-json" not in response.text
    assert "json_invalid" not in response.text
    assert "decode" not in response.text.lower()
    assert "detail" not in body


def test_validation_errors_hide_internal_details() -> None:
    """Return no raw body, error locations, or framework validation output."""
    app = create_validation_app(
        request_id_factory=_request_id_factory("generated-safe")
    )
    private_question = "Private question that must not appear in an error"

    with TestClient(app) as client:
        response = client.post(
            "/__test__/validation",
            json={
                "workflow": "unsupported_workflow",
                "question": private_question,
                "filters": {"author": "private"},
            },
        )

    body = response.json()
    assert response.status_code == 422
    assert body["request_id"] == "generated-safe"
    assert private_question not in response.text
    assert "filters" not in response.text
    assert "unsupported_workflow" not in response.text
    assert "author" not in response.text
    assert set(body) == {"api_version", "request_id", "error", "metadata"}
