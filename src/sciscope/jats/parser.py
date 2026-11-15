"""JATS paragraph and section parsing interfaces."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field, replace
from xml.etree import ElementTree as ET

from sciscope.jats.classify import classify_section
from sciscope.jats.locator import SourceDocument, local_name

UNTITLED_LABEL = "(untitled)"
INLINE_KINDS = frozenset(
    {
        "italic",
        "bold",
        "xref",
        "ext-link",
        "named-content",
        "email",
        "sub",
        "sup",
    }
)
KNOWN_OMITTED_KINDS = frozenset(
    {
        "inline-formula",
        "disp-formula",
        "list",
        "fig",
        "table-wrap",
        "supplementary-material",
        "boxed-text",
    }
)
BACK_MATTER_KINDS = frozenset(
    {"ack", "ref-list", "app", "notes", "fn-group", "glossary"}
)


def paragraph_text(element: ET.Element) -> tuple[str, Counter[str]]:
    """Extract included paragraph text and outer omitted-kind counts."""
    parts: list[str] = []
    omitted: Counter[str] = Counter()

    def visit(node: ET.Element) -> None:
        if node.text:
            parts.append(node.text)
        for child in node:
            kind = local_name(child)
            if kind in INLINE_KINDS:
                visit(child)
            else:
                omitted[kind] += 1
            if child.tail:
                parts.append(child.tail)

    visit(element)
    return " ".join("".join(parts).split()), omitted


@dataclass(frozen=True, slots=True)
class ParagraphRecord:
    """A direct paragraph owned by one section."""

    section_id: str
    paragraph_index: int
    text: str
    omitted: tuple[str, ...]
    source_locator: str


@dataclass(frozen=True, slots=True)
class SectionRecord:
    """A source section or implicit direct-body paragraph group."""

    section_id: str
    parent_section_id: str | None
    section_path: tuple[str, ...]
    original_heading: str
    normalized_type: str
    source_locator: str
    depth: int
    paragraph_count: int


@dataclass(frozen=True, slots=True)
class TypeConflict:
    """A body section whose explicit taxonomy sources disagree."""

    section_id: str
    sec_type: str
    heading: str


@dataclass(frozen=True, slots=True)
class ParseResult:
    """Parsed units and per-paper extraction diagnostics."""

    doi: str
    title: str
    xml_sha256: str
    sections: tuple[SectionRecord, ...]
    paragraphs: tuple[ParagraphRecord, ...]
    abstract_paragraph_count: int
    skipped_element_kinds: dict[str, int]
    warnings: tuple[str, ...]
    normalized_type_histogram: dict[str, int] = field(default_factory=dict)
    unclassified_headings: dict[str, int] = field(default_factory=dict)
    type_conflicts: tuple[TypeConflict, ...] = ()
    back_matter_containers: tuple[str, ...] = ()


class JatsParseError(ValueError):
    """The XML cannot be parsed into a supported JATS paper."""


class MissingBodyError(JatsParseError):
    """The article has no body element."""


def parse_paper(document: SourceDocument, doi: str, title: str) -> ParseResult:
    """Parse abstract, body sections, paragraphs, and diagnostics."""
    if local_name(document.root) != "article":
        raise JatsParseError("Source root must be article")

    def direct_child(parent: ET.Element | None, name: str) -> ET.Element | None:
        if parent is None:
            return None
        return next(
            (child for child in parent if local_name(child) == name), None
        )

    body = direct_child(document.root, "body")
    if body is None:
        raise MissingBodyError("Article has no body")

    sections: list[SectionRecord] = []
    paragraphs: list[ParagraphRecord] = []
    skipped: Counter[str] = Counter()
    warnings: list[str] = []
    unclassified_headings: Counter[str] = Counter()
    type_conflicts: list[TypeConflict] = []
    warned_skips: set[tuple[str, str]] = set()
    abstract_paragraph_count = 0

    def report_skipped(kind: str, locator: str) -> None:
        skipped[kind] += 1
        key = (locator, kind)
        if kind not in KNOWN_OMITTED_KINDS and key not in warned_skips:
            warnings.append(f"unlisted-element: {kind} in {locator}")
            warned_skips.add(key)

    def emit_paragraph(
        element: ET.Element,
        section_id: str,
        index: int,
        is_abstract: bool,
    ) -> None:
        nonlocal abstract_paragraph_count
        locator = document.locator_for(element)
        text, omitted = paragraph_text(element)
        paragraphs.append(
            ParagraphRecord(
                section_id=section_id,
                paragraph_index=index,
                text=text,
                omitted=tuple(sorted(omitted)),
                source_locator=locator,
            )
        )
        skipped.update(omitted)
        if is_abstract:
            abstract_paragraph_count += 1
        if not text:
            warnings.append(f"empty-paragraph: {locator}")
        for kind in omitted:
            if kind not in KNOWN_OMITTED_KINDS:
                warnings.append(f"unlisted-element: {kind} in {locator}")

    def visit_section(
        element: ET.Element,
        section_id: str,
        parent_id: str | None,
        parent_path: tuple[str, ...],
        depth: int,
        is_abstract: bool,
        nearest_explicit_ancestor_type: str | None = None,
        is_container: bool = False,
    ) -> None:
        heading_element = (
            None if is_container else direct_child(element, "title")
        )
        heading = (
            ""
            if heading_element is None
            else "".join(heading_element.itertext())
        )
        path = parent_path + (heading if heading.strip() else UNTITLED_LABEL,)
        own_count = sum(local_name(child) == "p" for child in element)
        locator = document.locator_for(element)
        normalized_type = "abstract"
        if not is_abstract:
            raw_sec_type = element.get("sec-type", "")
            classification = classify_section(
                raw_sec_type, heading, nearest_explicit_ancestor_type
            )
            normalized_type = classification.normalized_type
            if classification.explicit:
                nearest_explicit_ancestor_type = normalized_type
            else:
                heading_key = " ".join(heading.split()) or UNTITLED_LABEL
                unclassified_headings[heading_key] += 1
            if classification.conflict:
                type_conflicts.append(
                    TypeConflict(section_id, raw_sec_type, heading)
                )
        sections.append(
            SectionRecord(
                section_id=section_id,
                parent_section_id=parent_id,
                section_path=path,
                original_heading=heading,
                normalized_type=normalized_type,
                source_locator=locator,
                depth=depth,
                paragraph_count=own_count,
            )
        )
        has_child_section = any(local_name(child) == "sec" for child in element)
        if not is_container and own_count == 0 and not has_child_section:
            warnings.append(f"empty-section: {section_id}")

        paragraph_index = 0
        child_section_index = 0
        for child in element:
            kind = local_name(child)
            if kind == "p":
                paragraph_index += 1
                emit_paragraph(child, section_id, paragraph_index, is_abstract)
            elif kind == "sec":
                child_section_index += 1
                child_id = f"{section_id}.{child_section_index}"
                visit_section(
                    child,
                    child_id,
                    section_id,
                    path,
                    depth + 1,
                    is_abstract,
                    nearest_explicit_ancestor_type,
                )
            elif kind != "title":
                report_skipped(kind, locator)

    front = direct_child(document.root, "front")
    article_meta = direct_child(front, "article-meta")
    primary_abstract = None
    if article_meta is not None:
        primary_abstract = next(
            (
                child
                for child in article_meta
                if local_name(child) == "abstract"
                and "abstract-type" not in child.attrib
            ),
            None,
        )
    if primary_abstract is None:
        warnings.append("missing-abstract")
    else:
        abstract_warning_index = len(warnings)
        visit_section(
            primary_abstract,
            f"{doi}#abstract",
            None,
            (),
            1,
            True,
            is_container=True,
        )
        if abstract_paragraph_count == 0:
            warnings.insert(abstract_warning_index, "empty-abstract")

    body_section_index = 0
    body_paragraph_index = 0
    group_index: int | None = None
    body_locator = document.locator_for(body)
    body_warning_index = len(warnings)
    for child in body:
        kind = local_name(child)
        if kind == "sec":
            group_index = None
            body_section_index += 1
            visit_section(
                child,
                f"{doi}#sec-{body_section_index}",
                None,
                (),
                1,
                False,
            )
        elif kind == "p":
            body_paragraph_index += 1
            if group_index is None:
                group_index = len(sections)
                sections.append(
                    SectionRecord(
                        section_id=f"{doi}#body-p-{body_paragraph_index}",
                        parent_section_id=None,
                        section_path=(UNTITLED_LABEL,),
                        original_heading="",
                        normalized_type="other",
                        source_locator=document.locator_for(child),
                        depth=1,
                        paragraph_count=0,
                    )
                )
            group = sections[group_index]
            sections[group_index] = replace(
                group, paragraph_count=group.paragraph_count + 1
            )
            emit_paragraph(
                child,
                group.section_id,
                sections[group_index].paragraph_count,
                False,
            )
        elif kind != "title":
            report_skipped(kind, body_locator)

    if body_section_index == 0 and body_paragraph_index == 0:
        warnings.insert(body_warning_index, "empty-body")

    back = direct_child(document.root, "back")
    back_matter_containers = (
        tuple(sorted({local_name(child) for child in back} & BACK_MATTER_KINDS))
        if back is not None
        else ()
    )
    type_histogram = Counter(section.normalized_type for section in sections)

    return ParseResult(
        doi=doi,
        title=title,
        xml_sha256=document.sha256,
        sections=tuple(sections),
        paragraphs=tuple(paragraphs),
        abstract_paragraph_count=abstract_paragraph_count,
        skipped_element_kinds=dict(sorted(skipped.items())),
        warnings=tuple(warnings),
        normalized_type_histogram=dict(sorted(type_histogram.items())),
        unclassified_headings=dict(sorted(unclassified_headings.items())),
        type_conflicts=tuple(type_conflicts),
        back_matter_containers=back_matter_containers,
    )
