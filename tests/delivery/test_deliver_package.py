"""SYNTHETIC offline T003 Phase 1 behavior tests; expected RED until Phase 2."""

from __future__ import annotations

import ast
import builtins
import hashlib
import inspect
import io
import json
import os
import re
import shutil
import socket
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from delivery_fixtures import paper
from package_fixtures import (
    COPIED,
    PACKAGE_FILES,
    PAYLOADS,
    REPO,
    PackageTree,
    RecordingEnvironment,
    descriptor,
    make_tree,
    read_json,
    rows,
    snapshot,
    symlinks_supported,
    write_json,
    write_rows,
)

from sciscope.chunking.config import TEMPLATE_VERSION
from sciscope.chunking.counter import Utf8BytesDiv3Counter
from sciscope.chunking.output import CHUNKING_VERSION
from sciscope.delivery import contract, package
from sciscope.delivery.papers import build_papers
from sciscope.pipeline.cli import main


@pytest.fixture(autouse=True)
def block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Block sockets before building fixtures or calling delivery."""
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


def forbidden(*args: object, **kwargs: object) -> Any:
    """Fail on any forbidden environment-independent transport or cache call."""
    raise AssertionError("SYNTHETIC forbidden access")


@pytest.fixture
def tree(tmp_path: Path) -> PackageTree:
    """Build upstream artifacts without running delivery."""
    return make_tree(tmp_path)


def expected_manifest(tree: PackageTree) -> dict[str, Any]:
    """Calculate exact metadata independently of the delivery builder."""
    inputs = tree.inputs
    embedded = read_json(inputs.embedding_manifest)
    return {
        "schema_version": "0.3.0",
        "contract_version": "0.3.0",
        "status": "draft",
        "counts": {"papers": 2, "sections": 3, "chunks": 2},
        "files": {
            name: descriptor(inputs.output_dir / name, count)
            for name, count in zip(PAYLOADS, (2, 3, 2, 2, 1), strict=True)
        },
        "processing_versions": {
            "parser": {
                "version": None,
                "source_sha256": hashlib.sha256(
                    inputs.parser_source.read_bytes()
                ).hexdigest(),
            },
            "taxonomy": {
                "version": "v0",
                "source_sha256": hashlib.sha256(
                    inputs.taxonomy_source.read_bytes()
                ).hexdigest(),
            },
            "locator": "jats:v1",
            "chunking_version": CHUNKING_VERSION,
            "token_counter_id": Utf8BytesDiv3Counter.counter_id,
            "template_version": TEMPLATE_VERSION,
        },
        "source_reports": {
            name + ".json": descriptor(getattr(inputs, name))
            for name in ("parse_report", "chunk_report", "embedding_report")
        },
        "embedding_set": {
            "provider": embedded["provider"],
            "model": embedded["model"],
            "dimensions": embedded["returned_dimensions"],
            "dtype": "float32-le",
            "row_mapping": "embedding_manifest.entries",
            "passage_prefix": embedded["passage_prefix"],
            "query_prefix": embedded["query_prefix"],
            "normalization": {**embedded["normalization"], "tolerance": 0.01},
            "chunks_sha256": embedded["chunks_sha256"],
            "vectors_sha256": embedded["vectors_sha256"],
            "embedding_model_revision": None,
        },
    }


def assert_diagnostic(captured: pytest.CaptureResult[str], code: str) -> None:
    """Require bounded safe codes and IDs, with no arbitrary input echo."""
    assert captured.out == ""
    lines = captured.err.split("\n")
    assert lines[-1] == ""
    assert re.fullmatch(r"failures: [1-9][0-9]*", lines[-2])
    assert any(line.startswith(f"error: {code} count: ") for line in lines[:-2])
    for line in lines[:-2]:
        assert re.fullmatch(
            r"error: [a-z][a-z0-9_-]* count: [1-9][0-9]* first: "
            r"(?:report|manifest|vectors|[0-9a-f]{64})"
            r"(?:,(?:report|manifest|vectors|[0-9a-f]{64})){0,2}",
            line,
        )


def test_success_exact_manifest_and_counts(
    tree: PackageTree, capsys: pytest.CaptureFixture[str]
) -> None:
    """Deliver six files and the exact independently assembled metadata."""
    assert main(tree.args()) == 0
    assert capsys.readouterr() == (
        "delivered papers: 2 sections: 3 chunks: 2 vectors: 2 files: 6\n",
        "",
    )
    assert sorted(
        item.name for item in tree.inputs.output_dir.iterdir()
    ) == sorted(PACKAGE_FILES)
    manifest = read_json(tree.inputs.output_dir / "delivery_manifest.json")
    assert manifest == expected_manifest(tree)
    assert tuple(manifest) == tuple(expected_manifest(tree))
    assert contract.check_delivery_manifest(manifest) == ()
    assert manifest["embedding_set"]["dimensions"] == 2
    assert (
        manifest["embedding_set"]["dimensions"]
        == read_json(tree.inputs.embedding_manifest)["requested_dimensions"]
    )


def test_copies_sources_and_papers_unchanged(tree: PackageTree) -> None:
    """Preserve upstream bytes and produce the expected papers and copies."""
    before = snapshot(tree.root / "upstream")
    summary = package.run_delivery(tree.inputs)
    assert summary == package.DeliverySummary(2, 3, 2, 2, 6)
    assert snapshot(tree.root / "upstream") == before
    for name in COPIED:
        assert (
            tree.inputs.output_dir
            / (
                name
                + (
                    ".f32"
                    if name == "vectors"
                    else ".json"
                    if name == "embedding_manifest"
                    else ".jsonl"
                )
            )
        ).read_bytes() == getattr(tree.inputs, name).read_bytes()
    papers = rows(tree.inputs.output_dir / "papers.jsonl")
    assert papers == list(tree.expected_papers)
    assert all(tuple(row) == contract.PAPER_FIELDS for row in papers)
    assert [row["language"] for row in papers] == ["EN", "en"]
    assert (
        tree.inputs.committed_manifest.read_bytes()
        == (tree.inputs.output_dir / "delivery_manifest.json").read_bytes()
    )
    assert any(
        row["paragraph_count"] == 0
        for row in rows(tree.inputs.output_dir / "sections.jsonl")
    )


def test_two_run_determinism(tree: PackageTree) -> None:
    """Two successful runs produce the same six files and committed bytes."""
    package.run_delivery(tree.inputs)
    first, committed = (
        snapshot(tree.inputs.output_dir),
        tree.inputs.committed_manifest.read_bytes(),
    )
    package.run_delivery(tree.inputs)
    assert snapshot(tree.inputs.output_dir) == first
    assert tree.inputs.committed_manifest.read_bytes() == committed
    assert sorted(
        item.name for item in tree.inputs.output_dir.parent.iterdir()
    ) == ["pilot"]
    assert sorted(
        item.name for item in tree.inputs.committed_manifest.parent.iterdir()
    ) == ["delivery_manifest.json"]


@pytest.mark.parametrize(
    "defect,code,status",
    [
        ("corrupt-chunk", "chunk-hash-mismatch", 1),
        ("hash", "chunks-sha-mismatch", 1),
        ("partial", "partial-set", 1),
        ("truncated", "vectors-size", 1),
        ("report", "report-manifest-mismatch", 1),
        ("version", "chunk-version-mismatch", 1),
        ("unreadable", "missing-file", 2),
        ("structure", "wrong-type", 2),
    ],
)
def test_upstream_refused_preserves_previous(
    tree: PackageTree,
    capsys: pytest.CaptureFixture[str],
    defect: str,
    code: str,
    status: int,
) -> None:
    """Refuse each upstream defect before publishing."""
    inputs = tree.inputs
    if defect in ("corrupt-chunk", "version", "structure"):
        records = rows(inputs.chunks)
        field, value = {
            "corrupt-chunk": ("text_sha256", "0" * 64),
            "version": ("chunking_version", "SYNTHETIC-wrong"),
            "structure": ("ordinal", True),
        }[defect]
        records[0][field] = value
        write_rows(inputs.chunks, records)
    elif defect in ("hash", "partial"):
        manifest = read_json(inputs.embedding_manifest)
        manifest["chunks_sha256" if defect == "hash" else "status"] = (
            "0" * 64 if defect == "hash" else "partial"
        )
        write_json(inputs.embedding_manifest, manifest)
    elif defect == "truncated":
        inputs.vectors.write_bytes(inputs.vectors.read_bytes()[:-1])
    elif defect == "report":
        report = read_json(inputs.embedding_report)
        report["paper_count"] += 1
        write_json(inputs.embedding_report, report)
    else:
        inputs.metadata.unlink()
    tree.seed_previous()
    before = snapshot(tree.root)
    assert main(tree.args()) == status
    assert_diagnostic(capsys.readouterr(), code)
    assert snapshot(tree.root) == before


@pytest.mark.parametrize(
    "side,defect,code",
    [
        ("metadata", "missing", "paper-missing-metadata"),
        ("acquisition_manifest", "missing", "paper-missing-manifest"),
        ("metadata", "duplicate", "paper-duplicate-metadata-doi"),
        ("acquisition_manifest", "duplicate", "paper-duplicate-manifest-doi"),
        ("metadata", "license", "paper-license-mismatch"),
    ],
)
def test_join_failures_are_findings(
    tree: PackageTree,
    capsys: pytest.CaptureFixture[str],
    side: str,
    defect: str,
    code: str,
) -> None:
    """Convert paper errors into findings and preserve prior artifacts."""
    path = getattr(tree.inputs, side)
    records = rows(path)
    if defect == "missing":
        records.pop()
    elif defect == "duplicate":
        records.append(deepcopy(records[0]))
    else:
        records[0]["license"] = "SYNTHETIC secret mismatch"
    write_rows(path, records)
    tree.seed_previous()
    before = snapshot(tree.root)
    assert main(tree.args()) == 1
    captured = capsys.readouterr()
    assert_diagnostic(captured, code)
    assert f"error: {code} count: 1 first: report\n" in captured.err
    assert snapshot(tree.root) == before


@pytest.mark.parametrize("side", ["metadata", "acquisition_manifest"])
@pytest.mark.parametrize(
    "bad,code",
    [
        (b"\xff\n", "invalid-utf8"),
        (b"{\n", "invalid-json"),
        (b'{"doi":"x","doi":"y"}\n', "duplicate-json-key"),
        (b'{"doi":NaN}\n', "invalid-json"),
        (b'{"doi":Infinity}\n', "invalid-json"),
        (b"{}\n\n{}\n", "invalid-json"),
    ],
)
def test_strict_private_jsonl_reader(
    tree: PackageTree,
    capsys: pytest.CaptureFixture[str],
    side: str,
    bad: bytes,
    code: str,
) -> None:
    """Reject malformed JSONL with sanitized findings."""
    getattr(tree.inputs, side).write_bytes(bad)
    tree.seed_previous()
    before = snapshot(tree.root)
    assert main(tree.args()) == 2
    assert_diagnostic(capsys.readouterr(), code)
    assert snapshot(tree.root) == before


@pytest.mark.parametrize(
    "entity", ["paper", "section", "chunk", "delivery_manifest"]
)
def test_produced_structure_failure(
    tree: PackageTree,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    entity: str,
) -> None:
    """Run each Group A checker and refuse its structural findings as exit 1."""
    code = entity + "-extra-field"
    monkeypatch.setattr(contract, "check_" + entity, lambda value: (code,))
    tree.seed_previous()
    before = snapshot(tree.root)
    assert main(tree.args()) == 1
    assert_diagnostic(capsys.readouterr(), code)
    assert snapshot(tree.root) == before


@pytest.mark.parametrize(
    "case",
    [
        "output-input",
        "output-parent-input",
        "output-under-input",
        "output-cache",
        "output-under-cache",
        "committed-input",
        "committed-parent-input",
        "same-outputs",
        "committed-inside-output",
        "output-under-committed",
        "output-file",
        "reserved-stage",
        "reserved-backup",
    ],
)
def test_alias_matrix(tree: PackageTree, case: str) -> None:
    """Reject overlapping paths, file outputs and reserved names."""
    inputs = tree.inputs
    changes: dict[str, Path] = {
        "output_dir": inputs.output_dir,
        "committed_manifest": inputs.committed_manifest,
    }
    if case == "output-input":
        changes["output_dir"] = inputs.chunks
    elif case == "output-parent-input":
        changes["output_dir"] = inputs.chunks.parent
    elif case == "output-under-input":
        changes["output_dir"] = inputs.chunks / "pilot"
    elif case == "output-cache":
        changes["output_dir"] = inputs.cache_dir
    elif case == "output-under-cache":
        changes["output_dir"] = inputs.cache_dir / "nested"
    elif case == "committed-input":
        changes["committed_manifest"] = inputs.metadata
    elif case == "committed-parent-input":
        changes["committed_manifest"] = inputs.metadata.parent
    elif case == "same-outputs":
        changes["committed_manifest"] = inputs.output_dir
    elif case == "committed-inside-output":
        changes["committed_manifest"] = inputs.output_dir / "copy.json"
    elif case == "output-under-committed":
        changes["output_dir"] = inputs.committed_manifest / "pilot"
    elif case == "output-file":
        inputs.output_dir.parent.mkdir()
        inputs.output_dir.write_bytes(b"SYNTHETIC existing file")
    else:
        changes["output_dir"] = inputs.output_dir.parent / (
            ".sciscope-delivery-stage-old"
            if case == "reserved-stage"
            else ".sciscope-delivery-backup-old"
        )
    before = snapshot(tree.root)
    with pytest.raises(package.DeliveryError) as caught:
        package.run_delivery(replace(inputs, **changes))
    assert (caught.value.code, caught.value.exit_code) == (
        "output-path-conflict",
        2,
    )
    assert snapshot(tree.root) == before


@pytest.mark.skipif(
    not symlinks_supported(), reason="Symlink privilege unavailable"
)
def test_symlink_output(tree: PackageTree) -> None:
    """Reject a directory symlink without writing through it."""
    target = tree.root / "elsewhere"
    target.mkdir()
    tree.inputs.output_dir.parent.mkdir()
    tree.inputs.output_dir.symlink_to(target, target_is_directory=True)
    with pytest.raises(package.DeliveryError) as caught:
        package.run_delivery(tree.inputs)
    assert caught.value.code == "output-path-conflict"
    assert list(target.iterdir()) == []


@pytest.mark.parametrize("step", [1, 2, 3, 4])
@pytest.mark.parametrize("error_type", [OSError, PermissionError])
def test_each_publication_move_rolls_back(
    tree: PackageTree,
    monkeypatch: pytest.MonkeyPatch,
    step: int,
    error_type: type[OSError],
) -> None:
    """Fail one forward move, allow rollback, and recover both old artifacts."""
    package.run_delivery(tree.inputs)
    changed_metadata = rows(tree.inputs.metadata)
    changed_metadata[0]["title"] = "SYNTHETIC changed title for next delivery"
    write_rows(tree.inputs.metadata, changed_metadata)
    before = snapshot(tree.root)
    original = os.replace
    calls = 0

    def fail_move(source: Any, target: Any, *args: Any, **kwargs: Any) -> None:
        nonlocal calls
        calls += 1
        if calls == step:
            raise error_type("SYNTHETIC path/key/prose must never escape")
        original(source, target, *args, **kwargs)

    # Plan fixes all four forward moves to os.replace; Path.replace delegates.
    monkeypatch.setattr(os, "replace", fail_move)
    with pytest.raises(package.DeliveryError) as caught:
        package.run_delivery(tree.inputs)
    assert calls >= step
    assert (caught.value.code, caught.value.exit_code) == (
        "output-write-failed",
        1,
    )
    assert snapshot(tree.root) == before


def test_first_publication_failure_leaves_no_package(
    tree: PackageTree, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Remove the new package when the first committed copy fails."""
    original = os.replace

    def fail_copy(source: Any, target: Any) -> None:
        if Path(target) == tree.inputs.committed_manifest:
            raise OSError("SYNTHETIC")
        original(source, target)

    monkeypatch.setattr(os, "replace", fail_copy)
    with pytest.raises(package.DeliveryError) as caught:
        package.run_delivery(tree.inputs)
    assert caught.value.code == "output-write-failed"
    assert not tree.inputs.output_dir.exists()
    assert not tree.inputs.committed_manifest.exists()
    for parent in (
        tree.inputs.output_dir.parent,
        tree.inputs.committed_manifest.parent,
    ):
        assert not parent.exists() or list(parent.iterdir()) == []


def test_crash_leftovers_are_ignored(tree: PackageTree) -> None:
    """Ignore reserved old siblings and preserve their bytes."""
    leftovers = []
    for parent in (
        tree.inputs.output_dir.parent,
        tree.inputs.committed_manifest.parent,
    ):
        parent.mkdir(parents=True)
        for prefix in ("stage", "backup"):
            directory = parent / f".sciscope-delivery-{prefix}-old"
            directory.mkdir()
            (directory / "delivery_manifest.json").write_bytes(
                b"SYNTHETIC invalid crash leftover"
            )
            leftovers.append((directory, snapshot(directory)))
    package.run_delivery(tree.inputs)
    assert read_json(
        tree.inputs.output_dir / "delivery_manifest.json"
    ) == expected_manifest(tree)
    for directory, before in leftovers:
        assert snapshot(directory) == before
    package.run_delivery(tree.inputs)
    assert len(list(tree.inputs.output_dir.parent.iterdir())) == 3
    assert len(list(tree.inputs.committed_manifest.parent.iterdir())) == 3


def test_staged_copies_are_validated(
    tree: PackageTree, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Validate staged bytes even if original sources change."""
    original = package.validate_staged_inputs
    called = []

    def observe(inputs: package.DeliveryInputs, staged_dir: Path) -> Any:
        assert staged_dir.parent == inputs.output_dir.parent
        assert staged_dir != inputs.output_dir
        for name in COPIED:
            filename = {
                "sections": "sections.jsonl",
                "chunks": "chunks.jsonl",
                "vectors": "vectors.f32",
                "embedding_manifest": "embedding_manifest.json",
            }[name]
            assert (staged_dir / filename).read_bytes() == getattr(
                inputs, name
            ).read_bytes()
        inputs.chunks.write_bytes(b"SYNTHETIC changed original after copy\n")
        called.append(staged_dir)
        return original(inputs, staged_dir)

    monkeypatch.setattr(package, "validate_staged_inputs", observe)
    package.run_delivery(tree.inputs)
    assert called
    assert len(rows(tree.inputs.output_dir / "chunks.jsonl")) == 2


def test_staged_corruption_refused(
    tree: PackageTree, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject staged corruption before publication."""
    tree.seed_previous()
    before = snapshot(tree.root)
    original = package.render_manifest

    def corrupt(manifest: Any) -> bytes:
        stages = list(
            tree.inputs.output_dir.parent.glob(".sciscope-delivery-stage-*")
        )
        assert len(stages) == 1
        (stages[0] / "vectors.f32").write_bytes(b"SYNTHETIC corruption")
        return original(manifest)

    monkeypatch.setattr(package, "render_manifest", corrupt)
    with pytest.raises(package.DeliveryError) as caught:
        package.run_delivery(tree.inputs)
    assert caught.value.code == "delivery-integrity-mismatch"
    assert snapshot(tree.root) == before


def test_staged_validator_uses_staged_paths(tree: PackageTree) -> None:
    """Use staged data even when original inputs are good."""
    staged = tree.root / "staged"
    staged.mkdir()
    for name in COPIED:
        shutil.copyfile(
            getattr(tree.inputs, name),
            staged
            / {
                "sections": "sections.jsonl",
                "chunks": "chunks.jsonl",
                "vectors": "vectors.f32",
                "embedding_manifest": "embedding_manifest.json",
            }[name],
        )
    assert package.validate_staged_inputs(tree.inputs, staged) == ()
    (staged / "vectors.f32").write_bytes(b"x")
    assert "vectors-size" in {
        finding.code
        for finding in package.validate_staged_inputs(tree.inputs, staged)
    }


def test_pure_builder_and_renderers(
    tree: PackageTree, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Build and render with filesystem and network access blocked."""
    # Prepare independent descriptors before blocking I/O; no delivery needed.
    facts = {
        "counts": {"papers": 2, "sections": 3, "chunks": 2},
        "files": {
            name: {
                "sha256": "a" * 64,
                "bytes": 4,
                "record_count": 2 if name.endswith("jsonl") else 1,
            }
            for name in PAYLOADS
        },
        "source_reports": {
            name: {"sha256": "b" * 64, "bytes": 1}
            for name in (
                "parse_report.json",
                "chunk_report.json",
                "embedding_report.json",
            )
        },
        "parser_sha256": "c" * 64,
        "taxonomy_sha256": "d" * 64,
        "chunking_version": CHUNKING_VERSION,
        "token_counter_id": Utf8BytesDiv3Counter.counter_id,
        "template_version": TEMPLATE_VERSION,
        "embedding_manifest": read_json(tree.inputs.embedding_manifest),
    }
    before = deepcopy(facts)
    papers = build_papers(
        rows(tree.inputs.metadata), rows(tree.inputs.acquisition_manifest)
    )
    with monkeypatch.context() as guarded:
        guarded.setattr(builtins, "open", forbidden)
        guarded.setattr(io, "open", forbidden)
        manifest = package.build_delivery_manifest(**facts)
        encoded = package.render_manifest(manifest)
        rendered = package.render_papers(
            tuple(
                dict(reversed(tuple(row.items()))) for row in reversed(papers)
            )
        )
    assert facts == before
    assert (
        manifest["processing_versions"]["parser"]["source_sha256"] == "c" * 64
    )
    assert contract.check_delivery_manifest(manifest) == ()
    assert (
        encoded
        == (
            json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False)
            + "\n"
        ).encode()
    )
    assert (
        rendered
        == "".join(
            json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n"
            for row in tree.expected_papers
        ).encode()
    )
    assert b"\\u2028" not in rendered and "\u2028".encode() in rendered
    assert not encoded.startswith(b"\xef\xbb\xbf") and b"\r\n" not in encoded


@pytest.mark.parametrize("renderer", ["render_manifest", "render_papers"])
def test_renderers_refuse_nonfinite(renderer: str) -> None:
    """Strict JSON writers reject nonfinite numbers rather than emit NaN."""
    bad_paper = paper()
    bad_paper["publication_year"] = float("nan")
    with pytest.raises(ValueError):
        getattr(package, renderer)(
            {"bad": float("nan")}
            if renderer == "render_manifest"
            else [bad_paper]
        )


def test_source_hash_is_informational(
    tree: PackageTree, tmp_path: Path
) -> None:
    """Treat source edits as informational provenance."""
    package.run_delivery(tree.inputs)
    first = read_json(tree.inputs.committed_manifest)
    assert (
        first["processing_versions"]["parser"]["source_sha256"]
        == hashlib.sha256(
            (REPO / "src/sciscope/jats/parser.py").read_bytes()
        ).hexdigest()
    )
    alternate = tmp_path / "synthetic_parser.py"
    alternate.write_bytes(
        b"# SYNTHETIC alternate checkout, informational only\n"
    )
    package.run_delivery(replace(tree.inputs, parser_source=alternate))
    second = read_json(tree.inputs.committed_manifest)
    assert (
        second["processing_versions"]["parser"]["source_sha256"]
        == hashlib.sha256(alternate.read_bytes()).hexdigest()
    )
    second["processing_versions"]["parser"] = first["processing_versions"][
        "parser"
    ]
    assert second == first


def test_no_environment_transport_or_cache(
    tree: PackageTree,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Deliver without environment lookups, transport creation or cache I/O."""
    from sciscope.embedding.cache import EmbeddingCache

    environment = RecordingEnvironment()
    cache_before = snapshot(tree.inputs.cache_dir)
    original_open = io.open

    def guarded_open(file: Any, *args: Any, **kwargs: Any) -> Any:
        if isinstance(file, (str, os.PathLike)):
            path = Path(file).resolve()
            assert not path.is_relative_to(tree.inputs.cache_dir.resolve())
        return original_open(file, *args, **kwargs)

    with monkeypatch.context() as guarded:
        guarded.setattr(os, "environ", environment)
        guarded.setattr(EmbeddingCache, "__init__", forbidden)
        guarded.setattr(io, "open", guarded_open)
        assert (
            main(tree.args(), environ=environment, transport_factory=forbidden)
            == 0
        )
    assert environment.accessed_keys == []
    assert snapshot(tree.inputs.cache_dir) == cache_before
    assert "SYNTHETIC-KEY" not in str(capsys.readouterr())


def test_static_offline_and_validator_guard() -> None:
    """Require validator reuse and forbid offline dependency violations."""
    syntax = ast.parse(inspect.getsource(package))
    calls = {
        ast.unparse(node.func).split(".")[-1]
        for node in ast.walk(syntax)
        if isinstance(node, ast.Call)
    }
    assert {
        "load_sources",
        "validate_chunks",
        "validate_embedding_set",
        "validate_embedding_structure",
    } <= calls
    assert (
        not {
            "read_api_key",
            "read_base_url",
            "getenv",
            "EmbeddingCache",
            "UrllibTransport",
            "OpenAIEmbedder",
        }
        & calls
    )
    assert "splitlines" not in calls
    for node in ast.walk(syntax):
        if isinstance(node, ast.Attribute):
            assert node.attr != "environ"


def test_default_cli_paths(
    tree: PackageTree,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Resolve default paths in an isolated synthetic checkout via main."""
    for name in (
        "metadata",
        "acquisition_manifest",
        "sections",
        "paragraphs",
        "parse_report",
        "chunks",
        "chunk_report",
        "vectors",
        "embedding_manifest",
        "embedding_report",
        "parser_source",
        "taxonomy_source",
    ):
        target = tree.root / getattr(package.DeliveryInputs(), name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(getattr(tree.inputs, name), target)
    monkeypatch.chdir(tree.root)
    assert main(["deliver"]) == 0
    assert capsys.readouterr().out == (
        "delivered papers: 2 sections: 3 chunks: 2 vectors: 2 files: 6\n"
    )
    defaults = package.DeliveryInputs()
    assert defaults.output_dir == Path("data/delivery/pilot")
    assert defaults.committed_manifest == Path(
        "data/pilot/delivery_manifest.json"
    )
    assert (
        defaults.committed_manifest.read_bytes()
        == (defaults.output_dir / "delivery_manifest.json").read_bytes()
    )


def test_upstream_orchestration_parameters(
    tree: PackageTree, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reuse all four validators with staged paths and complete-set defaults."""
    from sciscope.chunking import loader
    from sciscope.chunking import validate as chunk_validation
    from sciscope.embedding import validate as embedding_validation

    staged = tree.root / "stage-validation"
    staged.mkdir()
    for name, filename in zip(
        COPIED,
        (
            "sections.jsonl",
            "chunks.jsonl",
            "vectors.f32",
            "embedding_manifest.json",
        ),
        strict=True,
    ):
        shutil.copyfile(getattr(tree.inputs, name), staged / filename)
    calls: set[str] = set()
    source_loader = loader.load_sources
    chunk_validator = chunk_validation.validate_chunks
    set_validator = embedding_validation.validate_embedding_set
    structure_validator = embedding_validation.validate_embedding_structure

    def load(sections: Path, paragraphs: Path, report: Path) -> Any:
        calls.add("sources")
        assert sections == staged / "sections.jsonl"
        assert paragraphs == tree.inputs.paragraphs
        assert report == tree.inputs.parse_report
        return source_loader(sections, paragraphs, report)

    def chunks(*args: Any, **kwargs: Any) -> Any:
        calls.add("chunks")
        assert kwargs["operational_cap_tokens"] == 384
        assert kwargs["chunk_report"] == read_json(tree.inputs.chunk_report)
        return chunk_validator(*args, **kwargs)

    def embeddings(*args: Any, **kwargs: Any) -> Any:
        calls.add("embedding-set")
        assert kwargs["allow_partial"] is False
        assert (
            kwargs["norm_tolerance"] == package.DEFAULT_NORM_TOLERANCE == 0.01
        )
        assert (
            kwargs["chunks_sha256"]
            == hashlib.sha256(
                (staged / "chunks.jsonl").read_bytes()
            ).hexdigest()
        )
        assert kwargs["vectors"] == (staged / "vectors.f32").read_bytes()
        assert kwargs["manifest"] == read_json(
            staged / "embedding_manifest.json"
        )
        return set_validator(*args, **kwargs)

    def structure(*args: Any, **kwargs: Any) -> Any:
        calls.add("embedding-structure")
        return structure_validator(*args, **kwargs)

    monkeypatch.setattr(loader, "load_sources", load)
    monkeypatch.setattr(chunk_validation, "validate_chunks", chunks)
    monkeypatch.setattr(
        embedding_validation, "validate_embedding_set", embeddings
    )
    monkeypatch.setattr(
        embedding_validation, "validate_embedding_structure", structure
    )
    assert package.validate_staged_inputs(tree.inputs, staged) == ()
    assert calls == {
        "sources",
        "chunks",
        "embedding-set",
        "embedding-structure",
    }


@pytest.mark.parametrize(
    "extra", [["--unknown", "SYNTHETIC-value"], ["--metadata"]]
)
def test_usage_exit_two_sanitized(
    tree: PackageTree, capsys: pytest.CaptureFixture[str], extra: list[str]
) -> None:
    """Usage errors use exit 2 and the same sanitized finding format."""
    assert main([*tree.args(), *extra]) == 2
    assert_diagnostic(capsys.readouterr(), "invalid-usage")


def test_output_failure_sanitized(
    tree: PackageTree,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Print only sanitized publication findings."""

    def fail_move(*args: object, **kwargs: object) -> Any:
        raise PermissionError(str(tree.root) + " SYNTHETIC-KEY secret prose")

    monkeypatch.setattr(os, "replace", fail_move)
    assert main(tree.args()) == 1
    assert_diagnostic(capsys.readouterr(), "output-write-failed")


@pytest.mark.parametrize(
    "code,status",
    [
        ("output-path-conflict", 2),
        ("output-write-failed", 1),
        ("SYNTHETIC unsafe / key", 1),
    ],
)
def test_delivery_error_sanitizes(code: str, status: int) -> None:
    """Retain only known error codes and classified statuses."""
    error = package.DeliveryError(code)
    expected = code if code.startswith("output-") else "delivery-failed"
    assert error.code == str(error) == expected
    assert error.exit_code == status


def test_delivery_gitignore_rule() -> None:
    """Phase 2 must add the ignored delivery package root."""
    assert "data/delivery/" in (REPO / ".gitignore").read_text(
        encoding="utf-8"
    ).split("\n")
