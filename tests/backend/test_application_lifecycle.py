"""RED behavior tests for explicit application composition and lifecycle."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any, Protocol, cast

import pytest
from fastapi import FastAPI

from sciscope.question_service.contracts import (
    ComponentMetadata,
    QuestionMetadata,
)
from sciscope.question_service.retrieval_adapter import (
    PublicRetrievalAdapter,
    RetrievalAdapterSettings,
)
from sciscope.retrieval import RetrievalService


class _EngineSentinel:
    """In-memory Engine substitute that records disposal without connecting."""

    def __init__(self, *, dispose_raises: bool = False) -> None:
        self.dispose_calls = 0
        self.dispose_raises = dispose_raises

    def dispose(self) -> None:
        """Record one disposal and optionally emulate a cleanup failure."""
        self.dispose_calls += 1
        if self.dispose_raises:
            raise RuntimeError("sentinel cleanup failure")


class _ProviderSentinel:
    """Offline provider placeholder that must not run during composition."""

    def answer(self, *args: object, **kwargs: object) -> object:
        """Fail when an unexpected construction-time provider call occurs."""
        del args, kwargs
        raise AssertionError("composition must not invoke the provider")


class _ComposedApplication(Protocol):
    """Expected public lifecycle surface of the composed application."""

    app: FastAPI

    def close(self) -> None:
        """Close composition-owned resources when no operation is active."""

    def operation(self) -> AbstractContextManager[None]:
        """Lease the composed application for one tracked operation."""


def _composition_module() -> Any:
    """Load the proposed explicit application-composition boundary."""
    return importlib.import_module("sciscope.api.composition")


def _arguments() -> dict[str, object]:
    """Return fully explicit, offline composition inputs."""
    retrieval_metadata = ComponentMetadata(
        configured_origin="real",
        executed=False,
        is_test_data=True,
    )
    return {
        "engine": None,
        "engine_factory": None,
        "query_embedder": None,
        "retrieval_settings": RetrievalAdapterSettings(
            contract_version="retrieval.v1",
            mode="lexical",
            top_k=1,
            filters=None,
            ranking=None,
            retrieval_metadata=retrieval_metadata,
        ),
        "provider": _ProviderSentinel(),
        "metadata": QuestionMetadata(
            retrieval=retrieval_metadata,
            answer_provider=ComponentMetadata(
                configured_origin="fake",
                executed=False,
                is_test_data=True,
            ),
        ),
    }


def _create_application(**overrides: object) -> _ComposedApplication:
    """Call the selected root with complete explicit configuration."""
    arguments = _arguments()
    arguments.update(overrides)
    module = _composition_module()
    create = cast(
        Callable[..., _ComposedApplication], module.create_application
    )
    return create(**arguments)


def test_composition_requires_exactly_one_engine_source() -> None:
    """Reject absent or competing owned and borrowed Engine inputs."""
    with pytest.raises(ValueError):
        _create_application(engine=None, engine_factory=None)

    with pytest.raises(ValueError):
        _create_application(
            engine=_EngineSentinel(),
            engine_factory=lambda: _EngineSentinel(),
        )


def test_borrowed_engine_builds_app_and_is_not_disposed_on_close() -> None:
    """Build from a caller-owned Engine without claiming ownership."""
    engine = _EngineSentinel()

    composed = _create_application(engine=engine)

    assert isinstance(composed.app, FastAPI)
    composed.close()
    assert engine.dispose_calls == 0


def test_owned_engine_is_disposed_once_when_closed_repeatedly() -> None:
    """Dispose an Engine created by the injected factory exactly once."""
    engine = _EngineSentinel()
    factory_calls = 0

    def engine_factory() -> _EngineSentinel:
        nonlocal factory_calls
        factory_calls += 1
        return engine

    composed = _create_application(engine_factory=engine_factory)

    composed.close()
    composed.close()

    assert factory_calls == 1
    assert engine.dispose_calls == 1


def test_validation_failure_does_not_allocate_an_owned_engine() -> None:
    """Reject invalid explicit configuration before invoking engine_factory."""
    factory_calls = 0

    def engine_factory() -> _EngineSentinel:
        nonlocal factory_calls
        factory_calls += 1
        return _EngineSentinel()

    with pytest.raises(ValueError):
        _create_application(engine_factory=engine_factory, provider=None)

    assert factory_calls == 0


def test_initialization_failure_disposes_owned_engine_and_preserves_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retain a composition failure when owned-Engine cleanup succeeds."""
    module = _composition_module()
    engine = _EngineSentinel()

    def fail_factory(**kwargs: object) -> object:
        del kwargs
        raise ValueError("original composition failure")

    monkeypatch.setattr(module, "create_retrieval_service", fail_factory)

    with pytest.raises(ValueError, match="original composition failure"):
        _create_application(engine_factory=lambda: engine)

    assert engine.dispose_calls == 1


def test_cleanup_failure_does_not_mask_initialization_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preserve the original failure when owned-resource cleanup also fails."""
    module = _composition_module()
    engine = _EngineSentinel(dispose_raises=True)

    def fail_factory(**kwargs: object) -> object:
        del kwargs
        raise ValueError("original composition failure")

    monkeypatch.setattr(module, "create_retrieval_service", fail_factory)

    with pytest.raises(ValueError, match="original composition failure"):
        _create_application(engine_factory=lambda: engine)

    assert engine.dispose_calls == 1


def test_close_rejects_active_operations_until_the_lease_is_released() -> None:
    """Prevent owned-resource disposal while the root tracks active work."""
    engine = _EngineSentinel()
    composed = _create_application(engine_factory=lambda: engine)

    with composed.operation():
        with pytest.raises(RuntimeError):
            composed.close()
        assert engine.dispose_calls == 0

    composed.close()
    assert engine.dispose_calls == 1


def test_operation_releases_and_rejects_leases_after_close() -> None:
    """Release exceptional leases and reject work after successful shutdown."""
    engine = _EngineSentinel()
    composed = _create_application(engine_factory=lambda: engine)

    with pytest.raises(ValueError, match="operation failure"):
        with composed.operation():
            raise ValueError("operation failure")

    composed.close()
    with pytest.raises(RuntimeError):
        composed.operation().__enter__()
    assert engine.dispose_calls == 1


def test_composition_wires_public_adapter_and_explicit_dependencies() -> None:
    """Build the accepted object graph without calling provider or Engine."""
    engine = _EngineSentinel()
    provider = _ProviderSentinel()
    arguments = _arguments()
    settings = cast(RetrievalAdapterSettings, arguments["retrieval_settings"])
    metadata = cast(QuestionMetadata, arguments["metadata"])

    composed = _create_application(
        engine=engine,
        provider=provider,
        retrieval_settings=settings,
        metadata=metadata,
    )

    adapter = composed.app.state.dependencies.retrieval
    assert type(adapter) is PublicRetrievalAdapter
    assert adapter._settings is settings
    assert type(adapter._service) is RetrievalService
    assert composed.app.state.dependencies.provider is provider
    assert engine.dispose_calls == 0
