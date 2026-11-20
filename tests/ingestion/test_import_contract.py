"""Tests for the stable importer request and result contract."""

from pathlib import Path

import pytest

from sciscope.ingestion.contract import ImportMode, ImportRequest, ImportResult
from sciscope.ingestion.errors import ImportErrorCode, SnapshotImportError
from sciscope.ingestion.service import _determine_operation


def test_request_and_result_are_typed_immutable_contracts() -> None:
    """Requests and result records are immutable and correctly typed."""
    request = ImportRequest(
        Path("package"),
        Path("parse"),
        Path("chunk"),
        Path("embedding"),
        ImportMode.INITIALIZE,
    )
    result = ImportResult(1, "sha256:" + "a" * 64, "imported", None, 1, 2, 3, 3)
    with pytest.raises((AttributeError, TypeError)):
        request.mode = ImportMode.REPLACE  # type: ignore[misc]
    assert result.outcome == "imported"


def test_import_error_exposes_only_stable_code() -> None:
    """Public importer errors expose only their stable code."""
    error = SnapshotImportError(ImportErrorCode.DELIVERY_INVALID)
    assert str(error) == "DELIVERY_INVALID"
    assert error.code is ImportErrorCode.DELIVERY_INVALID
    assert "path" not in repr(error).lower()


@pytest.mark.parametrize(
    ("mode", "active", "expected", "outcome"),
    [
        (ImportMode.INITIALIZE, None, None, "initialize"),
        (ImportMode.REPLACE, "same", "stale", "unchanged"),
        (ImportMode.REPLACE, "old", "old", "replace"),
    ],
)
def test_operation_state_table(
    mode: ImportMode,
    active: str | None,
    expected: str | None,
    outcome: str,
) -> None:
    """The pure transition logic matches the approved state table."""
    incoming = "same" if active == "same" else "new"
    assert _determine_operation(mode, incoming, expected, active) == outcome


@pytest.mark.parametrize(
    ("mode", "incoming", "expected", "active", "code"),
    [
        (
            ImportMode.INITIALIZE,
            "new",
            None,
            "old",
            ImportErrorCode.REPLACEMENT_REQUIRED,
        ),
        (
            ImportMode.REPLACE,
            "new",
            "stale",
            "old",
            ImportErrorCode.ACTIVE_CORPUS_CONFLICT,
        ),
        (
            ImportMode.REPLACE,
            "new",
            None,
            None,
            ImportErrorCode.ACTIVE_CORPUS_CONFLICT,
        ),
    ],
)
def test_invalid_state_transition_has_stable_code(
    mode: ImportMode,
    incoming: str,
    expected: str | None,
    active: str | None,
    code: ImportErrorCode,
) -> None:
    """Initialize and stale compare-and-swap errors remain stable."""
    with pytest.raises(SnapshotImportError) as caught:
        _determine_operation(mode, incoming, expected, active)
    assert caught.value.code is code


"""Tests for the stable importer request and result contract."""
