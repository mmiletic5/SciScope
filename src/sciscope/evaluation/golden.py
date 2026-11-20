"""Strict Golden dataset validation and protected allowlist loading."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

from sciscope.plos_pilot.doi import normalize_doi

_QUESTION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_LABELS = {"0", "1", "2", "3"}
_FUNCTIONALITIES = {
    "research_question_explorer",
    "evidence_comparison",
    "conflicting_evidence_finder",
    "research_gap_hypothesis_assistant",
}
_V1_CATEGORY_COUNTS = {
    "insufficient_evidence": 3,
    "conflicting_evidence": 0,
    "research_gap": 2,
    "single_paper_factual": 1,
    "multi_paper_comparison": 3,
}
_MAX_ID_PREFIX_BYTES = 512
_READ_SIZE = 4096


class GoldenDataError(ValueError):
    """Sanitized Golden dataset, partition, or provenance validation error."""


def load_allowlisted_records(
    path: Path,
    allowed_ids: frozenset[str],
    *,
    max_record_bytes: int = 1_000_000,
) -> list[dict[str, Any]]:
    """Decode only question records whose top-level ID is explicitly allowed.

    The reader scans bounded byte chunks and discards non-allowlisted records
    after reading only their top-level question ID. It never decodes their JSON.

    Args:
        path: JSON dataset path.
        allowed_ids: Exact question IDs authorized for this operation.
        max_record_bytes: Maximum bytes retained for one allowed record.

    Returns:
        Allowed records in source order.

    Raises:
        GoldenDataError: If the stream is malformed, IDs are missing or
            duplicated, the requested set is incomplete, or a record exceeds
            the configured bound.
    """
    if not allowed_ids or any(
        not isinstance(item, str)
        or _QUESTION_ID.fullmatch(item) is None
        or not item.isascii()
        for item in allowed_ids
    ):
        raise GoldenDataError("invalid question allowlist")
    if max_record_bytes < 1:
        raise GoldenDataError("record size limit must be positive")

    allowed_bytes = {item.encode("ascii"): item for item in allowed_ids}
    records: dict[str, dict[str, Any]] = {}
    stream_curly = 0
    stream_square = 0
    in_string = False
    escaped = False
    root_expect_key = False
    root_capture_key = False
    root_key_bytes = bytearray()
    root_questions_key = False
    root_value_expected = False
    in_questions_array = False
    record_curly = 0
    record_square = 0
    record_buffer = bytearray()
    record_id: str | None = None
    record_allowed: bool | None = None
    record_expect_key = False
    record_capture_key = False
    record_key_bytes = bytearray()
    record_expect_id_value = False
    record_capture_id = False
    record_id_bytes = bytearray()
    record_bytes_seen = 0

    def decode_json_string(value: bytearray) -> str:
        decoded = json.loads(b'"' + bytes(value) + b'"')
        if not isinstance(decoded, str):
            raise GoldenDataError("invalid question identity string")
        return decoded

    try:
        with path.open("rb") as source:
            while chunk := source.read(_READ_SIZE):
                for byte in chunk:
                    starts_record = (
                        not in_string
                        and in_questions_array
                        and stream_curly == 1
                        and stream_square == 1
                        and byte == ord("{")
                    )
                    if starts_record:
                        record_curly = 1
                        record_square = 0
                        record_buffer = bytearray(b"{")
                        record_id = None
                        record_allowed = None
                        record_expect_key = True
                        record_capture_key = False
                        record_key_bytes.clear()
                        record_expect_id_value = False
                        record_capture_id = False
                        record_id_bytes.clear()
                        record_bytes_seen = 1
                        stream_curly += 1
                        continue

                    if record_curly > 0:
                        record_bytes_seen += 1
                        if record_allowed is True:
                            record_buffer.append(byte)
                            if record_bytes_seen > max_record_bytes:
                                raise GoldenDataError(
                                    "allowlisted record exceeds size limit"
                                )
                        elif record_allowed is None:
                            record_buffer.append(byte)
                            if len(record_buffer) > _MAX_ID_PREFIX_BYTES:
                                raise GoldenDataError(
                                    "question ID missing or too far into record"
                                )

                    if in_string:
                        if record_curly == 1 and record_square == 0:
                            if record_capture_key:
                                record_key_bytes.append(byte)
                            elif record_capture_id:
                                record_id_bytes.append(byte)
                        if stream_curly == 1 and stream_square == 0:
                            if root_capture_key:
                                root_key_bytes.append(byte)
                        if escaped:
                            escaped = False
                        elif byte == ord("\\"):
                            escaped = True
                        elif byte == ord('"'):
                            in_string = False
                            if record_capture_key:
                                key = decode_json_string(record_key_bytes[:-1])
                                record_capture_key = False
                                record_key_bytes.clear()
                                record_expect_id_value = key == "question_id"
                            elif record_capture_id:
                                raw_id = decode_json_string(
                                    record_id_bytes[:-1]
                                )
                                record_capture_id = False
                                record_id_bytes.clear()
                                try:
                                    record_id = allowed_bytes.get(
                                        raw_id.encode("ascii")
                                    )
                                except UnicodeEncodeError:
                                    record_id = None
                                record_allowed = record_id is not None
                                if record_allowed:
                                    assert record_id is not None
                                    if record_id in records:
                                        raise GoldenDataError(
                                            "duplicate question ID in allowlist"
                                        )
                                else:
                                    record_buffer.clear()
                            elif root_capture_key:
                                root_key = decode_json_string(
                                    root_key_bytes[:-1]
                                )
                                root_capture_key = False
                                root_key_bytes.clear()
                                root_questions_key = root_key == "questions"
                            continue
                        continue

                    if byte == ord('"'):
                        in_string = True
                        escaped = False
                        if record_curly == 1 and record_square == 0:
                            if record_expect_key:
                                record_capture_key = True
                                record_key_bytes.clear()
                                record_expect_key = False
                            elif record_expect_id_value:
                                record_capture_id = True
                                record_id_bytes.clear()
                                record_expect_id_value = False
                        elif stream_curly == 1 and stream_square == 0:
                            if root_expect_key:
                                root_capture_key = True
                                root_key_bytes.clear()
                                root_expect_key = False
                        continue

                    if record_curly > 0:
                        if byte == ord("{"):
                            record_curly += 1
                        elif byte == ord("}"):
                            record_curly -= 1
                        elif byte == ord("["):
                            record_square += 1
                        elif byte == ord("]"):
                            record_square -= 1
                        elif (
                            byte == ord(",")
                            and record_curly == 1
                            and record_square == 0
                        ):
                            record_expect_key = True
                            record_expect_id_value = False
                        if record_curly == 0:
                            if record_allowed is None:
                                raise GoldenDataError(
                                    "top-level question ID missing"
                                )
                            if record_allowed:
                                assert record_id is not None
                                record = json.loads(
                                    record_buffer.decode("utf-8")
                                )
                                if (
                                    not isinstance(record, dict)
                                    or record.get("question_id") != record_id
                                ):
                                    raise GoldenDataError(
                                        "decoded question ID does not match"
                                    )
                                records[record_id] = cast(
                                    dict[str, Any], record
                                )
                            record_buffer.clear()
                            record_id = None
                            record_allowed = None
                        stream_curly += 1 if byte == ord("{") else 0
                        stream_curly -= 1 if byte == ord("}") else 0
                        stream_square += 1 if byte == ord("[") else 0
                        stream_square -= 1 if byte == ord("]") else 0
                        continue

                    if stream_curly == 1 and stream_square == 0:
                        if byte == ord(":") and root_questions_key:
                            root_value_expected = True
                            root_questions_key = False
                        elif root_value_expected and byte in b" \t\r\n":
                            pass
                        elif root_value_expected and byte == ord("["):
                            in_questions_array = True
                            root_value_expected = False
                            stream_square += 1
                            continue
                        elif byte == ord(","):
                            root_expect_key = True
                            root_questions_key = False

                    if (
                        in_questions_array
                        and stream_curly == 1
                        and byte == ord("]")
                    ):
                        in_questions_array = False
                    if byte == ord("{"):
                        stream_curly += 1
                        if stream_curly == 1:
                            root_expect_key = True
                    elif byte == ord("}"):
                        stream_curly -= 1
                    elif byte == ord("["):
                        stream_square += 1
                    elif byte == ord("]"):
                        stream_square -= 1
                    if stream_curly < 0 or stream_square < 0:
                        raise GoldenDataError("malformed Golden JSON structure")
    except GoldenDataError:
        raise
    except (OSError, UnicodeError, ValueError, RecursionError) as error:
        raise GoldenDataError(
            "could not safely decode allowlisted records"
        ) from error

    if (
        in_string
        or stream_curly != 0
        or stream_square != 0
        or in_questions_array
    ):
        raise GoldenDataError("malformed Golden JSON structure")
    if records.keys() != allowed_ids:
        raise GoldenDataError("question allowlist is incomplete or duplicated")
    return list(records.values())


def validate_dataset(
    document: Mapping[str, Any],
    schema_path: Path,
    *,
    corpus_dois: frozenset[str] | None = None,
) -> None:
    """Validate Golden schema and stricter Phase D answerability rules.

    Args:
        document: Parsed dataset mapping.
        schema_path: Path to the unchanged project Golden JSON Schema.
        corpus_dois: Optional normalized DOI set for the frozen corpus.

    Raises:
        GoldenDataError: If schema or Phase D constraints fail.
    """
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        errors = sorted(
            Draft202012Validator(schema).iter_errors(document),
            key=lambda error: list(error.absolute_path),
        )
    except (OSError, ValueError, TypeError) as error:
        raise GoldenDataError("Golden schema could not be validated") from error
    if errors:
        raise GoldenDataError("Golden dataset does not match its schema")

    questions = document.get("questions")
    if not isinstance(questions, list):
        raise GoldenDataError("Golden questions must be a list")
    question_ids: list[str] = []
    for question in questions:
        if not isinstance(question, dict):
            raise GoldenDataError("Golden question must be an object")
        question_id = question.get("question_id")
        question_ids.append(cast(str, question_id))
        question_type = question.get("question_type")
        insufficient_flag = question.get("expected_insufficient_evidence")
        if "question_type" not in question or not isinstance(
            insufficient_flag, bool
        ):
            raise GoldenDataError(
                "Phase D question type and answerability are required"
            )
        if (question_type == "insufficient_evidence") != insufficient_flag:
            raise GoldenDataError("question type conflicts with answerability")
        if question.get("verification_status") != "in_review":
            raise GoldenDataError("Phase D candidate must remain in_review")
        if "verified_date" in question:
            raise GoldenDataError("AI review cannot set a human verified date")
        if "ChatGPT" not in cast(str, question.get("reviewer", "")):
            raise GoldenDataError(
                "reviewer must truthfully identify ChatGPT as AI"
            )

        relevant_labels = _positive_labels(question)
        insufficient = cast(bool, question["expected_insufficient_evidence"])
        if insufficient and relevant_labels:
            raise GoldenDataError(
                "insufficient-evidence question has positive evidence labels"
            )
        if not insufficient and not relevant_labels:
            raise GoldenDataError(
                "answerable question lacks valid positive ground truth"
            )
        if corpus_dois is not None:
            _validate_corpus_dois(question, corpus_dois)
    if len(question_ids) != len(set(question_ids)):
        raise GoldenDataError("question IDs must be unique")


def _positive_labels(question: Mapping[str, Any]) -> list[str]:
    labels: list[str] = []
    papers = question.get("relevant_papers")
    if not isinstance(papers, list):
        return labels
    for paper in papers:
        if not isinstance(paper, dict):
            continue
        for evidence in paper.get("evidence", []):
            if isinstance(evidence, dict):
                label = evidence.get("relevance_label")
                if label in {"2", "3"}:
                    labels.append(cast(str, label))
                elif label not in _LABELS:
                    raise GoldenDataError(
                        "relevance label must be 0, 1, 2, or 3"
                    )
    return labels


def _validate_corpus_dois(
    question: Mapping[str, Any], corpus_dois: frozenset[str]
) -> None:
    papers = question.get("relevant_papers", [])
    if not papers:
        raise GoldenDataError(
            "every Golden v1 question must cite corpus sources"
        )
    for paper in papers:
        if not isinstance(paper, dict):
            continue
        doi = normalize_doi(cast(str, paper["doi"])).doi
        if doi not in corpus_dois:
            raise GoldenDataError("question DOI is outside frozen corpus")


def validate_v1_coverage(
    questions: Sequence[Mapping[str, Any]],
    sidecar: Mapping[str, Any],
    *,
    corpus_dois: frozenset[str],
) -> None:
    """Enforce the approved category matrix and minimum function coverage."""
    counts = {category: 0 for category in _V1_CATEGORY_COUNTS}
    if len(questions) != 9:
        raise GoldenDataError("Golden v1 must contain exactly nine questions")
    for question in questions:
        question_type = question.get("question_type")
        if question_type not in counts:
            raise GoldenDataError("unknown Golden v1 question category")
        counts[cast(str, question_type)] += 1
        _validate_corpus_dois(question, corpus_dois)
        if question_type in {"conflicting_evidence", "multi_paper_comparison"}:
            dois = {
                normalize_doi(cast(str, paper["doi"])).doi
                for paper in question.get("relevant_papers", [])
            }
            if len(dois) < 2:
                raise GoldenDataError(
                    "cross-paper question needs two source DOIs"
                )
    if counts != _V1_CATEGORY_COUNTS:
        raise GoldenDataError(
            "Golden v1 category matrix does not match approved counts"
        )

    expected_ids = frozenset(
        cast(str, item["question_id"]) for item in questions
    )
    validate_functionality_sidecar(sidecar, expected_ids=expected_ids)
    coverage: dict[str, set[str]] = {
        functionality: set() for functionality in _FUNCTIONALITIES
    }
    annotations = cast(list[dict[str, Any]], sidecar["annotations"])
    for annotation in annotations:
        question_id = cast(str, annotation["question_id"])
        for functionality in cast(list[str], annotation["functionalities"]):
            coverage[functionality].add(question_id)
    if any(len(question_ids) < 2 for question_ids in coverage.values()):
        raise GoldenDataError("functionality coverage is below two questions")


def validate_partitions(
    partitions: Mapping[str, Sequence[str]], *, expected_ids: frozenset[str]
) -> None:
    """Require disjoint, exhaustive, nonempty development and held-out IDs."""
    if set(partitions) != {"development", "held_out"}:
        raise GoldenDataError(
            "partition names must be development and held_out"
        )
    development = tuple(partitions["development"])
    held_out = tuple(partitions["held_out"])
    if not development or not held_out:
        raise GoldenDataError("both evaluation partitions must be nonempty")
    if len(development) != len(set(development)) or len(held_out) != len(
        set(held_out)
    ):
        raise GoldenDataError("partition IDs must be unique")
    if set(development) & set(held_out):
        raise GoldenDataError("development and held-out partitions overlap")
    if set(development) | set(held_out) != expected_ids:
        raise GoldenDataError("partitions are not exhaustive for dataset IDs")


def partition_sha256(question_ids: Sequence[str]) -> str:
    """Hash a partition's sorted, canonical UTF-8 JSON ID list."""
    if len(question_ids) != len(set(question_ids)):
        raise GoldenDataError("partition IDs must be unique")
    payload = json.dumps(
        sorted(question_ids), ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def validate_curation_manifest(
    manifest: Mapping[str, Any], *, expected_ids: frozenset[str]
) -> None:
    """Validate exact candidate provenance and truthful review state."""
    if manifest.get("manifest_version") != "golden-v1-curation-v1":
        raise GoldenDataError("unsupported curation manifest version")
    questions = manifest.get("questions")
    if not isinstance(questions, list):
        raise GoldenDataError("curation manifest questions must be a list")
    ids: list[str] = []
    for record in questions:
        if not isinstance(record, dict):
            raise GoldenDataError("curation manifest record must be an object")
        question_id = record.get("question_id")
        ids.append(cast(str, question_id))
        if record.get("creation_mode") not in {"ai_generated", "ai_assisted"}:
            raise GoldenDataError("creation mode must disclose AI involvement")
        if not isinstance(record.get("created_at_utc"), str):
            raise GoldenDataError("creation timestamp must be recorded")
        if not isinstance(record.get("tools"), list) or not record["tools"]:
            raise GoldenDataError("AI tools must be recorded")
        if not isinstance(record.get("tool_versions"), dict):
            raise GoldenDataError(
                "known tool versions or unknowns must be recorded"
            )
        if (
            not isinstance(record.get("source_inputs"), list)
            or not record["source_inputs"]
        ):
            raise GoldenDataError("frozen-pilot source inputs must be recorded")
        if (
            not isinstance(record.get("prompt_sha256"), str)
            or re.fullmatch(r"[0-9a-f]{64}", cast(str, record["prompt_sha256"]))
            is None
        ):
            raise GoldenDataError("prompt lineage hash is invalid")
        if not isinstance(record.get("draft_lineage"), list):
            raise GoldenDataError("AI draft lineage must be recorded")
        if (
            not isinstance(record.get("ai_contribution"), str)
            or not record["ai_contribution"].strip()
        ):
            raise GoldenDataError("AI contribution must be described")
        if not isinstance(record.get("correction_history"), list):
            raise GoldenDataError("correction history must be recorded")
        for correction in record["correction_history"]:
            if (
                not isinstance(correction, dict)
                or not isinstance(correction.get("corrected_at_utc"), str)
                or not isinstance(correction.get("reason"), str)
                or not isinstance(correction.get("fields_changed"), list)
                or not correction["fields_changed"]
                or not isinstance(correction.get("correction_spec_sha256"), str)
                or re.fullmatch(
                    r"[0-9a-f]{64}",
                    cast(str, correction["correction_spec_sha256"]),
                )
                is None
                or correction.get("review_status") != "pending"
            ):
                raise GoldenDataError(
                    "correction history must record rationale and pending "
                    "review"
                )
        if record.get("human_authored") is not False:
            raise GoldenDataError(
                "AI candidate cannot be labeled human-authored"
            )
        if record.get("verification_status") != "in_review":
            raise GoldenDataError("ChatGPT review is not human verification")
        if record.get("chatgpt_review_status") not in {
            "pending",
            "rejected",
            "approved",
        }:
            raise GoldenDataError("invalid ChatGPT model review status")
    if len(ids) != len(set(ids)) or set(ids) != expected_ids:
        raise GoldenDataError(
            "curation manifest IDs fail exact referential integrity"
        )
    if manifest.get("revision") == "golden-v1-curation-revision-2":
        revised_ids = {
            "golden-v1-q4",
            "golden-v1-q5",
            "golden-v1-q6",
            "golden-v1-q9",
        }
        by_id = {record["question_id"]: record for record in questions}
        if not revised_ids <= expected_ids or any(
            not by_id[question_id]["correction_history"]
            or by_id[question_id].get("chatgpt_review_status") != "pending"
            for question_id in revised_ids
        ):
            raise GoldenDataError(
                "revised candidate provenance or review state is incomplete"
            )
        amendment = manifest.get("amendment")
        if (
            not isinstance(amendment, dict)
            or amendment.get("owner_authorized") is not True
            or amendment.get("genuine_conflict_claims") != 0
        ):
            raise GoldenDataError("curation amendment provenance is invalid")


def validate_functionality_sidecar(
    sidecar: Mapping[str, Any], *, expected_ids: frozenset[str]
) -> None:
    """Require one valid functionality annotation per dataset question."""
    if sidecar.get("schema_version") != "golden-functionality-v1":
        raise GoldenDataError("unsupported functionality sidecar version")
    annotations = sidecar.get("annotations")
    if not isinstance(annotations, list):
        raise GoldenDataError("functionality annotations must be a list")
    ids: list[str] = []
    for annotation in annotations:
        if not isinstance(annotation, dict):
            raise GoldenDataError("functionality annotation must be an object")
        question_id = annotation.get("question_id")
        ids.append(cast(str, question_id))
        functions = annotation.get("functionalities")
        if (
            not isinstance(functions, list)
            or not functions
            or any(item not in _FUNCTIONALITIES for item in functions)
            or len(functions) != len(set(functions))
        ):
            raise GoldenDataError("invalid functionality tags")
        primary = annotation.get("primary_functionality")
        if primary not in functions:
            raise GoldenDataError(
                "primary functionality must be an assigned tag"
            )
        output = annotation.get("expected_output")
        if not isinstance(output, dict):
            raise GoldenDataError("functionality expected_output is required")
        for functionality in functions:
            _validate_expected_output(functionality, output)
    if len(ids) != len(set(ids)) or set(ids) != expected_ids:
        raise GoldenDataError("sidecar referential integrity is not exact")


def _validate_expected_output(
    functionality: str, output: Mapping[str, Any]
) -> None:
    if functionality == "research_question_explorer":
        links = output.get("claim_evidence_links")
        disposition = output.get("expected_disposition")
        if not isinstance(links, list) or disposition not in {
            "answer",
            "qualify",
            "abstain",
        }:
            raise GoldenDataError(
                "Explorer citation/disposition expectations are incomplete"
            )
        for link in links:
            if (
                not isinstance(link, dict)
                or not link.get("claim_id")
                or not isinstance(link.get("evidence_reference_ids"), list)
            ):
                raise GoldenDataError(
                    "Explorer claim links need evidence references"
                )
        if disposition == "answer" and not links:
            raise GoldenDataError(
                "answerable Explorer output needs claim citations"
            )
    elif functionality == "evidence_comparison":
        papers = output.get("paper_comparisons")
        if not isinstance(papers, list) or len(papers) < 2:
            raise GoldenDataError(
                "comparison requires at least two paper records"
            )
        required_fields = {
            "doi",
            "objective",
            "methods",
            "conditions",
            "outcomes",
            "limitations",
            "evidence_reference_ids",
        }
        if any(
            not isinstance(paper, dict)
            or not required_fields <= set(paper)
            or not all(paper.get(field) for field in required_fields)
            for paper in papers
        ):
            raise GoldenDataError(
                "comparison records lack required source fields"
            )
    elif functionality == "conflicting_evidence_finder":
        findings = output.get("contrasted_findings")
        explanations = output.get("methodological_explanations")
        assessment = output.get("conflict_assessment")
        if (
            not isinstance(findings, list)
            or len(findings) < 2
            or len(
                {
                    normalize_doi(cast(str, item.get("doi"))).doi
                    for item in findings
                    if (
                        isinstance(item, dict)
                        and isinstance(item.get("doi"), str)
                        and item.get("finding")
                        and item.get("evidence_reference_ids")
                    )
                }
            )
            < 2
            or not isinstance(explanations, list)
            or not isinstance(assessment, dict)
        ):
            raise GoldenDataError(
                "conflict annotations need distinct papers and an assessment"
            )
        relationship = assessment.get("finding_relationship")
        decision = assessment.get("decision")
        negative_control = assessment.get("negative_control")
        if relationship not in {
            "genuine_conflict",
            "apparent_contrast",
            "non_equivalent",
            "insufficiently_comparable",
        }:
            raise GoldenDataError("conflict relationship is invalid")
        if relationship == "genuine_conflict":
            if decision != "report_conflict" or negative_control is not False:
                raise GoldenDataError(
                    "genuine conflict assessment is inconsistent"
                )
        elif (
            decision != "do_not_report_conflict" or negative_control is not True
        ):
            raise GoldenDataError(
                "conflict negative control must reject non-equivalent evidence"
            )
        if (
            not isinstance(assessment.get("rationale"), str)
            or not assessment["rationale"].strip()
            or not isinstance(assessment.get("evidence_reference_ids"), list)
            or not assessment["evidence_reference_ids"]
        ):
            raise GoldenDataError(
                "conflict assessment needs rationale and linked evidence"
            )
        for item in explanations:
            if not isinstance(item, dict) or item.get("status") not in {
                "source_supported",
                "plausible_but_unverified",
                "unknown",
            }:
                raise GoldenDataError("conflict explanation status is invalid")
    elif functionality == "research_gap_hypothesis_assistant":
        required = (
            "gap_statement",
            "gap_scope",
            "supporting_evidence_ids",
            "candidate_research_question",
            "candidate_hypothesis",
            "assumptions",
            "uncertainties",
            "evidence_needed_to_test",
        )
        if any(not output.get(field) for field in required):
            raise GoldenDataError(
                "gap/hypothesis expected output is incomplete"
            )
