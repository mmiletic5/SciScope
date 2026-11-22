"""Public, import-safe retrieval-service boundary."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Literal, Protocol, cast

from sciscope.retrieval.contracts import (
    Author,
    CorpusIdentity,
    EmbeddingConfig,
    NormalizedType,
    PaperMetadata,
    RetrievalFilters,
    RetrievalMetadata,
    RetrievalMode,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
    RetrievalScore,
)
from sciscope.retrieval.errors import (
    PUBLIC_MESSAGES,
    RetrievalErrorCode,
    RetrievalException,
)


class QueryEmbedder(Protocol):
    """Produces one query vector for a supplied immutable configuration."""

    def embed_query(
        self, text: str, *, config: EmbeddingConfig
    ) -> Sequence[float]:
        """Return the embedding vector for one query."""


class _RetrievalExecutor(Protocol):
    """Internal structural seam used by the public service facade."""

    def retrieve(self, request: RetrievalRequest) -> object:
        """Execute one validated public retrieval request."""


class _PrivateCore(Protocol):
    """Minimal private-core seam required by the composition adapter."""

    def retrieve(self, value: dict[str, object]) -> object:
        """Execute one validated private retrieval request."""


def _private_request_value(request: RetrievalRequest) -> dict[str, object]:
    """Convert canonical public request values to the core's raw boundary."""
    value: dict[str, object] = {
        "contract_version": request.contract_version,
        "request_id": request.request_id,
        "query_text": request.query_text,
        "mode": request.mode,
        "top_k": request.top_k,
    }
    if request.filters is not None:
        filters = {
            name: filter_value
            for name, filter_value in (
                (
                    "publication_year_from",
                    request.filters.publication_year_from,
                ),
                ("publication_year_to", request.filters.publication_year_to),
                ("normalized_types", request.filters.normalized_types),
                ("journals", request.filters.journals),
                ("languages", request.filters.languages),
                ("dois", request.filters.dois),
            )
            if filter_value is not None
        }
        if filters:
            value["filters"] = filters
    if (
        request.ranking is not None
        and request.ranking.candidate_pool_size is not None
    ):
        value["ranking"] = {
            "candidate_pool_size": request.ranking.candidate_pool_size
        }
    return value


class _PrivateCoreExecutor:
    """Adapt canonical public requests to an injected private retrieval core."""

    def __init__(self, core: _PrivateCore) -> None:
        """Store the core without executing retrieval or opening resources."""
        self._core = core

    def retrieve(self, request: RetrievalRequest) -> object:
        """Execute the core once and leave its response unchanged."""
        return self._core.retrieve(_private_request_value(request))


class _PrivateEmbedderBridge:
    """Adapt the public query-embedder contract to the private core contract."""

    def __init__(self, embedder: QueryEmbedder) -> None:
        """Store the public embedder without creating a provider client."""
        self._embedder = embedder

    def embed_query(self, text: str, *, config: object) -> Sequence[float]:
        """Bridge one private configuration to its public immutable equivalent.

        Returns:
            The public embedder's unmodified vector.
        """
        from sciscope.retrieval._core import _EmbeddingConfig

        if not isinstance(config, _EmbeddingConfig):
            raise TypeError("Unsupported private embedding configuration")
        return self._embedder.embed_query(
            text,
            config=EmbeddingConfig(
                provider=config.provider,
                model=config.model,
                dimensions=config.dimensions,
                query_prefix=config.query_prefix,
            ),
        )


def _compose_private_executor(
    *,
    engine: object,
    embedder: QueryEmbedder | None,
    reranker: object | None = None,
) -> _PrivateCoreExecutor:
    """Lazily construct an internal executor without exposing private types."""
    from sciscope.retrieval._core import _RetrievalCore

    private_embedder = (
        _PrivateEmbedderBridge(embedder) if embedder is not None else None
    )
    core = _RetrievalCore(
        cast(Any, engine), private_embedder, reranker=cast(Any, reranker)
    )
    return _PrivateCoreExecutor(core)


def _public_exception(
    code: RetrievalErrorCode,
    *,
    request_id: str | None,
    retryable: bool,
) -> RetrievalException:
    """Create a fresh exception containing only contract-approved data."""
    return RetrievalException(
        code=code,
        request_id=request_id,
        retryable=retryable,
        public_message=PUBLIC_MESSAGES[code],
    )


def _map_private_response(value: object) -> RetrievalResponse:
    """Map a private core response to immutable public contract values.

    Private imports occur only after retrieval execution, preserving import
    isolation for consumers that only import the public package.
    """
    from sciscope.retrieval._core import _Response

    if not isinstance(value, _Response):
        raise TypeError("Unsupported retrieval executor response")

    filters = RetrievalFilters(
        publication_year_from=value.applied_filters.publication_year_from,
        publication_year_to=value.applied_filters.publication_year_to,
        normalized_types=value.applied_filters.normalized_types,
        journals=value.applied_filters.journals,
        languages=value.applied_filters.languages,
        dois=value.applied_filters.dois,
    )
    embedding = (
        EmbeddingConfig(
            provider=value.embedding.provider,
            model=value.embedding.model,
            dimensions=value.embedding.dimensions,
            query_prefix=value.embedding.query_prefix,
        )
        if value.embedding is not None
        else None
    )
    return RetrievalResponse(
        contract_version=value.contract_version,
        request_id=value.request_id,
        corpus=CorpusIdentity(
            delivery_digest=value.corpus.delivery_digest,
            source_contract_version=value.corpus.source_contract_version,
            corpus_version=value.corpus.corpus_version,
        ),
        embedding=embedding,
        retrieval=RetrievalMetadata(
            mode=cast(RetrievalMode, value.mode),
            top_k=value.top_k,
            candidate_pool_size=value.candidate_pool_size,
            applied_filters=filters,
            rrf_constant=value.rrf_constant,
        ),
        results=tuple(_map_private_result(result) for result in value.results),
        warnings=cast(tuple[Literal["EMPTY_RESULT"], ...], value.warnings),
    )


def _map_private_result(value: object) -> RetrievalResult:
    """Map one exact private hit without rewriting source or score values."""
    from sciscope.retrieval._core import _Hit

    if not isinstance(value, _Hit):
        raise TypeError("Unsupported retrieval result")
    paper = value.paper
    authors = tuple(
        Author(surname=author["surname"], given_names=author["given_names"])
        for author in paper["authors"]
    )
    return RetrievalResult(
        rank=value.rank,
        chunk_id=value.chunk_id,
        text=value.text,
        doi=value.doi,
        source_locator=value.source_locator,
        section_id=value.section_id,
        section_path=tuple(value.section_path),
        normalized_type=cast(NormalizedType, value.normalized_type),
        paper=PaperMetadata(
            title=paper["title"],
            authors=authors,
            journal=paper["journal"],
            publication_year=paper["publication_year"],
            language=paper["language"],
            license=paper["license"],
            source_url=paper["source_url"],
        ),
        scores=RetrievalScore(
            dense_similarity=value.scores.dense_similarity,
            dense_rank=value.scores.dense_rank,
            lexical_score=value.scores.lexical_score,
            lexical_rank=value.scores.lexical_rank,
            fusion_score=value.scores.fusion_score,
        ),
    )


class RetrievalService:
    """Driver-independent public facade over an injected retrieval executor."""

    def __init__(self, *, executor: _RetrievalExecutor) -> None:
        """Store the executor without opening resources or executing retrieval.

        Args:
            executor: Driver-independent dependency that executes public
                requests.
        """
        self._executor = executor

    def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        """Execute one request and return only public DTOs or public errors.

        Args:
            request: Immutable, validated public retrieval request.

        Returns:
            The executor's public response or a mapped private-core response.

        Raises:
            RetrievalException: For sanitized retrieval failures.
        """
        try:
            value: object = self._executor.retrieve(request)
            if isinstance(value, RetrievalResponse):
                return value
            return _map_private_response(value)
        except RetrievalException as error:
            from sciscope.retrieval._errors import RetrievalFailure

            if not isinstance(error, RetrievalFailure):
                raise
            raise _public_exception(
                error.code,
                request_id=error.request_id,
                retryable=error.retryable,
            ) from None
        except Exception:
            raise _public_exception(
                RetrievalErrorCode.RETRIEVAL_INTERNAL_ERROR,
                request_id=request.request_id,
                retryable=False,
            ) from None
