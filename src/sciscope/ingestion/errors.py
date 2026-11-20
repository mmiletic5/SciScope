"""Stable, sanitized importer errors."""

from __future__ import annotations

from enum import StrEnum


class ImportErrorCode(StrEnum):
    """Public importer failure codes from importer.v1."""

    DELIVERY_INVALID = "DELIVERY_INVALID"
    DELIVERY_INCOMPATIBLE = "DELIVERY_INCOMPATIBLE"
    EMBEDDING_CONFIGURATION_MISMATCH = "EMBEDDING_CONFIGURATION_MISMATCH"
    REPLACEMENT_REQUIRED = "REPLACEMENT_REQUIRED"
    ACTIVE_CORPUS_CONFLICT = "ACTIVE_CORPUS_CONFLICT"
    IMPORT_IN_PROGRESS = "IMPORT_IN_PROGRESS"
    DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
    IMPORT_TRANSACTION_FAILED = "IMPORT_TRANSACTION_FAILED"
    IMPORT_VERIFICATION_FAILED = "IMPORT_VERIFICATION_FAILED"


class SnapshotImportError(RuntimeError):
    """Importer exception whose public string contains only a stable code."""

    def __init__(self, code: ImportErrorCode) -> None:
        """Create an error without retaining source paths or exception text."""
        self.code = code
        super().__init__(code.value)
