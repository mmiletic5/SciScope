"""Importer compatibility checks layered on the delivery 0.3.0 validator."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from sciscope.delivery.validate import PackageReports, validate_package
from sciscope.ingestion.contract import ImportRequest
from sciscope.ingestion.errors import ImportErrorCode, SnapshotImportError

Record = Mapping[str, object]


@dataclass(frozen=True, slots=True)
class ValidatedSnapshot:
    """Immutable, fully checked source snapshot used by the transaction."""

    delivery_digest: str
    delivery_manifest: Record
    embedding_manifest: Record
    papers: tuple[Record, ...]
    sections: tuple[Record, ...]
    chunks: tuple[Record, ...]
    entries: tuple[Record, ...]
    dimensions: int


def validate_snapshot(request: ImportRequest) -> ValidatedSnapshot:
    """Validate all source bytes and importer-specific invariants before writes.

    Args:
        request: Delivery files and matching source reports.

    Returns:
        A snapshot whose records preserve the delivered field values.

    Raises:
        SnapshotImportError: If the delivery is invalid or incompatible.
    """
    outcome = validate_package(
        request.package_dir,
        PackageReports(
            request.parse_report, request.chunk_report, request.embedding_report
        ),
    )
    loaded = outcome.loaded
    delivery = _mapping(loaded.manifests.get("delivery_manifest.json"))
    embedding = _mapping(loaded.manifests.get("embedding_manifest.json"))
    if (
        delivery.get("schema_version") != "0.3.0"
        or delivery.get("contract_version") != "0.3.0"
    ):
        raise SnapshotImportError(ImportErrorCode.DELIVERY_INCOMPATIBLE)
    if embedding.get("status") != "complete":
        raise SnapshotImportError(ImportErrorCode.DELIVERY_INVALID)
    embedding_set = _mapping(delivery.get("embedding_set"))
    if any(
        (
            embedding.get("provider") != "openai",
            embedding.get("model") != "text-embedding-3-small",
            embedding.get("requested_dimensions") != 1536,
            embedding.get("returned_dimensions") != 1536,
            embedding.get("vectors_dtype") != "float32-le",
            embedding.get("passage_prefix") != "",
            embedding.get("query_prefix") != "",
            embedding_set.get("provider") != "openai",
            embedding_set.get("model") != "text-embedding-3-small",
            embedding_set.get("dimensions") != 1536,
            embedding_set.get("dtype") != "float32-le",
            embedding_set.get("passage_prefix") != "",
            embedding_set.get("query_prefix") != "",
        )
    ):
        raise SnapshotImportError(
            ImportErrorCode.EMBEDDING_CONFIGURATION_MISMATCH
        )
    if outcome.findings:
        raise SnapshotImportError(ImportErrorCode.DELIVERY_INVALID)

    records = {
        name: tuple(_mapping(record) for record in loaded.records[name])
        for name in ("papers.jsonl", "sections.jsonl", "chunks.jsonl")
    }
    entries_value = embedding.get("entries")
    if not isinstance(entries_value, list):
        raise SnapshotImportError(ImportErrorCode.DELIVERY_INVALID)
    entries = tuple(_mapping(entry) for entry in entries_value)
    chunk_ids = {record["chunk_id"] for record in records["chunks.jsonl"]}
    entry_ids = [entry.get("chunk_id") for entry in entries]
    if len(entry_ids) != len(set(entry_ids)) or set(entry_ids) != chunk_ids:
        raise SnapshotImportError(ImportErrorCode.DELIVERY_INVALID)

    raw_manifest = loaded.raw_files.get("delivery_manifest.json")
    if raw_manifest is None:
        raise SnapshotImportError(ImportErrorCode.DELIVERY_INVALID)
    return ValidatedSnapshot(
        "sha256:" + hashlib.sha256(raw_manifest).hexdigest(),
        delivery,
        embedding,
        records["papers.jsonl"],
        records["sections.jsonl"],
        records["chunks.jsonl"],
        entries,
        1536,
    )


def _mapping(value: object) -> Record:
    """Return a validated mapping or raise one sanitized delivery code."""
    if not isinstance(value, Mapping):
        raise SnapshotImportError(ImportErrorCode.DELIVERY_INVALID)
    return cast(Record, value)
