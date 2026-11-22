"""Synchronous orchestration for Feature 011 fake question outcomes."""

from dataclasses import dataclass
from typing import cast

from sciscope.question_service.contracts import (
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
)
from sciscope.question_service.validation import (
    ResponseContractFailure,
    validate_answered_outcome,
    validate_insufficient_evidence_outcome,
    validate_no_results_outcome,
    validate_question_metadata,
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


@dataclass(frozen=True, slots=True)
class NoResultsQuestionOutcome:
    """Validated plain value for an empty retrieval response."""

    request_id: str
    evidence: tuple[Evidence, ...]
    corpus: CorpusProvenance
    metadata: MockMetadata
    answer: None = None
    claims: tuple[Claim, ...] = ()


@dataclass(frozen=True, slots=True)
class InsufficientEvidenceQuestionOutcome:
    """Validated plain value for a provider-declined response."""

    request_id: str
    evidence: tuple[Evidence, ...]
    corpus: CorpusProvenance
    metadata: MockMetadata
    answer: None = None
    claims: tuple[Claim, ...] = ()


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

    def answer(self, question: str, request_id: str) -> QuestionOutcome:
        """Return a validated plain outcome for a valid question request.

        Args:
            question: Validated research question text.
            request_id: Valid request correlation ID.

        Returns:
            One of the three approved successful question outcomes.

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
            )

        provider_outcome = self._provider.answer(
            question,
            retrieval_outcome.evidence,
            retrieval_outcome.corpus,
            request_id,
        )
        if provider_outcome.status is ProviderOutcomeStatus.ANSWERED:
            validate_answered_outcome(retrieval_outcome, provider_outcome)
            assert provider_outcome.answer is not None
            return AnsweredQuestionOutcome(
                request_id=request_id,
                answer=provider_outcome.answer,
                claims=provider_outcome.claims,
                evidence=retrieval_outcome.evidence,
                corpus=retrieval_outcome.corpus,
                metadata=cast(
                    MockMetadata,
                    _answered_metadata(
                        retrieval_outcome.metadata, provider_outcome.metadata
                    ),
                ),
            )

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
