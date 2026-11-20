"""Generate approved frozen Phase D held-out query vectors."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from sciscope.chunking.counter import Utf8BytesDiv3Counter
from sciscope.embedding.config import EmbeddingConfig
from sciscope.embedding.openai_client import (
    OpenAIConnection,
    OpenAIEmbedder,
    UrllibTransport,
    embeddings_url,
    read_api_key,
    read_base_url,
)
from sciscope.evaluation.embeddings import verify_query_cache_manifest
from sciscope.evaluation.golden import (
    load_allowlisted_records,
    partition_sha256,
)
from sciscope.evaluation.query_cache import generate_query_cache

ROOT = Path(__file__).resolve().parents[1]
PROTECTED = ROOT / "evals" / "protected"
V0_PATH = ROOT / "evals" / "golden_questions.v0.json"
V1_BASE = PROTECTED / "golden_v1_review"
RECEIPT_PATH = (
    PROTECTED
    / "phase_d_authorizations"
    / ("t005_embedding_generation_user_approval.json")
)
READINESS_PATH = PROTECTED / "phase_d_t005_readiness_report.json"
CORPUS_VERSION = "pilot17-xml-1fff1573b610"
CORPUS_SHA256 = (
    "1fff1573b610c27e2e8016343d2f6429df294db974db4af898c4a0f82ffc26bd"
)
EMBEDDING_SET_ID = 115
V0_DEV_IDS = {
    "gq-sp-001",
    "gq-cmp-001",
    "gq-conf-001",
    "gq-gap-001",
    "gq-ins-001",
}
V0_ALL_IDS = {
    *(f"gq-sp-{number:03}" for number in range(1, 9)),
    *(f"gq-cmp-{number:03}" for number in range(1, 5)),
    *(f"gq-conf-{number:03}" for number in range(1, 4)),
    *(f"gq-gap-{number:03}" for number in range(1, 4)),
    *(f"gq-ins-{number:03}" for number in range(1, 4)),
}
V1_HO_IDS = {
    "golden-v1-q2",
    "golden-v1-q3",
    "golden-v1-q5",
    "golden-v1-q7",
    "golden-v1-q8",
    "golden-v1-q9",
}
EXPECTED_EXCERPT = (
    "I explicitly authorize you to generate ALL missing query embeddings "
    "required to complete Phase D, using OpenAI `text-embedding-3-small` "
    "with 1536 dimensions. There is NO monetary cap on the required "
    "embedding generation. Do not stop to request additional approval for "
    "these embedding API calls. You are explicitly authorized to access "
    "the necessary protected question text and transmit it to the OpenAI "
    "embeddings API solely for this purpose."
)
EXPECTED_CONFIG = {
    "provider": "openai",
    "model": "text-embedding-3-small",
    "response_model_id": "text-embedding-3-small",
    "dimensions": 1536,
    "query_prefix": "",
    "passage_prefix": "",
    "dtype": "float32-le",
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _read_environment() -> dict[str, str]:
    environment = dict(os.environ)
    if "OPENAI_API_KEY" not in environment:
        env_path = ROOT / ".env"
        if env_path.is_file():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                candidate = line.strip()
                if candidate.startswith("OPENAI_API_KEY="):
                    environment["OPENAI_API_KEY"] = (
                        candidate.split("=", 1)[1].strip().strip("\"'")
                    )
                    break
    return environment


def _verify_approval_receipt() -> dict[str, Any]:
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    excerpt = receipt.get("approval_excerpt")
    if (
        excerpt != EXPECTED_EXCERPT
        or receipt.get("approval_excerpt_sha256")
        != _sha256(EXPECTED_EXCERPT.encode("utf-8"))
        or receipt.get("purpose") != "T005 query embedding generation only"
        or receipt.get("scope", {}).get("cohorts")
        != ["v0-held-out", "v1-held-out"]
        or receipt.get("scope", {}).get("maximum_spend_usd") is not None
        or receipt.get("scope", {}).get("retrieval_evaluation") is not False
    ):
        raise ValueError("explicit embedding authorization receipt invalid")
    if not isinstance(receipt, dict):
        raise ValueError("explicit embedding authorization receipt invalid")
    return cast(dict[str, Any], receipt)


def _v0_identity() -> dict[str, Any]:
    dataset_bytes = V0_PATH.read_bytes()
    dataset_hash = _sha256(dataset_bytes)
    held_out_ids = frozenset(V0_ALL_IDS - V0_DEV_IDS)
    if len(held_out_ids) != 16:
        raise ValueError("frozen Golden v0 partition size mismatch")
    return {
        "dataset_version": "v0",
        "dataset_sha256": dataset_hash,
        "partition": "v0-held-out",
        "partition_sha256": partition_sha256(sorted(held_out_ids)),
        "expected_count": 16,
    }


def _v1_identity() -> dict[str, Any]:
    freeze_path = V1_BASE / "phase_d_baseline_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    frozen_partitions = freeze.get("golden_v1_partitions", {})
    if (
        frozen_partitions.get("assignment_frozen_before_question_generation")
        is not True
    ):
        raise ValueError("Golden v1 partition freeze missing")
    dataset_path = V1_BASE / "golden_questions.v1.candidates.json"
    dataset_hash = _sha256(dataset_path.read_bytes())
    return {
        "dataset_version": "golden-v1",
        "dataset_sha256": dataset_hash,
        "partition": "v1-held-out",
        "partition_sha256": partition_sha256(sorted(V1_HO_IDS)),
        "expected_count": 6,
    }


def _load_v0_held_out() -> list[dict[str, Any]]:
    held_out_ids = frozenset(V0_ALL_IDS - V0_DEV_IDS)
    return load_allowlisted_records(V0_PATH, held_out_ids)


def _load_v1_held_out() -> list[dict[str, Any]]:
    split_path = V1_BASE / "held_out" / "golden_questions.v1.held_out.json"
    records = json.loads(split_path.read_text(encoding="utf-8"))["questions"]
    if not isinstance(records, list):
        raise ValueError("frozen Golden v1 partition is malformed")
    if {record.get("question_id") for record in records} != V1_HO_IDS:
        raise ValueError("frozen Golden v1 held-out partition mismatch")
    return cast(list[dict[str, Any]], records)


def _cohort_expected(
    cohort: str, dataset: dict[str, Any], embedding_set_id: int
) -> dict[str, Any]:
    identity = {
        key: value for key, value in dataset.items() if key != "expected_count"
    }
    return {
        **identity,
        "corpus_version": CORPUS_VERSION,
        "corpus_sha256": CORPUS_SHA256,
        "embedding_set_id": embedding_set_id,
    }


def _prepare_cache(
    cohort: str,
    records: list[dict[str, Any]],
    dataset: dict[str, Any],
    *,
    config: EmbeddingConfig,
    environment: dict[str, str],
) -> dict[str, Any]:
    expected = _cohort_expected(cohort, dataset, EMBEDDING_SET_ID)
    cache_dir = ROOT / "data" / "embeddings" / "phase-d-query" / cohort
    manifest_path = cache_dir / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_with_hash = {
            **expected,
            "config": EXPECTED_CONFIG,
            "manifest_sha256": _sha256(_canonical(manifest)),
        }
        ready = verify_query_cache_manifest(
            cache_dir, manifest, records, expected=expected_with_hash
        )
        return {
            "cohort": cohort,
            "status": "REUSED_VERIFIED",
            "manifest_sha256": ready.manifest_sha256,
            "vector_count": len(ready.verified_question_ids),
            "api_calls": 0,
            "attempts": 0,
            "prompt_tokens": 0,
            "total_tokens": 0,
            "cost_usd": 0.0,
        }
    if cache_dir.exists() and any(cache_dir.iterdir()):
        raise ValueError("unmanifested cache content blocks safe generation")

    key = read_api_key(environment)
    base_url, custom = read_base_url(environment)
    connection = OpenAIConnection(key, embeddings_url(base_url), custom)

    def embedder_factory() -> OpenAIEmbedder:
        return OpenAIEmbedder(config, UrllibTransport(connection))

    result = generate_query_cache(
        records,
        cache_directory=cache_dir,
        manifest_path=manifest_path,
        expected=expected,
        config=config,
        counter=Utf8BytesDiv3Counter(),
        embedder_factory=embedder_factory,
        utc_now=lambda: datetime.now(UTC),
    )
    ready = verify_query_cache_manifest(
        cache_dir,
        result.manifest,
        records,
        expected={
            **expected,
            "config": EXPECTED_CONFIG,
            "manifest_sha256": result.manifest_sha256,
        },
    )
    return {
        "cohort": cohort,
        "status": "GENERATED_AND_VERIFIED",
        **result.to_dict(),
    }


def run() -> dict[str, Any]:
    """Verify the approval and cohort identities, then fill missing vectors."""
    _verify_approval_receipt()
    v0_dataset = _v0_identity()
    v1_dataset = _v1_identity()
    report = json.loads(READINESS_PATH.read_text(encoding="utf-8"))
    recorded = {item["cohort"]: item for item in report["cohorts"]}
    for name, data in (
        ("v0-held-out", v0_dataset),
        ("v1-held-out", v1_dataset),
    ):
        prior = recorded.get(name)
        if (
            prior is None
            or prior.get("dataset_sha256") != data["dataset_sha256"]
            or prior.get("partition_sha256") != data["partition_sha256"]
            or prior.get("expected_question_count") != data["expected_count"]
        ):
            raise ValueError("cohort identity differs from frozen T005 record")
    # Only after both frozen partitions and dataset hashes match the stored
    # preflight do we load allowlisted held-out question text.
    v0_records = _load_v0_held_out()
    v1_records = _load_v1_held_out()
    if len(v0_records) != 16 or len(v1_records) != 6:
        raise ValueError("held-out question population size mismatch")
    config = EmbeddingConfig()
    environment = _read_environment()
    cohorts = [
        _prepare_cache(
            "v0-held-out",
            v0_records,
            v0_dataset,
            config=config,
            environment=environment,
        ),
        _prepare_cache(
            "v1-held-out",
            v1_records,
            v1_dataset,
            config=config,
            environment=environment,
        ),
    ]
    return {
        "report_version": "phase-d-t005-query-vector-generation-v1",
        "recorded_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "authorization_receipt_sha256": _sha256(RECEIPT_PATH.read_bytes()),
        "provider": "openai",
        "model": "text-embedding-3-small",
        "dimensions": 1536,
        "query_prefix": "",
        "cohorts": cohorts,
        "totals": {
            key: sum(cohort[key] for cohort in cohorts)
            for key in (
                "vector_count",
                "api_calls",
                "attempts",
                "prompt_tokens",
                "total_tokens",
                "cost_usd",
            )
        },
        "held_out_text_logged": False,
        "retrieval_evaluation_performed": False,
        "database_mutation_performed": False,
    }


def main() -> int:
    """Execute generation with sanitized console output and protected report."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", required=True)
    parser.parse_args()
    try:
        result = run()
        output = PROTECTED / "phase_d_t005_embedding_generation_report.json"
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    except Exception:
        print("T005_QUERY_VECTOR_GENERATION=FAIL; details sanitized")
        return 1
    print(
        json.dumps(
            {
                "status": "PASS",
                "vector_count": result["totals"]["vector_count"],
                "api_calls": result["totals"]["api_calls"],
                "prompt_tokens": result["totals"]["prompt_tokens"],
                "cost_usd": result["totals"]["cost_usd"],
                "report": (
                    "evals/protected/phase_d_t005_embedding_generation_report.json"
                ),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
