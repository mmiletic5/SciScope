"""Synchronous orchestration for Feature 011 fake question outcomes."""

from dataclasses import dataclass
from typing import cast

from sciscope.question_service.contracts import (
    DEFAULT_WORKFLOW,
    AnswerProvider,
    Claim,
    ComponentMetadata,
    CorpusProvenance,
    Evidence,
    MockMetadata,
    OutcomeMetadata,
    ProviderOutcomeStatus,
    QuestionMetadata,
    RetrievalService,
    Workflow,
    WorkflowPayload,
    invoke_provider,
)
from sciscope.question_service.validation import (
    ResponseContractFailure,
    validate_answered_outcome,
    validate_insufficient_evidence_outcome,
    validate_no_results_outcome,
    validate_question_metadata,
)
from sciscope.question_service.workflow_validation import (
    is_payload_workflow,
    validate_payload_answer,
)


@dataclass(frozen=True, slots=True)
class AnsweredQuestionOutcome:
    """Validated plain value for an answered question response."""

    request_id: str
    answer: str
    claims: tuple[Claim, ...]
    evidence: tuple[Evidence, ...]
    corpus: CorpusProvenance
    metadata: MockMetadata
    workflow: Workflow = DEFAULT_WORKFLOW
    payload: WorkflowPayload | None = None


@dataclass(frozen=True, slots=True)
class NoResultsQuestionOutcome:
    """Validated plain value for an empty retrieval response."""

    request_id: str
    evidence: tuple[Evidence, ...]
    corpus: CorpusProvenance
    metadata: MockMetadata
    answer: None = None
    claims: tuple[Claim, ...] = ()
    workflow: Workflow = DEFAULT_WORKFLOW


@dataclass(frozen=True, slots=True)
class InsufficientEvidenceQuestionOutcome:
    """Validated plain value for a provider-declined response."""

    request_id: str
    evidence: tuple[Evidence, ...]
    corpus: CorpusProvenance
    metadata: MockMetadata
    answer: None = None
    claims: tuple[Claim, ...] = ()
    workflow: Workflow = DEFAULT_WORKFLOW


QuestionOutcome = (
    AnsweredQuestionOutcome
    | NoResultsQuestionOutcome
    | InsufficientEvidenceQuestionOutcome
)


class QuestionService:
    """Coordinates injected fake dependencies for one valid question request."""

    def __init__(
        self,
        retrieval: RetrievalService,
        provider: AnswerProvider,
    ) -> None:
        """Bind explicitly injected fake dependencies.

        Args:
            retrieval: Dependency supplying synthetic retrieval outcomes.
            provider: Dependency supplying synthetic provider outcomes.
        """
        self._retrieval = retrieval
        self._provider = provider

    def answer(
        self,
        question: str,
        request_id: str,
        workflow: Workflow = DEFAULT_WORKFLOW,
    ) -> QuestionOutcome:
        """Return a validated plain outcome for a valid question request.

        Args:
            question: Validated research question text.
            request_id: Valid request correlation ID.
            workflow: Requested workflow; selects the provider task and the
                payload validation rules.

        Returns:
            One of the three approved successful question outcomes. A payload
            answer that a contract rule marks as insufficient (comparison
            citing fewer than two papers, conflicts without items) becomes
            the insufficient-evidence outcome.

        Raises:
            DependencyFailure: Propagated controlled dependency failure for
                T008 mapping.
            ResponseContractFailure: If fake output violates the approved
                response contract.
        """
        retrieval_outcome = self._retrieval.retrieve(question, request_id)
        if not retrieval_outcome.evidence:
            validate_no_results_outcome(retrieval_outcome)
            return NoResultsQuestionOutcome(
                request_id=request_id,
                evidence=retrieval_outcome.evidence,
                corpus=retrieval_outcome.corpus,
                metadata=cast(
                    MockMetadata,
                    _no_results_metadata(retrieval_outcome.metadata),
                ),
                workflow=workflow,
            )

        provider_outcome = invoke_provider(
            self._provider,
            question,
            retrieval_outcome.evidence,
            retrieval_outcome.corpus,
            request_id,
            workflow,
        )
        if provider_outcome.workflow != workflow:
            raise ResponseContractFailure()
        if provider_outcome.status is ProviderOutcomeStatus.ANSWERED:
            if is_payload_workflow(workflow):
                claims = validate_payload_answer(
                    workflow, retrieval_outcome, provider_outcome
                )
            else:
                validate_answered_outcome(retrieval_outcome, provider_outcome)
                claims = provider_outcome.claims
            if claims is not None:
                assert provider_outcome.answer is not None
                return AnsweredQuestionOutcome(
                    request_id=request_id,
                    answer=provider_outcome.answer,
                    claims=claims,
                    evidence=retrieval_outcome.evidence,
                    corpus=retrieval_outcome.corpus,
                    metadata=cast(
                        MockMetadata,
                        _answered_metadata(
                            retrieval_outcome.metadata,
                            provider_outcome.metadata,
                        ),
                    ),
                    workflow=workflow,
                    payload=provider_outcome.payload,
                )
        else:
            validate_insufficient_evidence_outcome(
                retrieval_outcome, provider_outcome
            )
        return InsufficientEvidenceQuestionOutcome(
            request_id=request_id,
            evidence=retrieval_outcome.evidence,
            corpus=retrieval_outcome.corpus,
            metadata=cast(
                MockMetadata,
                _answered_metadata(
                    retrieval_outcome.metadata, provider_outcome.metadata
                ),
            ),
            workflow=workflow,
        )


def _no_results_metadata(
    metadata: OutcomeMetadata,
) -> MockMetadata | QuestionMetadata:
    """Return validated metadata for a retrieval request with no evidence.

    Empty retrieval has no provider invocation. Component metadata must already
    include that configured provider with ``executed`` set to ``False``.
    """
    if type(metadata) is MockMetadata:
        return metadata
    if type(metadata) is QuestionMetadata:
        validate_question_metadata(metadata)
        if (
            metadata.retrieval.executed is not True
            or metadata.answer_provider.executed is not False
        ):
            raise ResponseContractFailure()
        return metadata
    raise ResponseContractFailure()


def _answered_metadata(
    retrieval_metadata: OutcomeMetadata,
    provider_metadata: OutcomeMetadata,
) -> MockMetadata | QuestionMetadata:
    """Combine the components that were invoked for an answered outcome."""
    if type(retrieval_metadata) is MockMetadata:
        if type(provider_metadata) is not MockMetadata:
            raise ResponseContractFailure()
        return retrieval_metadata
    if type(retrieval_metadata) is ComponentMetadata:
        if type(provider_metadata) is not ComponentMetadata:
            raise ResponseContractFailure()
        metadata = QuestionMetadata(
            retrieval=retrieval_metadata,
            answer_provider=provider_metadata,
        )
    elif type(retrieval_metadata) is QuestionMetadata:
        if type(provider_metadata) is not ComponentMetadata:
            raise ResponseContractFailure()
        if retrieval_metadata.answer_provider != provider_metadata:
            raise ResponseContractFailure()
        metadata = retrieval_metadata
    else:
        raise ResponseContractFailure()
    validate_question_metadata(metadata)
    if (
        metadata.retrieval.executed is not True
        or metadata.answer_provider.executed is not True
    ):
        raise ResponseContractFailure()
    return metadata
