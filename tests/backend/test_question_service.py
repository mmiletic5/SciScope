"""Behavior tests for Feature 011 synchronous question orchestration."""

from dataclasses import dataclass, field, replace

import pytest

from sciscope.question_service.contracts import (
    ProviderOutcome,
    RetrievalOutcome,
)
from sciscope.question_service.fakes import FakeAnswerProvider, FakeRetrieval
from sciscope.question_service.service import (
    AnsweredQuestionOutcome,
    InsufficientEvidenceQuestionOutcome,
    NoResultsQuestionOutcome,
    QuestionService,
)
from sciscope.question_service.validation import ResponseContractFailure


@dataclass
class _SpyRetrieval:
    """Records calls while returning a configured synthetic retrieval result."""

    outcome: RetrievalOutcome
    calls: list[tuple[str, str]] = field(default_factory=list)

    def retrieve(self, question: str, request_id: str) -> RetrievalOutcome:
        self.calls.append((question, request_id))
        return self.outcome


@dataclass
class _SpyProvider:
    """Records calls while returning a configured synthetic provider outcome."""

    outcome: ProviderOutcome
    calls: list[tuple[str, str]] = field(default_factory=list)

    def answer(
        self,
        question: str,
        evidence: tuple[object, ...],
        corpus: object,
        request_id: str,
    ) -> ProviderOutcome:
        del evidence, corpus
        self.calls.append((question, request_id))
        return self.outcome


def test_service_orchestrates_answered_outcome_with_injected_dependencies() -> (
    None
):
    """Return validated synthetic answer data from the supplied dependencies."""
    retrieval_outcome = FakeRetrieval().retrieve(
        "fixture question", "request-1"
    )
    provider_outcome = FakeAnswerProvider().answer(
        "fixture question",
        retrieval_outcome.evidence,
        retrieval_outcome.corpus,
        "request-1",
    )
    retrieval = _SpyRetrieval(retrieval_outcome)
    provider = _SpyProvider(provider_outcome)

    outcome = QuestionService(retrieval, provider).answer(
        "fixture question", "request-1"
    )

    assert isinstance(outcome, AnsweredQuestionOutcome)
    assert outcome.answer == provider_outcome.answer
    assert outcome.claims[0].citation_chunk_ids == ("synthetic-chunk-001",)
    assert outcome.corpus == retrieval_outcome.corpus
    assert outcome.metadata.is_mock is True
    assert retrieval.calls == [("fixture question", "request-1")]
    assert provider.calls == [("fixture question", "request-1")]


def test_service_skips_provider_for_empty_retrieval() -> None:
    """Map empty retrieval to no-results without invoking the provider."""
    retrieval_outcome = FakeRetrieval(mode="empty").retrieve(
        "fixture question", "request-2"
    )
    provider_outcome = FakeAnswerProvider().answer(
        "fixture question",
        FakeRetrieval().retrieve("fixture question", "request-2").evidence,
        retrieval_outcome.corpus,
        "request-2",
    )
    retrieval = _SpyRetrieval(retrieval_outcome)
    provider = _SpyProvider(provider_outcome)

    outcome = QuestionService(retrieval, provider).answer(
        "fixture question", "request-2"
    )

    assert isinstance(outcome, NoResultsQuestionOutcome)
    assert outcome.evidence == ()
    assert outcome.claims == ()
    assert outcome.answer is None
    assert outcome.corpus == retrieval_outcome.corpus
    assert provider.calls == []


def test_service_preserves_evidence_for_insufficient_evidence() -> None:
    """Return provider-declined state with the original retrieval evidence."""
    retrieval_outcome = FakeRetrieval().retrieve(
        "fixture question", "request-3"
    )
    provider_outcome = FakeAnswerProvider(mode="insufficient_evidence").answer(
        "fixture question",
        retrieval_outcome.evidence,
        retrieval_outcome.corpus,
        "request-3",
    )

    outcome = QuestionService(
        _SpyRetrieval(retrieval_outcome), _SpyProvider(provider_outcome)
    ).answer("fixture question", "request-3")

    assert isinstance(outcome, InsufficientEvidenceQuestionOutcome)
    assert outcome.answer is None
    assert outcome.claims == ()
    assert outcome.evidence == retrieval_outcome.evidence
    assert outcome.corpus == retrieval_outcome.corpus


def test_service_runs_output_validation_before_returning_an_answer() -> None:
    """Reject invalid provider output rather than repairing or returning it."""
    retrieval_outcome = FakeRetrieval().retrieve(
        "fixture question", "request-4"
    )
    invalid_provider = replace(
        FakeAnswerProvider().answer(
            "fixture question",
            retrieval_outcome.evidence,
            retrieval_outcome.corpus,
            "request-4",
        ),
        answer="",
    )

    with pytest.raises(ResponseContractFailure):
        QuestionService(
            _SpyRetrieval(retrieval_outcome), _SpyProvider(invalid_provider)
        ).answer("fixture question", "request-4")
