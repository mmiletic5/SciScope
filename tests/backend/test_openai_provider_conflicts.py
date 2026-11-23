"""Offline tests for the ``conflicting_evidence`` OpenAI workflow."""

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
    CONFLICTS_REVIEW_NOTE,
    ConflictsPayload,
    ProviderOutcomeStatus,
    RetrievalOutcome,
)
from sciscope.question_service.openai_provider import (
    conflicting_evidence_schema,
)
from sciscope.question_service.service import (
    AnsweredQuestionOutcome,
    InsufficientEvidenceQuestionOutcome,
    QuestionService,
)
from sciscope.question_service.validation import ResponseContractFailure

DOCUMENT = fx.load("conflicting_evidence.answered.json")
RETRIEVAL = fx.retrieval(DOCUMENT)
EVIDENCE = RETRIEVAL.evidence
A1, B1, C1 = (item.chunk_id for item in EVIDENCE)
ITEMS = DOCUMENT["conflicts"]["items"]


def model_output(**overrides: object) -> dict[str, object]:
    """Return grounded model output mirroring the contract fixture."""
    output: dict[str, object] = {
        "status": "answered",
        "answer": DOCUMENT["answer"],
        "items": [
            {
                "topic": item["topic"],
                "summary": item["summary"],
                "positions": [
                    {
                        "text": p["text"],
                        "citation_chunk_ids": p["citation_chunk_ids"],
                    }
                    for p in item["positions"]
                ],
            }
            for item in ITEMS
        ],
    }
    output.update(overrides)
    return output


def one_item(positions: list[dict[str, object]]) -> dict[str, object]:
    """Return model output with a single item holding ``positions``."""
    return model_output(
        items=[{"topic": "t", "summary": "s", "positions": positions}]
    )


def position(text: str, *ids: str) -> dict[str, object]:
    """Return one model position."""
    return {"text": text, "citation_chunk_ids": list(ids)}


def ask(script: list[Any]) -> tuple[Any, ScriptedTransport]:
    """Run the provider for ``conflicting_evidence``."""
    instance, transport, _ = provider(script)
    outcome = instance.answer(
        QUESTION, EVIDENCE, CORPUS, "req-1", workflow="conflicting_evidence"
    )
    return outcome, transport


def ask_failing(script: list[Any], calls: int) -> None:
    """Assert the provider fails the contract after ``calls`` requests."""
    instance, transport, _ = provider(script)
    with pytest.raises(ResponseContractFailure):
        instance.answer(
            QUESTION, EVIDENCE, CORPUS, "r", workflow="conflicting_evidence"
        )
    assert len(transport.calls) == calls


class _Retrieval:
    def __init__(self, outcome: RetrievalOutcome) -> None:
        self._outcome = outcome

    def retrieve(self, question: str, request_id: str) -> RetrievalOutcome:
        return self._outcome


def test_grounded_conflicts_equal_the_contract_fixture_structure() -> None:
    """Server-assigned IDs and the fixed review note match the fixture."""
    outcome, transport = ask([completion(model_output())])

    assert outcome.status is ProviderOutcomeStatus.ANSWERED
    assert outcome.workflow == "conflicting_evidence"
    assert outcome.claims == ()
    assert outcome.payload == fx.payload(DOCUMENT)
    assert isinstance(outcome.payload, ConflictsPayload)
    assert outcome.payload.review_note == CONFLICTS_REVIEW_NOTE
    assert len(transport.calls) == 1


def test_service_turns_the_outcome_into_the_fixture_claims() -> None:
    """The shared validation accepts it and derives the fixture's claims."""
    instance, _, _ = provider([completion(model_output())])

    outcome = QuestionService(_Retrieval(RETRIEVAL), instance).answer(
        QUESTION, "req-1", "conflicting_evidence"
    )

    assert isinstance(outcome, AnsweredQuestionOutcome)
    assert [(c.claim_id, c.text) for c in outcome.claims] == [
        (c["claim_id"], c["text"]) for c in DOCUMENT["claims"]
    ]


def test_schema_enum_has_no_review_note_and_follows_strict_mode() -> None:
    """Citations use the chunk-ID enum; every object is strict."""
    _, transport = ask([completion(model_output())])
    payload: Any = transport.calls[0].payload
    json_schema = payload["response_format"]["json_schema"]
    assert json_schema["name"] == "conflicting_evidence_answer"
    schema = json_schema["schema"]
    assert set(schema["properties"]) == {"status", "answer", "items"}
    position_schema = schema["properties"]["items"]["items"]["properties"][
        "positions"
    ]["items"]
    assert position_schema["properties"]["citation_chunk_ids"]["items"] == {
        "type": "string",
        "enum": [A1, B1, C1],
    }

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

    walk(conflicting_evidence_schema(["x"]))
    assert found == 3


def test_prompt_forbids_asserting_a_proven_contradiction() -> None:
    """The built request carries the wording and safety instructions."""
    _, transport = ask([completion(model_output())])

    payload: Any = transport.calls[0].payload
    system = payload["messages"][0]["content"]
    assert "NEVER assert that a contradiction is proven" in system
    assert "that a source is wrong" in system
    assert "potential difference" in system
    assert "ONE paper" in system
    assert "insufficient_evidence" in system
    assert "untrusted data" in system
    for item in EVIDENCE:
        assert item.chunk_id in user_message(transport)


def test_invalid_chunk_id_retries_once_then_fails() -> None:
    """A citation outside the evidence is ungrounded."""
    bad = one_item([position("x", A1), position("y", "nope")])
    ask_failing([completion(bad), completion(bad)], calls=2)


def test_ungrounded_output_is_retried_and_can_recover() -> None:
    """A fixable first answer is replaced by a grounded second one."""
    bad = one_item([position("x", A1), position("y", "nope")])
    outcome, transport = ask([completion(bad), completion(model_output())])
    assert outcome.payload == fx.payload(DOCUMENT)
    assert len(transport.calls) == 2


def test_position_without_citation_is_ungrounded() -> None:
    """Every position needs at least one citation."""
    bad = one_item([position("x", A1), position("y")])
    ask_failing([completion(bad), completion(bad)], calls=2)


def test_item_with_one_position_is_rejected() -> None:
    """An item needs at least two positions."""
    bad = one_item([position("x", A1)])
    ask_failing([completion(bad), completion(bad)], calls=2)


def test_more_than_five_items_is_ungrounded() -> None:
    """The contract allows at most five items."""
    items = [
        {
            "topic": f"t{n}",
            "summary": "s",
            "positions": [position("x", A1), position("y", B1)],
        }
        for n in range(6)
    ]
    ask_failing(
        [completion(model_output(items=items))] * 2,
        calls=2,
    )


def test_model_supplied_review_note_is_rejected_as_unknown_field() -> None:
    """Top-level, item and position extras fail without a retry."""
    item = ITEMS[0]
    positions = [position(p["text"], A1) for p in item["positions"]]
    variants: list[dict[str, object]] = [
        model_output(review_note="All verified contradictions."),
        model_output(
            items=[
                {
                    "topic": "t",
                    "summary": "s",
                    "positions": positions,
                    "review_note": "x",
                }
            ]
        ),
        one_item(
            [{**position("x", A1), "position_id": "p"}, position("y", B1)]
        ),
    ]
    for bad in variants:
        ask_failing([completion(bad)], calls=1)


def test_answered_with_empty_items_downgrades_to_insufficient() -> None:
    """Shared validation turns an answered empty payload into a decline."""
    empty = model_output(items=[])
    instance, transport, _ = provider([completion(empty)])

    outcome = QuestionService(_Retrieval(RETRIEVAL), instance).answer(
        QUESTION, "req-1", "conflicting_evidence"
    )

    assert isinstance(outcome, InsufficientEvidenceQuestionOutcome)
    assert outcome.workflow == "conflicting_evidence"
    assert len(transport.calls) == 1


def test_insufficient_answer_carries_no_payload() -> None:
    """A clean decline has no payload or claims."""
    decline = model_output(
        status="insufficient_evidence", answer=None, items=[]
    )
    outcome, _ = ask([completion(decline)])
    assert outcome.status is ProviderOutcomeStatus.INSUFFICIENT_EVIDENCE
    assert outcome.payload is None and outcome.claims == ()


@pytest.mark.parametrize(
    "extra",
    [{"answer": "text"}, {"items": model_output()["items"]}],
)
def test_insufficient_with_content_is_ungrounded(
    extra: dict[str, object],
) -> None:
    """A decline carrying an answer or items is retried, then fails."""
    bad = model_output(status="insufficient_evidence", answer=None, items=[])
    bad.update(extra)
    ask_failing([completion(bad), completion(bad)], calls=2)
