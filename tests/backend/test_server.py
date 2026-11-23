"""Offline tests for the environment-configured server entry point."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from sciscope.api import server
from sciscope.api.server import ServerConfigError, create_server_app

VITE = "http://localhost:5173"
SECRET = "sk-test-SECRET-value-123"
DB_SECRET = "postgresql://user:dbpass-SECRET@localhost/db"


class _Engine:
    def __init__(self) -> None:
        self.disposed = 0

    def dispose(self) -> None:
        self.disposed += 1


def _client(env: dict[str, str] | None = None) -> TestClient:
    return TestClient(
        create_server_app(env or {}), raise_server_exceptions=False
    )


def test_defaults_run_fake_without_database_or_keys() -> None:
    """Serve a valid v2 answer with zero configuration."""
    response = _client().post(
        "/api/v2/questions",
        json={
            "workflow": "research_question",
            "question": "Why do bees dance?",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["metadata"] == {
        "retrieval": {
            "configured_origin": "synthetic",
            "executed": True,
            "is_test_data": True,
        },
        "answer_provider": {
            "configured_origin": "fake",
            "executed": True,
            "is_test_data": True,
        },
    }


def test_health_reports_origins_and_provider_workflows() -> None:
    """List the fake provider's workflows (all four) and configured origins."""
    response = _client().get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "api_versions": ["v1", "v2"],
        "workflows": [
            "research_question",
            "evidence_comparison",
            "conflicting_evidence",
            "research_gap",
        ],
        "components": {
            "retrieval": {"configured_origin": "synthetic"},
            "answer_provider": {"configured_origin": "fake"},
        },
    }


def test_cors_preflight_allows_vite_origin_only() -> None:
    """Allow the Vite origin and reject a foreign origin."""
    client = _client()
    headers = {
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
    }

    allowed = client.options(
        "/api/v2/questions", headers={"Origin": VITE, **headers}
    )
    denied = client.options(
        "/api/v2/questions",
        headers={"Origin": "http://evil.example", **headers},
    )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == VITE
    assert denied.status_code == 400
    assert "access-control-allow-origin" not in denied.headers


def test_cors_origins_are_configurable() -> None:
    """Honor the CORS_ORIGINS allowlist."""
    client = _client({"CORS_ORIGINS": "http://example.test:3000"})
    response = client.get(
        "/api/health", headers={"Origin": "http://example.test:3000"}
    )
    assert response.headers["access-control-allow-origin"] == (
        "http://example.test:3000"
    )


@pytest.mark.parametrize(
    ("env", "name"),
    [
        ({"AI_PROVIDER": "bogus"}, "AI_PROVIDER"),
        ({"RETRIEVAL_BACKEND": "mongo"}, "RETRIEVAL_BACKEND"),
        ({"RETRIEVAL_MODE": "dense"}, "RETRIEVAL_MODE"),
        ({"RETRIEVAL_BACKEND": "postgres"}, "DATABASE_URL"),
        (
            {"RETRIEVAL_BACKEND": "postgres", "RETRIEVAL_MODE": "lexical"},
            "DATABASE_URL",
        ),
        (
            {"RETRIEVAL_BACKEND": "postgres", "DATABASE_URL": DB_SECRET},
            "OPENAI_API_KEY",
        ),
        ({"AI_PROVIDER": "openai"}, "OPENAI_API_KEY"),
        (
            {"AI_PROVIDER": "openai", "OPENAI_API_KEY": SECRET},
            "OPENAI_ANSWER_MODEL",
        ),
        (
            {
                "AI_PROVIDER": "openai",
                "OPENAI_API_KEY": SECRET,
                "OPENAI_ANSWER_MODEL": "m",
                "OPENAI_TIMEOUT_SECONDS": "abc",
            },
            "OPENAI_TIMEOUT_SECONDS",
        ),
        (
            {
                "AI_PROVIDER": "openai",
                "OPENAI_API_KEY": SECRET,
                "OPENAI_ANSWER_MODEL": "m",
                "OPENAI_BASE_URL": "http://insecure.example",
            },
            "OPENAI_BASE_URL",
        ),
        ({"CORS_ORIGINS": "*"}, "CORS_ORIGINS"),
    ],
)
def test_invalid_configuration_fails_fast_without_secrets(
    env: dict[str, str], name: str
) -> None:
    """Name the offending variable without echoing any secret."""
    with pytest.raises(ServerConfigError) as raised:
        create_server_app(env)

    message = str(raised.value)
    assert name in message
    for secret in (SECRET, DB_SECRET, "dbpass-SECRET"):
        assert secret not in message
    assert raised.value.__cause__ is None or secret not in repr(
        raised.value.__cause__
    )


def test_hybrid_without_key_never_falls_back_to_lexical() -> None:
    """Fail at startup when hybrid lacks an API key."""
    with pytest.raises(ServerConfigError, match="RETRIEVAL_MODE=hybrid"):
        create_server_app(
            {"RETRIEVAL_BACKEND": "postgres", "DATABASE_URL": DB_SECRET}
        )


def test_invalid_database_url_message_has_no_url() -> None:
    """Reject a bad database URL without echoing it."""
    with pytest.raises(ServerConfigError) as raised:
        create_server_app(
            {
                "RETRIEVAL_BACKEND": "postgres",
                "DATABASE_URL": "mysql://user:dbpass-SECRET@host/db",
            }
        )
    assert "dbpass-SECRET" not in str(raised.value)


def test_postgres_lexical_owns_engine_and_disposes_on_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dispose the owned engine when the app shuts down."""
    engine = _Engine()
    monkeypatch.setattr(
        server, "create_database_engine", lambda settings: engine
    )
    app = create_server_app(
        {
            "RETRIEVAL_BACKEND": "postgres",
            "RETRIEVAL_MODE": "lexical",
            "DATABASE_URL": DB_SECRET,
        }
    )

    with TestClient(app) as client:
        health = client.get("/api/health").json()
        assert health["components"]["retrieval"]["configured_origin"] == "real"
        assert engine.disposed == 0

    assert engine.disposed == 1


def test_postgres_hybrid_builds_with_key_without_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Build hybrid retrieval offline and dispose on shutdown."""
    engine = _Engine()
    monkeypatch.setattr(
        server, "create_database_engine", lambda settings: engine
    )
    app = create_server_app(
        {
            "RETRIEVAL_BACKEND": "postgres",
            "DATABASE_URL": DB_SECRET,
            "OPENAI_API_KEY": SECRET,
        }
    )

    with TestClient(app):
        pass

    assert engine.disposed == 1


def test_openai_provider_selected_reports_real_origin() -> None:
    """Report the real provider origin without leaking the key."""
    app = create_server_app(
        {
            "AI_PROVIDER": "openai",
            "OPENAI_API_KEY": SECRET,
            "OPENAI_ANSWER_MODEL": "test-model",
        }
    )
    body = TestClient(app).get("/api/health").json()
    assert body["components"]["answer_provider"]["configured_origin"] == "real"
    assert SECRET not in str(body)
