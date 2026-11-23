"""Deterministic, offline-only fake dependencies for Feature 011."""

from dataclasses import dataclass, replace
from typing import Literal

from sciscope.question_service.contracts import (
    Claim,
    ComponentMetadata,
    CorpusProvenance,
    DependencyFailure,
    DependencyFailureCode,
    Evidence,
    ProviderOutcome,
    ProviderOutcomeStatus,
    RetrievalOutcome,
)

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

    def answer(
        self,
        question: str,
        evidence: tuple[Evidence, ...],
        corpus: CorpusProvenance,
        request_id: str,
    ) -> ProviderOutcome:
        """Return a deterministic provider outcome for supplied fake evidence.

        Args:
            question: Validated question retained only at the protocol boundary.
            evidence: Synthetic evidence whose first identity is cited when
                answered.
            corpus: Synthetic provenance retained at the protocol boundary.
            request_id: Valid request correlation ID retained at the boundary.

        Returns:
            A configured synthetic provider outcome.

        Raises:
            DependencyFailure: If the configured fake simulates an outage or
                timeout.
        """
        del question, corpus, request_id
        if self.mode == "unavailable":
            raise DependencyFailure(DependencyFailureCode.PROVIDER_UNAVAILABLE)
        if self.mode == "timeout":
            raise DependencyFailure(DependencyFailureCode.DEPENDENCY_TIMEOUT)
        if self.mode == "insufficient_evidence":
            return ProviderOutcome(
                status=ProviderOutcomeStatus.INSUFFICIENT_EVIDENCE,
                answer=None,
                claims=(),
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


_FAKE_RETRIEVAL_METADATA = ComponentMetadata(
    configured_origin="synthetic", executed=True, is_test_data=True
)
_FAKE_PROVIDER_METADATA = ComponentMetadata(
    configured_origin="fake", executed=True, is_test_data=True
)


@dataclass(frozen=True, slots=True)
class ComponentFakeRetrieval:
    """Synthetic retrieval that reports truthful v2 component metadata.

    Wraps ``FakeRetrieval`` so v1 behavior and tests stay unchanged.
    """

    mode: RetrievalMode = "evidence"

    def retrieve(self, question: str, request_id: str) -> RetrievalOutcome:
        """Return the fake outcome labeled as synthetic test data."""
        outcome = FakeRetrieval(self.mode).retrieve(question, request_id)
        return replace(outcome, metadata=_FAKE_RETRIEVAL_METADATA)


@dataclass(frozen=True, slots=True)
class ComponentFakeAnswerProvider:
    """Fake answer provider that reports truthful v2 component metadata."""

    mode: ProviderMode = "answered"

    def answer(
        self,
        question: str,
        evidence: tuple[Evidence, ...],
        corpus: CorpusProvenance,
        request_id: str,
    ) -> ProviderOutcome:
        """Return the fake outcome labeled as a fake test-data provider."""
        outcome = FakeAnswerProvider(self.mode).answer(
            question, evidence, corpus, request_id
        )
        return replace(outcome, metadata=_FAKE_PROVIDER_METADATA)
