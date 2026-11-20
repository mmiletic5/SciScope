"""Synthetic-only tests for data-driven protected curation corrections."""

from __future__ import annotations

from typing import Any

import pytest

from sciscope.evaluation.candidate_builder import apply_candidate_corrections
from sciscope.evaluation.golden import GoldenDataError


def _inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    questions = []
    annotations = []
    provenance = []
    for index in range(1, 10):
        question_id = f"golden-v1-q{index}"
        slot = f"Q{index}"
        partition = "development" if index in {1, 4, 6} else "held_out"
        questions.append(
            {
                "question_id": question_id,
                "question_type": "multi_paper_comparison",
                "question": f"Synthetic question {index}.",
                "expected_findings": "Synthetic expected finding.",
                "relevant_papers": [],
                "expected_insufficient_evidence": False,
                "reviewer": "ChatGPT pending",
                "verification_status": "in_review",
                "source_corpus_version": "synthetic-corpus",
            }
        )
        annotations.append(
            {
                "question_id": question_id,
                "slot": slot,
                "partition": partition,
                "functionalities": ["evidence_comparison"],
                "primary_functionality": "evidence_comparison",
                "evidence_references": [],
                "expected_output": {},
            }
        )
        provenance.append(
            {
                "question_id": question_id,
                "correction_history": [],
                "chatgpt_review_status": "pending",
            }
        )
    return (
        {"questions": questions, "change_history": []},
        {"annotations": annotations},
        {"questions": provenance},
    )


def _correction(question_id: str, slot: str, chunk_id: str) -> dict[str, Any]:
    return {
        "question_id": question_id,
        "slot": slot,
        "partition": "development" if slot in {"Q4", "Q6"} else "held_out",
        "question_type": "multi_paper_comparison",
        "question": "Synthetic revised question.",
        "expected_findings": "Synthetic revised finding.",
        "functionalities": ["evidence_comparison"],
        "primary_functionality": "evidence_comparison",
        "fields_changed": ["question"],
        "reason": "Synthetic correction reason.",
        "add_evidence": [
            {
                "chunk_id": chunk_id,
                "quotation": "Synthetic exact quote.",
                "relevance_label": "3",
                "relevance_rationale": "Synthetic source rationale.",
                "claim_ids": ["synthetic_claim"],
                "role": "supports",
            }
        ],
        "expected_output": {
            "claim_evidence_links": [
                {
                    "claim_id": "synthetic_claim",
                    "evidence_reference_ids": [f"{question_id}-e1"],
                }
            ]
        },
    }


def test_correction_builder_changes_only_authorized_records() -> None:
    """Corrections preserve other question text and fixed partitions."""
    dataset, sidecar, manifest = _inputs()
    chunks = {}
    papers = {}
    corrections = []
    for index, slot in zip((4, 5, 6, 9), ("Q4", "Q5", "Q6", "Q9"), strict=True):
        question_id = f"golden-v1-q{index}"
        doi = f"10.1234/synthetic{index}"
        chunk_id = f"synthetic-chunk-{index}"
        chunks[chunk_id] = {
            "doi": doi,
            "section_path": ["Results"],
            "source_locator": f"jats:test:/p[{index}]",
            "xml_sha256": "a" * 64,
            "text": "Synthetic exact quote.",
        }
        papers[doi] = {
            "source_url": f"https://example.test/{index}",
            "xml_sha256": "a" * 64,
        }
        corrections.append(_correction(question_id, slot, chunk_id))

    updated = apply_candidate_corrections(
        dataset=dataset,
        sidecar=sidecar,
        curation_manifest=manifest,
        correction_spec={"corrections": corrections},
        chunks_by_id=chunks,
        papers_by_doi=papers,
        corrected_at_utc="2026-11-20T04:00:00+00:00",
    )
    revised, revised_sidecar, revised_manifest = updated
    by_id = {item["question_id"]: item for item in revised["questions"]}
    notes = {
        item["question_id"]: item for item in revised_manifest["questions"]
    }

    assert by_id["golden-v1-q1"]["question"] == "Synthetic question 1."
    assert by_id["golden-v1-q4"]["question"] == "Synthetic revised question."
    assert by_id["golden-v1-q4"]["reviewer"].startswith("ChatGPT (")
    assert len(notes["golden-v1-q4"]["correction_history"]) == 1
    assert notes["golden-v1-q4"]["chatgpt_review_status"] == "pending"
    assert notes["golden-v1-q1"]["chatgpt_review_status"] == "approved"
    assert revised_sidecar["annotations"][3]["partition"] == "development"


def test_correction_builder_fails_closed_for_out_of_scope_record() -> None:
    """A correction specification cannot alter unapproved question IDs."""
    dataset, sidecar, manifest = _inputs()
    with pytest.raises(GoldenDataError, match="authorized scope"):
        apply_candidate_corrections(
            dataset=dataset,
            sidecar=sidecar,
            curation_manifest=manifest,
            correction_spec={
                "corrections": [_correction("golden-v1-q1", "Q1", "c1")]
            },
            chunks_by_id={},
            papers_by_doi={},
            corrected_at_utc="2026-11-20T04:00:00+00:00",
        )
