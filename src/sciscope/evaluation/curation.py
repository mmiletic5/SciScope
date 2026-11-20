"""Source-level validation for Golden v1 and its private sidecar."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

from sciscope.evaluation.golden import (
    GoldenDataError,
    validate_curation_manifest,
    validate_dataset,
    validate_functionality_sidecar,
    validate_v1_coverage,
)
from sciscope.evaluation.protection import (
    ProtectedDataError,
    validate_v1_slot_categories,
    validate_v1_slot_functionalities,
    validate_v1_slot_partitions,
)
from sciscope.plos_pilot.doi import normalize_doi


class CurationValidationError(ValueError):
    """Sanitized source-grounding or sidecar validation failure."""


def validate_evidence_reference(
    reference: Mapping[str, Any],
    chunks_by_id: Mapping[str, Mapping[str, Any]],
    papers_by_doi: Mapping[str, Mapping[str, Any]],
) -> None:
    """Require one sidecar reference to reproduce its frozen source chunk."""
    chunk_id = reference.get("chunk_id")
    chunk = chunks_by_id.get(cast(str, chunk_id))
    if not isinstance(chunk_id, str) or chunk is None:
        raise CurationValidationError("evidence chunk is not in frozen corpus")

    try:
        same_doi = normalize_doi(cast(str, reference.get("doi"))).doi == (
            normalize_doi(cast(str, chunk.get("doi"))).doi
        )
    except (TypeError, ValueError) as error:
        raise CurationValidationError("evidence DOI is invalid") from error
    if not same_doi:
        raise CurationValidationError("evidence DOI does not match source")
    doi = normalize_doi(cast(str, reference.get("doi"))).doi
    paper = papers_by_doi.get(doi)
    if paper is None:
        raise CurationValidationError("source paper metadata is unavailable")
    source_xml_sha256 = chunk.get("xml_sha256")
    if (
        not isinstance(source_xml_sha256, str)
        or reference.get("source_xml_sha256") != source_xml_sha256
        or paper.get("xml_sha256") != source_xml_sha256
    ):
        raise CurationValidationError("source XML identity does not match")
    if reference.get("source_url") != paper.get("source_url"):
        raise CurationValidationError(
            "source URL does not match corpus metadata"
        )

    section_path = chunk.get("section_path")
    if not isinstance(section_path, list) or any(
        not isinstance(item, str) or not item for item in section_path
    ):
        raise CurationValidationError("source section path is unavailable")
    if reference.get("section") != " > ".join(section_path):
        raise CurationValidationError("evidence section does not match source")

    locators: set[str] = set()
    source_locator = chunk.get("source_locator")
    if isinstance(source_locator, str):
        locators.add(source_locator)
    spans = chunk.get("spans")
    if isinstance(spans, list):
        locators.update(
            cast(str, span["source_locator"])
            for span in spans
            if isinstance(span, dict)
            and isinstance(span.get("source_locator"), str)
        )
    if reference.get("source_locator") not in locators:
        raise CurationValidationError("evidence locator does not match source")

    source_text = chunk.get("text")
    if (
        not isinstance(source_text, str)
        or reference.get("source_passage") != source_text
    ):
        raise CurationValidationError("source passage differs from corpus")
    quotation = reference.get("quotation")
    if not isinstance(quotation, str) or not quotation:
        raise CurationValidationError("evidence quotation is missing")
    if quotation not in source_text:
        raise CurationValidationError("evidence quotation is not exact")

    label = reference.get("relevance_label")
    if label not in {"0", "1", "2", "3"}:
        raise CurationValidationError("evidence relevance label is invalid")
    rationale = reference.get("relevance_rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        raise CurationValidationError("evidence relevance rationale is missing")


def validate_sidecar_schema(
    sidecar: Mapping[str, Any],
    schema_path: Path,
    *,
    expected_ids: frozenset[str],
) -> None:
    """Validate the private sidecar schema and exact question ID relation."""
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        errors = tuple(Draft202012Validator(schema).iter_errors(sidecar))
    except (OSError, UnicodeError, ValueError, TypeError) as error:
        raise CurationValidationError(
            "functionality sidecar schema is unavailable or invalid"
        ) from error
    if errors:
        raise CurationValidationError(
            "functionality sidecar does not match its versioned schema"
        )
    annotations = sidecar.get("annotations")
    if not isinstance(annotations, list):
        raise CurationValidationError("functionality annotations are missing")
    ids = [
        annotation.get("question_id")
        for annotation in annotations
        if isinstance(annotation, dict)
    ]
    if len(ids) != len(annotations) or len(ids) != len(set(ids)):
        raise CurationValidationError("sidecar question IDs are duplicated")
    if set(ids) != expected_ids:
        raise CurationValidationError("sidecar question IDs do not match")


def validate_v1_artifacts(
    *,
    dataset: Mapping[str, Any],
    sidecar: Mapping[str, Any],
    curation_manifest: Mapping[str, Any],
    golden_schema_path: Path,
    sidecar_schema_path: Path,
    corpus_dois: frozenset[str],
    chunks_by_id: Mapping[str, Mapping[str, Any]],
    papers_by_doi: Mapping[str, Mapping[str, Any]],
    slot_by_question_id: Mapping[str, str],
) -> dict[str, Any]:
    """Validate all candidates and return content-free summary metadata."""
    questions_value = dataset.get("questions")
    if not isinstance(questions_value, list) or any(
        not isinstance(question, dict) for question in questions_value
    ):
        raise CurationValidationError("candidate question list is malformed")
    questions = cast(list[dict[str, Any]], questions_value)
    if (
        dataset.get("dataset_version") != "golden-v1"
        or dataset.get("corpus_version") != "pilot17-xml-1fff1573b610"
        or curation_manifest.get("dataset_version") != "golden-v1"
        or curation_manifest.get("corpus_version") != "pilot17-xml-1fff1573b610"
    ):
        raise CurationValidationError("dataset or corpus version mismatch")
    expected_ids = frozenset(
        cast(str, question["question_id"]) for question in questions
    )
    if set(slot_by_question_id) != expected_ids:
        raise CurationValidationError("question slots are incomplete")
    slot_partitions = {
        slot: _partition_for_slot(slot) for slot in slot_by_question_id.values()
    }
    try:
        validate_v1_slot_partitions(slot_partitions)
    except ProtectedDataError as error:
        raise CurationValidationError(
            "fixed partition assignment mismatch"
        ) from error

    try:
        validate_dataset(dataset, golden_schema_path, corpus_dois=corpus_dois)
        validate_sidecar_schema(
            sidecar, sidecar_schema_path, expected_ids=expected_ids
        )
        validate_functionality_sidecar(sidecar, expected_ids=expected_ids)
        validate_v1_coverage(questions, sidecar, corpus_dois=corpus_dois)
        validate_curation_manifest(curation_manifest, expected_ids=expected_ids)
    except GoldenDataError as error:
        raise CurationValidationError(
            "Golden v1 candidate validation failed"
        ) from error

    annotations = cast(list[dict[str, Any]], sidecar["annotations"])
    annotation_by_id = {
        cast(str, item["question_id"]): item for item in annotations
    }
    slot_by_slot = {
        slot_by_question_id[question_id]: question_id
        for question_id in expected_ids
    }
    slot_categories = {
        slot: cast(
            str,
            next(
                question["question_type"]
                for question in questions
                if question["question_id"] == question_id
            ),
        )
        for slot, question_id in slot_by_slot.items()
    }
    slot_functionalities = {
        slot_by_question_id[cast(str, annotation["question_id"])]: cast(
            list[str], annotation["functionalities"]
        )
        for annotation in annotations
    }
    try:
        validate_v1_slot_categories(slot_categories)
        validate_v1_slot_functionalities(slot_functionalities)
    except ProtectedDataError as error:
        raise CurationValidationError(
            "fixed category/functionality assignment mismatch"
        ) from error
    category_counts: dict[str, int] = {}
    functionality_counts: dict[str, int] = {}
    source_dois: set[str] = set()
    reference_count = 0
    for question in questions:
        question_id = cast(str, question["question_id"])
        slot = slot_by_question_id[question_id]
        annotation = annotation_by_id[question_id]
        if question.get("source_corpus_version") != dataset["corpus_version"]:
            raise CurationValidationError(
                "question source corpus version mismatch"
            )
        if annotation.get("slot") != slot:
            raise CurationValidationError(
                "sidecar slot does not match frozen map"
            )
        if annotation.get("partition") != _partition_for_slot(slot):
            raise CurationValidationError(
                "sidecar partition does not match frozen map"
            )
        insufficient = question.get("expected_insufficient_evidence") is True
        expected_answerability = (
            "insufficient_evidence" if insufficient else "answerable"
        )
        if annotation.get("answerability") != expected_answerability:
            raise CurationValidationError(
                "sidecar answerability does not match"
            )

        references_value = annotation.get("evidence_references")
        if not isinstance(references_value, list) or not references_value:
            raise CurationValidationError(
                "source evidence annotations are missing"
            )
        refs = cast(list[dict[str, Any]], references_value)
        ref_ids: set[str] = set()
        labels: list[str] = []
        for reference in refs:
            validate_evidence_reference(reference, chunks_by_id, papers_by_doi)
            reference_id = cast(str, reference["evidence_reference_id"])
            if reference_id in ref_ids:
                raise CurationValidationError(
                    "evidence reference IDs are duplicated"
                )
            ref_ids.add(reference_id)
            labels.append(cast(str, reference["relevance_label"]))
            source_dois.add(normalize_doi(cast(str, reference["doi"])).doi)
        functions = cast(list[str], annotation["functionalities"])
        if "conflicting_evidence_finder" in functions:
            assessment = annotation["expected_output"].get(
                "conflict_assessment"
            )
            doi_count = len(
                {normalize_doi(cast(str, item["doi"])).doi for item in refs}
            )
            if (
                slot not in {"Q4", "Q5"}
                or question.get("question_type") != "multi_paper_comparison"
                or not isinstance(assessment, dict)
                or assessment.get("finding_relationship")
                not in {"apparent_contrast", "non_equivalent"}
                or assessment.get("decision") != "do_not_report_conflict"
                or assessment.get("negative_control") is not True
                or doi_count < 2
            ):
                raise CurationValidationError(
                    "Conflict Finder cases must be approved negative controls"
                )
        if insufficient and any(label in {"2", "3"} for label in labels):
            raise CurationValidationError(
                "insufficient question contains positive evidence"
            )
        if not insufficient and not any(
            label in {"2", "3"} for label in labels
        ):
            raise CurationValidationError(
                "answerable question lacks positive source evidence"
            )
        _validate_output_references(annotation["expected_output"], ref_ids)
        _validate_golden_evidence_alignment(question, refs)
        category = cast(str, question["question_type"])
        category_counts[category] = category_counts.get(category, 0) + 1
        for function in cast(list[str], annotation["functionalities"]):
            functionality_counts[function] = (
                functionality_counts.get(function, 0) + 1
            )
        reference_count += len(refs)

    return {
        "validation_status": "pass",
        "question_count": len(questions),
        "category_counts": dict(sorted(category_counts.items())),
        "partition_counts": {"development": 3, "held_out": 6},
        "functionality_question_counts": dict(
            sorted(functionality_counts.items())
        ),
        "source_doi_count": len(source_dois),
        "evidence_reference_count": reference_count,
        "golden_schema_changed": False,
    }


def _partition_for_slot(slot: str) -> str:
    if slot in {"Q1", "Q4", "Q6"}:
        return "development"
    if slot in {"Q2", "Q3", "Q5", "Q7", "Q8", "Q9"}:
        return "held_out"
    raise CurationValidationError("unknown preregistered slot")


def _validate_output_references(
    expected_output: Mapping[str, Any], reference_ids: set[str]
) -> None:
    def visit(value: object, key: str = "") -> None:
        if isinstance(value, Mapping):
            for child_key, child in value.items():
                visit(child, cast(str, child_key))
        elif isinstance(value, Sequence) and not isinstance(
            value, (str, bytes, bytearray)
        ):
            if key.endswith("evidence_reference_ids") or key in {
                "supporting_evidence_ids",
            }:
                if any(
                    not isinstance(item, str) or item not in reference_ids
                    for item in value
                ):
                    raise CurationValidationError(
                        "expected output links to unknown evidence"
                    )
            else:
                for item in value:
                    visit(item)

    visit(expected_output)


def _validate_golden_evidence_alignment(
    question: Mapping[str, Any],
    sidecar_references: Sequence[Mapping[str, Any]],
) -> None:
    sidecar_keys = {
        (
            normalize_doi(cast(str, item["doi"])).doi,
            cast(str, item["source_locator"]),
            cast(str, item["quotation"]),
            cast(str, item["relevance_label"]),
        )
        for item in sidecar_references
    }
    paper_records = question.get("relevant_papers")
    if not isinstance(paper_records, list):
        raise CurationValidationError(
            "Golden evidence references are malformed"
        )
    for paper in paper_records:
        if not isinstance(paper, dict):
            raise CurationValidationError("Golden source record is malformed")
        doi = normalize_doi(cast(str, paper.get("doi"))).doi
        evidence = paper.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise CurationValidationError("Golden source evidence is missing")
        for item in evidence:
            if not isinstance(item, dict):
                raise CurationValidationError("Golden evidence is malformed")
            key = (
                doi,
                cast(str, item.get("source_locator", "")),
                cast(str, item.get("quotation", "")),
                cast(str, item.get("relevance_label", "")),
            )
            if key not in sidecar_keys:
                raise CurationValidationError(
                    "Golden and sidecar evidence annotations differ"
                )
