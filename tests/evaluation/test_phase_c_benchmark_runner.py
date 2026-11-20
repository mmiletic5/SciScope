"""Tests for the allowlist-scoped smoke input reader."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import scripts.phase_c_minilm_benchmark as benchmark_runner
from scripts.phase_c_minilm_benchmark import _extract_allowlisted_records


def test_reader_decodes_only_matching_question_objects(tmp_path: Path) -> None:
    """Invalid non-allowlisted content is never passed to the JSON decoder."""
    source = tmp_path / "questions.json"
    source.write_text(
        '{"questions":[{"question_id":"gq-sp-001","question":"ok"},'
        '{"question_id":"held-out","question":not-json}]}',
        encoding="utf-8",
    )

    records = _extract_allowlisted_records(source, frozenset({"gq-sp-001"}))

    assert records == [{"question_id": "gq-sp-001", "question": "ok"}]


def test_reader_uses_bounded_reads_without_buffering_the_full_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The reader uses bounded reads instead of materializing all bytes."""
    source = tmp_path / "questions.json"
    allowed = b'{"question_id":"gq-sp-001","question":"ok"}'
    held_out = b'{"question_id":"held-out","question":not-json}'
    source.write_bytes(b'{"questions":[' + allowed + b"," + held_out + b"]}")
    original_open = Path.open
    read_sizes: list[int] = []

    class ReadOnlyStream:
        def __init__(self, wrapped: object) -> None:
            self._wrapped = wrapped

        def __enter__(self) -> ReadOnlyStream:
            self._wrapped.__enter__()  # type: ignore[attr-defined]
            return self

        def __exit__(self, *args: object) -> None:
            self._wrapped.__exit__(*args)  # type: ignore[attr-defined]

        def read(self, size: int = -1) -> bytes:
            assert size > 0, "streaming reader must use bounded reads"
            value = self._wrapped.read(size)  # type: ignore[attr-defined]
            read_sizes.append(len(value))
            return value

    def open_with_observer(
        path: Path, *args: object, **kwargs: object
    ) -> object:
        stream = original_open(path, *args, **kwargs)
        if path == source:
            return ReadOnlyStream(stream)
        return stream

    monkeypatch.setattr(Path, "open", open_with_observer)

    records = _extract_allowlisted_records(source, frozenset({"gq-sp-001"}))

    assert records == [{"question_id": "gq-sp-001", "question": "ok"}]
    assert read_sizes
    assert all(0 <= size <= 4096 for size in read_sizes)


def test_reader_deserializes_only_allowlisted_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nonallowlisted record objects never reach the JSON deserializer."""
    source = tmp_path / "questions.json"
    source.write_text(
        '{"questions":[{"question_id":"gq-sp-001","question":"ok"},'
        '{"question_id":"held-out","question":"synthetic"}]}',
        encoding="utf-8",
    )
    original_loads = benchmark_runner.json.loads
    decoded: list[str] = []

    def observe_loads(value: str) -> object:
        decoded.append(value)
        return original_loads(value)

    monkeypatch.setattr(benchmark_runner.json, "loads", observe_loads)

    records = _extract_allowlisted_records(source, frozenset({"gq-sp-001"}))

    assert records == [{"question_id": "gq-sp-001", "question": "ok"}]
    assert len(decoded) == 1
    assert '"question_id":"gq-sp-001"' in decoded[0]


def test_reader_rejects_duplicate_allowlisted_id_across_stream_chunks(
    tmp_path: Path,
) -> None:
    """Duplicate allowed identities fail even when separated in the file."""
    source = tmp_path / "questions.json"
    source.write_text(
        '{"questions":[{"question_id":"gq-sp-001","question":"one"},'
        '{"question_id":"gq-sp-001","question":"two"}]}',
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="missing or duplicated"):
        _extract_allowlisted_records(source, frozenset({"gq-sp-001"}))


def test_reader_bounds_prefix_before_question_id(tmp_path: Path) -> None:
    """A malformed record cannot force buffering before its identity field."""
    source = tmp_path / "questions.json"
    source.write_text(
        '{"questions":[{"question":"'
        + "x" * 600
        + '","question_id":"gq-sp-001"}]}',
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="too far into its record"):
        _extract_allowlisted_records(source, frozenset({"gq-sp-001"}))


def test_offline_run_requires_saved_inputs_without_preparing_them(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Offline mode refuses missing inputs without paid preparation."""
    monkeypatch.setattr(benchmark_runner, "ARTIFACTS", tmp_path)
    monkeypatch.setattr(sys, "argv", ["phase_c_minilm_benchmark.py", "--run"])
    monkeypatch.setattr(
        benchmark_runner,
        "_prepare_inputs",
        lambda: pytest.fail("offline mode called the paid input preparer"),
    )

    with pytest.raises(RuntimeError, match="run --prepare-inputs separately"):
        benchmark_runner.main()
