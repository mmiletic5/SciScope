"""Read-only query-vector provenance and compatibility verification."""

from __future__ import annotations

import hashlib
import json
import math
import struct
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from sciscope.embedding.cache import cache_key, decode_entry
from sciscope.embedding.config import EmbeddingCacheError

_REQUIRED_MANIFEST_FIELDS = {
    "manifest_version",
    "dataset_version",
    "dataset_sha256",
    "corpus_version",
    "corpus_sha256",
    "partition",
    "partition_sha256",
    "embedding_set_id",
    "config",
    "vectors",
}
_REQUIRED_VECTOR_FIELDS = {
    "question_id",
    "query_sha256",
    "provider_input_sha256",
    "cache_key",
    "entry_path",
    "entry_sha256",
    "vector_sha256",
    "provenance",
    "generated_at_utc",
}


class EmbeddingReadinessError(ValueError):
    """Sanitized query embedding readiness failure."""


@dataclass(frozen=True, slots=True)
class QueryCacheReadiness:
    """Secret- and question-text-free vector preflight summary."""

    ready: bool
    verified_question_ids: tuple[str, ...]
    manifest_sha256: str
    vector_sha256_by_question: Mapping[str, str]

    def to_dict(self) -> dict[str, Any]:
        """Return an IDs-and-hashes-only JSON-ready summary."""
        return {
            "ready": self.ready,
            "verified_question_ids": list(self.verified_question_ids),
            "manifest_sha256": self.manifest_sha256,
            "vector_sha256_by_question": dict(
                sorted(self.vector_sha256_by_question.items())
            ),
        }


def verify_query_cache_manifest(
    cache_directory: Path,
    manifest: Mapping[str, Any],
    questions: Sequence[Mapping[str, Any]],
    *,
    expected: Mapping[str, Any],
) -> QueryCacheReadiness:
    """Verify exact query/vector/cache identity without writes or generation.

    Args:
        cache_directory: Read-only directory containing existing cache entries.
        manifest: Versioned query-specific provenance manifest.
        questions: Explicitly authorized question records only.
        expected: Frozen dataset, partition, corpus, embedding-set, and config
            identities, including the expected canonical manifest SHA-256.

    Returns:
        Readiness with verified IDs and vector hashes, never vector values.

    Raises:
        EmbeddingReadinessError: If any question/vector identity or integrity
            prerequisite is missing, stale, mismatched, or unverifiable.
    """
    if set(manifest) != _REQUIRED_MANIFEST_FIELDS:
        raise EmbeddingReadinessError(
            "manifest fields are incomplete or unknown"
        )
    if manifest.get("manifest_version") != "phase-d-query-cache-v1":
        raise EmbeddingReadinessError("query-cache manifest version mismatch")

    manifest_digest = _sha256(_canonical_json(manifest))
    if expected.get("manifest_sha256") != manifest_digest:
        raise EmbeddingReadinessError("manifest integrity mismatch")
    for field in (
        "dataset_version",
        "dataset_sha256",
        "corpus_version",
        "corpus_sha256",
        "partition",
        "partition_sha256",
        "embedding_set_id",
    ):
        if manifest.get(field) != expected.get(field):
            raise EmbeddingReadinessError(
                f"{field.replace('_', ' ')} identity mismatch"
            )

    config = manifest.get("config")
    expected_config = expected.get("config")
    if not isinstance(config, dict) or config != expected_config:
        raise EmbeddingReadinessError("embedding configuration mismatch")
    if (
        config.get("provider") != "openai"
        or config.get("model") != "text-embedding-3-small"
        or config.get("response_model_id") != "text-embedding-3-small"
        or config.get("dimensions") != 1536
        or config.get("query_prefix") != ""
        or config.get("passage_prefix") != ""
        or config.get("dtype") != "float32-le"
    ):
        raise EmbeddingReadinessError("embedding configuration is incompatible")

    question_by_id: dict[str, Mapping[str, Any]] = {}
    for question in questions:
        question_id = question.get("question_id")
        query = question.get("question")
        if not isinstance(question_id, str) or not isinstance(query, str):
            raise EmbeddingReadinessError(
                "authorized question identity is invalid"
            )
        if question_id in question_by_id:
            raise EmbeddingReadinessError("duplicate authorized question ID")
        question_by_id[question_id] = question
    if not question_by_id:
        raise EmbeddingReadinessError("authorized question population is empty")

    vector_records = manifest.get("vectors")
    if not isinstance(vector_records, list):
        raise EmbeddingReadinessError("vector manifest records are invalid")
    record_by_id: dict[str, Mapping[str, Any]] = {}
    for record in vector_records:
        if not isinstance(record, dict):
            raise EmbeddingReadinessError("vector manifest record is invalid")
        if set(record) != _REQUIRED_VECTOR_FIELDS:
            raise EmbeddingReadinessError("vector manifest fields are invalid")
        question_id = record.get("question_id")
        if not isinstance(question_id, str) or question_id in record_by_id:
            raise EmbeddingReadinessError(
                "vector ID mapping is duplicate or invalid"
            )
        record_by_id[question_id] = record
    if record_by_id.keys() != question_by_id.keys():
        raise EmbeddingReadinessError("vector mapping is missing or unexpected")

    root = cache_directory.resolve(strict=True)
    vector_digests: dict[str, str] = {}
    for question_id in sorted(question_by_id):
        question = question_by_id[question_id]
        record = record_by_id[question_id]
        query = cast(str, question["question"]).strip()
        if not query or len(query) > 2000:
            raise EmbeddingReadinessError("normalized query is invalid")
        query_bytes = query.encode("utf-8")
        query_digest = _sha256(query_bytes)
        input_digest = _sha256(query_bytes)  # Frozen query prefix is empty.
        if record.get("query_sha256") != query_digest:
            raise EmbeddingReadinessError("query hash mismatch")
        if record.get("provider_input_sha256") != input_digest:
            raise EmbeddingReadinessError("provider input hash mismatch")

        if record.get("provenance") not in {
            "openai-response-cache",
            "verified-cache",
        }:
            raise EmbeddingReadinessError("vector provenance is unverifiable")
        generated_at = record.get("generated_at_utc")
        if not isinstance(generated_at, str):
            raise EmbeddingReadinessError(
                "vector provenance timestamp is invalid"
            )
        try:
            created = datetime.fromisoformat(
                generated_at.replace("Z", "+00:00")
            )
        except (TypeError, ValueError) as error:
            raise EmbeddingReadinessError(
                "vector provenance timestamp is invalid"
            ) from error
        if created.tzinfo is None:
            raise EmbeddingReadinessError(
                "vector provenance timestamp is invalid"
            )

        key = cache_key("text-embedding-3-small", 1536, input_digest)
        if (
            record.get("cache_key") != key
            or record.get("entry_path") != f"{key}.entry"
        ):
            raise EmbeddingReadinessError("query cache key mismatch")
        entry_path = root / f"{key}.entry"
        try:
            if (
                entry_path.is_symlink()
                or entry_path.resolve(strict=True).parent != root
            ):
                raise EmbeddingReadinessError("cache path is unsafe")
            before = entry_path.stat()
            data = entry_path.read_bytes()
            verify_data = entry_path.read_bytes()
            after = entry_path.stat()
        except OSError as error:
            raise EmbeddingReadinessError(
                "missing or unreadable cache entry"
            ) from error
        if (before.st_size, before.st_mtime_ns) != (
            after.st_size,
            after.st_mtime_ns,
        ) or data != verify_data:
            raise EmbeddingReadinessError(
                "cache entry changed during verification"
            )
        entry_digest = _sha256(data)
        if record.get("entry_sha256") != entry_digest:
            raise EmbeddingReadinessError("cache entry integrity mismatch")
        try:
            entry = decode_entry(
                data,
                model="text-embedding-3-small",
                dimensions=1536,
                input_sha256=input_digest,
            )
        except EmbeddingCacheError as error:
            raise EmbeddingReadinessError(
                "cache entry integrity mismatch"
            ) from error
        if record.get("vector_sha256") != entry.vector_sha256:
            raise EmbeddingReadinessError("vector digest mismatch")
        norm_squared = sum(
            value * value
            for (value,) in struct.iter_unpack("<f", entry.vector_bytes)
        )
        norm = math.sqrt(norm_squared)
        if not math.isfinite(norm) or norm <= 0.0:
            raise EmbeddingReadinessError("vector norm is invalid")
        if abs(norm - 1.0) > 0.01:
            raise EmbeddingReadinessError(
                "vector norm is outside corpus tolerance"
            )
        vector_digests[question_id] = entry.vector_sha256

    return QueryCacheReadiness(
        ready=True,
        verified_question_ids=tuple(sorted(question_by_id)),
        manifest_sha256=manifest_digest,
        vector_sha256_by_question=vector_digests,
    )


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise EmbeddingReadinessError(
            "manifest is not canonical JSON"
        ) from error


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()
