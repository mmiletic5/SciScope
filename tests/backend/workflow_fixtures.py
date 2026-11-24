"""Convert docs/mvp/fixtures responses into internal question-service values."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sciscope.question_service.contracts import (
    CitedItem,
    ComparisonPayload,
    ComparisonSubject,
    ComponentMetadata,
    ConflictItem,
    ConflictPosition,
    ConflictsPayload,
    CorpusProvenance,
    Evidence,
    GapAnalysisPayload,
    GapItem,
    Hypothesis,
    ProviderOutcome,
    ProviderOutcomeStatus,
    RetrievalOutcome,
    WorkflowPayload,
)

FIXTURES = Path(__file__).parents[2] / "docs" / "mvp" / "fixtures"
RETRIEVAL_METADATA = ComponentMetadata(
    configured_origin="fake", executed=True, is_test_data=True
)
PROVIDER_METADATA = ComponentMetadata(
    configured_origin="fake", executed=True, is_test_data=True
)


def load(name: str) -> dict[str, Any]:
    """Return one parsed contract fixture."""
    value: dict[str, Any] = json.loads(
        (FIXTURES / name).read_text(encoding="utf-8")
    )
    return value


def retrieval(document: dict[str, Any]) -> RetrievalOutcome:
    """Return the fixture evidence as a retrieval outcome."""
    return RetrievalOutcome(
        evidence=tuple(Evidence(**item) for item in document["evidence"]),
        corpus=CorpusProvenance(**document["corpus"]),
        metadata=RETRIEVAL_METADATA,
    )


def _ids(item: dict[str, Any]) -> tuple[str, ...]:
    return tuple(item["citation_chunk_ids"])


def payload(document: dict[str, Any]) -> WorkflowPayload:
    """Return the fixture's workflow payload as an internal value."""
    if "comparison" in document:
        value = document["comparison"]
        return ComparisonPayload(
            subjects=tuple(
                ComparisonSubject(
                    s["subject_id"],
                    s["doi"],
                    s["paper_title"],
                    s["summary"],
                    _ids(s),
                )
                for s in value["subjects"]
            ),
            similarities=tuple(
                CitedItem(i["item_id"], i["text"], _ids(i))
                for i in value["similarities"]
            ),
            differences=tuple(
                CitedItem(i["item_id"], i["text"], _ids(i))
                for i in value["differences"]
            ),
        )
    if "conflicts" in document:
        value = document["conflicts"]
        return ConflictsPayload(
            review_note=value["review_note"],
            items=tuple(
                ConflictItem(
                    item["item_id"],
                    item["topic"],
                    item["summary"],
                    tuple(
                        ConflictPosition(p["position_id"], p["text"], _ids(p))
                        for p in item["positions"]
                    ),
                )
                for item in value["items"]
            ),
        )
    value = document["gap_analysis"]
    return GapAnalysisPayload(
        gaps=tuple(
            GapItem(g["gap_id"], g["text"], _ids(g)) for g in value["gaps"]
        ),
        hypotheses=tuple(
            Hypothesis(
                h["hypothesis_id"],
                h["text"],
                h["rationale"],
                tuple(h["based_on_gap_ids"]),
                _ids(h),
                h["is_speculative"],
            )
            for h in value["hypotheses"]
        ),
    )


def provider(document: dict[str, Any]) -> ProviderOutcome:
    """Return the fixture as an answered provider outcome without claims."""
    return ProviderOutcome(
        status=ProviderOutcomeStatus.ANSWERED,
        answer=document["answer"],
        claims=(),
        metadata=PROVIDER_METADATA,
        workflow=document["workflow"],
        payload=payload(document),
    )
