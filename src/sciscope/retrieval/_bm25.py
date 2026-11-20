"""Minimal in-memory BM25Okapi adapter for active corpus chunks."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from rank_bm25 import BM25Okapi  # type: ignore[import-untyped]


@dataclass(frozen=True, slots=True)
class BM25Document:
    """Stable source chunk identity and exact text to index."""

    chunk_id: str
    text: str


@dataclass(frozen=True, slots=True)
class BM25Hit:
    """One BM25-ranked chunk and its raw Okapi score."""

    chunk_id: str
    score: float


class BM25OkapiRetriever:
    """Build and query a small in-memory rank-bm25 corpus index.

    Token boundaries use standard whitespace splitting and case folding; the
    BM25 scoring implementation is provided by ``rank-bm25``.
    """

    def __init__(self, documents: Sequence[BM25Document]) -> None:
        if len({item.chunk_id for item in documents}) != len(documents):
            raise ValueError("BM25 documents must have unique chunk IDs")
        if any(
            not isinstance(item.chunk_id, str)
            or not item.chunk_id
            or not isinstance(item.text, str)
            or not item.text.strip()
            for item in documents
        ):
            raise ValueError("BM25 documents require nonempty IDs and text")
        self._documents = tuple(documents)
        self._tokens = tuple(
            tuple(item.text.casefold().split()) for item in self._documents
        )
        self._model = BM25Okapi(self._tokens) if self._tokens else None

    def search(self, query: str, *, limit: int) -> tuple[BM25Hit, ...]:
        """Return deterministically ordered candidates containing query terms.

        Args:
            query: Exact query text, tokenized by whitespace boundaries.
            limit: Maximum number of returned candidates.

        Returns:
            Matching chunks sorted by BM25 score descending and chunk ID.

        Raises:
            ValueError: If query or limit has the wrong type or limit is
                outside the positive integer range.
        """
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        if not isinstance(query, str):
            raise ValueError("query must be a string")
        terms = tuple(dict.fromkeys(query.casefold().split()))
        if not terms or self._model is None:
            return ()

        scores = self._model.get_scores(terms)
        candidates: list[BM25Hit] = []
        for index, raw_score in enumerate(scores):
            if not any(term in self._tokens[index] for term in terms):
                continue
            score = float(raw_score)
            if not math.isfinite(score):
                raise ValueError("BM25 returned a non-finite score")
            candidates.append(BM25Hit(self._documents[index].chunk_id, score))
        candidates.sort(key=lambda hit: (-hit.score, hit.chunk_id))
        return tuple(candidates[:limit])
