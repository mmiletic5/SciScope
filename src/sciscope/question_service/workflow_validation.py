"""Pure fail-closed validation for the payload workflows (API contract rev 2).

The three payload workflows (``evidence_comparison``, ``conflicting_evidence``
and ``research_gap``) return a typed payload instead of provider claims. This
module checks a payload against ``docs/mvp/API_CONTRACT.md`` sections 3.2-3.5
and derives the flat, server-owned ``claims`` list from it.

Every rule violation raises ``ResponseContractFailure``. Two contract rules
instead turn an otherwise valid answer into ``insufficient_evidence``; for
those, ``validate_payload_answer`` returns None.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from sciscope.question_service.contracts import (
    CONFLICTS_REVIEW_NOTE,
    Claim,
    ComparisonPayload,
    ConflictsPayload,
    Evidence,
    GapAnalysisPayload,
    ProviderOutcome,
    ProviderOutcomeStatus,
    RetrievalOutcome,
    Workflow,
    WorkflowPayload,
)
from sciscope.question_service.validation import (
    ResponseContractFailure,
    validate_outcome_metadata,
    validate_retrieval_outcome,
)

MIN_COMPARISON_SUBJECTS = 2
MAX_COMPARISON_SUBJECTS = 6
MIN_COMPARISON_ITEM_DOIS = 2
MIN_CONFLICT_ITEMS = 1
MAX_CONFLICT_ITEMS = 5
MIN_CONFLICT_POSITIONS = 2
MIN_GAPS = 1
MAX_HYPOTHESES = 4

_PAYLOAD_TYPES: Mapping[Workflow, type] = {
    "evidence_comparison": ComparisonPayload,
    "conflicting_evidence": ConflictsPayload,
    "research_gap": GapAnalysisPayload,
}


def is_payload_workflow(workflow: Workflow) -> bool:
    """Return whether ``workflow`` answers with a typed payload."""
    return workflow in _PAYLOAD_TYPES


def validate_payload_answer(
    workflow: Workflow,
    retrieval: RetrievalOutcome,
    provider: ProviderOutcome,
) -> tuple[Claim, ...] | None:
    """Validate an answered payload outcome and derive its claims.

    Args:
        workflow: Requested payload workflow.
        retrieval: Validated-shape retrieval output for this response.
        provider: Provider output with status ``answered``.

    Returns:
        The server-derived flat claims, or None when a contract rule turns
        the answer into ``insufficient_evidence``.

    Raises:
        ResponseContractFailure: If any contract rule is violated.
    """
    if not is_payload_workflow(workflow):
        raise ResponseContractFailure()
    validate_retrieval_outcome(retrieval)
    validate_outcome_metadata(provider.metadata)
    if (
        provider.status is not ProviderOutcomeStatus.ANSWERED
        or provider.workflow != workflow
        or not retrieval.evidence
        or not _is_text(provider.answer)
        or provider.claims
        or type(provider.payload) is not _PAYLOAD_TYPES[workflow]
    ):
        raise ResponseContractFailure()
    evidence = {item.chunk_id: item for item in retrieval.evidence}
    claims = derive_claims(provider.payload)
    validate_claims(claims, evidence)
    if isinstance(provider.payload, ComparisonPayload):
        if len(_cited_dois(claims, evidence)) < MIN_COMPARISON_ITEM_DOIS:
            return None
        validate_comparison(provider.payload, evidence)
    elif isinstance(provider.payload, ConflictsPayload):
        if not provider.payload.items:
            return None
        validate_conflicts(provider.payload)
    elif isinstance(provider.payload, GapAnalysisPayload):
        validate_gap_analysis(provider.payload)
    return claims


def derive_claims(payload: WorkflowPayload | None) -> tuple[Claim, ...]:
    """Flatten every cited statement of a payload into claims, in order.

    Comparison: subjects (summary), similarities, differences. Conflicts:
    every position of every item. Gap analysis: gaps, then hypotheses. The
    claim ID is the statement's own ID.

    Args:
        payload: A workflow payload.

    Returns:
        One claim per cited statement.

    Raises:
        ResponseContractFailure: If ``payload`` is not a known payload type.
    """
    if isinstance(payload, ComparisonPayload):
        return (
            *(
                Claim(s.subject_id, s.summary, s.citation_chunk_ids)
                for s in payload.subjects
            ),
            *(
                Claim(i.item_id, i.text, i.citation_chunk_ids)
                for i in (*payload.similarities, *payload.differences)
            ),
        )
    if isinstance(payload, ConflictsPayload):
        return tuple(
            Claim(p.position_id, p.text, p.citation_chunk_ids)
            for item in payload.items
            for p in item.positions
        )
    if isinstance(payload, GapAnalysisPayload):
        return (
            *(
                Claim(g.gap_id, g.text, g.citation_chunk_ids)
                for g in payload.gaps
            ),
            *(
                Claim(h.hypothesis_id, h.text, h.citation_chunk_ids)
                for h in payload.hypotheses
            ),
        )
    raise ResponseContractFailure()


def validate_claims(
    claims: Sequence[Claim], evidence: Mapping[str, Evidence]
) -> None:
    """Require nonempty text, unique IDs and resolvable unique citations.

    Args:
        claims: Claims of one response.
        evidence: Response evidence by chunk ID.

    Raises:
        ResponseContractFailure: If a claim has no text, a duplicate ID, no
            citation, a duplicate citation, or a citation outside
            ``evidence``.
    """
    _require_unique_ids(claim.claim_id for claim in claims)
    for claim in claims:
        if not _is_text(claim.text):
            raise ResponseContractFailure()
        _validate_citations(claim.citation_chunk_ids, evidence)


def validate_comparison(
    payload: ComparisonPayload, evidence: Mapping[str, Evidence]
) -> None:
    """Apply the ``evidence_comparison`` rules (contract section 3.2).

    Args:
        payload: Comparison payload whose citations already resolve.
        evidence: Response evidence by chunk ID.

    Raises:
        ResponseContractFailure: Unless there are 2-6 subjects with distinct
            DOIs, each citing only its own DOI, and every similarity or
            difference cites at least two distinct DOIs.
    """
    subjects = payload.subjects
    if not MIN_COMPARISON_SUBJECTS <= len(subjects) <= MAX_COMPARISON_SUBJECTS:
        raise ResponseContractFailure()
    _require_unique_ids(subject.doi for subject in subjects)
    for subject in subjects:
        if not all(
            _is_text(value)
            for value in (subject.doi, subject.paper_title, subject.summary)
        ):
            raise ResponseContractFailure()
        if any(
            evidence[chunk_id].doi != subject.doi
            for chunk_id in subject.citation_chunk_ids
        ):
            raise ResponseContractFailure()
    for item in (*payload.similarities, *payload.differences):
        dois = {evidence[chunk_id].doi for chunk_id in item.citation_chunk_ids}
        if len(dois) < MIN_COMPARISON_ITEM_DOIS:
            raise ResponseContractFailure()


def validate_conflicts(payload: ConflictsPayload) -> None:
    """Apply the ``conflicting_evidence`` rules (contract section 3.3).

    Args:
        payload: Conflicts payload whose citations already resolve.

    Raises:
        ResponseContractFailure: Unless the review note is the server
            constant and there are 1-5 items, each with a topic, a summary
            and at least two positions.
    """
    if payload.review_note != CONFLICTS_REVIEW_NOTE:
        raise ResponseContractFailure()
    if not MIN_CONFLICT_ITEMS <= len(payload.items) <= MAX_CONFLICT_ITEMS:
        raise ResponseContractFailure()
    _require_unique_ids(item.item_id for item in payload.items)
    for item in payload.items:
        if not _is_text(item.topic) or not _is_text(item.summary):
            raise ResponseContractFailure()
        if len(item.positions) < MIN_CONFLICT_POSITIONS:
            raise ResponseContractFailure()


def validate_gap_analysis(payload: GapAnalysisPayload) -> None:
    """Apply the ``research_gap`` rules (contract section 3.4).

    Args:
        payload: Gap-analysis payload whose citations already resolve.

    Raises:
        ResponseContractFailure: Unless there is at least one gap, at most
            four hypotheses, and every hypothesis is speculative, has a
            rationale, and references one or more existing gaps uniquely.
    """
    if len(payload.gaps) < MIN_GAPS or len(payload.hypotheses) > MAX_HYPOTHESES:
        raise ResponseContractFailure()
    gap_ids = {gap.gap_id for gap in payload.gaps}
    for hypothesis in payload.hypotheses:
        if hypothesis.is_speculative is not True or not _is_text(
            hypothesis.rationale
        ):
            raise ResponseContractFailure()
        if not hypothesis.based_on_gap_ids:
            raise ResponseContractFailure()
        _require_unique_ids(hypothesis.based_on_gap_ids)
        if not gap_ids.issuperset(hypothesis.based_on_gap_ids):
            raise ResponseContractFailure()


def _cited_dois(
    claims: Iterable[Claim], evidence: Mapping[str, Evidence]
) -> set[str]:
    """Return the distinct DOIs of all cited evidence."""
    return {
        evidence[chunk_id].doi
        for claim in claims
        for chunk_id in claim.citation_chunk_ids
    }


def _validate_citations(
    citation_ids: Sequence[str], evidence: Mapping[str, Evidence]
) -> None:
    """Require a nonempty, unique citation list inside ``evidence``."""
    if not citation_ids:
        raise ResponseContractFailure()
    _require_unique_ids(citation_ids)
    if not all(chunk_id in evidence for chunk_id in citation_ids):
        raise ResponseContractFailure()


def _require_unique_ids(values: Iterable[object]) -> None:
    """Require nonempty, pairwise distinct string identifiers."""
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not value.strip() or value in seen:
            raise ResponseContractFailure()
        seen.add(value)


def _is_text(value: object) -> bool:
    """Return whether a contract field contains non-whitespace text."""
    return isinstance(value, str) and bool(value.strip())
