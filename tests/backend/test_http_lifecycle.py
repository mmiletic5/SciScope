"""RED tests for HTTP request leases owned by a composed application."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Event, Thread
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from sciscope.api.app import AppDependencies
from sciscope.api.composition import ComposedApplication, create_application
from sciscope.question_service.contracts import (
    ComponentMetadata,
    QuestionMetadata,
    RetrievalOutcome,
)
from sciscope.question_service.fakes import FakeAnswerProvider, FakeRetrieval
from sciscope.question_service.retrieval_adapter import RetrievalAdapterSettings


class _EngineSentinel:
    """Record disposal without constructing or connecting an Engine."""

    def __init__(self) -> None:
        self.dispose_calls = 0

    def dispose(self) -> None:
        """Record an owned-resource cleanup attempt."""
        self.dispose_calls += 1


@dataclass
class _BlockingRetrieval:
    """Hold a v1 request at retrieval until the test releases it."""

    started: Event
    release: Event
    calls: int = 0

    def retrieve(self, question: str, request_id: str) -> RetrievalOutcome:
        """Wait deterministically before returning a synthetic outcome."""
        self.calls += 1
        self.started.set()
        if not self.release.wait(timeout=2):
            raise AssertionError("test did not release the blocked request")
        return FakeRetrieval().retrieve(question, request_id)


class _RaisingRetrieval:
    """Raise locally to prove HTTP lease release on a handled failure."""

    def retrieve(self, question: str, request_id: str) -> RetrievalOutcome:
        """Raise after the HTTP lifecycle boundary has been entered."""
        del question, request_id
        raise RuntimeError("offline lifecycle fixture failure")


def _metadata() -> QuestionMetadata:
    """Return explicit offline metadata for a composed application."""
    retrieval = ComponentMetadata(
        configured_origin="real",
        executed=False,
        is_test_data=True,
    )
    return QuestionMetadata(
        retrieval=retrieval,
        answer_provider=ComponentMetadata(
            configured_origin="fake",
            executed=False,
            is_test_data=True,
        ),
    )


def _composed_application(engine: _EngineSentinel) -> ComposedApplication:
    """Create an owned offline composition with explicit dependencies."""
    metadata = _metadata()
    return create_application(
        engine=None,
        engine_factory=lambda: cast(Engine, engine),
        query_embedder=None,
        retrieval_settings=RetrievalAdapterSettings(
            contract_version="retrieval.v1",
            mode="lexical",
            top_k=1,
            filters=None,
            ranking=None,
            retrieval_metadata=metadata.retrieval,
        ),
        provider=FakeAnswerProvider(),
        metadata=metadata,
    )


def _borrowed_composed_application(
    engine: _EngineSentinel,
) -> ComposedApplication:
    """Create an offline composition that borrows its supplied Engine."""
    metadata = _metadata()
    return create_application(
        engine=cast(Engine, engine),
        engine_factory=None,
        query_embedder=None,
        retrieval_settings=RetrievalAdapterSettings(
            contract_version="retrieval.v1",
            mode="lexical",
            top_k=1,
            filters=None,
            ranking=None,
            retrieval_metadata=metadata.retrieval,
        ),
        provider=FakeAnswerProvider(),
        metadata=metadata,
    )


def _install_blocking_retrieval(
    composed: ComposedApplication,
    retrieval: _BlockingRetrieval,
) -> None:
    """Install an in-memory dependency without changing production wiring."""
    dependencies = composed.app.state.dependencies
    composed.app.state.dependencies = AppDependencies(
        retrieval=retrieval,
        provider=dependencies.provider,
        v2_metadata=dependencies.v2_metadata,
    )


def _post_v1(
    app: Any,
    result: dict[str, object],
) -> None:
    """Issue one in-process request and retain its response or failure."""
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            result["response"] = client.post(
                "/api/v1/questions",
                json={
                    "workflow": "research_question",
                    "question": "lifecycle fixture question",
                    "request_id": "http-lifecycle-request-001",
                },
            )
    except BaseException as error:
        result["error"] = error


def test_owned_engine_is_not_disposed_during_an_active_http_request() -> None:
    """Require an HTTP request to hold the composition operation lease."""
    engine = _EngineSentinel()
    composed = _composed_application(engine)
    started = Event()
    release = Event()
    retrieval = _BlockingRetrieval(started=started, release=release)
    _install_blocking_retrieval(composed, retrieval)
    result: dict[str, object] = {}
    worker = Thread(target=_post_v1, args=(composed.app, result))

    worker.start()
    assert started.wait(timeout=2), "HTTP request did not reach retrieval"
    try:
        with pytest.raises(RuntimeError, match="active operations"):
            composed.close()
        assert engine.dispose_calls == 0
    finally:
        release.set()
        worker.join(timeout=2)

    assert not worker.is_alive(), "HTTP request did not finish after release"
    assert "error" not in result
    assert result["response"].status_code == 200  # type: ignore[attr-defined]
    composed.close()
    assert engine.dispose_calls == 1


def test_closed_composition_does_not_enter_a_resource_using_handler() -> None:
    """Reject a request before retrieval after local lifecycle shutdown."""
    engine = _EngineSentinel()
    composed = _composed_application(engine)
    started = Event()
    release = Event()
    release.set()
    retrieval = _BlockingRetrieval(started=started, release=release)
    _install_blocking_retrieval(composed, retrieval)

    composed.close()
    with TestClient(composed.app, raise_server_exceptions=False) as client:
        client.post(
            "/api/v1/questions",
            json={
                "workflow": "research_question",
                "question": "closed lifecycle fixture question",
                "request_id": "http-lifecycle-request-002",
            },
        )

    assert retrieval.calls == 0
    assert engine.dispose_calls == 1


def test_v2_request_holds_a_lease_until_its_handler_completes() -> None:
    """Protect the separately versioned route with the same owner lease."""
    engine = _EngineSentinel()
    composed = _composed_application(engine)
    started = Event()
    release = Event()
    retrieval = _BlockingRetrieval(started=started, release=release)
    _install_blocking_retrieval(composed, retrieval)
    result: dict[str, object] = {}

    def post_v2() -> None:
        with TestClient(composed.app, raise_server_exceptions=False) as client:
            result["response"] = client.post(
                "/api/v2/questions",
                json={
                    "workflow": "research_question",
                    "question": "v2 lifecycle fixture question",
                    "request_id": "http-lifecycle-request-v2-001",
                },
            )

    worker = Thread(target=post_v2)
    worker.start()
    assert started.wait(timeout=2), "v2 request did not reach retrieval"
    try:
        with pytest.raises(RuntimeError, match="active operations"):
            composed.close()
        assert engine.dispose_calls == 0
    finally:
        release.set()
        worker.join(timeout=2)

    assert not worker.is_alive(), "v2 request did not finish after release"
    assert "response" in result


def test_request_failure_releases_its_lease_before_later_close() -> None:
    """Release a lease when a route raises and FastAPI handles the failure."""
    engine = _EngineSentinel()
    composed = _composed_application(engine)
    dependencies = composed.app.state.dependencies
    composed.app.state.dependencies = AppDependencies(
        retrieval=_RaisingRetrieval(),
        provider=dependencies.provider,
        v2_metadata=dependencies.v2_metadata,
    )

    with TestClient(composed.app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/v1/questions",
            json={
                "workflow": "research_question",
                "question": "exceptional lifecycle fixture question",
                "request_id": "http-lifecycle-request-003",
            },
        )

    assert response.status_code == 500
    composed.close()
    assert engine.dispose_calls == 1


def test_lifespan_shutdown_disposes_owned_engine_once() -> None:
    """Use the composed application's shutdown hook for owned cleanup."""
    engine = _EngineSentinel()
    composed = _composed_application(engine)

    with TestClient(composed.app):
        pass

    assert engine.dispose_calls == 1
    composed.close()
    assert engine.dispose_calls == 1


def test_lifespan_shutdown_never_disposes_a_borrowed_engine() -> None:
    """Preserve caller ownership when the composed app shuts down."""
    engine = _EngineSentinel()
    composed = _borrowed_composed_application(engine)

    with TestClient(composed.app):
        pass

    assert engine.dispose_calls == 0
