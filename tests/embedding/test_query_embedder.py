"""Offline tests for the retrieval query-embedder adapter."""

from __future__ import annotations

import pytest
from embed_fixtures import (
    FAKE_KEY,
    RetryClock,
    ScriptedTransport,
    response,
    response_body,
)

from sciscope.embedding.config import EmbeddingConfig
from sciscope.embedding.openai_client import (
    OpenAIEmbedder,
    TransportConnectionError,
    TransportResponse,
)
from sciscope.embedding.provider import FakeEmbedder
from sciscope.embedding.query_embedder import (
    OpenAIQueryEmbedder,
    QueryEmbedderConfigMismatch,
)
from sciscope.retrieval._core import QueryEmbeddingUnavailable
from sciscope.retrieval.contracts import EmbeddingConfig as QueryConfig

_MODEL = "text-embedding-3-small"
_DIMENSIONS = 2


def _config(**overrides: object) -> EmbeddingConfig:
    """Build a small synthetic embedding configuration."""
    values: dict[str, object] = {
        "model": _MODEL,
        "dimensions": _DIMENSIONS,
        "max_attempts": 2,
        "initial_backoff_seconds": 0.0,
    }
    values.update(overrides)
    return EmbeddingConfig(**values)  # type: ignore[arg-type]


def _query_config(**overrides: object) -> QueryConfig:
    """Build the query identity the retrieval core would request."""
    values: dict[str, object] = {
        "provider": "openai",
        "model": _MODEL,
        "dimensions": _DIMENSIONS,
        "query_prefix": "",
    }
    values.update(overrides)
    return QueryConfig(**values)  # type: ignore[arg-type]


def _adapter(
    script: list[TransportResponse | Exception],
) -> tuple[OpenAIQueryEmbedder, ScriptedTransport]:
    """Wrap an OpenAI embedder that uses a scripted offline transport."""
    config = _config()
    transport = ScriptedTransport(script)
    clock = RetryClock()
    embedder = OpenAIEmbedder(
        config,
        transport,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
        uniform=clock.uniform,
    )
    return OpenAIQueryEmbedder(embedder, config), transport


def test_returns_single_vector_and_sends_unprefixed_query() -> None:
    """A matching identity embeds exactly one query with no prefix."""
    adapter, transport = _adapter(
        [response(body=response_body(((0.25, -0.5),)))]
    )

    vector = adapter.embed_query("honey bee foraging", config=_query_config())

    assert tuple(vector) == (0.25, -0.5)
    assert len(transport.calls) == 1
    payload = transport.calls[0].payload
    assert payload["input"] == ["honey bee foraging"]
    assert payload["model"] == _MODEL
    assert payload["dimensions"] == _DIMENSIONS


@pytest.mark.parametrize(
    "overrides",
    [
        {"provider": "other"},
        {"model": "text-embedding-3-large"},
        {"dimensions": 3},
        {"query_prefix": "query: "},
    ],
)
def test_requested_identity_mismatch_fails_closed(
    overrides: dict[str, object],
) -> None:
    """Any requested identity difference refuses before transport use."""
    adapter, transport = _adapter([])

    with pytest.raises(QueryEmbedderConfigMismatch) as raised:
        adapter.embed_query("query", config=_query_config(**overrides))

    assert not isinstance(raised.value, QueryEmbeddingUnavailable)
    assert transport.calls == []


def test_wrapped_embedder_identity_mismatch_fails_at_construction() -> None:
    """The adapter refuses an embedder built from another configuration."""
    embedder = OpenAIEmbedder(_config(dimensions=3), ScriptedTransport([]))

    with pytest.raises(QueryEmbedderConfigMismatch):
        OpenAIQueryEmbedder(embedder, _config())


def test_fake_embedder_provider_does_not_match_openai_identity() -> None:
    """A fake embedder can never stand in for the OpenAI query identity."""
    with pytest.raises(QueryEmbedderConfigMismatch):
        OpenAIQueryEmbedder(FakeEmbedder(_config()), _config())


@pytest.mark.parametrize(
    "script",
    [
        [response(401, body={"error": {"code": "invalid_api_key"}})],
        [TransportConnectionError(), TransportConnectionError()],
        [response(500, body={}), response(503, body={})],
        [response(body={"model": _MODEL, "data": []})],
    ],
)
def test_provider_failures_map_to_unavailable(
    script: list[TransportResponse | Exception],
) -> None:
    """Provider failures raise a bare unavailable signal without context."""
    adapter, _ = _adapter(script)

    with pytest.raises(QueryEmbeddingUnavailable) as raised:
        adapter.embed_query("secret-free query", config=_query_config())

    assert str(raised.value) == ""
    assert raised.value.__cause__ is None
    assert raised.value.__suppress_context__ is True


def test_repr_contains_no_secret() -> None:
    """The adapter representation exposes only the embedding identity."""
    adapter, _ = _adapter([])

    assert FAKE_KEY not in repr(adapter)
    assert _MODEL in repr(adapter)
