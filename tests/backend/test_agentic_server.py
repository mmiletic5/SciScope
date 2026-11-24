"""Offline server-wiring tests for the agentic retrieval flag."""

from __future__ import annotations

import logging
from typing import Any

import pytest
from fastapi.testclient import TestClient

from sciscope.api import server
from sciscope.api.server import ServerConfigError, create_server_app
from sciscope.question_service.agentic_retrieval import (
    LOGGER_NAME,
    AgenticRetrieval,
    AgenticStats,
)
from sciscope.question_service.fakes import ComponentFakeRetrieval
from sciscope.question_service.retrieval_adapter import PublicRetrievalAdapter


@pytest.fixture(autouse=True)
def _capture(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger=LOGGER_NAME)


def stats(caplog: pytest.LogCaptureFixture) -> list[AgenticStats]:
    """Return the stats of every agentic log record."""
    return [
        record.agentic_stats  # type: ignore[attr-defined]
        for record in caplog.records
        if record.name == LOGGER_NAME
    ]


# Server wiring: flag off leaves the composition unchanged.


def _ask(app: Any, workflow: str) -> dict[str, Any]:
    response = TestClient(app).post(
        "/api/v2/questions",
        json={
            "workflow": workflow,
            "question": "Compare bee papers",
            "request_id": "req-agentic-1",
        },
    )
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


@pytest.mark.parametrize("env", [{}, {"SCISCOPE_AGENTIC_RETRIEVAL": "0"}])
def test_flag_off_keeps_the_default_composition(
    env: dict[str, str], caplog: pytest.LogCaptureFixture
) -> None:
    """No per-workflow wrapping and no agentic log line when off."""
    app = create_server_app(env)

    assert app.state.dependencies.workflow_retrievals is None
    _ask(app, "evidence_comparison")
    assert stats(caplog) == []


def test_invalid_flag_value_is_rejected_by_name_only() -> None:
    """Only 0 or 1; the message names the variable, never the value."""
    with pytest.raises(ServerConfigError) as raised:
        create_server_app({"SCISCOPE_AGENTIC_RETRIEVAL": "yes-secret"})

    assert "SCISCOPE_AGENTIC_RETRIEVAL" in str(raised.value)
    assert "yes-secret" not in str(raised.value)


def test_flag_on_fake_mode_wraps_only_comparison(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Fake mode simulates stage 1; the response equals the flag-off one."""
    on = create_server_app({"SCISCOPE_AGENTIC_RETRIEVAL": "1"})
    retrievals = on.state.dependencies.workflow_retrievals

    assert isinstance(retrievals["evidence_comparison"], AgenticRetrieval)
    assert isinstance(retrievals["research_question"], ComponentFakeRetrieval)
    assert _ask(on, "evidence_comparison") == _ask(
        create_server_app({}), "evidence_comparison"
    )
    (record,) = stats(caplog)
    assert (record.searches, record.merged_chunks, record.fallback) == (
        2,
        4,
        False,
    )
    _ask(on, "research_question")
    assert len(stats(caplog)) == 1


def test_flag_on_postgres_wraps_only_the_comparison_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The composed real-retrieval app wraps one adapter, offline."""

    class _Engine:
        def dispose(self) -> None:
            pass

    monkeypatch.setattr(
        server, "create_database_engine", lambda settings: _Engine()
    )
    app = create_server_app(
        {
            "RETRIEVAL_BACKEND": "postgres",
            "RETRIEVAL_MODE": "lexical",
            "DATABASE_URL": "postgresql://u:p@localhost/db",
            "SCISCOPE_AGENTIC_RETRIEVAL": "1",
        }
    )
    retrievals = app.state.dependencies.workflow_retrievals

    assert isinstance(retrievals["evidence_comparison"], AgenticRetrieval)
    for workflow in (
        "research_question",
        "conflicting_evidence",
        "research_gap",
    ):
        assert isinstance(retrievals[workflow], PublicRetrievalAdapter)
