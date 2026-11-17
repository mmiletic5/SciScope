"""Offline chunk pipeline command-line interface."""

from __future__ import annotations

import argparse
import io
import sys
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
    """Build the chunk-only CLI for this implementation phase."""
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


def main(argv: list[str] | None = None) -> int:
    """Run chunk generation with sanitized statuses and numeric output."""
    _configure_console()
    try:
        args = _parser().parse_args(argv)
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
