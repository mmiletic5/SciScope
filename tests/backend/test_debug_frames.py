"""SCISCOPE_DEBUG_FRAMES logs only frame locations and exception class names."""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from sciscope.api.app import create_app
from sciscope.question_service.contracts import (
    ComponentMetadata,
    QuestionMetadata,
)
from sciscope.question_service.fakes import ComponentFakeAnswerProvider
from sciscope.question_service.validation import ResponseContractFailure

_SECRET_QUESTION = "SECRET-QUESTION-TEXT about bees"
_SECRET_MESSAGE = "SECRET-EXCEPTION-MESSAGE"


class _FailingRetrieval:
    def __init__(self, error: Exception) -> None:
        self._error = error

    def retrieve(self, question: str, request_id: str) -> object:
        secret_local = "SECRET-LOCAL-VALUE"  # noqa: F841
        raise self._error


def _client(error: Exception) -> TestClient:
    metadata = QuestionMetadata(
        retrieval=ComponentMetadata("fake", executed=False, is_test_data=True),
        answer_provider=ComponentMetadata(
            "fake", executed=False, is_test_data=True
        ),
    )
    app = create_app(
        retrieval=_FailingRetrieval(error),
        provider=ComponentFakeAnswerProvider(),
        v2_metadata=metadata,
    )
    return TestClient(app, raise_server_exceptions=False)


def _post(client: TestClient) -> int:
    return client.post(
        "/api/v2/questions",
        json={"workflow": "research_question", "question": _SECRET_QUESTION},
    ).status_code


@pytest.mark.parametrize(
    ("error", "class_name", "status"),
    [
        (ResponseContractFailure(), "ResponseContractFailure", 500),
        (RuntimeError(_SECRET_MESSAGE), "RuntimeError", 500),
    ],
)
def test_enabled_logs_only_frames_and_class_name(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    error: Exception,
    class_name: str,
    status: int,
) -> None:
    """Enabled output has frame lines and the class; no content or locals."""
    monkeypatch.setenv("SCISCOPE_DEBUG_FRAMES", "1")
    with caplog.at_level(logging.ERROR, logger="sciscope.debug_frames"):
        assert _post(_client(error)) == status

    records = [r for r in caplog.records if r.name == "sciscope.debug_frames"]
    assert len(records) == 1
    text = records[0].getMessage()
    assert text.splitlines()[0] == f"debug_frames {class_name}"
    for line in text.splitlines()[1:]:
        path_line, _, function = line.rpartition(" ")
        assert function.isidentifier() or function.startswith("<")
        assert path_line.rsplit(":", 1)[1].isdigit()
    for secret in (_SECRET_QUESTION, _SECRET_MESSAGE, "SECRET-LOCAL-VALUE"):
        assert secret not in text
        assert secret not in caplog.text
    assert records[0].exc_info is None


def test_disabled_by_default_logs_nothing(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Without the opt-in variable nothing is logged."""
    monkeypatch.delenv("SCISCOPE_DEBUG_FRAMES", raising=False)
    with caplog.at_level(logging.DEBUG):
        assert _post(_client(ResponseContractFailure())) == 500

    assert not [r for r in caplog.records if r.name == "sciscope.debug_frames"]
