"""Closed Pydantic models for the v2 HTTP contract (docs/mvp/API_CONTRACT.md).

``research_question`` keeps its original v2 shape. The three payload
workflows add exactly one payload field to the answered response; the field
is absent (not null) for every other status.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from sciscope.api.http_models import (
    Claim,
    CorpusProvenance,
    Evidence,
    NonEmptyString,
    QuestionString,
    RequestId,
)
from sciscope.question_service.contracts import CONFLICTS_REVIEW_NOTE

ApiVersionV2 = Literal["v2"]
WorkflowV2 = Literal[
    "research_question",
    "evidence_comparison",
    "conflicting_evidence",
    "research_gap",
]
CitationIds = Annotated[list[NonEmptyString], Field(min_length=1)]
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

    workflow: WorkflowV2
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


class CitedItemV2(_ClosedModel):
    """A cited similarity or difference statement."""

    item_id: NonEmptyString
    text: NonEmptyString
    citation_chunk_ids: CitationIds


class ComparisonSubjectV2(_ClosedModel):
    """One compared paper."""

    subject_id: NonEmptyString
    doi: NonEmptyString
    paper_title: NonEmptyString
    summary: NonEmptyString
    citation_chunk_ids: CitationIds


class ComparisonPayloadV2(_ClosedModel):
    """``evidence_comparison`` payload."""

    subjects: list[ComparisonSubjectV2] = Field(min_length=2, max_length=6)
    similarities: list[CitedItemV2]
    differences: list[CitedItemV2]


class ConflictPositionV2(_ClosedModel):
    """One side of a potential difference."""

    position_id: NonEmptyString
    text: NonEmptyString
    citation_chunk_ids: CitationIds


class ConflictItemV2(_ClosedModel):
    """A potential difference flagged for human review."""

    item_id: NonEmptyString
    topic: NonEmptyString
    summary: NonEmptyString
    positions: list[ConflictPositionV2] = Field(min_length=2)


class ConflictsPayloadV2(_ClosedModel):
    """``conflicting_evidence`` payload with the fixed server review note."""

    # mypy rejects a Final name inside Literal; pydantic gets the value.
    review_note: Literal[CONFLICTS_REVIEW_NOTE]  # type: ignore[valid-type]
    items: list[ConflictItemV2] = Field(min_length=1, max_length=5)


class GapItemV2(_ClosedModel):
    """A cited research gap."""

    gap_id: NonEmptyString
    text: NonEmptyString
    citation_chunk_ids: CitationIds


class HypothesisV2(_ClosedModel):
    """A speculative hypothesis; never a finding."""

    hypothesis_id: NonEmptyString
    text: NonEmptyString
    rationale: NonEmptyString
    based_on_gap_ids: list[NonEmptyString] = Field(min_length=1)
    citation_chunk_ids: CitationIds
    is_speculative: Literal[True]


class GapAnalysisPayloadV2(_ClosedModel):
    """``research_gap`` payload."""

    gaps: list[GapItemV2] = Field(min_length=1)
    hypotheses: list[HypothesisV2] = Field(max_length=4)


class _SuccessResponseV2(_ClosedModel):
    """Shared fields for closed v2 successful responses."""

    api_version: ApiVersionV2
    request_id: RequestId
    workflow: WorkflowV2
    claims: list[Claim]
    evidence: list[Evidence]
    corpus: CorpusProvenance
    metadata: QuestionMetadataV2


class AnsweredResponseV2(_SuccessResponseV2):
    """``research_question`` answer from valid response-local evidence."""

    workflow: Literal["research_question"]
    status: Literal["answered"]
    answer: NonEmptyString


class AnsweredComparisonResponseV2(_SuccessResponseV2):
    """``evidence_comparison`` answer; claims are server-derived."""

    workflow: Literal["evidence_comparison"]
    status: Literal["answered"]
    answer: NonEmptyString
    comparison: ComparisonPayloadV2


class AnsweredConflictsResponseV2(_SuccessResponseV2):
    """``conflicting_evidence`` answer; claims are server-derived."""

    workflow: Literal["conflicting_evidence"]
    status: Literal["answered"]
    answer: NonEmptyString
    conflicts: ConflictsPayloadV2


class AnsweredGapAnalysisResponseV2(_SuccessResponseV2):
    """``research_gap`` answer; claims are server-derived."""

    workflow: Literal["research_gap"]
    status: Literal["answered"]
    answer: NonEmptyString
    gap_analysis: GapAnalysisPayloadV2


class NoResultsResponseV2(_SuccessResponseV2):
    """No-result response that preserves corpus identity."""

    status: Literal["no_results"]
    answer: None


class InsufficientEvidenceResponseV2(_SuccessResponseV2):
    """Provider refusal that preserves retrieved evidence."""

    status: Literal["insufficient_evidence"]
    answer: None


AnyAnsweredResponseV2 = Annotated[
    AnsweredResponseV2
    | AnsweredComparisonResponseV2
    | AnsweredConflictsResponseV2
    | AnsweredGapAnalysisResponseV2,
    Field(discriminator="workflow"),
]

SuccessResponseV2 = Annotated[
    AnyAnsweredResponseV2
    | NoResultsResponseV2
    | InsufficientEvidenceResponseV2,
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


class HealthComponent(_ClosedModel):
    """Configured origin of one component; no execution state."""

    configured_origin: ComponentOrigin


class HealthComponents(_ClosedModel):
    """Configured component origins."""

    retrieval: HealthComponent
    answer_provider: HealthComponent


class HealthResponse(_ClosedModel):
    """``GET /api/health`` body; carries no secrets."""

    status: Literal["ok"]
    api_versions: list[NonEmptyString]
    workflows: list[WorkflowV2]
    components: HealthComponents
