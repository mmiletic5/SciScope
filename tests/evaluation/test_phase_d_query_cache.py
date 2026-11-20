"""Synthetic tests for the isolated Phase D query-cache writer."""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import pytest

from sciscope.chunking.counter import Utf8BytesDiv3Counter
from sciscope.embedding.config import EmbeddingConfig
from sciscope.embedding.provider import EmbeddingResult, EmbeddingUsage
from sciscope.evaluation.query_cache import generate_query_cache


class _SyntheticOpenAIEmbedder:
    """Offline API-compatible fake that captures only synthetic inputs."""

    provider_id = "openai"
    model = "text-embedding-3-small"
    dimensions = 1536

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed_passages(self, texts: Sequence[str]) -> EmbeddingResult:
        self.calls.append(list(texts))
        vectors = tuple((1.0,) + (0.0,) * (self.dimensions - 1) for _ in texts)
        tokens = sum((len(text.encode("utf-8")) + 2) // 3 for text in texts)
        return EmbeddingResult(
            vectors, EmbeddingUsage(tokens, tokens), {}, attempts=1
        )

    def embed_queries(self, queries: Sequence[str]) -> EmbeddingResult:
        return self.embed_passages(queries)


def _expected() -> dict[str, object]:
    return {
        "dataset_version": "golden-v1",
        "dataset_sha256": "a" * 64,
        "corpus_version": "pilot17-xml-1fff1573b610",
        "corpus_sha256": "b" * 64,
        "partition": "v1-held-out",
        "partition_sha256": "c" * 64,
        "embedding_set_id": 7,
    }


def test_generation_uses_exact_strip_only_query_and_emits_cache_manifest(
    tmp_path: Path,
) -> None:
    """Input normalization, identities, usage, and cache files are stable."""
    embedder = _SyntheticOpenAIEmbedder()
    cache = tmp_path / "cache"
    manifest_path = cache / "manifest.json"
    questions = [
        {"question_id": "q-b", "question": "  second\n"},
        {"question_id": "q-a", "question": " first  "},
    ]

    result = generate_query_cache(
        questions,
        cache_directory=cache,
        manifest_path=manifest_path,
        expected=_expected(),
        config=EmbeddingConfig(),
        counter=Utf8BytesDiv3Counter(),
        embedder_factory=lambda: embedder,
        utc_now=lambda: datetime(2026, 11, 20, tzinfo=UTC),
    )

    assert embedder.calls == [["first", "second"]]
    assert result.vector_count == 2
    assert result.api_calls == 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["partition"] == "v1-held-out"
    assert manifest["dataset_sha256"] == "a" * 64
    assert [item["question_id"] for item in manifest["vectors"]] == [
        "q-a",
        "q-b",
    ]
    assert all(
        item["provenance"] == "openai-response-cache"
        for item in manifest["vectors"]
    )
    assert all(len(list(cache.glob("*.entry"))) == 2 for _ in (0,))
    assert result.prompt_tokens > 0
    assert result.cost_usd > 0


def test_generation_refuses_to_overwrite_an_existing_manifest(
    tmp_path: Path,
) -> None:
    """Existing cache identity must be verified, never silently replaced."""
    cache = tmp_path / "cache"
    cache.mkdir()
    manifest = cache / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    embedder = _SyntheticOpenAIEmbedder()

    with pytest.raises(ValueError, match="already exists"):
        generate_query_cache(
            [{"question_id": "q1", "question": "synthetic"}],
            cache_directory=cache,
            manifest_path=manifest,
            expected=_expected(),
            config=EmbeddingConfig(),
            counter=Utf8BytesDiv3Counter(),
            embedder_factory=lambda: embedder,
            utc_now=lambda: datetime(2026, 11, 20, tzinfo=UTC),
        )

    assert embedder.calls == []


@pytest.mark.parametrize(
    "questions",
    [
        [],
        [{"question_id": "q1", "question": "   "}],
        [
            {"question_id": "q1", "question": "one"},
            {"question_id": "q1", "question": "two"},
        ],
    ],
)
def test_generation_rejects_invalid_question_population_before_api(
    tmp_path: Path, questions: list[dict[str, str]]
) -> None:
    """Empty, blank, and duplicate query inputs fail before any API call."""
    embedder = _SyntheticOpenAIEmbedder()

    with pytest.raises(ValueError):
        generate_query_cache(
            questions,
            cache_directory=tmp_path / "cache",
            manifest_path=tmp_path / "cache" / "manifest.json",
            expected=_expected(),
            config=EmbeddingConfig(),
            counter=Utf8BytesDiv3Counter(),
            embedder_factory=lambda: embedder,
            utc_now=lambda: datetime(2026, 11, 20, tzinfo=UTC),
        )

    assert embedder.calls == []
