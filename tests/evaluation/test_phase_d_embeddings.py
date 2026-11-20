"""Synthetic fail-closed query-vector provenance tests."""

from __future__ import annotations

import hashlib
import json
import math
import struct
from datetime import date
from pathlib import Path

import pytest

from sciscope.embedding.cache import CacheEntry, cache_key, encode_entry
from sciscope.embedding.config import CACHE_FORMAT_VERSION
from sciscope.evaluation.embeddings import (
    EmbeddingReadinessError,
    verify_query_cache_manifest,
)

MODEL = "text-embedding-3-small"
DIMENSIONS = 1536


def _vector() -> bytes:
    values = [0.0] * DIMENSIONS
    values[0] = 1.0
    return struct.pack("<1536f", *values)


def _fixture(
    tmp_path: Path,
) -> tuple[Path, dict[str, object], dict[str, object]]:
    cache = tmp_path / "cache"
    cache.mkdir(parents=True)
    question = {"question_id": "q1", "question": "  synthetic query?  "}
    normalized = "synthetic query?"
    input_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    vector = _vector()
    vector_hash = hashlib.sha256(vector).hexdigest()
    entry = CacheEntry(
        format=CACHE_FORMAT_VERSION,
        model=MODEL,
        dimensions=DIMENSIONS,
        input_sha256=input_hash,
        vector_sha256=vector_hash,
        estimated_tokens=3,
        counter_id="synthetic-counter-v1",
        embedded_on=date(2026, 11, 20).isoformat(),
        batch_id="a" * 64,
        batch_input_count=1,
        batch_estimated_tokens=3,
        batch_prompt_tokens=3,
        batch_total_tokens=3,
        vector_bytes=vector,
    )
    encoded = encode_entry(entry)
    key = cache_key(MODEL, DIMENSIONS, input_hash)
    entry_path = cache / f"{key}.entry"
    entry_path.write_bytes(encoded)
    entry_hash = hashlib.sha256(encoded).hexdigest()
    manifest: dict[str, object] = {
        "manifest_version": "phase-d-query-cache-v1",
        "dataset_version": "golden-v1",
        "dataset_sha256": "b" * 64,
        "corpus_version": "pilot-fixture",
        "corpus_sha256": "c" * 64,
        "partition": "development",
        "partition_sha256": hashlib.sha256(b'["q1"]').hexdigest(),
        "embedding_set_id": 7,
        "config": {
            "provider": "openai",
            "model": MODEL,
            "response_model_id": MODEL,
            "dimensions": DIMENSIONS,
            "query_prefix": "",
            "passage_prefix": "",
            "dtype": "float32-le",
        },
        "vectors": [
            {
                "question_id": "q1",
                "query_sha256": input_hash,
                "provider_input_sha256": input_hash,
                "cache_key": key,
                "entry_path": f"{key}.entry",
                "entry_sha256": entry_hash,
                "vector_sha256": vector_hash,
                "provenance": "verified-cache",
                "generated_at_utc": "2026-11-20T00:00:00Z",
            }
        ],
    }
    expected: dict[str, object] = {
        "dataset_version": "golden-v1",
        "dataset_sha256": "b" * 64,
        "corpus_version": "pilot-fixture",
        "corpus_sha256": "c" * 64,
        "partition": "development",
        "partition_sha256": hashlib.sha256(b'["q1"]').hexdigest(),
        "embedding_set_id": 7,
        "config": {
            "provider": "openai",
            "model": MODEL,
            "response_model_id": MODEL,
            "dimensions": DIMENSIONS,
            "query_prefix": "",
            "passage_prefix": "",
            "dtype": "float32-le",
        },
    }
    expected["manifest_sha256"] = hashlib.sha256(
        json.dumps(
            manifest,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    return cache, manifest, {"question": question, "expected": expected}


def test_valid_query_cache_manifest_proves_exact_question_mapping(
    tmp_path: Path,
) -> None:
    """A fully bound synthetic cache passes without generating embeddings."""
    cache, manifest, fixture = _fixture(tmp_path)

    report = verify_query_cache_manifest(
        cache,
        manifest,
        (fixture["question"],),
        expected=fixture["expected"],
    )

    assert report.ready
    assert report.verified_question_ids == ("q1",)
    report_json = json.dumps(report.to_dict()).lower()
    assert "vector_bytes" not in report_json
    assert (
        report.to_dict()["vector_sha256_by_question"]["q1"]
        == hashlib.sha256(_vector()).hexdigest()
    )


@pytest.mark.parametrize(
    "mutation, message",
    [
        ("question", "query hash"),
        ("dataset", "dataset"),
        ("model", "configuration"),
        ("missing", "missing"),
        ("entry_hash", "integrity"),
    ],
)
def test_invalid_or_stale_query_vector_fails_closed(
    tmp_path: Path, mutation: str, message: str
) -> None:
    """A bad mapping, identity, model, or cache entry cannot pass readiness."""
    cache, manifest, fixture = _fixture(tmp_path)
    records = manifest["vectors"]
    assert isinstance(records, list)
    if mutation == "question":
        fixture["question"]["question"] = "changed question"
    elif mutation == "dataset":
        manifest["dataset_sha256"] = "d" * 64
    elif mutation == "model":
        manifest["config"]["model"] = "incompatible-model"
    elif mutation == "missing":
        (cache / records[0]["entry_path"]).unlink()
    elif mutation == "entry_hash":
        records[0]["entry_sha256"] = "e" * 64
    if mutation in {"dataset", "model", "entry_hash"}:
        fixture["expected"]["manifest_sha256"] = hashlib.sha256(
            json.dumps(
                manifest,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()

    with pytest.raises(EmbeddingReadinessError, match=message):
        verify_query_cache_manifest(
            cache,
            manifest,
            (fixture["question"],),
            expected=fixture["expected"],
        )


def test_nonfinite_and_zero_norm_vectors_fail_closed(tmp_path: Path) -> None:
    """Vector byte validation rejects NaN and zero vectors independently."""
    for vector in (
        struct.pack("<1536f", *([math.nan] + [0.0] * 1535)),
        bytes(1536 * 4),
    ):
        cache, manifest, fixture = _fixture(
            tmp_path / hashlib.sha256(vector).hexdigest()
        )
        record = manifest["vectors"][0]
        input_hash = record["provider_input_sha256"]
        vector_hash = hashlib.sha256(vector).hexdigest()
        entry = CacheEntry(
            CACHE_FORMAT_VERSION,
            MODEL,
            DIMENSIONS,
            input_hash,
            vector_hash,
            3,
            "synthetic-counter-v1",
            "2026-11-20",
            "a" * 64,
            1,
            3,
            3,
            3,
            vector,
        )
        encoded = encode_entry(entry)
        path = cache / record["entry_path"]
        path.write_bytes(encoded)
        record["entry_sha256"] = hashlib.sha256(encoded).hexdigest()
        record["vector_sha256"] = vector_hash

        with pytest.raises(EmbeddingReadinessError):
            verify_query_cache_manifest(
                cache,
                manifest,
                (fixture["question"],),
                expected=fixture["expected"],
            )
