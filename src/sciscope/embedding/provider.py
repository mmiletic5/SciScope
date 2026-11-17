"""Provider-neutral results and a deterministic synthetic embedder."""

from __future__ import annotations

import hashlib
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from sciscope.chunking.counter import Utf8BytesDiv3Counter
from sciscope.embedding.config import EmbeddingConfig, EmbeddingInputError


@dataclass(frozen=True, slots=True)
class EmbeddingUsage:
    """Provider-reported usage for one successful batch."""

    prompt_tokens: int
    total_tokens: int


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    """Input-ordered vectors, successful usage, headers, and attempts."""

    vectors: tuple[tuple[float, ...], ...]
    usage: EmbeddingUsage
    rate_limit_headers: Mapping[str, str]
    attempts: int


@runtime_checkable
class Embedder(Protocol):
    """Embed final passages or prefixed queries with one configuration."""

    @property
    def provider_id(self) -> str:
        """Return the declared provider identifier."""
        ...

    @property
    def model(self) -> str:
        """Return the configured model identifier."""
        ...

    @property
    def dimensions(self) -> int:
        """Return the requested vector dimensions."""
        ...

    def embed_passages(self, texts: Sequence[str]) -> EmbeddingResult:
        """Embed final passage inputs without adding any prefix."""
        ...

    def embed_queries(self, queries: Sequence[str]) -> EmbeddingResult:
        """Embed queries after prepending the configured query prefix."""
        ...


def _fake_usage(texts: Sequence[str]) -> EmbeddingUsage:
    """Estimate synthetic usage for offline tests."""
    tokens = sum(Utf8BytesDiv3Counter().count(text) for text in texts)
    return EmbeddingUsage(tokens, tokens)


def _validate_inputs(texts: Sequence[str], maximum: int) -> None:
    """Reject invalid input before prefixing, usage counting, or transport."""
    if not texts:
        raise EmbeddingInputError("empty-input-list")
    if any(not isinstance(text, str) or not text.strip() for text in texts):
        raise EmbeddingInputError("blank-input")
    if len(texts) > maximum:
        raise EmbeddingInputError("too-many-inputs")


@dataclass(frozen=True, slots=True)
class FakeEmbedder:
    """Deterministic normalized test provider, unavailable through the CLI."""

    config: EmbeddingConfig
    usage_counter: Callable[[Sequence[str]], EmbeddingUsage] = _fake_usage
    provider_id: str = "fake"

    @property
    def model(self) -> str:
        """Return the configured synthetic model."""
        return self.config.model

    @property
    def dimensions(self) -> int:
        """Return the configured synthetic dimensions."""
        return self.config.dimensions

    def embed_passages(self, texts: Sequence[str]) -> EmbeddingResult:
        """Return input-ordered deterministic normalized vectors."""
        _validate_inputs(texts, self.config.max_inputs_per_request)
        vectors = []
        for text in texts:
            seed = text.encode("utf-8")
            values = tuple(
                (
                    int.from_bytes(
                        hashlib.sha256(
                            seed + index.to_bytes(8, "big")
                        ).digest()[:4],
                        "big",
                    )
                    + 1
                )
                / (2**32 + 1)
                for index in range(self.dimensions)
            )
            norm = math.sqrt(math.fsum(value * value for value in values))
            vectors.append(tuple(value / norm for value in values))
        return EmbeddingResult(tuple(vectors), self.usage_counter(texts), {}, 1)

    def embed_queries(self, queries: Sequence[str]) -> EmbeddingResult:
        """Prefix queries exactly once and embed the resulting text."""
        _validate_inputs(queries, self.config.max_inputs_per_request)
        return self.embed_passages(
            [self.config.query_prefix + query for query in queries]
        )
