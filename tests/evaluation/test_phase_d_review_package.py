"""Safe, deterministic review-archive tests with synthetic payloads only."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from sciscope.evaluation.review_package import (
    ReviewPackageError,
    build_review_package,
)


def _members() -> dict[str, bytes]:
    names = (
        "README.md",
        "golden_questions.v1.candidates.json",
        "golden_functionality_annotations.v1.json",
        "golden_v1_curation_manifest.json",
        "source_passages.v1.json",
        "corpus_scope_search_report.json",
        "validation_report.json",
        "curation_prompt_record.md",
        "phase_d_baseline_freeze.json",
    )
    return {name: b'{"synthetic":"private fixture"}' for name in names}


def test_review_package_has_only_allowlisted_members_and_hashes(
    tmp_path: Path,
) -> None:
    """Archive membership is exact and the index contains only digests."""
    target = tmp_path / "review.zip"
    payloads = _members()

    archive_sha = build_review_package(target, payloads)

    with ZipFile(target) as archive:
        assert set(archive.namelist()) == set(payloads) | {
            "packet_manifest.json"
        }
        manifest = json.loads(archive.read("packet_manifest.json"))
    assert manifest["artifact_type"] == "golden-v1-chatgpt-review-packet"
    assert (
        manifest["members"]["README.md"]["sha256"]
        == hashlib.sha256(payloads["README.md"]).hexdigest()
    )
    assert "synthetic" not in json.dumps(manifest)
    assert archive_sha == hashlib.sha256(target.read_bytes()).hexdigest()


def test_review_package_is_byte_reproducible(tmp_path: Path) -> None:
    """Fixed archive metadata yields the same hash for identical inputs."""
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    payloads = _members()

    first_sha = build_review_package(first, payloads)
    second_sha = build_review_package(second, payloads)

    assert first_sha == second_sha


def test_review_package_never_overwrites_existing_artifact(
    tmp_path: Path,
) -> None:
    """A previous packet is preserved rather than silently replaced."""
    target = tmp_path / "existing.zip"
    target.write_bytes(b"pre-existing artifact")

    with pytest.raises(ReviewPackageError, match="destination"):
        build_review_package(target, _members())

    assert target.read_bytes() == b"pre-existing artifact"


def test_review_package_rejects_unallowlisted_files_and_secret_patterns(
    tmp_path: Path,
) -> None:
    """Caches, v0, database URLs, and credentials cannot be packaged."""
    payloads = _members()
    payloads["golden_questions.v0.json"] = b"must not be included"
    with pytest.raises(ReviewPackageError, match="member allowlist"):
        build_review_package(tmp_path / "bad-member.zip", payloads)

    payloads = _members()
    payloads["README.md"] = b"postgresql://user:password@host/database"
    with pytest.raises(ReviewPackageError, match="sensitive pattern"):
        build_review_package(tmp_path / "secret.zip", payloads)
