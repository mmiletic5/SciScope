"""Contract rules for the payload workflows (API_CONTRACT.md 3.2-3.5).

Each test names the contract rule it documents. Violations fail closed with
``ResponseContractFailure``; the two downgrade rules return None, which the
service maps to ``insufficient_evidence``.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from backend import workflow_fixtures as fx
from sciscope.question_service.contracts import (
    CONFLICTS_REVIEW_NOTE,
    CitedItem,
    Claim,
    ComparisonPayload,
    ComparisonSubject,
    ConflictsPayload,
    Evidence,
    GapAnalysisPayload,
    Hypothesis,
    ProviderOutcome,
    RetrievalOutcome,
    Workflow,
    WorkflowPayload,
)
from sciscope.question_service.validation import ResponseContractFailure
from sciscope.question_service.workflow_validation import (
    derive_claims,
    validate_payload_answer,
)

COMPARISON = fx.load("evidence_comparison.answered.json")
CONFLICTS = fx.load("conflicting_evidence.answered.json")
GAPS = fx.load("research_gap.answered.json")
A1 = "197dd6e17c18af1a673084210bf029f58cb8cd64081fbbdb4e753dbd21970c37"
B1 = "e908fa76c0aea5c4aa8f31e426a1e152d092fa38eb464cd7d0f19cdc2d89d920"
A2 = "9544c5fffd45b88e732418c3a68b8586c4629db2c4262445af930899412f2570"
C1 = "93edc76563922c6ddc6ec6ce7208af5947d0c8fd036eee644f65060dc208f6b9"


def _check(
    document: dict[str, Any],
    new_payload: WorkflowPayload | None = None,
    *,
    retrieval: RetrievalOutcome | None = None,
    **provider_changes: Any,
) -> tuple[Claim, ...] | None:
    provider = fx.provider(document)
    if new_payload is not None:
        provider = replace(provider, payload=new_payload)
    if provider_changes:
        provider = replace(provider, **provider_changes)
    return validate_payload_answer(
        document["workflow"],
        retrieval or fx.retrieval(document),
        provider,
    )


def _fails(*args: Any, **kwargs: Any) -> None:
    with pytest.raises(ResponseContractFailure):
        _check(*args, **kwargs)


def _comparison(**changes: Any) -> ComparisonPayload:
    value = fx.payload(COMPARISON)
    assert isinstance(value, ComparisonPayload)
    return replace(value, **changes)


def _conflicts(**changes: Any) -> ConflictsPayload:
    value = fx.payload(CONFLICTS)
    assert isinstance(value, ConflictsPayload)
    return replace(value, **changes)


def _gaps(**changes: Any) -> GapAnalysisPayload:
    value = fx.payload(GAPS)
    assert isinstance(value, GapAnalysisPayload)
    return replace(value, **changes)


def _claims_json(claims: tuple[Claim, ...] | None) -> list[dict[str, Any]]:
    assert claims is not None
    return [
        {
            "claim_id": c.claim_id,
            "text": c.text,
            "citation_chunk_ids": list(c.citation_chunk_ids),
        }
        for c in claims
    ]


# 3.5: claims are server-derived, flattened in payload order.


@pytest.mark.parametrize("document", [COMPARISON, CONFLICTS, GAPS])
def test_contract_fixtures_are_valid_and_claims_match_derivation(
    document: dict[str, Any],
) -> None:
    """Derived claims equal the fixture claims: same ids, order, citations."""
    assert _claims_json(_check(document)) == document["claims"]


def test_unknown_payload_cannot_be_flattened() -> None:
    """Only the three payload types have a claim derivation."""
    with pytest.raises(ResponseContractFailure):
        derive_claims(None)


# Shared rules.


@pytest.mark.parametrize(
    "citations",
    [(), (A1, A1), ("not-in-evidence",)],
    ids=("empty", "duplicate", "not-in-response-evidence"),
)
def test_citations_are_nonempty_unique_and_in_response_evidence(
    citations: tuple[str, ...],
) -> None:
    """Every cited statement cites >= 1 unique chunk of evidence[]."""
    gap = replace(_gaps().gaps[0], citation_chunk_ids=citations)
    _fails(GAPS, _gaps(gaps=(gap,), hypotheses=()))


def test_evidence_chunk_ids_are_unique() -> None:
    """Duplicate evidence chunk IDs fail before payload checks."""
    retrieval = fx.retrieval(GAPS)
    duplicated = replace(
        retrieval, evidence=(*retrieval.evidence, retrieval.evidence[0])
    )
    _fails(GAPS, retrieval=duplicated)


def test_statement_ids_are_unique() -> None:
    """Two cited statements may not share an ID (they become claim IDs)."""
    payload = _comparison(
        differences=(replace(_comparison().differences[0], item_id="sim-1"),)
    )
    _fails(COMPARISON, payload)


@pytest.mark.parametrize(
    "changes",
    [
        {"claims": (Claim("x", "provider claim", (A1,)),)},
        {"answer": "   "},
        {"workflow": "research_gap"},
        {"payload": None},
    ],
    ids=(
        "provider-supplied-claims",
        "blank-answer",
        "workflow-mismatch",
        "missing-payload",
    ),
)
def test_answered_outcome_shape(changes: dict[str, Any]) -> None:
    """Answer text required; payload type matches; claims are server-only."""
    _fails(COMPARISON, **changes)


def test_payload_type_must_match_the_workflow() -> None:
    """A gap payload cannot answer an evidence_comparison request."""
    _fails(COMPARISON, fx.payload(GAPS))


def test_research_question_is_not_a_payload_workflow() -> None:
    """The payload validator refuses research_question."""
    with pytest.raises(ResponseContractFailure):
        validate_payload_answer(
            "research_question",
            fx.retrieval(COMPARISON),
            fx.provider(COMPARISON),
        )


# 3.2 evidence_comparison.


def test_comparison_citing_fewer_than_two_papers_is_insufficient() -> None:
    """Downgrade rule: < 2 distinct DOIs in the cited evidence."""
    subject = _comparison().subjects[0]
    payload = _comparison(subjects=(subject,), similarities=(), differences=())

    assert _check(COMPARISON, payload) is None


def test_comparison_needs_at_least_two_subjects() -> None:
    """One subject is invalid even when items cite two papers."""
    payload = _comparison(subjects=_comparison().subjects[:1])
    _fails(COMPARISON, payload)


def _many_papers(count: int) -> tuple[RetrievalOutcome, ComparisonPayload]:
    evidence = tuple(
        Evidence(f"c{i}", f"10.0/p{i}", f"loc{i}", f"text {i}", f"T{i}")
        for i in range(count)
    )
    retrieval = replace(fx.retrieval(COMPARISON), evidence=evidence)
    payload = ComparisonPayload(
        subjects=tuple(
            ComparisonSubject(
                f"subj-{i}", e.doi, e.paper_title, "S.", (e.chunk_id,)
            )
            for i, e in enumerate(evidence)
        ),
        similarities=(),
        differences=(),
    )
    return retrieval, payload


def test_comparison_allows_six_subjects_but_not_seven() -> None:
    """Subjects: 2-6 entries."""
    retrieval, payload = _many_papers(6)
    assert _check(COMPARISON, payload, retrieval=retrieval) is not None
    retrieval, payload = _many_papers(7)
    _fails(COMPARISON, payload, retrieval=retrieval)


def test_subject_citations_belong_to_the_subject_doi() -> None:
    """A subject citing a chunk of another paper fails."""
    first, second = _comparison().subjects
    payload = _comparison(
        subjects=(replace(first, citation_chunk_ids=(A1, B1)), second)
    )
    _fails(COMPARISON, payload)


def test_subjects_are_one_per_paper() -> None:
    """Two subjects for the same DOI fail."""
    first, second = _comparison().subjects
    payload = _comparison(
        subjects=(
            first,
            replace(
                second,
                subject_id="subj-x",
                doi=first.doi,
                citation_chunk_ids=(A2,),
            ),
        )
    )
    _fails(COMPARISON, payload)


@pytest.mark.parametrize("field", ["similarities", "differences"])
def test_items_cite_at_least_two_distinct_papers(field: str) -> None:
    """Each similarity/difference cites chunks from >= 2 DOIs."""
    same_paper = CitedItem(f"{field}-x", "Same paper only.", (A1, A2))
    _fails(COMPARISON, _comparison(**{field: (same_paper,)}))


def test_similarities_and_differences_may_be_empty() -> None:
    """Either list may be empty."""
    payload = _comparison(similarities=(), differences=())
    claims = _check(COMPARISON, payload)
    assert [c.claim_id for c in claims or ()] == ["subj-1", "subj-2"]


# 3.3 conflicting_evidence.


def test_conflicts_without_items_are_insufficient() -> None:
    """Downgrade rule: no potential difference identified."""
    assert _check(CONFLICTS, _conflicts(items=())) is None


def test_conflicts_allow_at_most_five_items() -> None:
    """Items: 1-5."""
    item = _conflicts().items[0]
    items = tuple(
        replace(
            item,
            item_id=f"conf-{i}",
            positions=tuple(
                replace(p, position_id=f"conf-{i}-p{j}")
                for j, p in enumerate(item.positions)
            ),
        )
        for i in range(6)
    )
    assert _check(CONFLICTS, _conflicts(items=items[:5])) is not None
    _fails(CONFLICTS, _conflicts(items=items))


def test_conflict_items_need_two_positions() -> None:
    """Each item has >= 2 positions."""
    item = _conflicts().items[0]
    _fails(
        CONFLICTS,
        _conflicts(items=(replace(item, positions=item.positions[:1]),)),
    )


def test_positions_may_come_from_one_paper() -> None:
    """Fixture item conf-2 cites the same chunk on both sides; allowed."""
    payload = _conflicts(items=_conflicts().items[1:])
    assert _check(CONFLICTS, payload) is not None


def test_review_note_is_the_fixed_server_constant() -> None:
    """The model never supplies review_note; any other text fails."""
    assert _conflicts().review_note == CONFLICTS_REVIEW_NOTE
    assert ConflictsPayload(items=()).review_note == CONFLICTS_REVIEW_NOTE
    _fails(CONFLICTS, _conflicts(review_note="Model-written note."))


# 3.4 research_gap.


def test_gap_analysis_needs_a_gap() -> None:
    """>= 1 gap when answered (fails closed, not a downgrade)."""
    _fails(GAPS, _gaps(gaps=(), hypotheses=()))


def test_hypotheses_are_optional_and_at_most_four() -> None:
    """0-4 hypotheses."""
    hypothesis = _gaps().hypotheses[0]
    many = tuple(
        replace(hypothesis, hypothesis_id=f"hyp-{i}") for i in range(5)
    )
    assert _check(GAPS, _gaps(hypotheses=())) is not None
    assert _check(GAPS, _gaps(hypotheses=many[:4])) is not None
    _fails(GAPS, _gaps(hypotheses=many))


@pytest.mark.parametrize(
    "changes",
    [
        {"based_on_gap_ids": ()},
        {"based_on_gap_ids": ("gap-9",)},
        {"based_on_gap_ids": ("gap-1", "gap-1")},
        {"is_speculative": False},
        {"rationale": " "},
    ],
    ids=(
        "no-gap-reference",
        "unknown-gap",
        "duplicate-gap-reference",
        "not-speculative",
        "blank-rationale",
    ),
)
def test_hypothesis_rules(changes: dict[str, Any]) -> None:
    """Hypotheses reference existing gaps and are always speculative."""
    hypothesis: Hypothesis = replace(_gaps().hypotheses[0], **changes)
    _fails(GAPS, _gaps(hypotheses=(hypothesis,)))


def test_every_workflow_in_the_validator_is_a_known_workflow() -> None:
    """Guard: the three payload workflows are exactly the non-default ones."""
    workflows: list[Workflow] = [
        "evidence_comparison",
        "conflicting_evidence",
        "research_gap",
    ]
    for workflow, document in zip(
        workflows, (COMPARISON, CONFLICTS, GAPS), strict=True
    ):
        assert document["workflow"] == workflow
        provider: ProviderOutcome = fx.provider(document)
        assert provider.workflow == workflow
