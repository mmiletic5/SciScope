"""Explicit, connection-free composition for the public retrieval facade."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from sciscope.retrieval.service import QueryEmbedder, RetrievalService

if TYPE_CHECKING:
    from sqlalchemy import Engine


def create_retrieval_service(
    *, engine: Engine, query_embedder: QueryEmbedder | None
) -> RetrievalService:
    """Compose a public facade around explicitly supplied retrieval resources.

    The caller retains ownership of ``engine``. Construction only assembles the
    compatible internal executor; it does not connect, dispose resources, read
    configuration, or initialize providers.
    """
    from sciscope.retrieval._core import _RetrievalCore
    from sciscope.retrieval.service import (
        _PrivateCoreExecutor,
        _PrivateEmbedderBridge,
    )

    private_embedder = (
        _PrivateEmbedderBridge(query_embedder)
        if query_embedder is not None
        else None
    )
    core = _RetrievalCore(cast(Any, engine), private_embedder)
    return RetrievalService(executor=_PrivateCoreExecutor(core))
