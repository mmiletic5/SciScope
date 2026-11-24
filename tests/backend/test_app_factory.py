"""Behavior tests for the Feature 011 FastAPI composition root."""

import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sciscope.api.app import create_app
from sciscope.question_service.contracts import (
    ComponentMetadata,
    QuestionMetadata,
)


class _OpaqueSentinel:
    """Raises if the factory attempts to use an injected dependency."""

    def __init__(self) -> None:
        self.call_count = 0

    def __call__(self) -> None:
        self.call_count += 1
        raise AssertionError("T002 must not invoke injected dependencies")


def _route_paths(app: FastAPI) -> set[str]:
    """Return the declared paths across FastAPI's heterogeneous routes."""
    return {str(getattr(route, "path", "")) for route in app.routes}


def test_create_app_stores_injected_sentinels_without_initialization() -> None:
    """Construct an offline app and register its question endpoint inertly."""
    retrieval_sentinel = _OpaqueSentinel()
    provider_sentinel = _OpaqueSentinel()
    prohibited_modules = {
        "sciscope.database.session",
        "sciscope.embedding.provider",
        "sciscope.retrieval._core",
    }
    modules_before_creation = prohibited_modules & sys.modules.keys()

    app = create_app(
        retrieval=retrieval_sentinel,
        provider=provider_sentinel,
    )

    assert isinstance(app, FastAPI)
    assert app.state.dependencies.retrieval is retrieval_sentinel
    assert app.state.dependencies.provider is provider_sentinel
    assert retrieval_sentinel.call_count == 0
    assert provider_sentinel.call_count == 0
    assert prohibited_modules & sys.modules.keys() == modules_before_creation
    assert "/api/v1/questions" in _route_paths(app)

    with TestClient(app):
        pass

    assert retrieval_sentinel.call_count == 0
    assert provider_sentinel.call_count == 0


def test_create_app_registers_v2_only_for_explicit_metadata_inertly() -> None:
    """Register v2 from explicit metadata without invoking dependencies."""
    retrieval_sentinel = _OpaqueSentinel()
    provider_sentinel = _OpaqueSentinel()
    metadata = QuestionMetadata(
        retrieval=ComponentMetadata(
            configured_origin="fake",
            executed=False,
            is_test_data=True,
        ),
        answer_provider=ComponentMetadata(
            configured_origin="fake",
            executed=False,
            is_test_data=True,
        ),
    )

    app = create_app(
        retrieval=retrieval_sentinel,
        provider=provider_sentinel,
        v2_metadata=metadata,
    )

    assert app.state.dependencies.v2_metadata is metadata
    assert "/api/v2/questions" in _route_paths(app)
    assert retrieval_sentinel.call_count == 0
    assert provider_sentinel.call_count == 0

    with TestClient(app):
        pass

    assert retrieval_sentinel.call_count == 0
    assert provider_sentinel.call_count == 0
