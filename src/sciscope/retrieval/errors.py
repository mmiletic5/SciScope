"""Public sanitized errors for the versioned retrieval contract."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class RetrievalErrorCode(StrEnum):
    """Stable public error identifiers for retrieval operations."""

    INVALID_REQUEST = "INVALID_REQUEST"
    UNSUPPORTED_CONTRACT_VERSION = "UNSUPPORTED_CONTRACT_VERSION"
    CORPUS_NOT_LOADED = "CORPUS_NOT_LOADED"
    EMBEDDING_CONFIGURATION_MISMATCH = "EMBEDDING_CONFIGURATION_MISMATCH"
    EMBEDDING_UNAVAILABLE = "EMBEDDING_UNAVAILABLE"
    DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
    RETRIEVAL_INTERNAL_ERROR = "RETRIEVAL_INTERNAL_ERROR"


PUBLIC_MESSAGES: dict[RetrievalErrorCode, str] = {
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


@dataclass(frozen=True, slots=True)
class RetrievalException(Exception):
    """Typed retrieval error containing only public, sanitized information."""

    code: RetrievalErrorCode
    request_id: str | None
    retryable: bool
    public_message: str

    def __post_init__(self) -> None:
        """Expose the public message through standard exception display."""
        object.__setattr__(self, "args", (self.public_message,))
