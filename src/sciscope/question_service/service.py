"""Synchronous orchestration for Feature 011 fake question outcomes."""

from dataclasses import dataclass

from sciscope.question_service.contracts import (
    AnswerProvider,
    Claim,
    CorpusProvenance,
    Evidence,
    MockMetadata,
    ProviderOutcomeStatus,
    RetrievalService,
)
from sciscope.question_service.validation import (
    validate_answered_outcome,
    validate_insufficient_evidence_outcome,
    validate_no_results_outcome,
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
                metadata=retrieval_outcome.metadata,
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
                metadata=retrieval_outcome.metadata,
            )

        validate_insufficient_evidence_outcome(
            retrieval_outcome, provider_outcome
        )
        return InsufficientEvidenceQuestionOutcome(
            request_id=request_id,
            evidence=retrieval_outcome.evidence,
            corpus=retrieval_outcome.corpus,
            metadata=retrieval_outcome.metadata,
        )
