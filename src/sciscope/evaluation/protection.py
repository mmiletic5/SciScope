"""Procedural safeguards for protected Golden v1 evaluation artifacts."""

from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import TypedDict

_PROTECTED_RELATIVE_ROOT = Path("evals/protected/golden_v1_review")
_FIXED_V1_SLOT_PARTITIONS = {
    "Q1": "development",
    "Q2": "held_out",
    "Q3": "held_out",
    "Q4": "development",
    "Q5": "held_out",
    "Q6": "development",
    "Q7": "held_out",
    "Q8": "held_out",
    "Q9": "held_out",
}
_FIXED_V1_SLOT_CATEGORIES = {
    "Q1": "insufficient_evidence",
    "Q2": "insufficient_evidence",
    "Q3": "insufficient_evidence",
    "Q4": "multi_paper_comparison",
    "Q5": "multi_paper_comparison",
    "Q6": "research_gap",
    "Q7": "research_gap",
    "Q8": "single_paper_factual",
    "Q9": "multi_paper_comparison",
}
_FIXED_V1_SLOT_FUNCTIONALITIES = {
    "Q1": {"research_question_explorer"},
    "Q2": {"evidence_comparison"},
    "Q3": {"research_gap_hypothesis_assistant"},
    "Q4": {
        "evidence_comparison",
        "conflicting_evidence_finder",
        "research_question_explorer",
    },
    "Q5": {"evidence_comparison", "conflicting_evidence_finder"},
    "Q6": {
        "research_gap_hypothesis_assistant",
        "research_question_explorer",
    },
    "Q7": {"research_gap_hypothesis_assistant"},
    "Q8": {"research_question_explorer"},
    "Q9": {"evidence_comparison"},
}
_MINIMUM_LEAK_CHECK_CHARS = 24
_IGNORED_SCAN_COMPONENTS = {".git", "__pycache__", ".pytest_cache"}
_NEVER_SCAN_FILENAMES = {"golden_questions.v0.json"}
_TEXT_SUFFIXES = {
    ".cfg",
    ".csv",
    ".ini",
    ".json",
    ".log",
    ".md",
    ".ps1",
    ".py",
    ".toml",
    ".tsv",
    ".txt",
    ".yaml",
    ".yml",
}


class ProtectedDataError(ValueError):
    """Sanitized failure to enforce the protected evaluation workflow."""


class ProtectedArtifactRecord(TypedDict):
    """Content-free integrity metadata for one protected artifact."""

    path: str
    bytes: int
    sha256: str


def validate_v1_slot_partitions(slot_partitions: Mapping[str, str]) -> None:
    """Require the exact pre-registered Q1–Q9 development/held-out split."""
    if dict(slot_partitions) != _FIXED_V1_SLOT_PARTITIONS:
        raise ProtectedDataError(
            "Golden v1 fixed partition assignment mismatch"
        )


def validate_v1_slot_categories(slot_categories: Mapping[str, str]) -> None:
    """Require the approved category assignment for every fixed slot."""
    if dict(slot_categories) != _FIXED_V1_SLOT_CATEGORIES:
        raise ProtectedDataError("Golden v1 fixed category assignment mismatch")


def validate_v1_slot_functionalities(
    slot_functionalities: Mapping[str, Iterable[str]],
) -> None:
    """Require the pre-registered functionality tags for every fixed slot."""
    normalized = {
        slot: set(functionalities)
        for slot, functionalities in slot_functionalities.items()
    }
    if normalized != _FIXED_V1_SLOT_FUNCTIONALITIES:
        raise ProtectedDataError(
            "Golden v1 fixed functionality assignment mismatch"
        )


def validate_protected_artifact_paths(
    repository_root: Path, artifact_paths: Sequence[Path]
) -> tuple[Path, ...]:
    """Require existing artifacts under the exact ignored protected root.

    The Git ignore rule is a workflow safeguard, not an operating-system ACL.
    This function deliberately does not read artifact contents.
    """
    root = repository_root.resolve(strict=True)
    protected_root = (root / _PROTECTED_RELATIVE_ROOT).resolve(strict=True)
    if not artifact_paths:
        raise ProtectedDataError("protected artifact list is empty")

    validated: list[Path] = []
    for artifact_path in artifact_paths:
        lexical = (
            artifact_path
            if artifact_path.is_absolute()
            else root / artifact_path
        )
        if _contains_symlink(root, lexical):
            raise ProtectedDataError("protected artifact path contains a link")
        try:
            resolved = lexical.resolve(strict=True)
            relative = resolved.relative_to(protected_root)
        except (OSError, ValueError) as error:
            raise ProtectedDataError(
                "artifact is outside the protected ignored root"
            ) from error
        if not relative.parts or not resolved.is_file():
            raise ProtectedDataError("protected artifact must be a file")

        repository_relative = resolved.relative_to(root).as_posix()
        ignored = subprocess.run(
            ["git", "check-ignore", "--quiet", "--", repository_relative],
            cwd=root,
            check=False,
            capture_output=True,
        )
        if ignored.returncode != 0:
            raise ProtectedDataError("protected artifact is not Git-ignored")
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", repository_relative],
            cwd=root,
            check=False,
            capture_output=True,
        )
        if tracked.returncode == 0:
            raise ProtectedDataError("protected artifact is Git-tracked")
        validated.append(resolved)
    return tuple(validated)


def validate_protected_destination(
    repository_root: Path, destination: Path
) -> Path:
    """Require a new destination under the ignored root before writing it."""
    root = repository_root.resolve(strict=True)
    lexical = destination if destination.is_absolute() else root / destination
    if _contains_symlink(root, lexical):
        raise ProtectedDataError("protected destination path contains a link")
    try:
        resolved = lexical.resolve(strict=False)
        relative = resolved.relative_to(root)
    except (OSError, ValueError) as error:
        raise ProtectedDataError(
            "destination is outside the protected ignored root"
        ) from error
    if not relative.parts or not relative.is_relative_to(
        _PROTECTED_RELATIVE_ROOT
    ):
        raise ProtectedDataError("destination is outside protected storage")
    if resolved.exists():
        raise ProtectedDataError("protected destination already exists")
    ignored = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", relative.as_posix()],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if ignored.returncode != 0:
        raise ProtectedDataError("protected destination is not Git-ignored")
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative.as_posix()],
        cwd=root,
        check=False,
        capture_output=True,
    )
    if tracked.returncode == 0:
        raise ProtectedDataError("protected destination is Git-tracked")
    return resolved


def write_protected_file(
    repository_root: Path,
    destination: Path,
    payload: bytes,
    *,
    replace_existing: bool = False,
) -> Path:
    """Atomically write bytes only under Git-ignored protected storage."""
    lexical = (
        destination
        if destination.is_absolute()
        else repository_root / destination
    )
    if lexical.exists():
        validate_protected_artifact_paths(repository_root, (lexical,))
        if not replace_existing:
            raise ProtectedDataError("protected destination already exists")
    else:
        validate_protected_destination(repository_root, lexical)
    parent = lexical.parent
    parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=".protected-write-",
            suffix=".tmp",
            dir=parent,
            delete=False,
        ) as temporary:
            temporary.write(payload)
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, lexical)
        temporary_path = None
    except OSError as error:
        raise ProtectedDataError("protected artifact write failed") from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    validate_protected_artifact_paths(repository_root, (lexical,))
    return lexical


def protected_artifact_manifest(
    repository_root: Path, artifact_paths: Sequence[Path]
) -> list[ProtectedArtifactRecord]:
    """Hash protected artifacts without returning or logging their contents."""
    root = repository_root.resolve(strict=True)
    validated = validate_protected_artifact_paths(root, artifact_paths)
    records: list[ProtectedArtifactRecord] = []
    for path in validated:
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path.read_bytes()),
            }
        )
    return records


def audit_no_text_leak(
    protected_text_values: Iterable[str], scan_paths: Sequence[Path]
) -> int:
    """Fail if protected prose appears in ordinary fixtures, logs, or docs.

    Content from Golden v0 is explicitly excluded from scanning. Callers must
    pass only ordinary development paths; the review packet and source corpus
    are not scan targets. Errors never include the matching protected text.

    Returns:
        Number of text files scanned.
    """
    needles = {
        _normalize_text(value)
        for value in protected_text_values
        if isinstance(value, str)
        and len(_normalize_text(value)) >= _MINIMUM_LEAK_CHECK_CHARS
    }
    needles.discard("")
    if not needles:
        raise ProtectedDataError("no substantive protected text to audit")

    scanned = 0
    for scan_path in scan_paths:
        if not scan_path.exists():
            raise ProtectedDataError("required leak-audit path is unavailable")
        paths = (scan_path,) if scan_path.is_file() else scan_path.rglob("*")
        for path in paths:
            if path.is_symlink():
                raise ProtectedDataError(
                    "leak-audit path contains an unchecked link"
                )
            if not path.is_file():
                continue
            if any(part in _IGNORED_SCAN_COMPONENTS for part in path.parts):
                continue
            if path.name in _NEVER_SCAN_FILENAMES:
                continue
            if path.suffix.lower() not in _TEXT_SUFFIXES:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as error:
                raise ProtectedDataError(
                    "required leak-audit file could not be read"
                ) from error
            normalized = _normalize_text(content)
            scanned += 1
            if any(needle in normalized for needle in needles):
                raise ProtectedDataError(
                    "protected content was found outside protected storage"
                )
    return scanned


def protected_text_values(value: object) -> tuple[str, ...]:
    """Collect substantive string leaves for a content-free leak audit call."""
    values: list[str] = []

    def visit(item: object) -> None:
        if isinstance(item, str):
            values.append(item)
        elif isinstance(item, Mapping):
            for key, nested in item.items():
                if isinstance(key, str):
                    values.append(key)
                visit(nested)
        elif isinstance(item, Sequence) and not isinstance(
            item, (str, bytes, bytearray)
        ):
            for nested in item:
                visit(nested)

    visit(value)
    return tuple(values)


def protected_evaluation_text_values(
    dataset: Mapping[str, object], sidecar: Mapping[str, object]
) -> tuple[str, ...]:
    """Return candidate prose and evidence text for leak auditing.

    Stable identifiers, schema keys, DOI strings, enum values, and corpus
    version metadata are excluded because their ordinary appearance is not
    question-text leakage. Free-text annotations and expected output prose
    remain included.
    """
    values: list[str] = []
    questions = dataset.get("questions", [])
    if not isinstance(questions, Sequence) or isinstance(
        questions, (str, bytes, bytearray)
    ):
        questions = ()
    for question in questions:
        if not isinstance(question, Mapping):
            continue
        for field in ("question", "expected_findings", "notes"):
            text = question.get(field)
            if isinstance(text, str):
                values.append(text)

    excluded_fields = {
        "question_id",
        "slot",
        "partition",
        "doi",
        "chunk_id",
        "source_locator",
        "source_xml_sha256",
        "source_url",
        "evidence_reference_id",
        "relevance_label",
        "claim_ids",
        "claim_id",
        "evidence_reference_ids",
        "supporting_evidence_ids",
        "primary_functionality",
        "functionalities",
        "answerability",
        "role",
        "expected_disposition",
        "status",
    }

    def collect_prose(item: object, field: str = "") -> None:
        if isinstance(item, str):
            if field not in excluded_fields:
                values.append(item)
        elif isinstance(item, Mapping):
            for key, nested in item.items():
                if isinstance(key, str):
                    collect_prose(nested, key)
        elif isinstance(item, Sequence) and not isinstance(
            item, (str, bytes, bytearray)
        ):
            for nested in item:
                collect_prose(nested, field)

    annotations = sidecar.get("annotations", [])
    if not isinstance(annotations, Sequence) or isinstance(
        annotations, (str, bytes, bytearray)
    ):
        annotations = ()
    for annotation in annotations:
        if not isinstance(annotation, Mapping):
            continue
        references = annotation.get("evidence_references", [])
        if not isinstance(references, Sequence) or isinstance(
            references, (str, bytes, bytearray)
        ):
            references = ()
        for reference in references:
            if isinstance(reference, Mapping):
                for field in (
                    "source_passage",
                    "quotation",
                    "relevance_rationale",
                ):
                    text = reference.get(field)
                    if isinstance(text, str):
                        values.append(text)
        collect_prose(annotation.get("expected_output", {}))
    return tuple(values)


def _contains_symlink(root: Path, target: Path) -> bool:
    try:
        relative = target.absolute().relative_to(root)
    except ValueError:
        return True
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(normalized.split())


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()
