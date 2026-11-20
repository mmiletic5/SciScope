"""Behavior tests for Phase D Golden loading and partition controls."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sciscope.evaluation.golden import (
    GoldenDataError,
    load_allowlisted_records,
    partition_sha256,
    validate_dataset,
    validate_partitions,
    validate_v1_coverage,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "evals" / "golden_questions.schema.json"


def _question(question_id: str) -> dict[str, object]:
    return {
        "question_id": question_id,
        "question": "Synthetic fixture question?",
        "query_language": "en",
        "expected_findings": "Synthetic fixture finding.",
        "relevant_papers": [
            {
                "doi": "10.1234/synthetic",
                "sections": ["Results"],
                "evidence": [
                    {
                        "relevance_label": "3",
                        "source_locator": "Results/p1",
                        "quotation": "Synthetic evidence.",
                    }
                ],
            }
        ],
        "question_type": "single_paper_factual",
        "expected_insufficient_evidence": False,
        "reviewer": "ChatGPT (synthetic fixture; no scientific review)",
        "verification_status": "in_review",
        "source_corpus_version": "synthetic-corpus",
    }


def _dataset(questions: list[dict[str, object]]) -> dict[str, object]:
    return {
        "dataset_version": "synthetic-v1",
        "corpus_version": "synthetic-corpus",
        "questions": questions,
    }


def test_loader_never_decodes_nonallowlisted_question_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Malformed nonallowlisted records are discarded before JSON decoding."""
    import sciscope.evaluation.golden as golden

    allowed = json.dumps(_question("dev-001"), separators=(",", ":"))
    source = tmp_path / "synthetic.json"
    source.write_text(
        '{"dataset_version":"synthetic-v1","corpus_version":"synthetic-corpus",'
        f'"questions":[{allowed},'
        '{"question_id":"held-001","question":not-json}]}',
        encoding="utf-8",
    )
    decoded_records: list[str] = []
    original_loads = golden.json.loads

    def observe_loads(value: str, *args: object, **kwargs: object) -> object:
        if isinstance(value, str) and value.startswith("{"):
            decoded_records.append(value)
        return original_loads(value, *args, **kwargs)

    monkeypatch.setattr(golden.json, "loads", observe_loads)
    records = load_allowlisted_records(source, frozenset({"dev-001"}))

    assert [item["question_id"] for item in records] == ["dev-001"]
    assert len(decoded_records) == 1
    assert '"question_id":"dev-001"' in decoded_records[0]


def test_loader_rejects_missing_duplicate_and_oversized_allowlisted_records(
    tmp_path: Path,
) -> None:
    """Requested identities are exact and allowed records remain bounded."""
    source = tmp_path / "synthetic.json"
    first = json.dumps(_question("dev-001"), separators=(",", ":"))

    source.write_text('{"questions":[' + first + "]}", encoding="utf-8")
    with pytest.raises(GoldenDataError, match="allowlist"):
        load_allowlisted_records(source, frozenset({"dev-001", "dev-002"}))

    source.write_text(
        '{"questions":[' + first + "," + first + "]}", encoding="utf-8"
    )
    with pytest.raises(GoldenDataError, match="duplicate"):
        load_allowlisted_records(source, frozenset({"dev-001"}))

    source.write_text('{"questions":[' + first + "]}", encoding="utf-8")
    with pytest.raises(GoldenDataError, match="size"):
        load_allowlisted_records(
            source, frozenset({"dev-001"}), max_record_bytes=24
        )


def test_dataset_uses_unchanged_golden_schema() -> None:
    """The P2 validator accepts truthful in-review schema-compatible data."""
    document = _dataset([_question("dev-001")])

    validate_dataset(document, SCHEMA_PATH)


def test_partition_validation_and_hash_are_deterministic() -> None:
    """Partitions are disjoint, exhaustive, and hashed in stable ID order."""
    partitions = {"development": ("q3", "q1"), "held_out": ("q2",)}

    validate_partitions(partitions, expected_ids=frozenset({"q1", "q2", "q3"}))

    assert partition_sha256(partitions["development"]) == partition_sha256(
        ("q1", "q3")
    )
    with pytest.raises(GoldenDataError, match="overlap"):
        validate_partitions(
            {"development": ("q1",), "held_out": ("q1",)},
            expected_ids=frozenset({"q1"}),
        )


def test_amended_v1_matrix_and_function_coverage_are_enforced() -> None:
    """Nine synthetic rows meet the matrix and two-case/function minimum."""
    categories = (
        "insufficient_evidence",
        "insufficient_evidence",
        "insufficient_evidence",
        "multi_paper_comparison",
        "multi_paper_comparison",
        "research_gap",
        "research_gap",
        "single_paper_factual",
        "multi_paper_comparison",
    )
    questions = [_question(f"q{index}") for index in range(1, 10)]
    for question, category in zip(questions, categories, strict=True):
        question["question_type"] = category
        if category == "insufficient_evidence":
            question["expected_insufficient_evidence"] = True
            question["relevant_papers"][0]["evidence"][0]["relevance_label"] = (
                "1"
            )
    for index in (3, 4, 8):
        questions[index]["relevant_papers"].append(
            {
                "doi": "10.5678/second",
                "sections": ["Results"],
                "evidence": [
                    {
                        "relevance_label": "3",
                        "source_locator": "Results/p2",
                        "quotation": "Second synthetic evidence.",
                    }
                ],
            }
        )

    explorer = "research_question_explorer"
    comparison = "evidence_comparison"
    conflict = "conflicting_evidence_finder"
    gap = "research_gap_hypothesis_assistant"
    coverage = (
        (explorer,),
        (explorer,),
        (explorer,),
        (conflict, comparison),
        (conflict,),
        (gap,),
        (gap,),
        (explorer,),
        (comparison,),
    )
    annotations = []
    for question, functions in zip(questions, coverage, strict=True):
        output: dict[str, object] = {}
        if explorer in functions:
            output.update(
                claim_evidence_links=[
                    {"claim_id": "c1", "evidence_reference_ids": ["e1"]}
                ],
                expected_disposition=(
                    "qualify"
                    if question["expected_insufficient_evidence"]
                    else "answer"
                ),
            )
        if comparison in functions:
            output["paper_comparisons"] = [
                {
                    "doi": "10.1234/synthetic",
                    "objective": "Objective.",
                    "methods": "Methods.",
                    "conditions": "Conditions.",
                    "outcomes": "Outcomes.",
                    "limitations": "not_reported",
                    "evidence_reference_ids": ["e1"],
                },
                {
                    "doi": "10.5678/second",
                    "objective": "Objective.",
                    "methods": "Methods.",
                    "conditions": "Conditions.",
                    "outcomes": "Outcomes.",
                    "limitations": "not_reported",
                    "evidence_reference_ids": ["e2"],
                },
            ]
        if conflict in functions:
            output["contrasted_findings"] = [
                {
                    "doi": "10.1234/synthetic",
                    "finding": "Finding one.",
                    "evidence_reference_ids": ["e1"],
                },
                {
                    "doi": "10.5678/second",
                    "finding": "Finding two.",
                    "evidence_reference_ids": ["e2"],
                },
            ]
            output["methodological_explanations"] = [
                {
                    "status": "plausible_but_unverified",
                    "evidence_reference_ids": [],
                }
            ]
            output["conflict_assessment"] = {
                "finding_relationship": "non_equivalent",
                "decision": "do_not_report_conflict",
                "negative_control": True,
                "rationale": (
                    "Synthetic findings concern non-equivalent conditions."
                ),
                "evidence_reference_ids": ["e1", "e2"],
            }
        if gap in functions:
            output.update(
                gap_statement="A bounded synthetic gap.",
                gap_scope="Synthetic corpus only.",
                supporting_evidence_ids=["e1"],
                candidate_research_question=(
                    "Could the synthetic result replicate?"
                ),
                candidate_hypothesis=(
                    "The result may replicate under the stated conditions."
                ),
                assumptions=["Synthetic assumption."],
                uncertainties=["Synthetic uncertainty."],
                evidence_needed_to_test=["A further synthetic study."],
            )
        annotations.append(
            {
                "question_id": question["question_id"],
                "primary_functionality": functions[0],
                "functionalities": list(functions),
                "expected_output": output,
            }
        )
    sidecar = {
        "schema_version": "golden-functionality-v1",
        "annotations": annotations,
    }

    validate_v1_coverage(
        questions,
        sidecar,
        corpus_dois=frozenset({"10.1234/synthetic", "10.5678/second"}),
    )

    invalid_control = annotations[3]["expected_output"]
    assert isinstance(invalid_control, dict)
    invalid_control["conflict_assessment"]["decision"] = "report_conflict"
    with pytest.raises(GoldenDataError, match="negative control"):
        validate_v1_coverage(
            questions,
            sidecar,
            corpus_dois=frozenset({"10.1234/synthetic", "10.5678/second"}),
        )
    invalid_control["conflict_assessment"]["decision"] = (
        "do_not_report_conflict"
    )

    for annotation in sidecar["annotations"][:3]:
        annotation["functionalities"] = [gap]
        annotation["primary_functionality"] = gap
        annotation["expected_output"] = {
            "gap_statement": "A gap.",
            "gap_scope": "Scope.",
            "supporting_evidence_ids": ["e1"],
            "candidate_research_question": "Question?",
            "candidate_hypothesis": "Hypothesis.",
            "assumptions": ["A"],
            "uncertainties": ["U"],
            "evidence_needed_to_test": ["E"],
        }
    with pytest.raises(GoldenDataError, match="coverage"):
        validate_v1_coverage(
            questions,
            sidecar,
            corpus_dois=frozenset({"10.1234/synthetic", "10.5678/second"}),
        )
