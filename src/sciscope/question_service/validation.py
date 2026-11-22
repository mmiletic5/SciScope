"""Pure fail-closed validation for Feature 011 fake dependency output."""

from sciscope.question_service.contracts import (
    Claim,
    ComponentMetadata,
    CorpusProvenance,
    Evidence,
    MockMetadata,
    OutcomeMetadata,
    ProviderOutcome,
    ProviderOutcomeStatus,
    QuestionMetadata,
    RetrievalOutcome,
)


class ResponseContractFailure(RuntimeError):
    """Signals invalid fake output without exposing fixture details."""

    code = "response_contract_failure"

    def __init__(self) -> None:
        """Create the stable failure consumed by later HTTP error mapping."""
        super().__init__(self.code)


def validate_no_results_outcome(outcome: RetrievalOutcome) -> None:
    """Validate retrieval output that will map to the no-results state.

    Args:
        outcome: Retrieval dependency output with no eligible evidence.

    Raises:
        ResponseContractFailure: If the output is not a valid no-results value.
    """
    _validate_retrieval_outcome(outcome)
    if outcome.evidence:
        raise ResponseContractFailure()


def validate_answered_outcome(
    retrieval: RetrievalOutcome,
    provider: ProviderOutcome,
) -> None:
    """Validate retrieval and provider output for the answered state.

    Args:
        retrieval: Retrieval dependency output containing response-local
            evidence.
        provider: Provider output containing a synthetic answer and claims.

    Raises:
        ResponseContractFailure: If any output field violates the response
            contract.
    """
    evidence_ids = _validate_retrieval_outcome(retrieval)
    _validate_metadata(provider.metadata)
    if provider.status is not ProviderOutcomeStatus.ANSWERED:
        raise ResponseContractFailure()
    if not retrieval.evidence or not _is_nonempty_string(provider.answer):
        raise ResponseContractFailure()
    if not provider.claims:
        raise ResponseContractFailure()
    for claim in provider.claims:
        _validate_claim(claim, evidence_ids)


def validate_insufficient_evidence_outcome(
    retrieval: RetrievalOutcome,
    provider: ProviderOutcome,
) -> None:
    """Validate output for the insufficient-evidence state.

    Args:
        retrieval: Nonempty retrieval output preserved by the later service.
        provider: Provider policy output declining to produce an answer.

    Raises:
        ResponseContractFailure: If the state does not preserve its invariants.
    """
    _validate_retrieval_outcome(retrieval)
    _validate_metadata(provider.metadata)
    if (
        provider.status is not ProviderOutcomeStatus.INSUFFICIENT_EVIDENCE
        or not retrieval.evidence
        or provider.answer is not None
        or provider.claims
    ):
        raise ResponseContractFailure()


def _validate_retrieval_outcome(outcome: RetrievalOutcome) -> set[str]:
    """Validate shared retrieval evidence, provenance, and metadata fields."""
    _validate_metadata(outcome.metadata)
    _validate_corpus(outcome.corpus)
    evidence_ids: set[str] = set()
    for evidence in outcome.evidence:
        _validate_evidence(evidence)
        if evidence.chunk_id in evidence_ids:
            raise ResponseContractFailure()
        evidence_ids.add(evidence.chunk_id)
    return evidence_ids


def validate_question_metadata(metadata: QuestionMetadata) -> None:
    """Validate independent metadata for retrieval and answer components.

    Args:
        metadata: Internal component metadata for one question request.

    Raises:
        ResponseContractFailure: If either component is absent or malformed.
    """
    if type(metadata) is not QuestionMetadata:
        raise ResponseContractFailure()
    _validate_component_metadata(metadata.retrieval)
    _validate_component_metadata(metadata.answer_provider)


def _validate_metadata(metadata: OutcomeMetadata) -> None:
    """Validate Feature 011 or T012-B internal metadata without coercion."""
    if type(metadata) is MockMetadata:
        if metadata.is_mock is not True or metadata.is_test_data is not True:
            raise ResponseContractFailure()
        return
    if type(metadata) is ComponentMetadata:
        _validate_component_metadata(metadata)
        return
    if type(metadata) is QuestionMetadata:
        validate_question_metadata(metadata)
        return
    raise ResponseContractFailure()


def _validate_component_metadata(metadata: object) -> None:
    """Require the exact component contract and strict field types."""
    if (
        type(metadata) is not ComponentMetadata
        or metadata.configured_origin not in {"synthetic", "fake", "real"}
        or type(metadata.executed) is not bool
        or type(metadata.is_test_data) is not bool
    ):
        raise ResponseContractFailure()


def _validate_corpus(corpus: CorpusProvenance) -> None:
    """Require every response-level synthetic provenance value."""
    if not all(
        _is_nonempty_string(value)
        for value in (
            corpus.delivery_digest,
            corpus.source_contract_version,
            corpus.corpus_version,
        )
    ):
        raise ResponseContractFailure()


def _validate_evidence(evidence: Evidence) -> None:
    """Require complete synthetic source fields without changing them."""
    if not all(
        _is_nonempty_string(value)
        for value in (
            evidence.chunk_id,
            evidence.doi,
            evidence.source_locator,
            evidence.passage,
            evidence.paper_title,
        )
    ):
        raise ResponseContractFailure()


def _validate_claim(claim: Claim, evidence_ids: set[str]) -> None:
    """Require nonempty unique citations that resolve to response evidence."""
    if not _is_nonempty_string(claim.claim_id) or not _is_nonempty_string(
        claim.text
    ):
        raise ResponseContractFailure()
    if not claim.citation_chunk_ids:
        raise ResponseContractFailure()
    citation_ids: set[str] = set()
    for citation_id in claim.citation_chunk_ids:
        if (
            not _is_nonempty_string(citation_id)
            or citation_id not in evidence_ids
            or citation_id in citation_ids
        ):
            raise ResponseContractFailure()
        citation_ids.add(citation_id)


def _is_nonempty_string(value: object) -> bool:
    """Return whether a contract field contains non-whitespace text."""
    return isinstance(value, str) and bool(value.strip())
