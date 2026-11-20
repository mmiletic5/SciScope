"""Build corrected Golden v1 from a Git-ignored protected data specification."""

from __future__ import annotations

import hashlib
import json
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from sciscope.evaluation.candidate_builder import apply_candidate_corrections
from sciscope.evaluation.curation import validate_v1_artifacts
from sciscope.evaluation.protection import (
    ProtectedDataError,
    validate_protected_artifact_paths,
    write_protected_file,
)

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / "evals" / "protected" / "golden_v1_review"
CORRECTION_SPEC = PRIVATE / "correction_spec.v1.json"
DATASET = PRIVATE / "golden_questions.v1.candidates.json"
SIDECAR = PRIVATE / "golden_functionality_annotations.v1.json"
CURATION = PRIVATE / "golden_v1_curation_manifest.json"
SOURCE_PASSAGES = PRIVATE / "source_passages.v1.json"
SEARCH_REPORT = PRIVATE / "corpus_scope_search_report.json"
PROMPT_RECORD = PRIVATE / "curation_prompt_record.md"
REVIEW_INSTRUCTIONS = PRIVATE / "review_instructions.md"
GOLDEN_SCHEMA = ROOT / "evals" / "golden_questions.schema.json"
SIDECAR_SCHEMA = ROOT / "evals" / "golden_functionality_annotations.schema.json"
CORPUS_VERSION = "pilot17-xml-1fff1573b610"
SLOT_BY_ID = {f"golden-v1-q{i}": f"Q{i}" for i in range(1, 10)}


class BuildError(ValueError):
    """Sanitized failure while preparing protected candidate artifacts."""


def main() -> int:
    """Apply only the protected, owner-authorized correction specification."""
    try:
        summary = build_corrected_candidates()
        print(json.dumps(summary, sort_keys=True))
        return 0
    except (BuildError, ProtectedDataError, ValueError, OSError) as error:
        print(f"BUILD_BLOCKED: {error}", file=sys.stderr)
        return 2


def build_corrected_candidates() -> dict[str, Any]:
    """Validate in memory, then atomically update protected Golden artifacts."""
    input_paths = (CORRECTION_SPEC, DATASET, SIDECAR, CURATION)
    validate_protected_artifact_paths(ROOT, input_paths)
    spec = _read_json(CORRECTION_SPEC)
    dataset = _read_json(DATASET)
    sidecar = _read_json(SIDECAR)
    manifest = _read_json(CURATION)
    corpus_dois, chunks_by_id, papers_by_doi = _load_local_corpus()

    corrected_at = datetime.now(UTC).isoformat()
    revised_dataset, revised_sidecar, revised_manifest = (
        apply_candidate_corrections(
            dataset=dataset,
            sidecar=sidecar,
            curation_manifest=manifest,
            correction_spec=spec,
            chunks_by_id=chunks_by_id,
            papers_by_doi=papers_by_doi,
            corrected_at_utc=corrected_at,
        )
    )
    validation = validate_v1_artifacts(
        dataset=revised_dataset,
        sidecar=revised_sidecar,
        curation_manifest=revised_manifest,
        golden_schema_path=GOLDEN_SCHEMA,
        sidecar_schema_path=SIDECAR_SCHEMA,
        corpus_dois=corpus_dois,
        chunks_by_id=chunks_by_id,
        papers_by_doi=papers_by_doi,
        slot_by_question_id=SLOT_BY_ID,
    )
    source_passages = _source_passage_projection(revised_sidecar)
    search = _read_json(SEARCH_REPORT)
    search["amended_conflict_scope"] = {
        "genuine_conflicts_supported_in_frozen_corpus": 0,
        "q4_q5_role": (
            "negative controls for rejecting apparent or "
            "non-equivalent conflicts"
        ),
        "sensitivity_claim_permitted": False,
        "basis": (
            "Source-level review of overlapping outcomes in the 17-paper "
            "frozen "
            "corpus found no defensible pair of genuinely contradictory, "
            "comparable findings."
        ),
    }
    correction_hash = hashlib.sha256(
        json.dumps(
            spec,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    prompt_record = (
        PROMPT_RECORD.read_text(encoding="utf-8")
        + "\n\n## Owner-authorized T004 correction lineage\n\n"
        + "Codex applied only the Q4, Q5, Q6, and Q9 corrections after the "
        + "reported independent ChatGPT review. Protected correction-spec "
        + f"SHA-256: `{correction_hash}`. Q4 and Q5 are multi-paper comparison "
        + "negative controls; the frozen corpus supports zero genuine-conflict "
        + "claims, and no genuine-conflict sensitivity claim is permitted. Q6 "
        + "removes the unsupported presupposition. Q9 links the design details "
        + "to the exact abstract passage. Revised records remain pending "
        + "independent ChatGPT review.\n"
    )
    review_instructions = _review_instructions()

    outputs: dict[Path, bytes] = {
        DATASET: _json_bytes(revised_dataset),
        SIDECAR: _json_bytes(revised_sidecar),
        CURATION: _json_bytes(revised_manifest),
        SOURCE_PASSAGES: _json_bytes(source_passages),
        SEARCH_REPORT: _json_bytes(search),
        PROMPT_RECORD: prompt_record.encode("utf-8"),
        REVIEW_INSTRUCTIONS: review_instructions.encode("utf-8"),
        **_partition_outputs(revised_dataset, revised_sidecar),
    }
    existing = set(outputs) & set(_existing_protected_files())
    for destination, payload in outputs.items():
        write_protected_file(
            ROOT,
            destination,
            payload,
            replace_existing=destination in existing,
        )
    validation["correction_spec_sha256"] = correction_hash
    validation["revised_question_ids"] = [
        "golden-v1-q4",
        "golden-v1-q5",
        "golden-v1-q6",
        "golden-v1-q9",
    ]
    validation["genuine_conflict_claims"] = 0
    validation["conflict_finder_cases"] = {
        "negative_controls": 2,
        "genuine_conflict_sensitivity_claim_permitted": False,
    }
    return validation


def _load_local_corpus() -> tuple[
    frozenset[str],
    dict[str, Mapping[str, Any]],
    dict[str, Mapping[str, Any]],
]:
    source_root = ROOT / "data" / "delivery" / "pilot"
    papers = _read_jsonl(source_root / "papers.jsonl")
    chunks = _read_jsonl(source_root / "chunks.jsonl")
    papers_by_doi: dict[str, Mapping[str, Any]] = {
        cast(str, item["doi"]): item for item in papers
    }
    chunks_by_id: dict[str, Mapping[str, Any]] = {
        cast(str, item["chunk_id"]): item for item in chunks
    }
    if len(papers_by_doi) != 17 or len(chunks_by_id) != 728:
        raise BuildError("local frozen corpus identity/count mismatch")
    return frozenset(papers_by_doi), chunks_by_id, papers_by_doi


def _source_passage_projection(sidecar: Mapping[str, Any]) -> dict[str, Any]:
    annotations = cast(list[dict[str, Any]], sidecar["annotations"])
    return {
        "artifact_version": "golden-v1-source-passages-v1",
        "passages": [
            {
                "question_id": item["question_id"],
                "slot": item["slot"],
                "evidence_references": item["evidence_references"],
            }
            for item in annotations
        ],
    }


def _partition_outputs(
    dataset: Mapping[str, Any], sidecar: Mapping[str, Any]
) -> dict[Path, bytes]:
    questions = cast(list[dict[str, Any]], dataset["questions"])
    annotations = cast(list[dict[str, Any]], sidecar["annotations"])
    question_by_id = {item["question_id"]: item for item in questions}
    annotation_by_id = {item["question_id"]: item for item in annotations}
    outputs: dict[Path, bytes] = {}
    for partition, ids in {
        "development": ("golden-v1-q1", "golden-v1-q4", "golden-v1-q6"),
        "held_out": (
            "golden-v1-q2",
            "golden-v1-q3",
            "golden-v1-q5",
            "golden-v1-q7",
            "golden-v1-q8",
            "golden-v1-q9",
        ),
    }.items():
        common = {
            "dataset_version": dataset["dataset_version"],
            "corpus_version": dataset["corpus_version"],
        }
        question_path = (
            PRIVATE / partition / f"golden_questions.v1.{partition}.json"
        )
        annotation_path = (
            PRIVATE
            / partition
            / f"functionality_annotations.v1.{partition}.json"
        )
        outputs[question_path] = _json_bytes(
            {
                **common,
                "questions": [question_by_id[item] for item in ids],
            }
        )
        outputs[annotation_path] = _json_bytes(
            {
                "schema_version": sidecar["schema_version"],
                **common,
                "annotations": [annotation_by_id[item] for item in ids],
            }
        )
    return outputs


def _existing_protected_files() -> tuple[Path, ...]:
    return tuple(path for path in PRIVATE.rglob("*") if path.is_file())


def _review_instructions() -> str:
    return """# Golden v1 independent ChatGPT review instructions

This protected archive contains six preregistered held-out records. Use it
only for authorized scientific source review. Do not use question text,
expected findings, annotations, or results for retrieval development,
debugging, tuning, prompt optimization, threshold selection, or model
selection. Do not request retrieval rankings.

Q1, Q2, Q3, Q7, and Q8 were approved in the prior independent ChatGPT review
as reported by the owner; their question content and evidence are preserved.
Q4, Q5, Q6, and Q9 were corrected and remain pending review. Inspect each
revised record against every supplied source passage, DOI, source URL, XML
digest, section, chunk ID, and locator. Check quotations, scientific claims,
answerability, relevance, comparison details, and evidence links. Q4 and Q5
are Conflict Finder negative controls: verify that neither is labeled a
genuine conflict. The frozen corpus contains no defensible genuine-conflict
pair, and this dataset supports no genuine-conflict sensitivity claim.

For Q6, verify that the question does not presuppose an unsupported effect
and that the conclusion separates the reported cellular observation from
organism-level behavior. For Q9, verify each design statement against the
supplied abstract methods passage. Raw XML was unavailable locally; passages
were validated against frozen derived chunks and source identity metadata.

Return explicit APPROVE or DEFECT decisions for Q4, Q5, Q6, and Q9, with
source-based reasons. Do not mark revised records human-verified. The project
owner separately decides whether to continue after review.
"""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise BuildError("protected JSON input is unavailable") from error
    if not isinstance(value, dict):
        raise BuildError("protected JSON input is malformed")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        rows = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except (OSError, UnicodeError, ValueError) as error:
        raise BuildError("local frozen source file is malformed") from error
    if any(not isinstance(item, dict) for item in rows):
        raise BuildError("local frozen source record is malformed")
    return cast(list[dict[str, Any]], rows)


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
