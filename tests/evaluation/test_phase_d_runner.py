"""Authorization and dry-run protections for the Phase D runner."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from sciscope.evaluation.runner import (
    EvaluationAuthorizationError,
    require_evaluation_authorizations,
    require_preflight_authorization,
)

_PARTITION_SHA256 = "a" * 64
_APPROVAL_SHA256 = "b" * 64


def _authorization(record_purpose: str, **overrides: str) -> str:
    """Build a synthetic authorization record without protected data."""
    fields = {
        "purpose": record_purpose,
        "approval_status": "explicitly-approved",
        "authorizer": "Person 2 user",
        "approval_evidence_sha256": _APPROVAL_SHA256,
        "approved_at_utc": "2026-11-20T00:00:00Z",
        "cohort": "v1-held-out",
        "dataset_version": "golden-v1",
        "partition_sha256": _PARTITION_SHA256,
    }
    fields.update(overrides)
    return json.dumps(fields)


def _write_authorization(
    path: Path, record_purpose: str, **overrides: str
) -> None:
    path.write_text(
        _authorization(record_purpose, **overrides), encoding="utf-8"
    )


def test_preflight_authorization_is_standalone_and_cohort_bound(
    tmp_path: Path,
) -> None:
    """T005 validates one owner approval without requiring T006 approval."""
    preflight = tmp_path / "preflight.json"
    _write_authorization(preflight, "protected-preflight")

    approved = require_preflight_authorization(
        preflight, expected_cohort="v1-held-out"
    )

    assert approved["cohort"] == "v1-held-out"
    assert not (tmp_path / "retrieval.json").exists()


@pytest.mark.parametrize(
    "contents",
    [
        None,
        "{malformed",
        "[]",
        _authorization("held-out-retrieval"),
        _authorization("protected-preflight", approval_status="pending"),
        _authorization("protected-preflight", authorizer="unknown"),
        _authorization("protected-preflight", approval_evidence_sha256="bad"),
        _authorization("protected-preflight", approved_at_utc="not-a-date"),
        _authorization(
            "protected-preflight", approved_at_utc="2026-11-20T00:00:00"
        ),
        _authorization(
            "protected-preflight", approved_at_utc="2026-11-20T01:00:00+01:00"
        ),
        _authorization("protected-preflight", cohort="v0-held-out"),
        _authorization("protected-preflight", dataset_version=""),
        _authorization("protected-preflight", partition_sha256="a"),
    ],
)
def test_preflight_authorization_fails_closed(
    tmp_path: Path, contents: str | None
) -> None:
    """Missing, malformed, forged, and mismatched T005 records are rejected."""
    preflight = tmp_path / "preflight.json"
    if contents is not None:
        preflight.write_text(contents, encoding="utf-8")

    with pytest.raises(EvaluationAuthorizationError):
        require_preflight_authorization(
            preflight, expected_cohort="v1-held-out"
        )


def test_preflight_errors_are_sanitized(tmp_path: Path) -> None:
    """Validation errors never include paths or record contents."""
    preflight = tmp_path / "preflight.json"
    preflight.write_text("private question text", encoding="utf-8")

    with pytest.raises(EvaluationAuthorizationError) as error:
        require_preflight_authorization(
            preflight, expected_cohort="v1-held-out"
        )

    assert "private question text" not in str(error.value)
    assert str(preflight) not in str(error.value)


def test_preflight_requires_explicit_expected_cohort(tmp_path: Path) -> None:
    """A valid record cannot be checked without an operator-named cohort."""
    preflight = tmp_path / "preflight.json"
    _write_authorization(preflight, "protected-preflight")

    with pytest.raises(EvaluationAuthorizationError, match="expected cohort"):
        require_preflight_authorization(preflight, expected_cohort=" ")


def test_protected_evaluation_requires_two_distinct_authorizations(
    tmp_path: Path,
) -> None:
    """A T005 approval alone cannot authorize retrieval execution."""
    preflight = tmp_path / "preflight.json"
    retrieval = tmp_path / "retrieval.json"
    _write_authorization(preflight, "protected-preflight")
    with pytest.raises(EvaluationAuthorizationError, match="retrieval"):
        require_evaluation_authorizations(preflight, retrieval)

    _write_authorization(retrieval, "held-out-retrieval")
    require_evaluation_authorizations(preflight, retrieval)


def test_authorizations_must_bind_same_frozen_population(
    tmp_path: Path,
) -> None:
    """Mismatched versions or partitions cannot be joined into one run gate."""
    preflight = tmp_path / "preflight.json"
    retrieval = tmp_path / "retrieval.json"
    _write_authorization(preflight, "protected-preflight")
    _write_authorization(
        retrieval,
        "held-out-retrieval",
        cohort="v0-held-out",
        dataset_version="golden-v0",
        partition_sha256="c" * 64,
    )

    with pytest.raises(EvaluationAuthorizationError, match="match"):
        require_evaluation_authorizations(preflight, retrieval)


@pytest.mark.parametrize(
    "retrieval_overrides",
    [
        {"purpose": "protected-preflight"},
        {"approval_status": "pending"},
        {"authorizer": "forged"},
        {"approval_evidence_sha256": "invalid"},
        {"cohort": "v0-held-out"},
        {"dataset_version": "golden-v0"},
        {"partition_sha256": "c" * 64},
    ],
)
def test_retrieval_requires_separate_valid_matching_approval(
    tmp_path: Path, retrieval_overrides: dict[str, str]
) -> None:
    """T006 rejects missing, forged, wrong-purpose, or mismatched approval."""
    preflight = tmp_path / "preflight.json"
    retrieval = tmp_path / "retrieval.json"
    _write_authorization(preflight, "protected-preflight")
    _write_authorization(retrieval, "held-out-retrieval", **retrieval_overrides)

    with pytest.raises(EvaluationAuthorizationError):
        require_evaluation_authorizations(preflight, retrieval)


def test_retrieval_rejects_same_record_for_both_gates(tmp_path: Path) -> None:
    """One T005 record cannot be reused as the separate T006 approval."""
    preflight = tmp_path / "preflight.json"
    _write_authorization(preflight, "protected-preflight")

    with pytest.raises(EvaluationAuthorizationError, match="distinct"):
        require_evaluation_authorizations(preflight, preflight)


def test_retrieval_rejects_malformed_and_missing_records(
    tmp_path: Path,
) -> None:
    """T006 fails closed when either approval cannot be parsed."""
    preflight = tmp_path / "preflight.json"
    retrieval = tmp_path / "retrieval.json"
    _write_authorization(preflight, "protected-preflight")

    with pytest.raises(EvaluationAuthorizationError):
        require_evaluation_authorizations(preflight, retrieval)

    retrieval.write_text("{broken", encoding="utf-8")
    with pytest.raises(EvaluationAuthorizationError):
        require_evaluation_authorizations(preflight, retrieval)


def test_cli_accepts_preflight_without_retrieval_authorization(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The T005 CLI mode needs only the named cohort's approval record."""
    from scripts.phase_d_retrieval_evaluation import main

    preflight = tmp_path / "preflight.json"
    _write_authorization(preflight, "protected-preflight")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "phase_d_retrieval_evaluation.py",
            "--check-preflight-authorization",
            "--preflight-authorization",
            str(preflight),
            "--cohort",
            "v1-held-out",
        ],
    )

    assert main() == 0
    assert "no data was accessed" in capsys.readouterr().out


def test_cli_retrieval_mode_still_requires_both_approvals(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """T006 CLI accepts only the separate matching two-record gate."""
    from scripts.phase_d_retrieval_evaluation import main

    preflight = tmp_path / "preflight.json"
    retrieval = tmp_path / "retrieval.json"
    _write_authorization(preflight, "protected-preflight")
    _write_authorization(retrieval, "held-out-retrieval")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "phase_d_retrieval_evaluation.py",
            "--check-retrieval-authorizations",
            "--preflight-authorization",
            str(preflight),
            "--retrieval-authorization",
            str(retrieval),
        ],
    )

    assert main() == 0
    assert "Both authorization records" in capsys.readouterr().out


def test_cli_retrieval_alias_fails_without_second_approval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The legacy retrieval check cannot convert T005 into T006 approval."""
    from scripts.phase_d_retrieval_evaluation import main

    preflight = tmp_path / "preflight.json"
    _write_authorization(preflight, "protected-preflight")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "phase_d_retrieval_evaluation.py",
            "--check-authorizations",
            "--preflight-authorization",
            str(preflight),
            "--retrieval-authorization",
            str(tmp_path / "missing-retrieval.json"),
        ],
    )

    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2


@pytest.mark.parametrize(
    "extra_arguments",
    [
        [],
        ["--retrieval-authorization", "retrieval.json"],
        ["--cohort", "v0-held-out"],
    ],
)
def test_cli_preflight_mode_rejects_missing_or_premature_gate_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    extra_arguments: list[str],
) -> None:
    """T005 mode fails closed on missing, premature, or mismatched inputs."""
    from scripts.phase_d_retrieval_evaluation import main

    preflight = tmp_path / "preflight.json"
    _write_authorization(preflight, "protected-preflight")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "phase_d_retrieval_evaluation.py",
            "--check-preflight-authorization",
            "--preflight-authorization",
            str(preflight),
            *extra_arguments,
        ],
    )

    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2
