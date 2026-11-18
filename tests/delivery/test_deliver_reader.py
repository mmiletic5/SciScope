"""SYNTHETIC offline reader behavior and future delivery-guide checks."""

from __future__ import annotations

import ast
import importlib
import inspect
import json
import re
import socket
import struct
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import pytest

from sciscope.delivery import reader


@pytest.fixture(autouse=True)
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reject accidental networking in every synthetic case."""

    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("Network access is forbidden")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)


def assert_error(
    error: reader.DeliveryReadError, code: str, path: Path
) -> None:
    """Require exactly a safe code without synthetic content or paths."""
    assert error.code == code
    assert str(error) == code
    assert path.name not in str(error)
    assert str(path) not in str(error)
    assert "SYNTHETIC" not in str(error)


def manifest(tmp_path: Path, value: object) -> Path:
    """Write disposable JSON without newline translation."""
    path = tmp_path / "SYNTHETIC-manifest.json"
    path.write_bytes(json.dumps(value).encode("utf-8"))
    return path


def vectors(tmp_path: Path, values: tuple[float, ...]) -> Path:
    """Pack independent little-endian synthetic values."""
    path = tmp_path / "SYNTHETIC-vectors.f32"
    path.write_bytes(struct.pack("<" + "f" * len(values), *values))
    return path


@pytest.mark.parametrize(
    "ending", [pytest.param(b"", id="no-lf"), pytest.param(b"\n", id="lf")]
)
def test_jsonl_order(tmp_path: Path, ending: bytes) -> None:
    """Preserve three objects and their file order with either ending."""
    path = tmp_path / "SYNTHETIC.jsonl"
    path.write_bytes(b'{"i":3}\n{"i":1}\n{"i":2}' + ending)
    assert list(reader.iter_jsonl(path)) == [{"i": 3}, {"i": 1}, {"i": 2}]


def test_jsonl_empty(tmp_path: Path) -> None:
    """An empty file contains no records."""
    path = tmp_path / "SYNTHETIC.jsonl"
    path.write_bytes(b"")
    assert list(reader.iter_jsonl(str(path))) == []


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("SYNTHETIC\u0085value", id="nel"),
        pytest.param("SYNTHETIC\u2028value", id="line-separator"),
        pytest.param("SYNTHETIC\u2029value", id="paragraph-separator"),
        pytest.param("SYNTHETIC Ž漢字🙂", id="unicode"),
        pytest.param("SYNTHETIC " + "x" * (3 * 1024 * 1024), id="three-mib"),
    ],
)
def test_jsonl_strings(tmp_path: Path, text: str) -> None:
    """Keep raw Unicode separators and large single-line strings intact."""
    path = tmp_path / "SYNTHETIC.jsonl"
    path.write_bytes(json.dumps({"text": text}, ensure_ascii=False).encode())
    assert list(reader.iter_jsonl(path)) == [{"text": text}]


@pytest.mark.parametrize(
    "payload,code",
    [
        pytest.param(b"{}\n\n{}", "reader-line", id="blank"),
        pytest.param(b"{}\n \t\n{}", "reader-line", id="whitespace"),
        pytest.param(b"{}\n\n", "reader-line", id="extra-lf"),
        pytest.param(b"\xef\xbb\xbf{}", "reader-decoding", id="bom"),
        pytest.param(b'{"SYNTHETIC":"\xff"}', "reader-decoding", id="utf8"),
        pytest.param(b'{"SYNTHETIC":', "reader-json", id="malformed"),
        pytest.param(b"{} SYNTHETIC", "reader-json", id="garbage"),
        pytest.param(b"[]", "reader-line", id="array"),
        pytest.param(b'"SYNTHETIC"', "reader-line", id="string"),
        pytest.param(b"42", "reader-line", id="number"),
        pytest.param(b"null", "reader-line", id="null"),
        pytest.param(b'{"x":NaN}', "reader-json", id="nan"),
        pytest.param(b'{"x":Infinity}', "reader-json", id="inf"),
        pytest.param(b'{"x":-Infinity}', "reader-json", id="negative-inf"),
        pytest.param(b"{}\r\n", "reader-json", id="crlf"),
        pytest.param(b'{\r"x":1}', "reader-json", id="cr-whitespace"),
        pytest.param(b'{"x":"SYNTHETIC\r"}', "reader-json", id="cr-string"),
    ],
)
def test_jsonl_errors(tmp_path: Path, payload: bytes, code: str) -> None:
    """Reject invalid lines with sanitized, stable codes."""
    path = tmp_path / "SYNTHETIC.jsonl"
    path.write_bytes(payload)
    with pytest.raises(reader.DeliveryReadError) as caught:
        list(reader.iter_jsonl(path))
    assert_error(caught.value, code, path)


def test_jsonl_error_after_record(tmp_path: Path) -> None:
    """Yield earlier records before encountering a later malformed line."""
    path = tmp_path / "SYNTHETIC.jsonl"
    path.write_bytes(b'{"i":1}\nSYNTHETIC')
    iterator = reader.iter_jsonl(path)
    assert next(iterator) == {"i": 1}
    with pytest.raises(reader.DeliveryReadError) as caught:
        list(iterator)
    assert_error(caught.value, "reader-json", path)


def test_jsonl_duplicate_keys(tmp_path: Path) -> None:
    """Leave duplicate-key validation to validate-delivery; last value wins."""
    path = tmp_path / "SYNTHETIC.jsonl"
    path.write_bytes(b'{"x":1,"x":2}')
    assert list(reader.iter_jsonl(path)) == [{"x": 2}]


@pytest.mark.parametrize(
    "kind",
    [pytest.param(kind, id=kind) for kind in ("missing", "directory")],
)
@pytest.mark.parametrize(
    "api",
    [pytest.param(api, id=api) for api in ("jsonl", "vectors", "mapping")],
)
def test_io(tmp_path: Path, kind: str, api: str) -> None:
    """Normalize missing paths and directories across the public readers."""
    path = tmp_path / "SYNTHETIC-unreadable"
    if kind == "directory":
        path.mkdir()
    with pytest.raises(reader.DeliveryReadError) as caught:
        if api == "jsonl":
            list(reader.iter_jsonl(path))
        elif api == "vectors":
            reader.load_vectors(path, dimensions=2, count=1)
        else:
            reader.vectors_by_chunk_id(path, path, dimensions=2)
    assert_error(caught.value, "reader-io", path)


def test_vector_values_and_types(tmp_path: Path) -> None:
    """Widen exact float32 values into an immutable tuple matrix."""
    values = (0.1, -2.5, 1.0, 123.456)
    path = vectors(tmp_path, values)
    expected = tuple(
        struct.unpack("<f", struct.pack("<f", x))[0] for x in values
    )
    result = reader.load_vectors(str(path), dimensions=2, count=2)
    assert result == (expected[:2], expected[2:])
    assert type(result) is tuple
    assert all(type(row) is tuple for row in result)
    assert all(type(value) is float for row in result for value in row)


def test_vector_byte_order(tmp_path: Path) -> None:
    """Decode known bytes little-endian even when big-endian differs."""
    path = vectors(tmp_path, (1.0, -2.5))
    assert struct.unpack(">2f", path.read_bytes()) != (1.0, -2.5)
    assert reader.load_vectors(path, dimensions=2, count=1) == ((1.0, -2.5),)


@pytest.mark.parametrize(
    "size",
    [
        pytest.param(15, id="short-byte"),
        pytest.param(17, id="long-byte"),
        pytest.param(0, id="empty"),
    ],
)
def test_vector_size(tmp_path: Path, size: int) -> None:
    """Require exactly count times dimensions times four bytes."""
    path = tmp_path / "SYNTHETIC.f32"
    path.write_bytes(b"\0" * size)
    with pytest.raises(reader.DeliveryReadError) as caught:
        reader.load_vectors(path, dimensions=2, count=2 if size else 1)
    assert_error(caught.value, "reader-size", path)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(0, id="zero"),
        pytest.param(-1, id="negative"),
        pytest.param(True, id="bool"),
        pytest.param(1.5, id="float"),
        pytest.param("2", id="string"),
    ],
)
@pytest.mark.parametrize(
    "field",
    [
        pytest.param("count", id="count"),
        pytest.param("dimensions", id="dimensions"),
    ],
)
def test_vector_arguments(tmp_path: Path, value: Any, field: str) -> None:
    """Reject arguments before attempting I/O on a nonexistent file."""
    path = tmp_path / "SYNTHETIC-missing.f32"
    arguments = {"dimensions": 2, "count": 2, field: value}
    with pytest.raises(reader.DeliveryReadError) as caught:
        reader.load_vectors(path, **arguments)
    assert_error(caught.value, "reader-argument", path)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(float("nan"), id="nan"),
        pytest.param(float("inf"), id="inf"),
        pytest.param(float("-inf"), id="negative-inf"),
    ],
)
@pytest.mark.parametrize(
    "index",
    [
        pytest.param(0, id="first"),
        pytest.param(1, id="first-row-end"),
        pytest.param(2, id="second-row"),
        pytest.param(3, id="last-row-end"),
    ],
)
def test_vector_nonfinite(tmp_path: Path, value: float, index: int) -> None:
    """Reject nonfinite float32 values in every matrix position."""
    values = [1.0] * 4
    values[index] = value
    path = vectors(tmp_path, tuple(values))
    with pytest.raises(reader.DeliveryReadError) as caught:
        reader.load_vectors(path, dimensions=2, count=2)
    assert_error(caught.value, "reader-nonfinite", path)


def test_vector_size_precedes_nonfinite(tmp_path: Path) -> None:
    """Report size before inspecting an otherwise nonfinite matrix."""
    path = vectors(tmp_path, (float("nan"), 1.0, 2.0, 3.0))
    path.write_bytes(path.read_bytes() + b"x")
    with pytest.raises(reader.DeliveryReadError) as caught:
        reader.load_vectors(path, dimensions=2, count=2)
    assert_error(caught.value, "reader-size", path)


@pytest.mark.parametrize(
    "with_chunks",
    [pytest.param(True, id="reordered"), pytest.param(False, id="absent")],
)
def test_mapping_order(tmp_path: Path, with_chunks: bool) -> None:
    """Use manifest IDs exclusively, ignoring chunk order and metadata."""
    ids = ["SYNTHETIC-b", "SYNTHETIC-a", "SYNTHETIC-c"]
    source = manifest(
        tmp_path,
        {
            "entries": [
                {"chunk_id": key, "input_sha256": "ignored"} for key in ids
            ],
            "dimensions": 999,
            "extra": "ignored",
        },
    )
    chunk_order = [ids[2], ids[0], ids[1]]
    if with_chunks:
        (tmp_path / "chunks.jsonl").write_bytes(
            b"\n".join(
                json.dumps({"chunk_id": key}).encode() for key in chunk_order
            )
        )
    path = vectors(tmp_path, (1.0, 2.0, 3.0, 4.0, 5.0, 6.0))
    result = reader.vectors_by_chunk_id(source, path, dimensions=2)
    rows = ((1.0, 2.0), (3.0, 4.0), (5.0, 6.0))
    assert list(result) == ids
    for index, key in enumerate(ids):
        assert result[key] == rows[index]
        assert result[key] != rows[chunk_order.index(key)]


@pytest.mark.parametrize(
    "value,code",
    [
        pytest.param(
            {"entries": [{"chunk_id": "x"}, {"chunk_id": "x"}]},
            "reader-duplicate-id",
            id="duplicate",
        ),
        pytest.param({"entries": [{}]}, "reader-manifest", id="missing-id"),
        pytest.param(
            {"entries": [{"chunk_id": 1}]}, "reader-manifest", id="id-type"
        ),
        pytest.param({"entries": [None]}, "reader-manifest", id="entry-type"),
        pytest.param({"entries": {}}, "reader-manifest", id="entries-type"),
        pytest.param({"entries": []}, "reader-manifest", id="empty"),
        pytest.param({}, "reader-manifest", id="missing-entries"),
        pytest.param([], "reader-manifest", id="array-root"),
    ],
)
def test_mapping_shape(tmp_path: Path, value: object, code: str) -> None:
    """Reject malformed manifest structure and repeated IDs safely."""
    source = manifest(tmp_path, value)
    path = vectors(tmp_path, (1.0, 2.0))
    with pytest.raises(reader.DeliveryReadError) as caught:
        reader.vectors_by_chunk_id(source, path, dimensions=2)
    assert_error(caught.value, code, source)


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(b"\xff", id="utf8"),
        pytest.param(b"\xef\xbb\xbf{}", id="bom"),
        pytest.param(b"{SYNTHETIC", id="json"),
    ],
)
def test_mapping_decoding(tmp_path: Path, payload: bytes) -> None:
    """Manifest decoding failures use reader-manifest, not JSONL codes."""
    source = tmp_path / "SYNTHETIC-manifest.json"
    source.write_bytes(payload)
    path = vectors(tmp_path, (1.0, 2.0))
    with pytest.raises(reader.DeliveryReadError) as caught:
        reader.vectors_by_chunk_id(source, path, dimensions=2)
    assert_error(caught.value, "reader-manifest", source)


@pytest.mark.parametrize(
    "values,dimensions",
    [
        pytest.param((1.0, 2.0), 2, id="row-short"),
        pytest.param((1.0,) * 6, 2, id="row-long"),
        pytest.param((1.0,) * 4, 3, id="dimensions"),
    ],
)
def test_mapping_size(
    tmp_path: Path, values: tuple[float, ...], dimensions: int
) -> None:
    """Apply the same exact row-count and dimension loading rules."""
    source = manifest(
        tmp_path, {"entries": [{"chunk_id": "a"}, {"chunk_id": "b"}]}
    )
    path = vectors(tmp_path, values)
    with pytest.raises(reader.DeliveryReadError) as caught:
        reader.vectors_by_chunk_id(source, path, dimensions=dimensions)
    assert_error(caught.value, "reader-size", path)


def test_standalone_imports() -> None:
    """Permit only the agreed stdlib roots, including relative-import guards."""
    tree = ast.parse(Path(reader.__file__).read_bytes())
    allowed = set(
        "__future__ collections json math os pathlib struct typing".split()
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(
                alias.name.split(".")[0] in allowed for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            assert node.module and node.module.split(".")[0] in allowed


def test_quiet_import(capsys: pytest.CaptureFixture[str]) -> None:
    """Re-execute the module and require no printed output."""
    importlib.reload(reader)
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""


def repo_root() -> Path:
    """Discover the checkout without assuming a fixed test-directory depth."""
    for candidate in Path(__file__).resolve().parents:
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise AssertionError("Repository root with pyproject.toml was not found")


def guide() -> str:
    """Read the guide once per test, clearly failing while it is absent."""
    path = repo_root() / "docs" / "DELIVERY_GUIDE.md"
    assert path.is_file(), "Phase 2 must create docs/DELIVERY_GUIDE.md"
    return path.read_bytes().decode("utf-8")


def test_guide_exists() -> None:
    """Require a nonempty delivery guide."""
    assert guide().strip()


def test_guide_size() -> None:
    """Keep the handoff within both approved size limits."""
    text = guide()
    assert len(text.splitlines()) <= 140
    assert len(text.split()) <= 1100


def test_guide_first_block() -> None:
    """Open with the mapping helper after a title and at most one sentence."""
    text = guide()
    first = re.search(r"^```([^\n]*)\n(.*?)^```", text, re.M | re.S)
    assert first is not None
    assert first.group(1).strip() == "python"
    prefix = text[: first.start()].strip().splitlines()
    assert prefix and prefix[0].startswith("# ")
    intro = " ".join(line.strip() for line in prefix[1:] if line.strip())
    assert not intro or len(re.findall(r"[.!?](?:\s|$)", intro)) <= 1
    assert "vectors_by_chunk_id(" in first.group(2)
    tree = ast.parse(first.group(2))
    assert any(
        isinstance(node, ast.ImportFrom)
        and node.module == "sciscope.delivery.reader"
        and any(item.name == "vectors_by_chunk_id" for item in node.names)
        for node in ast.walk(tree)
    )


def test_guide_never_zip() -> None:
    """Warn early that chunk-file position cannot identify vector rows."""
    opening = " ".join(guide().splitlines()[:25]).lower()
    sentences = re.split(r"(?<=[.!?])\s+", opening)
    assert any(
        all(
            word in sentence
            for word in ("never zip", "chunks.jsonl", "position")
        )
        for sentence in sentences
    )


def test_guide_python_blocks() -> None:
    """Parse every Python example as valid Python source."""
    blocks = re.findall(r"^```python\s*\n(.*?)^```", guide(), re.M | re.S)
    assert blocks, "The guide must include Python examples"
    for block in blocks:
        assert isinstance(ast.parse(block), ast.Module)


def test_guide_links() -> None:
    """Resolve relative Markdown links from docs within the repository."""
    text = guide()
    root = repo_root()
    targets = re.findall(r"\[[^\]]*\]\(([^)]+)\)", text)
    targets += re.findall(r"^\s*\[[^\]]+\]:\s*(\S+)", text, re.M)
    for target in targets:
        target = target.split(' "', 1)[0].strip("<>")
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        path = (root / "docs" / unquote(parsed.path)).resolve()
        assert path.is_relative_to(root)
        assert path.exists(), f"Missing relative guide link: {target}"


@pytest.mark.parametrize(
    "keyword",
    [
        pytest.param(word, id=word)
        for word in (
            "papers.jsonl sections.jsonl chunks.jsonl vectors.f32 "
            "embedding_manifest.json delivery_manifest.json schema_version "
            "validate-delivery sha256 tar query_prefix EN case-insensitive "
            "data/raw/plos xml_sha256 show check-quote source_locator "
            "section_path (untitled) omitted hard_split report 16,000 2,000"
        ).split()
        + ["pull request"]
    ],
)
def test_guide_topic(keyword: str) -> None:
    """Require each independently identified handoff topic."""
    assert keyword.lower() in guide().lower()


def test_guide_forbidden_claims() -> None:
    """Exclude credential examples, local Windows paths and DB test claims."""
    text = guide()
    for forbidden in (
        "OPENAI_API_KEY=",
        "sk-",
        "C:\\",
        "tested with pgvector",
        "works with pgvector",
        "installed pgvector",
    ):
        assert forbidden.lower() not in text.lower()


@pytest.mark.parametrize(
    "payload,code",
    [
        pytest.param(
            b"[" * 100000 + b"]" * 100000,
            "reader-json",
            id="deep-nesting",
        ),
        pytest.param(b'{"x":1e999}', "reader-json", id="overflow"),
        pytest.param(b"9" * 5000, "reader-json", id="integer-limit"),
        pytest.param(b'{"x":-1e999}', "reader-json", id="negative-overflow"),
        pytest.param(b"{}\n \t", "reader-line", id="final-whitespace"),
    ],
)
def test_jsonl_review_errors(tmp_path: Path, payload: bytes, code: str) -> None:
    """Reject parser limits, numeric overflow and terminal blank records."""
    path = tmp_path / "SYNTHETIC-review.jsonl"
    path.write_bytes(payload)
    with pytest.raises(reader.DeliveryReadError) as caught:
        list(reader.iter_jsonl(path))
    assert_error(caught.value, code, path)


def test_jsonl_decoding_before_records(tmp_path: Path) -> None:
    """Decode the whole file before yielding even an earlier valid record."""
    path = tmp_path / "SYNTHETIC-review.jsonl"
    path.write_bytes(b'{"i":1}\n\xff')
    yielded: list[dict[str, object]] = []
    with pytest.raises(reader.DeliveryReadError) as caught:
        for record in reader.iter_jsonl(path):
            yielded.append(record)
    assert yielded == []
    assert_error(caught.value, "reader-decoding", path)


def test_jsonl_generator(tmp_path: Path) -> None:
    """Expose a generator rather than an eager object-list iterator."""
    path = tmp_path / "SYNTHETIC-review.jsonl"
    path.write_bytes(b"{}\n")
    iterator = reader.iter_jsonl(path)
    assert inspect.isgenerator(iterator)
    assert list(iterator) == [{}]


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(b'{"x":1e999}', id="overflow"),
        pytest.param(b"[" * 100000 + b"]" * 100000, id="deep-nesting"),
    ],
)
def test_mapping_review_decoding(tmp_path: Path, payload: bytes) -> None:
    """Use manifest codes for numeric overflow and recursion failures."""
    source = tmp_path / "SYNTHETIC-review.json"
    source.write_bytes(payload)
    path = vectors(tmp_path, (1.0, 2.0))
    with pytest.raises(reader.DeliveryReadError) as caught:
        reader.vectors_by_chunk_id(source, path, dimensions=2)
    assert_error(caught.value, "reader-manifest", source)


@pytest.mark.parametrize(
    "api",
    [
        pytest.param("vectors", id="vectors"),
        pytest.param("mapping", id="mapping"),
    ],
)
def test_embedded_nul_path(tmp_path: Path, api: str) -> None:
    """Normalize Path.read_bytes ValueError without leaking its context."""
    path = "SYNTHETIC\0x"
    with pytest.raises(reader.DeliveryReadError) as caught:
        if api == "vectors":
            reader.load_vectors(path, dimensions=2, count=1)
        else:
            reader.vectors_by_chunk_id(path, tmp_path / "absent", dimensions=2)
    assert_error(caught.value, "reader-io", Path(path))
    assert caught.value.__suppress_context__


@pytest.mark.parametrize(
    "dimensions", [pytest.param(0, id="zero"), pytest.param(True, id="bool")]
)
def test_mapping_argument_precedence(tmp_path: Path, dimensions: int) -> None:
    """Reject dimensions before opening a nonexistent manifest."""
    source = tmp_path / "SYNTHETIC-missing.json"
    with pytest.raises(reader.DeliveryReadError) as caught:
        reader.vectors_by_chunk_id(source, source, dimensions=dimensions)
    assert_error(caught.value, "reader-argument", source)


@pytest.mark.parametrize(
    "api",
    [pytest.param(api, id=api) for api in ("jsonl", "vectors", "mapping")],
)
def test_string_and_path_parity(tmp_path: Path, api: str) -> None:
    """Accept both supported path forms consistently for every API."""
    path = vectors(tmp_path, (1.0, 2.0))
    source = manifest(tmp_path, {"entries": [{"chunk_id": "SYNTHETIC-a"}]})
    if api == "jsonl":
        path.write_bytes(b'{"text":"SYNTHETIC"}\n')
        assert list(reader.iter_jsonl(str(path))) == list(
            reader.iter_jsonl(path)
        )
    elif api == "vectors":
        assert reader.load_vectors(str(path), dimensions=2, count=1) == (
            reader.load_vectors(path, dimensions=2, count=1)
        )
    else:
        assert reader.vectors_by_chunk_id(
            str(source), str(path), dimensions=2
        ) == (reader.vectors_by_chunk_id(source, path, dimensions=2))


def test_duplicate_before_vector_io(tmp_path: Path) -> None:
    """Reject duplicate IDs even when the vectors file does not exist."""
    source = manifest(
        tmp_path,
        {"entries": [{"chunk_id": "SYNTHETIC-a"}, {"chunk_id": "SYNTHETIC-a"}]},
    )
    path = tmp_path / "SYNTHETIC-missing.f32"
    with pytest.raises(reader.DeliveryReadError) as caught:
        reader.vectors_by_chunk_id(source, path, dimensions=2)
    assert_error(caught.value, "reader-duplicate-id", source)
