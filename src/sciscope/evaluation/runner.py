"""Fail-closed approval checks for later protected Phase D execution."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, cast


class EvaluationAuthorizationError(ValueError):
    """Sanitized error for a missing or mismatched explicit approval gate."""


def require_evaluation_authorizations(
    preflight_authorization_path: Path,
    retrieval_authorization_path: Path,
) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    """Require separate records for protected preflight and retrieval.

    These records document explicit owner decisions; their existence does not
    create authorization. The operator must preserve the source approval in
    the evidence ledger and ensure each record reflects that actual decision.

    Args:
        preflight_authorization_path: Record allowing only protected text/vector
            readiness reads for one frozen cohort.
        retrieval_authorization_path: Separate record allowing retrieval for
            that same frozen cohort after preflight passes.

    Returns:
        The validated, matching approval records.

    Raises:
        EvaluationAuthorizationError: If a record is absent, malformed, has
            the wrong purpose, or names a different population.
    """
    if (
        preflight_authorization_path.resolve()
        == retrieval_authorization_path.resolve()
    ):
        raise EvaluationAuthorizationError(
            "distinct authorization records are required"
        )
    if not retrieval_authorization_path.is_file():
        raise EvaluationAuthorizationError("retrieval authorization is missing")
    retrieval = _read_authorization(retrieval_authorization_path)
    if retrieval.get("purpose") != "held-out-retrieval":
        raise EvaluationAuthorizationError("retrieval authorization is missing")
    _validate_owner_approval(retrieval)
    _validate_population(retrieval)
    preflight = require_preflight_authorization(
        preflight_authorization_path,
        expected_cohort=cast(str, retrieval["cohort"]),
    )
    binding_fields = (
        "cohort",
        "dataset_version",
        "partition_sha256",
    )
    if any(
        not isinstance(preflight.get(field), str)
        or not preflight.get(field)
        or preflight.get(field) != retrieval.get(field)
        for field in binding_fields
    ):
        raise EvaluationAuthorizationError(
            "preflight and retrieval cohort mismatch"
        )
    return preflight, retrieval


def require_preflight_authorization(
    preflight_authorization_path: Path,
    *,
    expected_cohort: str,
) -> Mapping[str, Any]:
    """Validate the standalone T005 approval for one protected cohort.

    This gate authorizes only a read-only readiness preflight. It cannot
    authorize retrieval; T006 must call
    :func:`require_evaluation_authorizations` with a second approval.

    Args:
        preflight_authorization_path: Record documenting the explicit T005
            approval.
        expected_cohort: Cohort name supplied by the operator to bind this
            check to the intended protected population.

    Returns:
        The validated preflight approval record.

    Raises:
        EvaluationAuthorizationError: If the record is missing, malformed,
            forged, has the wrong purpose, or names another cohort.
    """
    preflight = _read_authorization(preflight_authorization_path)
    if preflight.get("purpose") != "protected-preflight":
        raise EvaluationAuthorizationError("preflight authorization is missing")
    _validate_owner_approval(preflight)
    _validate_population(preflight)
    cohort = preflight["cohort"]
    if not isinstance(expected_cohort, str) or not expected_cohort.strip():
        raise EvaluationAuthorizationError("expected cohort is invalid")
    if cohort != expected_cohort:
        raise EvaluationAuthorizationError("preflight cohort mismatch")
    return preflight


def _validate_population(record: Mapping[str, Any]) -> None:
    """Require a complete, structurally valid dataset/partition identity."""
    for field in ("cohort", "dataset_version"):
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            raise EvaluationAuthorizationError(
                "authorization population identity is invalid"
            )
    partition_digest = record.get("partition_sha256")
    if (
        not isinstance(partition_digest, str)
        or re.fullmatch(r"[0-9a-f]{64}", partition_digest) is None
    ):
        raise EvaluationAuthorizationError(
            "authorization partition identity is invalid"
        )


def _validate_owner_approval(record: Mapping[str, Any]) -> None:
    if (
        record.get("approval_status") != "explicitly-approved"
        or record.get("authorizer") != "Person 2 user"
    ):
        raise EvaluationAuthorizationError("explicit owner approval is missing")
    digest = record.get("approval_evidence_sha256")
    if (
        not isinstance(digest, str)
        or re.fullmatch(r"[0-9a-f]{64}", digest) is None
    ):
        raise EvaluationAuthorizationError(
            "approval evidence digest is invalid"
        )
    approved_at = record.get("approved_at_utc")
    if not isinstance(approved_at, str):
        raise EvaluationAuthorizationError("approval timestamp is missing")
    try:
        parsed = datetime.fromisoformat(approved_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise EvaluationAuthorizationError(
            "approval timestamp is invalid"
        ) from error
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise EvaluationAuthorizationError("approval timestamp must be UTC")


def _read_authorization(path: Path) -> Mapping[str, Any]:
    try:
        if not path.is_file():
            raise EvaluationAuthorizationError(
                "authorization record is unavailable"
            )
        raw = path.read_bytes()
        if len(raw) > 8192:
            raise EvaluationAuthorizationError(
                "authorization record is oversized"
            )
        value = json.loads(raw.decode("utf-8"))
    except EvaluationAuthorizationError:
        raise
    except (OSError, UnicodeError, ValueError) as error:
        raise EvaluationAuthorizationError(
            "authorization record is unavailable"
        ) from error
    if not isinstance(value, dict):
        raise EvaluationAuthorizationError("authorization record is malformed")
    return value
