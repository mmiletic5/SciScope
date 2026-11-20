"""Read-only Phase D evidence and lexical diagnostic checks.

This helper intentionally reports metadata and aggregate statuses only. It
never prints Golden question text, annotations, vectors, or held-out results.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
METRICS = ("recall_at_k", "evidence_hit_at_k", "mrr_at_k")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("expected a JSON object")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit_saved_evidence(root: Path = ROOT) -> dict[str, Any]:
    """Verify saved T006 report hashes and independently recompute macros."""
    manifest = _read_json(
        root / "evals/protected/phase_d_t006_run_manifest.json"
    )
    artifacts = manifest.get("result_artifacts")
    cohorts = manifest.get("cohorts")
    if not isinstance(artifacts, dict) or len(artifacts) != 7:
        raise ValueError("T006 artifact manifest is incomplete")
    if not isinstance(cohorts, list) or len(cohorts) != 2:
        raise ValueError("T006 cohort manifest is incomplete")

    verified_artifacts = 0
    for relative, expected in artifacts.items():
        path = (root / relative).resolve(strict=True)
        if root.resolve() not in path.parents or not path.is_file():
            raise ValueError("T006 artifact path is invalid")
        if path.stat().st_size != expected.get("bytes") or _sha256(
            path
        ) != expected.get("sha256"):
            raise ValueError("T006 artifact integrity check failed")
        verified_artifacts += 1

    verified_reports = 0
    verified_metric_aggregations = 0
    for cohort in cohorts:
        cohort_name = cohort["cohort"]
        files = cohort.get("result_files")
        if not isinstance(files, dict) or set(files) != {
            "dense",
            "lexical",
            "hybrid",
        }:
            raise ValueError("T006 arm inventory is incomplete")
        for arm, relative in files.items():
            report = _read_json(root / relative)
            expected_arm = "hybrid_rrf" if arm == "hybrid" else arm
            if (
                report.get("dataset", {}).get("cohort") != cohort_name
                or report.get("dataset", {}).get("version")
                != cohort.get("dataset_version")
                or report.get("retrieval", {}).get("arm") != expected_arm
                or report.get("population", {}).get("question_count")
                != cohort.get("question_count")
            ):
                raise ValueError("T006 report identity mismatch")
            if report.get("dataset", {}).get("sha256") != cohort.get(
                "dataset_sha256"
            ) or report.get("dataset", {}).get(
                "partition_sha256"
            ) != cohort.get("partition_sha256"):
                raise ValueError("T006 dataset/partition mismatch")

            questions = report.get("per_question")
            stored = report.get("macro_by_question")
            if not isinstance(questions, dict) or not isinstance(stored, dict):
                raise ValueError("T006 metric payload is incomplete")
            eligible = [
                item
                for item in questions.values()
                if item.get("positive_metric_eligible") is True
            ]
            if (
                len(eligible)
                != report["population"]["positive_metric_denominator_questions"]
            ):
                raise ValueError("T006 positive denominator mismatch")
            for metric in METRICS:
                by_k = stored.get(metric)
                if not isinstance(by_k, dict):
                    raise ValueError("T006 macro metric is missing")
                for cutoff, reported in by_k.items():
                    values = [
                        item[metric][cutoff]
                        for item in eligible
                        if item.get(metric, {}).get(cutoff) is not None
                    ]
                    if len(values) != len(eligible) or not values:
                        raise ValueError(
                            "T006 metric denominator is incomplete"
                        )
                    recomputed = math.fsum(values) / len(values)
                    if not math.isclose(
                        recomputed,
                        float(reported),
                        rel_tol=0.0,
                        abs_tol=1e-12,
                    ):
                        raise ValueError("T006 macro recomputation mismatch")
                    verified_metric_aggregations += 1
            verified_reports += 1

    delivery_path = root / "data/delivery/pilot/delivery_manifest.json"
    delivery = _read_json(delivery_path)
    delivery_files = delivery.get("files")
    if not isinstance(delivery_files, dict):
        raise ValueError("frozen delivery manifest is invalid")
    verified_delivery_files = 0
    for relative, metadata in delivery_files.items():
        path = (delivery_path.parent / relative).resolve(strict=True)
        if delivery_path.parent.resolve() not in path.parents:
            raise ValueError("delivery file path is invalid")
        if path.stat().st_size != metadata.get("bytes") or _sha256(
            path
        ) != metadata.get("sha256"):
            raise ValueError("frozen delivery payload hash mismatch")
        verified_delivery_files += 1

    readiness = _read_json(
        root / "evals/protected/phase_d_t005_readiness_report.json"
    )
    cache_cohorts = readiness.get("query_cache", {}).get("cohorts")
    frozen_cohorts = readiness.get("cohorts")
    if not isinstance(cache_cohorts, list) or len(cache_cohorts) != 2:
        raise ValueError("T005 query-cache cohort metadata is incomplete")
    if not isinstance(frozen_cohorts, list) or len(frozen_cohorts) != 2:
        raise ValueError("T005 frozen cohort identity is incomplete")
    frozen_by_name = {item["cohort"]: item for item in frozen_cohorts}
    verified_cache_manifests = 0
    for cache_cohort in cache_cohorts:
        name = cache_cohort.get("cohort")
        cache_path = (
            root / "data/embeddings/phase-d-query" / name / "manifest.json"
        ).resolve(strict=True)
        if root.resolve() not in cache_path.parents:
            raise ValueError("query-cache manifest path is invalid")
        cache = _read_json(cache_path)
        expected_cohort = frozen_by_name.get(name)
        config = cache.get("config", {})
        if (
            _sha256(cache_path) != cache_cohort.get("manifest_sha256")
            or len(cache.get("vectors", [])) != cache_cohort.get("vector_count")
            or cache.get("dataset_version")
            != expected_cohort.get("dataset_version")
            or cache.get("dataset_sha256")
            != expected_cohort.get("dataset_sha256")
            or cache.get("partition") != name
            or cache.get("partition_sha256")
            != expected_cohort.get("partition_sha256")
            or cache.get("corpus_version") != "pilot17-xml-1fff1573b610"
            or cache.get("embedding_set_id") != 115
            or config.get("provider") != "openai"
            or config.get("model") != "text-embedding-3-small"
            or config.get("dimensions") != 1536
            or config.get("query_prefix") != ""
            or config.get("passage_prefix") != ""
        ):
            raise ValueError("query-cache manifest identity mismatch")
        verified_cache_manifests += 1

    return {
        "status": "PASS",
        "t006_artifacts_verified": verified_artifacts,
        "t006_reports_verified": verified_reports,
        "macro_aggregations_recomputed": verified_metric_aggregations,
        "delivery_payloads_verified": verified_delivery_files,
        "query_cache_manifests_verified": verified_cache_manifests,
        "protected_question_text_emitted": False,
        "retrieval_rerun": False,
    }


_PROBES: tuple[dict[str, Any], ...] = (
    {
        "label": "latin_binomial",
        "query": "Apis mellifera",
        "doi": "10.1371/journal.pone.0000395",
        "section": "Honeybees",
        "pattern": r"Apis\s+mellifera",
        "expected_candidates": 48,
        "expected_rank": 3,
    },
    {
        "label": "acronym",
        "query": "RNA",
        "doi": "10.1371/journal.pone.0244648",
        "section": "Discussion",
        "pattern": r"\mRNA\M",
        "expected_candidates": 44,
        "expected_rank": 19,
    },
    {
        "label": "numeric_value",
        "query": "10",
        "doi": "10.1371/journal.pone.0244648",
        "section": "Discussion",
        "pattern": r"\m[0-9]+([.][0-9]+)?\M",
        "expected_candidates": 103,
        "expected_rank": 31,
    },
    {
        "label": "numeric_with_context",
        "query": "10 genes",
        "doi": "10.1371/journal.pone.0244648",
        "section": "Discussion",
        "pattern": r"\m[0-9]+([.][0-9]+)?\M",
        "expected_candidates": 17,
        "expected_rank": 1,
    },
    {
        "label": "method_term",
        "query": "feeding",
        "doi": "10.1371/journal.pone.0034137",
        "section": "Discussion",
        "pattern": r"\mfeeding\M",
        "expected_candidates": 36,
        "expected_rank": 11,
    },
    {
        "label": "named_taxon",
        "query": "Varroa destructor",
        "doi": "10.1371/journal.pone.0077354",
        "section": "Introduction",
        "pattern": r"Varroa\s+destructor",
        "expected_candidates": 14,
        "expected_rank": 3,
    },
    {
        "label": "long_single_source",
        "query": "How do Honeybees Apis mellifera bred open environment?",
        "doi": "10.1371/journal.pone.0000395",
        "section": "Honeybees",
        "pattern": r"Apis\s+mellifera",
        "expected_candidates": 1,
        "expected_rank": 1,
    },
    {
        "label": "long_cross_source",
        "query": "How do Honeybees Apis mellifera and sequencing used provide?",
        "expected_candidates": 0,
        "expected_rank": None,
    },
)


def run_lexical_probes() -> dict[str, Any]:
    """Run fixed source-derived probes in an explicit read-only transaction."""
    from sciscope.database.config import DatabaseSettings
    from sciscope.database.session import create_database_engine
    from scripts.phase_d_readonly_db_preflight import (
        _load_source_url,
        derive_test_database_url,
    )

    engine = create_database_engine(
        DatabaseSettings(url=derive_test_database_url(_load_source_url()))
    )
    rows: list[dict[str, Any]] = []
    try:
        with engine.connect() as connection:
            with connection.begin():
                connection.execute(text("SET TRANSACTION READ ONLY"))
                identity = connection.execute(
                    text(
                        "SELECT current_database(), current_user, "
                        "current_setting('transaction_read_only')"
                    )
                ).one()
                if identity != ("sciscope_test_005", "sciscope", "on"):
                    raise ValueError("diagnostic DB safety identity mismatch")
                for probe in _PROBES:
                    params = {"query": probe["query"]}
                    querytree = connection.execute(
                        text(
                            "SELECT querytree(websearch_to_tsquery("
                            "'english', :query))"
                        ),
                        params,
                    ).scalar_one()
                    candidate_count = connection.execute(
                        text(
                            "SELECT count(*) FROM chunks c "
                            "JOIN delivery_imports di "
                            "ON di.id = c.delivery_import_id AND di.is_active "
                            "WHERE to_tsvector('english', c.text) @@ "
                            "websearch_to_tsquery('english', :query)"
                        ),
                        params,
                    ).scalar_one()
                    target_rank: int | None = None
                    target_locator_verified: bool | None = None
                    if probe.get("doi"):
                        target = connection.execute(
                            text(
                                "SELECT c.chunk_id, c.doi, c.source_locator "
                                "FROM chunks c JOIN delivery_imports di "
                                "ON di.id = c.delivery_import_id "
                                "AND di.is_active WHERE c.doi = :doi "
                                "AND c.section_path::text ILIKE :section "
                                "AND c.text ~ :pattern "
                                "ORDER BY c.chunk_id LIMIT 1"
                            ),
                            {
                                "doi": probe["doi"],
                                "section": f"%{probe['section']}%",
                                "pattern": probe["pattern"],
                            },
                        ).one_or_none()
                        if target is None:
                            raise ValueError(
                                "diagnostic target evidence missing"
                            )
                        ranked = connection.execute(
                            text(
                                "SELECT c.chunk_id, c.doi, c.source_locator, "
                                "row_number() OVER (ORDER BY "
                                "ts_rank_cd(to_tsvector('english', c.text), "
                                "websearch_to_tsquery('english', :query)) "
                                "DESC, c.chunk_id ASC) AS rank "
                                "FROM chunks c JOIN delivery_imports di "
                                "ON di.id = c.delivery_import_id "
                                "AND di.is_active WHERE "
                                "to_tsvector('english', c.text) @@ "
                                "websearch_to_tsquery('english', :query)"
                            ),
                            params,
                        ).all()
                        target_rank = next(
                            (
                                int(row.rank)
                                for row in ranked
                                if row.chunk_id == target.chunk_id
                            ),
                            None,
                        )
                        target_locator_verified = target.doi == probe[
                            "doi"
                        ] and bool(target.source_locator)
                    expected_candidates = probe["expected_candidates"]
                    expected_rank = probe["expected_rank"]
                    passed = (
                        int(candidate_count) == expected_candidates
                        and target_rank == expected_rank
                        and (
                            target_locator_verified is None
                            or target_locator_verified
                        )
                    )
                    rows.append(
                        {
                            "label": probe["label"],
                            "query": probe["query"],
                            "expected_candidates": expected_candidates,
                            "observed_candidates": int(candidate_count),
                            "expected_target_rank": expected_rank,
                            "observed_target_rank": target_rank,
                            "target_doi_locator_verified": (
                                target_locator_verified
                            ),
                            "querytree": querytree,
                            "pass": passed,
                        }
                    )
    finally:
        engine.dispose()
    return {
        "status": "PASS" if all(row["pass"] for row in rows) else "FAIL",
        "transaction_read_only": True,
        "database": "sciscope_test_005",
        "probe_count": len(rows),
        "probes": rows,
        "protected_question_text_accessed": False,
        "retrieval_tuning_performed": False,
    }


def run_synthetic_rrf_diagnostic() -> dict[str, Any]:
    """Compare frozen RRF with a separate arithmetic oracle on mock ranks."""
    from sciscope.retrieval._ranking import BranchHit, fuse_ranked_candidates

    dense_ids = ["dense-only", "shared-a", "shared-b"]
    lexical_ids = ["lexical-only", "shared-b", "shared-a"]
    expected_scores: dict[str, float] = {}
    best_rank: dict[str, int] = {}
    for branch in (dense_ids, lexical_ids):
        for rank, chunk_id in enumerate(branch, start=1):
            expected_scores[chunk_id] = expected_scores.get(chunk_id, 0.0) + (
                1.0 / (60 + rank)
            )
            best_rank[chunk_id] = min(best_rank.get(chunk_id, rank), rank)
    expected = sorted(
        expected_scores,
        key=lambda chunk_id: (
            -expected_scores[chunk_id],
            best_rank[chunk_id],
            chunk_id,
        ),
    )
    actual = fuse_ranked_candidates(
        [
            BranchHit(chunk_id, 1.0 / rank)
            for rank, chunk_id in enumerate(dense_ids, 1)
        ],
        [
            BranchHit(chunk_id, 1.0 / rank)
            for rank, chunk_id in enumerate(lexical_ids, 1)
        ],
        constant=60,
        top_k=10,
    )
    actual_ids = [candidate.chunk_id for candidate in actual]
    passed = (
        actual_ids == expected
        and len(actual_ids) == 4
        and {candidate.chunk_id for candidate in actual}
        == set(dense_ids) | set(lexical_ids)
        and all(
            math.isclose(
                candidate.score,
                expected_scores[candidate.chunk_id],
                rel_tol=0.0,
                abs_tol=1e-15,
            )
            for candidate in actual
        )
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "expected_order": expected,
        "observed_order": actual_ids,
        "expected_unique_union_count": len(set(dense_ids) | set(lexical_ids)),
        "observed_unique_union_count": len(actual_ids),
        "overlap_deduplicated": len(actual_ids) == 4,
        "independent_score_oracle_matches": passed,
        "held_out_data_used": False,
    }


def main() -> int:
    """Run requested offline checks and emit sanitized JSON summaries."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saved-evidence", action="store_true")
    parser.add_argument("--lexical-probes", action="store_true")
    parser.add_argument("--rrf-diagnostic", action="store_true")
    args = parser.parse_args()
    if not (args.saved_evidence or args.lexical_probes or args.rrf_diagnostic):
        parser.error("select at least one audit")
    try:
        reports: dict[str, Any] = {}
        if args.saved_evidence:
            reports["saved_evidence"] = audit_saved_evidence()
        if args.lexical_probes:
            reports["lexical_probes"] = run_lexical_probes()
        if args.rrf_diagnostic:
            reports["rrf_diagnostic"] = run_synthetic_rrf_diagnostic()
        print(json.dumps(reports, sort_keys=True))
    except Exception:
        print("MANUAL_AUDIT=FAIL; details sanitized")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
