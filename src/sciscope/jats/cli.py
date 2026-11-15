"""Command-line interfaces for JATS source parsing."""

import argparse
import json
import os
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from sciscope.jats import source
from sciscope.jats.parser import JatsParseError, ParseResult, parse_paper
from sciscope.jats.source import InputFileError, ManifestEntry, SourceError


def _section_rows(result: ParseResult) -> list[dict[str, Any]]:
    """Serialize sections with the approved key order."""
    return [
        {
            "doi": result.doi,
            "title": result.title,
            "xml_sha256": result.xml_sha256,
            "section_id": section.section_id,
            "parent_section_id": section.parent_section_id,
            "section_path": list(section.section_path),
            "original_heading": section.original_heading,
            "normalized_type": section.normalized_type,
            "source_locator": section.source_locator,
            "depth": section.depth,
            "paragraph_count": section.paragraph_count,
        }
        for section in result.sections
    ]


def _paragraph_rows(result: ParseResult) -> list[dict[str, Any]]:
    """Serialize paragraphs with the approved key order."""
    return [
        {
            "doi": result.doi,
            "section_id": paragraph.section_id,
            "paragraph_index": paragraph.paragraph_index,
            "text": paragraph.text,
            "omitted": list(paragraph.omitted),
            "source_locator": paragraph.source_locator,
        }
        for paragraph in result.paragraphs
    ]


def _paper_report(
    entry: ManifestEntry,
    result: ParseResult | None,
    errors: list[str],
) -> dict[str, Any]:
    """Serialize one successful or failed paper report."""
    return {
        "doi": entry.doi,
        "xml_sha256": entry.xml_sha256,
        "section_count": len(result.sections) if result else 0,
        "paragraph_count": len(result.paragraphs) if result else 0,
        "abstract_paragraph_count": result.abstract_paragraph_count
        if result
        else 0,
        "normalized_type_histogram": result.normalized_type_histogram
        if result
        else {},
        "unclassified_headings": result.unclassified_headings if result else {},
        "type_conflicts": [
            {
                "section_id": conflict.section_id,
                "sec_type": conflict.sec_type,
                "heading": conflict.heading,
            }
            for conflict in result.type_conflicts
        ]
        if result
        else [],
        "skipped_element_kinds": result.skipped_element_kinds if result else {},
        "back_matter_containers": list(result.back_matter_containers)
        if result
        else [],
        "warnings": list(result.warnings) if result else [],
        "errors": errors,
    }


def _json_bytes(value: Any, *, indent: int | None = None) -> bytes:
    """Encode stable JSON as UTF-8 with a final LF."""
    return (
        json.dumps(value, ensure_ascii=False, indent=indent) + "\n"
    ).encode()


def _jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    """Encode JSONL records as UTF-8 with a final LF."""
    return (
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n"
    ).encode()


def _write_outputs(outputs: dict[Path, bytes]) -> None:
    """Stage all outputs beside their targets and replace after staging."""
    staged: dict[Path, Path] = {}
    previous: dict[Path, bytes | None] = {}
    replaced: list[Path] = []
    try:
        for target, content in outputs.items():
            target.parent.mkdir(parents=True, exist_ok=True)
            previous[target] = target.read_bytes() if target.exists() else None
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=target.parent, suffix=".tmp", delete=False
            ) as temporary_file:
                staged[target] = Path(temporary_file.name)
                temporary_file.write(content)
        for target, temporary_path in staged.items():
            os.replace(temporary_path, target)
            replaced.append(target)
    except OSError:
        for target in replaced:
            old_content = previous[target]
            if old_content is None:
                target.unlink()
            else:
                target.write_bytes(old_content)
        raise
    finally:
        for temporary_path in staged.values():
            temporary_path.unlink(missing_ok=True)


def _parse(args: argparse.Namespace) -> int:
    """Parse manifest papers and write deterministic outputs."""
    try:
        entries = source.read_manifest(args.manifest)
        titles = source.read_metadata_titles(args.metadata)
    except InputFileError as error:
        print(f"Input error: {error}")
        return 2

    duplicates = {
        doi
        for doi, count in Counter(entry.doi for entry in entries).items()
        if count > 1
    }
    sections: list[dict[str, Any]] = []
    paragraphs: list[dict[str, Any]] = []
    papers: list[dict[str, Any]] = []
    succeeded = failed = 0
    for entry in sorted(entries, key=lambda item: item.doi):
        result: ParseResult | None = None
        errors: list[str] = []
        if entry.doi in duplicates:
            errors.append("duplicate-manifest-doi")
        else:
            try:
                document = source.load_source(
                    entry, args.repo_root, max_bytes=source.MAX_XML_BYTES
                )
                title = titles.get(entry.doi)
                if title is None:
                    raise SourceError("missing-metadata")
                result = parse_paper(document, entry.doi, title)
            except SourceError as error:
                errors.append(error.code)
            except JatsParseError as error:
                errors.append(f"parse-error: {error}")

        if result is not None:
            succeeded += 1
            sections.extend(_section_rows(result))
            paragraphs.extend(_paragraph_rows(result))
        else:
            failed += 1
            for code in errors:
                print(f"{entry.doi}: {code}")
        papers.append(_paper_report(entry, result, errors))

    report = {
        "papers": papers,
        "summary": {"succeeded": succeeded, "failed": failed},
    }
    _write_outputs(
        {
            args.sections: _jsonl_bytes(sections),
            args.paragraphs: _jsonl_bytes(paragraphs),
            args.report: _json_bytes(report, indent=2),
        }
    )
    print(f"Succeeded: {succeeded}; failed: {failed}")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    """Run a JATS subcommand and return its exit status."""
    parser = argparse.ArgumentParser(description="Parse JATS pilot sources")
    commands = parser.add_subparsers(dest="command", required=True)
    parse = commands.add_parser("parse", help="Parse manifest papers")
    parse.add_argument(
        "--manifest", type=Path, default=Path("data/pilot/manifest.jsonl")
    )
    parse.add_argument(
        "--metadata", type=Path, default=Path("data/pilot/metadata.jsonl")
    )
    parse.add_argument("--repo-root", type=Path, default=Path("."))
    parse.add_argument(
        "--sections",
        type=Path,
        default=Path("data/processed/pilot/sections.jsonl"),
    )
    parse.add_argument(
        "--paragraphs",
        type=Path,
        default=Path("data/processed/pilot/paragraphs.jsonl"),
    )
    parse.add_argument(
        "--report", type=Path, default=Path("data/pilot/parse_report.json")
    )
    args = parser.parse_args(argv)
    if args.command == "parse":
        return _parse(args)
    raise AssertionError("Unexpected command")


if __name__ == "__main__":
    raise SystemExit(main())
