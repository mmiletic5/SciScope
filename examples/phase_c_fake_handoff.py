"""Runnable fake-only example for the proposed Person 2/3 handoff."""

from __future__ import annotations

import json
from dataclasses import dataclass

from sciscope.retrieval._context import select_context
from sciscope.retrieval._quality import rank_evidence


@dataclass(frozen=True)
class FakeHit:
    """Synthetic evidence record; never loaded from a real corpus."""

    chunk_id: str
    doi: str
    source_locator: str
    text: str
    section_id: str
    section_path: tuple[str, ...]
    normalized_type: str
    paper: dict[str, object]
    dense_similarity: float | None
    dense_rank: int | None
    lexical_score: float | None
    lexical_rank: int | None
    fusion_score: float | None


class FakeTokenCounter:
    """Deterministic example counter with an explicit identity."""

    counter_id = "example:whitespace-v1"

    def count(self, text: str) -> int:
        """Count whitespace-separated tokens for this example only."""
        return len(text.split())


class FakeRetrievalService:
    """Proposed service seam backed only by fixed illustrative data."""

    def retrieve(self, request: dict[str, object]) -> dict[str, object]:
        """Return fixed synthetic evidence without external dependencies."""
        del request
        return {
            "request_id": "example-001",
            "mode": "hybrid",
            "corpus": {
                "delivery_digest": "sha256:" + "a" * 64,
                "source_contract_version": "0.3.0",
                "corpus_version": "pilot17-xml-example",
            },
            "results": (
                FakeHit(
                    chunk_id="b" * 64,
                    doi="10.1234/example.1",
                    source_locator="example:article-1:paragraph-1",
                    text=(
                        "Synthetic evidence used only to demonstrate "
                        "integration."
                    ),
                    section_id="example:results",
                    section_path=("Results",),
                    normalized_type="results",
                    paper={
                        "title": "Synthetic article",
                        "authors": [{"surname": "Example"}],
                        "journal": "Example Journal",
                        "publication_year": 2026,
                        "language": "EN",
                        "license": "CC BY 4.0",
                        "source_url": "https://example.invalid/article",
                    },
                    dense_similarity=0.5,
                    dense_rank=1,
                    lexical_score=0.2,
                    lexical_rank=1,
                    fusion_score=0.032786885,
                ),
            ),
            "warnings": (),
        }


def build_example_response() -> dict[str, object]:
    """Run fake retrieval, deterministic ranking, and token selection."""
    raw = FakeRetrievalService().retrieve(
        {"query_text": "synthetic question", "mode": "hybrid", "top_k": 5}
    )
    candidates = raw["results"]
    assert isinstance(candidates, tuple)
    ranked = rank_evidence(candidates)
    selected = select_context(
        ranked.candidates,
        budget_tokens=32,
        token_counter=FakeTokenCounter(),
        expected_counter_id="example:whitespace-v1",
    )
    evidence = []
    for rank, item in enumerate(selected.selected, start=1):
        hit = item.hit
        corpus = raw["corpus"]
        assert isinstance(corpus, dict)
        evidence.append(
            {
                "rank": rank,
                "chunk_id": hit.chunk_id,
                "text": hit.text,
                "doi": hit.doi,
                "source_locator": hit.source_locator,
                "section_id": hit.section_id,
                "section_path": list(hit.section_path),
                "normalized_type": hit.normalized_type,
                "paper": hit.paper,
                "scores": {
                    "dense_similarity": hit.dense_similarity,
                    "dense_rank": hit.dense_rank,
                    "lexical_score": hit.lexical_score,
                    "lexical_rank": hit.lexical_rank,
                    "fusion_score": hit.fusion_score,
                },
                "citation": {
                    "doi": hit.doi,
                    "source_locator": hit.source_locator,
                    "chunk_id": hit.chunk_id,
                    "delivery_digest": corpus["delivery_digest"],
                },
            }
        )
    return {
        "request_id": raw["request_id"],
        "status": "ok",
        "answer": {
            "text": "[Fake provider output; synthetic example only.]",
            "insufficient_evidence": not evidence,
        },
        "corpus": raw["corpus"],
        "evidence": evidence,
        "warnings": list(raw["warnings"]),
        "selection": {
            "token_counter_id": selected.counter_id,
            "budget_tokens": selected.budget_tokens,
            "total_tokens": selected.total_tokens,
            "omitted_chunk_ids": [item.chunk_id for item in selected.omissions],
        },
    }


if __name__ == "__main__":
    print(json.dumps(build_example_response(), indent=2))
