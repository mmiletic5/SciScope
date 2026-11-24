"""RED behavior tests for public retrieval composition boundaries."""

from __future__ import annotations

import importlib
import subprocess
import sys
from collections.abc import Callable
from typing import cast

import pytest

from sciscope.retrieval import (
    QueryEmbedder,
    RetrievalErrorCode,
    RetrievalException,
    RetrievalRequest,
    RetrievalService,
)


class _NoUseEngine:
    """A borrowed Engine sentinel that records prohibited disposal."""

    def __init__(self) -> None:
        self.dispose_calls = 0
        self.connect_calls = 0

    def connect(self) -> None:
        """Fail if construction opens a database connection."""
        self.connect_calls += 1
        raise AssertionError("composition must not connect during construction")

    def dispose(self) -> None:
        """Record an unexpected attempt to dispose a borrowed Engine."""
        self.dispose_calls += 1


def _factory() -> Callable[..., RetrievalService]:
    """Load the proposed public factory at its approved module boundary."""
    module = importlib.import_module("sciscope.retrieval.factory")
    return cast(
        Callable[..., RetrievalService], module.create_retrieval_service
    )


def test_public_factory_requires_explicit_engine_and_embedder() -> None:
    """Require explicit resources instead of hidden composition defaults."""
    factory = _factory()

    with pytest.raises(TypeError):
        factory()


def test_public_factory_constructs_public_service_without_connecting() -> None:
    """Compose only the public facade without opening the borrowed Engine."""
    engine = _NoUseEngine()

    service = _factory()(engine=engine, query_embedder=None)

    assert type(service) is RetrievalService
    assert engine.dispose_calls == 0


def test_public_factory_does_not_dispose_a_borrowed_engine() -> None:
    """Leave disposal of a caller-supplied Engine to that caller."""
    engine = _NoUseEngine()

    _factory()(engine=engine, query_embedder=None)

    assert engine.dispose_calls == 0


def test_public_factory_accepts_an_explicit_public_query_embedder() -> None:
    """Accept the exported query-embedder protocol without constructing one."""
    engine = _NoUseEngine()
    embedder = cast(QueryEmbedder, object())

    service = _factory()(engine=engine, query_embedder=embedder)

    assert type(service) is RetrievalService
    assert engine.dispose_calls == 0


def test_factory_import_does_not_load_the_private_core() -> None:
    """Keep factory import-safe until composition is requested."""
    script = """
import sys
sys.path.insert(0, 'src')
import sciscope.retrieval.factory
assert 'sciscope.retrieval._core' not in sys.modules
assert 'sqlalchemy' not in sys.modules
"""

    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout


def test_composed_service_reaches_existing_executor_error_mapping() -> None:
    """Verify the facade uses the real executor path, not a dummy service."""
    engine = _NoUseEngine()
    request = RetrievalRequest(
        contract_version="retrieval.v1",
        request_id="factory-offline-001",
        query_text="offline composition request",
        mode="lexical",
        top_k=1,
    )

    with pytest.raises(RetrievalException) as raised:
        _factory()(engine=engine, query_embedder=None).retrieve(request)

    assert raised.value.code is RetrievalErrorCode.RETRIEVAL_INTERNAL_ERROR
    assert raised.value.request_id == request.request_id
    assert engine.connect_calls == 1
    assert engine.dispose_calls == 0
