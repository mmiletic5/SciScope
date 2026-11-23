"""QuestionService and fake behavior for the four v2 workflows."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, cast

import pytest

from backend import workflow_fixtures as fx
from sciscope.question_service.contracts import (
    WORKFLOWS,
    AnswerProvider,
    Claim,
    ConflictsPayload,
    CorpusProvenance,
    Evidence,
    ProviderOutcome,
    ProviderOutcomeStatus,
    RetrievalOutcome,
    Workflow,
)
from sciscope.question_service.fakes import (
    ComponentFakeAnswerProvider,
    ComponentFakeRetrieval,
    FakeAnswerProvider,
    FakeRetrieval,
)
from sciscope.question_service.service import (
    AnsweredQuestionOutcome,
    InsufficientEvidenceQuestionOutcome,
    NoResultsQuestionOutcome,
    QuestionService,
)
from sciscope.question_service.validation import ResponseContractFailure

COMPARISON = fx.load("evidence_comparison.answered.json")
CONFLICTS = fx.load("conflicting_evidence.answered.json")


@dataclass(frozen=True, slots=True)
class _Retrieval:
    outcome: RetrievalOutcome

    def retrieve(self, question: str, request_id: str) -> RetrievalOutcome:
        del question, request_id
        return self.outcome


@dataclass(slots=True)
class _RecordingProvider:
    """Accepts ``workflow`` and records what it was asked for."""

    outcome: ProviderOutcome
    workflows: list[str] = field(default_factory=list)

    def answer(
        self,
        question: str,
        evidence: tuple[Evidence, ...],
        corpus: CorpusProvenance,
        request_id: str,
        *,
        workflow: Workflow = "research_question",
    ) -> ProviderOutcome:
        del question, evidence, corpus, request_id
        self.workflows.append(workflow)
        return self.outcome


@dataclass(slots=True)
class _LegacyProvider:
    """A provider written before workflows existed (no ``workflow``)."""

    calls: int = 0

    def answer(
        self,
        question: str,
        evidence: tuple[Evidence, ...],
        corpus: CorpusProvenance,
        request_id: str,
    ) -> ProviderOutcome:
        del question, corpus, request_id
        self.calls += 1
        return ProviderOutcome(
            status=ProviderOutcomeStatus.ANSWERED,
            answer="Legacy answer.",
            claims=(
                Claim("claim-1", "Legacy claim.", (evidence[0].chunk_id,)),
            ),
            metadata=fx.PROVIDER_METADATA,
        )


def _run(document: dict[str, Any], provider: Any, workflow: Workflow) -> Any:
    return QuestionService(_Retrieval(fx.retrieval(document)), provider).answer(
        "Q?", "req-1", workflow
    )


def test_payload_answer_carries_payload_and_derived_claims() -> None:
    """The service forwards the workflow and returns the validated payload."""
    provider = _RecordingProvider(fx.provider(COMPARISON))

    outcome = _run(COMPARISON, provider, "evidence_comparison")

    assert isinstance(outcome, AnsweredQuestionOutcome)
    assert provider.workflows == ["evidence_comparison"]
    assert outcome.workflow == "evidence_comparison"
    assert outcome.payload == fx.payload(COMPARISON)
    assert [c.claim_id for c in outcome.claims] == [
        c["claim_id"] for c in COMPARISON["claims"]
    ]


def test_downgrade_rule_returns_insufficient_with_evidence() -> None:
    """A conflicts answer without items becomes insufficient_evidence."""
    conflicts = fx.payload(CONFLICTS)
    assert isinstance(conflicts, ConflictsPayload)
    empty = replace(conflicts, items=())
    provider = _RecordingProvider(
        replace(fx.provider(CONFLICTS), payload=empty)
    )

    outcome = _run(CONFLICTS, provider, "conflicting_evidence")

    assert isinstance(outcome, InsufficientEvidenceQuestionOutcome)
    assert outcome.workflow == "conflicting_evidence"
    assert outcome.evidence == fx.retrieval(CONFLICTS).evidence
    assert outcome.claims == ()


@pytest.mark.parametrize(
    "outcome",
    [
        # Provider answered a different workflow than requested.
        replace(fx.provider(COMPARISON), workflow="research_gap"),
        # Declining outcomes carry no payload.
        replace(
            fx.provider(COMPARISON),
            status=ProviderOutcomeStatus.INSUFFICIENT_EVIDENCE,
            answer=None,
        ),
    ],
    ids=("workflow-mismatch", "insufficient-with-payload"),
)
def test_inconsistent_provider_outcomes_fail_closed(
    outcome: ProviderOutcome,
) -> None:
    """Fail closed rather than return a mislabeled response."""
    with pytest.raises(ResponseContractFailure):
        _run(COMPARISON, _RecordingProvider(outcome), "evidence_comparison")


def test_research_question_answer_may_not_carry_a_payload() -> None:
    """research_question stays claims-only."""
    outcome = ProviderOutcome(
        status=ProviderOutcomeStatus.ANSWERED,
        answer="A.",
        claims=(
            Claim(
                "claim-1",
                "C.",
                (fx.retrieval(COMPARISON).evidence[0].chunk_id,),
            ),
        ),
        metadata=fx.PROVIDER_METADATA,
        payload=fx.payload(COMPARISON),
    )
    with pytest.raises(ResponseContractFailure):
        _run(COMPARISON, _RecordingProvider(outcome), "research_question")


def test_legacy_provider_still_serves_research_question() -> None:
    """Providers without a workflow parameter keep working unchanged."""
    provider = _LegacyProvider()

    # Statically the legacy signature no longer matches the extended
    # Protocol; at runtime the service omits ``workflow`` for this workflow.
    outcome = QuestionService(
        _Retrieval(fx.retrieval(COMPARISON)), cast(AnswerProvider, provider)
    ).answer("Q?", "req-1")

    assert isinstance(outcome, AnsweredQuestionOutcome)
    assert outcome.workflow == "research_question"
    assert outcome.payload is None
    assert provider.calls == 1


@pytest.mark.parametrize("workflow", WORKFLOWS)
def test_fakes_answer_every_workflow_with_synthetic_test_data(
    workflow: Workflow,
) -> None:
    """Fake retrieval + fake provider produce a valid answer per workflow."""
    service = QuestionService(
        ComponentFakeRetrieval(), ComponentFakeAnswerProvider()
    )

    outcome = service.answer("Synthetic?", "req-1", workflow)

    assert isinstance(outcome, AnsweredQuestionOutcome)
    assert outcome.workflow == workflow
    assert (outcome.payload is None) is (workflow == "research_question")
    assert outcome.metadata.retrieval.is_test_data is True  # type: ignore[attr-defined]
    assert outcome.metadata.answer_provider.is_test_data is True  # type: ignore[attr-defined]
    assert "Synthetic" in outcome.answer
    assert all(c.text.startswith("Synthetic") for c in outcome.claims)


def test_fake_retrieval_returns_three_synthetic_papers() -> None:
    """Comparison needs evidence from at least two papers; fakes give three."""
    outcome = ComponentFakeRetrieval().retrieve("Q?", "req-1")

    assert len({item.doi for item in outcome.evidence}) >= 3
    assert all(
        item.doi.startswith("10.0000/synthetic") for item in outcome.evidence
    )
    assert (
        ComponentFakeRetrieval(mode="empty").retrieve("Q", "r").evidence == ()
    )


def test_fake_comparison_declines_with_a_single_paper() -> None:
    """The fake never fabricates a comparison from one paper."""
    single = ComponentFakeRetrieval().retrieve("Q?", "r").evidence[:1]
    outcome = FakeAnswerProvider().answer(
        "Q?",
        single,
        fx.retrieval(COMPARISON).corpus,
        "r",
        workflow="evidence_comparison",
    )

    assert outcome.status is ProviderOutcomeStatus.INSUFFICIENT_EVIDENCE
    assert outcome.workflow == "evidence_comparison"


@pytest.mark.parametrize("workflow", WORKFLOWS)
def test_fake_no_results_and_insufficient_modes_per_workflow(
    workflow: Workflow,
) -> None:
    """Statuses keep the requested workflow."""
    empty = QuestionService(
        FakeRetrieval(mode="empty"), FakeAnswerProvider()
    ).answer("Q?", "r", workflow)
    declined = QuestionService(
        ComponentFakeRetrieval(),
        ComponentFakeAnswerProvider(mode="insufficient_evidence"),
    ).answer("Q?", "r", workflow)

    assert isinstance(empty, NoResultsQuestionOutcome)
    assert empty.workflow == workflow
    assert isinstance(declined, InsufficientEvidenceQuestionOutcome)
    assert declined.workflow == workflow


def test_fake_providers_support_all_workflows() -> None:
    """Health derives enabled workflows from this attribute."""
    assert ComponentFakeAnswerProvider.supported_workflows == WORKFLOWS
    assert FakeAnswerProvider.supported_workflows == WORKFLOWS
