"""Offline tests for the ``evidence_comparison`` OpenAI workflow."""

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
    Evidence,
    ProviderOutcomeStatus,
    RetrievalOutcome,
)
from sciscope.question_service.openai_provider import (
    evidence_comparison_schema,
)
from sciscope.question_service.service import (
    AnsweredQuestionOutcome,
    InsufficientEvidenceQuestionOutcome,
    QuestionService,
)
from sciscope.question_service.validation import ResponseContractFailure

DOCUMENT = fx.load("evidence_comparison.answered.json")
RETRIEVAL = fx.retrieval(DOCUMENT)
EVIDENCE = RETRIEVAL.evidence
A1, B1, A2 = (item.chunk_id for item in EVIDENCE)
COMPARISON = DOCUMENT["comparison"]


def model_output(**overrides: object) -> dict[str, object]:
    """Return grounded model output mirroring the contract fixture."""
    output: dict[str, object] = {
        "status": "answered",
        "answer": DOCUMENT["answer"],
        "subjects": [
            {
                "summary": s["summary"],
                "citation_chunk_ids": s["citation_chunk_ids"],
            }
            for s in COMPARISON["subjects"]
        ],
        "similarities": [
            {"text": i["text"], "citation_chunk_ids": i["citation_chunk_ids"]}
            for i in COMPARISON["similarities"]
        ],
        "differences": [
            {"text": i["text"], "citation_chunk_ids": i["citation_chunk_ids"]}
            for i in COMPARISON["differences"]
        ],
    }
    output.update(overrides)
    return output


def insufficient(**overrides: object) -> dict[str, object]:
    """Return model output declining to compare."""
    return model_output(
        status="insufficient_evidence",
        answer=None,
        subjects=[],
        similarities=[],
        differences=[],
        **overrides,
    )


def ask(
    script: list[Any],
    evidence: tuple[Evidence, ...] = EVIDENCE,
) -> tuple[Any, ScriptedTransport]:
    """Run the provider for ``evidence_comparison``."""
    instance, transport, _ = provider(script)
    outcome = instance.answer(
        QUESTION, evidence, CORPUS, "req-1", workflow="evidence_comparison"
    )
    return outcome, transport


def test_grounded_comparison_equals_the_contract_fixture_structure() -> None:
    """Server-assigned IDs and derived DOI/title match the fixture."""
    outcome, transport = ask([completion(model_output())])

    assert outcome.status is ProviderOutcomeStatus.ANSWERED
    assert outcome.workflow == "evidence_comparison"
    assert outcome.claims == ()
    assert outcome.payload == fx.payload(DOCUMENT)
    assert len(transport.calls) == 1


def test_service_turns_the_outcome_into_the_fixture_claims() -> None:
    """The shared validation accepts it and derives the fixture's claims."""
    instance, _, _ = provider([completion(model_output())])

    outcome = QuestionService(_Retrieval(RETRIEVAL), instance).answer(
        QUESTION, "req-1", "evidence_comparison"
    )

    assert isinstance(outcome, AnsweredQuestionOutcome)
    assert [(c.claim_id, c.text) for c in outcome.claims] == [
        (c["claim_id"], c["text"]) for c in DOCUMENT["claims"]
    ]


class _Retrieval:
    def __init__(self, outcome: RetrievalOutcome) -> None:
        self._outcome = outcome

    def retrieve(self, question: str, request_id: str) -> RetrievalOutcome:
        return self._outcome


def test_prompt_and_schema_carry_ids_doi_title_and_enum() -> None:
    """Each passage block shows chunk_id, DOI and title; schema has an enum."""
    _, transport = ask([completion(model_output())])

    text = user_message(transport)
    for item in EVIDENCE:
        assert f"chunk_id={item.chunk_id!r}".replace("'", '"') in text
        assert f"doi: {item.doi}" in text
        assert f"paper_title: {item.paper_title}" in text
    request = transport.calls[0].payload
    json_schema = request["response_format"]["json_schema"]
    assert json_schema["name"] == "evidence_comparison_answer"
    subject_items = json_schema["schema"]["properties"]["subjects"]["items"]
    assert set(subject_items["properties"]) == {
        "summary",
        "citation_chunk_ids",
    }
    assert subject_items["properties"]["citation_chunk_ids"]["items"] == {
        "type": "string",
        "enum": [A1, B1, A2],
    }
    system = request["messages"][0]["content"]
    assert "at least 2" in system and "untrusted data" in system


def test_schema_follows_strict_mode_rules() -> None:
    """All objects forbid extra keys and require every property."""
    schema = evidence_comparison_schema(["x"])
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

    walk(schema)
    assert found == 4


def test_invalid_chunk_id_retries_once_then_fails() -> None:
    """A citation outside the evidence is ungrounded."""
    bad = model_output(
        similarities=[{"text": "x", "citation_chunk_ids": [A1, "nope"]}]
    )
    instance, transport, _ = provider([completion(bad), completion(bad)])

    with pytest.raises(ResponseContractFailure):
        instance.answer(
            QUESTION, EVIDENCE, CORPUS, "r", workflow="evidence_comparison"
        )
    assert len(transport.calls) == 2


def test_subject_citing_two_dois_is_ungrounded() -> None:
    """A subject spanning papers is retried, then fails."""
    bad = model_output(
        subjects=[
            {"summary": "mixed", "citation_chunk_ids": [A1, B1]},
            {"summary": "b", "citation_chunk_ids": [B1]},
        ]
    )
    good = model_output()
    outcome, transport = ask([completion(bad), completion(good)])
    assert outcome.payload == fx.payload(DOCUMENT)
    assert len(transport.calls) == 2

    instance, _, _ = provider([completion(bad), completion(bad)])
    with pytest.raises(ResponseContractFailure):
        instance.answer(
            QUESTION, EVIDENCE, CORPUS, "r", workflow="evidence_comparison"
        )


def test_same_paper_in_two_subjects_is_ungrounded() -> None:
    """One subject per paper: reusing a DOI is retried."""
    bad = model_output(
        subjects=[
            {"summary": "a1", "citation_chunk_ids": [A1]},
            {"summary": "a2", "citation_chunk_ids": [A2]},
            {"summary": "b", "citation_chunk_ids": [B1]},
        ]
    )
    _, transport = ask([completion(bad), completion(model_output())])
    assert len(transport.calls) == 2


def test_item_citing_one_paper_is_ungrounded() -> None:
    """Similarities and differences need at least two papers."""
    bad = model_output(
        similarities=[{"text": "s", "citation_chunk_ids": [A1, A2]}]
    )
    _, transport = ask([completion(bad), completion(model_output())])
    assert len(transport.calls) == 2


def test_single_paper_evidence_downgrades_to_insufficient() -> None:
    """Fewer than two cited papers becomes insufficient_evidence."""
    one_paper = model_output(
        subjects=[{"summary": "a", "citation_chunk_ids": [A1, A2]}],
        similarities=[],
        differences=[],
    )
    instance, transport, _ = provider([completion(one_paper)])

    outcome = QuestionService(_Retrieval(RETRIEVAL), instance).answer(
        QUESTION, "req-1", "evidence_comparison"
    )

    assert isinstance(outcome, InsufficientEvidenceQuestionOutcome)
    assert outcome.workflow == "evidence_comparison"
    assert len(transport.calls) == 1


def test_insufficient_answer_goes_through_shared_validation() -> None:
    """A clean decline is accepted and carries no payload."""
    outcome, _ = ask([completion(insufficient())])
    assert outcome.status is ProviderOutcomeStatus.INSUFFICIENT_EVIDENCE
    assert outcome.payload is None and outcome.claims == ()
    assert outcome.workflow == "evidence_comparison"


@pytest.mark.parametrize(
    "extra",
    [
        {"answer": "text"},
        {"subjects": [{"summary": "s", "citation_chunk_ids": [A1]}]},
        {"similarities": [{"text": "s", "citation_chunk_ids": [A1, B1]}]},
        {"differences": [{"text": "s", "citation_chunk_ids": [A1, B1]}]},
    ],
)
def test_insufficient_with_content_is_ungrounded(
    extra: dict[str, object],
) -> None:
    """A decline carrying an answer or lists is retried, then fails."""
    bad = insufficient()
    bad.update(extra)
    instance, transport, _ = provider([completion(bad), completion(bad)])
    with pytest.raises(ResponseContractFailure):
        instance.answer(
            QUESTION, EVIDENCE, CORPUS, "r", workflow="evidence_comparison"
        )
    assert len(transport.calls) == 2


def test_model_supplied_extra_fields_are_rejected() -> None:
    """Model-supplied doi/title/ids fail the contract without retry."""
    variants: list[dict[str, object]] = [
        model_output(extra="x"),
        model_output(
            subjects=[
                {
                    "summary": "s",
                    "citation_chunk_ids": [A1],
                    "doi": "10.1/x",
                    "paper_title": "t",
                }
            ]
        ),
        model_output(
            similarities=[
                {"text": "s", "citation_chunk_ids": [A1, B1], "item_id": "1"}
            ]
        ),
    ]
    for bad in variants:
        instance, transport, _ = provider([completion(bad)])
        with pytest.raises(ResponseContractFailure):
            instance.answer(
                QUESTION, EVIDENCE, CORPUS, "r", workflow="evidence_comparison"
            )
        assert len(transport.calls) == 1
