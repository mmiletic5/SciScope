"""Behavior tests for the Feature 011 deterministic fake dependencies."""

import inspect

import pytest

from sciscope.question_service.contracts import (
    AnswerProvider,
    DependencyFailure,
    DependencyFailureCode,
    ProviderOutcomeStatus,
    RetrievalService,
)
from sciscope.question_service.fakes import FakeAnswerProvider, FakeRetrieval


def test_fakes_are_plain_independent_protocol_implementations() -> None:
    """Fakes satisfy separate plain contracts without framework coupling."""
    retrieval = FakeRetrieval()
    provider = FakeAnswerProvider()

    assert isinstance(retrieval, RetrievalService)
    assert isinstance(provider, AnswerProvider)

    for module in (FakeRetrieval.__module__, FakeAnswerProvider.__module__):
        source = inspect.getsource(__import__(module, fromlist=["*"]))
        assert "fastapi" not in source.lower()
        assert "pydantic" not in source.lower()
        assert "sciscope.retrieval" not in source


def test_equivalent_fake_inputs_are_deterministic_and_synthetic() -> None:
    """Equivalent fake retrieval calls return equal synthetic fixtures."""
    retrieval = FakeRetrieval()

    first = retrieval.retrieve("synthetic test question", "request-001")
    second = retrieval.retrieve("synthetic test question", "request-001")

    assert first == second
    assert first.metadata.is_mock is True
    assert first.metadata.is_test_data is True
    assert len(first.evidence) == 1
    evidence = first.evidence[0]
    assert evidence.chunk_id
    assert evidence.doi
    assert evidence.source_locator
    assert evidence.passage
    assert evidence.paper_title
    assert first.corpus.delivery_digest
    assert first.corpus.source_contract_version
    assert first.corpus.corpus_version


def test_empty_retrieval_keeps_synthetic_corpus_provenance() -> None:
    """An empty fake result retains response-level fixture provenance."""
    outcome = FakeRetrieval(mode="empty").retrieve(
        "synthetic test question", "request-002"
    )

    assert outcome.evidence == ()
    assert outcome.corpus.delivery_digest
    assert outcome.corpus.source_contract_version
    assert outcome.corpus.corpus_version
    assert outcome.metadata.is_mock is True
    assert outcome.metadata.is_test_data is True


def test_provider_fixture_cites_the_supplied_synthetic_evidence() -> None:
    """The fake answer fixture derives citation identities from its input."""
    retrieval_outcome = FakeRetrieval().retrieve(
        "synthetic test question", "request-003"
    )

    outcome = FakeAnswerProvider().answer(
        "synthetic test question",
        retrieval_outcome.evidence,
        retrieval_outcome.corpus,
        "request-003",
    )

    assert outcome.status is ProviderOutcomeStatus.ANSWERED
    assert outcome.answer
    assert outcome.claims
    assert outcome.claims[0].citation_chunk_ids == (
        retrieval_outcome.evidence[0].chunk_id,
    )
    assert outcome.metadata.is_mock is True
    assert outcome.metadata.is_test_data is True


@pytest.mark.parametrize(
    ("fake", "method", "failure_code"),
    [
        (
            FakeRetrieval(mode="unavailable"),
            "retrieve",
            DependencyFailureCode.RETRIEVAL_UNAVAILABLE,
        ),
        (
            FakeRetrieval(mode="timeout"),
            "retrieve",
            DependencyFailureCode.DEPENDENCY_TIMEOUT,
        ),
        (
            FakeAnswerProvider(mode="unavailable"),
            "answer",
            DependencyFailureCode.PROVIDER_UNAVAILABLE,
        ),
        (
            FakeAnswerProvider(mode="timeout"),
            "answer",
            DependencyFailureCode.DEPENDENCY_TIMEOUT,
        ),
    ],
)
def test_fakes_signal_configured_offline_failures(
    fake: FakeRetrieval | FakeAnswerProvider,
    method: str,
    failure_code: DependencyFailureCode,
) -> None:
    """Configured fake failures are explicit and require no live service."""
    retrieval_outcome = FakeRetrieval().retrieve(
        "synthetic test question", "request-004"
    )

    with pytest.raises(DependencyFailure) as caught:
        if method == "retrieve":
            fake.retrieve("synthetic test question", "request-004")
        else:
            fake.answer(
                "synthetic test question",
                retrieval_outcome.evidence,
                retrieval_outcome.corpus,
                "request-004",
            )

    assert caught.value.code is failure_code
