"""Data-driven builder mechanics for protected Golden v1 corrections."""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any, cast

from sciscope.evaluation.golden import GoldenDataError

_FIXED_CORRECTION_SLOTS = {
    "golden-v1-q4": "Q4",
    "golden-v1-q5": "Q5",
    "golden-v1-q6": "Q6",
    "golden-v1-q9": "Q9",
}
_APPROVED_PRIOR_IDS = {
    "golden-v1-q1",
    "golden-v1-q2",
    "golden-v1-q3",
    "golden-v1-q7",
    "golden-v1-q8",
}


def apply_candidate_corrections(
    *,
    dataset: Mapping[str, Any],
    sidecar: Mapping[str, Any],
    curation_manifest: Mapping[str, Any],
    correction_spec: Mapping[str, Any],
    chunks_by_id: Mapping[str, Mapping[str, Any]],
    papers_by_doi: Mapping[str, Mapping[str, Any]],
    corrected_at_utc: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Apply only the four owner-authorized, source-grounded corrections.

    The correction specification is data loaded from protected, Git-ignored
    storage. This module contains no question or evidence text.
    """
    revised_dataset = copy.deepcopy(dict(dataset))
    revised_sidecar = copy.deepcopy(dict(sidecar))
    revised_manifest = copy.deepcopy(dict(curation_manifest))

    corrections_value = correction_spec.get("corrections")
    if not isinstance(corrections_value, list):
        raise GoldenDataError("protected correction specification is malformed")
    corrections = cast(list[dict[str, Any]], corrections_value)
    correction_ids = [item.get("question_id") for item in corrections]
    if len(corrections) != len(_FIXED_CORRECTION_SLOTS) or set(
        correction_ids
    ) != set(_FIXED_CORRECTION_SLOTS):
        raise GoldenDataError("correction IDs do not match authorized scope")
    correction_spec_hash = hashlib.sha256(
        json.dumps(
            correction_spec,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()

    questions = cast(list[dict[str, Any]], revised_dataset["questions"])
    annotations = cast(list[dict[str, Any]], revised_sidecar["annotations"])
    provenance = cast(list[dict[str, Any]], revised_manifest["questions"])
    question_by_id = {item["question_id"]: item for item in questions}
    annotation_by_id = {item["question_id"]: item for item in annotations}
    provenance_by_id = {item["question_id"]: item for item in provenance}
    if set(question_by_id) != set(annotation_by_id) or set(
        question_by_id
    ) != set(provenance_by_id):
        raise GoldenDataError("protected candidate records are not aligned")

    for correction in corrections:
        question_id = cast(str, correction["question_id"])
        slot = _FIXED_CORRECTION_SLOTS[question_id]
        if correction.get("slot") != slot:
            raise GoldenDataError("correction slot does not match fixed map")
        question = question_by_id[question_id]
        annotation = annotation_by_id[question_id]
        history = provenance_by_id[question_id]
        if annotation.get("slot") != slot:
            raise GoldenDataError("existing sidecar slot does not match")

        for field in ("question", "question_type", "expected_findings"):
            if field in correction:
                question[field] = correction[field]
        question["verification_status"] = "in_review"
        question.pop("verified_date", None)
        question["reviewer"] = (
            "ChatGPT (revised AI candidate; independent review pending; "
            "not human verification)"
        )
        annotation["partition"] = correction["partition"]
        annotation["functionalities"] = correction["functionalities"]
        annotation["primary_functionality"] = correction[
            "primary_functionality"
        ]

        references = cast(
            list[dict[str, Any]], annotation["evidence_references"]
        )
        for evidence in cast(list[dict[str, Any]], correction["add_evidence"]):
            chunk_id = cast(str, evidence["chunk_id"])
            if any(
                item.get("chunk_id") == chunk_id
                and item.get("quotation") == evidence.get("quotation")
                for item in references
            ):
                continue
            chunk = chunks_by_id.get(chunk_id)
            if chunk is None:
                raise GoldenDataError(
                    "correction evidence is outside the frozen corpus"
                )
            doi = cast(str, chunk["doi"])
            paper = papers_by_doi.get(doi)
            if paper is None:
                raise GoldenDataError(
                    "correction source metadata is unavailable"
                )
            quote = cast(str, evidence["quotation"])
            source_text = cast(str, chunk["text"])
            if not quote or quote not in source_text:
                raise GoldenDataError(
                    "correction quotation is not exact in its source"
                )
            reference_id = f"{question_id}-e{len(references) + 1}"
            references.append(
                {
                    "evidence_reference_id": reference_id,
                    "doi": doi,
                    "section": " > ".join(
                        cast(list[str], chunk["section_path"])
                    ),
                    "chunk_id": chunk_id,
                    "source_locator": chunk["source_locator"],
                    "source_xml_sha256": chunk["xml_sha256"],
                    "source_url": paper["source_url"],
                    "source_passage": source_text,
                    "quotation": quote,
                    "relevance_label": evidence["relevance_label"],
                    "relevance_rationale": evidence["relevance_rationale"],
                    "claim_ids": evidence["claim_ids"],
                    "role": evidence["role"],
                }
            )
        annotation["expected_output"] = correction["expected_output"]
        question["relevant_papers"] = _golden_paper_projection(references)
        _validate_reference_ids(annotation["expected_output"], references)

        correction_history = cast(
            list[dict[str, Any]], history["correction_history"]
        )
        correction_history[:] = [
            item
            for item in correction_history
            if item.get("correction_spec_sha256") != correction_spec_hash
        ]
        correction_history.append(
            {
                "corrected_at_utc": corrected_at_utc,
                "reason": correction["reason"],
                "fields_changed": correction["fields_changed"],
                "correction_spec_sha256": correction_spec_hash,
                "review_status": "pending",
            }
        )
        history["chatgpt_review_status"] = "pending"
        history["chatgpt_review_note"] = (
            "Revised record requires independent ChatGPT review; no approval "
            "or human verification is claimed."
        )

    for question_id in _APPROVED_PRIOR_IDS:
        question_by_id[question_id]["reviewer"] = (
            "ChatGPT (independent model review approved per owner report; "
            "not human verification)"
        )
        provenance_by_id[question_id]["chatgpt_review_status"] = "approved"
        provenance_by_id[question_id]["chatgpt_review_note"] = (
            "Prior independent ChatGPT T004 approval reported by the owner; "
            "this records model review only, not human verification."
        )

    change_history = cast(
        list[dict[str, Any]], revised_dataset.setdefault("change_history", [])
    )
    change_history[:] = [
        item
        for item in change_history
        if item.get("reason")
        != (
            "Correct Q4, Q5, Q6, and Q9 after independent scientific review; "
            "preserve approved question content and frozen partitions."
        )
    ]
    change_history.append(
        {
            "date": corrected_at_utc[:10],
            "reviewer": (
                "Codex (AI curation under owner-authorized T004 corrections)"
            ),
            "reason": (
                "Correct Q4, Q5, Q6, and Q9 after scientific review; "
                "preserve approved question content and frozen partitions."
            ),
        }
    )
    revised_manifest["revision"] = "golden-v1-curation-revision-2"
    revised_manifest["updated_at_utc"] = corrected_at_utc
    revised_manifest["chatgpt_review_status"] = (
        "five prior records approved; four corrected records pending"
    )
    revised_manifest["chatgpt_review_summary"] = {
        "prior_approved_records": 5,
        "revised_records_pending": 4,
        "human_verification_claimed": False,
    }
    revised_manifest["amendment"] = {
        "owner_authorized": True,
        "scope": ["Q4", "Q5", "Q6", "Q9"],
        "genuine_conflict_claims": 0,
        "conflict_finder_use": (
            "negative controls for rejecting false conflicts"
        ),
        "review_status": "revised records pending independent ChatGPT review",
    }
    return revised_dataset, revised_sidecar, revised_manifest


def _golden_paper_projection(
    references: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for reference in references:
        grouped.setdefault(cast(str, reference["doi"]), []).append(reference)
    return [
        {
            "doi": doi,
            "sections": sorted({cast(str, item["section"]) for item in items}),
            "evidence": [
                {
                    key: item[key]
                    for key in (
                        "relevance_label",
                        "quotation",
                        "source_locator",
                        "chunk_id",
                    )
                }
                for item in items
            ],
        }
        for doi, items in sorted(grouped.items())
    ]


def _validate_reference_ids(
    value: object, references: Sequence[Mapping[str, Any]]
) -> None:
    valid_ids = {
        cast(str, item["evidence_reference_id"]) for item in references
    }

    def visit(item: object, field: str = "") -> None:
        if isinstance(item, Mapping):
            for key, child in item.items():
                visit(child, cast(str, key))
        elif isinstance(item, Sequence) and not isinstance(
            item, (str, bytes, bytearray)
        ):
            if field.endswith("evidence_reference_ids") or field in {
                "supporting_evidence_ids",
            }:
                if any(
                    not isinstance(ref_id, str) or ref_id not in valid_ids
                    for ref_id in item
                ):
                    raise GoldenDataError(
                        "correction output references unknown evidence"
                    )
            else:
                for child in item:
                    visit(child, field)

    visit(value)
