"""Plain service contracts for Feature 011 fake dependencies."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Literal, Protocol, get_args, runtime_checkable

Workflow = Literal[
    "research_question",
    "evidence_comparison",
    "conflicting_evidence",
    "research_gap",
]
"""Question workflows; each selects a prompt, output payload and retrieval."""

WORKFLOWS: Final[tuple[Workflow, ...]] = get_args(Workflow)
DEFAULT_WORKFLOW: Final[Workflow] = "research_question"

CONFLICTS_REVIEW_NOTE: Final = (
    "These are potential differences between statements in the retrieved "
    "passages, flagged for human review. They are not verified "
    "contradictions."
)
"""Fixed server text for every conflicts payload; never model-supplied."""


@dataclass(frozen=True, slots=True)
class MockMetadata:
    """Marks a contract value as synthetic Feature 011 test data."""

    is_mock: Literal[True] = True
    is_test_data: Literal[True] = True


ComponentOrigin = Literal["synthetic", "fake", "real"]


@dataclass(frozen=True, slots=True)
class ComponentMetadata:
    """Describes one configured dependency for an internal question outcome."""

    configured_origin: ComponentOrigin
    executed: bool
    is_test_data: bool


@dataclass(frozen=True, slots=True)
class QuestionMetadata:
    """Preserves independent retrieval and answer-provider metadata."""

    retrieval: ComponentMetadata
    answer_provider: ComponentMetadata


OutcomeMetadata = MockMetadata | ComponentMetadata | QuestionMetadata


@dataclass(frozen=True, slots=True)
class Evidence:
    """Synthetic retrieved evidence used by the fake retrieval dependency."""

    chunk_id: str
    doi: str
    source_locator: str
    passage: str
    paper_title: str


@dataclass(frozen=True, slots=True)
class CorpusProvenance:
    """Synthetic fixture-corpus identity independent of evidence IDs."""

    delivery_digest: str
    source_contract_version: str
    corpus_version: str


@dataclass(frozen=True, slots=True)
class Claim:
    """Synthetic provider claim with response-local citation identities."""

    claim_id: str
    text: str
    citation_chunk_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CitedItem:
    """A similarity or difference statement in a comparison payload."""

    item_id: str
    text: str
    citation_chunk_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ComparisonSubject:
    """One compared paper; its citations must all belong to ``doi``."""

    subject_id: str
    doi: str
    paper_title: str
    summary: str
    citation_chunk_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ComparisonPayload:
    """``evidence_comparison`` payload."""

    subjects: tuple[ComparisonSubject, ...]
    similarities: tuple[CitedItem, ...]
    differences: tuple[CitedItem, ...]


@dataclass(frozen=True, slots=True)
class ConflictPosition:
    """One side of a potential difference."""

    position_id: str
    text: str
    citation_chunk_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ConflictItem:
    """A potential difference between two or more positions."""

    item_id: str
    topic: str
    summary: str
    positions: tuple[ConflictPosition, ...]


@dataclass(frozen=True, slots=True)
class ConflictsPayload:
    """``conflicting_evidence`` payload.

    ``review_note`` defaults to the fixed server constant; providers never
    set it, and validation rejects any other value.
    """

    items: tuple[ConflictItem, ...]
    review_note: str = CONFLICTS_REVIEW_NOTE


@dataclass(frozen=True, slots=True)
class GapItem:
    """A research gap grounded in cited passages."""

    gap_id: str
    text: str
    citation_chunk_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Hypothesis:
    """A speculative hypothesis derived from one or more gaps."""

    hypothesis_id: str
    text: str
    rationale: str
    based_on_gap_ids: tuple[str, ...]
    citation_chunk_ids: tuple[str, ...]
    is_speculative: bool = True


@dataclass(frozen=True, slots=True)
class GapAnalysisPayload:
    """``research_gap`` payload."""

    gaps: tuple[GapItem, ...]
    hypotheses: tuple[Hypothesis, ...]


WorkflowPayload = ComparisonPayload | ConflictsPayload | GapAnalysisPayload


@dataclass(frozen=True, slots=True)
class RetrievalOutcome:
    """Result supplied by an injected retrieval dependency."""

    evidence: tuple[Evidence, ...]
    corpus: CorpusProvenance
    metadata: OutcomeMetadata = MockMetadata()


class ProviderOutcomeStatus(StrEnum):
    """Successful states available from the fake answer provider."""

    ANSWERED = "answered"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass(frozen=True, slots=True)
class ProviderOutcome:
    """Result supplied by an injected answer provider.

    Attributes:
        status: Answered or declined.
        answer: Answer text when answered, else None.
        claims: Provider claims for ``research_question``; empty for the
            payload workflows, whose claims the server derives.
        metadata: Component metadata of the provider.
        workflow: Workflow the provider executed; must match the request.
        payload: Typed workflow payload when an answered payload workflow,
            else None.
    """

    status: ProviderOutcomeStatus
    answer: str | None
    claims: tuple[Claim, ...]
    metadata: OutcomeMetadata = MockMetadata()
    workflow: Workflow = DEFAULT_WORKFLOW
    payload: WorkflowPayload | None = None


class DependencyFailureCode(StrEnum):
    """Controlled failures exposed by fake dependencies."""

    RETRIEVAL_UNAVAILABLE = "retrieval_unavailable"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    DEPENDENCY_TIMEOUT = "dependency_timeout"
    WORKFLOW_NOT_IMPLEMENTED = "workflow_not_implemented"


class DependencyFailure(RuntimeError):
    """Controlled offline fake-dependency failure.

    Args:
        code: Stable category used by later service error mapping.
    """

    def __init__(self, code: DependencyFailureCode) -> None:
        """Create a controlled failure with a stable category.

        Args:
            code: Stable category used by later service error mapping.
        """
        self.code = code
        super().__init__(code.value)


@runtime_checkable
class RetrievalService(Protocol):
    """Retrieves synthetic evidence for a validated question."""

    def retrieve(self, question: str, request_id: str) -> RetrievalOutcome:
        """Return an outcome or raise a controlled dependency failure."""


@runtime_checkable
class AnswerProvider(Protocol):
    """Generates an outcome for one workflow from retrieval output.

    Callers pass ``workflow`` only for workflows other than
    ``research_question`` (see ``invoke_provider``), so providers written
    before workflows existed remain valid ``research_question`` providers.
    """

    def answer(
        self,
        question: str,
        evidence: tuple[Evidence, ...],
        corpus: CorpusProvenance,
        request_id: str,
        *,
        workflow: Workflow = DEFAULT_WORKFLOW,
    ) -> ProviderOutcome:
        """Return a provider outcome or raise a controlled failure."""


def invoke_provider(
    provider: AnswerProvider,
    question: str,
    evidence: tuple[Evidence, ...],
    corpus: CorpusProvenance,
    request_id: str,
    workflow: Workflow,
) -> ProviderOutcome:
    """Call ``provider`` for ``workflow`` without breaking legacy providers.

    Args:
        provider: Answer provider to call.
        question: Validated question text.
        evidence: Nonempty retrieval evidence.
        corpus: Corpus provenance.
        request_id: Request correlation ID.
        workflow: Requested workflow.

    Returns:
        The provider outcome, unvalidated.
    """
    if workflow == DEFAULT_WORKFLOW:
        return provider.answer(question, evidence, corpus, request_id)
    return provider.answer(
        question, evidence, corpus, request_id, workflow=workflow
    )
