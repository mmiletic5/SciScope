"""Sanitized internal errors for the private retrieval implementation."""

from __future__ import annotations

from enum import StrEnum


class RetrievalErrorCode(StrEnum):
    """Stable error identifiers used inside the retrieval core."""

    INVALID_REQUEST = "INVALID_REQUEST"
    UNSUPPORTED_CONTRACT_VERSION = "UNSUPPORTED_CONTRACT_VERSION"
    CORPUS_NOT_LOADED = "CORPUS_NOT_LOADED"
    EMBEDDING_CONFIGURATION_MISMATCH = "EMBEDDING_CONFIGURATION_MISMATCH"
    EMBEDDING_UNAVAILABLE = "EMBEDDING_UNAVAILABLE"
    DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
    RETRIEVAL_INTERNAL_ERROR = "RETRIEVAL_INTERNAL_ERROR"


_PUBLIC_MESSAGES = {
    RetrievalErrorCode.INVALID_REQUEST: "The retrieval request is invalid.",
    RetrievalErrorCode.UNSUPPORTED_CONTRACT_VERSION: (
        "The retrieval contract version is unsupported."
    ),
    RetrievalErrorCode.CORPUS_NOT_LOADED: "No active corpus is available.",
    RetrievalErrorCode.EMBEDDING_CONFIGURATION_MISMATCH: (
        "The query embedding is incompatible with the active corpus."
    ),
    RetrievalErrorCode.EMBEDDING_UNAVAILABLE: (
        "The query embedding service is temporarily unavailable."
    ),
    RetrievalErrorCode.DATABASE_UNAVAILABLE: (
        "The retrieval database is temporarily unavailable."
    ),
    RetrievalErrorCode.RETRIEVAL_INTERNAL_ERROR: (
        "Retrieval could not complete."
    ),
}


class RetrievalFailure(RuntimeError):
    """Sanitized retrieval failure without driver or provider details."""

    def __init__(
        self,
        code: RetrievalErrorCode,
        *,
        request_id: str | None = None,
        retryable: bool = False,
    ) -> None:
        """Create a stable failure using only its public code and message."""
        self.code = code
        self.request_id = request_id
        self.retryable = retryable
        self.public_message = _PUBLIC_MESSAGES[code]
        super().__init__(code.value)
