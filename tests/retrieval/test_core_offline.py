"""Offline call-order and provider failure behavior for the retrieval core."""

from __future__ import annotations

from typing import cast

import pytest
from sqlalchemy import Engine

from sciscope.retrieval._core import (
    QueryEmbeddingUnavailable,
    _Corpus,
    _EmbeddingConfig,
    _RetrievalCore,
)
from sciscope.retrieval._errors import RetrievalErrorCode, RetrievalFailure


def _request(mode: str = "dense") -> dict[str, object]:
    return {
        "contract_version": "retrieval.v1",
        "request_id": "offline-core",
        "query_text": "bee homing",
        "mode": mode,
        "top_k": 5,
    }


def _corpus(config: _EmbeddingConfig | None = None) -> _Corpus:
    return _Corpus(
        import_id=1,
        embedding_set_id=1,
        delivery_digest="sha256:" + "0" * 64,
        source_contract_version="0.3.0",
        corpus_version="pilot17-xml-" + "0" * 12,
        embedding_config=config or _EmbeddingConfig(),
        embedding_compatible=True,
    )


def test_preflight_mismatch_stops_before_embedding(fake_embedder, monkeypatch):
    """An incompatible active set never calls the configured embedder."""
    core = _RetrievalCore(cast(Engine, None), fake_embedder)
    incompatible = _corpus(_EmbeddingConfig(dimensions=768))
    monkeypatch.setattr(
        core, "_read_preflight", lambda request_id: incompatible
    )
    with pytest.raises(RetrievalFailure) as raised:
        core.retrieve(_request())
    assert (
        raised.value.code == RetrievalErrorCode.EMBEDDING_CONFIGURATION_MISMATCH
    )
    assert fake_embedder.calls == []


def test_no_active_corpus_stops_before_embedding(fake_embedder, monkeypatch):
    """A missing corpus fails before any embedding provider work."""
    core = _RetrievalCore(cast(Engine, None), fake_embedder)
    failure = RetrievalFailure(RetrievalErrorCode.CORPUS_NOT_LOADED)

    def fail_preflight(request_id: str) -> _Corpus:
        del request_id
        raise failure

    monkeypatch.setattr(core, "_read_preflight", fail_preflight)
    with pytest.raises(RetrievalFailure) as raised:
        core.retrieve(_request())
    assert raised.value.code == RetrievalErrorCode.CORPUS_NOT_LOADED
    assert fake_embedder.calls == []


def test_transient_embedder_failure_is_typed_without_fallback(monkeypatch):
    """Provider outage raises one retryable failure and stops the request."""

    class UnavailableEmbedder:
        def __init__(self) -> None:
            self.calls = 0

        def embed_query(
            self, text: str, *, config: object
        ) -> tuple[float, ...]:
            self.calls += 1
            raise QueryEmbeddingUnavailable

    embedder = UnavailableEmbedder()
    core = _RetrievalCore(cast(Engine, None), embedder)
    monkeypatch.setattr(core, "_read_preflight", lambda request_id: _corpus())
    with pytest.raises(RetrievalFailure) as raised:
        core.retrieve(_request("hybrid"))
    assert raised.value.code == RetrievalErrorCode.EMBEDDING_UNAVAILABLE
    assert raised.value.retryable
    assert embedder.calls == 1


def test_lexical_mode_never_calls_embedder(fake_embedder, monkeypatch):
    """The lexical path does not require or invoke query embedding."""
    core = _RetrievalCore(cast(Engine, None), fake_embedder)
    monkeypatch.setattr(
        core, "_retrieve_in_snapshot", lambda request, vector: "ok"
    )
    assert core.retrieve(_request("lexical")) == "ok"
    assert fake_embedder.calls == []
