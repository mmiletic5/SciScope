"""Command-line interfaces for JATS source parsing."""

import argparse
import io
import json
import os
import sys
import tempfile
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from sciscope.jats import source
from sciscope.jats.locator import (
    DigestMismatchError,
    InvalidTargetError,
    MalformedLocatorError,
    PathNotFoundError,
    SourceDocument,
    local_name,
    locator_digest,
)
from sciscope.jats.parser import (
    JatsParseError,
    ParseResult,
    SectionRecord,
    heading_text,
    paragraph_text,
    parse_paper,
)
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


def _load_paper(
    entry: ManifestEntry, titles: dict[str, str], repo_root: Path
) -> tuple[SourceDocument, ParseResult]:
    """Load and parse one manifest paper without merging its error kinds."""
    document = source.load_source(
        entry, repo_root, max_bytes=source.MAX_XML_BYTES
    )
    title = titles.get(entry.doi)
    if title is None:
        raise SourceError("missing-metadata")
    return document, parse_paper(document, entry.doi, title)


def _read_inputs(
    args: argparse.Namespace,
) -> tuple[list[ManifestEntry], dict[str, str]]:
    """Read the two shared inputs for a JATS command."""
    return (
        source.read_manifest(args.manifest),
        source.read_metadata_titles(args.metadata),
    )


def _error(code: str, status: int = 2) -> int:
    """Write a concise command error to stderr and return its status."""
    print(f"error: {code}", file=sys.stderr)
    return status


def _paper_error(error: SourceError | JatsParseError) -> str:
    """Preserve the distinct source and parse diagnostics."""
    if isinstance(error, SourceError):
        return error.code
    return f"parse-error: {error}"


def _parse(args: argparse.Namespace) -> int:
    """Parse manifest papers and write deterministic outputs."""
    try:
        entries, titles = _read_inputs(args)
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
                _, result = _load_paper(entry, titles, args.repo_root)
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


def _show(args: argparse.Namespace) -> int:
    """Display a paper outline or one section's paragraph subtree."""
    try:
        entries, titles = _read_inputs(args)
    except InputFileError as error:
        return _error(f"input: {error}")
    doi = args.doi.strip()
    entry = next((item for item in entries if item.doi == doi), None)
    if entry is None:
        return _error("unknown-doi")
    try:
        _, result = _load_paper(entry, titles, args.repo_root)
    except (SourceError, JatsParseError) as error:
        return _error(_paper_error(error))

    selected_id = f"{doi}#abstract" if args.abstract else args.section
    selected = next(
        (item for item in result.sections if item.section_id == selected_id),
        None,
    )
    if selected_id is not None and selected is None:
        return _error("unknown-section")

    print(f"doi: {result.doi}")
    print(f"title: {result.title}")
    print(f"xml_sha256: {result.xml_sha256}")
    print()
    if selected is None:
        for section in result.sections:
            indent = "  " * (section.depth - 1)
            print(
                f"{section.section_id} | {section.normalized_type} | "
                f"{section.paragraph_count} | {indent}"
                f"{_display_heading(section)}"
            )
        return 0

    print(
        f"section: {selected.section_id} | {selected.normalized_type} | "
        f"{_display_heading(selected)}"
    )
    print()
    sections = {item.section_id: item for item in result.sections}
    for paragraph in result.paragraphs:
        if not _is_descendant(paragraph.section_id, selected_id, sections):
            continue
        print(
            f"[{paragraph.section_id} #{paragraph.paragraph_index}] "
            f"{paragraph.source_locator}"
        )
        print(paragraph.text)
        if paragraph.omitted:
            print(f"[omitted: {', '.join(paragraph.omitted)}]")
        print()
    return 0


def _display_heading(section: SectionRecord) -> str:
    """Collapse whitespace in a heading for console display."""
    return " ".join(section.original_heading.split()) or "(untitled)"


def _is_descendant(
    section_id: str,
    ancestor_id: str,
    sections: dict[str, SectionRecord],
) -> bool:
    """Check section ancestry through recorded parent links."""
    current: str | None = section_id
    while current is not None:
        if current == ancestor_id:
            return True
        section = sections.get(current)
        current = section.parent_section_id if section is not None else None
    return False


def _candidate_paragraphs(element: ET.Element) -> Iterator[ET.Element]:
    """Yield direct and nested section paragraphs in document order."""
    if local_name(element) == "p":
        yield element
        return
    for child in element:
        kind = local_name(child)
        if kind == "p":
            yield child
        elif kind == "sec":
            yield from _candidate_paragraphs(child)


def _locator_error_code(error: Exception) -> str:
    """Map a locator exception to its stable CLI code."""
    if isinstance(error, MalformedLocatorError):
        return "locator-malformed"
    if isinstance(error, DigestMismatchError):
        return "digest-mismatch"
    if isinstance(error, PathNotFoundError):
        return "path-not-found"
    if isinstance(error, InvalidTargetError):
        return "invalid-target"
    raise AssertionError("Unexpected locator error")


def _check_quote(args: argparse.Namespace) -> int:
    """Check a quote within one resolved paragraph at a time."""
    try:
        digest = locator_digest(args.locator)
    except MalformedLocatorError:
        return _error("locator-malformed")
    try:
        entries, titles = _read_inputs(args)
    except InputFileError as error:
        return _error(f"input: {error}")
    entry = next(
        (item for item in entries if item.xml_sha256.lower() == digest),
        None,
    )
    if entry is None:
        return _error("digest-mismatch")
    try:
        document, result = _load_paper(entry, titles, args.repo_root)
    except (SourceError, JatsParseError) as error:
        return _error(_paper_error(error))
    try:
        element = document.resolve(args.locator)
    except (
        MalformedLocatorError,
        DigestMismatchError,
        PathNotFoundError,
        InvalidTargetError,
    ) as error:
        return _error(_locator_error_code(error))
    quote = " ".join(args.quote.split())
    if not quote:
        return _error("quote-empty")

    matches = [
        paragraph
        for paragraph in _candidate_paragraphs(element)
        if quote in paragraph_text(paragraph)[0]
    ]
    if not matches:
        return _error("quote-absent", 1)
    first_locator = document.locator_for(matches[0])
    print(f"OK: quote found in {first_locator}")
    print(f"matches: {len(matches)}")
    emitted = next(
        (
            item
            for item in result.paragraphs
            if item.source_locator == first_locator
        ),
        None,
    )
    if emitted is not None:
        print(
            f"section: {emitted.section_id} "
            f"paragraph: {emitted.paragraph_index}"
        )
    return 0


def _verify_roundtrip(args: argparse.Namespace) -> int:
    """Verify every emitted locator and its stored source-derived content."""
    try:
        entries, titles = _read_inputs(args)
    except InputFileError as error:
        return _error(f"input: {error}")

    section_count = paragraph_count = mismatch_count = 0
    details: list[str] = []
    for entry in sorted(entries, key=lambda item: item.doi):
        try:
            document, result = _load_paper(entry, titles, args.repo_root)
        except (SourceError, JatsParseError) as error:
            print(f"{entry.doi}: {_paper_error(error)}")
            mismatch_count += 1
            continue
        section_count += len(result.sections)
        paragraph_count += len(result.paragraphs)
        paper_mismatches = _roundtrip_mismatches(document, result)
        mismatch_count += len(paper_mismatches)
        details.extend(paper_mismatches[: max(0, 10 - len(details))])
        status = (
            "OK"
            if not paper_mismatches
            else f"mismatches {len(paper_mismatches)}"
        )
        print(
            f"{entry.doi}: sections {len(result.sections)} "
            f"paragraphs {len(result.paragraphs)} {status}"
        )
    print(
        f"Checked: {section_count} sections, {paragraph_count} paragraphs "
        f"across {len(entries)} papers; mismatches: {mismatch_count}"
    )
    for detail in details:
        print(detail)
    return 1 if mismatch_count else 0


def _roundtrip_mismatches(
    document: SourceDocument, result: ParseResult
) -> list[str]:
    """Collect bounded diagnostic text for all inconsistent emitted units."""
    mismatches: list[str] = []
    paragraphs = {item.source_locator: item for item in result.paragraphs}
    for section in result.sections:
        try:
            element = document.resolve(section.source_locator)
        except (
            MalformedLocatorError,
            DigestMismatchError,
            PathNotFoundError,
            InvalidTargetError,
        ) as error:
            mismatches.append(
                f"{section.section_id}: {_locator_error_code(error)}"
            )
            continue
        if "#body-p-" in section.section_id:
            first = paragraphs.get(section.source_locator)
            if (
                local_name(element) != "p"
                or section.original_heading != ""
                or first is None
                or first.section_id != section.section_id
                or first.paragraph_index != 1
            ):
                mismatches.append(
                    f"{section.section_id}: implicit anchor mismatch"
                )
        elif (
            local_name(element) not in {"sec", "abstract"}
            or heading_text(element) != section.original_heading
        ):
            mismatches.append(f"{section.section_id}: heading mismatch")
    for paragraph in result.paragraphs:
        try:
            element = document.resolve(paragraph.source_locator)
        except (
            MalformedLocatorError,
            DigestMismatchError,
            PathNotFoundError,
            InvalidTargetError,
        ) as error:
            mismatches.append(
                f"{paragraph.source_locator}: {_locator_error_code(error)}"
            )
            continue
        if (
            local_name(element) != "p"
            or paragraph_text(element)[0] != paragraph.text
        ):
            mismatches.append(f"{paragraph.source_locator}: text mismatch")
    return mismatches


def _configure_console() -> None:
    """Use UTF-8 output when the stream permits reconfiguration."""
    for stream in (sys.stdout, sys.stderr):
        try:
            reconfigure = getattr(stream, "reconfigure", None)
            if reconfigure is not None:
                reconfigure(
                    encoding="utf-8", errors="backslashreplace", newline="\n"
                )
        except (AttributeError, ValueError, io.UnsupportedOperation):
            continue


def main(argv: list[str] | None = None) -> int:
    """Run a JATS subcommand and return its exit status."""
    _configure_console()
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
    show = commands.add_parser("show", help="Show a paper or section")
    show.add_argument("doi")
    selection = show.add_mutually_exclusive_group()
    selection.add_argument("--section")
    selection.add_argument("--abstract", action="store_true")
    check_quote = commands.add_parser("check-quote", help="Check source quote")
    check_quote.add_argument("--locator", required=True)
    check_quote.add_argument("--quote", required=True)
    verify = commands.add_parser("verify-roundtrip", help="Verify locators")
    for command in (show, check_quote, verify):
        command.add_argument(
            "--manifest", type=Path, default=Path("data/pilot/manifest.jsonl")
        )
        command.add_argument(
            "--metadata", type=Path, default=Path("data/pilot/metadata.jsonl")
        )
        command.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args(argv)
    if args.command == "parse":
        return _parse(args)
    if args.command == "show":
        return _show(args)
    if args.command == "check-quote":
        return _check_quote(args)
    if args.command == "verify-roundtrip":
        return _verify_roundtrip(args)
    raise AssertionError("Unexpected command")


if __name__ == "__main__":
    raise SystemExit(main())
