"""Offline tests for the ``research_gap`` OpenAI workflow."""

from __future__ import annotations

from typing import Any

import pytest

from backend import workflow_fixtures as fx
from backend.test_openai_provider import (
    CORPUS,
    QUESTION,
    ScriptedTransport,
    completion,
    forbid_network,  # noqa: F401  (autouse fixture)
    provider,
    user_message,
)
from sciscope.question_service.contracts import (
    GapAnalysisPayload,
    ProviderOutcomeStatus,
    RetrievalOutcome,
)
from sciscope.question_service.openai_provider import research_gap_schema
from sciscope.question_service.service import (
    AnsweredQuestionOutcome,
    InsufficientEvidenceQuestionOutcome,
    QuestionService,
)
from sciscope.question_service.validation import ResponseContractFailure

DOCUMENT = fx.load("research_gap.answered.json")
RETRIEVAL = fx.retrieval(DOCUMENT)
EVIDENCE = RETRIEVAL.evidence
A2, B2 = (item.chunk_id for item in EVIDENCE)
GAPS = DOCUMENT["gap_analysis"]["gaps"]
HYPOTHESES = DOCUMENT["gap_analysis"]["hypotheses"]


def model_output(**overrides: object) -> dict[str, object]:
    """Return grounded model output mirroring the contract fixture."""
    output: dict[str, object] = {
        "status": "answered",
        "answer": DOCUMENT["answer"],
        "gaps": [
            {"text": g["text"], "citation_chunk_ids": g["citation_chunk_ids"]}
            for g in GAPS
        ],
        "hypotheses": [
            {
                "text": h["text"],
                "rationale": h["rationale"],
                "based_on_gap_numbers": [1],
                "citation_chunk_ids": h["citation_chunk_ids"],
            }
            for h in HYPOTHESES
        ],
    }
    output.update(overrides)
    return output


def hypothesis(**changes: object) -> dict[str, object]:
    """Return one model hypothesis, overridden by ``changes``."""
    base: dict[str, object] = {
        "text": "Test seasonality.",
        "rationale": "Only one season was covered.",
        "based_on_gap_numbers": [1],
        "citation_chunk_ids": [A2],
    }
    base.update(changes)
    return base


def ask(script: list[Any]) -> tuple[Any, ScriptedTransport]:
    """Run the provider for ``research_gap``."""
    instance, transport, _ = provider(script)
    outcome = instance.answer(
        QUESTION, EVIDENCE, CORPUS, "req-1", workflow="research_gap"
    )
    return outcome, transport


def ask_failing(script: list[Any], calls: int) -> None:
    """Assert the provider fails the contract after ``calls`` requests."""
    instance, transport, _ = provider(script)
    with pytest.raises(ResponseContractFailure):
        instance.answer(
            QUESTION, EVIDENCE, CORPUS, "r", workflow="research_gap"
        )
    assert len(transport.calls) == calls


class _Retrieval:
    def __init__(self, outcome: RetrievalOutcome) -> None:
        self._outcome = outcome

    def retrieve(self, question: str, request_id: str) -> RetrievalOutcome:
        return self._outcome


def test_grounded_gaps_equal_the_contract_fixture_structure() -> None:
    """Server-assigned IDs and speculative flag match the fixture."""
    outcome, transport = ask([completion(model_output())])

    assert outcome.status is ProviderOutcomeStatus.ANSWERED
    assert outcome.workflow == "research_gap"
    assert outcome.claims == ()
    assert outcome.payload == fx.payload(DOCUMENT)
    assert isinstance(outcome.payload, GapAnalysisPayload)
    assert all(h.is_speculative for h in outcome.payload.hypotheses)
    assert len(transport.calls) == 1


def test_service_turns_the_outcome_into_the_fixture_claims() -> None:
    """Shared validation accepts it and derives the fixture's claims."""
    instance, _, _ = provider([completion(model_output())])

    outcome = QuestionService(_Retrieval(RETRIEVAL), instance).answer(
        QUESTION, "req-1", "research_gap"
    )

    assert isinstance(outcome, AnsweredQuestionOutcome)
    assert [(c.claim_id, c.text) for c in outcome.claims] == [
        (c["claim_id"], c["text"]) for c in DOCUMENT["claims"]
    ]


def test_schema_restricts_citations_and_is_strict() -> None:
    """Citations use the chunk-ID enum; every object is strict."""
    _, transport = ask([completion(model_output())])
    payload: Any = transport.calls[0].payload
    json_schema = payload["response_format"]["json_schema"]
    assert json_schema["name"] == "research_gap_answer"
    properties = json_schema["schema"]["properties"]
    assert set(properties) == {"status", "answer", "gaps", "hypotheses"}
    enum = {"type": "string", "enum": [A2, B2]}
    gap = properties["gaps"]["items"]["properties"]
    hyp = properties["hypotheses"]["items"]["properties"]
    assert gap["citation_chunk_ids"]["items"] == enum
    assert hyp["citation_chunk_ids"]["items"] == enum

    found = 0

    def walk(node: object) -> None:
        nonlocal found
        if isinstance(node, dict):
            if node.get("type") == "object":
                found += 1
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(research_gap_schema(["x"]))
    assert found == 3


def test_prompt_demands_stated_gaps_and_tentative_hypotheses() -> None:
    """The built request carries the grounding and safety instructions."""
    _, transport = ask([completion(model_output())])

    payload: Any = transport.calls[0].payload
    system = payload["messages"][0]["content"]
    assert "AS STATED IN THE PASSAGES" in system
    assert "Never invent a gap" in system
    assert "suggestion to test" in system
    assert "no new factual claims" in system.lower()
    assert "insufficient_evidence" in system
    assert "untrusted data" in system
    for item in EVIDENCE:
        assert item.chunk_id in user_message(transport)


def test_invalid_chunk_id_retries_once_then_fails() -> None:
    """A citation outside the evidence is ungrounded."""
    bad = model_output(
        gaps=[{"text": "g", "citation_chunk_ids": ["nope"]}], hypotheses=[]
    )
    ask_failing([completion(bad), completion(bad)], calls=2)


def test_invalid_hypothesis_chunk_id_is_ungrounded() -> None:
    """Hypothesis citations are checked too."""
    bad = model_output(hypotheses=[hypothesis(citation_chunk_ids=["nope"])])
    ask_failing([completion(bad), completion(bad)], calls=2)


def test_ungrounded_output_is_retried_and_can_recover() -> None:
    """A fixable first answer is replaced by a grounded second one."""
    bad = model_output(hypotheses=[hypothesis(citation_chunk_ids=["nope"])])
    outcome, transport = ask([completion(bad), completion(model_output())])
    assert outcome.payload == fx.payload(DOCUMENT)
    assert len(transport.calls) == 2


@pytest.mark.parametrize("numbers", [[3], [0], [-1], [], [1, 1]])
def test_bad_gap_numbers_are_ungrounded(numbers: list[int]) -> None:
    """Out-of-range, empty or duplicated gap numbers retry, then fail."""
    bad = model_output(hypotheses=[hypothesis(based_on_gap_numbers=numbers)])
    ask_failing([completion(bad), completion(bad)], calls=2)


def test_gap_numbers_map_to_server_gap_ids() -> None:
    """1-based numbers become ``gap-N`` ids."""
    output = model_output(hypotheses=[hypothesis(based_on_gap_numbers=[2, 1])])
    outcome, _ = ask([completion(output)])
    assert outcome.payload.hypotheses[0].based_on_gap_ids == (
        "gap-2",
        "gap-1",
    )


def test_more_than_four_hypotheses_is_ungrounded() -> None:
    """The contract allows at most four hypotheses."""
    bad = model_output(hypotheses=[hypothesis() for _ in range(5)])
    ask_failing([completion(bad), completion(bad)], calls=2)


def test_zero_hypotheses_with_gaps_is_valid() -> None:
    """Hypotheses are optional."""
    instance, transport, _ = provider([completion(model_output(hypotheses=[]))])

    outcome = QuestionService(_Retrieval(RETRIEVAL), instance).answer(
        QUESTION, "req-1", "research_gap"
    )

    assert isinstance(outcome, AnsweredQuestionOutcome)
    assert [c.claim_id for c in outcome.claims] == ["gap-1", "gap-2"]
    assert len(transport.calls) == 1


def test_extra_fields_are_rejected_without_retry() -> None:
    """Top-level, gap and hypothesis extras fail the contract at once."""
    variants: list[dict[str, object]] = [
        model_output(gap_ids=["gap-1"]),
        model_output(
            gaps=[{"text": "g", "citation_chunk_ids": [A2], "gap_id": "x"}]
        ),
        model_output(hypotheses=[hypothesis(is_speculative=True)]),
        model_output(hypotheses=[hypothesis(hypothesis_id="hyp-1")]),
    ]
    for bad in variants:
        ask_failing([completion(bad)], calls=1)


def test_answered_with_empty_gaps_downgrades_to_insufficient() -> None:
    """Shared validation turns an answered gapless payload into a decline."""
    empty = model_output(gaps=[], hypotheses=[])
    instance, transport, _ = provider([completion(empty)])

    outcome = QuestionService(_Retrieval(RETRIEVAL), instance).answer(
        QUESTION, "req-1", "research_gap"
    )

    assert isinstance(outcome, InsufficientEvidenceQuestionOutcome)
    assert outcome.workflow == "research_gap"
    assert len(transport.calls) == 1


def test_insufficient_answer_carries_no_payload() -> None:
    """A clean decline has no payload or claims."""
    decline = model_output(
        status="insufficient_evidence", answer=None, gaps=[], hypotheses=[]
    )
    outcome, _ = ask([completion(decline)])
    assert outcome.status is ProviderOutcomeStatus.INSUFFICIENT_EVIDENCE
    assert outcome.payload is None and outcome.claims == ()


@pytest.mark.parametrize(
    "extra",
    [
        {"answer": "text"},
        {"gaps": model_output()["gaps"]},
        {"hypotheses": [hypothesis()]},
    ],
)
def test_insufficient_with_content_is_ungrounded(
    extra: dict[str, object],
) -> None:
    """A decline carrying an answer, gaps or hypotheses is retried."""
    bad = model_output(
        status="insufficient_evidence", answer=None, gaps=[], hypotheses=[]
    )
    bad.update(extra)
    ask_failing([completion(bad), completion(bad)], calls=2)
