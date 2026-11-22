"""Sanitized internal errors for the private retrieval implementation."""

from __future__ import annotations

from sciscope.retrieval.errors import (
    PUBLIC_MESSAGES,
    RetrievalErrorCode,
    RetrievalException,
)

__all__ = ["RetrievalErrorCode", "RetrievalFailure"]


class RetrievalFailure(RetrievalException):
    """Sanitized retrieval failure without driver or provider details."""

    def __init__(
        self,
        code: RetrievalErrorCode,
        *,
        request_id: str | None = None,
        retryable: bool = False,
    ) -> None:
        """Create a stable failure using only its public code and message."""
        super().__init__(
            code=code,
            request_id=request_id,
            retryable=retryable,
            public_message=PUBLIC_MESSAGES[code],
        )
        object.__setattr__(self, "args", (code.value,))
