"""Behavior tests for Feature 011 response-contract validation."""

from dataclasses import replace

import pytest

from sciscope.question_service.contracts import (
    Claim,
    CorpusProvenance,
    Evidence,
    MockMetadata,
    ProviderOutcome,
    ProviderOutcomeStatus,
    RetrievalOutcome,
)
from sciscope.question_service.fakes import FakeAnswerProvider, FakeRetrieval
from sciscope.question_service.validation import (
    ResponseContractFailure,
    validate_answered_outcome,
    validate_insufficient_evidence_outcome,
    validate_no_results_outcome,
)


def _retrieval_outcome() -> RetrievalOutcome:
    """Return a valid deterministic synthetic retrieval outcome."""
    return FakeRetrieval().retrieve("synthetic question", "request-001")


def _answered_outcome(retrieval: RetrievalOutcome) -> ProviderOutcome:
    """Return a valid deterministic answered provider outcome."""
    return FakeAnswerProvider().answer(
        "synthetic question",
        retrieval.evidence,
        retrieval.corpus,
        "request-001",
    )


def test_valid_answered_outcome_preserves_fixture_values() -> None:
    """A valid answered fixture is accepted without replacement or invention."""
    retrieval = _retrieval_outcome()
    provider = _answered_outcome(retrieval)

    validated = validate_answered_outcome(retrieval, provider)

    assert validated is None
    assert retrieval.evidence[0].chunk_id == "synthetic-chunk-001"
    assert provider.claims[0].citation_chunk_ids == ("synthetic-chunk-001",)
    assert retrieval.corpus.corpus_version == "synthetic-corpus-v1"


@pytest.mark.parametrize(
    "claim",
    [
        Claim("claim-001", "fixture claim", ()),
        Claim("claim-001", "fixture claim", ("unknown-chunk",)),
        Claim(
            "claim-001",
            "fixture claim",
            ("synthetic-chunk-001", "synthetic-chunk-001"),
        ),
    ],
)
def test_answered_outcome_rejects_invalid_citation_identities(
    claim: Claim,
) -> None:
    """Missing, unknown, and duplicate citations fail closed."""
    retrieval = _retrieval_outcome()
    provider = replace(_answered_outcome(retrieval), claims=(claim,))

    with pytest.raises(ResponseContractFailure) as caught:
        validate_answered_outcome(retrieval, provider)

    assert caught.value.code == "response_contract_failure"
    assert str(caught.value) == "response_contract_failure"


@pytest.mark.parametrize(
    "evidence",
    [
        (
            Evidence(
                "synthetic-chunk-001",
                "10.0000/synthetic.002",
                "synthetic:section-2",
                "Synthetic duplicate passage.",
                "Synthetic Duplicate Paper",
            ),
        ),
        (
            Evidence(
                "",
                "10.0000/synthetic.001",
                "synthetic:section-1",
                "Synthetic passage.",
                "Synthetic Paper",
            ),
        ),
        (
            Evidence(
                "synthetic-chunk-002",
                "",
                "synthetic:section-1",
                "Synthetic passage.",
                "Synthetic Paper",
            ),
        ),
    ],
)
def test_answered_outcome_rejects_invalid_evidence(
    evidence: tuple[Evidence, ...],
) -> None:
    """Duplicate identities and blank required source fields fail closed."""
    retrieval = _retrieval_outcome()
    provider = _answered_outcome(retrieval)
    invalid_retrieval = replace(
        retrieval, evidence=retrieval.evidence + evidence
    )

    with pytest.raises(ResponseContractFailure):
        validate_answered_outcome(invalid_retrieval, provider)


@pytest.mark.parametrize(
    "corpus",
    [
        CorpusProvenance(
            "", "synthetic-source-contract-v1", "synthetic-corpus-v1"
        ),
        CorpusProvenance(
            "synthetic-delivery-digest-v1", "", "synthetic-corpus-v1"
        ),
        CorpusProvenance(
            "synthetic-delivery-digest-v1", "synthetic-source-contract-v1", ""
        ),
    ],
)
def test_invalid_corpus_provenance_fails_closed(
    corpus: CorpusProvenance,
) -> None:
    """Every response state requires complete corpus provenance."""
    retrieval = replace(_retrieval_outcome(), corpus=corpus)
    provider = _answered_outcome(_retrieval_outcome())

    with pytest.raises(ResponseContractFailure):
        validate_answered_outcome(retrieval, provider)


@pytest.mark.parametrize(
    "metadata",
    [
        MockMetadata(is_mock=False, is_test_data=True),  # type: ignore[arg-type]
        MockMetadata(is_mock=True, is_test_data=False),  # type: ignore[arg-type]
    ],
)
def test_false_mock_metadata_fails_closed(metadata: MockMetadata) -> None:
    """Misleading fake-output metadata is rejected before HTTP mapping."""
    retrieval = replace(
        _retrieval_outcome(),
        metadata=metadata,
    )
    provider = _answered_outcome(_retrieval_outcome())

    with pytest.raises(ResponseContractFailure):
        validate_answered_outcome(retrieval, provider)


@pytest.mark.parametrize(
    "provider",
    [
        ProviderOutcome(ProviderOutcomeStatus.ANSWERED, "", ()),
        ProviderOutcome(ProviderOutcomeStatus.ANSWERED, None, ()),
        ProviderOutcome(ProviderOutcomeStatus.ANSWERED, "answer", ()),
    ],
)
def test_answered_outcome_requires_answer_and_claims(
    provider: ProviderOutcome,
) -> None:
    """Answered state rejects blank answers and zero claims."""
    with pytest.raises(ResponseContractFailure):
        validate_answered_outcome(_retrieval_outcome(), provider)


def test_no_results_requires_empty_evidence_and_valid_provenance() -> None:
    """No-results accepts only empty evidence with synthetic provenance."""
    empty = FakeRetrieval(mode="empty").retrieve(
        "synthetic question", "request-002"
    )

    assert validate_no_results_outcome(empty) is None

    with pytest.raises(ResponseContractFailure):
        validate_no_results_outcome(_retrieval_outcome())


def test_insufficient_evidence_requires_evidence_without_answer_or_claims() -> (
    None
):
    """Insufficient evidence preserves retrieval output without answer data."""
    retrieval = _retrieval_outcome()
    insufficient = FakeAnswerProvider(mode="insufficient_evidence").answer(
        "synthetic question",
        retrieval.evidence,
        retrieval.corpus,
        "request-003",
    )

    assert (
        validate_insufficient_evidence_outcome(retrieval, insufficient) is None
    )

    invalid = replace(
        insufficient,
        answer="unexpected",
        claims=(Claim("claim-001", "unexpected", ("synthetic-chunk-001",)),),
    )
    with pytest.raises(ResponseContractFailure):
        validate_insufficient_evidence_outcome(retrieval, invalid)
