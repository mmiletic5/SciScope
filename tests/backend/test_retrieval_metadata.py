"""RED behavior tests for T012-B internal component metadata contracts."""

from dataclasses import dataclass, field, replace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from sciscope.api.app import create_app
from sciscope.question_service import contracts
from sciscope.question_service.contracts import (
    DependencyFailure,
    DependencyFailureCode,
    ProviderOutcome,
    QuestionMetadata,
    RetrievalOutcome,
)
from sciscope.question_service.fakes import FakeAnswerProvider, FakeRetrieval
from sciscope.question_service.service import (
    AnsweredQuestionOutcome,
    NoResultsQuestionOutcome,
    QuestionService,
)
from sciscope.question_service.validation import (
    ResponseContractFailure,
    validate_question_metadata,
)

_MISSING_COMPONENT = "T012-B ComponentMetadata is not implemented"
_MISSING_QUESTION_METADATA = "T012-B QuestionMetadata is not implemented"
_MISSING_VALIDATOR = "T012-B metadata validation is not implemented"


@dataclass
class _FixedRetrieval:
    """Return a configured outcome or failure and record each invocation."""

    outcome: RetrievalOutcome | None = None
    failure: DependencyFailure | None = None
    calls: list[tuple[str, str]] = field(default_factory=list)

    def retrieve(self, question: str, request_id: str) -> RetrievalOutcome:
        self.calls.append((question, request_id))
        if self.failure is not None:
            raise self.failure
        assert self.outcome is not None
        return self.outcome


@dataclass
class _FixedProvider:
    """Return a configured outcome or failure and record each invocation."""

    outcome: ProviderOutcome | None = None
    failure: DependencyFailure | None = None
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
        if self.failure is not None:
            raise self.failure
        assert self.outcome is not None
        return self.outcome


def _component(
    *,
    configured_origin: str,
    executed: bool,
    is_test_data: bool,
) -> Any:
    """Construct the approved T012-B component-metadata contract.

    The explicit lookup makes the RED failure identify the missing approved
    internal contract instead of an unrelated import or fixture problem.
    """
    component_type = getattr(contracts, "ComponentMetadata", None)
    assert component_type is not None, _MISSING_COMPONENT
    return component_type(
        configured_origin=configured_origin,
        executed=executed,
        is_test_data=is_test_data,
    )


def _metadata(
    *,
    retrieval_origin: str,
    retrieval_executed: bool,
    retrieval_is_test_data: bool,
    provider_origin: str,
    provider_executed: bool,
    provider_is_test_data: bool,
) -> Any:
    """Construct metadata for both independently configured components."""
    metadata_type = getattr(contracts, "QuestionMetadata", None)
    assert metadata_type is not None, _MISSING_QUESTION_METADATA
    return metadata_type(
        retrieval=_component(
            configured_origin=retrieval_origin,
            executed=retrieval_executed,
            is_test_data=retrieval_is_test_data,
        ),
        answer_provider=_component(
            configured_origin=provider_origin,
            executed=provider_executed,
            is_test_data=provider_is_test_data,
        ),
    )


def _validate_metadata(metadata: Any) -> None:
    """Call the approved T012-B metadata validator."""
    validate_question_metadata(metadata)


@pytest.mark.parametrize(
    (
        "retrieval_origin",
        "retrieval_is_test_data",
        "provider_origin",
        "provider_is_test_data",
    ),
    [
        ("synthetic", True, "fake", True),
        ("real", False, "fake", True),
        ("real", False, "real", False),
        ("real", True, "fake", True),
    ],
    ids=(
        "synthetic-retrieval-fake-provider",
        "real-retrieval-fake-provider",
        "real-retrieval-real-provider",
        "isolated-postgresql-test-database",
    ),
)
def test_answered_flow_preserves_component_origins_and_execution(
    retrieval_origin: str,
    retrieval_is_test_data: bool,
    provider_origin: str,
    provider_is_test_data: bool,
) -> None:
    """Represent all configured components when both dependencies run."""
    metadata = _metadata(
        retrieval_origin=retrieval_origin,
        retrieval_executed=True,
        retrieval_is_test_data=retrieval_is_test_data,
        provider_origin=provider_origin,
        provider_executed=True,
        provider_is_test_data=provider_is_test_data,
    )
    retrieval_outcome = replace(
        FakeRetrieval().retrieve("metadata question", "metadata-answered"),
        metadata=metadata,
    )
    provider_outcome = replace(
        FakeAnswerProvider().answer(
            "metadata question",
            retrieval_outcome.evidence,
            retrieval_outcome.corpus,
            "metadata-answered",
        ),
        metadata=metadata.answer_provider,
    )

    outcome = QuestionService(
        _FixedRetrieval(outcome=retrieval_outcome),
        _FixedProvider(outcome=provider_outcome),
    ).answer("metadata question", "metadata-answered")

    assert isinstance(outcome, AnsweredQuestionOutcome)
    assert isinstance(outcome.metadata, QuestionMetadata)
    assert outcome.metadata == metadata
    assert outcome.metadata.retrieval.configured_origin == retrieval_origin
    assert outcome.metadata.retrieval.executed is True
    assert outcome.metadata.retrieval.is_test_data is retrieval_is_test_data
    assert outcome.metadata.answer_provider.configured_origin == provider_origin
    assert outcome.metadata.answer_provider.executed is True
    assert (
        outcome.metadata.answer_provider.is_test_data is provider_is_test_data
    )


def test_empty_retrieval_reports_provider_configuration_without_execution() -> (
    None
):
    """Do not claim provider execution or fabricate output for no-results."""
    metadata = _metadata(
        retrieval_origin="real",
        retrieval_executed=True,
        retrieval_is_test_data=True,
        provider_origin="fake",
        provider_executed=False,
        provider_is_test_data=True,
    )
    retrieval_outcome = replace(
        FakeRetrieval(mode="empty").retrieve(
            "metadata question", "metadata-empty"
        ),
        metadata=metadata,
    )
    provider = _FixedProvider()

    outcome = QuestionService(
        _FixedRetrieval(outcome=retrieval_outcome), provider
    ).answer("metadata question", "metadata-empty")

    assert isinstance(outcome, NoResultsQuestionOutcome)
    assert isinstance(outcome.metadata, QuestionMetadata)
    assert outcome.metadata == metadata
    assert outcome.metadata.answer_provider.configured_origin == "fake"
    assert outcome.metadata.answer_provider.executed is False
    assert outcome.metadata.answer_provider.is_test_data is True
    assert outcome.answer is None
    assert outcome.claims == ()
    assert provider.calls == []


def test_retrieval_failure_skips_provider_before_output_is_created() -> None:
    """Preserve provider configuration without inventing failed-call output."""
    metadata = _metadata(
        retrieval_origin="real",
        retrieval_executed=True,
        retrieval_is_test_data=False,
        provider_origin="fake",
        provider_executed=False,
        provider_is_test_data=True,
    )
    _validate_metadata(metadata)
    provider = _FixedProvider()

    with pytest.raises(DependencyFailure) as caught:
        QuestionService(
            _FixedRetrieval(
                failure=DependencyFailure(
                    DependencyFailureCode.RETRIEVAL_UNAVAILABLE
                )
            ),
            provider,
        ).answer("metadata question", "metadata-retrieval-failure")

    assert caught.value.code is DependencyFailureCode.RETRIEVAL_UNAVAILABLE
    assert metadata.answer_provider.executed is False
    assert provider.calls == []


def test_provider_failure_preserves_attempted_execution_without_answer() -> (
    None
):
    """Record a provider call that fails without fabricating a response."""
    metadata = _metadata(
        retrieval_origin="real",
        retrieval_executed=True,
        retrieval_is_test_data=False,
        provider_origin="real",
        provider_executed=True,
        provider_is_test_data=False,
    )
    retrieval_outcome = replace(
        FakeRetrieval().retrieve(
            "metadata question", "metadata-provider-failure"
        ),
        metadata=metadata,
    )
    provider = _FixedProvider(
        failure=DependencyFailure(DependencyFailureCode.PROVIDER_UNAVAILABLE)
    )

    with pytest.raises(DependencyFailure) as caught:
        QuestionService(
            _FixedRetrieval(outcome=retrieval_outcome), provider
        ).answer("metadata question", "metadata-provider-failure")

    assert caught.value.code is DependencyFailureCode.PROVIDER_UNAVAILABLE
    assert metadata.answer_provider.executed is True
    assert provider.calls == [
        ("metadata question", "metadata-provider-failure")
    ]


@pytest.mark.parametrize(
    "metadata",
    [
        lambda: _metadata(
            retrieval_origin="unknown",
            retrieval_executed=True,
            retrieval_is_test_data=False,
            provider_origin="fake",
            provider_executed=True,
            provider_is_test_data=True,
        ),
        lambda: _metadata(
            retrieval_origin="real",
            retrieval_executed="true",  # type: ignore[arg-type]
            retrieval_is_test_data=False,
            provider_origin="fake",
            provider_executed=True,
            provider_is_test_data=True,
        ),
        lambda: _metadata(
            retrieval_origin="real",
            retrieval_executed=True,
            retrieval_is_test_data=False,
            provider_origin="fake",
            provider_executed=True,
            provider_is_test_data="true",  # type: ignore[arg-type]
        ),
    ],
    ids=("unknown-origin", "non-boolean-executed", "non-boolean-test-data"),
)
def test_invalid_component_metadata_fails_closed(metadata: Any) -> None:
    """Reject invalid origins and flag types rather than coercing them."""
    with pytest.raises(ResponseContractFailure):
        _validate_metadata(metadata())


def test_missing_component_metadata_fails_closed() -> None:
    """Require metadata for both components and reject wrong component types."""
    metadata_type = getattr(contracts, "QuestionMetadata", None)
    assert metadata_type is not None, _MISSING_QUESTION_METADATA
    retrieval = _component(
        configured_origin="real", executed=True, is_test_data=False
    )

    with pytest.raises((ResponseContractFailure, TypeError)):
        _validate_metadata(metadata_type(retrieval=retrieval))
    with pytest.raises(ResponseContractFailure):
        _validate_metadata(
            metadata_type(
                retrieval=retrieval,
                answer_provider="not-component-metadata",
            )
        )


def test_v1_fake_only_response_contract_remains_unchanged() -> None:
    """Keep the accepted fake-only route, metadata, and closed success shape."""
    app = create_app(
        retrieval=FakeRetrieval(),
        provider=FakeAnswerProvider(),
        request_id_factory=lambda: "metadata-v1-request",
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/questions",
            json={
                "workflow": "research_question",
                "question": "metadata regression question",
            },
        )

    assert response.status_code == 200
    assert response.json()["metadata"] == {
        "is_mock": True,
        "is_test_data": True,
    }
    assert set(response.json()) == {
        "api_version",
        "request_id",
        "workflow",
        "status",
        "answer",
        "claims",
        "evidence",
        "corpus",
        "metadata",
    }
    assert "/api/v2/questions" not in {
        path for route in app.routes if (path := getattr(route, "path", None))
    }


def test_v1_fake_only_error_envelope_remains_unchanged() -> None:
    """Keep the accepted fake-only controlled-error metadata and envelope."""
    app = create_app(
        retrieval=FakeRetrieval(mode="unavailable"),
        provider=FakeAnswerProvider(),
        request_id_factory=lambda: "metadata-v1-error",
    )

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/questions",
            json={
                "workflow": "research_question",
                "question": "metadata error regression question",
            },
        )

    assert response.status_code == 503
    assert response.json() == {
        "api_version": "v1",
        "request_id": "metadata-v1-error",
        "error": {
            "code": "retrieval_unavailable",
            "message": "The requested dependency is currently unavailable.",
            "retryable": True,
        },
        "metadata": {"is_mock": True, "is_test_data": True},
    }
