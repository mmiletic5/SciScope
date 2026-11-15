"""Search PLOS candidates or acquire a reviewed DOI selection."""

import argparse
import time
from collections.abc import Sequence
from pathlib import Path

from sciscope.plos_pilot.download import Now, _utc_now, download_selected
from sciscope.plos_pilot.metadata import write_metadata
from sciscope.plos_pilot.search import (
    Clock,
    Fetch,
    Sleep,
    _http_fetch,
    search_candidates,
)
from sciscope.plos_pilot.selection import validate_selection


def main(
    argv: Sequence[str] | None = None,
    *,
    fetch: Fetch = _http_fetch,
    sleep: Sleep = time.sleep,
    clock: Clock = time.monotonic,
    now: Now = _utc_now,
) -> int:
    """Run an offline-testable PLOS pilot command.

    Args:
        argv: Command arguments, or process arguments when omitted.
        fetch: Injected HTTP fetch callable.
        sleep: Injected delay callable.
        clock: Injected monotonic clock callable.
        now: Injected UTC wall-clock callable.

    Returns:
        Zero for success, two for invalid selection, or one for incomplete work.
    """
    parser = argparse.ArgumentParser(description="PLOS pilot acquisition")
    subcommands = parser.add_subparsers(dest="command", required=True)
    search_parser = subcommands.add_parser("search")
    search_parser.add_argument(
        "--candidates", type=Path, default=Path("data/pilot/candidates.jsonl")
    )
    download_parser = subcommands.add_parser("download")
    download_parser.add_argument(
        "--screening", type=Path, default=Path("data/pilot/screening.tsv")
    )
    download_parser.add_argument(
        "--selection", type=Path, default=Path("data/pilot/selection.tsv")
    )
    download_parser.add_argument(
        "--candidates", type=Path, default=Path("data/pilot/candidates.jsonl")
    )
    download_parser.add_argument(
        "--manifest", type=Path, default=Path("data/pilot/manifest.jsonl")
    )
    download_parser.add_argument(
        "--metadata", type=Path, default=Path("data/pilot/metadata.jsonl")
    )
    download_parser.add_argument(
        "--raw-dir", type=Path, default=Path("data/raw/plos")
    )
    download_parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args(argv)
    if args.command == "search":
        result = search_candidates(
            output_path=args.candidates,
            fetch=fetch,
            sleep=sleep,
            clock=clock,
        )
        for arm, count in result.arm_hits.items():
            print(f"{arm}: {count} hits (not eligible papers)")
        print(f"Unique candidates: {result.candidate_count}")
        print(f"Requests: {result.request_count}")
        return 0
    errors = validate_selection(
        screening_path=args.screening,
        selection_path=args.selection,
        candidate_path=args.candidates,
    )
    if errors:
        for error in errors:
            print(error)
        return 2
    summary = download_selected(
        screening_path=args.screening,
        selection_path=args.selection,
        candidate_path=args.candidates,
        manifest_path=args.manifest,
        raw_dir=args.raw_dir,
        repo_root=args.repo_root,
        fetch=fetch,
        sleep=sleep,
        clock=clock,
        now=now,
    )
    write_metadata(args.manifest, args.metadata, args.repo_root)
    print(f"Accepted: {len(summary.accepted)} {summary.accepted}")
    print(f"Duplicate: {len(summary.duplicate)} {summary.duplicate}")
    print(f"Conflict: {len(summary.conflict)}")
    for doi, reason in summary.conflict.items():
        print(f"  {doi}: {reason}")
    print(f"Failed: {len(summary.failed)}")
    for doi, reason in summary.failed.items():
        print(f"  {doi}: {reason}")
    print(f"Pending: {len(summary.pending)} {summary.pending}")
    return 1 if summary.conflict or summary.failed or summary.pending else 0


if __name__ == "__main__":
    raise SystemExit(main())
