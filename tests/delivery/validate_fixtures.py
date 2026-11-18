"""SYNTHETIC offline helpers for the received-package library tests."""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path
from typing import Any, Never

from package_fixtures import (
    PACKAGE_FILES,
    PackageTree,
    make_tree,
    read_json,
    rows,
    write_json,
    write_rows,
)

from sciscope.chunking.validate import Finding
from sciscope.delivery import package, validate

SAFE_IDS = frozenset(
    (*PACKAGE_FILES, *validate.REPORT_FILES, "manifest", "vectors", "report")
)


def delivered_tree(root: Path) -> PackageTree:
    """Deliver real writer output with disposable local provenance sources."""
    tree = make_tree(root)
    sources = root / "sources"
    sources.mkdir()
    parser = sources / "parser.py"
    taxonomy = sources / "classify.py"
    parser.write_bytes(b"# SYNTHETIC parser provenance\n")
    taxonomy.write_bytes(b"# SYNTHETIC taxonomy provenance\n")
    tree = replace(
        tree,
        inputs=replace(
            tree.inputs, parser_source=parser, taxonomy_source=taxonomy
        ),
    )
    package.run_delivery(tree.inputs)
    return tree


def report_paths(tree: PackageTree) -> validate.PackageReports:
    """Return the three explicit fixture report paths."""
    return validate.PackageReports(
        tree.inputs.parse_report,
        tree.inputs.chunk_report,
        tree.inputs.embedding_report,
    )


def check(tree: PackageTree, **kwargs: Any) -> validate.ValidationOutcome:
    """Call only the new receiver API, without any CLI or producer wiring."""
    return validate.validate_package(
        tree.inputs.output_dir, report_paths(tree), **kwargs
    )


def artifact_path(tree: PackageTree, name: str) -> Path:
    """Resolve a controlled fixed basename to its fixture path."""
    if name in validate.REPORT_FILES:
        return getattr(tree.inputs, name.removesuffix(".json"))
    return tree.inputs.output_dir / name


def read_artifact(tree: PackageTree, name: str) -> Any:
    """Read emitted records rather than standalone record factories."""
    path = artifact_path(tree, name)
    return rows(path) if name.endswith(".jsonl") else read_json(path)


def save_artifact(tree: PackageTree, name: str, value: Any) -> None:
    """Rewrite a mutated fixture without concealing descriptor collateral."""
    path = artifact_path(tree, name)
    if name.endswith(".jsonl"):
        write_rows(path, value)
    else:
        write_json(path, value)


def set_path(value: Any, path: tuple[str | int, ...], replacement: Any) -> None:
    """Replace one field along an explicit path in controlled test data."""
    for key in path[:-1]:
        value = value[key]
    value[path[-1]] = replacement


def assert_safe(findings: tuple[Finding, ...]) -> None:
    """Require bounded deterministic diagnostics without source values."""
    assert isinstance(findings, tuple)
    assert all(isinstance(item, Finding) for item in findings)
    assert [item.code for item in findings] == sorted(
        {item.code for item in findings}
    )
    for item in findings:
        assert re.fullmatch(r"[a-z][a-z0-9_-]*", item.code)
        assert item.count > 0
        assert 1 <= len(item.ids) <= 3
        assert len(set(item.ids)) == len(item.ids)
        assert all(
            identifier in SAFE_IDS or re.fullmatch(r"[0-9a-f]{64}", identifier)
            for identifier in item.ids
        )
    assert "SYNTHETIC" not in repr(findings)
    assert "/private" not in repr(findings)
    assert "10.1234/" not in repr(findings)


def require(
    outcome: validate.ValidationOutcome,
    code: str,
    identifier: str,
    *,
    structural: bool = False,
) -> Finding:
    """Assert a targeted code/ID, allowing related semantic collateral."""
    assert_safe(outcome.findings)
    assert outcome.structural is structural
    selected = {item.code: item for item in outcome.findings}
    assert code in selected
    assert identifier in selected[code].ids
    if not structural:
        assert not set(selected) & (
            validate.STRUCTURAL_CODES | {"report-structure"}
        )
    return selected[code]


def forbidden(*args: Any, **kwargs: Any) -> Never:
    """Reject source-dependent validation or an out-of-bound operation."""
    raise AssertionError("SYNTHETIC forbidden operation")
