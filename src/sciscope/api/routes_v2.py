"""Feature 012 route and mapping helpers for the separate v2 contract."""

from collections.abc import Callable
from typing import cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from sciscope.api.http_models import Claim, CorpusProvenance, Evidence
from sciscope.api.http_models_v2 import (
    AnsweredResponseV2,
    ComponentMetadataV2,
    ErrorDetailV2,
    ErrorResponseV2,
    InsufficientEvidenceResponseV2,
    NoResultsResponseV2,
    QuestionMetadataV2,
    QuestionRequestV2,
    SuccessResponseV2,
)
from sciscope.question_service.contracts import (
    AnswerProvider,
    ComponentMetadata,
    ProviderOutcome,
    QuestionMetadata,
    RetrievalOutcome,
    RetrievalService,
)
from sciscope.question_service.service import (
    AnsweredQuestionOutcome,
    InsufficientEvidenceQuestionOutcome,
    NoResultsQuestionOutcome,
    QuestionOutcome,
    QuestionService,
)


class _TrackedRetrieval:
    """Record an actual retrieval invocation without changing behavior."""

    def __init__(self, dependency: RetrievalService, request: Request) -> None:
        self._dependency = dependency
        self._request = request

    def retrieve(self, question: str, request_id: str) -> RetrievalOutcome:
        """Record invocation before delegating to the injected retrieval."""
        self._request.state.v2_retrieval_executed = True
        return self._dependency.retrieve(question, request_id)


class _TrackedProvider:
    """Record an actual provider invocation without changing behavior."""

    def __init__(self, dependency: AnswerProvider, request: Request) -> None:
        self._dependency = dependency
        self._request = request

    def answer(
        self,
        question: str,
        evidence: tuple[object, ...],
        corpus: object,
        request_id: str,
    ) -> ProviderOutcome:
        """Record invocation before delegating to the injected provider."""
        self._request.state.v2_answer_provider_executed = True
        return self._dependency.answer(
            question,
            evidence,  # type: ignore[arg-type]
            corpus,  # type: ignore[arg-type]
            request_id,
        )


def install_question_v2_route(
    app: FastAPI,
    *,
    request_id_factory: Callable[[], str],
) -> None:
    """Install the explicitly configured versioned question route.

    Args:
        app: Application storing explicit dependencies and v2 metadata config.
        request_id_factory: Supplies an ID when a valid caller ID is absent.
    """

    @app.post("/api/v2/questions", response_model=SuccessResponseV2)
    def ask_question_v2(
        request: QuestionRequestV2,
        fastapi_request: Request,
    ) -> SuccessResponseV2:
        """Serve a validated v2 question outcome using injected dependencies."""
        dependencies = app.state.dependencies
        request_id = request.request_id or request_id_factory()
        fastapi_request.state.request_id = request_id
        fastapi_request.state.v2_retrieval_executed = False
        fastapi_request.state.v2_answer_provider_executed = False
        service = QuestionService(
            retrieval=_TrackedRetrieval(
                cast(RetrievalService, dependencies.retrieval), fastapi_request
            ),
            provider=_TrackedProvider(
                cast(AnswerProvider, dependencies.provider), fastapi_request
            ),
        )
        outcome = service.answer(request.question, request_id)
        return _to_http_response_v2(outcome)


def is_v2_request(request: Request) -> bool:
    """Return whether a request belongs to the versioned route."""
    return request.url.path == "/api/v2/questions"


def failure_metadata(
    request: Request,
    *,
    retrieval_executed: bool,
    answer_provider_executed: bool,
) -> QuestionMetadataV2 | None:
    """Build execution metadata from explicitly injected v2 configuration.

    Args:
        request: Current route request containing application dependencies.
        retrieval_executed: Whether the retrieval call was attempted.
        answer_provider_executed: Whether the provider call was attempted.

    Returns:
        Metadata for a known execution state, or None before dependencies run.
    """
    configured = getattr(request.app.state.dependencies, "v2_metadata", None)
    if type(configured) is not QuestionMetadata:
        return None
    return QuestionMetadataV2(
        retrieval=_component_metadata(
            configured.retrieval, executed=retrieval_executed
        ),
        answer_provider=_component_metadata(
            configured.answer_provider,
            executed=answer_provider_executed,
        ),
    )


def error_response_v2(
    *,
    status_code: int,
    code: str,
    message: str,
    retryable: bool,
    request_id: str,
    metadata: QuestionMetadataV2 | None,
) -> JSONResponse:
    """Return one closed sanitized v2 error response."""
    response = ErrorResponseV2(
        api_version="v2",
        request_id=request_id,
        error=ErrorDetailV2(
            code=code,  # type: ignore[arg-type]
            message=message,
            retryable=retryable,
        ),
        metadata=metadata,
    )
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(exclude_none=True),
    )


def _to_http_response_v2(outcome: QuestionOutcome) -> SuccessResponseV2:
    """Map a validated internal outcome to the separately closed v2 model."""
    metadata_value = cast(QuestionMetadata, outcome.metadata)
    if type(metadata_value) is not QuestionMetadata:
        raise TypeError("v2 requires complete question component metadata")
    metadata = _question_metadata(metadata_value)
    if isinstance(outcome, AnsweredQuestionOutcome):
        return AnsweredResponseV2(
            api_version="v2",
            request_id=outcome.request_id,
            workflow="research_question",
            status="answered",
            answer=outcome.answer,
            claims=[_claim(value) for value in outcome.claims],
            evidence=[_evidence(value) for value in outcome.evidence],
            corpus=_corpus(outcome.corpus),
            metadata=metadata,
        )
    if isinstance(outcome, NoResultsQuestionOutcome):
        return NoResultsResponseV2(
            api_version="v2",
            request_id=outcome.request_id,
            workflow="research_question",
            status="no_results",
            answer=None,
            claims=[],
            evidence=[],
            corpus=_corpus(outcome.corpus),
            metadata=metadata,
        )
    assert isinstance(outcome, InsufficientEvidenceQuestionOutcome)
    return InsufficientEvidenceResponseV2(
        api_version="v2",
        request_id=outcome.request_id,
        workflow="research_question",
        status="insufficient_evidence",
        answer=None,
        claims=[],
        evidence=[_evidence(value) for value in outcome.evidence],
        corpus=_corpus(outcome.corpus),
        metadata=metadata,
    )


def _component_metadata(
    metadata: ComponentMetadata,
    *,
    executed: bool,
) -> ComponentMetadataV2:
    """Map configuration and explicit execution state without inference."""
    return ComponentMetadataV2(
        configured_origin=metadata.configured_origin,
        executed=executed,
        is_test_data=metadata.is_test_data,
    )


def _question_metadata(metadata: QuestionMetadata) -> QuestionMetadataV2:
    """Map already validated internal component metadata."""
    return QuestionMetadataV2(
        retrieval=_component_metadata(
            metadata.retrieval, executed=metadata.retrieval.executed
        ),
        answer_provider=_component_metadata(
            metadata.answer_provider,
            executed=metadata.answer_provider.executed,
        ),
    )


def _evidence(value: object) -> Evidence:
    """Map validated internal evidence without modifying provenance values."""
    return Evidence(
        chunk_id=value.chunk_id,  # type: ignore[attr-defined]
        doi=value.doi,  # type: ignore[attr-defined]
        source_locator=value.source_locator,  # type: ignore[attr-defined]
        passage=value.passage,  # type: ignore[attr-defined]
        paper_title=value.paper_title,  # type: ignore[attr-defined]
    )


def _corpus(value: object) -> CorpusProvenance:
    """Map validated internal corpus identity exactly."""
    return CorpusProvenance(
        delivery_digest=value.delivery_digest,  # type: ignore[attr-defined]
        source_contract_version=value.source_contract_version,  # type: ignore[attr-defined]
        corpus_version=value.corpus_version,  # type: ignore[attr-defined]
    )


def _claim(value: object) -> Claim:
    """Map a validated response-local claim exactly."""
    return Claim(
        claim_id=value.claim_id,  # type: ignore[attr-defined]
        text=value.text,  # type: ignore[attr-defined]
        citation_chunk_ids=list(value.citation_chunk_ids),  # type: ignore[attr-defined]
    )
