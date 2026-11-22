"""Closed Pydantic models for the proposed Feature 012 v2 HTTP contract."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from sciscope.api.http_models import (
    Claim,
    CorpusProvenance,
    Evidence,
    NonEmptyString,
    QuestionString,
    RequestId,
    Workflow,
)

ApiVersionV2 = Literal["v2"]
RequestStatus = Literal["answered", "no_results", "insufficient_evidence"]
ErrorCode = Literal[
    "invalid_request",
    "retrieval_unavailable",
    "provider_unavailable",
    "dependency_timeout",
    "response_contract_failure",
    "internal_error",
]
ComponentOrigin = Literal["synthetic", "fake", "real"]


class _ClosedModel(BaseModel):
    """Base model that rejects unknown fields and coercion."""

    model_config = ConfigDict(extra="forbid", strict=True)


class QuestionRequestV2(_ClosedModel):
    """Closed request body with server-owned retrieval configuration."""

    workflow: Workflow
    question: QuestionString
    request_id: RequestId | None = None


class ComponentMetadataV2(_ClosedModel):
    """Truthful configuration and execution state for one component."""

    configured_origin: ComponentOrigin
    executed: bool
    is_test_data: bool


class QuestionMetadataV2(_ClosedModel):
    """Separate metadata for retrieval and answer-provider components."""

    retrieval: ComponentMetadataV2
    answer_provider: ComponentMetadataV2


class _SuccessResponseV2(_ClosedModel):
    """Shared fields for closed v2 successful responses."""

    api_version: ApiVersionV2
    request_id: RequestId
    workflow: Workflow
    claims: list[Claim]
    evidence: list[Evidence]
    corpus: CorpusProvenance
    metadata: QuestionMetadataV2


class AnsweredResponseV2(_SuccessResponseV2):
    """Answer generated from valid response-local evidence."""

    status: Literal["answered"]
    answer: NonEmptyString


class NoResultsResponseV2(_SuccessResponseV2):
    """No-result response that preserves corpus identity."""

    status: Literal["no_results"]
    answer: None


class InsufficientEvidenceResponseV2(_SuccessResponseV2):
    """Provider refusal that preserves retrieved evidence."""

    status: Literal["insufficient_evidence"]
    answer: None


SuccessResponseV2 = Annotated[
    AnsweredResponseV2 | NoResultsResponseV2 | InsufficientEvidenceResponseV2,
    Field(discriminator="status"),
]


class ErrorDetailV2(_ClosedModel):
    """Sanitized v2 error details."""

    code: ErrorCode
    message: NonEmptyString
    retryable: bool


class ErrorResponseV2(_ClosedModel):
    """Closed v2 error envelope with metadata when execution is known."""

    api_version: ApiVersionV2
    request_id: RequestId
    error: ErrorDetailV2
    metadata: QuestionMetadataV2 | None = None
