"""Public, driver-independent contracts for versioned retrieval."""

from sciscope.retrieval.contracts import (
    Author,
    CorpusIdentity,
    EmbeddingConfig,
    NormalizedType,
    PaperMetadata,
    RankingOptions,
    RetrievalFilters,
    RetrievalMetadata,
    RetrievalMode,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
    RetrievalScore,
)
from sciscope.retrieval.errors import RetrievalErrorCode, RetrievalException
from sciscope.retrieval.service import QueryEmbedder, RetrievalService

__all__ = [
    "Author",
    "CorpusIdentity",
    "EmbeddingConfig",
    "NormalizedType",
    "PaperMetadata",
    "QueryEmbedder",
    "RankingOptions",
    "RetrievalErrorCode",
    "RetrievalException",
    "RetrievalFilters",
    "RetrievalMetadata",
    "RetrievalMode",
    "RetrievalRequest",
    "RetrievalResponse",
    "RetrievalResult",
    "RetrievalScore",
    "RetrievalService",
]
