"""Behavior tests for the closed Feature 011 HTTP schemas."""

import pytest
from pydantic import ValidationError

from sciscope.api.http_models import (
    AnsweredResponse,
    Claim,
    CorpusProvenance,
    ErrorDetail,
    ErrorResponse,
    Evidence,
    InsufficientEvidenceResponse,
    MockMetadata,
    NoResultsResponse,
    QuestionRequest,
)


def _evidence() -> Evidence:
    return Evidence(
        chunk_id="fixture-chunk-001",
        doi="10.0000/fixture.001",
        source_locator="Synthetic source locator",
        passage="Synthetic exact fixture passage.",
        paper_title="Synthetic fixture paper",
    )


def _corpus() -> CorpusProvenance:
    return CorpusProvenance(
        delivery_digest="synthetic-fixture-digest",
        source_contract_version="synthetic-fixture-v1",
        corpus_version="synthetic-fixture-v1",
    )


def _metadata() -> MockMetadata:
    return MockMetadata(is_mock=True, is_test_data=True)


def test_question_request_accepts_only_the_approved_workflow() -> None:
    """Accept a trimmed question and a valid optional caller request ID."""
    request = QuestionRequest(
        workflow="research_question",
        question="  Synthetic fixture question?  ",
        request_id="ui-42",
    )

    assert request.workflow == "research_question"
    assert request.question == "Synthetic fixture question?"
    assert request.request_id == "ui-42"


@pytest.mark.parametrize(
    "payload",
    [
        {"workflow": "other", "question": "Synthetic question"},
        {"workflow": "research_question", "question": "   "},
        {"workflow": "research_question", "question": "x" * 2001},
        {"workflow": "research_question", "question": 1},
        {
            "workflow": "research_question",
            "question": "Synthetic question",
            "request_id": "invalid request ID",
        },
        {
            "workflow": "research_question",
            "question": "Synthetic question",
            "filters": {},
        },
        {
            "workflow": "research_question",
            "question": "Synthetic question",
            "provider": "fake",
        },
        {
            "workflow": "research_question",
            "question": "Synthetic question",
            "model": "fixture-model",
        },
    ],
)
def test_question_request_rejects_invalid_or_unsupported_values(
    payload: dict[str, object],
) -> None:
    """Reject invalid request values and all unsupported public fields."""
    with pytest.raises(ValidationError):
        QuestionRequest.model_validate(payload)


def test_answered_response_requires_the_closed_versioned_shape() -> None:
    """Validate a synthetic answered response with its required fields."""
    response = AnsweredResponse(
        api_version="v1",
        request_id="ui-42",
        workflow="research_question",
        status="answered",
        answer="Synthetic answer from the configured fake provider.",
        claims=[
            Claim(
                claim_id="claim-1",
                text="Synthetic claim from the configured fake provider.",
                citation_chunk_ids=["fixture-chunk-001"],
            )
        ],
        evidence=[_evidence()],
        corpus=_corpus(),
        metadata=_metadata(),
    )

    assert response.api_version == "v1"
    assert response.status == "answered"
    assert response.evidence[0].chunk_id == "fixture-chunk-001"
    assert response.corpus.delivery_digest == "synthetic-fixture-digest"
    assert response.metadata.is_mock is True
    assert response.metadata.is_test_data is True


def test_non_answered_response_states_have_the_approved_shapes() -> None:
    """Validate the distinct synthetic no-results and insufficient states."""
    no_results = NoResultsResponse(
        api_version="v1",
        request_id="ui-42",
        workflow="research_question",
        status="no_results",
        answer=None,
        claims=[],
        evidence=[],
        corpus=_corpus(),
        metadata=_metadata(),
    )
    insufficient_evidence = InsufficientEvidenceResponse(
        api_version="v1",
        request_id="ui-42",
        workflow="research_question",
        status="insufficient_evidence",
        answer=None,
        claims=[],
        evidence=[_evidence()],
        corpus=_corpus(),
        metadata=_metadata(),
    )

    assert no_results.status == "no_results"
    assert no_results.answer is None
    assert insufficient_evidence.status == "insufficient_evidence"
    assert insufficient_evidence.answer is None


def test_error_response_requires_the_versioned_sanitized_envelope() -> None:
    """Validate the public error envelope and fixed mock/test metadata."""
    response = ErrorResponse(
        api_version="v1",
        request_id="ui-42",
        error=ErrorDetail(
            code="invalid_request",
            message=(
                "The request does not meet this API version's validation rules."
            ),
            retryable=False,
        ),
        metadata=_metadata(),
    )

    assert response.api_version == "v1"
    assert response.error.code == "invalid_request"
    assert response.error.retryable is False


@pytest.mark.parametrize(
    "model, payload",
    [
        (QuestionRequest, {}),
        (AnsweredResponse, {}),
        (ErrorResponse, {}),
        (
            Evidence,
            {
                "chunk_id": "",
                "doi": "10.0000/fixture.001",
                "source_locator": "locator",
                "passage": "passage",
                "paper_title": "title",
            },
        ),
        (
            CorpusProvenance,
            {
                "delivery_digest": "digest",
                "source_contract_version": "",
                "corpus_version": "version",
            },
        ),
        (
            Claim,
            {
                "claim_id": "claim-1",
                "text": "claim",
                "citation_chunk_ids": [],
            },
        ),
        (MockMetadata, {"is_mock": False, "is_test_data": True}),
        (
            ErrorDetail,
            {
                "code": "unsupported_error",
                "message": "Synthetic message",
                "retryable": False,
            },
        ),
    ],
)
def test_models_reject_missing_blank_or_malformed_fields(
    model: type[object],
    payload: dict[str, object],
) -> None:
    """Reject invalid required-field values across the public contract."""
    with pytest.raises(ValidationError):
        model.model_validate(payload)  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "model, payload",
    [
        (
            AnsweredResponse,
            {
                "api_version": "v1",
                "request_id": "ui-42",
                "workflow": "research_question",
                "status": "answered",
                "answer": "Synthetic answer",
                "claims": [],
                "evidence": [],
                "corpus": _corpus(),
                "metadata": _metadata(),
                "unexpected": "rejected",
            },
        ),
        (
            Evidence,
            {
                "chunk_id": "fixture-chunk-001",
                "doi": "10.0000/fixture.001",
                "source_locator": "locator",
                "passage": "passage",
                "paper_title": "title",
                "unexpected": "rejected",
            },
        ),
    ],
)
def test_response_models_reject_unknown_fields(
    model: type[object],
    payload: dict[str, object],
) -> None:
    """Keep every public response model closed to undocumented fields."""
    with pytest.raises(ValidationError):
        model.model_validate(payload)  # type: ignore[attr-defined]
