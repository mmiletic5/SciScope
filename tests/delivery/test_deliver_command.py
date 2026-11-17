"""SYNTHETIC offline Group E Phase 1 command and staging behavior tests."""

from __future__ import annotations

import builtins
import io
import os
import shutil
import socket
import struct
from copy import deepcopy
from pathlib import Path
from typing import Any
from unittest.mock import Mock

import pytest
from package_fixtures import (
    PACKAGE_FILES,
    PackageTree,
    RecordingEnvironment,
    read_json,
    rows,
    snapshot,
    write_rows,
)
from validate_fixtures import (
    artifact_path,
    check,
    delivered_tree,
    forbidden,
    read_artifact,
    report_paths,
    save_artifact,
    set_path,
)

from sciscope.chunking.config import ConfigError
from sciscope.chunking.validate import Finding
from sciscope.delivery import package, publish, validate
from sciscope.pipeline import cli

OPTIONS = ("package-dir", "parse-report", "chunk-report", "embedding-report")
SUCCESS = (
    "validated delivery papers: 2 sections: 3 chunks: 2 vectors: 2 "
    "files: 6 failures: 0\n"
)
USAGE_ERROR = "error: invalid-usage count: 1 first: report\nfailures: 1\n"
PRIVATE = "SYNTHETIC /private prose"


@pytest.fixture(autouse=True)
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent network access during setup as well as command execution."""
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


@pytest.fixture
def tree(tmp_path: Path) -> PackageTree:
    """Publish actual writer output using disposable provenance sources."""
    return delivered_tree(tmp_path)


def arguments(tree: PackageTree) -> list[str]:
    """Use all four explicit receiver paths, never default repository data."""
    return [
        "validate-delivery",
        "--package-dir",
        str(tree.inputs.output_dir),
        "--parse-report",
        str(tree.inputs.parse_report),
        "--chunk-report",
        str(tree.inputs.chunk_report),
        "--embedding-report",
        str(tree.inputs.embedding_report),
    ]


def diagnostics(findings: tuple[Finding, ...]) -> str:
    """Render already merged library findings independently of CLI helpers."""
    return (
        "".join(
            f"error: {item.code} count: {item.count} "
            f"first: {','.join(item.ids)}\n"
            for item in sorted(findings, key=lambda item: item.code)
        )
        + f"failures: {sum(item.count for item in findings)}\n"
    )


def assert_private(
    captured: pytest.CaptureResult[str], tree: PackageTree
) -> None:
    """Exclude invented prose, DOI and filesystem paths from diagnostics."""
    combined = captured.out + captured.err
    for value in ("SYNTHETIC", "/private", "prose", "10.1234/", str(tree.root)):
        assert value not in combined


def assert_corrupt(
    tree: PackageTree,
    capsys: pytest.CaptureFixture[str],
    code: str,
    status: int,
) -> None:
    """Require the target defect, complete diagnostics and unchanged bytes."""
    before = snapshot(tree.root)
    outcome = check(tree)
    assert code in {item.code for item in outcome.findings}
    assert outcome.structural is (status == 2)
    assert cli.main(arguments(tree)) == status
    captured = capsys.readouterr()
    assert captured == ("", diagnostics(outcome.findings))
    assert_private(captured, tree)
    assert snapshot(tree.root) == before


@pytest.mark.parametrize("help_option", ["--help", "-h"])
def test_help(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    help_option: str,
) -> None:
    """Help succeeds without a package, argparse, environment or validator."""
    environment = RecordingEnvironment()
    monkeypatch.setattr(cli, "_parser", forbidden)
    monkeypatch.setattr(validate, "validate_package", forbidden)
    with monkeypatch.context() as patch:
        patch.setattr(os, "environ", environment)
        assert (
            cli.main(["validate-delivery", help_option], environ=environment)
            == 0
        )
    assert capsys.readouterr() == (
        "usage: validate-delivery "
        + " ".join(f"[--{option} PATH]" for option in OPTIONS)
        + "\n",
        "",
    )
    assert environment.accessed_keys == []


@pytest.mark.parametrize("option", OPTIONS)
@pytest.mark.parametrize("spelling", ["space", "equals"])
def test_each_option_spelling(
    tree: PackageTree,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    option: str,
    spelling: str,
) -> None:
    """Each individual override preserves defaults of all other options."""
    defaults = package.DeliveryInputs()
    paths = {
        "package-dir": defaults.output_dir,
        "parse-report": defaults.parse_report,
        "chunk-report": defaults.chunk_report,
        "embedding-report": defaults.embedding_report,
    }
    target = tree.root / "SYNTHETIC path with spaces"
    paths[option] = target
    spy = Mock(return_value=check(tree))
    monkeypatch.setattr(validate, "validate_package", spy)
    monkeypatch.setattr(cli, "_parser", forbidden)
    tokens = (
        [f"--{option}", str(target)]
        if spelling == "space"
        else [f"--{option}={target}"]
    )
    assert cli.main(["validate-delivery", *tokens]) == 0
    spy.assert_called_once_with(
        paths["package-dir"],
        validate.PackageReports(
            paths["parse-report"],
            paths["chunk-report"],
            paths["embedding-report"],
        ),
    )
    assert capsys.readouterr() == (SUCCESS, "")


@pytest.mark.parametrize("option", OPTIONS)
@pytest.mark.parametrize(
    "kind",
    [
        "missing",
        "next-option",
        "empty",
        "empty-space",
        "repeat-space",
        "repeat-equals",
        "repeat-mixed",
    ],
)
def test_invalid_option_values(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    option: str,
    kind: str,
) -> None:
    """Reject missing/empty values and every duplicate spelling before I/O."""
    flag = "--" + option
    tokens = {
        "missing": [flag],
        "next-option": [flag, "--parse-report"],
        "empty": [flag + "="],
        "empty-space": [flag, ""],
        "repeat-space": [flag, PRIVATE, flag, PRIVATE],
        "repeat-equals": [flag + "=" + PRIVATE, flag + "=" + PRIVATE],
        "repeat-mixed": [flag, PRIVATE, flag + "=" + PRIVATE],
    }[kind]
    monkeypatch.setattr(validate, "validate_package", forbidden)
    monkeypatch.setattr(cli, "_parser", forbidden)
    assert cli.main(["validate-delivery", *tokens]) == 2
    assert capsys.readouterr() == ("", USAGE_ERROR)


@pytest.mark.parametrize(
    "tokens",
    [
        pytest.param(["--unknown", PRIVATE], id="unknown"),
        pytest.param(["--package", PRIVATE], id="abbreviation"),
        pytest.param(["--allow-partial"], id="partial"),
        pytest.param(["--operational-cap-tokens", "384"], id="cap"),
        pytest.param(["--norm-tolerance=0.01"], id="tolerance"),
        pytest.param([PRIVATE], id="positional"),
    ],
)
def test_unknown_options(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tokens: list[str],
) -> None:
    """No flags beyond the four exact options and help are accepted."""
    monkeypatch.setattr(validate, "validate_package", forbidden)
    assert cli.main(["validate-delivery", *tokens]) == 2
    assert capsys.readouterr() == ("", USAGE_ERROR)


def test_default_paths(
    tree: PackageTree,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Resolve actual defaults inside an isolated SYNTHETIC checkout."""
    defaults = package.DeliveryInputs()
    destination = tree.root / defaults.output_dir
    shutil.copytree(tree.inputs.output_dir, destination)
    for field in ("parse_report", "chunk_report", "embedding_report"):
        target = tree.root / getattr(defaults, field)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(getattr(tree.inputs, field), target)
    monkeypatch.chdir(tree.root)
    before = snapshot(tree.root)
    assert cli.main(["validate-delivery"]) == 0
    assert capsys.readouterr() == (SUCCESS, "")
    assert snapshot(tree.root) == before


def test_success_uses_validated_manifest_once(
    tree: PackageTree,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Read numeric counts from the returned validated manifest only."""
    outcome = check(tree)
    loaded_manifests = deepcopy(dict(outcome.loaded.manifests))
    manifest = loaded_manifests["delivery_manifest.json"]
    manifest["counts"] = {"papers": 7, "sections": 11, "chunks": 13}
    manifest["files"]["vectors.f32"]["record_count"] = 17
    loaded = validate.LoadedPackage({}, {}, loaded_manifests)
    spy = Mock(return_value=validate.ValidationOutcome((), False, loaded))
    monkeypatch.setattr(validate, "validate_package", spy)
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", forbidden)
        patch.setattr(io, "open", forbidden)
        patch.setattr(os, "open", forbidden)
        assert cli.main(arguments(tree)) == 0
    spy.assert_called_once_with(tree.inputs.output_dir, report_paths(tree))
    assert capsys.readouterr() == (
        "validated delivery papers: 7 sections: 11 chunks: 13 vectors: 17 "
        "files: 6 failures: 0\n",
        "",
    )


@pytest.mark.parametrize("implicit", [False, True], ids=["argv", "sys-argv"])
def test_actual_success(
    tree: PackageTree,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    implicit: bool,
) -> None:
    """Valid actual manifest counts produce precisely one success line."""
    monkeypatch.setattr(cli.sys, "argv", ["SYNTHETIC", *arguments(tree)])
    assert cli.main(None if implicit else arguments(tree)) == 0
    assert capsys.readouterr() == (SUCCESS, "")


@pytest.mark.parametrize("kind", ["missing", "extra", "directory"])
def test_inventory(
    tree: PackageTree, capsys: pytest.CaptureFixture[str], kind: str
) -> None:
    """Reject missing, additional and nonregular package entries."""
    path = artifact_path(tree, "papers.jsonl")
    if kind == "extra":
        (tree.inputs.output_dir / "SYNTHETIC extra").write_bytes(b"SYNTHETIC")
        code = "delivery-extra-file"
    else:
        path.unlink()
        if kind == "directory":
            path.mkdir()
        code = (
            "delivery-missing-file"
            if kind == "missing"
            else "delivery-not-regular-file"
        )
    assert_corrupt(tree, capsys, code, 2)


@pytest.mark.parametrize(
    "name", [*PACKAGE_FILES[:3], *PACKAGE_FILES[4:], *validate.REPORT_FILES]
)
@pytest.mark.parametrize(
    "raw,code",
    [
        pytest.param(b"\xef\xbb\xbf{}\n", "invalid-utf8", id="bom"),
        pytest.param(b"\xff\n", "invalid-utf8", id="utf8"),
        pytest.param(b"{\n", "invalid-json", id="json"),
        pytest.param(b'{"x":1,"x":2}\n', "duplicate-json-key", id="duplicate"),
    ],
)
def test_text_decoding(
    tree: PackageTree,
    capsys: pytest.CaptureFixture[str],
    name: str,
    raw: bytes,
    code: str,
) -> None:
    """Exercise every package text file and report through the command."""
    artifact_path(tree, name).write_bytes(raw)
    assert_corrupt(tree, capsys, code, 2)


@pytest.mark.parametrize(
    "name,path,value,code,status",
    [
        pytest.param(
            "chunks.jsonl",
            (0, "ordinal"),
            PRIVATE,
            "chunk-bad-type",
            2,
            id="structure",
        ),
        pytest.param(
            "sections.jsonl",
            (0, "doi"),
            "10.1234/synthetic.missing",
            "delivery-orphan-record",
            1,
            id="orphan",
        ),
        pytest.param(
            "sections.jsonl",
            (0, "parent_section_id"),
            PRIVATE,
            "delivery-parent-invalid",
            1,
            id="parent",
        ),
        pytest.param(
            "sections.jsonl",
            (0, "depth"),
            2,
            "delivery-section-structure-mismatch",
            1,
            id="section",
        ),
        pytest.param(
            "sections.jsonl",
            (0, "xml_sha256"),
            "c" * 64,
            "delivery-xml-sha-mismatch",
            1,
            id="xml",
        ),
        pytest.param(
            "sections.jsonl",
            (0, "source_locator"),
            f"jats:v1:{'c' * 64}:/article[1]",
            "delivery-locator-mismatch",
            1,
            id="locator",
        ),
        pytest.param(
            "chunks.jsonl",
            (0, "normalized_type"),
            "methods",
            "delivery-chunk-field-mismatch",
            1,
            id="chunk-field",
        ),
        pytest.param(
            "chunks.jsonl",
            (0, "ordinal"),
            2,
            "delivery-ordinal-gap",
            1,
            id="ordinal",
        ),
        pytest.param(
            "chunks.jsonl",
            (0, "text"),
            PRIVATE,
            "delivery-text-hash-mismatch",
            1,
            id="text",
        ),
        pytest.param(
            "chunks.jsonl",
            (0, "chunk_id"),
            "c" * 64,
            "delivery-chunk-id-mismatch",
            1,
            id="chunk-id",
        ),
        pytest.param(
            "chunk_report.json",
            ("chunking_version",),
            "synthetic-v9",
            "delivery-version-mismatch",
            1,
            id="version",
        ),
        pytest.param(
            "parse_report.json",
            ("summary", "succeeded"),
            99,
            "delivery-report-mismatch",
            1,
            id="report",
        ),
        pytest.param(
            "delivery_manifest.json",
            ("embedding_set", "provider"),
            "synthetic",
            "delivery-embedding-set-mismatch",
            1,
            id="embedding-set",
        ),
        pytest.param(
            "delivery_manifest.json",
            ("files", "papers.jsonl", "bytes"),
            1,
            "delivery-integrity-mismatch",
            1,
            id="descriptor",
        ),
        pytest.param(
            "delivery_manifest.json",
            ("counts", "papers"),
            99,
            "delivery-count-mismatch",
            1,
            id="count",
        ),
        pytest.param(
            "delivery_manifest.json",
            ("source_reports", "parse_report.json", "sha256"),
            "c" * 64,
            "source-report-mismatch",
            1,
            id="report-digest",
        ),
        pytest.param(
            "embedding_manifest.json",
            ("status",),
            "partial",
            "partial-set",
            1,
            id="partial",
        ),
    ],
)
def test_record_and_descriptor_defects(
    tree: PackageTree,
    capsys: pytest.CaptureFixture[str],
    name: str,
    path: tuple[str | int, ...],
    value: Any,
    code: str,
    status: int,
) -> None:
    """Cover every semantic family with real defects, retaining collateral."""
    artifact = read_artifact(tree, name)
    set_path(artifact, path, value)
    save_artifact(tree, name, artifact)
    assert_corrupt(tree, capsys, code, status)


def test_duplicate_records(
    tree: PackageTree, capsys: pytest.CaptureFixture[str]
) -> None:
    """A duplicate paper is a semantic failure at the command boundary."""
    papers = read_artifact(tree, "papers.jsonl")
    papers.append(deepcopy(papers[0]))
    save_artifact(tree, "papers.jsonl", papers)
    assert_corrupt(tree, capsys, "delivery-duplicate-record", 1)


@pytest.mark.parametrize("kind", ["norm", "size"])
def test_vector_defects(
    tree: PackageTree, capsys: pytest.CaptureFixture[str], kind: str
) -> None:
    """Real F003 norm validation and binary size failures reach the CLI."""
    path = artifact_path(tree, "vectors.f32")
    path.write_bytes(
        struct.pack("<ffff", 2.0, 0.0, 2.0, 0.0)
        if kind == "norm"
        else path.read_bytes()[:-1]
    )
    assert_corrupt(
        tree,
        capsys,
        "vector-norm-out-of-tolerance" if kind == "norm" else "vectors-size",
        1,
    )


@pytest.mark.parametrize("kind", ["extra", "count", "report-digest"])
def test_exact_representative_diagnostics(
    tree: PackageTree, capsys: pytest.CaptureFixture[str], kind: str
) -> None:
    """Pin exact sorted error lines independently of the library renderer."""
    manifest = read_artifact(tree, "delivery_manifest.json")
    if kind == "extra":
        (tree.inputs.output_dir / "SYNTHETIC extra").write_bytes(b"SYNTHETIC")
        expected = (
            "error: delivery-extra-file count: 1 first: report\nfailures: 1\n"
        )
        status = 2
    elif kind == "count":
        manifest["counts"]["papers"] = 99
        save_artifact(tree, "delivery_manifest.json", manifest)
        expected = (
            "error: delivery-count-mismatch count: 1 first: papers.jsonl\n"
            "error: delivery-report-mismatch count: 3 first: "
            "parse_report.json,chunk_report.json,embedding_report.json\n"
            "failures: 4\n"
        )
        status = 1
    else:
        manifest["source_reports"]["parse_report.json"]["sha256"] = "c" * 64
        save_artifact(tree, "delivery_manifest.json", manifest)
        expected = (
            "error: source-report-mismatch count: 1 first: parse_report.json\n"
            "failures: 1\n"
        )
        status = 1
    before = snapshot(tree.root)
    assert cli.main(arguments(tree)) == status
    assert capsys.readouterr() == ("", expected)
    assert snapshot(tree.root) == before


def test_simultaneous_classes(
    tree: PackageTree, capsys: pytest.CaptureFixture[str]
) -> None:
    """Structural precedence keeps all independent semantic findings visible."""
    artifact_path(tree, "papers.jsonl").write_bytes(b"\xff")
    chunks = read_artifact(tree, "chunks.jsonl")
    chunks[0]["text"] = PRIVATE
    save_artifact(tree, "chunks.jsonl", chunks)
    outcome = check(tree)
    assert {"invalid-utf8", "delivery-text-hash-mismatch"} <= {
        item.code for item in outcome.findings
    }
    assert_corrupt(tree, capsys, "invalid-utf8", 2)


@pytest.mark.parametrize(
    "exception",
    [RuntimeError, OSError, PermissionError],
    ids=["unexpected", "os", "permission"],
)
def test_exception_sanitization(
    tree: PackageTree,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    exception: type[Exception],
) -> None:
    """Never expose exception payloads, including paths and invented DOI."""
    spy = Mock(side_effect=exception(f"{tree.root} 10.1234/private {PRIVATE}"))
    monkeypatch.setattr(validate, "validate_package", spy)
    before = snapshot(tree.root)
    assert cli.main(arguments(tree)) == 1
    spy.assert_called_once_with(tree.inputs.output_dir, report_paths(tree))
    captured = capsys.readouterr()
    assert captured == (
        "",
        "error: delivery-failed count: 1 first: report\nfailures: 1\n",
    )
    assert_private(captured, tree)
    assert snapshot(tree.root) == before


@pytest.mark.parametrize(
    "structural", [False, True], ids=["semantic", "structural"]
)
def test_findings_use_existing_printer(
    tree: PackageTree,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    structural: bool,
) -> None:
    """Sort, sum and bound IDs through the existing printer with precedence."""
    findings = (
        Finding("vectors-size", 2, ("vectors",)),
        Finding(
            "delivery-orphan-record", 1, ("papers.jsonl", "sections.jsonl")
        ),
        Finding(
            "delivery-orphan-record",
            3,
            ("sections.jsonl", "chunks.jsonl", "report"),
        ),
    )
    loaded = check(tree).loaded
    monkeypatch.setattr(
        validate,
        "validate_package",
        Mock(
            return_value=validate.ValidationOutcome(
                findings, structural, loaded
            )
        ),
    )
    printer = Mock(wraps=cli._print_findings)
    monkeypatch.setattr(cli, "_print_findings", printer)
    assert cli.main(arguments(tree)) == (2 if structural else 1)
    printer.assert_called_once_with(list(findings))
    assert capsys.readouterr() == (
        "",
        "error: delivery-orphan-record count: 4 first: "
        "papers.jsonl,sections.jsonl,chunks.jsonl\n"
        "error: vectors-size count: 2 first: vectors\nfailures: 6\n",
    )


def test_source_digest_regression(
    tree: PackageTree, capsys: pytest.CaptureFixture[str]
) -> None:
    """Old packages survive source edits; new provenance still validates."""
    old = tree.inputs.committed_manifest.read_bytes()
    first = read_json(tree.inputs.committed_manifest)
    assert cli.main(arguments(tree)) == 0
    assert capsys.readouterr() == (SUCCESS, "")
    tree.inputs.parser_source.write_bytes(b"# SYNTHETIC changed parser\n")
    tree.inputs.taxonomy_source.write_bytes(b"# SYNTHETIC changed taxonomy\n")
    assert cli.main(arguments(tree)) == 0
    assert capsys.readouterr() == (SUCCESS, "")
    package.run_delivery(tree.inputs)
    second = read_json(tree.inputs.committed_manifest)
    for field in ("parser", "taxonomy"):
        assert (
            first["processing_versions"][field]["source_sha256"]
            != second["processing_versions"][field]["source_sha256"]
        )
    assert old != tree.inputs.committed_manifest.read_bytes()
    assert (
        tree.inputs.committed_manifest.read_bytes()
        == artifact_path(tree, "delivery_manifest.json").read_bytes()
    )
    assert cli.main(arguments(tree)) == 0
    assert capsys.readouterr() == (SUCCESS, "")


def test_command_access_boundary(
    tree: PackageTree,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Record opens and prohibit writes, environment, cache and network."""
    before = snapshot(tree.root)
    allowed = {
        *(tree.inputs.output_dir / name for name in PACKAGE_FILES),
        tree.inputs.parse_report,
        tree.inputs.chunk_report,
        tree.inputs.embedding_report,
    }
    opened: list[Path] = []
    environment, injected = RecordingEnvironment(), RecordingEnvironment()

    def guard_cache(original: Any) -> Any:
        def guarded(file: Any, *args: Any, **kwargs: Any) -> Any:
            if isinstance(file, (str, os.PathLike)):
                path = Path(file).absolute()
                assert not path.is_relative_to(tree.inputs.cache_dir)
                assert not path.is_relative_to(
                    package.DeliveryInputs().cache_dir.absolute()
                )
            return original(file, *args, **kwargs)

        return guarded

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
                    os.O_WRONLY
                    | os.O_RDWR
                    | os.O_CREAT
                    | os.O_TRUNC
                    | os.O_APPEND
                )
            return original(file, mode, *args, **kwargs)

        return guarded

    with monkeypatch.context() as patch:
        patch.setattr(os, "environ", environment)
        patch.setattr(builtins, "open", wrap(builtins.open))
        patch.setattr(io, "open", wrap(io.open))
        patch.setattr(os, "open", wrap(os.open))
        for name in ("stat", "lstat", "scandir", "listdir"):
            patch.setattr(os, name, guard_cache(getattr(os, name)))
        patch.setattr(cli, "_parser", forbidden)
        patch.setattr(package, "run_delivery", forbidden)
        for name in (
            "write_bytes",
            "write_text",
            "mkdir",
            "unlink",
            "rename",
            "replace",
            "rmdir",
            "touch",
        ):
            patch.setattr(Path, name, forbidden)
        for name in (
            "replace",
            "rename",
            "remove",
            "unlink",
            "mkdir",
            "makedirs",
            "rmdir",
            "write",
        ):
            patch.setattr(os, name, forbidden)
        assert (
            cli.main(
                arguments(tree), environ=injected, transport_factory=forbidden
            )
            == 0
        )
    assert capsys.readouterr() == (SUCCESS, "")
    assert set(opened) == allowed
    assert environment.accessed_keys == injected.accessed_keys == []
    assert snapshot(tree.root) == before


def test_staging_order_and_two_runs(
    tree: PackageTree, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Validate once after producer checks and before publishing the stage."""
    events: list[str] = []
    original_validate = validate.validate_package
    original_publish = publish._publish
    original_integrity = package._check_integrity
    original_produced = package._check_produced
    before = snapshot(tree.inputs.output_dir)
    committed = tree.inputs.committed_manifest.read_bytes()

    def produced(*args: Any, **kwargs: Any) -> None:
        original_produced(*args, **kwargs)
        events.append("produced")

    def integrity(*args: Any, **kwargs: Any) -> None:
        original_integrity(*args, **kwargs)
        events.append("integrity")

    def receiver(
        staged: Path, reports: validate.PackageReports
    ) -> validate.ValidationOutcome:
        assert staged != tree.inputs.output_dir
        assert staged.parent == tree.inputs.output_dir.parent
        assert {item.name for item in staged.iterdir()} == set(PACKAGE_FILES)
        assert all(item.is_file() for item in staged.iterdir())
        assert reports == report_paths(tree)
        assert events == ["produced", "produced", "integrity"]
        events.append("validate")
        return original_validate(staged, reports)

    def publication(staged: Path, *args: Any, **kwargs: Any) -> None:
        events.append("publish")
        original_publish(staged, *args, **kwargs)

    spy = Mock(side_effect=receiver)
    monkeypatch.setattr(package, "_check_produced", produced)
    monkeypatch.setattr(package, "_check_integrity", integrity)
    monkeypatch.setattr(validate, "validate_package", spy)
    monkeypatch.setattr(publish, "_publish", publication)
    for _ in range(2):
        events.clear()
        spy.reset_mock()
        assert package.run_delivery(tree.inputs) == package.DeliverySummary(
            2, 3, 2, 2, 6
        )
        spy.assert_called_once()
        assert events == [
            "produced",
            "produced",
            "integrity",
            "validate",
            "publish",
        ]
        assert snapshot(tree.inputs.output_dir) == before
        assert tree.inputs.committed_manifest.read_bytes() == committed
        assert sorted(
            item.name for item in tree.inputs.output_dir.parent.iterdir()
        ) == ["pilot"]


@pytest.mark.parametrize(
    "structural", [False, True], ids=["semantic", "structural"]
)
def test_staging_refuses_injected_findings(
    tree: PackageTree,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    structural: bool,
) -> None:
    """Retain both previous outputs and remove the stage on any finding."""
    loaded = check(tree).loaded
    code = "invalid-json" if structural else "delivery-parent-invalid"
    findings = (Finding(code, 1, ("sections.jsonl",)),)
    spy = Mock(
        return_value=validate.ValidationOutcome(findings, structural, loaded)
    )
    publisher = Mock(wraps=publish._publish)
    monkeypatch.setattr(validate, "validate_package", spy)
    monkeypatch.setattr(publish, "_publish", publisher)
    before = snapshot(tree.root)
    assert cli.main(tree.args()) == (2 if structural else 1)
    assert capsys.readouterr() == ("", diagnostics(findings))
    spy.assert_called_once()
    publisher.assert_not_called()
    assert snapshot(tree.root) == before


@pytest.mark.parametrize("multiple", [False, True], ids=["xml", "independent"])
def test_staging_real_defects(
    tree: PackageTree,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    multiple: bool,
) -> None:
    """Refuse real upstream defects accepted by earlier producer checks."""
    acquisitions = rows(tree.inputs.acquisition_manifest)
    acquisitions[0]["xml_sha256"] = "c" * 64
    write_rows(tree.inputs.acquisition_manifest, acquisitions)
    if multiple:
        sections = rows(tree.inputs.sections)
        sections[0]["depth"] = 2
        write_rows(tree.inputs.sections, sections)
        report = read_artifact(tree, "parse_report.json")
        report["summary"]["succeeded"] = 99
        save_artifact(tree, "parse_report.json", report)
    before = snapshot(tree.root)
    producer_checks: list[str] = []

    def record(original: Any, name: str) -> Any:
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            result = original(*args, **kwargs)
            producer_checks.append(name)
            return result

        return wrapped

    monkeypatch.setattr(
        package, "_check_produced", record(package._check_produced, "produced")
    )
    monkeypatch.setattr(
        package,
        "_check_integrity",
        record(package._check_integrity, "integrity"),
    )
    publisher = Mock(wraps=publish._publish)
    monkeypatch.setattr(publish, "_publish", publisher)
    assert cli.main(tree.args()) == 1
    captured = capsys.readouterr()
    assert producer_checks == ["produced", "produced", "integrity"]
    assert captured.out == ""
    assert "error: delivery-xml-sha-mismatch " in captured.err
    assert "error: delivery-report-mismatch " in captured.err
    if multiple:
        assert "error: delivery-parent-invalid " in captured.err
        assert "error: delivery-section-structure-mismatch " in captured.err
    assert_private(captured, tree)
    publisher.assert_not_called()
    assert snapshot(tree.root) == before


def assert_no_deliver_subparser() -> None:
    """Require the old argparse route to reject deliver with sanitized usage."""
    rejected = False
    try:
        cli._parser().parse_args(["deliver"])
    except ConfigError as error:
        assert str(error) == "invalid-usage"
        rejected = True
    assert rejected, "SYNTHETIC dead deliver subparser is still registered"


def test_dead_subparser_removed() -> None:
    """Dedicated delivery routing leaves no dead argparse subcommand."""
    assert_no_deliver_subparser()


def test_deliver_default_route_survives(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Default deliver retains its dedicated producer after parser cleanup."""
    spy = Mock(return_value=package.DeliverySummary(2, 3, 2, 2, 6))
    monkeypatch.setattr(package, "run_delivery", spy)
    assert cli.main(["deliver"]) == 0
    spy.assert_called_once_with(package.DeliveryInputs())
    assert capsys.readouterr() == (
        "delivered papers: 2 sections: 3 chunks: 2 vectors: 2 files: 6\n",
        "",
    )
    assert_no_deliver_subparser()


def test_deliver_help_route_survives(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Existing deliver help is unchanged once the dead subparser is removed."""
    monkeypatch.setattr(package, "run_delivery", forbidden)
    assert cli.main(["deliver", "--help"]) == 0
    assert capsys.readouterr() == (
        "usage: deliver "
        + " ".join(
            "[--" + name.replace("_", "-") + " PATH]"
            for name in cli._DELIVERY_FIELDS
        )
        + "\n",
        "",
    )
    assert_no_deliver_subparser()
