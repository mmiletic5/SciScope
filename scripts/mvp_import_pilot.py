"""Import the validated pilot snapshot into the local demo database.

Reads DATABASE_URL from the environment, refuses any database other than
``sciscope_test_005`` and never prints the URL or any credential.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from sciscope.database.config import DatabaseSettings
from sciscope.ingestion.contract import ImportMode, ImportRequest
from sciscope.ingestion.errors import ImportErrorCode, SnapshotImportError
from sciscope.ingestion.service import SnapshotImporter

REQUIRED_DATABASE = "sciscope_test_005"


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--package-dir", type=Path, default=Path("data/delivery/pilot")
    )
    parser.add_argument(
        "--parse-report",
        type=Path,
        default=Path("data/pilot/parse_report.json"),
    )
    parser.add_argument(
        "--chunk-report",
        type=Path,
        default=Path("data/pilot/chunk_report.json"),
    )
    parser.add_argument(
        "--embedding-report",
        type=Path,
        default=Path("data/pilot/embedding_report.json"),
    )
    return parser.parse_args(argv)


def build_request(args: argparse.Namespace) -> ImportRequest:
    """Build an INITIALIZE request from parsed arguments."""
    return ImportRequest(
        package_dir=args.package_dir,
        parse_report=args.parse_report,
        chunk_report=args.chunk_report,
        embedding_report=args.embedding_report,
        mode=ImportMode.INITIALIZE,
    )


def database_url_from(environ: Mapping[str, str]) -> str:
    """Return the validated URL, refusing any non-demo database."""
    url = DatabaseSettings.from_environment(environ).url
    if make_url(url).database != REQUIRED_DATABASE:
        raise ValueError(
            f"refusing to run: database must be {REQUIRED_DATABASE}"
        )
    return url


def main(argv: Sequence[str] | None = None) -> int:
    """Run the import and print the result counts as JSON."""
    args = parse_args(argv)
    try:
        url = database_url_from(os.environ)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    engine = create_engine(url, pool_pre_ping=True)
    try:
        result = SnapshotImporter(engine).import_snapshot(build_request(args))
    except SnapshotImportError as error:
        if error.code is ImportErrorCode.REPLACEMENT_REQUIRED:
            print(
                "already initialized with a different snapshot; nothing "
                "was changed. Reset with `docker compose down -v` to start "
                "over.",
                file=sys.stderr,
            )
        else:
            print(f"error: import failed: {error.code.value}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()
    print(json.dumps(asdict(result), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
