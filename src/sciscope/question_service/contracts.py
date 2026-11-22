"""Plain service contracts for Feature 011 fake dependencies."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, Protocol, runtime_checkable


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
    """Result supplied by an injected answer provider."""

    status: ProviderOutcomeStatus
    answer: str | None
    claims: tuple[Claim, ...]
    metadata: OutcomeMetadata = MockMetadata()


class DependencyFailureCode(StrEnum):
    """Controlled failures exposed by fake dependencies."""

    RETRIEVAL_UNAVAILABLE = "retrieval_unavailable"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    DEPENDENCY_TIMEOUT = "dependency_timeout"


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
    """Generates a synthetic outcome from retrieval output."""

    def answer(
        self,
        question: str,
        evidence: tuple[Evidence, ...],
        corpus: CorpusProvenance,
        request_id: str,
    ) -> ProviderOutcome:
        """Return a provider outcome or raise a controlled failure."""
