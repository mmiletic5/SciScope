"""Environment-configured server entry point for the MVP backend.

Run with ``python -m sciscope.api.server`` or
``uvicorn sciscope.api.server:create_server_app --factory``.

Configuration comes only from environment variables and is validated before
the application is built. Error messages name variables, never their values.
There is no silent fallback between providers or retrieval modes.
"""

from __future__ import annotations

import logging
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, cast

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from sciscope.api.app import create_app
from sciscope.api.composition import create_application
from sciscope.api.http_models_v2 import (
    HealthComponent,
    HealthComponents,
    HealthResponse,
)
from sciscope.database.config import DatabaseSettings
from sciscope.database.session import create_database_engine
from sciscope.embedding.config import EmbeddingConfig, EmbeddingConfigError
from sciscope.embedding.openai_client import (
    OpenAIConnection,
    OpenAIEmbedder,
    UrllibTransport,
    embeddings_url,
    read_api_key,
    read_base_url,
)
from sciscope.embedding.query_embedder import OpenAIQueryEmbedder
from sciscope.question_service.agentic_retrieval import (
    AGENTIC_FLAG_ENV,
    LOGGER_NAME,
    wrap_agentic,
)
from sciscope.question_service.contracts import (
    WORKFLOWS,
    ComponentMetadata,
    QuestionMetadata,
    RetrievalService,
    Workflow,
)
from sciscope.question_service.fakes import (
    ComponentFakeAnswerProvider,
    ComponentFakeRetrieval,
)
from sciscope.question_service.openai_provider import (
    DEFAULT_TIMEOUT_SECONDS,
    AnswerProviderConfigError,
    OpenAIAnswerProvider,
)
from sciscope.question_service.retrieval_adapter import (
    RetrievalAdapterSettings,
)
from sciscope.retrieval import QueryEmbedder, RankingOptions

DEFAULT_CORS_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000

_RETRIEVAL_CONTRACT_VERSION = "retrieval.v2"
_CANDIDATE_POOL_SIZE = 50
WORKFLOW_TOP_K: Mapping[Workflow, int] = {
    "research_question": 5,
    "evidence_comparison": 10,
    "conflicting_evidence": 10,
    "research_gap": 10,
}
"""Server-owned retrieval ``top_k`` per workflow (contract section 6)."""

AiProvider = Literal["fake", "openai"]
RetrievalBackend = Literal["fake", "postgres"]
ServerRetrievalMode = Literal["hybrid", "lexical"]


class ServerConfigError(ValueError):
    """Invalid server configuration; the message never contains a value."""


@dataclass(frozen=True, slots=True)
class ServerConfig:
    """Validated server configuration. Secrets are held, never printed."""

    ai_provider: AiProvider
    retrieval_backend: RetrievalBackend
    retrieval_mode: ServerRetrievalMode
    cors_origins: tuple[str, ...]
    database_settings: DatabaseSettings | None
    openai_api_key: str | None
    openai_base_url: str | None
    openai_answer_model: str | None
    openai_timeout_seconds: float
    agentic_retrieval: bool = False

    def __repr__(self) -> str:
        """Describe non-secret selections only."""
        return (
            f"ServerConfig(ai_provider={self.ai_provider!r}, "
            f"retrieval_backend={self.retrieval_backend!r}, "
            f"retrieval_mode={self.retrieval_mode!r}, "
            f"agentic_retrieval={self.agentic_retrieval!r})"
        )

    @classmethod
    def from_environment(
        cls, environ: Mapping[str, str] | None = None
    ) -> ServerConfig:
        """Read and validate configuration.

        Args:
            environ: Mapping to read; defaults to ``os.environ``.

        Returns:
            The validated configuration.

        Raises:
            ServerConfigError: If any setting is missing or invalid.
        """
        env = os.environ if environ is None else environ
        ai_provider = cast(
            AiProvider, _choice(env, "AI_PROVIDER", ("fake", "openai"), "fake")
        )
        backend = cast(
            RetrievalBackend,
            _choice(env, "RETRIEVAL_BACKEND", ("fake", "postgres"), "fake"),
        )
        mode = cast(
            ServerRetrievalMode,
            _choice(env, "RETRIEVAL_MODE", ("hybrid", "lexical"), "hybrid"),
        )
        cors = _cors_origins(env)
        agentic = _choice(env, AGENTIC_FLAG_ENV, ("0", "1"), "0") == "1"

        database_settings: DatabaseSettings | None = None
        if backend == "postgres":
            try:
                database_settings = DatabaseSettings.from_environment(env)
            except ValueError as error:
                raise ServerConfigError(
                    "DATABASE_URL is missing or invalid for "
                    "RETRIEVAL_BACKEND=postgres"
                ) from error

        needs_key = ai_provider == "openai" or (
            backend == "postgres" and mode == "hybrid"
        )
        api_key: str | None = None
        base_url: str | None = None
        if needs_key:
            reason = (
                "AI_PROVIDER=openai"
                if ai_provider == "openai"
                else "RETRIEVAL_MODE=hybrid"
            )
            try:
                api_key = read_api_key(env)
            except EmbeddingConfigError as error:
                raise ServerConfigError(
                    f"OPENAI_API_KEY is missing or invalid; required by "
                    f"{reason}"
                ) from error
            if "OPENAI_BASE_URL" in env:
                try:
                    base_url, _ = read_base_url(env)
                except EmbeddingConfigError as error:
                    raise ServerConfigError(
                        "OPENAI_BASE_URL is invalid"
                    ) from error

        model: str | None = None
        timeout = DEFAULT_TIMEOUT_SECONDS
        if ai_provider == "openai":
            model = env.get("OPENAI_ANSWER_MODEL", "").strip()
            if not model:
                raise ServerConfigError(
                    "OPENAI_ANSWER_MODEL must be set for AI_PROVIDER=openai"
                )
            raw_timeout = env.get("OPENAI_TIMEOUT_SECONDS")
            if raw_timeout is not None:
                try:
                    timeout = float(raw_timeout)
                except ValueError:
                    raise ServerConfigError(
                        "OPENAI_TIMEOUT_SECONDS must be a number"
                    ) from None
        return cls(
            ai_provider=ai_provider,
            retrieval_backend=backend,
            retrieval_mode=mode,
            cors_origins=cors,
            database_settings=database_settings,
            openai_api_key=api_key,
            openai_base_url=base_url,
            openai_answer_model=model,
            openai_timeout_seconds=timeout,
            agentic_retrieval=agentic,
        )


def _choice(
    env: Mapping[str, str],
    name: str,
    allowed: tuple[str, ...],
    default: str,
) -> str:
    """Return a validated enumerated setting without echoing a bad value."""
    value = env.get(name)
    if value is None or not value.strip():
        return default
    value = value.strip()
    if value not in allowed:
        raise ServerConfigError(f"{name} must be one of: {', '.join(allowed)}")
    return value


def _cors_origins(env: Mapping[str, str]) -> tuple[str, ...]:
    """Parse the comma-separated CORS allowlist."""
    raw = env.get("CORS_ORIGINS")
    if raw is None or not raw.strip():
        return DEFAULT_CORS_ORIGINS
    origins = tuple(item.strip() for item in raw.split(",") if item.strip())
    if any("*" in origin for origin in origins):
        raise ServerConfigError("CORS_ORIGINS must list explicit origins")
    return origins


ServerProvider = ComponentFakeAnswerProvider | OpenAIAnswerProvider


def _build_provider(config: ServerConfig) -> ServerProvider:
    """Build the configured answer provider."""
    if config.ai_provider == "fake":
        return ComponentFakeAnswerProvider()
    assert config.openai_api_key is not None
    assert config.openai_answer_model is not None
    try:
        return OpenAIAnswerProvider(
            api_key=config.openai_api_key,
            model=config.openai_answer_model,
            base_url=config.openai_base_url or "https://api.openai.com",
            timeout_seconds=config.openai_timeout_seconds,
        )
    except AnswerProviderConfigError as error:
        raise ServerConfigError(
            f"OpenAI answer provider configuration is invalid ({error.code})"
        ) from None


def _build_query_embedder(config: ServerConfig) -> QueryEmbedder:
    """Build the OpenAI query embedder for hybrid retrieval."""
    assert config.openai_api_key is not None
    base, custom = read_base_url(
        {"OPENAI_BASE_URL": config.openai_base_url}
        if config.openai_base_url
        else {}
    )
    embedding_config = EmbeddingConfig()
    transport = UrllibTransport(
        OpenAIConnection(config.openai_api_key, embeddings_url(base), custom)
    )
    return cast(
        QueryEmbedder,
        OpenAIQueryEmbedder(
            OpenAIEmbedder(embedding_config, transport), embedding_config
        ),
    )


def retrieval_settings_for(
    workflow: Workflow,
    mode: ServerRetrievalMode,
    retrieval_metadata: ComponentMetadata,
) -> RetrievalAdapterSettings:
    """Return the server-owned retrieval profile of one workflow.

    Args:
        workflow: Workflow served by the profile.
        mode: Configured retrieval mode.
        retrieval_metadata: Configured retrieval component metadata.

    Returns:
        ``retrieval.v2`` settings with the workflow's ``top_k``. The candidate
        pool applies in hybrid mode only, because the retrieval contract
        accepts ranking options only there.
    """
    return RetrievalAdapterSettings(
        contract_version=_RETRIEVAL_CONTRACT_VERSION,
        mode=mode,
        top_k=WORKFLOW_TOP_K[workflow],
        filters=None,
        ranking=(
            RankingOptions(candidate_pool_size=_CANDIDATE_POOL_SIZE)
            if mode == "hybrid"
            else None
        ),
        retrieval_metadata=retrieval_metadata,
    )


def _health_route(
    app: FastAPI,
    metadata: QuestionMetadata,
    workflows: tuple[Workflow, ...],
) -> None:
    """Install ``GET /api/health``: static, no secrets, no I/O."""
    body = HealthResponse(
        status="ok",
        api_versions=["v1", "v2"],
        workflows=[workflow for workflow in WORKFLOWS if workflow in workflows],
        components=HealthComponents(
            retrieval=HealthComponent(
                configured_origin=metadata.retrieval.configured_origin
            ),
            answer_provider=HealthComponent(
                configured_origin=metadata.answer_provider.configured_origin
            ),
        ),
    ).model_dump()

    @app.get("/api/health")
    def health() -> dict[str, object]:
        """Report liveness, enabled workflows and configured origins."""
        return body


def _add_cors(app: FastAPI, origins: tuple[str, ...]) -> None:
    """Allow only the configured browser origins."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(origins),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )


def create_server_app(
    environ: Mapping[str, str] | None = None,
) -> FastAPI:
    """Build the configured application (uvicorn ``--factory`` target).

    Args:
        environ: Mapping to read; defaults to ``os.environ``.

    Returns:
        The FastAPI application. With ``RETRIEVAL_BACKEND=postgres`` the
        application owns its database engine and disposes it on shutdown.

    Raises:
        ServerConfigError: If configuration is invalid.
    """
    config = ServerConfig.from_environment(environ)
    provider = _build_provider(config)
    provider_metadata = (
        ComponentMetadata("fake", executed=False, is_test_data=True)
        if config.ai_provider == "fake"
        else ComponentMetadata("real", executed=False, is_test_data=False)
    )
    if config.retrieval_backend == "fake":
        metadata = QuestionMetadata(
            retrieval=ComponentMetadata(
                "synthetic", executed=False, is_test_data=True
            ),
            answer_provider=provider_metadata,
        )
        fake_retrieval = cast(RetrievalService, ComponentFakeRetrieval())
        app = create_app(
            retrieval=fake_retrieval,
            provider=provider,
            v2_metadata=metadata,
            workflow_retrievals=(
                wrap_agentic(
                    {workflow: fake_retrieval for workflow in WORKFLOWS},
                    provider,
                )
                if config.agentic_retrieval
                else None
            ),
        )
    else:
        assert config.database_settings is not None
        settings = config.database_settings
        retrieval_metadata = ComponentMetadata(
            "real", executed=False, is_test_data=False
        )
        metadata = QuestionMetadata(
            retrieval=retrieval_metadata, answer_provider=provider_metadata
        )
        embedder = (
            _build_query_embedder(config)
            if config.retrieval_mode == "hybrid"
            else None
        )
        workflow_settings = {
            workflow: retrieval_settings_for(
                workflow, config.retrieval_mode, retrieval_metadata
            )
            for workflow in WORKFLOWS
        }
        composed = create_application(
            engine=None,
            engine_factory=lambda: create_database_engine(settings),
            query_embedder=embedder,
            retrieval_settings=workflow_settings["research_question"],
            provider=provider,
            metadata=metadata,
            workflow_retrieval_settings=workflow_settings,
            agentic_planner=provider if config.agentic_retrieval else None,
        )
        app = composed.app
    _health_route(app, metadata, provider.supported_workflows)
    _add_cors(app, config.cors_origins)
    if config.agentic_retrieval:
        _enable_agentic_log()
    return app


def _enable_agentic_log() -> None:
    """Send the content-free agentic retrieval lines to stderr, once."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
        logger.addHandler(handler)


def main() -> None:
    """Validate configuration, then serve with uvicorn."""
    import uvicorn

    host = os.environ.get("HOST", DEFAULT_HOST)
    try:
        port = int(os.environ.get("PORT", str(DEFAULT_PORT)))
    except ValueError:
        raise SystemExit("PORT must be an integer") from None
    try:
        app = create_server_app()
    except ServerConfigError as error:
        raise SystemExit(f"Configuration error: {error}") from None
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
