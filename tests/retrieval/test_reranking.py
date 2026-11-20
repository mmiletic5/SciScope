"""Behavior tests for optional local reranking and its no-op baseline."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from sciscope.retrieval._reranking import (
    DeterministicFakeReranker,
    NoOpReranker,
    rank_with_reranker,
)


def _hit(chunk_id: str, locator: str, text: str) -> SimpleNamespace:
    return SimpleNamespace(
        chunk_id=chunk_id,
        doi="10.1234/example",
        source_locator=locator,
        text=text,
    )


def test_noop_reranker_preserves_base_order_and_deduplicates_first() -> None:
    """No-op mode uses Phase B order and sends unique evidence only."""
    duplicate = _hit("b" * 64, "loc-a", "same")
    later_duplicate = _hit("a" * 64, "loc-a", "same")
    other = _hit("c" * 64, "loc-b", "other")

    result = rank_with_reranker(
        [duplicate, later_duplicate, other],
        query_text="query",
        reranker=NoOpReranker(),
    )

    assert [item.hit.chunk_id for item in result.candidates] == [
        "b" * 64,
        "c" * 64,
    ]
    assert [(item.chunk_id, item.reason) for item in result.exclusions] == [
        ("a" * 64, "duplicate_evidence")
    ]


def test_fake_reranker_receives_deduplicated_candidates_and_sorts() -> None:
    """A deterministic fake orders candidates by score, then base rank."""
    first = _hit("a" * 64, "loc-a", "first")
    duplicate = _hit("b" * 64, "loc-a", "first")
    other = _hit("c" * 64, "loc-c", "other")
    reranker = DeterministicFakeReranker({"a" * 64: 0.1, "c" * 64: 0.9})

    result = rank_with_reranker(
        [first, duplicate, other], query_text="query", reranker=reranker
    )

    assert reranker.calls == [("query", ("a" * 64, "c" * 64))]
    assert [item.hit.chunk_id for item in result.candidates] == [
        "c" * 64,
        "a" * 64,
    ]
    assert result.candidates[0].reranker_score == 0.9


@pytest.mark.parametrize(
    "output",
    [
        [("a" * 64, 1.0)],
        [("a" * 64, 1.0), ("x" * 64, 0.0)],
        [("a" * 64, 1.0), ("a" * 64, 0.0)],
        [("a" * 64, float("nan"))],
        [("a" * 64, float("inf"))],
        [("a" * 64, True)],
    ],
)
def test_invalid_reranker_output_fails_without_fallback(output) -> None:
    """Missing, extra, duplicate, or non-finite scores raise an error."""

    class InvalidReranker:
        def rerank(self, query_text, candidates):
            del query_text, candidates
            return output

    with pytest.raises(ValueError, match="reranker output"):
        rank_with_reranker(
            [_hit("a" * 64, "loc-a", "one"), _hit("b" * 64, "loc-b", "two")],
            query_text="query",
            reranker=InvalidReranker(),
        )


def test_reranker_failure_is_not_silently_replaced() -> None:
    """A selected reranker's exception reaches the caller."""

    class FailedReranker:
        def rerank(self, query_text, candidates):
            del query_text, candidates
            raise RuntimeError("model failed")

    with pytest.raises(RuntimeError, match="model failed"):
        rank_with_reranker(
            [_hit("a" * 64, "loc-a", "one")],
            query_text="query",
            reranker=FailedReranker(),
        )


def test_optional_local_adapter_requires_existing_pinned_checkpoint(
    tmp_path,
):
    """The MiniLM adapter never downloads or accepts an unpinned directory."""
    from sciscope.retrieval._reranking import MiniLMCrossEncoderReranker

    with pytest.raises(ValueError, match="checkpoint directory"):
        MiniLMCrossEncoderReranker(
            tmp_path / "missing",
            model_revision="fixed-revision",
            expected_sha256="0" * 64,
        )


def test_optional_local_adapter_forces_local_only_loading(
    tmp_path, monkeypatch
) -> None:
    """The model loader is pinned to local files and remote code is disabled."""
    import sys
    from types import SimpleNamespace

    from sciscope.retrieval._reranking import (
        MiniLMCrossEncoderReranker,
        RerankerCandidate,
        _directory_sha256,
    )

    checkpoint = tmp_path / "checkpoint"
    checkpoint.mkdir()
    (checkpoint / "weights.bin").write_bytes(b"offline-test-only")
    observed = {}

    class FakeCrossEncoder:
        def __init__(self, model_path, **kwargs):
            observed["path"] = model_path
            observed.update(kwargs)

        def predict(self, pairs, **kwargs):
            del kwargs
            return [0.5 for _pair in pairs]

    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        SimpleNamespace(CrossEncoder=FakeCrossEncoder),
    )
    reranker = MiniLMCrossEncoderReranker(
        checkpoint,
        model_revision="a" * 40,
        expected_sha256=_directory_sha256(checkpoint),
    )

    scores = reranker.rerank(
        "offline query", (RerankerCandidate("b" * 64, "local text"),)
    )

    assert scores == [("b" * 64, 0.5)]
    assert observed["local_files_only"] is True
    assert observed["trust_remote_code"] is False
    assert observed["device"] == "cpu"
