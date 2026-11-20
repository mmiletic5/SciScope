"""Validate and package protected Golden v1 candidates without retrieval."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast
from zipfile import ZipFile

from sciscope.evaluation.curation import (
    CurationValidationError,
    validate_v1_artifacts,
)
from sciscope.evaluation.protection import (
    ProtectedDataError,
    audit_no_text_leak,
    protected_artifact_manifest,
    protected_evaluation_text_values,
    validate_protected_artifact_paths,
    validate_protected_destination,
    write_protected_file,
)
from sciscope.evaluation.review_package import (
    ReviewPackageError,
    build_review_package,
)

ROOT = Path(__file__).resolve().parents[1]
PROTECTED = ROOT / "evals" / "protected" / "golden_v1_review"
DATASET = PROTECTED / "golden_questions.v1.candidates.json"
SIDECAR = PROTECTED / "golden_functionality_annotations.v1.json"
CURATION = PROTECTED / "golden_v1_curation_manifest.json"
SOURCE_PASSAGES = PROTECTED / "source_passages.v1.json"
SEARCH_REPORT = PROTECTED / "corpus_scope_search_report.json"
PROMPT_RECORD = PROTECTED / "curation_prompt_record.md"
REVIEW_INSTRUCTIONS = PROTECTED / "review_instructions.md"
BASELINE = PROTECTED / "phase_d_baseline_freeze.json"
VALIDATION = PROTECTED / "validation_report.json"
PACKAGE = PROTECTED / "golden_v1_chatgpt_review_packet_r2.zip"
PRIOR_PACKAGE = PROTECTED / "golden_v1_chatgpt_review_packet.zip"
PRIOR_PACKAGE_SHA256 = (
    "138f5ec5c4c4386b4c72dc51972d1aee83bca74ea6a5fdd7ff5b559c37936922"
)
CORRECTION_SPEC = PROTECTED / "correction_spec.v1.json"
GOLDEN_SCHEMA = ROOT / "evals" / "golden_questions.schema.json"
SIDECAR_SCHEMA = ROOT / "evals" / "golden_functionality_annotations.schema.json"
FROZEN_CORPUS = "pilot17-xml-1fff1573b610"
EXPECTED_COUNTS = {"papers": 17, "sections": 319, "chunks": 728}
SLOT_BY_QUESTION_ID = {f"golden-v1-q{i}": f"Q{i}" for i in range(1, 10)}


class PrepareError(ValueError):
    """Sanitized local curation preparation failure."""


def main() -> int:
    """Validate protected candidates and optionally build the review packet."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--build-review-package",
        action="store_true",
        help="build the final allowlisted ChatGPT review zip after validation",
    )
    args = parser.parse_args()
    try:
        summary = validate_packet_inputs()
        if args.build_review_package:
            archive_sha256 = build_packet()
            summary["review_package_sha256"] = archive_sha256
        print(json.dumps(summary, sort_keys=True))
        return 0
    except (
        PrepareError,
        ProtectedDataError,
        CurationValidationError,
        ReviewPackageError,
    ) as error:
        print(f"PREPARATION_BLOCKED: {error}", file=sys.stderr)
        return 2


def validate_packet_inputs() -> dict[str, Any]:
    """Validate protected source-grounded candidates and report no prose."""
    _validate_local_corpus()
    input_paths = (
        DATASET,
        SIDECAR,
        CURATION,
        SOURCE_PASSAGES,
        SEARCH_REPORT,
        PROMPT_RECORD,
        REVIEW_INSTRUCTIONS,
        BASELINE,
        CORRECTION_SPEC,
    )
    validate_protected_artifact_paths(ROOT, input_paths)
    dataset = _read_json(DATASET)
    sidecar = _read_json(SIDECAR)
    curation = _read_json(CURATION)
    passages = _read_json(SOURCE_PASSAGES)
    if passages != _source_passage_projection(sidecar):
        raise PrepareError("source-passage packet does not match sidecar")
    corpus_dois, chunks_by_id, papers_by_doi = _load_source_records()
    _validate_frozen_baseline()
    summary = validate_v1_artifacts(
        dataset=dataset,
        sidecar=sidecar,
        curation_manifest=curation,
        golden_schema_path=GOLDEN_SCHEMA,
        sidecar_schema_path=SIDECAR_SCHEMA,
        corpus_dois=corpus_dois,
        chunks_by_id=chunks_by_id,
        papers_by_doi=papers_by_doi,
        slot_by_question_id=SLOT_BY_QUESTION_ID,
    )
    summary["approved_question_content_preserved"] = (
        _approved_question_content_preserved(dataset)
    )
    _validate_partition_files(dataset)
    scan_paths = [
        ROOT / name
        for name in ("src", "tests", "scripts", "docs", "examples")
        if (ROOT / name).exists()
    ]
    scan_paths.extend(
        path
        for path in (ROOT / "EVIDENCE.md", ROOT / "PROJECT_TODO.md")
        if path.exists()
    )
    if (ROOT / "evals" / "results").exists():
        scan_paths.append(ROOT / "evals" / "results")
    scanned = audit_no_text_leak(
        protected_evaluation_text_values(dataset, sidecar),
        scan_paths,
    )
    artifacts = (
        DATASET,
        SIDECAR,
        CURATION,
        SOURCE_PASSAGES,
        SEARCH_REPORT,
        PROMPT_RECORD,
        REVIEW_INSTRUCTIONS,
        BASELINE,
        CORRECTION_SPEC,
        PROTECTED / "development" / "golden_questions.v1.development.json",
        PROTECTED
        / "development"
        / "functionality_annotations.v1.development.json",
        PROTECTED / "held_out" / "golden_questions.v1.held_out.json",
        PROTECTED / "held_out" / "functionality_annotations.v1.held_out.json",
    )
    summary["ordinary_text_files_scanned"] = scanned
    summary["genuine_conflict_claims"] = 0
    summary["conflict_finder_negative_controls"] = 2
    summary["genuine_conflict_sensitivity_claim_permitted"] = False
    summary["protected_artifacts"] = protected_artifact_manifest(
        ROOT, artifacts
    )
    summary["retrieval_or_database_accessed"] = False
    summary["golden_v0_accessed"] = False
    summary["held_out_used_for_tuning"] = False
    _write_json_new(VALIDATION, summary)
    validate_protected_artifact_paths(ROOT, (VALIDATION,))
    return summary


def build_packet() -> str:
    """Build the exact allowlisted review archive after passing all checks."""
    validate_packet_inputs()
    validate_protected_destination(ROOT, PACKAGE)
    readme = REVIEW_INSTRUCTIONS.read_bytes()
    members = {
        "README.md": readme,
        "golden_questions.v1.candidates.json": DATASET.read_bytes(),
        "golden_functionality_annotations.v1.json": SIDECAR.read_bytes(),
        "golden_v1_curation_manifest.json": CURATION.read_bytes(),
        "source_passages.v1.json": SOURCE_PASSAGES.read_bytes(),
        "corpus_scope_search_report.json": SEARCH_REPORT.read_bytes(),
        "validation_report.json": VALIDATION.read_bytes(),
        "curation_prompt_record.md": PROMPT_RECORD.read_bytes(),
        "phase_d_baseline_freeze.json": BASELINE.read_bytes(),
    }
    return build_review_package(PACKAGE, members)


def _approved_question_content_preserved(
    current_dataset: Mapping[str, Any],
) -> bool:
    """Compare prior-approved question content without printing any text."""
    validate_protected_artifact_paths(ROOT, (PRIOR_PACKAGE,))
    if hashlib.sha256(PRIOR_PACKAGE.read_bytes()).hexdigest() != (
        PRIOR_PACKAGE_SHA256
    ):
        raise PrepareError("prior review packet identity mismatch")
    fields = (
        "question",
        "question_type",
        "expected_findings",
        "relevant_papers",
        "expected_insufficient_evidence",
        "source_corpus_version",
    )
    try:
        with ZipFile(PRIOR_PACKAGE) as archive:
            previous = json.loads(
                archive.read("golden_questions.v1.candidates.json")
            )
    except (OSError, KeyError, ValueError) as error:
        raise PrepareError("prior approved records are unavailable") from error
    previous_by_id = {
        item["question_id"]: item for item in previous["questions"]
    }
    current_by_id = {
        item["question_id"]: item for item in current_dataset["questions"]
    }
    for question_id in (
        "golden-v1-q1",
        "golden-v1-q2",
        "golden-v1-q3",
        "golden-v1-q7",
        "golden-v1-q8",
    ):
        if any(
            previous_by_id[question_id].get(field)
            != current_by_id[question_id].get(field)
            for field in fields
        ):
            raise PrepareError("previously approved question content changed")
    return True


def _validate_frozen_baseline() -> None:
    baseline = _read_json(BASELINE)
    if baseline.get("corpus", {}).get("corpus_version") != FROZEN_CORPUS:
        raise PrepareError("frozen baseline corpus identity mismatch")
    retrieval = baseline.get("retrieval", {})
    if retrieval.get("modes") != ["dense", "lexical", "hybrid"]:
        raise PrepareError("frozen retrieval modes changed")
    if retrieval.get("rrf_constant") != 60:
        raise PrepareError("frozen RRF constant changed")
    if retrieval.get("reranker") != (
        "disabled; MiniLM remains NO-GO and not part of Phase D"
    ):
        raise PrepareError("frozen reranker decision changed")
    embedding = baseline.get("embedding", {})
    if (
        embedding.get("model_identifier") != "text-embedding-3-small"
        or embedding.get("dimensions") != 1536
    ):
        raise PrepareError("frozen embedding identity changed")
    assignment = baseline.get("golden_v1_partitions", {})
    if assignment.get("development") != ["Q1", "Q4", "Q6"] or assignment.get(
        "held_out"
    ) != ["Q2", "Q3", "Q5", "Q7", "Q8", "Q9"]:
        raise PrepareError("frozen partition assignment changed")
    hash_maps = (
        baseline.get("retrieval_and_embedding_code_sha256", {}),
        baseline.get("evaluator", {}).get("module_sha256", {}),
    )
    amendments = (
        baseline.get("post_generation_protection_amendment", {}),
        baseline.get("post_generation_curation_amendment", {}),
    )
    overrides: dict[str, str] = {}
    additional_hashes: dict[str, str] = {}
    for amendment in amendments:
        overrides.update(amendment.get("file_sha256_overrides", {}))
        additional_hashes.update(
            amendment.get("additional_evaluator_module_sha256", {})
        )
    for file_hashes in hash_maps:
        for name, expected_hash in file_hashes.items():
            expected_hash = overrides.get(name, expected_hash)
            try:
                actual_hash = hashlib.sha256(
                    (ROOT / name).read_bytes()
                ).hexdigest()
            except OSError as error:
                raise PrepareError(
                    "frozen baseline file is unavailable"
                ) from error
            if actual_hash != expected_hash:
                raise PrepareError(
                    "frozen baseline source/configuration changed"
                )
    for name, expected_hash in additional_hashes.items():
        actual_hash = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            raise PrepareError("authorized evaluator amendment hash mismatch")


def _validate_local_corpus() -> None:
    manifest_path = (
        ROOT / "data" / "delivery" / "pilot" / "delivery_manifest.json"
    )
    try:
        manifest = _read_json(manifest_path)
        counts = manifest["counts"]
        files = manifest["files"]
    except (KeyError, TypeError) as error:
        raise PrepareError(
            "frozen local corpus manifest is malformed"
        ) from error
    if counts != EXPECTED_COUNTS:
        raise PrepareError("frozen local corpus counts do not match")
    for name, expected in files.items():
        path = manifest_path.parent / name
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            size = path.stat().st_size
        except OSError as error:
            raise PrepareError(
                "frozen local corpus payload is unavailable"
            ) from error
        if digest != expected.get("sha256") or size != expected.get("bytes"):
            raise PrepareError("frozen local corpus payload hash mismatch")
    rows = [
        json.loads(line)
        for line in (ROOT / "data" / "pilot" / "manifest.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    material = "".join(
        f"{row['doi']}\t{row['xml_sha256']}\n"
        for row in sorted(rows, key=lambda row: row["doi"])
    ).encode("utf-8")
    version = (
        f"pilot{len(rows)}-xml-{hashlib.sha256(material).hexdigest()[:12]}"
    )
    if version != FROZEN_CORPUS:
        raise PrepareError("local source manifest identity mismatch")


def _load_source_records() -> tuple[
    frozenset[str],
    dict[str, Mapping[str, Any]],
    dict[str, Mapping[str, Any]],
]:
    data_root = ROOT / "data" / "delivery" / "pilot"
    papers = _read_jsonl(data_root / "papers.jsonl")
    chunks = _read_jsonl(data_root / "chunks.jsonl")
    chunks_by_id = {cast(str, item["chunk_id"]): item for item in chunks}
    papers_by_doi = {cast(str, item["doi"]): item for item in papers}
    if len(papers_by_doi) != 17 or len(chunks_by_id) != 728:
        raise PrepareError("local source records do not match frozen counts")
    return (
        frozenset(papers_by_doi),
        cast(dict[str, Mapping[str, Any]], chunks_by_id),
        cast(dict[str, Mapping[str, Any]], papers_by_doi),
    )


def _validate_partition_files(dataset: Mapping[str, Any]) -> None:
    questions = cast(list[dict[str, Any]], dataset["questions"])
    dev_ids = {"golden-v1-q1", "golden-v1-q4", "golden-v1-q6"}
    held_out_ids = {
        "golden-v1-q2",
        "golden-v1-q3",
        "golden-v1-q5",
        "golden-v1-q7",
        "golden-v1-q8",
        "golden-v1-q9",
    }
    records = {cast(str, item["question_id"]): item for item in questions}
    if set(records) != dev_ids | held_out_ids:
        raise PrepareError("candidate IDs do not match frozen slots")
    development = {
        "dataset_version": dataset["dataset_version"],
        "corpus_version": dataset["corpus_version"],
        "questions": [records[item] for item in sorted(dev_ids)],
    }
    held_out = {
        "dataset_version": dataset["dataset_version"],
        "corpus_version": dataset["corpus_version"],
        "questions": [records[item] for item in sorted(held_out_ids)],
    }
    _write_json_new(
        PROTECTED / "development" / "golden_questions.v1.development.json",
        development,
    )
    _write_json_new(
        PROTECTED / "held_out" / "golden_questions.v1.held_out.json",
        held_out,
    )
    sidecar = _read_json(SIDECAR)
    annotations = cast(list[dict[str, Any]], sidecar["annotations"])
    annotation_by_id = {
        cast(str, item["question_id"]): item for item in annotations
    }
    _write_json_new(
        PROTECTED
        / "development"
        / "functionality_annotations.v1.development.json",
        {
            "schema_version": sidecar["schema_version"],
            "dataset_version": sidecar["dataset_version"],
            "corpus_version": sidecar["corpus_version"],
            "annotations": [annotation_by_id[item] for item in sorted(dev_ids)],
        },
    )
    _write_json_new(
        PROTECTED / "held_out" / "functionality_annotations.v1.held_out.json",
        {
            "schema_version": sidecar["schema_version"],
            "dataset_version": sidecar["dataset_version"],
            "corpus_version": sidecar["corpus_version"],
            "annotations": [
                annotation_by_id[item] for item in sorted(held_out_ids)
            ],
        },
    )
    validate_protected_artifact_paths(
        ROOT,
        (
            PROTECTED / "development" / "golden_questions.v1.development.json",
            PROTECTED
            / "development"
            / "functionality_annotations.v1.development.json",
            PROTECTED / "held_out" / "golden_questions.v1.held_out.json",
            PROTECTED
            / "held_out"
            / "functionality_annotations.v1.held_out.json",
        ),
    )


def _source_passage_projection(sidecar: Mapping[str, Any]) -> dict[str, Any]:
    annotations = cast(list[dict[str, Any]], sidecar["annotations"])
    return {
        "artifact_version": "golden-v1-source-passages-v1",
        "passages": [
            {
                "question_id": annotation["question_id"],
                "slot": annotation["slot"],
                "evidence_references": annotation["evidence_references"],
            }
            for annotation in annotations
        ],
    }


def _write_json_new(path: Path, value: Mapping[str, Any]) -> None:
    payload = (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    try:
        write_protected_file(
            ROOT, path, payload, replace_existing=path.exists()
        )
    except ProtectedDataError as error:
        raise PrepareError(
            "protected JSON output could not be written"
        ) from error


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        raise PrepareError("protected JSON artifact is unavailable") from error
    if not isinstance(value, dict):
        raise PrepareError("protected JSON artifact is malformed")
    return value


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        records = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except (OSError, UnicodeError, ValueError) as error:
        raise PrepareError("frozen local source file is malformed") from error
    if any(not isinstance(item, dict) for item in records):
        raise PrepareError("frozen local source record is malformed")
    return cast(list[dict[str, Any]], records)


if __name__ == "__main__":
    raise SystemExit(main())
