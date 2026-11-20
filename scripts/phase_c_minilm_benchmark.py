"""Run the approved five-question Phase C MiniLM diagnostic benchmark."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url

from sciscope.embedding.config import EmbeddingConfig
from sciscope.embedding.openai_client import (
    OpenAIConnection,
    OpenAIEmbedder,
    UrllibTransport,
    embeddings_url,
    read_api_key,
    read_base_url,
)
from sciscope.evaluation.rerank import (
    APPROVED_QUESTION_IDS,
    BenchmarkCandidate,
    BenchmarkQuestion,
    assess_diagnostic,
    compare_reranker,
)
from sciscope.retrieval._core import _RetrievalCore
from sciscope.retrieval._lookup import EvidenceLookup
from sciscope.retrieval._reranking import MiniLMCrossEncoderReranker

ARTIFACTS = ROOT / ".cache" / "phase_c_rerank"
QUESTIONS_PATH = ROOT / "evals" / "golden_questions.v0.json"
DEPENDENCY_LOCK_PATH = (
    ROOT
    / "specs"
    / "008-phase-c-quality"
    / "benchmark-environment-win-py312.lock"
)
MODEL_ID = "cross-encoder/ms-marco-MiniLM-L6-v2"
MODEL_REVISION = "233902d25c440f23af6f7d6e94d2946bac0bee0a"
MODEL_SHA256 = (
    "402c3a69514c2ccb83898cef29bdf468ec79da80fa091d9967b2de03e7e4adc0"
)
EXPECTED_COUNTS = (17, 319, 728, 728)
MAX_QUERY_TOKENS = 782
MAX_QUERY_COST_USD = 0.01
QUESTION_READ_CHUNK_BYTES = 4096


def _read_env_value(name: str) -> str:
    value = os.environ.get(name, "")
    if value:
        return value
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        match = re.match(rf"^\s*{re.escape(name)}\s*=(.*)$", line)
        if match:
            return match.group(1).strip().strip("\"'")
    return ""


def _approved_questions() -> list[dict[str, Any]]:
    """Decode only allowlisted question objects; reject partition drift."""
    allowed = _extract_allowlisted_records(
        QUESTIONS_PATH, APPROVED_QUESTION_IDS
    )
    if {item["question_id"] for item in allowed} != APPROVED_QUESTION_IDS:
        raise RuntimeError("approved five-question set is incomplete")
    return sorted(allowed, key=lambda item: item["question_id"])


def _extract_allowlisted_records(
    path: Path, allowed_ids: frozenset[str]
) -> list[dict[str, Any]]:
    """Read the JSON stream incrementally and decode only allowed records.

    Nonallowlisted record bytes are discarded after their ID is recognized.
    Before the ID, at most 512 bytes are buffered; allowlisted records are
    retained for decoding, alongside one fixed-size input chunk.
    """
    records: dict[str, dict[str, Any]] = {}
    allowed_bytes = {item.encode("ascii"): item for item in allowed_ids}
    id_pattern = re.compile(rb'"question_id"\s*:\s*"([^"]*)"')
    chunk_size = 4096
    max_id_prefix_bytes = 512
    curly_depth = 0
    square_depth = 0
    in_string = False
    escaped = False
    record_buffer = bytearray()
    record_id: str | None = None
    record_curly_depth = 0
    record_square_depth = 0

    with path.open("rb") as source:
        while chunk := source.read(chunk_size):
            for byte in chunk:
                at_record_start = (
                    not in_string
                    and byte == ord("{")
                    and curly_depth == 1
                    and square_depth == 1
                )
                if at_record_start:
                    record_buffer = bytearray(b"{")
                    record_id = None
                    record_curly_depth = 1
                    record_square_depth = 0
                    curly_depth += 1
                    continue

                if record_curly_depth > 0:
                    if record_id is not None:
                        record_buffer.append(byte)
                    else:
                        record_buffer.append(byte)
                        match = id_pattern.search(record_buffer)
                        if match is not None:
                            record_id = allowed_bytes.get(match.group(1))
                            if record_id is None:
                                record_buffer.clear()
                            elif record_id in records:
                                raise RuntimeError(
                                    "question allowlist identity is missing "
                                    "or duplicated"
                                )
                        elif len(record_buffer) > max_id_prefix_bytes:
                            raise RuntimeError(
                                "question ID is missing or too far into its "
                                "record"
                            )

                if in_string:
                    if escaped:
                        escaped = False
                    elif byte == ord("\\"):
                        escaped = True
                    elif byte == ord('"'):
                        in_string = False
                    continue
                if byte == ord('"'):
                    in_string = True
                    continue

                if byte == ord("{"):
                    curly_depth += 1
                    if record_curly_depth > 0:
                        record_curly_depth += 1
                elif byte == ord("}"):
                    curly_depth -= 1
                    if record_curly_depth > 0:
                        record_curly_depth -= 1
                elif byte == ord("["):
                    square_depth += 1
                    if record_curly_depth > 0:
                        record_square_depth += 1
                elif byte == ord("]"):
                    square_depth -= 1
                    if record_curly_depth > 0:
                        record_square_depth -= 1

                if record_curly_depth == 0:
                    if record_id is not None:
                        record = json.loads(record_buffer.decode("utf-8"))
                        if record.get("question_id") != record_id:
                            raise RuntimeError(
                                "question record does not match its "
                                "allowlisted ID"
                            )
                        records[record_id] = record
                    record_buffer.clear()
                    record_id = None

    if records.keys() != allowed_ids:
        raise RuntimeError(
            "question allowlist identity is missing or duplicated"
        )
    return list(records.values())


def _connect_test_database() -> Engine:
    url = _read_env_value("SCISCOPE_TEST_DATABASE_URL")
    if not url or make_url(url).database != "sciscope_test_005":
        raise RuntimeError("test database identity preflight failed")
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as connection, connection.begin():
            connection.execute(text("SET TRANSACTION READ ONLY"))
            identity = connection.execute(
                text(
                    "SELECT current_database(), current_user, "
                    "current_setting('server_version_num')"
                )
            ).one()
            extension = connection.execute(
                text(
                    "SELECT extversion FROM pg_extension WHERE extname='vector'"
                )
            ).scalar_one_or_none()
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one_or_none()
            active_id = connection.execute(
                text("SELECT id FROM delivery_imports WHERE is_active")
            ).scalar_one_or_none()
            counts = connection.execute(
                text(
                    "SELECT (SELECT count(*) FROM papers "
                    "WHERE delivery_import_id=:id), "
                    "(SELECT count(*) FROM sections "
                    "WHERE delivery_import_id=:id), "
                    "(SELECT count(*) FROM chunks "
                    "WHERE delivery_import_id=:id), "
                    "(SELECT count(*) FROM chunk_embeddings "
                    "WHERE delivery_import_id=:id)"
                ),
                {"id": active_id},
            ).one()
            if (
                identity[0] != "sciscope_test_005"
                or identity[1] != "sciscope"
                or not str(identity[2]).startswith("17")
                or extension != "0.8.7"
                or revision != "f005_pgvector_foundation"
                or tuple(counts) != EXPECTED_COUNTS
            ):
                raise RuntimeError(
                    "read-only identity or pilot preflight failed"
                )
        return engine
    except Exception:
        engine.dispose()
        raise


def _read_embedding_vectors(
    questions: list[dict[str, Any]],
) -> dict[str, list[float]]:
    utf8_bytes = sum(
        len(item["question"].encode("utf-8")) for item in questions
    )
    if utf8_bytes > MAX_QUERY_TOKENS:
        raise RuntimeError(
            "approved question set exceeded the token safety cap"
        )
    config = EmbeddingConfig(
        model="text-embedding-3-small",
        dimensions=1536,
        query_prefix="",
        max_inputs_per_request=5,
        max_tokens_per_request=MAX_QUERY_TOKENS,
        max_attempts=1,
        request_timeout_seconds=60.0,
    )
    environment = {"OPENAI_API_KEY": _read_env_value("OPENAI_API_KEY")}
    key = read_api_key(environment)
    base_url, custom = read_base_url({})
    transport = UrllibTransport(
        OpenAIConnection(
            api_key=key,
            url=embeddings_url(base_url),
            custom_base_url_used=custom,
        )
    )
    result = OpenAIEmbedder(config, transport).embed_queries(
        [item["question"] for item in questions]
    )
    if result.usage.prompt_tokens > MAX_QUERY_TOKENS:
        raise RuntimeError("embedding usage exceeded the token spending cap")
    cost = result.usage.prompt_tokens * 0.02 / 1_000_000
    if cost > MAX_QUERY_COST_USD:
        raise RuntimeError("embedding usage exceeded the USD spending cap")
    vectors = {
        item["question_id"]: list(vector)
        for item, vector in zip(questions, result.vectors, strict=True)
    }
    return {
        "provider": "openai",
        "model": "text-embedding-3-small",
        "dimensions": 1536,
        "query_prefix": "",
        "prompt_tokens": result.usage.prompt_tokens,
        "total_tokens": result.usage.total_tokens,
        "estimated_cost_usd": round(cost, 9),
        "attempts": result.attempts,
        "vectors": vectors,
    }


def _positive_references(question: dict[str, Any]) -> list[dict[str, str]]:
    references: list[dict[str, str]] = []
    for paper in question["relevant_papers"]:
        for evidence in paper["evidence"]:
            if int(evidence["relevance_label"]) < 2:
                continue
            locator = evidence["source_locator"]
            quotation = evidence["quotation"]
            evidence_id = hashlib.sha256(
                f"{paper['doi']}\t{locator}\t{quotation}".encode()
            ).hexdigest()
            references.append(
                {
                    "evidence_id": evidence_id,
                    "doi": paper["doi"],
                    "locator": locator,
                    "quotation": quotation,
                    "section": paper["sections"][0],
                }
            )
    return references


def _prepare_inputs() -> dict[str, Any]:
    questions = _approved_questions()
    engine = _connect_test_database()
    # Confirm identity and pilot counts read-only before the paid API request.
    embedding_data = _read_embedding_vectors(questions)
    vectors = embedding_data["vectors"]
    try:
        lookup = EvidenceLookup(engine)
        references = {
            question["question_id"]: _positive_references(question)
            for question in questions
        }
        locator_ref_matches: dict[str, dict[str, set[str]]] = {}
        for question_id, items in references.items():
            matches: dict[str, set[str]] = {}
            for item in items:
                for row in lookup.get_by_locator(item["doi"], item["locator"]):
                    matches.setdefault(row.chunk.chunk_id, set()).add(
                        item["evidence_id"]
                    )
            locator_ref_matches[question_id] = matches

        class SavedVectorEmbedder:
            def embed_query(self, query: str, *, config: object) -> list[float]:
                del config
                for item in questions:
                    if item["question"] == query:
                        return vectors[item["question_id"]]
                raise ValueError("query was not in the approved smoke set")

        core = _RetrievalCore(engine, SavedVectorEmbedder())
        result_questions = []
        corpus_metadata: dict[str, Any] | None = None
        for question in questions:
            question_id = question["question_id"]
            request = {
                "contract_version": "retrieval.v1",
                "request_id": f"phase-c-rerank-{question_id}",
                "query_text": question["question"],
                "mode": "hybrid",
                "top_k": 50,
                "ranking": {"candidate_pool_size": 50},
            }
            started = time.perf_counter()
            response = core.retrieve(request)
            retrieval_ms = (time.perf_counter() - started) * 1000
            if corpus_metadata is None:
                corpus_metadata = {
                    "corpus_version": response.corpus.corpus_version,
                    "delivery_digest": response.corpus.delivery_digest,
                    "source_contract_version": (
                        response.corpus.source_contract_version
                    ),
                    "rrf_constant": response.rrf_constant,
                    "active_import_id": response.corpus.import_id,
                }
            positive_refs = references[question_id]
            relevant_ids = tuple(item["evidence_id"] for item in positive_refs)
            candidates = []
            for hit in response.results:
                matched = sorted(
                    locator_ref_matches[question_id].get(hit.chunk_id, set())
                )
                # Controlled fallback from the protocol: same DOI/section and
                # exact quotation containment; locator match remains primary.
                if not matched:
                    for reference in positive_refs:
                        if (
                            reference["doi"] == hit.doi
                            and " > ".join(hit.section_path)
                            == reference["section"]
                            and reference["quotation"] in hit.text
                        ):
                            matched.append(reference["evidence_id"])
                candidates.append(
                    {
                        "chunk_id": hit.chunk_id,
                        "text": hit.text,
                        "matched_evidence_ids": matched,
                        "doi": hit.doi,
                        "source_locator": hit.source_locator,
                        "rrf_score": hit.scores.fusion_score,
                    }
                )
            result_questions.append(
                {
                    "question_id": question_id,
                    "question_type": question["question_type"],
                    "question": question["question"],
                    "question_sha256": hashlib.sha256(
                        question["question"].encode("utf-8")
                    ).hexdigest(),
                    "candidates": candidates,
                    "relevant_evidence_ids": list(relevant_ids),
                    "rrf_latency_ms": retrieval_ms,
                    "candidate_count": len(candidates),
                }
            )
        return {
            "input_schema": "phase-c-rerank-input-v1",
            "approved_question_ids": sorted(APPROVED_QUESTION_IDS),
            "embedding": {
                key: value
                for key, value in embedding_data.items()
                if key != "vectors"
            },
            "vectors": vectors,
            "corpus": corpus_metadata,
            "questions": result_questions,
        }
    finally:
        engine.dispose()


def _load_model() -> tuple[MiniLMCrossEncoderReranker, dict[str, str]]:
    allowed = [
        "config.json",
        "model.safetensors",
        "special_tokens_map.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "vocab.txt",
    ]
    checkpoint = ARTIFACTS / "model" / MODEL_REVISION
    if not checkpoint.is_dir() or any(
        not (checkpoint / filename).is_file() for filename in allowed
    ):
        from huggingface_hub import snapshot_download

        cached_snapshot = Path(
            snapshot_download(
                MODEL_ID,
                revision=MODEL_REVISION,
                cache_dir=str(ARTIFACTS / "hf-cache"),
                allow_patterns=allowed,
                local_files_only=True,
            )
        )
        checkpoint.mkdir(parents=True, exist_ok=True)
        for filename in allowed:
            source = cached_snapshot / filename
            destination = checkpoint / filename
            destination.parent.mkdir(parents=True, exist_ok=True)
            # Copy through HF cache links to create a self-contained model.
            shutil.copyfile(source, destination)
    digest = _directory_sha256(checkpoint)
    if digest != MODEL_SHA256:
        raise RuntimeError("pinned local model checkpoint SHA-256 mismatch")
    reranker = MiniLMCrossEncoderReranker(
        checkpoint,
        model_revision=MODEL_REVISION,
        expected_sha256=MODEL_SHA256,
    )
    return reranker, {
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "model_sha256": digest,
        "allowed_files": ",".join(allowed),
    }


def _directory_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(path.rglob("*")):
        if item.is_file():
            relative = item.relative_to(path).as_posix().encode("utf-8")
            digest.update(len(relative).to_bytes(8, "big"))
            digest.update(relative)
            digest.update(item.read_bytes())
    return digest.hexdigest()


def _metric_dict(value: Any) -> dict[str, dict[str, float | None]]:
    return {
        name: {str(k): v for k, v in getattr(value, name).items()}
        for name in ("recall_at_k", "evidence_hit_at_k", "mrr_at_k")
    }


def _run() -> dict[str, Any]:
    input_path = ARTIFACTS / "benchmark-inputs.json"
    if not input_path.is_file():
        raise RuntimeError(
            "saved benchmark inputs are missing; run --prepare-inputs "
            "separately before offline --run"
        )
    inputs = json.loads(input_path.read_text(encoding="utf-8"))
    if inputs.get("approved_question_ids") != sorted(APPROVED_QUESTION_IDS):
        raise RuntimeError("saved benchmark inputs are not the approved set")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    reranker, model_metadata = _load_model()
    questions = [
        BenchmarkQuestion(
            question_id=item["question_id"],
            question_type={
                "single_paper_factual": "single_paper",
                "multi_paper_comparison": "comparison",
                "conflicting_evidence": "conflict",
                "research_gap": "gap",
                "insufficient_evidence": "insufficient",
            }[item["question_type"]],
            query_text=item["question"],
            candidates=tuple(
                BenchmarkCandidate(
                    chunk_id=candidate["chunk_id"],
                    text=candidate["text"],
                    matched_evidence_ids=tuple(
                        candidate["matched_evidence_ids"]
                    ),
                )
                for candidate in item["candidates"]
            ),
            relevant_evidence_ids=tuple(item["relevant_evidence_ids"]),
            rrf_latency_ms=item["rrf_latency_ms"],
        )
        for item in inputs["questions"]
    ]
    environment = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu": platform.processor() or platform.machine(),
        "torch": _package_version("torch"),
        "sentence_transformers": _package_version("sentence-transformers"),
        "transformers": _package_version("transformers"),
        "huggingface_hub": _package_version("huggingface-hub"),
        "numpy": _package_version("numpy"),
        "device": "cpu",
    }
    import torch

    environment["torch_threads"] = str(torch.get_num_threads())
    environment["torch_interop_threads"] = str(torch.get_num_interop_threads())
    result = compare_reranker(
        questions,
        reranker,
        repetitions=5,
        environment=environment,
        run_metadata={
            **model_metadata,
            "git_revision": subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip(),
            "benchmark_command": (
                "python scripts/phase_c_minilm_benchmark.py --run"
            ),
            "benchmark_runner_sha256": hashlib.sha256(
                Path(__file__).read_bytes()
            ).hexdigest(),
            "evaluation_engine_sha256": hashlib.sha256(
                (ROOT / "src/sciscope/evaluation/rerank.py").read_bytes()
            ).hexdigest(),
            "reranker_adapter_sha256": hashlib.sha256(
                (ROOT / "src/sciscope/retrieval/_reranking.py").read_bytes()
            ).hexdigest(),
            "ranking_policy_sha256": hashlib.sha256(
                (ROOT / "src/sciscope/retrieval/_quality.py").read_bytes()
            ).hexdigest(),
            "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
            "dependency_lock_sha256": hashlib.sha256(
                DEPENDENCY_LOCK_PATH.read_bytes()
            ).hexdigest(),
            "dataset_version": "v0-approved-five-question-subset",
            "corpus_version": inputs["corpus"]["corpus_version"],
            "delivery_digest": inputs["corpus"]["delivery_digest"],
            "postgresql_major": "17",
            "pgvector_version": "0.8.7",
            "migration_revision": "f005_pgvector_foundation",
            "embedding_model": "text-embedding-3-small",
            "embedding_dimensions": "1536",
            "retrieval_mode": "hybrid",
            "filters": "none",
            "top_k": "50",
            "candidate_pool_size": "50",
            "rrf_constant": str(inputs["corpus"]["rrf_constant"]),
        },
    )
    assessment = assess_diagnostic(result)
    output = {
        "benchmark_schema": "phase-c-rerank-result-v1",
        "question_ids": list(result.question_ids),
        "per_question": {
            question_id: {
                "question_type": next(
                    item["question_type"]
                    for item in inputs["questions"]
                    if item["question_id"] == question_id
                ),
                "candidate_count": next(
                    item["candidate_count"]
                    for item in inputs["questions"]
                    if item["question_id"] == question_id
                ),
                "relevant_evidence_count": len(
                    next(
                        item["relevant_evidence_ids"]
                        for item in inputs["questions"]
                        if item["question_id"] == question_id
                    )
                ),
                "baseline": _metric_dict(comparison.baseline),
                "reranked": _metric_dict(comparison.reranked),
            }
            for question_id, comparison in result.per_question.items()
        },
        "baseline_macro": _metric_dict(result.baseline_macro),
        "reranked_macro": _metric_dict(result.reranked_macro),
        "positive_macro_denominator": sum(
            bool(item["relevant_evidence_ids"]) for item in inputs["questions"]
        ),
        "latency_ms": {
            "rrf_p95": result.rrf_p95_ms,
            "reranker_warm_p95": result.reranker_p95_ms,
            "combined_warm_p95": result.warm_p95_ms,
            "cold_start": result.cold_start_ms,
            "per_question_rrf_ms": {
                item["question_id"]: item["rrf_latency_ms"]
                for item in inputs["questions"]
            },
        },
        "assessment": {
            "quality_gate_passed": assessment.quality_gate_passed,
            "regression_gate_passed": assessment.regression_gate_passed,
            "latency_gate_passed": assessment.latency_gate_passed,
            "diagnostic_passed": assessment.diagnostic_passed,
            "production_enabled": assessment.production_enabled,
            "reasons": list(assessment.reasons),
        },
        "embedding_usage": inputs["embedding"],
        "model": model_metadata,
        "manifest": result.run_manifest,
        "limitations": [
            "five development smoke questions only; not a release benchmark",
            "insufficient-evidence has no positive labels and is excluded "
            "from positive macro metrics",
            "candidate set is limited to the fixed Phase B hybrid top 50",
            "latency is diagnostic local retrieval plus reranking, not total "
            "RAG latency",
            "production reranking remains disabled pending owner approval",
        ],
    }
    result_path = ARTIFACTS / "benchmark-result.json"
    result_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    output["artifact_paths"] = {
        "inputs": str(input_path.relative_to(ROOT)),
        "result": str(result_path.relative_to(ROOT)),
    }
    return output


def _package_version(name: str) -> str:
    from importlib.metadata import version

    return version(name)


def main() -> int:
    """Run the approved benchmark and print its secret-free summary."""
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--prepare-inputs",
        action="store_true",
        help="make the bounded embedding request and read-only retrieval",
    )
    mode.add_argument(
        "--run",
        action="store_true",
        help="run only from saved inputs and pinned local model artifacts",
    )
    arguments = parser.parse_args()
    if arguments.prepare_inputs:
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        input_path = ARTIFACTS / "benchmark-inputs.json"
        if input_path.exists():
            raise RuntimeError(
                "benchmark inputs already exist; refusing duplicate API spend"
            )
        inputs = _prepare_inputs()
        input_path.write_text(json.dumps(inputs, indent=2), encoding="utf-8")
        print(
            json.dumps(
                {
                    "prepared_question_ids": inputs["approved_question_ids"],
                    "embedding_usage": inputs["embedding"],
                    "candidate_counts": {
                        item["question_id"]: item["candidate_count"]
                        for item in inputs["questions"]
                    },
                    "input_path": str(input_path.relative_to(ROOT)),
                },
                indent=2,
            )
        )
        return 0
    result = _run()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
