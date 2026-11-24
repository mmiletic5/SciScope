"""Leaked chunk ids in model free text are removed in all four workflows."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

import pytest

from backend import test_openai_provider_comparison as cmp
from backend import test_openai_provider_conflicts as cfl
from backend import test_openai_provider_gaps as gap
from backend.test_openai_provider import (
    CORPUS,
    QUESTION,
    answered,
    completion,
    forbid_network,  # noqa: F401  (autouse fixture)
    provider,
)
from backend.test_openai_provider import (
    EVIDENCE as RQ_EVIDENCE,
)
from sciscope.question_service.contracts import Workflow
from sciscope.question_service.openai_provider import (
    GROUNDING_RULES,
    WORKFLOW_PROMPTS,
    build_messages,
)
from sciscope.question_service.text_sanitizer import strip_chunk_ids
from sciscope.question_service.validation import ResponseContractFailure

ID1 = "866145e0" + "a1" * 28
ID2 = "DE3EB5A9" + "B2" * 28
ID3 = "0123abcd" + "ef" * 28
HEX64 = re.compile(r"[0-9a-fA-F]{64}")
TEXT_KEYS = frozenset({"answer", "text", "summary", "topic", "rationale"})

# Leak patterns appended to a clean sentence ending in a period.
SUFFIXES = {
    "bracket_at_sentence_end": f" [{ID1}]",
    "several_lines": f"\n[{ID1}]\n[{ID2}]\n[{ID3}]",
    "bare_id": f" {ID1}",
    "comma_group": f" [{ID1}, {ID2}]",
    "paren_group": f" ({ID1}; {ID2})",
    "uppercase_adjacent": f" [{ID2}] [{ID1}]",
}


def leak(value: Any, suffix: str) -> Any:
    """Append ``suffix`` to every free-text field, never to citations."""
    if isinstance(value, dict):
        return {
            key: (
                value[key] + suffix
                if key in TEXT_KEYS and isinstance(value[key], str)
                else leak(value[key], suffix)
            )
            for key in value
        }
    if isinstance(value, list):
        return [leak(item, suffix) for item in value]
    return value


def research_question_output() -> dict[str, Any]:
    """Return clean grounded ``research_question`` model output."""
    return answered(
        ("Diet B claim.", ["chunk-b"]),
        ("Longevity claim.", ["chunk-a", "chunk-b"]),
    )


def run(workflow: Workflow, output: dict[str, Any], script_len: int = 1) -> Any:
    """Run the provider for ``workflow`` with a scripted model output."""
    script = [completion(output)] * script_len
    instance, _, _ = provider(script)
    evidence = {
        "research_question": RQ_EVIDENCE,
        "evidence_comparison": cmp.EVIDENCE,
        "conflicting_evidence": cfl.EVIDENCE,
        "research_gap": gap.EVIDENCE,
    }[workflow]
    return instance.answer(QUESTION, evidence, CORPUS, "r", workflow=workflow)


CLEAN: dict[Workflow, Callable[[], dict[str, Any]]] = {
    "research_question": research_question_output,
    "evidence_comparison": cmp.model_output,
    "conflicting_evidence": cfl.model_output,
    "research_gap": gap.model_output,
}


@pytest.mark.parametrize("workflow", list(CLEAN))
@pytest.mark.parametrize("name", list(SUFFIXES))
def test_leaked_ids_are_removed_from_every_text_field(
    workflow: Workflow, name: str
) -> None:
    """The outcome equals the one from clean output; no 64-hex id remains."""
    expected = run(workflow, CLEAN[workflow]())
    leaked = leak(CLEAN[workflow](), SUFFIXES[name])
    assert HEX64.search(json.dumps(leaked)), "test must leak ids"

    outcome = run(workflow, leaked)

    assert outcome == expected
    assert not any(i.lower() in repr(outcome).lower() for i in (ID1, ID2, ID3))


@pytest.mark.parametrize("workflow", list(CLEAN))
def test_citations_are_not_touched_by_sanitizing(workflow: Workflow) -> None:
    """citation_chunk_ids keep their values even when text leaks ids."""
    outcome = run(workflow, leak(CLEAN[workflow](), SUFFIXES["comma_group"]))
    expected = run(workflow, CLEAN[workflow]())
    assert outcome.claims == expected.claims
    assert outcome.payload == expected.payload


@pytest.mark.parametrize("workflow", list(CLEAN))
def test_field_that_becomes_empty_is_ungrounded(workflow: Workflow) -> None:
    """A field holding only ids is retried once, then fails the contract."""
    only_ids = f"[{ID1}]\n[{ID2}]"
    output = CLEAN[workflow]()
    output["answer"] = only_ids
    instance, transport, _ = provider([completion(output), completion(output)])
    evidence = {
        "research_question": RQ_EVIDENCE,
        "evidence_comparison": cmp.EVIDENCE,
        "conflicting_evidence": cfl.EVIDENCE,
        "research_gap": gap.EVIDENCE,
    }[workflow]
    with pytest.raises(ResponseContractFailure):
        instance.answer(QUESTION, evidence, CORPUS, "r", workflow=workflow)
    assert len(transport.calls) == 2


def test_comparison_subject_summary_that_becomes_empty_is_ungrounded() -> None:
    """An id-only subject summary retries once, then fails."""
    output = cmp.model_output()
    output["subjects"][0]["summary"] = f"[{ID1}]"
    instance, transport, _ = provider([completion(output)] * 2)
    with pytest.raises(ResponseContractFailure):
        instance.answer(
            QUESTION, cmp.EVIDENCE, CORPUS, "r", workflow="evidence_comparison"
        )
    assert len(transport.calls) == 2


def test_conflict_topic_that_becomes_empty_is_ungrounded() -> None:
    """An id-only conflict topic retries once, then fails."""
    output = cfl.model_output()
    output["items"][0]["topic"] = f"({ID1})"
    instance, transport, _ = provider([completion(output)] * 2)
    with pytest.raises(ResponseContractFailure):
        instance.answer(
            QUESTION, cfl.EVIDENCE, CORPUS, "r", workflow="conflicting_evidence"
        )
    assert len(transport.calls) == 2


def test_gap_hypothesis_rationale_that_becomes_empty_is_ungrounded() -> None:
    """An id-only rationale retries once, then fails."""
    output = gap.model_output()
    output["hypotheses"][0]["rationale"] = f"[{ID1}]"
    instance, transport, _ = provider([completion(output)] * 2)
    with pytest.raises(ResponseContractFailure):
        instance.answer(
            QUESTION, gap.EVIDENCE, CORPUS, "r", workflow="research_gap"
        )
    assert len(transport.calls) == 2


@pytest.mark.parametrize("workflow", list(WORKFLOW_PROMPTS))
def test_built_request_forbids_ids_and_brackets_in_text(
    workflow: Workflow,
) -> None:
    """The system message of every workflow carries the no-ids rule."""
    messages = build_messages(
        task_instructions=WORKFLOW_PROMPTS[workflow].task_instructions,
        question=QUESTION,
        evidence=RQ_EVIDENCE,
    )
    system = messages[0]["content"]
    assert "Never write chunk ids, bracketed references of any kind" in system
    assert "ONLY in the citation_chunk_ids" in system
    assert GROUNDING_RULES in system


@pytest.mark.parametrize("workflow", list(WORKFLOW_PROMPTS))
def test_sent_payload_carries_the_rule(workflow: Workflow) -> None:
    """The recorded request itself contains the rule."""
    instance, transport, _ = provider([completion(CLEAN[workflow]())])
    evidence = {
        "research_question": RQ_EVIDENCE,
        "evidence_comparison": cmp.EVIDENCE,
        "conflicting_evidence": cfl.EVIDENCE,
        "research_gap": gap.EVIDENCE,
    }[workflow]
    instance.answer(QUESTION, evidence, CORPUS, "r", workflow=workflow)
    payload: Any = transport.calls[0].payload
    assert (
        "bracketed references of any kind" in payload["messages"][0]["content"]
    )


class TestStripChunkIds:
    """Unit tests of the pure sanitizer."""

    def test_removes_bracketed_id_and_fixes_spacing(self) -> None:
        """Removes bracketed id and fixes spacing."""
        assert strip_chunk_ids(f"No difference [{ID1}] .") == "No difference."

    def test_removes_bare_id_mid_sentence(self) -> None:
        """Removes bare id mid sentence."""
        assert strip_chunk_ids(f"As in {ID1} the data agree.") == (
            "As in the data agree."
        )

    def test_removes_group_with_separators_and_newlines(self) -> None:
        """Removes group with separators and newlines."""
        text = f"Same. [{ID1},\n {ID2} ;{ID3}]"
        assert strip_chunk_ids(text) == "Same."

    def test_keeps_short_bracketed_numbers(self) -> None:
        """Keeps short bracketed numbers."""
        text = "Earlier work [20] and [3, 4] agrees (2019)."
        assert strip_chunk_ids(text) == text

    def test_keeps_longer_hex_runs(self) -> None:
        """Keeps longer hex runs."""
        text = "digest " + "a" * 65
        assert strip_chunk_ids(text) == text

    def test_removes_empty_brackets_left_behind(self) -> None:
        """Removes empty brackets left behind."""
        assert strip_chunk_ids(f"Text ([{ID1}]) end.") == "Text end."

    def test_only_ids_gives_empty(self) -> None:
        """Only ids gives empty."""
        assert strip_chunk_ids(f"[{ID1}] [{ID2}]") == ""

    def test_clean_text_is_unchanged(self) -> None:
        """Clean text is unchanged."""
        assert strip_chunk_ids("A plain sentence.") == "A plain sentence."
