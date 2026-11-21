"""Feature 011 HTTP route adapters for successful question outcomes."""

from collections.abc import Callable
from typing import cast

from fastapi import FastAPI

from sciscope.api.http_models import (
    AnsweredResponse,
    Claim,
    CorpusProvenance,
    Evidence,
    InsufficientEvidenceResponse,
    MockMetadata,
    NoResultsResponse,
    QuestionRequest,
    SuccessResponse,
)
from sciscope.question_service.contracts import (
    AnswerProvider,
    RetrievalService,
)
from sciscope.question_service.contracts import (
    Claim as PlainClaim,
)
from sciscope.question_service.contracts import (
    CorpusProvenance as PlainCorpusProvenance,
)
from sciscope.question_service.contracts import (
    Evidence as PlainEvidence,
)
from sciscope.question_service.contracts import (
    MockMetadata as PlainMockMetadata,
)
from sciscope.question_service.service import (
    AnsweredQuestionOutcome,
    InsufficientEvidenceQuestionOutcome,
    NoResultsQuestionOutcome,
    QuestionOutcome,
    QuestionService,
)


def install_question_route(
    app: FastAPI,
    *,
    request_id_factory: Callable[[], str],
) -> None:
    """Install the single Feature 011 question route on an application.

    Args:
        app: Application whose explicit dependencies serve the route.
        request_id_factory: Supplies a request ID when valid input omits one.
    """

    @app.post("/api/v1/questions", response_model=SuccessResponse)
    def ask_question(request: QuestionRequest) -> SuccessResponse:
        """Serve one validated, fake-only research-question outcome."""
        dependencies = app.state.dependencies
        service = QuestionService(
            retrieval=cast(RetrievalService, dependencies.retrieval),
            provider=cast(AnswerProvider, dependencies.provider),
        )
        request_id = request.request_id or request_id_factory()
        outcome = service.answer(request.question, request_id)
        return _to_http_response(outcome)


def _to_http_response(outcome: QuestionOutcome) -> SuccessResponse:
    """Map a validated plain service value to its closed public model."""
    if isinstance(outcome, AnsweredQuestionOutcome):
        return AnsweredResponse(
            api_version="v1",
            request_id=outcome.request_id,
            workflow="research_question",
            status="answered",
            answer=outcome.answer,
            claims=[_to_claim(value) for value in outcome.claims],
            evidence=[_to_evidence(value) for value in outcome.evidence],
            corpus=_to_corpus(outcome.corpus),
            metadata=_to_metadata(outcome.metadata),
        )
    if isinstance(outcome, NoResultsQuestionOutcome):
        return NoResultsResponse(
            api_version="v1",
            request_id=outcome.request_id,
            workflow="research_question",
            status="no_results",
            answer=None,
            claims=[],
            evidence=[_to_evidence(value) for value in outcome.evidence],
            corpus=_to_corpus(outcome.corpus),
            metadata=_to_metadata(outcome.metadata),
        )
    assert isinstance(outcome, InsufficientEvidenceQuestionOutcome)
    return InsufficientEvidenceResponse(
        api_version="v1",
        request_id=outcome.request_id,
        workflow="research_question",
        status="insufficient_evidence",
        answer=None,
        claims=[],
        evidence=[_to_evidence(value) for value in outcome.evidence],
        corpus=_to_corpus(outcome.corpus),
        metadata=_to_metadata(outcome.metadata),
    )


def _to_evidence(value: PlainEvidence) -> Evidence:
    """Map validated plain evidence to its public schema value."""
    return Evidence(
        chunk_id=value.chunk_id,
        doi=value.doi,
        source_locator=value.source_locator,
        passage=value.passage,
        paper_title=value.paper_title,
    )


def _to_corpus(value: PlainCorpusProvenance) -> CorpusProvenance:
    """Map validated plain corpus provenance to its public schema value."""
    return CorpusProvenance(
        delivery_digest=value.delivery_digest,
        source_contract_version=value.source_contract_version,
        corpus_version=value.corpus_version,
    )


def _to_metadata(value: PlainMockMetadata) -> MockMetadata:
    """Map validated plain fake markers to their public schema value."""
    return MockMetadata(
        is_mock=value.is_mock,
        is_test_data=value.is_test_data,
    )


def _to_claim(value: PlainClaim) -> Claim:
    """Map a validated plain claim to its public schema value."""
    return Claim(
        claim_id=value.claim_id,
        text=value.text,
        citation_chunk_ids=list(value.citation_chunk_ids),
    )
