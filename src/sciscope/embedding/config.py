"""Embedding configuration and sanitized public errors."""

from __future__ import annotations

import math
from dataclasses import dataclass

from sciscope.chunking.config import build_embedding_text

EMBEDDING_FORMAT_VERSION = "embedding-set-v1"
CACHE_FORMAT_VERSION = "embedding-cache-v1"
DEFAULT_PROVIDER = "openai"
DEFAULT_MODEL = "text-embedding-3-small"
DEFAULT_DIMENSIONS = 1536
DEFAULT_BASE_URL = "https://api.openai.com"
PRICE_USD_PER_MILLION_TOKENS = 0.02
API_MAX_INPUTS_PER_REQUEST = 2048
API_MAX_TOKENS_PER_REQUEST = 300000


class EmbeddingError(ValueError):
    """An embedding failure represented only by a sanitized public code."""

    def __init__(self, code: str) -> None:
        """Store a stable error code without sensitive context."""
        self.code = code
        super().__init__(code)


class EmbeddingConfigError(EmbeddingError):
    """Embedding configuration is invalid."""


class EmbeddingInputError(EmbeddingError):
    """An embedding input is invalid."""


class EmbeddingProviderError(EmbeddingError):
    """The provider failed or returned an invalid response."""


class EmbeddingCacheError(EmbeddingError):
    """A cache entry is corrupt, optionally identified by its hex key."""

    def __init__(self, code: str, entry_key: str | None = None) -> None:
        """Keep the public code and optional cache key for CLI diagnostics."""
        self.entry_key = entry_key
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class EmbeddingConfig:
    """Provider configuration and bounded sequential request limits."""

    provider: str = DEFAULT_PROVIDER
    model: str = DEFAULT_MODEL
    dimensions: int = DEFAULT_DIMENSIONS
    passage_prefix: str = ""
    query_prefix: str = ""
    max_inputs_per_request: int = 8
    max_tokens_per_request: int = 2048
    max_attempts: int = 3
    request_timeout_seconds: float = 30.0
    initial_backoff_seconds: float = 1.0
    max_backoff_seconds: float = 30.0
    max_total_retry_seconds: float = 120.0
    operational_cap_tokens: int = 384

    def __post_init__(self) -> None:
        """Validate configuration before any external state is accessed."""
        self._validate()

    def _validate(self) -> None:
        """Reject invalid configuration before file or environment access."""
        if self.provider != DEFAULT_PROVIDER:
            raise EmbeddingConfigError("invalid-provider")
        if not isinstance(self.model, str) or not self.model.strip():
            raise EmbeddingConfigError("invalid-model")
        limits = (
            (self.dimensions, None, "invalid-dimensions"),
            (
                self.max_inputs_per_request,
                API_MAX_INPUTS_PER_REQUEST,
                "invalid-max-inputs",
            ),
            (
                self.max_tokens_per_request,
                API_MAX_TOKENS_PER_REQUEST,
                "invalid-max-tokens",
            ),
            (self.max_attempts, None, "invalid-max-attempts"),
            (self.operational_cap_tokens, 512, "invalid-operational-cap"),
        )
        for value, ceiling, code in limits:
            if (
                type(value) is not int
                or value < 1
                or (ceiling is not None and value > ceiling)
            ):
                raise EmbeddingConfigError(code)
        for retry_value in (
            self.request_timeout_seconds,
            self.initial_backoff_seconds,
            self.max_backoff_seconds,
            self.max_total_retry_seconds,
        ):
            if (
                type(retry_value) not in (float, int)
                or not math.isfinite(retry_value)
                or retry_value < 0
            ):
                raise EmbeddingConfigError("invalid-retry-limits")
        if not isinstance(self.passage_prefix, str) or not isinstance(
            self.query_prefix, str
        ):
            raise EmbeddingConfigError("invalid-prefix")


def build_passage_input(
    config: EmbeddingConfig, section_path: tuple[str, ...], chunk_text: str
) -> str:
    """Build final passage text through the public chunk template."""
    return build_embedding_text(section_path, chunk_text, config.passage_prefix)
