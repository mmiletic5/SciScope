"""Adapter from the public retrieval facade to question-service retrieval."""

from __future__ import annotations

from dataclasses import dataclass

from sciscope.question_service.contracts import (
    ComponentMetadata,
    CorpusProvenance,
    Evidence,
    RetrievalOutcome,
)
from sciscope.question_service.validation import ResponseContractFailure
from sciscope.retrieval import (
    CorpusIdentity,
    PaperMetadata,
    RankingOptions,
    RetrievalFilters,
    RetrievalMetadata,
    RetrievalMode,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
    RetrievalService,
)
from sciscope.retrieval.errors import RetrievalException


@dataclass(frozen=True, slots=True)
class RetrievalAdapterSettings:
    """Explicit server-owned configuration for one public retrieval adapter."""

    contract_version: str
    mode: RetrievalMode
    top_k: int
    filters: RetrievalFilters | None
    ranking: RankingOptions | None
    retrieval_metadata: ComponentMetadata

    def __post_init__(self) -> None:
        """Fail closed before the facade is invoked for invalid settings."""
        _validate_component_metadata(self.retrieval_metadata)
        if self.retrieval_metadata.configured_origin != "real":
            raise ResponseContractFailure()
        try:
            RetrievalRequest(
                contract_version=self.contract_version,
                request_id="adapter-settings",
                query_text="adapter settings validation",
                mode=self.mode,
                top_k=self.top_k,
                filters=self.filters,
                ranking=self.ranking,
            )
        except RetrievalException as error:
            raise ResponseContractFailure() from error


class PublicRetrievalAdapter:
    """Adapt one injected public retrieval facade to question-service output."""

    def __init__(
        self,
        *,
        service: RetrievalService,
        settings: RetrievalAdapterSettings,
    ) -> None:
        """Store injected dependencies without initializing resources.

        Args:
            service: Already-composed public retrieval facade.
            settings: Explicit immutable server-owned retrieval configuration.
        """
        self._service = service
        self._settings = settings

    def retrieve(self, question: str, request_id: str) -> RetrievalOutcome:
        """Retrieve and map exact public evidence into the internal protocol.

        Args:
            question: Validated question-service input.
            request_id: Valid question-service correlation ID.

        Returns:
            Exact evidence and corpus provenance with retrieval-only metadata.

        Raises:
            ResponseContractFailure: If the facade response is incompatible.
            RetrievalException: If the injected public facade reports an error.
        """
        request = RetrievalRequest(
            contract_version=self._settings.contract_version,
            request_id=request_id,
            query_text=question,
            mode=self._settings.mode,
            top_k=self._settings.top_k,
            filters=self._settings.filters,
            ranking=self._settings.ranking,
        )
        response = self._service.retrieve(request)
        _validate_response(response, request, self._settings)
        return RetrievalOutcome(
            evidence=tuple(_map_result(result) for result in response.results),
            corpus=_map_corpus(response.corpus),
            metadata=ComponentMetadata(
                configured_origin=self._settings.retrieval_metadata.configured_origin,
                executed=True,
                is_test_data=self._settings.retrieval_metadata.is_test_data,
            ),
        )


def _validate_component_metadata(metadata: object) -> None:
    """Require explicit, truthful retrieval-component configuration."""
    if (
        type(metadata) is not ComponentMetadata
        or metadata.configured_origin not in {"synthetic", "fake", "real"}
        or type(metadata.executed) is not bool
        or type(metadata.is_test_data) is not bool
    ):
        raise ResponseContractFailure()


def _validate_response(
    response: object,
    request: RetrievalRequest,
    settings: RetrievalAdapterSettings,
) -> None:
    """Validate a public response before mapping any partial evidence."""
    if type(response) is not RetrievalResponse:
        raise ResponseContractFailure()
    if (
        response.request_id != request.request_id
        or response.contract_version != settings.contract_version
    ):
        raise ResponseContractFailure()
    _validate_corpus(response.corpus)
    _validate_retrieval_metadata(response.retrieval, settings)
    evidence_ids: set[str] = set()
    for result in response.results:
        _validate_result(result)
        if result.chunk_id in evidence_ids:
            raise ResponseContractFailure()
        evidence_ids.add(result.chunk_id)
    if not response.results and response.warnings != ("EMPTY_RESULT",):
        raise ResponseContractFailure()
    if response.results and response.warnings:
        raise ResponseContractFailure()


def _validate_corpus(corpus: object) -> None:
    """Require complete exact corpus identity before internal mapping."""
    if type(corpus) is not CorpusIdentity or not all(
        _is_nonempty_string(value)
        for value in (
            corpus.delivery_digest,
            corpus.source_contract_version,
            corpus.corpus_version,
        )
    ):
        raise ResponseContractFailure()


def _validate_retrieval_metadata(
    metadata: object, settings: RetrievalAdapterSettings
) -> None:
    """Require the response to describe the explicitly requested retrieval."""
    if (
        type(metadata) is not RetrievalMetadata
        or metadata.mode != settings.mode
        or metadata.top_k != settings.top_k
        or metadata.applied_filters != settings.filters
    ):
        raise ResponseContractFailure()
    candidate_pool_size = (
        settings.ranking.candidate_pool_size
        if settings.ranking is not None
        else None
    )
    if metadata.candidate_pool_size != candidate_pool_size:
        raise ResponseContractFailure()


def _validate_result(result: object) -> None:
    """Require complete public source fields without rewriting their values."""
    if (
        type(result) is not RetrievalResult
        or type(result.paper) is not PaperMetadata
    ):
        raise ResponseContractFailure()
    if not all(
        _is_nonempty_string(value)
        for value in (
            result.chunk_id,
            result.doi,
            result.source_locator,
            result.text,
            result.paper.title,
        )
    ):
        raise ResponseContractFailure()


def _map_result(result: RetrievalResult) -> Evidence:
    """Map one validated public result without changing source values."""
    return Evidence(
        chunk_id=result.chunk_id,
        doi=result.doi,
        source_locator=result.source_locator,
        passage=result.text,
        paper_title=result.paper.title,
    )


def _map_corpus(corpus: CorpusIdentity) -> CorpusProvenance:
    """Map one validated public corpus identity without changing its values."""
    return CorpusProvenance(
        delivery_digest=corpus.delivery_digest,
        source_contract_version=corpus.source_contract_version,
        corpus_version=corpus.corpus_version,
    )


def _is_nonempty_string(value: object) -> bool:
    """Return whether a contract field contains non-whitespace text."""
    return isinstance(value, str) and bool(value.strip())
