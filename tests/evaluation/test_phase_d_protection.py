"""Procedural held-out protection tests using synthetic content only."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from sciscope.evaluation.protection import (
    ProtectedDataError,
    audit_no_text_leak,
    protected_artifact_manifest,
    protected_evaluation_text_values,
    validate_protected_artifact_paths,
    validate_protected_destination,
    validate_v1_slot_categories,
    validate_v1_slot_functionalities,
    validate_v1_slot_partitions,
    write_protected_file,
)


def _git_repository(path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(path)], check=True)


def test_fixed_v1_partition_assignment_is_exact() -> None:
    """Question content cannot influence the pre-registered slot split."""
    validate_v1_slot_partitions(
        {
            "Q1": "development",
            "Q2": "held_out",
            "Q3": "held_out",
            "Q4": "development",
            "Q5": "held_out",
            "Q6": "development",
            "Q7": "held_out",
            "Q8": "held_out",
            "Q9": "held_out",
        }
    )
    invalid = {
        "Q1": "held_out",
        "Q2": "development",
        "Q3": "held_out",
        "Q4": "development",
        "Q5": "held_out",
        "Q6": "development",
        "Q7": "held_out",
        "Q8": "held_out",
        "Q9": "held_out",
    }
    with pytest.raises(ProtectedDataError, match="fixed partition"):
        validate_v1_slot_partitions(invalid)


def test_fixed_v1_category_and_functionality_crosswalk_is_enforced() -> None:
    """Question drafting cannot reassign matrix categories or workflows."""
    validate_v1_slot_categories(
        {
            "Q1": "insufficient_evidence",
            "Q2": "insufficient_evidence",
            "Q3": "insufficient_evidence",
            "Q4": "multi_paper_comparison",
            "Q5": "multi_paper_comparison",
            "Q6": "research_gap",
            "Q7": "research_gap",
            "Q8": "single_paper_factual",
            "Q9": "multi_paper_comparison",
        }
    )
    validate_v1_slot_functionalities(
        {
            "Q1": {"research_question_explorer"},
            "Q2": {"evidence_comparison"},
            "Q3": {"research_gap_hypothesis_assistant"},
            "Q4": {
                "evidence_comparison",
                "conflicting_evidence_finder",
                "research_question_explorer",
            },
            "Q5": {"evidence_comparison", "conflicting_evidence_finder"},
            "Q6": {
                "research_gap_hypothesis_assistant",
                "research_question_explorer",
            },
            "Q7": {"research_gap_hypothesis_assistant"},
            "Q8": {"research_question_explorer"},
            "Q9": {"evidence_comparison"},
        }
    )
    with pytest.raises(ProtectedDataError, match="category assignment"):
        validate_v1_slot_categories({"Q1": "research_gap"})
    with pytest.raises(ProtectedDataError, match="functionality assignment"):
        validate_v1_slot_functionalities({"Q1": {"evidence_comparison"}})


def test_protected_artifact_must_be_ignored_untracked_and_in_private_root(
    tmp_path: Path,
) -> None:
    """Review artifacts can only be stored under the Git-ignored root."""
    root = tmp_path / "repo"
    root.mkdir()
    _git_repository(root)
    (root / ".gitignore").write_text("/evals/protected/\n", encoding="utf-8")
    artifact = root / "evals" / "protected" / "golden_v1_review" / "x.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text('{"synthetic":true}', encoding="utf-8")

    validate_protected_artifact_paths(root, (artifact,))

    visible = root / "evals" / "results" / "x.json"
    visible.parent.mkdir(parents=True)
    visible.write_text("{}", encoding="utf-8")
    with pytest.raises(ProtectedDataError, match="protected ignored root"):
        validate_protected_artifact_paths(root, (visible,))


def test_protected_artifact_fails_closed_when_not_ignored(
    tmp_path: Path,
) -> None:
    """A directory name alone does not establish Git exclusion."""
    root = tmp_path / "repo"
    root.mkdir()
    _git_repository(root)
    artifact = root / "evals" / "protected" / "golden_v1_review" / "x.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{}", encoding="utf-8")

    with pytest.raises(ProtectedDataError, match="Git-ignored"):
        validate_protected_artifact_paths(root, (artifact,))


def test_new_protected_destination_is_checked_before_write(
    tmp_path: Path,
) -> None:
    """Destination preflight requires ignored storage and no overwrite."""
    root = tmp_path / "repo"
    root.mkdir()
    _git_repository(root)
    (root / ".gitignore").write_text("/evals/protected/\n", encoding="utf-8")
    destination = root / "evals" / "protected" / "golden_v1_review" / "new.json"

    assert validate_protected_destination(root, destination) == destination
    destination.parent.mkdir(parents=True)
    destination.write_text("{}", encoding="utf-8")
    with pytest.raises(ProtectedDataError, match="already exists"):
        validate_protected_destination(root, destination)


def test_protected_writer_requires_ignore_and_explicit_replacement(
    tmp_path: Path,
) -> None:
    """Atomic protected writes fail closed and replace only by instruction."""
    root = tmp_path / "repo"
    root.mkdir()
    _git_repository(root)
    (root / ".gitignore").write_text("/evals/protected/\n", encoding="utf-8")
    target = root / "evals" / "protected" / "golden_v1_review" / "x.json"

    write_protected_file(root, target, b'{"synthetic":1}')
    with pytest.raises(ProtectedDataError, match="already exists"):
        write_protected_file(root, target, b'{"synthetic":2}')
    write_protected_file(
        root, target, b'{"synthetic":2}', replace_existing=True
    )

    assert target.read_bytes() == b'{"synthetic":2}'


def test_protected_manifest_contains_hashes_not_payload_text(
    tmp_path: Path,
) -> None:
    """Audit manifests expose integrity metadata without record contents."""
    root = tmp_path / "repo"
    root.mkdir()
    _git_repository(root)
    (root / ".gitignore").write_text("/evals/protected/\n", encoding="utf-8")
    artifact = root / "evals" / "protected" / "golden_v1_review" / "x.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text(
        '{"question":"synthetic private text"}', encoding="utf-8"
    )

    manifest = protected_artifact_manifest(root, (artifact,))

    assert manifest[0]["path"] == "evals/protected/golden_v1_review/x.json"
    assert manifest[0]["bytes"] == artifact.stat().st_size
    assert len(manifest[0]["sha256"]) == 64
    assert "synthetic private text" not in str(manifest)


def test_leak_audit_reports_location_without_echoing_protected_text(
    tmp_path: Path,
) -> None:
    """Leak diagnostics identify a failure without printing its contents."""
    fixture = tmp_path / "fixture.json"
    secret_text = (
        "A long synthetic answer that must remain in protected storage only."
    )
    fixture.write_text(secret_text, encoding="utf-8")

    with pytest.raises(ProtectedDataError, match="protected content") as error:
        audit_no_text_leak((secret_text,), (fixture,))

    assert secret_text not in str(error.value)


def test_leak_values_include_prose_but_ignore_ids_and_enum_fields() -> None:
    """Leak audit targets candidate prose rather than routine schema IDs."""
    dataset = {
        "corpus_version": "pilot17-xml-1fff1573b610",
        "questions": [
            {
                "question": "Synthetic private question prose.",
                "expected_findings": "Synthetic private expected answer.",
                "question_id": "golden-v1-q1",
            }
        ],
    }
    sidecar = {
        "annotations": [
            {
                "answerability": "answerable",
                "evidence_references": [
                    {
                        "doi": "10.1234/example",
                        "source_passage": "Synthetic private original passage.",
                        "quotation": "Synthetic private quote.",
                        "relevance_rationale": (
                            "Synthetic private relevance note."
                        ),
                    }
                ],
                "expected_output": {
                    "statement": "Synthetic private expected output prose.",
                    "expected_disposition": "answer",
                },
            }
        ]
    }

    values = protected_evaluation_text_values(dataset, sidecar)

    assert "Synthetic private question prose." in values
    assert "Synthetic private original passage." in values
    assert "Synthetic private expected output prose." in values
    assert "pilot17-xml-1fff1573b610" not in values
    assert "answerable" not in values
