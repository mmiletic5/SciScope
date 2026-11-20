"""Create provenance-bound query vectors using the frozen embedding cache."""

from __future__ import annotations

import hashlib
import json
import math
import os
import struct
import tempfile
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from sciscope.chunking.counter import TokenCounter
from sciscope.embedding.cache import (
    CacheEntry,
    EmbeddingCache,
    cache_key,
    encode_entry,
)
from sciscope.embedding.config import (
    CACHE_FORMAT_VERSION,
    DEFAULT_DIMENSIONS,
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
    EmbeddingConfig,
)
from sciscope.embedding.provider import Embedder
from sciscope.embedding.store import pack_vector

_REQUIRED_EXPECTED_FIELDS = {
    "dataset_version",
    "dataset_sha256",
    "corpus_version",
    "corpus_sha256",
    "partition",
    "partition_sha256",
    "embedding_set_id",
}


@dataclass(frozen=True, slots=True)
class QueryGenerationResult:
    """Usage and identity metadata without query text or vector values."""

    manifest: Mapping[str, Any]
    manifest_sha256: str
    vector_count: int
    api_calls: int
    attempts: int
    prompt_tokens: int
    total_tokens: int
    cost_usd: float

    def to_dict(self) -> dict[str, Any]:
        """Return a text-free generation record suitable for protected logs."""
        return {
            "manifest_sha256": self.manifest_sha256,
            "vector_count": self.vector_count,
            "api_calls": self.api_calls,
            "attempts": self.attempts,
            "prompt_tokens": self.prompt_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
        }


def generate_query_cache(
    questions: Sequence[Mapping[str, Any]],
    *,
    cache_directory: Path,
    manifest_path: Path,
    expected: Mapping[str, Any],
    config: EmbeddingConfig,
    counter: TokenCounter,
    embedder_factory: Callable[[], Embedder],
    utc_now: Callable[[], datetime],
) -> QueryGenerationResult:
    """Generate exact normalized queries and atomically publish their manifest.

    A compatible existing cache must be verified by
    ``verify_query_cache_manifest`` before this writer is called. This writer
    never overwrites a manifest or reuses unmanifested entries.

    Args:
        questions: The explicitly authorized question cohort only.
        cache_directory: Cohort-specific cache directory.
        manifest_path: Query-cache manifest path inside that directory.
        expected: Frozen dataset, partition, corpus, and embedding-set IDs.
        config: Approved query embedding configuration.
        counter: Existing token estimator used to enforce per-input/batch caps.
        embedder_factory: Factory for the configured OpenAI embedding client.
        utc_now: UTC-aware clock used for provenance timestamps.

    Returns:
        A query-cache manifest and provider usage summary with no question text.

    Raises:
        ValueError: On identity, input, cache, or configuration mismatch.
    """
    if set(expected) != _REQUIRED_EXPECTED_FIELDS:
        raise ValueError("query-cache expected identity fields are invalid")
    if (
        config.provider != DEFAULT_PROVIDER
        or config.model != DEFAULT_MODEL
        or config.dimensions != DEFAULT_DIMENSIONS
        or config.query_prefix != ""
        or config.passage_prefix != ""
    ):
        raise ValueError("query embedding configuration is incompatible")
    if manifest_path.parent.resolve() != cache_directory.resolve():
        raise ValueError(
            "query-cache manifest must be inside its cache directory"
        )
    if manifest_path.exists():
        raise ValueError("query-cache manifest already exists")
    if cache_directory.exists() and any(
        path.suffix == ".entry" for path in cache_directory.iterdir()
    ):
        raise ValueError("unmanifested query-cache entries already exist")

    jobs = _prepare_jobs(questions, config, counter)
    if not jobs:
        raise ValueError("query-cache population is empty")

    batches = _batches(jobs, config)
    cache = EmbeddingCache(cache_directory)
    records: list[dict[str, Any]] = []
    prompt_tokens = total_tokens = attempts = 0
    embedder = embedder_factory()
    if (
        embedder.provider_id != DEFAULT_PROVIDER
        or embedder.model != DEFAULT_MODEL
        or embedder.dimensions != DEFAULT_DIMENSIONS
    ):
        raise ValueError("query embedder identity is incompatible")

    for batch in batches:
        result = embedder.embed_queries([job["query"] for job in batch])
        if len(result.vectors) != len(batch):
            raise ValueError("query embedding response count mismatch")
        timestamp = _timestamp(utc_now())
        embedded_on = timestamp[:10]
        vectors: list[bytes] = []
        for vector in result.vectors:
            if len(vector) != DEFAULT_DIMENSIONS:
                raise ValueError("query embedding response dimensions mismatch")
            vector_bytes = pack_vector(vector)
            norm = math.sqrt(
                sum(
                    value * value
                    for (value,) in struct.iter_unpack("<f", vector_bytes)
                )
            )
            if not math.isfinite(norm) or norm <= 0 or abs(norm - 1.0) > 0.01:
                raise ValueError("query embedding norm is incompatible")
            vectors.append(vector_bytes)

        batch_id = hashlib.sha256(
            "\n".join(sorted(job["input_sha256"] for job in batch)).encode(
                "ascii"
            )
        ).hexdigest()
        estimated_batch_tokens = sum(job["estimated_tokens"] for job in batch)
        pending: list[CacheEntry] = []
        for job, vector_bytes in zip(batch, vectors, strict=True):
            pending.append(
                CacheEntry(
                    CACHE_FORMAT_VERSION,
                    DEFAULT_MODEL,
                    DEFAULT_DIMENSIONS,
                    job["input_sha256"],
                    hashlib.sha256(vector_bytes).hexdigest(),
                    job["estimated_tokens"],
                    counter.counter_id,
                    embedded_on,
                    batch_id,
                    len(batch),
                    estimated_batch_tokens,
                    result.usage.prompt_tokens,
                    result.usage.total_tokens,
                    vector_bytes,
                )
            )
        cache.put_batch(pending)
        for job, entry in zip(batch, pending, strict=True):
            key = cache_key(
                DEFAULT_MODEL, DEFAULT_DIMENSIONS, job["input_sha256"]
            )
            encoded = encode_entry(entry)
            records.append(
                {
                    "question_id": job["question_id"],
                    "query_sha256": job["query_sha256"],
                    "provider_input_sha256": job["input_sha256"],
                    "cache_key": key,
                    "entry_path": f"{key}.entry",
                    "entry_sha256": hashlib.sha256(encoded).hexdigest(),
                    "vector_sha256": entry.vector_sha256,
                    "provenance": "openai-response-cache",
                    "generated_at_utc": timestamp,
                }
            )
        prompt_tokens += result.usage.prompt_tokens
        total_tokens += result.usage.total_tokens
        attempts += result.attempts

    manifest = {
        "manifest_version": "phase-d-query-cache-v1",
        "dataset_version": expected["dataset_version"],
        "dataset_sha256": expected["dataset_sha256"],
        "corpus_version": expected["corpus_version"],
        "corpus_sha256": expected["corpus_sha256"],
        "partition": expected["partition"],
        "partition_sha256": expected["partition_sha256"],
        "embedding_set_id": expected["embedding_set_id"],
        "config": {
            "provider": DEFAULT_PROVIDER,
            "model": DEFAULT_MODEL,
            "response_model_id": DEFAULT_MODEL,
            "dimensions": DEFAULT_DIMENSIONS,
            "query_prefix": "",
            "passage_prefix": "",
            "dtype": "float32-le",
        },
        "vectors": sorted(records, key=lambda item: item["question_id"]),
    }
    manifest_bytes = _canonical_json(manifest)
    _write_manifest_atomically(manifest_path, manifest_bytes)
    return QueryGenerationResult(
        manifest,
        hashlib.sha256(manifest_bytes).hexdigest(),
        len(records),
        len(batches),
        attempts,
        prompt_tokens,
        total_tokens,
        prompt_tokens * 0.02 / 1_000_000,
    )


def _prepare_jobs(
    questions: Sequence[Mapping[str, Any]],
    config: EmbeddingConfig,
    counter: TokenCounter,
) -> list[dict[str, Any]]:
    """Normalize only authorized text and compute exact input identities."""
    by_id: dict[str, str] = {}
    for question in questions:
        question_id = question.get("question_id")
        raw_query = question.get("question")
        if (
            not isinstance(question_id, str)
            or not question_id
            or not isinstance(raw_query, str)
            or question_id in by_id
        ):
            raise ValueError("authorized query identity is invalid")
        by_id[question_id] = raw_query
    jobs: list[dict[str, Any]] = []
    for question_id, raw_query in sorted(by_id.items()):
        query = raw_query.strip()
        provider_input = config.query_prefix + query
        if not query or len(query) > 2000:
            raise ValueError("authorized query text is invalid")
        estimated_tokens = counter.count(provider_input)
        if estimated_tokens > min(
            config.operational_cap_tokens,
            config.max_tokens_per_request,
            512,
        ):
            raise ValueError("authorized query exceeds embedding input cap")
        input_bytes = provider_input.encode("utf-8")
        jobs.append(
            {
                "question_id": question_id,
                "query": query,
                "query_sha256": hashlib.sha256(
                    query.encode("utf-8")
                ).hexdigest(),
                "input_sha256": hashlib.sha256(input_bytes).hexdigest(),
                "estimated_tokens": estimated_tokens,
            }
        )
    return jobs


def _batches(
    jobs: Sequence[Mapping[str, Any]], config: EmbeddingConfig
) -> list[list[Mapping[str, Any]]]:
    """Batch in stable question-ID order within configured count/token caps."""
    result: list[list[Mapping[str, Any]]] = []
    batch: list[Mapping[str, Any]] = []
    tokens = 0
    for job in jobs:
        estimate = cast(int, job["estimated_tokens"])
        if batch and (
            len(batch) >= config.max_inputs_per_request
            or tokens + estimate > config.max_tokens_per_request
        ):
            result.append(batch)
            batch = []
            tokens = 0
        batch.append(job)
        tokens += estimate
    if batch:
        result.append(batch)
    return result


def _timestamp(value: datetime) -> str:
    """Require an aware UTC timestamp and return canonical ISO text."""
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("generation timestamp must be UTC-aware")
    return value.isoformat(timespec="seconds").replace("+00:00", "Z")


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    """Serialize deterministic JSON for manifest integrity hashing."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _write_manifest_atomically(path: Path, data: bytes) -> None:
    """Write the manifest atomically without overwriting prior data."""
    if path.exists():
        raise ValueError("query-cache manifest already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, suffix=".tmp", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            raise ValueError("query-cache manifest already exists")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
