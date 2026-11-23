"""Retrieval query-embedder adapter over an injected passage embedder."""

from __future__ import annotations

from collections.abc import Sequence

from sciscope.embedding.config import EmbeddingConfig, EmbeddingProviderError
from sciscope.embedding.provider import Embedder
from sciscope.retrieval._core import QueryEmbeddingUnavailable
from sciscope.retrieval.contracts import EmbeddingConfig as QueryConfig


class QueryEmbedderConfigMismatch(ValueError):
    """The requested query configuration differs from the wrapped embedder.

    The message is a stable code; it never contains query text or secrets.
    """

    code = "query-embedding-config-mismatch"

    def __init__(self) -> None:
        """Create the stable mismatch failure."""
        super().__init__(self.code)


class OpenAIQueryEmbedder:
    """Embed one retrieval query with exactly the wrapped configuration.

    The retrieval core supplies the corpus's query-embedding identity with
    every call. This adapter refuses to embed when that identity differs from
    the identity of the injected embedder, so a query is never silently
    embedded with another provider, model, dimension, or prefix.

    Transient and provider failures are reported as
    ``QueryEmbeddingUnavailable``, which the retrieval core maps to a
    retryable ``EMBEDDING_UNAVAILABLE`` failure. Any other failure (including
    a configuration mismatch) surfaces as an internal retrieval error.
    """

    def __init__(self, embedder: Embedder, config: EmbeddingConfig) -> None:
        """Bind an embedder and the configuration it was built with.

        Args:
            embedder: Already-constructed embedder, normally an
                ``OpenAIEmbedder`` with an owned transport.
            config: The embedding configuration used to build ``embedder``;
                its query prefix is applied by ``embedder.embed_queries``.

        Raises:
            QueryEmbedderConfigMismatch: If the embedder's declared identity
                differs from ``config``.
        """
        if (
            embedder.provider_id != config.provider
            or embedder.model != config.model
            or embedder.dimensions != config.dimensions
        ):
            raise QueryEmbedderConfigMismatch()
        self._embedder = embedder
        self._config = config

    def __repr__(self) -> str:
        """Describe the adapter by its non-secret embedding identity."""
        return (
            "OpenAIQueryEmbedder("
            f"provider={self._config.provider!r}, "
            f"model={self._config.model!r}, "
            f"dimensions={self._config.dimensions!r})"
        )

    def embed_query(self, text: str, *, config: QueryConfig) -> Sequence[float]:
        """Return one query vector after verifying the requested identity.

        Args:
            text: Validated retrieval query text.
            config: Query-embedding identity required by the active corpus.

        Returns:
            The single vector produced by the wrapped embedder.

        Raises:
            QueryEmbedderConfigMismatch: If ``config`` differs from the
                wrapped configuration.
            QueryEmbeddingUnavailable: If the provider fails or returns an
                invalid response.
        """
        if (
            config.provider != self._config.provider
            or config.model != self._config.model
            or config.dimensions != self._config.dimensions
            or config.query_prefix != self._config.query_prefix
        ):
            raise QueryEmbedderConfigMismatch()
        try:
            result = self._embedder.embed_queries([text])
        except EmbeddingProviderError:
            raise QueryEmbeddingUnavailable() from None
        if len(result.vectors) != 1:
            raise QueryEmbeddingUnavailable()
        return result.vectors[0]
