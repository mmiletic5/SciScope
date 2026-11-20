"""Deterministic report serialization tests using synthetic data."""

from __future__ import annotations

import json

from sciscope.evaluation.metrics import compute_question_metrics
from sciscope.evaluation.report import build_result_report


def test_report_is_stable_and_contains_no_question_or_secret_text() -> None:
    """Manifest reports bind hashes and IDs while excluding sensitive text."""
    metrics = compute_question_metrics(
        question_id="q1",
        gold_unit_ids=frozenset({"gold-unit-1"}),
        first_rank_by_unit={"gold-unit-1": 2},
        expected_insufficient_evidence=False,
        cutoffs=(1, 3),
    )
    report = build_result_report(
        dataset_version="synthetic-v1",
        dataset_sha256="a" * 64,
        cohort="development",
        partition_sha256="b" * 64,
        corpus_version="synthetic-corpus",
        corpus_sha256="c" * 64,
        arm="hybrid_rrf",
        config_sha256="d" * 64,
        question_metrics={"q1": metrics},
        latency_ms={"retrieval": (1.0, 2.0, 3.0)},
    )

    first = json.dumps(report.to_dict(), sort_keys=True)
    second = json.dumps(report.to_dict(), sort_keys=True)
    assert first == second
    assert "synthetic question text" not in first
    assert "api_key" not in first.lower()
    assert report.to_dict()["population"]["positive_question_count"] == 1


def test_report_rejects_sensitive_manifest_metadata() -> None:
    """Secrets cannot enter ordinary result manifests."""
    metrics = compute_question_metrics(
        question_id="q1",
        gold_unit_ids=frozenset({"g1"}),
        first_rank_by_unit={},
        expected_insufficient_evidence=False,
        cutoffs=(1,),
    )
    try:
        build_result_report(
            dataset_version="synthetic-v1",
            dataset_sha256="a" * 64,
            cohort="development",
            partition_sha256="b" * 64,
            corpus_version="synthetic-corpus",
            corpus_sha256="c" * 64,
            arm="dense",
            config_sha256="d" * 64,
            question_metrics={"q1": metrics},
            latency_ms={},
            environment={"api_key": "never-log"},
        )
    except ValueError as error:
        assert "secret" in str(error)
    else:
        raise AssertionError("secret-bearing metadata was accepted")
