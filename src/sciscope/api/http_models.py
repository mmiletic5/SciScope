"""Closed Pydantic models for the Feature 011 public HTTP contract."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

ApiVersion = Literal["v1"]
Workflow = Literal["research_question"]
RequestStatus = Literal["answered", "no_results", "insufficient_evidence"]
ErrorCode = Literal[
    "invalid_request",
    "retrieval_unavailable",
    "provider_unavailable",
    "dependency_timeout",
    "response_contract_failure",
    "internal_error",
]

NonEmptyString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
QuestionString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=2000),
]
RequestId = Annotated[
    str,
    StringConstraints(pattern=r"^[A-Za-z0-9._:-]{1,128}$"),
]


class _ClosedModel(BaseModel):
    """Base model that rejects unknown fields and coercion."""

    model_config = ConfigDict(extra="forbid", strict=True)


class QuestionRequest(_ClosedModel):
    """Closed request body for the supported question workflow."""

    workflow: Workflow
    question: QuestionString
    request_id: RequestId | None = None


class MockMetadata(_ClosedModel):
    """Marks every Feature 011 response as synthetic test data."""

    is_mock: Literal[True]
    is_test_data: Literal[True]


class CorpusProvenance(_ClosedModel):
    """Identifies the synthetic corpus independently from response evidence."""

    delivery_digest: NonEmptyString
    source_contract_version: NonEmptyString
    corpus_version: NonEmptyString


class Evidence(_ClosedModel):
    """Carries response-local synthetic source material and its identity."""

    chunk_id: NonEmptyString
    doi: NonEmptyString
    source_locator: NonEmptyString
    passage: NonEmptyString
    paper_title: NonEmptyString


class Claim(_ClosedModel):
    """Represents a synthetic answer claim and its cited chunk identities."""

    claim_id: NonEmptyString
    text: NonEmptyString
    citation_chunk_ids: list[NonEmptyString] = Field(min_length=1)


class _SuccessResponse(_ClosedModel):
    """Shared required fields for every successful question response."""

    api_version: ApiVersion
    request_id: RequestId
    workflow: Workflow
    claims: list[Claim]
    evidence: list[Evidence]
    corpus: CorpusProvenance
    metadata: MockMetadata


class AnsweredResponse(_SuccessResponse):
    """Successful synthetic answer response."""

    status: Literal["answered"]
    answer: NonEmptyString


class NoResultsResponse(_SuccessResponse):
    """Successful synthetic response for an empty retrieval result."""

    status: Literal["no_results"]
    answer: None


class InsufficientEvidenceResponse(_SuccessResponse):
    """Successful synthetic response when evidence is insufficient to answer."""

    status: Literal["insufficient_evidence"]
    answer: None


SuccessResponse = Annotated[
    AnsweredResponse | NoResultsResponse | InsufficientEvidenceResponse,
    Field(discriminator="status"),
]


class ErrorDetail(_ClosedModel):
    """Sanitized stable error information for a failed request."""

    code: ErrorCode
    message: NonEmptyString
    retryable: bool


class ErrorResponse(_ClosedModel):
    """Closed versioned public error envelope."""

    api_version: ApiVersion
    request_id: RequestId
    error: ErrorDetail
    metadata: MockMetadata
