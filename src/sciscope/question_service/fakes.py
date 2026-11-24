"""Deterministic, offline-only fake dependencies for Feature 011."""

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, ClassVar, Final, Literal

from sciscope.question_service.contracts import (
    DEFAULT_WORKFLOW,
    WORKFLOWS,
    CitedItem,
    Claim,
    ComparisonPayload,
    ComparisonSubject,
    ComponentMetadata,
    ConflictItem,
    ConflictPosition,
    ConflictsPayload,
    CorpusProvenance,
    DependencyFailure,
    DependencyFailureCode,
    Evidence,
    GapAnalysisPayload,
    GapItem,
    Hypothesis,
    ProviderOutcome,
    ProviderOutcomeStatus,
    RetrievalOutcome,
    Workflow,
    WorkflowPayload,
)

if TYPE_CHECKING:
    from sciscope.question_service.agentic_retrieval import AgenticSession

FAKE_PLANNER_QUERY_SUFFIXES: Final = ("", "methods and results")
"""Two scripted searches: the question itself, then a refined query."""

_SYNTHETIC_CORPUS = CorpusProvenance(
    delivery_digest="synthetic-delivery-digest-v1",
    source_contract_version="synthetic-source-contract-v1",
    corpus_version="synthetic-corpus-v1",
)
_SYNTHETIC_EVIDENCE = Evidence(
    chunk_id="synthetic-chunk-001",
    doi="10.0000/synthetic.001",
    source_locator="synthetic:section-1:paragraph-1",
    passage="Synthetic fixture passage for deterministic backend testing.",
    paper_title="Synthetic Fixture Paper",
)

_NOT_A_FINDING = "Synthetic test data, not a scientific finding."
_MULTI_PAPER_EVIDENCE: Final = (
    _SYNTHETIC_EVIDENCE,
    Evidence(
        chunk_id="synthetic-chunk-002",
        doi="10.0000/synthetic.002",
        source_locator="synthetic:section-2:paragraph-1",
        passage=(
            "Synthetic fixture passage B. Invented for deterministic backend "
            "testing; not a scientific finding."
        ),
        paper_title="Synthetic Fixture Paper B",
    ),
    Evidence(
        chunk_id="synthetic-chunk-003",
        doi="10.0000/synthetic.003",
        source_locator="synthetic:section-3:paragraph-2",
        passage=(
            "Synthetic fixture passage C. Invented for deterministic backend "
            "testing; not a scientific finding."
        ),
        paper_title="Synthetic Fixture Paper C",
    ),
    Evidence(
        chunk_id="synthetic-chunk-004",
        doi="10.0000/synthetic.001",
        source_locator="synthetic:section-4:paragraph-1",
        passage=(
            "Second synthetic fixture passage of the first paper. Invented "
            "for deterministic backend testing."
        ),
        paper_title="Synthetic Fixture Paper",
    ),
)
"""Four passages from three synthetic papers, so comparison can answer."""

RetrievalMode = Literal["evidence", "empty", "unavailable", "timeout"]
ProviderMode = Literal[
    "answered", "insufficient_evidence", "unavailable", "timeout"
]


@dataclass(frozen=True, slots=True)
class FakeRetrieval:
    """Returns configured synthetic retrieval fixtures without external access.

    Args:
        mode: Determines evidence availability or a controlled failure signal.
    """

    mode: RetrievalMode = "evidence"

    def retrieve(self, question: str, request_id: str) -> RetrievalOutcome:
        """Return deterministic evidence and provenance for a fake request.

        Args:
            question: Validated question retained only at the protocol boundary.
            request_id: Valid request correlation ID retained at the boundary.

        Returns:
            A configured synthetic retrieval outcome.

        Raises:
            DependencyFailure: If the configured fake simulates an outage or
                timeout.
        """
        del question, request_id
        if self.mode == "unavailable":
            raise DependencyFailure(DependencyFailureCode.RETRIEVAL_UNAVAILABLE)
        if self.mode == "timeout":
            raise DependencyFailure(DependencyFailureCode.DEPENDENCY_TIMEOUT)
        if self.mode == "empty":
            return RetrievalOutcome(evidence=(), corpus=_SYNTHETIC_CORPUS)
        return RetrievalOutcome(
            evidence=(_SYNTHETIC_EVIDENCE,), corpus=_SYNTHETIC_CORPUS
        )


@dataclass(frozen=True, slots=True)
class FakeAnswerProvider:
    """Returns configured synthetic provider fixtures without external access.

    Args:
        mode: Determines the synthetic answer state or controlled failure
            signal.
    """

    mode: ProviderMode = "answered"
    supported_workflows: ClassVar[tuple[Workflow, ...]] = WORKFLOWS

    def answer(
        self,
        question: str,
        evidence: tuple[Evidence, ...],
        corpus: CorpusProvenance,
        request_id: str,
        *,
        workflow: Workflow = DEFAULT_WORKFLOW,
    ) -> ProviderOutcome:
        """Return a deterministic provider outcome for supplied fake evidence.

        Args:
            question: Validated question retained only at the protocol boundary.
            evidence: Synthetic evidence whose first identity is cited when
                answered.
            corpus: Synthetic provenance retained at the protocol boundary.
            request_id: Valid request correlation ID retained at the boundary.
            workflow: Workflow whose synthetic output shape is produced.

        Returns:
            A configured synthetic provider outcome. ``evidence_comparison``
            declines when the evidence covers fewer than two papers.

        Raises:
            DependencyFailure: If the configured fake simulates an outage or
                timeout.
        """
        del question, corpus, request_id
        if self.mode == "unavailable":
            raise DependencyFailure(DependencyFailureCode.PROVIDER_UNAVAILABLE)
        if self.mode == "timeout":
            raise DependencyFailure(DependencyFailureCode.DEPENDENCY_TIMEOUT)
        declined = ProviderOutcome(
            status=ProviderOutcomeStatus.INSUFFICIENT_EVIDENCE,
            answer=None,
            claims=(),
            workflow=workflow,
        )
        if self.mode == "insufficient_evidence":
            return declined
        if workflow != DEFAULT_WORKFLOW:
            payload = _synthetic_payload(workflow, evidence)
            if payload is None:
                return declined
            return ProviderOutcome(
                status=ProviderOutcomeStatus.ANSWERED,
                answer=(
                    f"Synthetic {workflow} summary from the fake provider. "
                    + _NOT_A_FINDING
                ),
                claims=(),
                workflow=workflow,
                payload=payload,
            )
        citation_ids = (evidence[0].chunk_id,) if evidence else ()
        return ProviderOutcome(
            status=ProviderOutcomeStatus.ANSWERED,
            answer=(
                "Synthetic fixture answer for deterministic backend testing."
            ),
            claims=(
                Claim(
                    claim_id="synthetic-claim-001",
                    text="Synthetic fixture claim linked to supplied evidence.",
                    citation_chunk_ids=citation_ids,
                ),
            ),
        )


def _synthetic_payload(
    workflow: Workflow, evidence: tuple[Evidence, ...]
) -> WorkflowPayload | None:
    """Build a valid, clearly synthetic payload from the supplied evidence.

    Returns:
        The payload, or None when the evidence cannot support the workflow.
    """
    if not evidence:
        return None
    papers: dict[str, list[Evidence]] = {}
    for item in evidence:
        papers.setdefault(item.doi, []).append(item)
    firsts = [chunks[0] for chunks in papers.values()]
    if workflow == "evidence_comparison":
        if len(papers) < 2:
            return None
        pair = (firsts[0].chunk_id, firsts[1].chunk_id)
        return ComparisonPayload(
            subjects=tuple(
                ComparisonSubject(
                    subject_id=f"subj-{index}",
                    doi=chunks[0].doi,
                    paper_title=chunks[0].paper_title,
                    summary=f"Synthetic summary of paper {index}. "
                    + _NOT_A_FINDING,
                    citation_chunk_ids=tuple(c.chunk_id for c in chunks),
                )
                for index, chunks in enumerate(list(papers.values())[:6], 1)
            ),
            similarities=(
                CitedItem(
                    "sim-1",
                    "Synthetic similarity of papers 1 and 2. " + _NOT_A_FINDING,
                    pair,
                ),
            ),
            differences=(
                CitedItem(
                    "diff-1",
                    "Synthetic difference of papers 1 and 2. " + _NOT_A_FINDING,
                    pair,
                ),
            ),
        )
    if workflow == "conflicting_evidence":
        other = firsts[1] if len(firsts) > 1 else firsts[0]
        return ConflictsPayload(
            items=(
                ConflictItem(
                    item_id="conf-1",
                    topic="Synthetic topic for review",
                    summary="Synthetic potential difference. " + _NOT_A_FINDING,
                    positions=(
                        ConflictPosition(
                            "conf-1-p1",
                            "Synthetic position one. " + _NOT_A_FINDING,
                            (firsts[0].chunk_id,),
                        ),
                        ConflictPosition(
                            "conf-1-p2",
                            "Synthetic position two. " + _NOT_A_FINDING,
                            (other.chunk_id,),
                        ),
                    ),
                ),
            )
        )
    if workflow == "research_gap":
        return GapAnalysisPayload(
            gaps=tuple(
                GapItem(
                    f"gap-{index}",
                    f"Synthetic gap {index}. " + _NOT_A_FINDING,
                    (item.chunk_id,),
                )
                for index, item in enumerate(evidence[:2], 1)
            ),
            hypotheses=(
                Hypothesis(
                    hypothesis_id="hyp-1",
                    text="Synthetic hypothesis. " + _NOT_A_FINDING,
                    rationale="Synthetic rationale derived from gap 1.",
                    based_on_gap_ids=("gap-1",),
                    citation_chunk_ids=(evidence[0].chunk_id,),
                ),
            ),
        )
    return None


_FAKE_RETRIEVAL_METADATA = ComponentMetadata(
    configured_origin="synthetic", executed=True, is_test_data=True
)
_FAKE_PROVIDER_METADATA = ComponentMetadata(
    configured_origin="fake", executed=True, is_test_data=True
)


@dataclass(frozen=True, slots=True)
class ComponentFakeRetrieval:
    """Synthetic retrieval that reports truthful v2 component metadata.

    Wraps ``FakeRetrieval`` so v1 behavior and tests stay unchanged. Returns
    passages from three synthetic papers so every workflow can answer.
    """

    mode: RetrievalMode = "evidence"

    def retrieve(self, question: str, request_id: str) -> RetrievalOutcome:
        """Return the fake outcome labeled as synthetic test data."""
        outcome = FakeRetrieval(self.mode).retrieve(question, request_id)
        evidence = _MULTI_PAPER_EVIDENCE if outcome.evidence else ()
        return replace(
            outcome, evidence=evidence, metadata=_FAKE_RETRIEVAL_METADATA
        )


@dataclass(frozen=True, slots=True)
class ComponentFakeAnswerProvider:
    """Fake answer provider that reports truthful v2 component metadata."""

    mode: ProviderMode = "answered"
    supported_workflows: ClassVar[tuple[Workflow, ...]] = WORKFLOWS

    def answer(
        self,
        question: str,
        evidence: tuple[Evidence, ...],
        corpus: CorpusProvenance,
        request_id: str,
        *,
        workflow: Workflow = DEFAULT_WORKFLOW,
    ) -> ProviderOutcome:
        """Return the fake outcome labeled as a fake test-data provider."""
        outcome = FakeAnswerProvider(self.mode).answer(
            question, evidence, corpus, request_id, workflow=workflow
        )
        return replace(outcome, metadata=_FAKE_PROVIDER_METADATA)

    def plan_searches(self, question: str, session: "AgenticSession") -> None:
        """Simulate a stage 1 tool loop deterministically, without network.

        Three simulated model rounds: one search per round for the first
        ``FAKE_PLANNER_QUERY_SUFFIXES`` entries, then a round that stops.
        The ``unavailable`` and ``timeout`` modes fail like the real planner,
        which makes the caller fall back.

        Args:
            question: Validated question text; each query extends it.
            session: Budgets, counters and the search tool.

        Raises:
            DependencyFailure: In the ``unavailable`` and ``timeout`` modes.
        """
        session.note_model_call()
        if self.mode == "unavailable":
            raise DependencyFailure(DependencyFailureCode.PROVIDER_UNAVAILABLE)
        if self.mode == "timeout":
            raise DependencyFailure(DependencyFailureCode.DEPENDENCY_TIMEOUT)
        for index, suffix in enumerate(FAKE_PLANNER_QUERY_SUFFIXES):
            if session.remaining_calls <= 0:
                return
            if index:
                session.note_model_call()
            session.search(f"{question} {suffix}".strip())
        session.note_model_call()
