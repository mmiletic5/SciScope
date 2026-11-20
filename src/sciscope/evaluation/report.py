"""Deterministic, question-text-free Phase D result reports."""

from __future__ import annotations

import math
import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sciscope.evaluation.metrics import QuestionMetrics, aggregate_macro

_SAFE_ENVIRONMENT_FIELDS = {
    "os",
    "windows_build",
    "python_version",
    "dependency_lock_sha256",
    "git_revision",
    "git_dirty",
    "cpu_model",
    "memory_bytes",
}


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    """Machine-readable per-question and cohort retrieval report."""

    payload: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready copy of the deterministic report payload."""
        return dict(self.payload)


def build_result_report(
    *,
    dataset_version: str,
    dataset_sha256: str,
    cohort: str,
    partition_sha256: str,
    corpus_version: str,
    corpus_sha256: str,
    arm: str,
    config_sha256: str,
    question_metrics: Mapping[str, QuestionMetrics],
    latency_ms: Mapping[str, Sequence[float]],
    environment: Mapping[str, str | int | bool] | None = None,
) -> EvaluationReport:
    """Create stable results with explicit populations and no query text.

    Args:
        dataset_version: Frozen dataset identity.
        dataset_sha256: Full dataset content digest.
        cohort: Named evaluation cohort, not a mixed partition.
        partition_sha256: Hash of the exact evaluated question IDs.
        corpus_version: Frozen retrieval corpus identity.
        corpus_sha256: Frozen corpus digest.
        arm: One of dense, lexical, or hybrid RRF.
        config_sha256: Frozen retrieval configuration digest.
        question_metrics: Per-question metric records indexed by question ID.
        latency_ms: Observed stage timings, in milliseconds.
        environment: Allowlisted, non-secret execution context.

    Returns:
        A deterministic report payload suitable for JSON serialization.

    Raises:
        ValueError: If identities, metric IDs, timings, or environment are
            invalid or may expose a secret.
    """
    identities = (dataset_version, cohort, corpus_version, arm)
    if any(
        not isinstance(value, str) or not value.strip() for value in identities
    ):
        raise ValueError("report identities must be nonempty")
    if arm not in {"dense", "lexical", "hybrid_rrf"}:
        raise ValueError("unsupported retrieval arm")
    for digest in (
        dataset_sha256,
        partition_sha256,
        corpus_sha256,
        config_sha256,
    ):
        if len(digest) != 64 or any(
            ch not in "0123456789abcdef" for ch in digest
        ):
            raise ValueError("report hashes must be lowercase SHA-256")
    if any(
        key != metric.question_id for key, metric in question_metrics.items()
    ):
        raise ValueError("question metric keys must match question IDs")
    if not question_metrics:
        raise ValueError("report requires at least one eligible question")
    macro = aggregate_macro(tuple(question_metrics.values()))

    safe_environment = dict(environment or {})
    if set(safe_environment) - _SAFE_ENVIRONMENT_FIELDS:
        raise ValueError(
            "environment metadata contains an unapproved or secret field"
        )
    stages: dict[str, dict[str, float | int]] = {}
    for name, observations in sorted(latency_ms.items()):
        if not name or any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
            for value in observations
        ):
            raise ValueError(
                "latency observations must be finite nonnegative values"
            )
        ordered = sorted(float(value) for value in observations)
        stages[name] = {
            "repetitions": len(ordered),
            "median_ms": statistics.median(ordered) if ordered else 0.0,
            "p95_ms": _percentile95(ordered) if ordered else 0.0,
            "max_ms": max(ordered) if ordered else 0.0,
        }

    payload: dict[str, Any] = {
        "report_version": "phase-d-results-v1",
        "dataset": {
            "version": dataset_version,
            "sha256": dataset_sha256,
            "cohort": cohort,
            "partition_sha256": partition_sha256,
        },
        "corpus": {"version": corpus_version, "sha256": corpus_sha256},
        "retrieval": {"arm": arm, "config_sha256": config_sha256},
        "population": {
            "question_count": macro.question_count,
            "positive_question_count": macro.positive_question_count,
            "insufficient_question_count": macro.insufficient_question_count,
            "positive_metric_denominator_questions": (
                macro.positive_question_count
            ),
        },
        "macro_by_question": {
            "recall_at_k": _stringify_cutoffs(macro.recall_at_k),
            "evidence_hit_at_k": _stringify_cutoffs(macro.evidence_hit_at_k),
            "mrr_at_k": _stringify_cutoffs(macro.mrr_at_k),
        },
        "per_question": {
            question_id: _question_metric_dict(metrics)
            for question_id, metrics in sorted(question_metrics.items())
        },
        "latency": stages,
        "environment": safe_environment,
    }
    return EvaluationReport(payload)


def _question_metric_dict(metrics: QuestionMetrics) -> dict[str, Any]:
    return {
        "expected_insufficient_evidence": (
            metrics.expected_insufficient_evidence
        ),
        "gold_unit_count": metrics.gold_unit_count,
        "positive_metric_eligible": metrics.positive_metric_eligible,
        "recall_at_k": _stringify_cutoffs(metrics.recall_at_k),
        "evidence_hit_at_k": _stringify_cutoffs(metrics.evidence_hit_at_k),
        "mrr_at_k": _stringify_cutoffs(metrics.mrr_at_k),
    }


def _stringify_cutoffs(
    values: Mapping[int, float | None],
) -> dict[str, float | None]:
    return {str(cutoff): values[cutoff] for cutoff in sorted(values)}


def _percentile95(values: Sequence[float]) -> float:
    index = max(0, math.ceil(0.95 * len(values)) - 1)
    return values[index]
