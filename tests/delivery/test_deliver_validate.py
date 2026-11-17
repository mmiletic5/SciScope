"""SYNTHETIC offline RED contract for T005 library semantics only."""

from __future__ import annotations

import builtins
import hashlib
import io
import os
import random
import socket
import struct
from copy import deepcopy
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from delivery_fixtures import DIGEST
from package_fixtures import (
    PACKAGE_FILES,
    PackageTree,
    RecordingEnvironment,
    read_json,
    snapshot,
)
from validate_fixtures import (
    artifact_path,
    assert_safe,
    check,
    delivered_tree,
    forbidden,
    read_artifact,
    report_paths,
    require,
    save_artifact,
    set_path,
)

from sciscope.chunking import output as chunk_output
from sciscope.chunking import validate as chunk_validate
from sciscope.chunking.counter import Utf8BytesDiv3Counter
from sciscope.chunking.loader import SourceInputError
from sciscope.chunking.validate import Finding
from sciscope.delivery import validate
from sciscope.embedding import validate as embedding_validate
from sciscope.jats import locator
from sciscope.plos_pilot import doi as doi_module


@pytest.fixture(autouse=True)
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Block sockets during fixture setup and receiver validation."""
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


@pytest.fixture
def tree(tmp_path: Path) -> PackageTree:
    """Publish two SYNTHETIC papers with real offline writers."""
    return delivered_tree(tmp_path)


def test_valid_package_is_read_only_and_outcome_is_frozen(
    tree: PackageTree,
) -> None:
    """Accept actual delivery output with no false positives or byte changes."""
    before = snapshot(tree.root)
    outcome = check(tree)
    assert isinstance(outcome, validate.ValidationOutcome)
    assert outcome.findings == ()
    assert outcome.structural is False
    assert snapshot(tree.root) == before
    with pytest.raises(FrozenInstanceError):
        outcome.structural = True  # type: ignore[misc]


@pytest.mark.parametrize(
    "name,kind",
    [
        pytest.param("papers.jsonl", "paper", id="paper-doi"),
        pytest.param("sections.jsonl", "section", id="section-key"),
        pytest.param("chunks.jsonl", "chunk", id="chunk-id"),
        pytest.param("chunks.jsonl", "ordinal", id="chunk-ordinal-key"),
    ],
)
def test_duplicate_records(tree: PackageTree, name: str, kind: str) -> None:
    """Detect each of the four identity collisions on real emitted records."""
    records = read_artifact(tree, name)
    duplicate = deepcopy(records[0])
    if kind == "ordinal":
        duplicate["chunk_id"] = "c" * 64
    records.append(duplicate)
    save_artifact(tree, name, records)
    identifier = duplicate["chunk_id"] if name == "chunks.jsonl" else name
    require(check(tree), "delivery-duplicate-record", identifier)


@pytest.mark.parametrize(
    "name,path,value,code",
    [
        pytest.param(
            "sections.jsonl",
            (0, "doi"),
            "10.1234/synthetic.missing",
            "orphan-record",
            id="section-paper",
        ),
        pytest.param(
            "chunks.jsonl",
            (0, "doi"),
            "10.1234/synthetic.missing",
            "orphan-record",
            id="chunk-paper",
        ),
        pytest.param(
            "chunks.jsonl",
            (0, "section_id"),
            "10.1234/synthetic.a#missing",
            "orphan-record",
            id="chunk-section",
        ),
        pytest.param(
            "papers.jsonl",
            (0, "doi"),
            "10.1234/SYNTHETIC.A",
            "orphan-record",
            id="paper-normalization",
        ),
        pytest.param(
            "sections.jsonl",
            (0, "doi"),
            "10.1234/SYNTHETIC.A",
            "orphan-record",
            id="section-normalization",
        ),
        pytest.param(
            "chunks.jsonl",
            (0, "doi"),
            "10.1234/SYNTHETIC.A",
            "orphan-record",
            id="chunk-normalization",
        ),
        pytest.param(
            "sections.jsonl",
            (0, "section_id"),
            "SYNTHETIC /private prose",
            "orphan-record",
            id="section-owner",
        ),
        pytest.param(
            "chunks.jsonl",
            (0, "section_id"),
            "SYNTHETIC /private prose",
            "orphan-record",
            id="chunk-owner",
        ),
        pytest.param(
            "sections.jsonl",
            (0, "parent_section_id"),
            "SYNTHETIC /private prose",
            "parent-invalid",
            id="missing-parent",
        ),
        pytest.param(
            "sections.jsonl",
            (0, "depth"),
            2,
            "section-structure-mismatch",
            id="root-depth",
        ),
        pytest.param(
            "sections.jsonl",
            (0, "section_path"),
            ["SYNTHETIC wrong"],
            "section-structure-mismatch",
            id="root-path",
        ),
        pytest.param(
            "sections.jsonl",
            (0, "normalized_type"),
            "abstract",
            "section-structure-mismatch",
            id="body-abstract",
        ),
        pytest.param(
            "sections.jsonl",
            (0, "section_id"),
            "10.1234/synthetic.a#abstract",
            "section-structure-mismatch",
            id="abstract-type",
        ),
        pytest.param(
            "sections.jsonl",
            (0, "xml_sha256"),
            "c" * 64,
            "xml-sha-mismatch",
            id="section-xml",
        ),
        pytest.param(
            "chunks.jsonl",
            (0, "xml_sha256"),
            "c" * 64,
            "xml-sha-mismatch",
            id="chunk-xml",
        ),
        pytest.param(
            "sections.jsonl",
            (0, "source_locator"),
            f"jats:v1:{'c' * 64}:/article[1]",
            "locator-mismatch",
            id="section-locator-digest",
        ),
        pytest.param(
            "chunks.jsonl",
            (0, "source_locator"),
            f"jats:v1:{'c' * 64}:/article[1]",
            "locator-mismatch",
            id="chunk-locator-digest",
        ),
        pytest.param(
            "chunks.jsonl",
            (0, "spans", 0, "source_locator"),
            f"jats:v1:{'c' * 64}:/article[1]",
            "locator-mismatch",
            id="span-locator-digest",
        ),
        pytest.param(
            "chunks.jsonl",
            (0, "source_locator"),
            f"jats:v1:{DIGEST}:/article[1]/p[9]",
            "locator-mismatch",
            id="first-span-locator",
        ),
        pytest.param(
            "chunks.jsonl",
            (0, "normalized_type"),
            "methods",
            "chunk-field-mismatch",
            id="chunk-type",
        ),
        pytest.param(
            "chunks.jsonl",
            (0, "section_path"),
            ["SYNTHETIC wrong"],
            "chunk-field-mismatch",
            id="chunk-path",
        ),
        pytest.param(
            "chunks.jsonl",
            (0, "spans", 0, "start"),
            100,
            "chunk-field-mismatch",
            id="span-reversed",
        ),
        pytest.param(
            "chunks.jsonl", (0, "ordinal"), 2, "ordinal-gap", id="ordinal-start"
        ),
        pytest.param(
            "chunks.jsonl",
            (0, "text_sha256"),
            "c" * 64,
            "text-hash-mismatch",
            id="text-hash",
        ),
        pytest.param(
            "chunks.jsonl",
            (0, "text"),
            "SYNTHETIC /private prose",
            "text-hash-mismatch",
            id="text-changed",
        ),
        pytest.param(
            "chunks.jsonl",
            (0, "chunk_id"),
            "c" * 64,
            "chunk-id-mismatch",
            id="chunk-id-hash",
        ),
    ],
)
def test_semantic_mutations(
    tree: PackageTree,
    name: str,
    path: tuple[str | int, ...],
    value: Any,
    code: str,
) -> None:
    """Keep shape valid and assert the target without exact collateral sets."""
    records = read_artifact(tree, name)
    set_path(records, path, value)
    save_artifact(tree, name, records)
    identifier = records[0]["chunk_id"] if name == "chunks.jsonl" else name
    require(check(tree), "delivery-" + code, identifier)


@pytest.mark.parametrize(
    "kind", ["self", "forward", "cycle", "cross-paper", "null-child"]
)
def test_parent_graph_terminates(tree: PackageTree, kind: str) -> None:
    """Reject invalid ownership/preorder and bounded cyclic parent walks."""
    records = read_artifact(tree, "sections.jsonl")
    if kind == "self":
        records[0]["parent_section_id"] = records[0]["section_id"]
    elif kind == "forward":
        records[0]["parent_section_id"] = records[1]["section_id"]
    elif kind == "cycle":
        records[0]["parent_section_id"] = records[1]["section_id"]
        records[1]["parent_section_id"] = records[0]["section_id"]
    elif kind == "cross-paper":
        records[1]["parent_section_id"] = records[2]["section_id"]
    else:
        records[1].update(depth=2, section_path=["SYNTHETIC heading"] * 2)
    save_artifact(tree, "sections.jsonl", records)
    require(check(tree), "delivery-parent-invalid", "sections.jsonl")


@pytest.mark.parametrize("kind", ["valid", "depth", "path", "untitled"])
def test_nested_section_conventions(tree: PackageTree, kind: str) -> None:
    """Derive child depth/path from the earlier same-paper parent."""
    records = read_artifact(tree, "sections.jsonl")
    parent, child = records[:2]
    child.update(
        parent_section_id=parent["section_id"],
        depth=2,
        section_path=parent["section_path"] + [child["original_heading"]],
    )
    if kind == "depth":
        child["depth"] = 3
    elif kind == "path":
        child["section_path"] = ["SYNTHETIC other", child["original_heading"]]
    elif kind == "untitled":
        child.update(
            original_heading="  ",
            section_path=parent["section_path"] + ["(untitled)"],
        )
    save_artifact(tree, "sections.jsonl", records)
    chunks = read_artifact(tree, "chunks.jsonl")
    chunks[0]["section_path"] = child["section_path"]
    save_artifact(tree, "chunks.jsonl", chunks)
    outcome = check(tree)
    if kind in ("depth", "path"):
        require(
            outcome, "delivery-section-structure-mismatch", "sections.jsonl"
        )
    else:
        assert outcome.structural is False
        assert not {item.code for item in outcome.findings} & {
            "delivery-parent-invalid",
            "delivery-section-structure-mismatch",
            "delivery-chunk-field-mismatch",
        }


@pytest.mark.parametrize(
    "name,path,code",
    [
        pytest.param(
            "sections.jsonl",
            (0, "source_locator"),
            "section-bad-pattern",
            id="section-grammar",
        ),
        pytest.param(
            "chunks.jsonl",
            (0, "source_locator"),
            "chunk-bad-pattern",
            id="chunk-grammar",
        ),
        pytest.param(
            "chunks.jsonl",
            (0, "spans", 0, "source_locator"),
            "chunk-bad-pattern",
            id="span-grammar",
        ),
        pytest.param(
            "chunks.jsonl", (0, "spans"), "chunk-bad-value", id="empty-spans"
        ),
    ],
)
def test_contract_gates_locator_grammar_and_empty_spans(
    tree: PackageTree, name: str, path: tuple[str | int, ...], code: str
) -> None:
    """Preserve contract rejection rather than demand a semantic cascade."""
    records = read_artifact(tree, name)
    value = [] if path[-1] == "spans" else f"jats:v1:{DIGEST}:/sec[01]"
    set_path(records, path, value)
    save_artifact(tree, name, records)
    outcome = check(tree)
    require(outcome, code, name, structural=True)
    assert "delivery-locator-mismatch" not in {
        item.code for item in outcome.findings
    }


def test_equal_span_bounds(tree: PackageTree) -> None:
    """Positive equal bounds pass structure and fail cross-field semantics."""
    records = read_artifact(tree, "chunks.jsonl")
    records[0]["spans"][0].update(start=1, end=1)
    save_artifact(tree, "chunks.jsonl", records)
    require(
        check(tree), "delivery-chunk-field-mismatch", records[0]["chunk_id"]
    )


def test_ordinals_follow_file_order(tree: PackageTree) -> None:
    """A two-row section numbered 2 then 1 fails despite a contiguous set."""
    records = read_artifact(tree, "chunks.jsonl")
    second = deepcopy(records[0])
    records[0]["ordinal"] = 2
    second.update(ordinal=1, chunk_id="c" * 64)
    records.insert(1, second)
    save_artifact(tree, "chunks.jsonl", records)
    require(check(tree), "delivery-ordinal-gap", records[0]["chunk_id"])


@pytest.mark.parametrize(
    "field", ["chunking_version", "token_counter_id", "template_version"]
)
@pytest.mark.parametrize(
    "source",
    [
        "chunks.jsonl",
        "delivery_manifest.json",
        "embedding_manifest.json",
        "chunk_report.json",
    ],
)
def test_versions_respect_structure_gates(
    tree: PackageTree, field: str, source: str
) -> None:
    """Reports admit semantic version drift; fixed contract enums gate files."""
    value = read_artifact(tree, source)
    path = (0, field) if source.endswith(".jsonl") else (field,)
    if source == "delivery_manifest.json":
        path = ("processing_versions", field)
    set_path(value, path, "synthetic-v9")
    save_artifact(tree, source, value)
    outcome = check(tree)
    if source == "chunk_report.json":
        require(outcome, "delivery-version-mismatch", source)
    else:
        entity = (
            "chunk"
            if source == "chunks.jsonl"
            else source.removesuffix(".json")
        )
        require(outcome, entity + "-bad-value", source, structural=True)
        assert "delivery-version-mismatch" not in {
            item.code for item in outcome.findings
        }


@pytest.mark.parametrize(
    "source,path,value",
    [
        pytest.param(
            "parse_report.json",
            ("papers", 0, "doi"),
            "10.1234/synthetic.missing",
            id="parse-dois",
        ),
        pytest.param(
            "parse_report.json",
            ("papers", 0, "xml_sha256"),
            "c" * 64,
            id="parse-xml",
        ),
        pytest.param(
            "parse_report.json",
            ("papers", 0, "section_count"),
            99,
            id="parse-sections",
        ),
        pytest.param(
            "parse_report.json", ("summary", "succeeded"), 99, id="parse-total"
        ),
        pytest.param(
            "chunk_report.json",
            ("papers", 0, "doi"),
            "10.1234/synthetic.missing",
            id="chunk-dois",
        ),
        pytest.param(
            "chunk_report.json",
            ("papers", 0, "xml_sha256"),
            "c" * 64,
            id="chunk-xml",
        ),
        pytest.param(
            "chunk_report.json",
            ("papers", 0, "section_count"),
            99,
            id="chunk-sections",
        ),
        pytest.param(
            "chunk_report.json",
            ("papers", 0, "chunk_count"),
            99,
            id="chunk-chunks",
        ),
        pytest.param(
            "chunk_report.json",
            ("papers", 0, "sections_with_chunks"),
            99,
            id="chunk-populated",
        ),
        pytest.param(
            "chunk_report.json",
            ("summary", "paper_count"),
            99,
            id="total-papers",
        ),
        pytest.param(
            "chunk_report.json",
            ("summary", "section_count"),
            99,
            id="total-sections",
        ),
        pytest.param(
            "chunk_report.json",
            ("summary", "chunk_count"),
            99,
            id="total-chunks",
        ),
        pytest.param(
            "chunk_report.json",
            ("summary", "sections_with_chunks"),
            99,
            id="total-populated",
        ),
        pytest.param(
            "embedding_report.json", ("paper_count",), 99, id="embedding-papers"
        ),
        pytest.param(
            "embedding_report.json", ("chunk_count",), 99, id="embedding-chunks"
        ),
        pytest.param(
            "embedding_report.json",
            ("vector_count",),
            99,
            id="embedding-vectors",
        ),
    ],
)
def test_report_comparisons(
    tree: PackageTree, source: str, path: tuple[str | int, ...], value: Any
) -> None:
    """Compare each claimed report count/set/digest with delivered records."""
    report = read_artifact(tree, source)
    set_path(report, path, value)
    save_artifact(tree, source, report)
    require(check(tree), "delivery-report-mismatch", source)


@pytest.mark.parametrize(
    "path,value",
    [
        pytest.param(("provider",), "synthetic", id="provider"),
        pytest.param(("model",), "synthetic", id="model"),
        pytest.param(("dimensions",), 3, id="dimensions"),
        pytest.param(("passage_prefix",), "synthetic:", id="passage"),
        pytest.param(("query_prefix",), "synthetic:", id="query"),
        pytest.param(
            ("normalization", "observed_norm_min"), 0.5, id="norm-min"
        ),
        pytest.param(
            ("normalization", "observed_norm_max"), 1.5, id="norm-max"
        ),
        pytest.param(("normalization", "tolerance"), 0.02, id="tolerance"),
        pytest.param(("chunks_sha256",), "c" * 64, id="chunks-hash"),
        pytest.param(("vectors_sha256",), "c" * 64, id="vectors-hash"),
        pytest.param(("embedding_model_revision",), "synthetic", id="revision"),
    ],
)
def test_embedding_set_agreement(
    tree: PackageTree, path: tuple[str | int, ...], value: Any
) -> None:
    """Check every variable embedding-set fact without hardcoding dimensions."""
    manifest = read_artifact(tree, "delivery_manifest.json")
    set_path(manifest["embedding_set"], path, value)
    save_artifact(tree, "delivery_manifest.json", manifest)
    require(check(tree), "delivery-embedding-set-mismatch", "manifest")


@pytest.mark.parametrize(
    "field",
    ["requested_dimensions", "returned_dimensions", "provider", "model"],
)
def test_embedding_report_agrees_with_set(
    tree: PackageTree, field: str
) -> None:
    """Shared report metadata participates in the delivery-set comparison."""
    report = read_artifact(tree, "embedding_report.json")
    report[field] = 3 if field.endswith("dimensions") else "synthetic"
    save_artifact(tree, "embedding_report.json", report)
    require(check(tree), "delivery-embedding-set-mismatch", "manifest")


@pytest.mark.parametrize("kind", ["norm", "chunks-hash"])
def test_real_f003_findings_are_preserved(tree: PackageTree, kind: str) -> None:
    """Return F003 diagnostics directly, including the hex vector-row ID."""
    if kind == "norm":
        path = artifact_path(tree, "vectors.f32")
        path.write_bytes(struct.pack("<ff", 3.0, 0.0) + path.read_bytes()[8:])
        embedded = read_artifact(tree, "embedding_manifest.json")
        code, identifier = (
            "vector-norm-out-of-tolerance",
            embedded["entries"][0]["chunk_id"],
        )
    else:
        embedded = read_artifact(tree, "embedding_manifest.json")
        embedded["chunks_sha256"] = "c" * 64
        save_artifact(tree, "embedding_manifest.json", embedded)
        code, identifier = "chunks-sha-mismatch", "manifest"
    require(check(tree), code, identifier)


@pytest.mark.parametrize("kind", ["vectors-size", "partial-set"])
def test_overlap_uses_maximum_count(tree: PackageTree, kind: str) -> None:
    """T004 and F003 reporting one defect must not count it twice."""
    if kind == "vectors-size":
        path = artifact_path(tree, "vectors.f32")
        path.write_bytes(path.read_bytes()[:-1])
        identifier = "vectors"
    else:
        embedded = read_artifact(tree, "embedding_manifest.json")
        embedded["status"] = "partial"
        save_artifact(tree, "embedding_manifest.json", embedded)
        identifier = "manifest"
    assert require(check(tree), kind, identifier).count == 1


def test_reuse_calls_exact_public_arguments(
    tree: PackageTree, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Spy on direct delegation with a set stub that has no internal calls."""
    loaded, findings = validate.load_package(tree.inputs.output_dir)
    report = read_json(tree.inputs.embedding_report)
    structure_spy = Mock(return_value=None)
    set_spy = Mock(return_value=[])
    checker = Mock(wraps=validate.check_package_structure)
    with monkeypatch.context() as patch:
        patch.setattr(
            embedding_validate, "validate_embedding_structure", structure_spy
        )
        patch.setattr(embedding_validate, "validate_embedding_set", set_spy)
        patch.setattr(chunk_validate, "validate_chunks", forbidden)
        patch.setattr(validate, "check_package_structure", checker)
        outcome = check(tree, loaded=loaded, load_findings=tuple(findings))
    assert outcome.findings == ()
    checker.assert_called_once_with(
        tree.inputs.output_dir,
        report_paths(tree),
        loaded=loaded,
        load_findings=tuple(findings),
    )
    structure_spy.assert_called_once_with(
        loaded.manifests["embedding_manifest.json"], report
    )
    set_spy.assert_called_once()
    args, kwargs = set_spy.call_args
    assert args == (loaded.records["chunks.jsonl"],)
    assert isinstance(kwargs.pop("counter"), Utf8BytesDiv3Counter)
    assert kwargs == {
        "chunks_sha256": hashlib.sha256(
            loaded.raw_files["chunks.jsonl"]
        ).hexdigest(),
        "manifest": loaded.manifests["embedding_manifest.json"],
        "report": report,
        "vectors": loaded.raw_files["vectors.f32"],
        "operational_cap_tokens": 384,
        "norm_tolerance": 0.01,
        "allow_partial": False,
    }


def test_structure_exception_is_sanitized(
    tree: PackageTree, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Map SourceInputError to report-structure without leaking its payload."""
    with monkeypatch.context() as patch:
        patch.setattr(
            embedding_validate,
            "validate_embedding_structure",
            Mock(side_effect=SourceInputError("SYNTHETIC /private prose")),
        )
        patch.setattr(embedding_validate, "validate_embedding_set", forbidden)
        outcome = check(tree)
    require(outcome, "report-structure", "report", structural=True)


def test_merge_order_counts_and_unmodified_f003_ids(
    tree: PackageTree, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Preserve F003 counts/IDs and truncate the ordered cross-source union."""
    upstream = [
        Finding("set-input-mismatch", 7, ("c" * 64, "b" * 64, "a" * 64)),
        Finding("vectors-size", 4, ("vectors",)),
    ]
    original = validate.check_package_structure

    def structure(*args: Any, **kwargs: Any) -> validate.StructureOutcome:
        result = original(*args, **kwargs)
        return validate.StructureOutcome(
            (Finding("vectors-size", 3, ("manifest", "report", "d" * 64)),),
            False,
            result.loaded,
        )

    with monkeypatch.context() as patch:
        patch.setattr(validate, "check_package_structure", structure)
        patch.setattr(
            embedding_validate,
            "validate_embedding_set",
            Mock(return_value=upstream),
        )
        outcome = check(tree)
    selected = {item.code: item for item in outcome.findings}
    assert selected["set-input-mismatch"] == upstream[0]
    assert selected["vectors-size"] == Finding(
        "vectors-size", 4, ("manifest", "report", "d" * 64)
    )
    assert_safe(outcome.findings)
    assert outcome.structural is False


def test_bad_chunks_gate_only_dependent_rules(
    tree: PackageTree, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One structurally bad row gates the entire file, preserving other work."""
    chunks = read_artifact(tree, "chunks.jsonl")
    chunks[0]["ordinal"] = "SYNTHETIC /private prose"
    chunks[1]["text_sha256"] = "c" * 64
    save_artifact(tree, "chunks.jsonl", chunks)
    sections = read_artifact(tree, "sections.jsonl")
    sections[0]["xml_sha256"] = "c" * 64
    save_artifact(tree, "sections.jsonl", sections)
    report = read_artifact(tree, "parse_report.json")
    report["summary"]["succeeded"] = 99
    save_artifact(tree, "parse_report.json", report)
    with monkeypatch.context() as patch:
        patch.setattr(embedding_validate, "validate_embedding_set", forbidden)
        outcome = check(tree)
    require(outcome, "chunk-bad-type", "chunks.jsonl", structural=True)
    require(
        outcome, "delivery-xml-sha-mismatch", "sections.jsonl", structural=True
    )
    require(
        outcome,
        "delivery-report-mismatch",
        "parse_report.json",
        structural=True,
    )
    assert "delivery-text-hash-mismatch" not in {
        item.code for item in outcome.findings
    }


def test_independent_failures_all_survive(tree: PackageTree) -> None:
    """Collect simultaneous paper, section, chunk and report defects."""
    for name, path, value in (
        ("papers.jsonl", (0, "doi"), "10.1234/SYNTHETIC.A"),
        ("sections.jsonl", (2, "depth"), 2),
        ("chunks.jsonl", (1, "text_sha256"), "c" * 64),
        ("chunk_report.json", ("summary", "paper_count"), 99),
    ):
        artifact = read_artifact(tree, name)
        set_path(artifact, path, value)
        save_artifact(tree, name, artifact)
    outcome = check(tree)
    for code, identifier in (
        ("delivery-orphan-record", "papers.jsonl"),
        ("delivery-section-structure-mismatch", "sections.jsonl"),
        (
            "delivery-text-hash-mismatch",
            read_artifact(tree, "chunks.jsonl")[1]["chunk_id"],
        ),
        ("delivery-report-mismatch", "chunk_report.json"),
    ):
        require(outcome, code, identifier)


@pytest.mark.parametrize(
    "source",
    ["parse_report.json", "chunk_report.json", "embedding_report.json"],
)
@pytest.mark.parametrize(
    "raw,code",
    [
        pytest.param(b"\xef\xbb\xbf{}", "invalid-utf8", id="bom"),
        pytest.param(b"\xff", "invalid-utf8", id="utf8"),
        pytest.param(b"{", "invalid-json", id="malformed"),
        pytest.param(b'{"x":1,"x":2}', "duplicate-json-key", id="duplicate"),
        pytest.param(b"[]", "report-structure", id="wrong-root"),
        pytest.param(b"{}", "report-structure", id="missing-fields"),
    ],
)
def test_report_decoding_matrix(
    tree: PackageTree, source: str, raw: bytes, code: str
) -> None:
    """Decode each report strictly and classify corrupt structure safely."""
    artifact_path(tree, source).write_bytes(raw)
    outcome = check(tree)
    if source == "embedding_report.json" and code == "report-structure":
        assert any(
            item.code == code and set(item.ids) & {source, "report"}
            for item in outcome.findings
        )
        assert outcome.structural is True
        assert_safe(outcome.findings)
    else:
        require(outcome, code, source, structural=True)


@pytest.mark.parametrize(
    "source,path,value",
    [
        pytest.param("parse_report.json", ("papers",), {}, id="parse-papers"),
        pytest.param("parse_report.json", ("papers", 0), [], id="parse-paper"),
        pytest.param(
            "parse_report.json", ("papers", 0, "doi"), 7, id="parse-doi"
        ),
        pytest.param(
            "parse_report.json",
            ("papers", 0, "xml_sha256"),
            None,
            id="parse-digest",
        ),
        pytest.param(
            "parse_report.json",
            ("papers", 0, "section_count"),
            True,
            id="parse-count",
        ),
        pytest.param(
            "parse_report.json",
            ("summary", "succeeded"),
            2.0,
            id="parse-succeeded",
        ),
        pytest.param(
            "parse_report.json", ("summary", "failed"), False, id="parse-failed"
        ),
        pytest.param(
            "chunk_report.json",
            ("summary", "paper_count"),
            True,
            id="chunk-count",
        ),
        pytest.param(
            "chunk_report.json",
            ("papers", 0, "chunk_count"),
            1.0,
            id="chunk-paper",
        ),
        pytest.param(
            "embedding_report.json",
            ("paper_count",),
            True,
            id="embedding-count",
        ),
        pytest.param(
            "embedding_report.json",
            ("usage", "total_tokens"),
            "SYNTHETIC /private prose",
            id="embedding-usage",
        ),
    ],
)
def test_report_nested_types(
    tree: PackageTree, source: str, path: tuple[str | int, ...], value: Any
) -> None:
    """Exact primitive types include bool and integral-float rejection."""
    report = read_artifact(tree, source)
    set_path(report, path, value)
    save_artifact(tree, source, report)
    outcome = check(tree)
    assert outcome.structural is True
    assert_safe(outcome.findings)
    assert any(
        item.code == "report-structure" and set(item.ids) & {source, "report"}
        for item in outcome.findings
    )


@pytest.mark.parametrize("broken", [False, True], ids=["valid", "failed-load"])
def test_loaded_reuse_and_one_report_decode(
    tree: PackageTree, monkeypatch: pytest.MonkeyPatch, broken: bool
) -> None:
    """Never reload/decode package files, but decode each report once."""
    if broken:
        artifact_path(tree, "papers.jsonl").write_bytes(b"\xff")
    loaded, findings = validate.load_package(tree.inputs.output_dir)
    report_bytes = [
        getattr(tree.inputs, field).read_bytes()
        for field in ("parse_report", "chunk_report", "embedding_report")
    ]
    decoder = validate.decode_json
    seen: list[bytes] = []

    def decode(raw: bytes) -> tuple[object, tuple[str, ...]]:
        assert raw in report_bytes
        seen.append(raw)
        return decoder(raw)

    with monkeypatch.context() as patch:
        patch.setattr(validate, "load_package", forbidden)
        patch.setattr(validate, "decode_json", decode)
        outcome = check(tree, loaded=loaded, load_findings=tuple(findings))
    assert outcome.loaded is loaded
    assert len(seen) == 3
    assert all(seen.count(raw) == 1 for raw in report_bytes)
    if broken:
        require(outcome, "invalid-utf8", "papers.jsonl", structural=True)
    else:
        assert outcome.findings == ()


def test_existing_identity_helpers_are_reused(
    tree: PackageTree, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Resolve public normalization, locator and chunk identity at call time."""
    normalize = Mock(wraps=doi_module.normalize_doi)
    digest = Mock(wraps=locator.locator_digest)
    identity = Mock(wraps=chunk_output.chunk_id)
    with monkeypatch.context() as patch:
        patch.setattr(doi_module, "normalize_doi", normalize)
        patch.setattr(locator, "locator_digest", digest)
        patch.setattr(chunk_output, "chunk_id", identity)
        patch.setattr(chunk_validate, "validate_chunks", forbidden)
        outcome = check(tree)
    assert outcome.findings == ()
    assert normalize.call_count >= 7
    assert digest.call_count >= 7
    assert identity.call_count == 2


def test_local_source_changes_are_informational(tree: PackageTree) -> None:
    """Changed disposable parser/classifier bytes never invalidate delivery."""
    tree.inputs.parser_source.write_bytes(b"# SYNTHETIC changed parser\n")
    tree.inputs.taxonomy_source.write_bytes(b"# SYNTHETIC changed taxonomy\n")
    outcome = check(tree)
    assert outcome.findings == ()
    assert outcome.structural is False


def test_access_boundary(
    tree: PackageTree, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Record every open; block writes, environment, sockets and paragraphs."""
    before = snapshot(tree.root)
    allowed = {
        *(tree.inputs.output_dir / name for name in PACKAGE_FILES),
        tree.inputs.parse_report,
        tree.inputs.chunk_report,
        tree.inputs.embedding_report,
    }
    environment = RecordingEnvironment()
    opened: list[Path] = []
    originals = (builtins.open, io.open, os.open)

    def wrap(original: Any) -> Any:
        def guarded(
            file: Any, mode: Any = "r", *args: Any, **kwargs: Any
        ) -> Any:
            assert not isinstance(file, int)
            path = Path(file)
            opened.append(path)
            assert path in allowed
            if isinstance(mode, str):
                assert not set(mode) & set("wax+")
            else:
                assert not mode & (
                    os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC
                )
            return original(file, mode, *args, **kwargs)

        return guarded

    with monkeypatch.context() as patch:
        patch.setattr(os, "environ", environment)
        patch.setattr(builtins, "open", wrap(originals[0]))
        patch.setattr(io, "open", wrap(originals[1]))
        patch.setattr(os, "open", wrap(originals[2]))
        for name in (
            "write_bytes",
            "write_text",
            "mkdir",
            "unlink",
            "rename",
            "replace",
        ):
            patch.setattr(Path, name, forbidden)
        for name in ("replace", "rename", "remove", "unlink", "mkdir", "rmdir"):
            patch.setattr(os, name, forbidden)
        patch.setattr(socket, "socket", forbidden)
        patch.setattr(socket, "create_connection", forbidden)
        patch.setattr(chunk_validate, "validate_chunks", forbidden)
        outcome = check(tree)
    assert outcome.findings == ()
    assert outcome.structural is False
    assert set(opened) == allowed
    assert environment.accessed_keys == []
    assert snapshot(tree.root) == before


def test_deterministic_single_field_fuzz(tree: PackageTree) -> None:
    """Two hundred bounded random mutations never raise or leak values."""
    generator = random.Random(5004)
    names = ("papers.jsonl", "sections.jsonl", "chunks.jsonl")
    original = {name: read_artifact(tree, name) for name in names}
    raw = {name: artifact_path(tree, name).read_bytes() for name in names}
    values = (None, True, -1, 1.0, [], {}, "SYNTHETIC /private prose", "c" * 64)
    for _ in range(200):
        name = generator.choice(names)
        records = deepcopy(original[name])
        row = generator.choice(records)
        row[generator.choice(tuple(row))] = deepcopy(generator.choice(values))
        save_artifact(tree, name, records)
        outcome = check(tree)
        assert_safe(outcome.findings)
        assert isinstance(outcome.structural, bool)
        artifact_path(tree, name).write_bytes(raw[name])


@pytest.mark.parametrize(
    "path,value",
    [
        pytest.param(("dtype",), "synthetic", id="dtype"),
        pytest.param(("row_mapping",), "synthetic", id="row-mapping"),
        pytest.param(("normalization", "declared"), "synthetic", id="declared"),
    ],
)
def test_fixed_embedding_facts_are_structurally_gated(
    tree: PackageTree, path: tuple[str | int, ...], value: Any
) -> None:
    """Fixed embedding-set enums are rejected by the existing contract."""
    manifest = read_artifact(tree, "delivery_manifest.json")
    set_path(manifest["embedding_set"], path, value)
    save_artifact(tree, "delivery_manifest.json", manifest)
    outcome = check(tree)
    require(
        outcome,
        "delivery_manifest-bad-value",
        "delivery_manifest.json",
        structural=True,
    )
    assert "delivery-embedding-set-mismatch" not in {
        item.code for item in outcome.findings
    }


@pytest.mark.parametrize(
    "source,path",
    [
        pytest.param("parse_report.json", ("papers", 0, "doi"), id="parse-doi"),
        pytest.param(
            "parse_report.json", ("papers", 0, "xml_sha256"), id="parse-xml"
        ),
        pytest.param(
            "parse_report.json",
            ("papers", 0, "section_count"),
            id="parse-sections",
        ),
        pytest.param(
            "parse_report.json", ("summary", "succeeded"), id="parse-succeeded"
        ),
        pytest.param(
            "parse_report.json", ("summary", "failed"), id="parse-failed"
        ),
        pytest.param(
            "chunk_report.json",
            ("papers", 0, "section_count"),
            id="chunk-sections",
        ),
        pytest.param(
            "embedding_report.json", ("paper_count",), id="embedding-papers"
        ),
    ],
)
def test_missing_nested_report_fields(
    tree: PackageTree, source: str, path: tuple[str | int, ...]
) -> None:
    """Missing required nested fields produce structural report findings."""
    report = read_artifact(tree, source)
    parent = report
    for key in path[:-1]:
        parent = parent[key]
    del parent[path[-1]]
    save_artifact(tree, source, report)
    outcome = check(tree)
    assert outcome.structural is True
    assert_safe(outcome.findings)
    assert any(
        item.code == "report-structure" and set(item.ids) & {source, "report"}
        for item in outcome.findings
    )


def test_delivery_counts_preserve_record_units(tree: PackageTree) -> None:
    """Two defects in one row count once; equal indices in files differ."""
    sections = read_artifact(tree, "sections.jsonl")
    for section in sections[:2]:
        section.update(
            doi="10.1234/SYNTHETIC.MISSING",
            section_id="SYNTHETIC /private prose",
        )
    save_artifact(tree, "sections.jsonl", sections)
    chunks = read_artifact(tree, "chunks.jsonl")
    chunks[0].update(
        doi="10.1234/SYNTHETIC.MISSING",
        section_id="SYNTHETIC /private prose",
    )
    save_artifact(tree, "chunks.jsonl", chunks)
    finding = require(check(tree), "delivery-orphan-record", "sections.jsonl")
    assert finding.count == 3
    assert finding.ids == ("sections.jsonl", chunks[0]["chunk_id"])


def test_public_structure_and_loader_run_once(
    tree: PackageTree, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Load/check once and decode each report once in an ordinary call."""
    loader_spy = Mock(wraps=validate.load_package)
    structure_spy = Mock(wraps=validate.check_package_structure)
    decoder_spy = Mock(wraps=validate.decode_json)
    reports = [
        getattr(tree.inputs, name).read_bytes()
        for name in ("parse_report", "chunk_report", "embedding_report")
    ]
    with monkeypatch.context() as patch:
        patch.setattr(validate, "load_package", loader_spy)
        patch.setattr(validate, "check_package_structure", structure_spy)
        patch.setattr(validate, "decode_json", decoder_spy)
        outcome = check(tree)
    assert outcome.findings == ()
    loader_spy.assert_called_once_with(tree.inputs.output_dir)
    structure_spy.assert_called_once()
    for raw in reports:
        assert (
            sum(call.args == (raw,) for call in decoder_spy.call_args_list) == 1
        )
