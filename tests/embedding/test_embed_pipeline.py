"""T006 synthetic offline RED contracts for resume, batching, and the CLI."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tomllib
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

import pytest
from embed_fixtures import (
    FAKE_ENV,
    FAKE_KEY,
    FIXED_DATE,
    AdditiveTransport,
    RetryClock,
    ScriptedTransport,
    response,
    synthetic_record,
    write_chunks,
)

from sciscope.chunking.counter import Utf8BytesDiv3Counter
from sciscope.embedding.cache import cache_key
from sciscope.embedding.config import (
    EmbeddingConfig,
    EmbeddingInputError,
)
from sciscope.embedding.openai_client import (
    OpenAIConnection,
    OpenAIEmbedder,
    Transport,
)
from sciscope.embedding.pipeline import EmbedOptions, EmbedStats, run_embedding
from sciscope.embedding.provider import Embedder
from sciscope.pipeline.cli import main


@dataclass
class RunFiles:
    """Keep input, cache, and the three published synthetic artifact paths."""

    root: Path

    @property
    def chunks(self) -> Path:
        """Return the synthetic JSONL source path."""
        return self.root / "chunks.jsonl"

    @property
    def cache(self) -> Path:
        """Return the isolated cache directory."""
        return self.root / "cache"

    @property
    def outputs(self) -> tuple[Path, Path, Path]:
        """Return vector, manifest, and report paths in publication order."""
        return (
            self.root / "vectors.f32",
            self.root / "manifest.json",
            self.root / "embedding_report.json",
        )

    def options(self, limit: int | None = None) -> EmbedOptions:
        """Build the pipeline's immutable file and selection options."""
        return EmbedOptions(self.chunks, self.cache, *self.outputs, limit=limit)

    def argv(self, *extra: str) -> list[str]:
        """Build CLI arguments that never contain a key or environment URL."""
        vectors, manifest, report = self.outputs
        return [
            "embed",
            "--chunks",
            str(self.chunks),
            "--cache-dir",
            str(self.cache),
            "--vectors",
            str(vectors),
            "--manifest",
            str(manifest),
            "--report",
            str(report),
            "--dimensions",
            "2",
            *extra,
        ]

    def bytes(self) -> tuple[bytes, ...]:
        """Read the three artifacts for exact reproducibility assertions."""
        return tuple(path.read_bytes() for path in self.outputs)

    def report(self) -> dict[str, object]:
        """Read report JSON as object-valued data."""
        return cast(dict[str, object], json.loads(self.outputs[2].read_bytes()))


def prepare(root: Path, count: int = 10) -> RunFiles:
    """Write synthetic records in file order distinct from chunk ID order."""
    write_chunks(root, [synthetic_record(i) for i in range(count)])
    return RunFiles(root)


@dataclass
class TransportFactory:
    """Record lazy transport creation without retaining credentials in repr."""

    transport: Transport
    calls: int = 0
    connections: list[OpenAIConnection] = field(
        default_factory=list, repr=False
    )

    def __call__(self, connection: OpenAIConnection) -> Transport:
        """Return the supplied fake and record sanitized connection objects."""
        self.calls += 1
        self.connections.append(connection)
        return self.transport


class UnreadableEnvironment(Mapping[str, str]):
    """Fail if a no-live invocation inspects the injected environment."""

    def __getitem__(self, key: str) -> str:
        """Reject environment key access."""
        raise AssertionError("Environment must not be read")

    def __iter__(self) -> Iterator[str]:
        """Reject environment enumeration."""
        raise AssertionError("Environment must not be read")

    def __len__(self) -> int:
        """Reject environment length access."""
        raise AssertionError("Environment must not be read")


def invoke(
    files: RunFiles,
    transport: Transport,
    *extra: str,
    environ: Mapping[str, str] = FAKE_ENV,
    date: str = FIXED_DATE,
) -> tuple[int, TransportFactory]:
    """Run the CLI using only injected environment, time, and transport."""
    factory = TransportFactory(transport)
    clock = RetryClock()
    code = main(
        files.argv(*extra),
        environ=environ,
        transport_factory=factory,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
        uniform=clock.uniform,
        utc_date=lambda: date,
    )
    return code, factory


def forbidden_embedder() -> Embedder:
    """Fail if the pipeline creates a provider for a warm cache."""
    raise AssertionError("Warm runs must never construct an embedder")


def test_cold_and_warm_three_file_identity_and_lazy_factories(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T006-P01: cold outputs sort by ID and warm runs create no provider."""
    files = prepare(tmp_path, count=4)
    cold = AdditiveTransport()
    code, factory = invoke(files, cold, "--live", "--provider", "openai")
    assert code == 0 and factory.calls == 1
    before = files.bytes()
    manifest = json.loads(before[1])
    entries = manifest["entries"]
    assert [row["chunk_id"] for row in entries] == sorted(
        str(synthetic_record(i)["chunk_id"]) for i in range(4)
    )
    for index, row in enumerate(entries):
        key = cache_key("text-embedding-3-small", 2, row["input_sha256"])
        cached = (
            (files.cache / (key + ".entry")).read_bytes().split(b"\n", 1)[1]
        )
        assert before[0][index * 8 : (index + 1) * 8] == cached
    stats = run_embedding(
        files.options(),
        EmbeddingConfig(dimensions=2),
        Utf8BytesDiv3Counter(),
        embedder_factory=forbidden_embedder,
        utc_date=lambda: "2026-11-20",
    )
    assert stats.api_calls == 0 and stats.cache_hits == 4
    assert files.bytes() == before
    capsys.readouterr()
    code, warm_factory = invoke(files, ScriptedTransport([]), "--live")
    assert code == 0 and warm_factory.calls == 0
    assert files.bytes() == before
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 2
    assert "api-calls: 0 retries: 0 status: complete" in lines[0]


def test_crash_second_batch_persists_first_and_resume_matches_cold(
    tmp_path: Path,
) -> None:
    """T006-P02: failed batches preserve outputs and resume only misses."""
    resumed = prepare(tmp_path / "resume", count=6)
    cold = prepare(tmp_path / "cold", count=6)
    for path in resumed.outputs:
        path.write_bytes(b"previous synthetic output")
    failing = AdditiveTransport(fail_on_call=2)
    assert (
        invoke(resumed, failing, "--live", "--max-inputs-per-request", "2")[0]
        == 1
    )
    assert len(failing.calls) == 2
    assert len(list(resumed.cache.glob("*.entry"))) == 2
    assert resumed.bytes() == (b"previous synthetic output",) * 3
    success = AdditiveTransport()
    assert (
        invoke(resumed, success, "--live", "--max-inputs-per-request", "2")[0]
        == 0
    )
    assert [len(call.payload["input"]) for call in success.calls] == [2, 2]
    assert (
        invoke(
            cold, AdditiveTransport(), "--live", "--max-inputs-per-request", "2"
        )[0]
        == 0
    )
    assert resumed.bytes() == cold.bytes()


def test_limit_five_probe_full_resume_warm_and_smaller_subset(
    tmp_path: Path,
) -> None:
    """T006-P03: preserve probe accounting through full runs and subsets."""
    files = prepare(tmp_path / "resume")
    cold = prepare(tmp_path / "cold")
    probe = AdditiveTransport()
    assert invoke(files, probe, "--live", "--limit", "5")[0] == 0
    partial = files.report()
    assert partial["status"] == "partial" and partial["vector_count"] == 5
    assert partial["provider_input_count"] == 5
    assert partial["usage"] == {"prompt_tokens": 10, "total_tokens": 15}
    first_estimate = partial["estimated_input_tokens"]
    assert isinstance(first_estimate, int)
    later = AdditiveTransport()
    assert invoke(files, later, "--live", date="2026-11-18")[0] == 0
    complete = files.report()
    assert complete["status"] == "complete" and complete["vector_count"] == 10
    assert complete["usage"] == {"prompt_tokens": 20, "total_tokens": 30}
    assert complete["provider_input_count"] == 10
    assert complete["creation_date"] == FIXED_DATE
    sent = [
        text
        for call in probe.calls + later.calls
        for text in call.payload["input"]
    ]
    estimate = sum(Utf8BytesDiv3Counter().count(text) for text in sent)
    assert complete["estimated_input_tokens"] == estimate
    assert estimate > first_estimate
    assert invoke(cold, AdditiveTransport(), "--live")[0] == 0
    assert files.bytes() == cold.bytes()
    full_bytes = files.bytes()
    assert invoke(files, ScriptedTransport([]), "--live")[0] == 0
    assert files.bytes() == full_bytes
    assert (
        invoke(files, ScriptedTransport([]), "--live", "--limit", "3")[0] == 0
    )
    smaller = files.report()
    assert smaller["vector_count"] == 3 and smaller["provider_input_count"] == 5
    assert smaller["usage"] == partial["usage"]
    assert smaller["estimated_input_tokens"] == first_estimate
    assert smaller["creation_date"] == FIXED_DATE
    assert invoke(files, ScriptedTransport([]), "--live")[0] == 0
    assert files.bytes() == full_bytes


def test_nonadditive_batch_usage_is_summed_exactly_once(tmp_path: Path) -> None:
    """T006-P04: distinct persisted per-batch usage survives a probe resume."""
    files = prepare(tmp_path)
    assert (
        invoke(
            files,
            AdditiveTransport(usage_values=[(31, 37)]),
            "--live",
            "--limit",
            "5",
        )[0]
        == 0
    )
    transport = AdditiveTransport(usage_values=[(41, 47), (59, 61)])
    assert (
        invoke(files, transport, "--live", "--max-inputs-per-request", "3")[0]
        == 0
    )
    report = files.report()
    assert report["usage"] == {"prompt_tokens": 131, "total_tokens": 145}
    assert report["provider_input_count"] == 10
    before = files.bytes()
    assert invoke(files, ScriptedTransport([]), "--live")[0] == 0
    assert files.bytes() == before


def test_deduplication_input_hash_and_batch_metadata(tmp_path: Path) -> None:
    """T006-P05: identical final inputs are sent, estimated, and stored once."""
    rows = [
        synthetic_record(i, "Synthetic duplicate sentence.") for i in range(3)
    ]
    files = RunFiles(tmp_path)
    write_chunks(tmp_path, rows)
    transport = AdditiveTransport()
    assert invoke(files, transport, "--live")[0] == 0
    assert len(transport.calls) == 1
    final = "Synthetic heading\n\nSynthetic duplicate sentence."
    assert transport.calls[0].payload["input"] == [final]
    input_hash = hashlib.sha256(final.encode()).hexdigest()
    manifest = json.loads(files.bytes()[1])
    assert {row["input_sha256"] for row in manifest["entries"]} == {input_hash}
    report = files.report()
    assert report["vector_count"] == 3 and report["provider_input_count"] == 1
    assert report["estimated_input_tokens"] == Utf8BytesDiv3Counter().count(
        final
    )
    header = next(files.cache.glob("*.entry")).read_bytes().split(b"\n", 1)[0]
    metadata = json.loads(header)
    assert (
        metadata["batch_id"] == hashlib.sha256(input_hash.encode()).hexdigest()
    )


@pytest.mark.parametrize("token_limit", [40, 2048])
def test_batches_respect_both_limits_and_selection_order(
    tmp_path: Path, token_limit: int
) -> None:
    """T006-P06: split misses greedily by count and final-input estimates."""
    files = prepare(tmp_path, count=7)
    transport = AdditiveTransport()
    assert (
        invoke(
            files,
            transport,
            "--live",
            "--max-inputs-per-request",
            "3",
            "--max-tokens-per-request",
            str(token_limit),
        )[0]
        == 0
    )
    batches = [call.payload["input"] for call in transport.calls]
    assert [len(batch) for batch in batches] == (
        [3, 3, 1] if token_limit == 2048 else [2, 2, 2, 1]
    )
    texts = [text for batch in batches for text in batch]
    assert texts == [
        "Synthetic heading\n\nSynthetic sentence number " + str(i) + "."
        for i in range(7)
    ]
    for batch in batches:
        assert len(batch) <= 3
        assert (
            sum(Utf8BytesDiv3Counter().count(text) for text in batch)
            <= token_limit
        )
    for path in files.cache.glob("*.entry"):
        metadata = json.loads(path.read_bytes().split(b"\n", 1)[0])
        batch = next(
            batch
            for batch in batches
            if metadata["input_sha256"]
            in {hashlib.sha256(text.encode()).hexdigest() for text in batch}
        )
        hashes = sorted(
            hashlib.sha256(text.encode()).hexdigest() for text in batch
        )
        assert (
            metadata["batch_id"]
            == hashlib.sha256("\n".join(hashes).encode()).hexdigest()
        )
        assert metadata["batch_input_count"] == len(batch)


def test_reversed_response_indices_do_not_change_artifacts(
    tmp_path: Path,
) -> None:
    """T006-P07: float32 outputs ignore provider data ordering."""
    forward, reverse = (
        prepare(tmp_path / "forward"),
        prepare(tmp_path / "reverse"),
    )
    assert invoke(forward, AdditiveTransport(), "--live")[0] == 0
    assert (
        invoke(reverse, AdditiveTransport(reversed_indices=True), "--live")[0]
        == 0
    )
    assert forward.bytes() == reverse.bytes()


@pytest.mark.parametrize("cap", [384, 512])
def test_over_cap_has_no_provider_or_cache_write(
    tmp_path: Path, cap: int, capsys: pytest.CaptureFixture[str]
) -> None:
    """T006-P08: count the passage prefix and reject overflow before writes."""
    files = prepare(tmp_path, count=1)
    transport = ScriptedTransport([])
    code, factory = invoke(
        files,
        transport,
        "--live",
        "--passage-prefix",
        "x" * 1600,
        "--operational-cap-tokens",
        str(cap),
    )
    assert code == 2 and factory.calls == 0 and transport.calls == []
    assert capsys.readouterr().err == "error: input-over-cap\n"
    assert not list(files.cache.glob("*.entry"))
    assert all(not path.exists() for path in files.outputs)


def test_corrupt_cache_preserves_outputs_without_provider(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T006-P09: corrupt entries fail closed and identify only a hex key."""
    files = prepare(tmp_path, count=2)
    assert invoke(files, AdditiveTransport(), "--live")[0] == 0
    before = files.bytes()
    path = next(files.cache.glob("*.entry"))
    path.write_bytes(b"corrupt offline entry")
    capsys.readouterr()
    code, factory = invoke(files, ScriptedTransport([]), "--live")
    assert code == 1 and factory.calls == 0
    assert capsys.readouterr().err == (
        "error: cache-entry-corrupt\nentry: " + path.stem + "\n"
    )
    assert (
        files.bytes() == before
        and path.read_bytes() == b"corrupt offline entry"
    )


def test_changed_raw_chunks_update_provenance_but_reuse_inputs(
    tmp_path: Path,
) -> None:
    """T006-P10: raw-byte provenance changes independently of input hashes."""
    files = prepare(tmp_path, count=2)
    assert invoke(files, AdditiveTransport(), "--live")[0] == 0
    before = files.bytes()
    files.chunks.write_bytes(files.chunks.read_bytes().replace(b"\n", b"\r\n"))
    code, factory = invoke(files, ScriptedTransport([]), "--live")
    assert code == 0 and factory.calls == 0
    after = files.bytes()
    assert before[0] == after[0] and before[1] != after[1]
    assert (
        files.report()["chunks_sha256"]
        == hashlib.sha256(files.chunks.read_bytes()).hexdigest()
    )
    assert invoke(files, ScriptedTransport([]), "--live")[0] == 0
    assert files.bytes() == after


def test_no_live_checks_neither_environment_files_nor_transport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """T006-P11: no live selection exits 2 before reading any file or key."""
    files = RunFiles(tmp_path)

    def forbidden_read(*args: object, **kwargs: object) -> None:
        raise AssertionError("No-live invocation must not read files")

    monkeypatch.setattr(Path, "read_bytes", forbidden_read)
    monkeypatch.setattr(Path, "read_text", forbidden_read)
    code, factory = invoke(
        files, ScriptedTransport([]), environ=UnreadableEnvironment()
    )
    assert code == 2 and factory.calls == 0
    assert capsys.readouterr().err == "error: live-not-selected\n"


def test_live_missing_key_has_no_network_or_cache_write(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T006-P12: explicit live selection still requires a valid injected key."""
    files = prepare(tmp_path, count=1)
    code, factory = invoke(files, ScriptedTransport([]), "--live", environ={})
    assert code == 2 and factory.calls == 0
    assert capsys.readouterr().err == "error: missing-api-key\n"
    assert not list(files.cache.glob("*.entry"))


@pytest.mark.parametrize("provider", ["fake", "other", "local"])
def test_cli_provider_accepts_only_openai(
    tmp_path: Path, provider: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """T006-P13: synthetic providers cannot publish real CLI artifacts."""
    code, factory = invoke(
        RunFiles(tmp_path),
        ScriptedTransport([]),
        "--live",
        "--provider",
        provider,
        environ=UnreadableEnvironment(),
    )
    assert code == 2 and factory.calls == 0
    assert capsys.readouterr().err == "error: invalid-usage\n"


@pytest.mark.parametrize("limit", ["0", "-1", "not-an-int"])
def test_invalid_limit_exits_two(
    tmp_path: Path, limit: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """T006-P14: only positive integer selection limits are accepted."""
    code, factory = invoke(
        RunFiles(tmp_path),
        ScriptedTransport([]),
        "--live",
        "--limit",
        limit,
        environ=UnreadableEnvironment(),
    )
    assert code == 2 and factory.calls == 0
    assert capsys.readouterr().err == (
        "error: invalid-usage\n"
        if limit == "not-an-int"
        else "error: invalid-limit\n"
    )


@pytest.mark.parametrize("limit", ["4", "8"])
def test_limit_at_or_above_count_is_complete(
    tmp_path: Path, limit: str
) -> None:
    """T006-P15: selecting at least every record yields a complete set."""
    files = prepare(tmp_path, count=4)
    assert (
        invoke(files, AdditiveTransport(), "--live", "--limit", limit)[0] == 0
    )
    assert files.report()["status"] == "complete"


@pytest.mark.parametrize(
    ("left", "right"),
    [
        (left, right)
        for left in ("vectors", "manifest", "report")
        for right in ("chunks", "cache-dir", "vectors", "manifest", "report")
        if left != right
    ],
)
def test_output_path_aliases_rejected_before_reading(
    tmp_path: Path, left: str, right: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """T006-P16: resolve aliases before reading input or the environment."""
    files = RunFiles(tmp_path)
    alias = tmp_path / "nested" / ".." / "same"
    code, factory = invoke(
        files,
        ScriptedTransport([]),
        "--live",
        "--" + left,
        str(tmp_path / "same"),
        "--" + right,
        str(alias),
        environ=UnreadableEnvironment(),
    )
    assert code == 2 and factory.calls == 0
    assert capsys.readouterr().err == "error: output-path-conflict\n"


def test_console_exact_lines_custom_url_and_secret_absence(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T006-P17: print run counts only and persist only a custom-URL flag."""
    files = prepare(tmp_path, count=2)
    url = "https://private-gateway.invalid/root"
    code, factory = invoke(
        files,
        AdditiveTransport(),
        "--live",
        environ={
            **FAKE_ENV,
            "OPENAI_BASE_URL": url,
        },
    )
    assert code == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    estimate = files.report()["estimated_input_tokens"]
    assert captured.out == (
        "chunks: 2 selected: 2 unique-inputs: 2 cache-hits: 0 cache-misses: 2 "
        "api-calls: 1 retries: 0 status: complete\n"
        f"usage-total-tokens: 6 estimated-input-tokens: {estimate}\n"
        "x-ratelimit-remaining-tokens: 99\n"
    )
    assert factory.connections[0].custom_base_url_used is True
    assert files.report()["custom_base_url_used"] is True
    manifest = json.loads(files.bytes()[1])
    assert manifest["custom_base_url_used"] is True
    text = (
        captured.out
        + captured.err
        + "".join(data.decode("utf-8") for data in files.bytes()[1:])
    )
    for forbidden in (
        FAKE_KEY,
        FAKE_KEY[:8],
        url,
        str(tmp_path),
        "Synthetic sentence",
        "Synthetic heading",
    ):
        assert forbidden not in text
    for path in files.cache.glob("*.entry"):
        assert FAKE_KEY.encode() not in path.read_bytes()
        assert url.encode() not in path.read_bytes()


def test_console_counts_successful_calls_and_retried_attempts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """T006-P18: API-call counts exclude failed attempts that were retried."""
    files = prepare(tmp_path, count=1)
    transport = ScriptedTransport([response(429), response()])
    assert invoke(files, transport, "--live")[0] == 0
    assert "api-calls: 1 retries: 1 status: complete" in capsys.readouterr().out


def test_cli_publish_failure_keeps_previous_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """T006-P19: sanitize OSError and retain all previous output bytes."""
    files = prepare(tmp_path, count=2)
    assert invoke(files, AdditiveTransport(), "--live")[0] == 0
    before = files.bytes()
    capsys.readouterr()
    real_replace = os.replace

    def fail_manifest(source: str | Path, target: str | Path) -> None:
        if Path(target) == files.outputs[1]:
            raise OSError(FAKE_KEY + str(tmp_path))
        real_replace(source, target)

    monkeypatch.setattr(os, "replace", fail_manifest)
    code, factory = invoke(files, ScriptedTransport([]), "--live")
    assert code == 1 and factory.calls == 0
    captured = capsys.readouterr()
    assert captured.err == "error: output-write-failed\n" and captured.out == ""
    assert files.bytes() == before
    assert list(files.root.rglob("*.tmp")) == []


def test_embedding_ignores_and_approved_database_dependencies_only() -> None:
    """T006-P20: preserve artifact ignores and approved dependencies."""
    root = Path(__file__).resolve().parents[2]
    ignored = subprocess.run(
        ["git", "check-ignore", "--stdin"],
        input=(
            b"data/embeddings/pilot/cache/fake.entry\n"
            b"data/embeddings/pilot/vectors.f32\n"
            b"data/embeddings/pilot/manifest.json\n"
            b"data/pilot/embedding_report.json\n"
        ),
        cwd=root,
        capture_output=True,
        check=False,
    )
    assert ignored.returncode == 0
    assert ignored.stdout.decode("utf-8").splitlines() == [
        "data/embeddings/pilot/cache/fake.entry",
        "data/embeddings/pilot/vectors.f32",
        "data/embeddings/pilot/manifest.json",
    ]
    with (root / "pyproject.toml").open("rb") as file:
        project = tomllib.load(file)
    dependency_names = {
        dependency.split(">=", maxsplit=1)[0]
        for dependency in project["project"]["dependencies"]
    }
    assert {
        "alembic",
        "pgvector",
        "psycopg[binary]",
        "sqlalchemy",
    }.issubset(dependency_names)


def test_direct_pipeline_overflow_never_constructs_embedder(
    tmp_path: Path,
) -> None:
    """T006-P21: check the final input cap before any cache writes."""
    files = prepare(tmp_path, count=1)
    with pytest.raises(EmbeddingInputError) as caught:
        run_embedding(
            files.options(),
            EmbeddingConfig(passage_prefix="x" * 1600),
            Utf8BytesDiv3Counter(),
            embedder_factory=forbidden_embedder,
            utc_date=lambda: FIXED_DATE,
        )
    assert caught.value.code == "input-over-cap"
    assert not list(files.cache.glob("*.entry"))


def test_direct_pipeline_defers_provider_until_after_cache_lookup(
    tmp_path: Path,
) -> None:
    """T006-P22: reusable pipeline creates one embedder only for misses."""
    files = prepare(tmp_path, count=2)
    config = EmbeddingConfig(dimensions=2)
    transport = AdditiveTransport()
    clock = RetryClock()
    calls = 0

    def create() -> Embedder:
        nonlocal calls
        calls += 1
        return OpenAIEmbedder(
            config,
            transport,
            sleep=clock.sleep,
            monotonic=clock.monotonic,
            uniform=clock.uniform,
        )

    stats: EmbedStats = run_embedding(
        files.options(),
        config,
        Utf8BytesDiv3Counter(),
        embedder_factory=create,
        utc_date=lambda: FIXED_DATE,
    )
    assert calls == 1 and stats.api_calls == 1
    assert stats.cache_misses == 2 and stats.cache_hits == 0
