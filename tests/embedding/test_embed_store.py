"""T006 synthetic offline RED contracts for chunk input, cache, and files."""

from __future__ import annotations

import hashlib
import json
import math
import os
from collections.abc import Mapping
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest
from embed_fixtures import (
    FAKE_KEY,
    FIXED_DATE,
    f32_bytes,
    synthetic_record,
    write_chunks,
)

from sciscope.chunking.counter import Utf8BytesDiv3Counter
from sciscope.embedding.cache import (
    CacheEntry,
    EmbeddingCache,
    cache_key,
    decode_entry,
    encode_entry,
)
from sciscope.embedding.config import (
    DEFAULT_MODEL,
    EmbeddingCacheError,
    EmbeddingConfig,
    EmbeddingInputError,
    EmbeddingProviderError,
    build_passage_input,
)
from sciscope.embedding.inputs import load_chunk_inputs
from sciscope.embedding.store import (
    build_manifest,
    build_report,
    pack_vector,
    render_json,
    unpack_vector,
    vector_norm,
    write_embedding_files,
)

MANIFEST_KEYS = (
    "format_version",
    "status",
    "provider",
    "model",
    "requested_dimensions",
    "returned_dimensions",
    "normalization",
    "passage_prefix",
    "query_prefix",
    "template_version",
    "token_counter_id",
    "chunking_version",
    "chunks_sha256",
    "chunk_count",
    "vector_count",
    "creation_date",
    "usage",
    "estimated_input_tokens",
    "provider_input_count",
    "custom_base_url_used",
    "vectors_file",
    "vectors_dtype",
    "vectors_sha256",
    "entries",
)
REPORT_KEYS = (
    "format_version",
    "status",
    "provider",
    "model",
    "requested_dimensions",
    "returned_dimensions",
    "chunks_sha256",
    "chunk_count",
    "vector_count",
    "paper_count",
    "estimated_input_tokens",
    "usage",
    "provider_input_count",
    "approximate_cost",
    "template_version",
    "token_counter_id",
    "chunking_version",
    "creation_date",
    "custom_base_url_used",
)


def entry(
    input_hash: str = "b" * 64,
    *,
    batch_id: str | None = None,
    count: int = 1,
    estimate: int = 20,
    prompt: int = 7,
    total: int = 9,
    date: str = FIXED_DATE,
) -> CacheEntry:
    """Create explicit float32 metadata without calling production encoders."""
    vector = f32_bytes((1.0, 0.0))
    return CacheEntry(
        format="embedding-cache-v1",
        model=DEFAULT_MODEL,
        dimensions=2,
        input_sha256=input_hash,
        vector_sha256=hashlib.sha256(vector).hexdigest(),
        estimated_tokens=20,
        counter_id="utf8-bytes-div3-v1",
        embedded_on=date,
        batch_id=batch_id or hashlib.sha256(input_hash.encode()).hexdigest(),
        batch_input_count=count,
        batch_estimated_tokens=estimate,
        batch_prompt_tokens=prompt,
        batch_total_tokens=total,
        vector_bytes=vector,
    )


@pytest.mark.parametrize("separator", ["\u2028", "\u2029", "\u0085"])
@pytest.mark.parametrize("ending", [b"\n", b"\r\n", b""])
def test_reader_splits_only_on_lf(
    tmp_path: Path, separator: str, ending: bytes
) -> None:
    """T006-S01: Unicode separators inside text never split JSONL records."""
    text = "Synthetic first." + separator + "Synthetic second."
    row = synthetic_record(text=text)
    raw = json.dumps(row, ensure_ascii=False).encode("utf-8") + ending
    path = tmp_path / "chunks.jsonl"
    path.write_bytes(raw)
    loaded = load_chunk_inputs(path, Utf8BytesDiv3Counter())
    assert len(loaded.chunks) == 1
    assert loaded.chunks[0].text == text
    assert loaded.chunks[0].section_path[0] == "(untitled)"
    assert loaded.chunks_sha256 == hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize(
    ("defect", "code"),
    [
        ("missing", "chunks-unreadable"),
        ("utf8", "chunks-invalid-utf8"),
        ("json", "chunks-invalid-json"),
        ("nan", "chunks-invalid-json"),
        ("infinity", "chunks-invalid-json"),
        ("blank-line", "chunks-invalid-json"),
        ("two-final-lf", "chunks-invalid-json"),
        ("missing-field", "chunks-bad-record"),
        ("extra-field", "chunks-bad-record"),
        ("not-object", "chunks-bad-record"),
        ("blank-text", "chunks-bad-record"),
        ("text-hash", "chunks-bad-record"),
        ("path-string", "chunks-bad-record"),
        ("path-item", "chunks-bad-record"),
        ("uppercase-id", "chunks-bad-record"),
        ("short-id", "chunks-bad-record"),
        ("nonhex-id", "chunks-bad-record"),
        ("duplicate", "chunks-duplicate-id"),
        ("empty", "chunks-empty"),
        ("versions", "chunks-mixed-versions"),
        ("counter", "counter-mismatch"),
        ("template", "template-mismatch"),
    ],
)
def test_reader_rejects_bad_chunks(
    tmp_path: Path, defect: str, code: str
) -> None:
    """T006-S02: reject malformed input with the exact sanitized input code."""
    rows = [synthetic_record(), synthetic_record(1)]
    if defect == "missing-field":
        del rows[0]["doi"]
    elif defect == "extra-field":
        rows[0]["extra"] = 0
    elif defect == "blank-text":
        rows[0]["text"] = " \t"
    elif defect == "text-hash":
        rows[0]["text_sha256"] = "0" * 64
    elif defect in ("path-string", "path-item"):
        rows[0]["section_path"] = "heading" if defect == "path-string" else [3]
    elif defect in ("uppercase-id", "short-id", "nonhex-id"):
        rows[0]["chunk_id"] = {
            "uppercase-id": "A" * 64,
            "short-id": "a",
            "nonhex-id": "g" * 64,
        }[defect]
    elif defect == "duplicate":
        rows[1]["chunk_id"] = rows[0]["chunk_id"]
    elif defect == "versions":
        rows[1]["chunking_version"] = "chunking-v2"
    elif defect in ("counter", "template"):
        rows[0][
            "token_counter_id" if defect == "counter" else "template_version"
        ] = "different-version"
    path = write_chunks(tmp_path, rows)
    if defect == "missing":
        path.unlink()
    elif defect in ("utf8", "json", "nan", "infinity", "empty", "not-object"):
        path.write_bytes(
            {
                "utf8": b"\xff",
                "json": b"{bad}\n",
                "nan": b"NaN\n",
                "infinity": b"Infinity\n",
                "empty": b"",
                "not-object": b"[]\n",
            }[defect]
        )
    elif defect == "blank-line":
        path.write_bytes(path.read_bytes().replace(b"\n", b"\n\n", 1))
    elif defect == "two-final-lf":
        path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(EmbeddingInputError) as caught:
        load_chunk_inputs(path, Utf8BytesDiv3Counter())
    assert caught.value.code == code
    assert str(tmp_path) not in str(caught.value)


def test_passage_template_prefix_hash_and_estimate(tmp_path: Path) -> None:
    """T006-S03: template filters untitled only when building final input."""
    config = EmbeddingConfig(dimensions=2, passage_prefix="passage: ")
    loaded = load_chunk_inputs(
        write_chunks(tmp_path, [synthetic_record()]), Utf8BytesDiv3Counter()
    )
    chunk = loaded.chunks[0]
    final = build_passage_input(config, chunk.section_path, chunk.text)
    expected = "passage: Synthetic heading\n\nSynthetic sentence number 0."
    assert final == expected
    assert chunk.section_path == ("(untitled)", "Synthetic heading")
    counter = Utf8BytesDiv3Counter()
    assert counter.count(final) == (len(expected.encode()) + 2) // 3
    assert counter.count(final) > counter.count(chunk.text)
    assert (
        hashlib.sha256(final.encode()).hexdigest()
        == hashlib.sha256(expected.encode()).hexdigest()
    )


def test_cache_key_uses_canonical_length_delimited_fields(
    tmp_path: Path,
) -> None:
    """T006-S04: canonical keys produce only lowercase hex entry filenames."""
    fields = (DEFAULT_MODEL, "2", "b" * 64)
    canonical = len(fields).to_bytes(8, "big") + b"".join(
        len(value.encode()).to_bytes(8, "big") + value.encode()
        for value in fields
    )
    expected = hashlib.sha256(canonical).hexdigest()
    assert cache_key(DEFAULT_MODEL, 2, "b" * 64) == expected
    assert cache_key("ab", 2, "c") != cache_key("a", 2, "bc")
    cache = EmbeddingCache(tmp_path)
    cache.put_batch([entry()])
    assert sorted(p.name for p in tmp_path.iterdir()) == [expected + ".entry"]


def test_cache_entry_roundtrip_and_metadata_layout() -> None:
    """T006-S05: one compact ASCII metadata line precedes exact vector bytes."""
    original = entry()
    encoded = encode_entry(original)
    header, binary = encoded.split(b"\n", 1)
    metadata = json.loads(header)
    assert (
        header
        == json.dumps(
            metadata, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        ).encode()
    )
    assert tuple(metadata) == tuple(
        sorted(
            (
                "format",
                "model",
                "dimensions",
                "input_sha256",
                "vector_sha256",
                "estimated_tokens",
                "counter_id",
                "embedded_on",
                "batch_id",
                "batch_input_count",
                "batch_estimated_tokens",
                "batch_prompt_tokens",
                "batch_total_tokens",
            )
        )
    )
    assert binary == f32_bytes((1.0, 0.0))
    decoded = decode_entry(
        encoded, model=DEFAULT_MODEL, dimensions=2, input_sha256="b" * 64
    )
    assert decoded == original
    assert encode_entry(decoded) == encoded


@pytest.mark.parametrize(
    "defect",
    [
        "no-newline",
        "json",
        "format",
        "model",
        "dimensions",
        "input",
        "short-vector",
        "long-vector",
        "checksum",
        "nonfinite",
        "negative-estimate",
        "counter",
        "date",
        "batch-id",
        "batch-count",
        "batch-estimate",
        "batch-prompt",
        "batch-total",
        "missing-field",
    ],
)
def test_cache_corruption_never_silently_reembeds(defect: str) -> None:
    """T006-S06: reject every cache defect with cache-entry-corrupt."""
    vector = f32_bytes((1.0, 0.0))
    raw = encode_entry(entry())
    header, _ = raw.split(b"\n", 1)
    metadata = json.loads(header)
    changes: dict[str, tuple[str, object]] = {
        "format": ("format", "unknown"),
        "model": ("model", "other"),
        "dimensions": ("dimensions", 3),
        "input": ("input_sha256", "c" * 64),
        "checksum": ("vector_sha256", "0" * 64),
        "negative-estimate": ("estimated_tokens", -1),
        "counter": ("counter_id", ""),
        "date": ("embedded_on", "not-a-date"),
        "batch-id": ("batch_id", "z" * 64),
        "batch-count": ("batch_input_count", 0),
        "batch-estimate": ("batch_estimated_tokens", -1),
        "batch-prompt": ("batch_prompt_tokens", True),
        "batch-total": ("batch_total_tokens", -1),
    }
    if defect in changes:
        key, value = changes[defect]
        metadata[key] = value
    if defect == "missing-field":
        del metadata["batch_total_tokens"]
    elif defect == "short-vector":
        vector = vector[:-1]
    elif defect == "long-vector":
        vector += b"\x00"
    elif defect == "nonfinite":
        vector = f32_bytes((math.nan, 0.0))
        metadata["vector_sha256"] = hashlib.sha256(vector).hexdigest()
    raw = json.dumps(metadata).encode() + b"\n" + vector
    if defect == "no-newline":
        raw = b"{}"
    elif defect == "json":
        raw = b"{bad}\n" + vector
    with pytest.raises(EmbeddingCacheError) as caught:
        decode_entry(
            raw, model=DEFAULT_MODEL, dimensions=2, input_sha256="b" * 64
        )
    assert caught.value.code == "cache-entry-corrupt"


@pytest.mark.parametrize(
    "field",
    [
        "embedded_on",
        "batch_input_count",
        "batch_estimated_tokens",
        "batch_prompt_tokens",
        "batch_total_tokens",
    ],
)
def test_cache_rejects_inconsistent_batch_fields(
    tmp_path: Path, field: str
) -> None:
    """T006-S07: entries sharing a batch ID must share every batch field."""
    batch_id = hashlib.sha256(("b" * 64 + "\n" + "c" * 64).encode()).hexdigest()
    first = entry(batch_id=batch_id, count=2, estimate=40)
    second = replace(first, input_sha256="c" * 64)
    changed = replace(
        second,
        **{
            field: "2026-11-18"
            if field == "embedded_on"
            else getattr(second, field) + 1
        },
    )
    cache = EmbeddingCache(tmp_path)
    cache.put_batch([first, second])
    target = tmp_path / (
        cache_key(DEFAULT_MODEL, 2, changed.input_sha256) + ".entry"
    )
    target.write_bytes(encode_entry(changed))
    with pytest.raises(EmbeddingCacheError) as caught:
        cache.get(DEFAULT_MODEL, 2, first.input_sha256)
        cache.get(DEFAULT_MODEL, 2, changed.input_sha256)
    assert caught.value.code == "cache-entry-corrupt"


@pytest.mark.parametrize("new_entry", [False, True])
def test_cache_ignores_stale_temp_and_atomic_failure_keeps_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, new_entry: bool
) -> None:
    """T006-S08: failed replacement retains old entries without staging."""
    cache = EmbeddingCache(tmp_path)
    original = entry()
    cache.put_batch([original])
    stale = tmp_path / "stale.tmp"
    stale.write_bytes(b"incomplete offline staging")
    assert cache.get(DEFAULT_MODEL, 2, original.input_sha256) == original
    assert cache.get(DEFAULT_MODEL, 2, "c" * 64) is None
    stale.unlink()
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}

    def fail_replace(*args: object, **kwargs: object) -> None:
        raise OSError("synthetic replace failure")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises((OSError, EmbeddingCacheError)):
        candidate = (
            entry("c" * 64)
            if new_entry
            else replace(original, embedded_on="2026-11-18")
        )
        cache.put_batch([candidate])
    assert {p.name: p.read_bytes() for p in tmp_path.iterdir()} == before
    assert list(tmp_path.glob("*.tmp")) == []


def test_float32_little_endian_exactness_and_norm() -> None:
    """T006-S09: vector storage is exact float32 with an fsum-based norm."""
    expected = b"\x00\x00\x80\x3f\x00\x00\x00\xbf"
    assert pack_vector((1.0, -0.5)) == expected
    assert unpack_vector(expected, 2) == (1.0, -0.5)
    assert vector_norm((3.0, 4.0)) == 5.0
    assert vector_norm((1e100, 1e100)) == pytest.approx(math.sqrt(2) * 1e100)


@pytest.mark.parametrize(
    "values", [(math.nan,), (math.inf,), (-math.inf,), (1e40,)]
)
def test_float32_overflow_and_nonfinite_rejected(
    values: tuple[float, ...],
) -> None:
    """T006-S10: reject nonfinite and overflowing floats before storage."""
    with pytest.raises(EmbeddingProviderError):
        pack_vector(values)


@pytest.mark.parametrize("raw", [b"", b"123", f32_bytes((math.inf, 0.0))])
def test_unpack_rejects_invalid_vectors(raw: bytes) -> None:
    """T006-S11: reject vector byte count and nonfinite storage defects."""
    with pytest.raises(EmbeddingCacheError):
        unpack_vector(raw, 2)


def test_manifest_report_aggregate_unique_batches_and_order(
    tmp_path: Path,
) -> None:
    """T006-S12: aggregate whole unique batches, retaining earliest UTC date."""
    rows = [synthetic_record(i) for i in range(3)]
    loaded = load_chunk_inputs(
        write_chunks(tmp_path, rows), Utf8BytesDiv3Counter()
    )
    first = entry(batch_id="d" * 64, count=5, estimate=100, prompt=13, total=17)
    second = entry(
        "c" * 64,
        batch_id="e" * 64,
        count=1,
        estimate=20,
        prompt=19,
        total=23,
        date="2026-11-18",
    )
    entries = {
        loaded.chunks[0].chunk_id: first,
        loaded.chunks[1].chunk_id: first,
        loaded.chunks[2].chunk_id: second,
    }
    manifest = build_manifest(
        EmbeddingConfig(dimensions=2),
        loaded,
        loaded.chunks,
        entries,
        custom_base_url_used=True,
    )
    report = build_report(manifest, paper_count=1)
    assert tuple(manifest) == MANIFEST_KEYS
    assert tuple(report) == REPORT_KEYS
    for output in (manifest, report):
        assert output["usage"] == {"prompt_tokens": 32, "total_tokens": 40}
        assert output["estimated_input_tokens"] == 120
        assert output["provider_input_count"] == 6
        assert output["creation_date"] == FIXED_DATE
        assert output["chunks_sha256"] == loaded.chunks_sha256
        assert output["chunk_count"] == output["vector_count"] == 3
        assert output["custom_base_url_used"] is True
        assert output["status"] == "complete"
    assert manifest["normalization"] == {
        "declared": "l2",
        "observed_norm_min": 1.0,
        "observed_norm_max": 1.0,
    }
    assert manifest["vectors_file"] == "vectors.f32"
    assert manifest["vectors_dtype"] == "float32-le"
    assert (
        manifest["vectors_sha256"]
        == hashlib.sha256(first.vector_bytes * 3).hexdigest()
    )
    manifest_entries = cast(list[dict[str, str]], manifest["entries"])
    assert [row["chunk_id"] for row in manifest_entries] == sorted(entries)
    assert all(
        tuple(row) == ("chunk_id", "input_sha256") for row in manifest_entries
    )
    assert report["approximate_cost"] == {
        "usd": round(40 * 0.02 / 1_000_000, 6),
        "label": "approximate",
        "basis": (
            "reported usage x USD 0.02 per 1M tokens; official model page; "
            "team billing not verified"
        ),
    }
    for output in (manifest, report):
        rendered = render_json(output)
        assert (
            rendered
            == (
                json.dumps(output, ensure_ascii=False, indent=2) + "\n"
            ).encode()
        )
        assert rendered == render_json(output)
        for forbidden in (
            FAKE_KEY,
            "https://",
            str(tmp_path),
            "Synthetic sentence",
            "cache_hits",
            "cache_misses",
            "api_calls",
            "retries",
            "x-ratelimit",
        ):
            assert forbidden.encode() not in rendered


def test_partial_manifest_reports_the_original_larger_batch(
    tmp_path: Path,
) -> None:
    """T006-S13: a warm subset retains whole-batch totals and original date."""
    loaded = load_chunk_inputs(
        write_chunks(tmp_path, [synthetic_record(i) for i in range(5)]),
        Utf8BytesDiv3Counter(),
    )
    selected = loaded.chunks[:3]
    stored = entry(
        batch_id="d" * 64, count=5, estimate=100, prompt=13, total=17
    )
    manifest = build_manifest(
        EmbeddingConfig(dimensions=2),
        loaded,
        selected,
        {chunk.chunk_id: stored for chunk in selected},
    )
    assert manifest["status"] == "partial"
    assert manifest["vector_count"] == 3
    assert manifest["provider_input_count"] == 5
    assert manifest["estimated_input_tokens"] == 100
    assert manifest["usage"] == {"prompt_tokens": 13, "total_tokens": 17}


def test_json_render_keeps_unicode_and_final_lf() -> None:
    """T006-S14: retain Unicode, insertion order, and final LF in JSON."""
    assert render_json({"z": "é", "a": 1}) == (
        '{\n  "z": "é",\n  "a": 1\n}\n'.encode()
    )


def test_all_three_files_use_one_shared_atomic_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T006-S15: publish the binary, manifest, and report in one shared call."""
    calls: list[Mapping[Path, bytes]] = []

    def capture(outputs: Mapping[Path, bytes]) -> None:
        calls.append(outputs)

    monkeypatch.setattr("sciscope.chunking.output.write_outputs", capture)
    paths = (
        tmp_path / "vectors.f32",
        tmp_path / "manifest.json",
        tmp_path / "embedding_report.json",
    )
    write_embedding_files(b"vectors", {"a": 1}, {"b": 2}, *paths)
    assert calls == [
        {
            paths[0]: b"vectors",
            paths[1]: b'{\n  "a": 1\n}\n',
            paths[2]: b'{\n  "b": 2\n}\n',
        }
    ]


def test_atomic_publish_failure_restores_all_previous_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T006-S16: replacement failure leaves all old files and no staging."""
    paths = tuple(
        tmp_path / name
        for name in ("vectors.f32", "manifest.json", "embedding_report.json")
    )
    for path in paths:
        path.write_bytes(b"previous synthetic output")
    real_replace = os.replace
    calls = 0

    def fail_second(source: str | Path, target: str | Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic publish failure")
        real_replace(source, target)

    monkeypatch.setattr(os, "replace", fail_second)
    with pytest.raises(OSError):
        write_embedding_files(b"new", {"a": 1}, {"b": 2}, *paths)
    assert all(
        path.read_bytes() == b"previous synthetic output" for path in paths
    )
    assert list(tmp_path.glob("*.tmp")) == []
