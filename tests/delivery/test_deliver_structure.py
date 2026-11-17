"""SYNTHETIC offline T004 Phase 1 tests; behavior must remain RED."""

from __future__ import annotations

import builtins
import hashlib
import io
import os
import re
import socket
from collections.abc import Iterator
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from delivery_fixtures import MUTATIONS, Mutation
from jsonschema import Draft202012Validator
from package_fixtures import (
    PACKAGE_FILES,
    PAYLOADS,
    REPO,
    PackageTree,
    RecordingEnvironment,
    make_tree,
    read_json,
    rows,
    snapshot,
    symlinks_supported,
    write_json,
    write_rows,
)

from sciscope.chunking import validate as chunk_validate
from sciscope.chunking.validate import Finding
from sciscope.delivery import contract, package, validate
from sciscope.embedding import validate as embedding_validate

REPORTS = (
    "parse_report.json",
    "chunk_report.json",
    "embedding_report.json",
)
ENTITY_FILES = {
    "paper": "papers.jsonl",
    "section": "sections.jsonl",
    "chunk": "chunks.jsonl",
    "embedding_manifest": "embedding_manifest.json",
    "delivery_manifest": "delivery_manifest.json",
}
TEXT_FILES = tuple(ENTITY_FILES.values())
JSONL_FILES = TEXT_FILES[:3]
PARITY = tuple(
    case
    for case in MUTATIONS
    if case.entity in ENTITY_FILES and "DOCUMENTED-C3" not in case.name
)
SAFE_IDS = {*PACKAGE_FILES, *REPORTS, "manifest", "vectors", "report"}
SUFFIXES = (
    "missing-field",
    "extra-field",
    "bad-type",
    "bad-value",
    "bad-pattern",
)
STRUCTURE_CODES = {
    f"{entity}-{suffix}"
    for entity in (*ENTITY_FILES, "embedding_set")
    for suffix in SUFFIXES
}
FILE_CODES = {
    "delivery-missing-file",
    "delivery-extra-file",
    "delivery-not-regular-file",
    "invalid-utf8",
    "invalid-json",
    "duplicate-json-key",
    "delivery-integrity-mismatch",
    "delivery-count-mismatch",
    "source-report-mismatch",
    "vectors-size",
    "partial-set",
    "delivery-manifest-impure",
}
DECODING = (
    (b"\xef\xbb\xbf{}", "invalid-utf8"),
    (b"\xff", "invalid-utf8"),
    (b"{", "invalid-json"),
    (b'{"x":1,"x":2}', "duplicate-json-key"),
    (b'{"x":{"y":1,"y":2}}', "duplicate-json-key"),
    (b'{"x":NaN}', "invalid-json"),
    (b'{"x":Infinity}', "invalid-json"),
    (b'{"x":-Infinity}', "invalid-json"),
    (b'{"x":1e999}', "invalid-json"),
    (b"[" * 2000 + b"0" + b"]" * 2000, "invalid-json"),
)


def forbidden(*args: object, **kwargs: object) -> Any:
    """Reject forbidden access without using any real sensitive value."""
    raise AssertionError("SYNTHETIC forbidden access")


@pytest.fixture(autouse=True)
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Block sockets during setup, package construction, and validation."""
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


@pytest.fixture
def tree(tmp_path: Path) -> PackageTree:
    """Publish a valid SYNTHETIC package through the GREEN real delivery API."""
    result = make_tree(tmp_path)
    package.run_delivery(result.inputs)
    return result


def report_paths(tree: PackageTree) -> validate.PackageReports:
    """Use the three explicit fixture reports without default repository I/O."""
    return validate.PackageReports(
        tree.inputs.parse_report,
        tree.inputs.chunk_report,
        tree.inputs.embedding_report,
    )


def check(tree: PackageTree) -> validate.StructureOutcome:
    """Run the new API and check diagnostic safety for every returning case."""
    outcome = validate.check_package_structure(
        tree.inputs.output_dir, report_paths(tree)
    )
    assert type(outcome.findings) is tuple
    assert type(outcome.structural) is bool
    assert_safe(outcome.findings)
    return outcome


def assert_safe(findings: tuple[Finding, ...] | list[Finding]) -> None:
    """Require bounded safe codes/IDs, including on corrupt file contents."""
    assert [item.code for item in findings] == sorted(
        {item.code for item in findings}
    )
    for item in findings:
        assert item.code in FILE_CODES | STRUCTURE_CODES
        assert type(item.count) is int and item.count > 0
        assert 1 <= len(item.ids) <= 3
        assert len(item.ids) == len(set(item.ids))
        assert all(
            identifier in SAFE_IDS or re.fullmatch(r"[0-9a-f]{64}", identifier)
            for identifier in item.ids
        )


def require(
    outcome: validate.StructureOutcome, code: str, identifier: str
) -> Finding:
    """Find one trusted code and expected safe identifier."""
    finding = next(item for item in outcome.findings if item.code == code)
    assert identifier in finding.ids
    return finding


def edit_manifest(tree: PackageTree) -> tuple[Path, dict[str, Any]]:
    """Return the delivery manifest path and fresh controlled fixture data."""
    path = tree.inputs.output_dir / "delivery_manifest.json"
    return path, read_json(path)


def rewrite_record(tree: PackageTree, entity: str, value: Any) -> None:
    """Replace the first real row or whole manifest, preserving other rows."""
    path = tree.inputs.output_dir / ENTITY_FILES[entity]
    if entity in ("paper", "section", "chunk"):
        records = rows(path)
        records[0] = value
        write_rows(path, records)
    else:
        write_json(path, value)


def first_record(tree: PackageTree, entity: str) -> dict[str, Any]:
    """Read the first real emitted record rather than a standalone factory."""
    path = tree.inputs.output_dir / ENTITY_FILES[entity]
    return rows(path)[0] if path.suffix == ".jsonl" else read_json(path)


def test_valid_package_is_unchanged(tree: PackageTree) -> None:
    """Accept the real six-file package and retain exact reusable bytes."""
    before = snapshot(tree.root)
    outcome = check(tree)
    assert outcome.findings == ()
    assert outcome.structural is False
    assert dict(outcome.loaded.raw_files) == snapshot(tree.inputs.output_dir)
    for name in JSONL_FILES:
        assert outcome.loaded.records[name] == tuple(
            rows(tree.inputs.output_dir / name)
        )
    for name in TEXT_FILES[3:]:
        assert outcome.loaded.manifests[name] == read_json(
            tree.inputs.output_dir / name
        )
    assert snapshot(tree.root) == before


@pytest.mark.parametrize("name", (*PACKAGE_FILES, *REPORTS))
def test_missing_files(tree: PackageTree, name: str) -> None:
    """Detect each fixed payload/manifest/report absence independently."""
    path = (
        tree.inputs.output_dir / name
        if name in PACKAGE_FILES
        else getattr(tree.inputs, name.removesuffix(".json"))
    )
    path.unlink()
    outcome = check(tree)
    assert require(outcome, "delivery-missing-file", name).count == 1
    assert outcome.structural is True


@pytest.mark.parametrize(
    "name,is_directory",
    [
        ("SYNTHETIC-extra", False),
        ("SYNTHETIC-nested", True),
        (".SYNTHETIC-hidden", False),
        (".sciscope-delivery-stage-SYNTHETIC", True),
        (".sciscope-delivery-backup-SYNTHETIC", True),
    ],
)
def test_extra_entries(
    tree: PackageTree, name: str, is_directory: bool
) -> None:
    """Reject all extra top-level entries without exposing their names."""
    path = tree.inputs.output_dir / name
    if is_directory:
        path.mkdir()
        (path / "SYNTHETIC-private").write_bytes(b"SYNTHETIC value")
    else:
        path.write_bytes(b"SYNTHETIC prose")
    before = snapshot(tree.root)
    outcome = check(tree)
    require(outcome, "delivery-extra-file", "report")
    assert outcome.structural is True
    assert snapshot(tree.root) == before


@pytest.mark.parametrize("name", (*PACKAGE_FILES, *REPORTS))
def test_directory_at_fixed_name(tree: PackageTree, name: str) -> None:
    """Treat directories as nonregular, including repository reports."""
    path = (
        tree.inputs.output_dir / name
        if name in PACKAGE_FILES
        else getattr(tree.inputs, name.removesuffix(".json"))
    )
    path.unlink()
    path.mkdir()
    outcome = check(tree)
    code = (
        "delivery-not-regular-file"
        if name in PACKAGE_FILES
        else "delivery-missing-file"
    )
    require(outcome, code, name)
    assert outcome.structural is True


@pytest.mark.skipif(
    not symlinks_supported(), reason="Symlink privilege unavailable"
)
def test_symlinks_are_never_followed(
    tree: PackageTree, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject fixed-file, report, dangling and extra links without following."""
    original = Path.open
    for index, name in enumerate((*PACKAGE_FILES, *REPORTS)):
        path = (
            tree.inputs.output_dir / name
            if name in PACKAGE_FILES
            else getattr(tree.inputs, name.removesuffix(".json"))
        )
        raw = path.read_bytes()
        path.unlink()
        target = tree.root / f"SYNTHETIC-target-{index}"
        target.write_bytes(raw)
        path.symlink_to(target)

        def guarded(
            self: Path,
            *args: Any,
            blocked: tuple[Path, Path] = (path, target),
            **kwargs: Any,
        ) -> Any:
            assert self not in blocked
            return original(self, *args, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(Path, "open", guarded)
            outcome = check(tree)
        require(
            outcome,
            "delivery-not-regular-file"
            if name in PACKAGE_FILES
            else "delivery-missing-file",
            name,
        )
        assert outcome.structural is True
        assert target.read_bytes() == raw
        path.unlink()
        path.write_bytes(raw)
    extra = tree.inputs.output_dir / "SYNTHETIC-link"
    extra.symlink_to(tree.root / "SYNTHETIC-absent")
    require(check(tree), "delivery-extra-file", "report")
    fixed = tree.inputs.output_dir / "papers.jsonl"
    fixed.unlink()
    fixed.symlink_to(tree.root / "SYNTHETIC-absent")
    require(check(tree), "delivery-not-regular-file", "papers.jsonl")


@pytest.mark.parametrize("name", TEXT_FILES)
@pytest.mark.parametrize("raw,code", DECODING)
def test_decoding_matrix(
    tree: PackageTree, name: str, raw: bytes, code: str
) -> None:
    """Collect strict decoder findings for every textual package file."""
    (tree.inputs.output_dir / name).write_bytes(raw + b"\n")
    outcome = check(tree)
    require(outcome, code, name)
    assert outcome.structural is True


@pytest.mark.parametrize("raw,code", DECODING)
def test_public_decoder_never_raises(raw: bytes, code: str) -> None:
    """Return safe decoder codes rather than exception text or raw values."""
    value, codes = validate.decode_json(raw)
    assert value is None
    assert codes == (code,)


@pytest.mark.parametrize(
    "raw,expected",
    [
        (b"null", None),
        (b"{}\r\n", {}),
        (b"[1,true]", [1, True]),
        (
            '"SYNTHETIC\u0085\u2028\u2029"'.encode(),
            "SYNTHETIC\u0085\u2028\u2029",
        ),
    ],
)
def test_public_decoder_valid_values(raw: bytes, expected: object) -> None:
    """Distinguish successful JSON null from a sanitized decoding failure."""
    assert validate.decode_json(raw) == (expected, ())


@pytest.mark.parametrize("name", JSONL_FILES)
@pytest.mark.parametrize("separator", [b"\n\n", b"\n \n", b"\n\r\n"])
def test_interior_blank_lines(
    tree: PackageTree, name: str, separator: bytes
) -> None:
    """Reject empty or whitespace-only physical records between real rows."""
    path = tree.inputs.output_dir / name
    first, rest = path.read_bytes().split(b"\n", 1)
    path.write_bytes(first + separator + rest)
    outcome = check(tree)
    require(outcome, "invalid-json", name)
    assert outcome.structural is True


@pytest.mark.parametrize("name", TEXT_FILES)
@pytest.mark.parametrize("ending", [b"", b"\n", b"\r\n"])
def test_valid_line_endings(
    tree: PackageTree, name: str, ending: bytes
) -> None:
    """Allow final-LF variants and JSON whitespace CR without splitlines."""
    path = tree.inputs.output_dir / name
    path.write_bytes(path.read_bytes().rstrip(b"\n") + ending)
    outcome = check(tree)
    assert outcome.structural is False
    assert not {item.code for item in outcome.findings} & {
        "invalid-json",
        "invalid-utf8",
        "duplicate-json-key",
    }


@pytest.mark.parametrize("name", JSONL_FILES)
def test_crlf_between_records(tree: PackageTree, name: str) -> None:
    """Keep CR as legal JSON trailing whitespace on every LF-delimited row."""
    path = tree.inputs.output_dir / name
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    outcome = check(tree)
    assert outcome.structural is False
    assert outcome.loaded.records[name] == tuple(rows(path))


@pytest.mark.parametrize("name", JSONL_FILES)
@pytest.mark.parametrize("defect", ["two-final-lf", "cr-only-separator"])
def test_only_lf_delimits_records(
    tree: PackageTree, name: str, defect: str
) -> None:
    """Reject a second final blank row and CR used as a record delimiter."""
    path = tree.inputs.output_dir / name
    raw = path.read_bytes()
    path.write_bytes(
        raw + b"\n" if defect == "two-final-lf" else raw.replace(b"\n", b"\r")
    )
    outcome = check(tree)
    require(outcome, "invalid-json", name)
    assert outcome.structural is True


@pytest.mark.parametrize("raw", [b'"SYNTHETIC\rvalue"', b'"SYNTHETIC\nvalue"'])
def test_raw_control_inside_string_is_invalid(raw: bytes) -> None:
    """CR and LF are legal JSON whitespace only outside a string."""
    assert validate.decode_json(raw) == (None, ("invalid-json",))


@pytest.mark.parametrize("name", TEXT_FILES)
def test_unicode_separators_survive(tree: PackageTree, name: str) -> None:
    """Preserve raw U+0085/U+2028/U+2029 in JSON strings in every file kind."""
    entity = next(key for key, value in ENTITY_FILES.items() if value == name)
    record = first_record(tree, entity)
    marker = "SYNTHETIC\u0085\u2028\u2029"
    if entity in ("paper", "section"):
        record["title"] = marker
    elif entity == "chunk":
        record["text"] = marker
    elif entity == "embedding_manifest":
        record["model"] = marker
    else:
        record["embedding_set"]["model"] = marker
    rewrite_record(tree, entity, record)
    loaded, findings = validate.load_package(tree.inputs.output_dir)
    assert findings == []
    actual = (
        loaded.records[name][0]
        if name in JSONL_FILES
        else loaded.manifests[name]
    )
    assert actual == record


@pytest.mark.parametrize("name", JSONL_FILES)
def test_empty_jsonl_parses(tree: PackageTree, name: str) -> None:
    """Parse empty JSONL; descriptor/count mismatches may remain."""
    (tree.inputs.output_dir / name).write_bytes(b"")
    outcome = check(tree)
    assert outcome.structural is False
    assert outcome.loaded.records[name] == ()
    assert all(item.code not in STRUCTURE_CODES for item in outcome.findings)


@pytest.mark.parametrize("name", TEXT_FILES[3:])
@pytest.mark.parametrize("raw", [b"", b"{}\n{}", b"[]", b"null"])
def test_manifest_requires_single_object(
    tree: PackageTree, name: str, raw: bytes
) -> None:
    """Reject empty/multiple JSON documents and non-object manifest roots."""
    (tree.inputs.output_dir / name).write_bytes(raw)
    outcome = check(tree)
    entity = name.removesuffix(".json")
    require(
        outcome,
        "invalid-json" if raw in (b"", b"{}\n{}") else entity + "-bad-type",
        name,
    )
    assert outcome.structural is True


@pytest.mark.parametrize("entity", tuple(ENTITY_FILES))
@pytest.mark.parametrize("bad", [None, [], "SYNTHETIC /private/value", 1, True])
def test_non_object_records(tree: PackageTree, entity: str, bad: Any) -> None:
    """Report the unchanged Group A type code for every record-file kind."""
    rewrite_record(tree, entity, bad)
    outcome = check(tree)
    require(outcome, entity + "-bad-type", ENTITY_FILES[entity])
    assert outcome.structural is True


@pytest.mark.parametrize("entity", tuple(ENTITY_FILES))
def test_every_record_is_checked(tree: PackageTree, entity: str) -> None:
    """Count independent record units once per code, never per bad field."""
    record = first_record(tree, entity)
    record["SYNTHETIC-extra"] = "SYNTHETIC /private prose"
    if entity in ("paper", "section", "chunk"):
        path = tree.inputs.output_dir / ENTITY_FILES[entity]
        write_rows(path, [first_record(tree, entity), record, deepcopy(record)])
    else:
        rewrite_record(tree, entity, record)
    outcome = check(tree)
    finding = require(outcome, entity + "-extra-field", ENTITY_FILES[entity])
    assert finding.count == (
        3 - 1 if entity in ("paper", "section", "chunk") else 1
    )
    assert outcome.structural is True


@pytest.mark.parametrize("entity", tuple(ENTITY_FILES))
def test_contract_codes_pass_through(
    tree: PackageTree, monkeypatch: pytest.MonkeyPatch, entity: str
) -> None:
    """Call each public Group A checker on every row, preserving its codes."""
    expected = (
        tuple(rows(tree.inputs.output_dir / ENTITY_FILES[entity]))
        if entity in ("paper", "section", "chunk")
        else (first_record(tree, entity),)
    )
    calls = []
    codes = (entity + "-bad-pattern", entity + "-bad-value")

    def record(value: object) -> tuple[str, ...]:
        calls.append(deepcopy(value))
        return codes

    monkeypatch.setattr(contract, "check_" + entity, record)
    outcome = check(tree)
    assert tuple(calls) == expected
    for code in codes:
        assert require(outcome, code, ENTITY_FILES[entity]).count == len(
            expected
        )
    assert outcome.structural is True


@pytest.mark.parametrize("name", PAYLOADS)
@pytest.mark.parametrize("field", ["sha256", "bytes", "record_count"])
def test_payload_descriptor_facts(
    tree: PackageTree, name: str, field: str
) -> None:
    """Check each descriptor field against actual bytes/physical row counts."""
    path, manifest = edit_manifest(tree)
    value = manifest["files"][name][field]
    manifest["files"][name][field] = (
        "0" * 64 if field == "sha256" else value + 1
    )
    write_json(path, manifest)
    outcome = check(tree)
    require(outcome, "delivery-integrity-mismatch", name)
    assert outcome.structural is False


@pytest.mark.parametrize("name", REPORTS)
@pytest.mark.parametrize("field", ["sha256", "bytes"])
def test_report_descriptor_facts(
    tree: PackageTree, name: str, field: str
) -> None:
    """Compare every report descriptor as bytes without report-content joins."""
    path, manifest = edit_manifest(tree)
    value = manifest["source_reports"][name][field]
    manifest["source_reports"][name][field] = (
        "0" * 64 if field == "sha256" else value + 1
    )
    write_json(path, manifest)
    outcome = check(tree)
    require(outcome, "source-report-mismatch", name)
    assert outcome.structural is False


@pytest.mark.parametrize("name", REPORTS)
def test_reports_are_opaque_bytes(tree: PackageTree, name: str) -> None:
    """Do not parse report contents even when bytes are not JSON or UTF-8."""
    report = getattr(tree.inputs, name.removesuffix(".json"))
    raw = b"\xffSYNTHETIC opaque report bytes"
    report.write_bytes(raw)
    path, manifest = edit_manifest(tree)
    manifest["source_reports"][name] = {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
    }
    write_json(path, manifest)
    outcome = check(tree)
    assert outcome.findings == ()
    assert outcome.structural is False


@pytest.mark.parametrize("field", ["papers", "sections", "chunks"])
def test_counts(tree: PackageTree, field: str) -> None:
    """Compare three manifest counts only with physical JSONL counts."""
    path, manifest = edit_manifest(tree)
    manifest["counts"][field] += 1
    write_json(path, manifest)
    outcome = check(tree)
    require(outcome, "delivery-count-mismatch", field + ".jsonl")
    assert outcome.structural is False


@pytest.mark.parametrize("field", ["chunks_sha256", "vectors_sha256"])
def test_embedding_set_digests(tree: PackageTree, field: str) -> None:
    """Compare set digests with bytes independently of payload metadata."""
    path, manifest = edit_manifest(tree)
    manifest["embedding_set"][field] = "0" * 64
    write_json(path, manifest)
    outcome = check(tree)
    require(
        outcome,
        "delivery-integrity-mismatch",
        "chunks.jsonl" if field == "chunks_sha256" else "vectors.f32",
    )
    assert outcome.structural is False


@pytest.mark.parametrize("defect", ["truncated-row", "fragment", "dimensions"])
def test_vector_size_shape(tree: PackageTree, defect: str) -> None:
    """Detect short rows, trailing fragments and descriptor dimension shape."""
    vector = tree.inputs.output_dir / "vectors.f32"
    if defect == "dimensions":
        path, manifest = edit_manifest(tree)
        manifest["embedding_set"]["dimensions"] += 1
        write_json(path, manifest)
    else:
        raw = vector.read_bytes()
        vector.write_bytes(
            raw[:-4] if defect == "truncated-row" else raw + b"x"
        )
    outcome = check(tree)
    require(outcome, "vectors-size", "vectors")
    assert outcome.structural is False


def test_partial_marker(tree: PackageTree) -> None:
    """Reject partial status independently of T005 set membership checks."""
    path = tree.inputs.output_dir / "embedding_manifest.json"
    manifest = read_json(path)
    manifest["status"] = "partial"
    write_json(path, manifest)
    outcome = check(tree)
    require(outcome, "partial-set", "manifest")
    assert outcome.structural is False


@pytest.mark.parametrize(
    "location",
    [("embedding_set", "model"), ("processing_versions", "parser", "version")],
)
@pytest.mark.parametrize(
    "value",
    [
        "SYNTHETIC prose with spaces",
        "/SYNTHETIC/private",
        "SYNTHETIC\\private",
        "C:SYNTHETIC",
        "C:\\SYNTHETIC\\private",
        "SYNTHETIC..private",
        "SYNTHETIC\tvalue",
        "SYNTHETIC\nvalue",
        "SYNTHETIC\x00value",
        "SYNTHETIC\x7fvalue",
        "SYNTHETIC\x85value",
        "SYNTHETIC\u2028value",
        "x" * 129,
    ],
)
def test_manifest_purity(
    tree: PackageTree, location: tuple[str, ...], value: str
) -> None:
    """Detect prose/path/token violations without secret scanning."""
    path, manifest = edit_manifest(tree)
    target = manifest
    for key in location[:-1]:
        target = target[key]
    target[location[-1]] = value
    write_json(path, manifest)
    outcome = check(tree)
    require(outcome, "delivery-manifest-impure", "manifest")
    assert outcome.structural is True


@pytest.mark.parametrize("field", ["passage_prefix", "query_prefix"])
@pytest.mark.parametrize(
    "value,accepted",
    [
        ("SYNTHETIC prefix: ", True),
        (" " * 64, True),
        ("x" * 65, False),
        ("SYNTHETIC\t", False),
        ("SYNTHETIC\x85", False),
    ],
)
def test_prefix_purity_exceptions(
    tree: PackageTree, field: str, value: str, accepted: bool
) -> None:
    """Allow prefix spaces up to 64 characters while rejecting controls."""
    path, manifest = edit_manifest(tree)
    manifest["embedding_set"][field] = value
    write_json(path, manifest)
    outcome = check(tree)
    impure = any(
        item.code == "delivery-manifest-impure" for item in outcome.findings
    )
    assert impure is not accepted
    assert outcome.structural is not accepted
    if accepted:
        assert outcome.findings == ()


def test_hex_digests_and_token_boundary(tree: PackageTree) -> None:
    """Accept all real digest strings and the inclusive 128-char token bound."""
    path, manifest = edit_manifest(tree)
    manifest["embedding_set"]["model"] = "a" * 128
    write_json(path, manifest)
    outcome = check(tree)
    assert outcome.findings == ()
    assert outcome.structural is False


def test_independent_failures_and_failed_parse_retention(
    tree: PackageTree,
) -> None:
    """One corrupt file must never hide other independent findings."""
    root = tree.inputs.output_dir
    (root / "papers.jsonl").write_bytes(b"\xffSYNTHETIC /private prose")
    (root / "sections.jsonl").write_bytes(b"{}\n")
    (root / "chunks.jsonl").unlink()
    (root / "SYNTHETIC-extra").write_bytes(b"SYNTHETIC prose")
    tree.inputs.parse_report.unlink()
    vector = root / "vectors.f32"
    vector.write_bytes(vector.read_bytes() + b"x")
    outcome = check(tree)
    for code, identifier in (
        ("invalid-utf8", "papers.jsonl"),
        ("section-missing-field", "sections.jsonl"),
        ("delivery-missing-file", "chunks.jsonl"),
        ("delivery-missing-file", "parse_report.json"),
        ("delivery-extra-file", "report"),
        ("vectors-size", "vectors"),
    ):
        require(outcome, code, identifier)
    assert outcome.structural is True
    assert "papers.jsonl" not in outcome.loaded.records
    assert "chunks.jsonl" not in outcome.loaded.raw_files
    assert outcome.loaded.records["sections.jsonl"] == ({},)
    assert set(outcome.loaded.manifests) == set(TEXT_FILES[3:])


def test_bad_manifest_gates_descriptor_checks(tree: PackageTree) -> None:
    """Do not use invalid manifest facts for cascading descriptor findings."""
    path, manifest = edit_manifest(tree)
    manifest["embedding_set"]["dimensions"] = True
    write_json(path, manifest)
    vector = tree.inputs.output_dir / "vectors.f32"
    vector.write_bytes(b"x")
    outcome = check(tree)
    require(outcome, "delivery_manifest-bad-type", "delivery_manifest.json")
    assert outcome.structural is True
    assert not {item.code for item in outcome.findings} & {
        "delivery-integrity-mismatch",
        "delivery-count-mismatch",
        "source-report-mismatch",
        "vectors-size",
    }


def test_collector_safe_ids_codes_and_units() -> None:
    """Sanitize untrusted IDs/codes and count file/index pairs, not fields."""
    collector = validate.DeliveryFindingCollector()
    for index, identifier in enumerate(sorted(SAFE_IDS)):
        collector.add("invalid-json", identifier, ("papers.jsonl", index))
        collector.add("invalid-json", identifier, ("papers.jsonl", index))
    for index, identifier in enumerate(
        ("a" * 64, "A" * 64, "/SYNTHETIC/private", "SYNTHETIC prose"), 100
    ):
        collector.add("duplicate-json-key", identifier, ("chunks.jsonl", index))
    collector.add("SYNTHETIC /private code", "SYNTHETIC prose", ("manifest", 0))
    findings = collector.findings()
    assert_safe(findings)
    by_code = {item.code: item for item in findings}
    assert by_code["invalid-json"].count == len(SAFE_IDS) + 1
    assert by_code["duplicate-json-key"] == Finding(
        "duplicate-json-key", 4, ("a" * 64, "report")
    )
    assert "SYNTHETIC" not in repr(findings)


@pytest.mark.parametrize("identifier", sorted(SAFE_IDS) + ["a" * 64])
def test_collector_retains_each_allowed_id(identifier: str) -> None:
    """Keep every fixed basename/token and lowercase digest, without masking."""
    collector = validate.DeliveryFindingCollector()
    collector.add("invalid-json", identifier, ("papers.jsonl", 0))
    assert collector.findings() == [Finding("invalid-json", 1, (identifier,))]


def test_collector_counts_file_and_index() -> None:
    """Equal indices in different files remain independent failing units."""
    collector = validate.DeliveryFindingCollector()
    for name in JSONL_FILES:
        for index in (0, 1):
            collector.add("invalid-json", name, (name, index))
            collector.add("invalid-json", name, (name, index))
    assert collector.findings() == [Finding("invalid-json", 6, JSONL_FILES)]


def test_loader_reuse_parses_nothing_twice(
    tree: PackageTree, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pass exact load results through validation for later T005 reuse."""
    loaded, findings = validate.load_package(tree.inputs.output_dir)
    with monkeypatch.context() as patch:
        patch.setattr(validate, "load_package", forbidden)
        patch.setattr(validate, "decode_json", forbidden)
        outcome = validate.check_package_structure(
            tree.inputs.output_dir,
            report_paths(tree),
            loaded=loaded,
            load_findings=tuple(findings),
        )
    assert outcome.loaded is loaded
    assert outcome.findings == ()
    assert outcome.structural is False


def test_loader_reuse_preserves_structural_findings(tree: PackageTree) -> None:
    """Carry failed-load findings into the combined outcome with precedence."""
    (tree.inputs.output_dir / "papers.jsonl").write_bytes(b"\xff")
    loaded, findings = validate.load_package(tree.inputs.output_dir)
    outcome = validate.check_package_structure(
        tree.inputs.output_dir,
        report_paths(tree),
        loaded=loaded,
        load_findings=tuple(findings),
    )
    require(outcome, "invalid-utf8", "papers.jsonl")
    assert outcome.loaded is loaded
    assert outcome.structural is True


def test_offline_read_only_access_boundary(
    tree: PackageTree, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Read only package/reports without env/cache/XML/paragraphs or writes."""
    before = snapshot(tree.root)
    environment = RecordingEnvironment()
    allowed = {
        *(tree.inputs.output_dir / name for name in PACKAGE_FILES),
        tree.inputs.parse_report,
        tree.inputs.chunk_report,
        tree.inputs.embedding_report,
    }
    opens = (builtins.open, io.open, os.open)

    def guarded_open(
        original: Any, file: Any, mode: Any = "r", *args: Any, **kwargs: Any
    ) -> Any:
        assert not isinstance(file, int)
        assert Path(file) in allowed
        if isinstance(mode, str):
            assert not set(mode) & set("wax+")
        else:
            assert not mode & (
                os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC
            )
        return original(file, mode, *args, **kwargs)

    def wrap(original: Any) -> Any:
        return lambda *args, **kwargs: guarded_open(original, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(os, "environ", environment)
        patch.setattr(builtins, "open", wrap(opens[0]))
        patch.setattr(io, "open", wrap(opens[1]))
        patch.setattr(os, "open", wrap(opens[2]))
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
        patch.setattr(embedding_validate, "validate_embedding_set", forbidden)
        patch.setattr(
            embedding_validate, "validate_embedding_structure", forbidden
        )
        patch.setattr(chunk_validate, "validate_chunks", forbidden)
        outcome = check(tree)
    assert environment.accessed_keys == []
    assert outcome.findings == ()
    assert snapshot(tree.root) == before


def object_nodes(value: object) -> Iterator[dict[str, Any]]:
    """Walk controlled schema data to verify local references before use."""
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from object_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from object_nodes(child)


@pytest.mark.parametrize(
    "mutation", PARITY, ids=lambda item: f"{item.entity}-{item.name}"
)
def test_file_schema_runtime_parity(
    tree: PackageTree, mutation: Mutation
) -> None:
    """Mutate published records and compare all three structural verdicts."""
    record = first_record(tree, mutation.entity)
    mutation.apply(record)
    rewrite_record(tree, mutation.entity, record)
    outcome = check(tree)
    prefix = mutation.entity + "-"
    file_rejects = any(
        item.code.startswith(prefix) for item in outcome.findings
    )
    assert file_rejects is not mutation.runtime_accepts
    checker = getattr(contract, "check_" + mutation.entity)
    assert (not checker(record)) is mutation.runtime_accepts
    schema = read_json(REPO / "docs/DATA_CONTRACT.json")
    assert all(
        node["$ref"].startswith("#/$defs/")
        for node in object_nodes(schema)
        if "$ref" in node
    )
    wrapped = (
        schema
        if mutation.entity == "delivery_manifest"
        else {
            "$schema": schema["$schema"],
            "$ref": f"#/$defs/{mutation.entity}",
            "$defs": schema["$defs"],
        }
    )
    Draft202012Validator.check_schema(wrapped)
    assert (
        Draft202012Validator(wrapped).is_valid(record)
        is mutation.runtime_accepts
    )
