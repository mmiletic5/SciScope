"""Optional offline reranking interfaces and local MiniLM adapter."""

from __future__ import annotations

import hashlib
import importlib
import math
import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

from sciscope.retrieval._quality import (
    EvidenceCandidate,
    RankingResult,
    rank_evidence,
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_IMMUTABLE_REVISION = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True, slots=True)
class RerankerCandidate:
    """Only the stable identity and exact text needed by a cross encoder."""

    chunk_id: str
    text: str


class _CrossEncoderModel(Protocol):
    """Narrow runtime interface used by the optional adapter."""

    def predict(
        self, sentences: Sequence[tuple[str, str]], **kwargs: object
    ) -> object: ...


class Reranker(Protocol):
    """Score a fixed sequence of candidate identities for a query."""

    model_id: str
    model_revision: str
    model_sha256: str

    def rerank(
        self,
        query_text: str,
        candidates: Sequence[RerankerCandidate],
    ) -> Sequence[tuple[str, float]]: ...


class NoOpReranker:
    """Represent the production-safe baseline without changing base order."""

    model_id = "none"
    model_revision = "none"
    model_sha256 = "none"

    def rerank(
        self,
        query_text: str,
        candidates: Sequence[RerankerCandidate],
    ) -> Sequence[tuple[str, float]]:
        del query_text, candidates
        return ()


class DeterministicFakeReranker:
    """Return configured scores for offline deterministic tests."""

    model_id = "deterministic-fake"
    model_revision = "test-fixture-v1"
    model_sha256 = "0" * 64

    def __init__(self, scores: Mapping[str, float]) -> None:
        self._scores = dict(scores)
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def rerank(
        self,
        query_text: str,
        candidates: Sequence[RerankerCandidate],
    ) -> Sequence[tuple[str, float]]:
        ids = tuple(candidate.chunk_id for candidate in candidates)
        self.calls.append((query_text, ids))
        return [
            (chunk_id, self._scores[chunk_id])
            for chunk_id in ids
            if chunk_id in self._scores
        ]


def rank_with_reranker[CandidateT: EvidenceCandidate](
    results: Sequence[CandidateT],
    *,
    query_text: str,
    reranker: Reranker | None = None,
    max_per_doi: int | None = 2,
) -> RankingResult[CandidateT]:
    """Apply exact deduplication, optional score ordering, and DOI diversity.

    Args:
        results: Ordered Phase B candidates.
        query_text: Original query string supplied to the reranker.
        reranker: Optional score provider. ``None`` and ``NoOpReranker`` retain
            the Phase B order.
        max_per_doi: Diversity cap forwarded to the Phase C ranker.

    Returns:
        The final stable ranking with duplicate and diversity exclusions.

    Raises:
        ValueError: If the reranker output does not exactly score each
            deduplicated candidate once with a finite numeric score.
        Exception: A selected reranker's inference failures are propagated.
    """
    if reranker is None or isinstance(reranker, NoOpReranker):
        return rank_evidence(results, max_per_doi=max_per_doi)

    prepared = rank_evidence(results, max_per_doi=None)
    inputs = tuple(
        RerankerCandidate(candidate.hit.chunk_id, candidate.hit.text)
        for candidate in prepared.candidates
    )
    raw_scores = reranker.rerank(query_text, inputs)
    scores = _validate_output(inputs, raw_scores)
    ranked = rank_evidence(
        tuple(candidate.hit for candidate in prepared.candidates),
        max_per_doi=max_per_doi,
        reranker_scores=scores,
    )
    return RankingResult(
        candidates=ranked.candidates,
        exclusions=prepared.exclusions + ranked.exclusions,
    )


def _validate_output(
    candidates: Sequence[RerankerCandidate],
    output: Sequence[tuple[str, float]],
) -> dict[str, float]:
    expected = {candidate.chunk_id for candidate in candidates}
    result: dict[str, float] = {}
    for item in output:
        if not isinstance(item, tuple) or len(item) != 2:
            raise ValueError(
                "reranker output must contain (chunk_id, score) pairs"
            )
        chunk_id, value = item
        if not isinstance(chunk_id, str) or chunk_id not in expected:
            raise ValueError(
                "reranker output contains an invented candidate ID"
            )
        if chunk_id in result:
            raise ValueError("reranker output contains duplicate candidate IDs")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("reranker output scores must be finite numbers")
        score = float(value)
        if not math.isfinite(score):
            raise ValueError("reranker output scores must be finite numbers")
        result[chunk_id] = score
    if set(result) != expected:
        raise ValueError("reranker output is missing candidate IDs")
    return result


class MiniLMCrossEncoderReranker:
    """Load only a pinned local MiniLM checkpoint; never fetch model files."""

    model_id = "cross-encoder/ms-marco-MiniLM-L6-v2"

    def __init__(
        self,
        checkpoint_directory: Path,
        *,
        model_revision: str,
        expected_sha256: str,
        batch_size: int = 8,
    ) -> None:
        if not checkpoint_directory.is_dir():
            raise ValueError("checkpoint directory must already exist locally")
        if not _IMMUTABLE_REVISION.fullmatch(model_revision):
            raise ValueError(
                "model_revision must be a 40-character commit hash"
            )
        if not _SHA256.fullmatch(expected_sha256):
            raise ValueError("expected_sha256 must be lowercase SHA-256")
        if isinstance(batch_size, bool) or not 1 <= batch_size <= 64:
            raise ValueError("batch_size must be from 1 to 64")
        actual_sha256 = _directory_sha256(checkpoint_directory)
        if actual_sha256 != expected_sha256:
            raise ValueError("checkpoint SHA-256 does not match")
        self.model_revision = model_revision
        self.model_sha256 = actual_sha256
        self._checkpoint_directory = checkpoint_directory
        self._batch_size = batch_size
        self._model: _CrossEncoderModel | None = None
        self._cold_start_ms: float | None = None

    @property
    def cold_start_ms(self) -> float | None:
        """Return the observed model load duration, if the model was loaded."""
        return self._cold_start_ms

    def rerank(
        self,
        query_text: str,
        candidates: Sequence[RerankerCandidate],
    ) -> Sequence[tuple[str, float]]:
        if not candidates:
            return ()
        model = self._load_model()
        pairs = [(query_text, candidate.text) for candidate in candidates]
        values = cast(
            Sequence[float],
            model.predict(
                pairs,
                batch_size=self._batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
            ),
        )
        if len(values) != len(candidates):
            raise ValueError("local model returned an unexpected score count")
        return [
            (candidate.chunk_id, float(score))
            for candidate, score in zip(candidates, values, strict=True)
        ]

    def _load_model(self) -> _CrossEncoderModel:
        if self._model is not None:
            return self._model
        try:
            module = importlib.import_module("sentence_transformers")
        except ImportError as error:
            raise RuntimeError(
                "sentence-transformers is required for the optional "
                "local reranker"
            ) from error
        started = time.perf_counter()
        cross_encoder = cast(Any, module).CrossEncoder
        self._model = cast(
            _CrossEncoderModel,
            cross_encoder(
                str(self._checkpoint_directory),
                device="cpu",
                revision=self.model_revision,
                local_files_only=True,
                trust_remote_code=False,
            ),
        )
        self._cold_start_ms = (time.perf_counter() - started) * 1000
        return self._model


def _directory_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(path.rglob("*"))
    regular_files = [item for item in files if item.is_file()]
    if not regular_files or any(item.is_symlink() for item in files):
        raise ValueError("checkpoint must contain regular local files only")
    for item in regular_files:
        relative = item.relative_to(path).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        with item.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    return digest.hexdigest()
