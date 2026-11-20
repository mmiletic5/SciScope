"""Typed sanitized error behavior for private retrieval operations."""

from __future__ import annotations

from sqlalchemy.exc import DBAPIError, OperationalError

from sciscope.retrieval._core import _database_failure
from sciscope.retrieval._errors import RetrievalErrorCode


def test_transient_connection_errors_are_retryable_and_sanitized() -> None:
    """A connection outage maps to a stable retryable public code."""
    failure = _database_failure(
        OperationalError("connect", {}, Exception("password=hidden")),
        "request-1",
    )
    assert failure.code == RetrievalErrorCode.DATABASE_UNAVAILABLE
    assert failure.retryable
    assert "hidden" not in str(failure)
    assert failure.request_id == "request-1"


def test_unknown_database_errors_are_internal_and_not_retryable() -> None:
    """Non-transient SQL failures are not mislabeled as availability errors."""
    error = DBAPIError.instance(
        "statement", {}, Exception("internal-secret"), Exception
    )
    failure = _database_failure(error, "request-2")
    assert failure.code == RetrievalErrorCode.RETRIEVAL_INTERNAL_ERROR
    assert not failure.retryable
    assert "internal-secret" not in str(failure)
