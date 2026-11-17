"""Chunk pipeline CLI and typed embedding command seam."""

from __future__ import annotations

import argparse
import io
import math
import os
import random
import sys
import time
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Never, cast

from sciscope.chunking.config import ChunkConfig, ChunkingError, ConfigError
from sciscope.chunking.core import chunk_sections
from sciscope.chunking.counter import Utf8BytesDiv3Counter
from sciscope.chunking.loader import (
    SourceConsistencyError,
    SourceInputError,
    load_sources,
)
from sciscope.chunking.output import chunk_report, write_chunk_files
from sciscope.chunking.validate import (
    Finding,
    load_chunk_records,
    read_validation_bytes,
    read_validation_json,
    validate_chunks,
)
from sciscope.delivery import package as delivery_package
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
from sciscope.embedding.pipeline import (
    EmbedOptions,
    EmbedStats,
    run_dry_run,
    run_embedding,
)
from sciscope.embedding.provider import Embedder
from sciscope.embedding.validate import (
    validate_embedding_set,
    validate_embedding_structure,
)

_DELIVERY_FIELDS = (
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
    "output_dir",
    "committed_manifest",
)


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
    embed.add_argument("--dry-run", action="store_true")
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
    validate = commands.add_parser("validate")
    validate.add_argument("--chunks-only", action="store_true")
    validate.add_argument("--allow-partial", action="store_true")
    validate.add_argument("--norm-tolerance", default=0.01)
    validate.add_argument("--operational-cap-tokens", type=int, default=384)
    validate.add_argument(
        "--sections",
        type=Path,
        default=Path("data/processed/pilot/sections.jsonl"),
    )
    validate.add_argument(
        "--paragraphs",
        type=Path,
        default=Path("data/processed/pilot/paragraphs.jsonl"),
    )
    validate.add_argument(
        "--parse-report",
        type=Path,
        default=Path("data/pilot/parse_report.json"),
    )
    validate.add_argument(
        "--chunks",
        type=Path,
        default=Path("data/processed/pilot/chunks.jsonl"),
    )
    validate.add_argument(
        "--chunk-report",
        type=Path,
        default=Path("data/pilot/chunk_report.json"),
    )
    validate.add_argument(
        "--vectors",
        type=Path,
        default=Path("data/embeddings/pilot/vectors.f32"),
    )
    validate.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/embeddings/pilot/manifest.json"),
    )
    validate.add_argument(
        "--report",
        type=Path,
        default=Path("data/pilot/embedding_report.json"),
    )
    deliver = commands.add_parser("deliver")
    defaults = delivery_package.DeliveryInputs()
    for name in _DELIVERY_FIELDS:
        deliver.add_argument(
            "--" + name.replace("_", "-"),
            type=Path,
            default=getattr(defaults, name),
        )
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


def _validate(args: argparse.Namespace) -> int:
    """Validate artifacts without environment or cache access."""
    tolerance = _norm_tolerance(args.norm_tolerance)
    config = ChunkConfig(operational_cap_tokens=args.operational_cap_tokens)
    try:
        sources = load_sources(
            args.sections, args.paragraphs, args.parse_report
        )
    except SourceConsistencyError as error:
        _print_findings([Finding(error.code, 1, ("report",))])
        return 1
    loaded = load_chunk_records(args.chunks)
    counter = Utf8BytesDiv3Counter()
    report = read_validation_json(args.chunk_report)
    findings = validate_chunks(
        sources,
        loaded.records,
        counter,
        operational_cap_tokens=config.operational_cap_tokens,
        chunk_report=report,
    )
    manifest: dict[str, Any] = {}
    status = 1
    if not args.chunks_only:
        manifest = read_validation_json(args.manifest)
        embedding_report = read_validation_json(args.report)
        vectors = read_validation_bytes(args.vectors)
        findings.extend(
            validate_embedding_set(
                loaded.records,
                chunks_sha256=loaded.chunks_sha256,
                manifest=manifest,
                report=embedding_report,
                vectors=vectors,
                counter=counter,
                operational_cap_tokens=config.operational_cap_tokens,
                norm_tolerance=tolerance,
                allow_partial=args.allow_partial,
            )
        )
        try:
            validate_embedding_structure(manifest, embedding_report)
        except SourceInputError as error:
            findings.append(Finding(error.code, 1, ("report",)))
            status = 2
    if findings:
        _print_findings(findings)
        return status
    text = (
        f"validated chunks: {len(loaded.records)} "
        f"sections: {len(sources.sections)} "
        f"papers: {len(sources.xml_sha256_by_doi)}"
    )
    if not args.chunks_only:
        norms = manifest["normalization"]
        text += (
            f" vectors: {manifest['vector_count']} status: {manifest['status']}"
            f" norm-min: {norms['observed_norm_min']:.9f}"
            f" norm-max: {norms['observed_norm_max']:.9f}"
        )
    print(text)
    return 0


def _norm_tolerance(value: object) -> float:
    """Parse finite tolerance with a specific sanitized usage error."""
    tolerance: float | None = None
    try:
        tolerance = float(cast(str | float, value))
    except (ValueError, TypeError, OverflowError):
        pass
    if (
        tolerance is None
        or not math.isfinite(tolerance)
        or not 0 < tolerance <= 1
    ):
        raise ConfigError("invalid-norm-tolerance")
    return tolerance


def _print_findings(findings: list[Finding]) -> None:
    """Merge semantic groups and print deterministic bounded diagnostics."""
    counts: dict[str, int] = {}
    identifiers: dict[str, list[str]] = {}
    for finding in findings:
        counts[finding.code] = counts.get(finding.code, 0) + finding.count
        ids = identifiers.setdefault(finding.code, [])
        for identifier in finding.ids:
            if identifier not in ids and len(ids) < 3:
                ids.append(identifier)
    for code in sorted(counts):
        print(
            f"error: {code} count: {counts[code]} "
            f"first: {','.join(identifiers[code])}",
            file=sys.stderr,
        )
    print(f"failures: {sum(counts.values())}", file=sys.stderr)


def _deliver(argv: list[str]) -> int:
    """Run delivery with dedicated parsing and sanitized finding diagnostics."""
    try:
        if "--help" in argv[1:] or "-h" in argv[1:]:
            options = " ".join(
                "[--" + name.replace("_", "-") + " PATH]"
                for name in _DELIVERY_FIELDS
            )
            print("usage: deliver " + options)
            return 0
        summary = delivery_package.run_delivery(_delivery_inputs(argv[1:]))
    except ConfigError:
        _print_findings([Finding("invalid-usage", 1, ("report",))])
        return 2
    except delivery_package.DeliveryError as error:
        _print_findings(list(error.findings))
        return error.exit_code
    except OSError:
        _print_findings([Finding("output-write-failed", 1, ("report",))])
        return 1
    except Exception:
        _print_findings([Finding("delivery-failed", 1, ("report",))])
        return 1
    print(
        f"delivered papers: {summary.papers} sections: {summary.sections} "
        f"chunks: {summary.chunks} vectors: {summary.vectors} "
        f"files: {summary.files}"
    )
    return 0


def _delivery_inputs(arguments: list[str]) -> delivery_package.DeliveryInputs:
    """Parse exact delivery options without argparse's environment probes."""
    defaults = delivery_package.DeliveryInputs()
    values = {name: getattr(defaults, name) for name in _DELIVERY_FIELDS}
    options = {"--" + name.replace("_", "-"): name for name in values}
    index = 0
    while index < len(arguments):
        option, equals, value = arguments[index].partition("=")
        if option not in options:
            raise ConfigError("invalid-usage")
        if not equals:
            index += 1
            if index == len(arguments) or arguments[index].startswith("-"):
                raise ConfigError("invalid-usage")
            value = arguments[index]
        values[options[option]] = Path(value)
        index += 1
    return delivery_package.DeliveryInputs(**values)


def _dry_run(args: argparse.Namespace) -> int:
    """Print a read-only embedding estimate without environment or transport."""
    try:
        if args.live:
            raise EmbeddingConfigError("dry-run-with-live")
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
        options = EmbedOptions(
            args.chunks.resolve(),
            args.cache_dir.resolve(),
            args.vectors.resolve(),
            args.manifest.resolve(),
            args.report.resolve(),
            args.limit,
        )
        stats = run_dry_run(options, config, Utf8BytesDiv3Counter())
    except (EmbeddingConfigError, EmbeddingInputError) as error:
        print(f"error: {error.code}", file=sys.stderr)
        return 2
    except EmbeddingCacheError as error:
        print(f"error: {error.code}", file=sys.stderr)
        if error.entry_key is not None:
            print(f"entry: {error.entry_key}", file=sys.stderr)
        return 1
    print(
        f"dry-run chunks: {stats.chunk_count} selected: {stats.selected_count} "
        f"unique-inputs: {stats.unique_input_count} "
        f"cache-hits: {stats.cache_hits} "
        f"cache-misses: {stats.cache_misses} "
        f"estimated-input-tokens: {stats.estimated_input_tokens} "
        f"estimated-tokens-to-send: {stats.estimated_tokens_to_send} "
        f"approximate-cost-usd: {stats.approximate_cost_usd:.6f} "
        "basis: estimator-based approximate"
    )
    return 0


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
    delivery_argv = sys.argv[1:] if argv is None else argv
    if delivery_argv and delivery_argv[0] == "deliver":
        return _deliver(delivery_argv)
    try:
        args = _parser().parse_args(argv)
        if args.command == "validate":
            return _validate(args)
        if args.command == "embed":
            if args.dry_run:
                return _dry_run(args)
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
