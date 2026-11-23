"""Explicit offline-safe application composition and resource ownership."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock
from typing import TYPE_CHECKING, Protocol, cast

from fastapi import FastAPI, Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from sciscope.api.app import create_app
from sciscope.question_service.contracts import (
    AnswerProvider,
    QuestionMetadata,
)
from sciscope.question_service.retrieval_adapter import (
    PublicRetrievalAdapter,
    RetrievalAdapterSettings,
)
from sciscope.question_service.validation import validate_question_metadata
from sciscope.retrieval import QueryEmbedder
from sciscope.retrieval.factory import create_retrieval_service

if TYPE_CHECKING:
    from sqlalchemy import Engine


class _DisposableEngine(Protocol):
    """Lifecycle capability retained by an owned application resource."""

    def dispose(self) -> None:
        """Dispose the engine's pooled resources."""


@dataclass(slots=True)
class ComposedApplication:
    """An application plus explicit ownership-aware lifecycle controls."""

    app: FastAPI
    _owned_engine: _DisposableEngine | None
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)
    _active_operations: int = field(default=0, init=False, repr=False)
    _closed: bool = field(default=False, init=False, repr=False)

    @contextmanager
    def operation(self) -> Iterator[None]:
        """Lease the composition while a caller-managed operation is active."""
        with self._lock:
            if self._closed:
                raise RuntimeError("Application composition is closed")
            self._active_operations += 1
        try:
            yield
        finally:
            with self._lock:
                self._active_operations -= 1

    def close(self) -> None:
        """Dispose an owned Engine once when no operation lease is active."""
        with self._lock:
            if self._active_operations:
                raise RuntimeError(
                    "Application composition has active operations"
                )
            if self._closed:
                return
            self._closed = True
            owned_engine = self._owned_engine

        if owned_engine is not None:
            owned_engine.dispose()

    def install_http_lifecycle(self) -> None:
        """Protect HTTP handlers with this composition's operation lease.

        The wrapper covers request dispatch through handler completion. It does
        not extend the lease to streaming-response iteration or background-task
        execution after the handler returns.
        """

        @self.app.middleware("http")
        async def operation_lease(
            request: Request,
            call_next: RequestResponseEndpoint,
        ) -> Response:
            with self.operation():
                return await call_next(request)

        self.app.router.on_shutdown.append(self.close)


def create_application(
    *,
    engine: Engine | None,
    engine_factory: Callable[[], Engine] | None,
    query_embedder: QueryEmbedder | None,
    retrieval_settings: RetrievalAdapterSettings,
    provider: AnswerProvider,
    metadata: QuestionMetadata,
) -> ComposedApplication:
    """Compose the accepted API dependencies without hidden resources.

    Exactly one Engine source is required. A directly supplied Engine remains
    borrowed; an Engine returned by ``engine_factory`` is owned by the result.
    """
    _validate_configuration(
        engine=engine,
        engine_factory=engine_factory,
        query_embedder=query_embedder,
        retrieval_settings=retrieval_settings,
        provider=provider,
        metadata=metadata,
    )
    owned_engine: _DisposableEngine | None = None
    resolved_engine = engine
    try:
        if engine_factory is not None:
            resolved_engine = engine_factory()
            owned_engine = cast(_DisposableEngine, resolved_engine)
        assert resolved_engine is not None
        service = create_retrieval_service(
            engine=resolved_engine,
            query_embedder=query_embedder,
        )
        adapter = PublicRetrievalAdapter(
            service=service,
            settings=retrieval_settings,
        )
        app = create_app(
            retrieval=adapter,
            provider=provider,
            v2_metadata=metadata,
        )
        composed = ComposedApplication(app=app, _owned_engine=owned_engine)
        composed.install_http_lifecycle()
        return composed
    except Exception as error:
        if owned_engine is not None:
            try:
                owned_engine.dispose()
            except Exception:
                error.add_note(
                    "Owned Engine cleanup failed during initialization"
                )
        raise


def _validate_configuration(
    *,
    engine: Engine | None,
    engine_factory: Callable[[], Engine] | None,
    query_embedder: QueryEmbedder | None,
    retrieval_settings: RetrievalAdapterSettings,
    provider: AnswerProvider,
    metadata: QuestionMetadata,
) -> None:
    """Reject invalid explicit inputs before allocating an Engine."""
    if (engine is None) is (engine_factory is None):
        raise ValueError("Provide exactly one Engine source")
    if type(retrieval_settings) is not RetrievalAdapterSettings:
        raise ValueError("Invalid retrieval settings")
    if type(metadata) is not QuestionMetadata:
        raise ValueError("Invalid question metadata")
    if provider is None:
        raise ValueError("An explicit answer provider is required")
    validate_question_metadata(metadata)
    settings_metadata = retrieval_settings.retrieval_metadata
    if (
        metadata.retrieval.configured_origin
        != settings_metadata.configured_origin
        or metadata.retrieval.is_test_data != settings_metadata.is_test_data
    ):
        raise ValueError("Retrieval metadata does not match retrieval settings")
    if (
        retrieval_settings.mode in ("dense", "hybrid")
        and query_embedder is None
    ):
        raise ValueError("Dense and hybrid retrieval require a query embedder")
