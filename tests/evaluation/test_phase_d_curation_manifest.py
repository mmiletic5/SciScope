"""Synthetic provenance and functionality-sidecar contract tests."""

from __future__ import annotations

import pytest

from sciscope.evaluation.golden import (
    GoldenDataError,
    validate_curation_manifest,
    validate_functionality_sidecar,
)


def test_curation_manifest_requires_truthful_ai_provenance_and_reviews() -> (
    None
):
    """Model review cannot be represented as human verification."""
    manifest = {
        "manifest_version": "golden-v1-curation-v1",
        "dataset_version": "golden-v1",
        "corpus_version": "synthetic-corpus",
        "questions": [
            {
                "question_id": "q1",
                "creation_mode": "ai_generated",
                "created_at_utc": "2026-11-20T00:00:00Z",
                "tools": ["ChatGPT", "Codex"],
                "tool_versions": {"ChatGPT": "unknown", "Codex": "unknown"},
                "source_inputs": ["10.1234/synthetic#Results/p1"],
                "prompt_sha256": "a" * 64,
                "draft_lineage": ["initial synthetic fixture draft"],
                "ai_contribution": "Synthetic test-only question text.",
                "correction_history": [],
                "human_authored": False,
                "verification_status": "in_review",
                "chatgpt_review_status": "pending",
            }
        ],
    }

    validate_curation_manifest(manifest, expected_ids=frozenset({"q1"}))

    manifest["questions"][0]["verification_status"] = "verified"
    with pytest.raises(GoldenDataError, match="human verification"):
        validate_curation_manifest(manifest, expected_ids=frozenset({"q1"}))


def test_correction_history_requires_reason_fields_and_pending_review() -> None:
    """Revised candidates retain an auditable correction and review gate."""
    record = {
        "question_id": "q4",
        "creation_mode": "ai_assisted",
        "created_at_utc": "2026-11-20T00:00:00Z",
        "tools": ["Codex"],
        "tool_versions": {"Codex": "GPT-6"},
        "source_inputs": ["10.1234/synthetic#Results/p1"],
        "prompt_sha256": "a" * 64,
        "draft_lineage": ["synthetic initial draft"],
        "ai_contribution": "Synthetic test fixture.",
        "correction_history": [
            {
                "corrected_at_utc": "2026-11-20T01:00:00Z",
                "reason": "Synthetic review correction.",
                "fields_changed": ["expected_findings"],
                "correction_spec_sha256": "b" * 64,
                "review_status": "pending",
            }
        ],
        "human_authored": False,
        "verification_status": "in_review",
        "chatgpt_review_status": "pending",
    }
    manifest = {
        "manifest_version": "golden-v1-curation-v1",
        "dataset_version": "golden-v1",
        "corpus_version": "synthetic-corpus",
        "questions": [record],
    }

    validate_curation_manifest(manifest, expected_ids=frozenset({"q4"}))

    record["correction_history"][0]["review_status"] = "approved"
    with pytest.raises(GoldenDataError, match="correction history"):
        validate_curation_manifest(manifest, expected_ids=frozenset({"q4"}))


def test_functionality_sidecar_requires_exact_referential_integrity() -> None:
    """Every versioned sidecar record maps once to a dataset question ID."""
    sidecar = {
        "schema_version": "golden-functionality-v1",
        "annotations": [
            {
                "question_id": "q1",
                "primary_functionality": "research_question_explorer",
                "functionalities": ["research_question_explorer"],
                "expected_output": {
                    "claim_evidence_links": [
                        {
                            "claim_id": "c1",
                            "evidence_reference_ids": ["e1"],
                        }
                    ],
                    "expected_disposition": "answer",
                },
            }
        ],
    }
    validate_functionality_sidecar(sidecar, expected_ids=frozenset({"q1"}))
    with pytest.raises(GoldenDataError, match="referential"):
        validate_functionality_sidecar(
            sidecar, expected_ids=frozenset({"q1", "q2"})
        )
