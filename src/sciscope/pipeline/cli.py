"""Chunk pipeline CLI and typed embedding command seam."""

from __future__ import annotations

import argparse
import io
import os
import random
import sys
import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Never

from sciscope.chunking.config import ChunkConfig, ChunkingError, ConfigError
from sciscope.chunking.core import chunk_sections
from sciscope.chunking.counter import Utf8BytesDiv3Counter
from sciscope.chunking.loader import (
    SourceConsistencyError,
    SourceInputError,
    load_sources,
)
from sciscope.chunking.output import chunk_report, write_chunk_files
from sciscope.embedding.config import (
    EmbeddingCacheError,
    EmbeddingConfig,
    EmbeddingConfigError,
    EmbeddingInputError,
    EmbeddingProviderError,
)
from sciscope.embedding.openai_client import (
    OpenAIConnection,
    OpenAIEmbedder,
    Transport,
    UrllibTransport,
    embeddings_url,
    read_api_key,
    read_base_url,
)
from sciscope.embedding.pipeline import EmbedOptions, EmbedStats, run_embedding
from sciscope.embedding.provider import Embedder


class _Parser(argparse.ArgumentParser):
    """Convert usage errors to sanitized status codes."""

    def error(self, message: str) -> Never:
        """Raise a stable usage code without echoing argument values."""
        raise ConfigError("invalid-usage")


def _configure_console() -> None:
    """Use UTF-8 output when the stream supports reconfiguration."""
    for stream in (sys.stdout, sys.stderr):
        try:
            reconfigure = getattr(stream, "reconfigure", None)
            if reconfigure is not None:
                reconfigure(
                    encoding="utf-8", errors="backslashreplace", newline="\n"
                )
        except (AttributeError, ValueError, io.UnsupportedOperation):
            continue


def _parser() -> _Parser:
    """Build the chunk and explicitly selected embedding command arguments."""
    parser = _Parser(description="Generate paragraph chunks")
    commands = parser.add_subparsers(
        dest="command", required=True, parser_class=_Parser
    )
    chunk = commands.add_parser("chunk")
    chunk.add_argument(
        "--sections",
        type=Path,
        default=Path("data/processed/pilot/sections.jsonl"),
    )
    chunk.add_argument(
        "--paragraphs",
        type=Path,
        default=Path("data/processed/pilot/paragraphs.jsonl"),
    )
    chunk.add_argument(
        "--parse-report",
        type=Path,
        default=Path("data/pilot/parse_report.json"),
    )
    chunk.add_argument(
        "--chunks",
        type=Path,
        default=Path("data/processed/pilot/chunks.jsonl"),
    )
    chunk.add_argument(
        "--report",
        type=Path,
        default=Path("data/pilot/chunk_report.json"),
    )
    chunk.add_argument("--operational-cap-tokens", type=int, default=384)
    chunk.add_argument("--prefix-reserve-tokens", type=int, default=0)
    embed = commands.add_parser("embed")
    embed.add_argument("--live", action="store_true")
    embed.add_argument("--provider", choices=("openai",), default="openai")
    embed.add_argument(
        "--chunks",
        type=Path,
        default=Path("data/processed/pilot/chunks.jsonl"),
    )
    embed.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("data/embeddings/pilot/cache"),
    )
    embed.add_argument(
        "--vectors",
        type=Path,
        default=Path("data/embeddings/pilot/vectors.f32"),
    )
    embed.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/embeddings/pilot/manifest.json"),
    )
    embed.add_argument(
        "--report",
        type=Path,
        default=Path("data/pilot/embedding_report.json"),
    )
    embed.add_argument("--model", default="text-embedding-3-small")
    embed.add_argument("--dimensions", type=int, default=1536)
    embed.add_argument("--passage-prefix", default="")
    embed.add_argument("--query-prefix", default="")
    embed.add_argument("--operational-cap-tokens", type=int, default=384)
    embed.add_argument("--max-inputs-per-request", type=int, default=8)
    embed.add_argument("--max-tokens-per-request", type=int, default=2048)
    embed.add_argument("--max-attempts", type=int, default=3)
    embed.add_argument("--limit", type=int)
    return parser


def _check_output_paths(args: argparse.Namespace) -> None:
    """Reject output aliases before reading any source file."""
    inputs = {
        args.sections.resolve(),
        args.paragraphs.resolve(),
        args.parse_report.resolve(),
    }
    chunks_path = args.chunks.resolve()
    report_path = args.report.resolve()
    if (
        chunks_path == report_path
        or chunks_path in inputs
        or report_path in inputs
    ):
        raise ConfigError("output-path-conflict")


def _utc_date() -> str:
    """Return the current UTC date as YYYY-MM-DD."""
    return datetime.now(UTC).date().isoformat()


def _embed(
    args: argparse.Namespace,
    *,
    environ: Mapping[str, str] | None,
    transport_factory: Callable[[OpenAIConnection], Transport],
    sleep: Callable[[float], None],
    monotonic: Callable[[], float],
    uniform: Callable[[float, float], float],
    utc_date: Callable[[], str],
) -> int:
    """Run explicitly selected embedding with sanitized numeric CLI output."""
    try:
        config = EmbeddingConfig(
            provider=args.provider,
            model=args.model,
            dimensions=args.dimensions,
            passage_prefix=args.passage_prefix,
            query_prefix=args.query_prefix,
            operational_cap_tokens=args.operational_cap_tokens,
            max_inputs_per_request=args.max_inputs_per_request,
            max_tokens_per_request=args.max_tokens_per_request,
            max_attempts=args.max_attempts,
        )
        if args.limit is not None and args.limit < 1:
            raise EmbeddingConfigError("invalid-limit")
        if not args.live:
            raise EmbeddingConfigError("live-not-selected")
        options = EmbedOptions(
            args.chunks.resolve(),
            args.cache_dir.resolve(),
            args.vectors.resolve(),
            args.manifest.resolve(),
            args.report.resolve(),
            args.limit,
        )
        _check_embedding_paths(options)
        environment = os.environ if environ is None else environ
        key = read_api_key(environment)
        base, custom = read_base_url(environment)
        connection = OpenAIConnection(key, embeddings_url(base), custom)

        def create_embedder() -> Embedder:
            return OpenAIEmbedder(
                config,
                transport_factory(connection),
                sleep=sleep,
                monotonic=monotonic,
                uniform=uniform,
            )

        stats = run_embedding(
            options,
            config,
            Utf8BytesDiv3Counter(),
            embedder_factory=create_embedder,
            utc_date=utc_date,
            custom_base_url_used=custom,
        )
    except (EmbeddingConfigError, EmbeddingInputError) as error:
        print(f"error: {error.code}", file=sys.stderr)
        return 2
    except EmbeddingCacheError as error:
        print(f"error: {error.code}", file=sys.stderr)
        if error.entry_key is not None:
            print(f"entry: {error.entry_key}", file=sys.stderr)
        return 1
    except EmbeddingProviderError as error:
        print(f"error: {error.code}", file=sys.stderr)
        return 1
    _print_embedding_stats(stats)
    return 0


def _check_embedding_paths(options: EmbedOptions) -> None:
    """Reject output aliases before file or process-environment access."""
    outputs = (options.vectors, options.manifest, options.report)
    if (
        len(set(outputs)) != len(outputs)
        or options.chunks in outputs
        or options.cache_dir in outputs
    ):
        raise EmbeddingConfigError("output-path-conflict")


def _print_embedding_stats(stats: EmbedStats) -> None:
    """Print ephemeral numeric counts and this run's final safe headers."""
    print(
        f"chunks: {stats.chunk_count} selected: {stats.selected_count} "
        f"unique-inputs: {stats.unique_input_count} "
        f"cache-hits: {stats.cache_hits} "
        f"cache-misses: {stats.cache_misses} api-calls: {stats.api_calls} "
        f"retries: {stats.retries} status: {stats.status}"
    )
    print(
        f"usage-total-tokens: {stats.usage.total_tokens} "
        f"estimated-input-tokens: {stats.estimated_input_tokens}"
    )
    for name, value in stats.rate_limit_headers.items():
        if (
            name.startswith("x-ratelimit-")
            and len(value) <= 64
            and all(0x20 <= ord(char) <= 0x7E for char in value)
        ):
            print(f"{name}: {value}")


def main(
    argv: list[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    transport_factory: Callable[
        [OpenAIConnection], Transport
    ] = UrllibTransport,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    uniform: Callable[[float, float], float] = random.uniform,
    utc_date: Callable[[], str] = _utc_date,
) -> int:
    """Run chunk generation with sanitized statuses and numeric output."""
    _configure_console()
    try:
        args = _parser().parse_args(argv)
        if args.command == "embed":
            return _embed(
                args,
                environ=environ,
                transport_factory=transport_factory,
                sleep=sleep,
                monotonic=monotonic,
                uniform=uniform,
                utc_date=utc_date,
            )
        config = ChunkConfig(
            operational_cap_tokens=args.operational_cap_tokens,
            prefix_reserve_tokens=args.prefix_reserve_tokens,
        )
        _check_output_paths(args)
        bundle = load_sources(args.sections, args.paragraphs, args.parse_report)
        counter = Utf8BytesDiv3Counter()
        chunks = chunk_sections(
            bundle.sections, bundle.paragraphs, config, counter
        )
        report = chunk_report(chunks, bundle, config, counter.counter_id)
        write_chunk_files(
            chunks,
            bundle,
            config,
            counter.counter_id,
            args.chunks,
            args.report,
        )
    except (ConfigError, SourceInputError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except (SourceConsistencyError, ChunkingError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except OSError:
        print("error: output-write-failed", file=sys.stderr)
        return 1
    summary = report["summary"]
    excluded_total = (
        summary["excluded_elements"] + summary["back_matter_excluded"]
    )
    print(
        f"papers: {summary['paper_count']} "
        f"sections: {summary['section_count']} "
        f"chunks: {summary['chunk_count']} "
        f"hard-split: {summary['hard_split_chunks']} "
        f"excluded: {excluded_total}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
