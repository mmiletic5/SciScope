"""Deterministic allowlisted archive creation for the Golden v1 review gate."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

_ALLOWED_MEMBERS = frozenset(
    {
        "README.md",
        "golden_questions.v1.candidates.json",
        "golden_functionality_annotations.v1.json",
        "golden_v1_curation_manifest.json",
        "source_passages.v1.json",
        "corpus_scope_search_report.json",
        "validation_report.json",
        "curation_prompt_record.md",
        "phase_d_baseline_freeze.json",
    }
)
_PACKET_MANIFEST = "packet_manifest.json"
_SENSITIVE_PATTERNS = (
    re.compile(r"(?i)\bpostgres(?:ql)?://"),
    re.compile(r"(?i)\bDATABASE_URL\b"),
    re.compile(
        r"(?i)\b(?:api[_-]?key|password|secret|access[_-]?token)\s*[:=]"
    ),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
)
_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


class ReviewPackageError(ValueError):
    """Sanitized failure to create an exact, safe review package."""


def build_review_package(
    output_path: Path, member_payloads: Mapping[str, bytes]
) -> str:
    """Write a deterministic zip containing only the approved review files.

    Args:
        output_path: Destination within the Git-ignored protected directory.
        member_payloads: Exact allowlisted names mapped to UTF-8 file bytes.

    Returns:
        SHA-256 of the completed archive.

    Raises:
        ReviewPackageError: If membership is incomplete, unsafe, or contains
            a recognized credential/database-secret pattern.
    """
    if set(member_payloads) != _ALLOWED_MEMBERS:
        raise ReviewPackageError("review package member allowlist mismatch")
    for name, payload in member_payloads.items():
        if (
            not isinstance(name, str)
            or Path(name).name != name
            or "/" in name
            or "\\" in name
            or not isinstance(payload, bytes)
        ):
            raise ReviewPackageError("review package member is unsafe")
        try:
            text = payload.decode("utf-8")
        except UnicodeError as error:
            raise ReviewPackageError(
                "review package members must be UTF-8 text"
            ) from error
        if any(pattern.search(text) for pattern in _SENSITIVE_PATTERNS):
            raise ReviewPackageError(
                "review package contains a sensitive pattern"
            )
    if (
        output_path.suffix.lower() != ".zip"
        or not output_path.parent.is_dir()
        or output_path.exists()
    ):
        raise ReviewPackageError("review package destination is unavailable")

    manifest: dict[str, Any] = {
        "artifact_type": "golden-v1-chatgpt-review-packet",
        "manifest_version": "golden-v1-review-packet-v1",
        "member_count": len(member_payloads),
        "members": {
            name: {
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }
            for name, payload in sorted(member_payloads.items())
        },
        "exclusions": [
            "Golden v0 datasets and questions",
            "database contents or credentials",
            "embedding caches and unrelated files",
            "retrieval evaluation results",
        ],
    }
    packet_manifest = (
        json.dumps(
            manifest,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=".golden-v1-packet-",
            suffix=".tmp",
            dir=output_path.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
        with ZipFile(temporary_path, "w", compression=ZIP_DEFLATED) as archive:
            for name, payload in sorted(member_payloads.items()):
                _write_member(archive, name, payload)
            _write_member(archive, _PACKET_MANIFEST, packet_manifest)
        os.replace(temporary_path, output_path)
        temporary_path = None
    except OSError as error:
        raise ReviewPackageError(
            "review package could not be written"
        ) from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    return hashlib.sha256(output_path.read_bytes()).hexdigest()


def _write_member(archive: ZipFile, name: str, payload: bytes) -> None:
    info = ZipInfo(name, date_time=_ZIP_TIMESTAMP)
    info.compress_type = ZIP_DEFLATED
    info.external_attr = 0o600 << 16
    archive.writestr(info, payload)
