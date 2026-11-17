"""Sequential resumable embedding with durable batch usage and provenance."""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from sciscope.chunking.counter import TokenCounter
from sciscope.embedding.cache import CacheEntry, EmbeddingCache, cache_key
from sciscope.embedding.config import (
    CACHE_FORMAT_VERSION,
    EmbeddingCacheError,
    EmbeddingConfig,
    EmbeddingConfigError,
    EmbeddingInputError,
    EmbeddingProviderError,
    build_passage_input,
)
from sciscope.embedding.inputs import load_chunk_inputs
from sciscope.embedding.provider import Embedder, EmbeddingUsage
from sciscope.embedding.store import (
    build_manifest,
    build_report,
    pack_vector,
    write_embedding_files,
)


@dataclass(frozen=True, slots=True)
class EmbedOptions:
    """Input, cache, output paths, and optional file-order selection limit."""

    chunks: Path = Path("data/processed/pilot/chunks.jsonl")
    cache_dir: Path = Path("data/embeddings/pilot/cache")
    vectors: Path = Path("data/embeddings/pilot/vectors.f32")
    manifest: Path = Path("data/embeddings/pilot/manifest.json")
    report: Path = Path("data/pilot/embedding_report.json")
    limit: int | None = None


@dataclass(frozen=True, slots=True)
class EmbedStats:
    """Ephemeral console counts, distinct from durable set-level totals."""

    chunk_count: int
    selected_count: int
    unique_input_count: int
    cache_hits: int
    cache_misses: int
    api_calls: int
    retries: int
    status: Literal["complete", "partial"]
    usage: EmbeddingUsage
    estimated_input_tokens: int
    provider_input_count: int
    rate_limit_headers: Mapping[str, str]


def run_embedding(
    options: EmbedOptions,
    config: EmbeddingConfig,
    counter: TokenCounter,
    *,
    embedder_factory: Callable[[], Embedder],
    utc_date: Callable[[], str],
    custom_base_url_used: bool = False,
) -> EmbedStats:
    """Validate, select, deduplicate, resume, batch, and atomically publish."""
    if options.limit is not None and (
        type(options.limit) is not int or options.limit < 1
    ):
        raise EmbeddingConfigError("invalid-limit")
    loaded = load_chunk_inputs(options.chunks, counter)
    selected = loaded.chunks[: options.limit]
    unique: dict[str, tuple[str, int]] = {}
    chunk_hashes: dict[str, str] = {}
    for chunk in selected:
        text = build_passage_input(config, chunk.section_path, chunk.text)
        estimate = counter.count(text)
        if estimate > min(config.operational_cap_tokens, 512):
            raise EmbeddingInputError("input-over-cap")
        if estimate > config.max_tokens_per_request:
            raise EmbeddingInputError("input-over-cap")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        chunk_hashes[chunk.chunk_id] = digest
        unique.setdefault(digest, (text, estimate))
    cache = EmbeddingCache(options.cache_dir)
    entries: dict[str, CacheEntry] = {}
    misses: list[str] = []
    for digest, (_, estimate) in unique.items():
        cached = cache.get(config.model, config.dimensions, digest)
        if cached is None:
            misses.append(digest)
        else:
            if (
                cached.counter_id != counter.counter_id
                or cached.estimated_tokens != estimate
            ):
                raise EmbeddingCacheError(
                    "cache-entry-corrupt",
                    cache_key(config.model, config.dimensions, digest),
                )
            entries[digest] = cached
    hits = len(entries)
    api_calls = retries = 0
    headers: Mapping[str, str] = {}
    if misses:
        embedder = embedder_factory()
        for batch in _batches(misses, unique, config):
            result = embedder.embed_passages(
                [unique[digest][0] for digest in batch]
            )
            if len(result.vectors) != len(batch):
                raise EmbeddingProviderError("response-count")
            if any(
                len(vector) != config.dimensions for vector in result.vectors
            ):
                raise EmbeddingProviderError("response-dimensions")
            vectors = [pack_vector(vector) for vector in result.vectors]
            batch_id = hashlib.sha256(
                "\n".join(sorted(batch)).encode()
            ).hexdigest()
            batch_estimate = sum(unique[digest][1] for digest in batch)
            embedded_on = utc_date()
            pending = [
                CacheEntry(
                    CACHE_FORMAT_VERSION,
                    config.model,
                    config.dimensions,
                    digest,
                    hashlib.sha256(vector).hexdigest(),
                    unique[digest][1],
                    counter.counter_id,
                    embedded_on,
                    batch_id,
                    len(batch),
                    batch_estimate,
                    result.usage.prompt_tokens,
                    result.usage.total_tokens,
                    vector,
                )
                for digest, vector in zip(batch, vectors, strict=True)
            ]
            cache.put_batch(pending)
            for entry in pending:
                entries[entry.input_sha256] = entry
            api_calls += 1
            retries += result.attempts - 1
            headers = result.rate_limit_headers
    by_chunk = {
        chunk.chunk_id: entries[chunk_hashes[chunk.chunk_id]]
        for chunk in selected
    }
    manifest = build_manifest(
        config,
        loaded,
        selected,
        by_chunk,
        custom_base_url_used=custom_base_url_used,
    )
    report = build_report(
        manifest, paper_count=len({chunk.doi for chunk in selected})
    )
    vectors_bytes = b"".join(
        by_chunk[chunk.chunk_id].vector_bytes
        for chunk in sorted(selected, key=lambda chunk: chunk.chunk_id)
    )
    write_embedding_files(
        vectors_bytes,
        manifest,
        report,
        options.vectors,
        options.manifest,
        options.report,
    )
    usage = cast(Mapping[str, object], manifest["usage"])
    return EmbedStats(
        len(loaded.chunks),
        len(selected),
        len(unique),
        hits,
        len(misses),
        api_calls,
        retries,
        cast(Literal["complete", "partial"], manifest["status"]),
        EmbeddingUsage(
            cast(int, usage["prompt_tokens"]), cast(int, usage["total_tokens"])
        ),
        cast(int, manifest["estimated_input_tokens"]),
        cast(int, manifest["provider_input_count"]),
        headers,
    )


def _batches(
    misses: list[str],
    inputs: Mapping[str, tuple[str, int]],
    config: EmbeddingConfig,
) -> list[list[str]]:
    """Greedily batch missing unique inputs in selection order."""
    batches: list[list[str]] = []
    batch: list[str] = []
    tokens = 0
    for digest in misses:
        estimate = inputs[digest][1]
        if batch and (
            len(batch) >= config.max_inputs_per_request
            or tokens + estimate > config.max_tokens_per_request
        ):
            batches.append(batch)
            batch = []
            tokens = 0
        batch.append(digest)
        tokens += estimate
    if batch:
        batches.append(batch)
    return batches
