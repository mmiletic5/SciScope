"""Behavior tests for synthetic JATS paragraphs, sections, and abstracts."""

from collections import Counter
from xml.etree import ElementTree as ET

import pytest
from jats_fixtures import synthetic_xml

from sciscope.jats.locator import SourceDocument
from sciscope.jats.parser import (
    JatsParseError,
    MissingBodyError,
    ParseResult,
    TypeConflict,
    heading_text,
    paragraph_text,
    parse_paper,
)

DOI = "10.9999/synthetic"
TITLE = "Synthetic paper"


def _paragraph(markup: str) -> ET.Element:
    """Parse one labeled synthetic paragraph."""
    return ET.fromstring(synthetic_xml(markup))


def _parse(markup: str) -> tuple[SourceDocument, ParseResult]:
    """Parse one labeled synthetic article in memory."""
    document = SourceDocument.from_bytes(synthetic_xml(markup))
    return document, parse_paper(document, DOI, TITLE)


def test_mixed_inline_text_and_xref_marker_are_retained() -> None:
    """Included inline kinds concatenate recursively without added spaces."""
    paragraph = _paragraph(
        "<p>Syn<italic>the<bold>tic</bold></italic> "
        "<xref>R1</xref> <ext-link>link</ext-link> "
        "<named-content>name</named-content> "
        "<email>fake@example.org</email>.</p>"
    )

    assert paragraph_text(paragraph) == (
        "Synthetic R1 link name fake@example.org.",
        Counter(),
    )


def test_subscript_and_superscript_gain_no_spaces() -> None:
    """Sub and sup content stays adjacent to surrounding characters."""
    paragraph = _paragraph("<p>H<sub>2</sub>O and x<sup>2</sup>.</p>")

    assert paragraph_text(paragraph) == ("H2O and x2.", Counter())


def test_unicode_and_nbsp_collapse_without_normalization() -> None:
    """Whitespace collapses while case and non-ASCII characters remain."""
    paragraph = _paragraph("<p>  naïve\u00a0\u00a0µm\n MIXED  </p>")

    assert paragraph_text(paragraph) == ("naïve µm MIXED", Counter())


@pytest.mark.parametrize(
    "kind",
    [
        "inline-formula",
        "disp-formula",
        "list",
        "fig",
        "table-wrap",
        "supplementary-material",
        "boxed-text",
    ],
)
def test_known_omitted_kind_drops_subtree_and_keeps_tail(kind: str) -> None:
    """Each approved omission kind removes its contents and keeps its tail."""
    paragraph = _paragraph(
        f"<p>Synthetic <{kind}><p>Hidden.</p></{kind}> sentence.</p>"
    )

    assert paragraph_text(paragraph) == (
        "Synthetic sentence.",
        Counter({kind: 1}),
    )


def test_nested_omission_inside_included_inline_is_counted_once() -> None:
    """An inline descendant obeys the same outer omission rule."""
    paragraph = _paragraph(
        "<p>A<italic>B<inline-formula><fig>Hidden</fig></inline-formula>"
        "C</italic>D</p>"
    )

    assert paragraph_text(paragraph) == (
        "ABCD",
        Counter({"inline-formula": 1}),
    )


def test_repeated_outer_omissions_count_occurrences_not_descendants() -> None:
    """Repeated outer blocks count separately while nested blocks do not."""
    paragraph = _paragraph(
        "<p>A<fig><table-wrap>Hidden</table-wrap></fig>B"
        "<fig>Hidden</fig>C<list><fig>Hidden</fig></list>D</p>"
    )

    assert paragraph_text(paragraph) == (
        "ABCD",
        Counter({"fig": 2, "list": 1}),
    )


def test_unlisted_child_and_nested_p_are_omitted() -> None:
    """Every unlisted child, including a nested paragraph, is omitted."""
    paragraph = _paragraph("<p>A<unknown>Hidden</unknown>B<p>Hidden</p>C</p>")

    assert paragraph_text(paragraph) == (
        "ABC",
        Counter({"unknown": 1, "p": 1}),
    )


def test_empty_extracted_text_is_preserved() -> None:
    """A paragraph containing only omitted content has empty text."""
    paragraph = _paragraph("<p> <fig>Hidden</fig> </p>")

    assert paragraph_text(paragraph) == ("", Counter({"fig": 1}))


def test_paragraph_records_have_sorted_distinct_omitted_kinds() -> None:
    """Per-paragraph omitted kinds are sorted and distinct, with empty tuple."""
    _, result = _parse(
        "<article><body><sec><p>Synthetic <fig/>one<unknown/>two<fig/>"
        "three.</p><p>Synthetic sentence one.</p></sec></body></article>"
    )

    assert [paragraph.omitted for paragraph in result.paragraphs] == [
        ("fig", "unknown"),
        (),
    ]
    assert result.skipped_element_kinds == {"fig": 2, "unknown": 1}
    assert (
        f"unlisted-element: unknown in {result.paragraphs[0].source_locator}"
        in result.warnings
    )


def test_empty_paragraph_record_remains_locatable_and_warns() -> None:
    """Empty extracted text still has a source paragraph and warning."""
    document, result = _parse(
        "<article><body><sec><p><fig>Hidden.</fig></p></sec></body></article>"
    )

    assert len(result.paragraphs) == 1
    assert result.paragraphs[0].text == ""
    assert document.resolve(result.paragraphs[0].source_locator) is not None
    assert any(
        warning.startswith("empty-paragraph: ") for warning in result.warnings
    )


def test_non_article_root_is_rejected() -> None:
    """A parseable XML root other than article is not JATS input."""
    document = SourceDocument.from_bytes(
        synthetic_xml("<not-article><body/></not-article>")
    )

    with pytest.raises(JatsParseError):
        parse_paper(document, DOI, TITLE)


def test_missing_body_raises_specific_error() -> None:
    """A missing body fails the paper rather than producing empty output."""
    document = SourceDocument.from_bytes(synthetic_xml("<article/>"))

    with pytest.raises(MissingBodyError):
        parse_paper(document, DOI, TITLE)


def test_empty_body_has_no_units_and_warns() -> None:
    """A body with no sections or paragraphs has empty record tuples."""
    _, result = _parse("<article><body/></article>")

    assert result.sections == ()
    assert result.paragraphs == ()
    assert "empty-body" in result.warnings
    assert "missing-abstract" in result.warnings


def test_section_ids_parents_depths_and_preorder() -> None:
    """Nested section IDs follow same-name indices and preorder."""
    _, result = _parse(
        "<article><body><sec><title>First</title><p>One.</p>"
        "<sec><title>Nested</title><p>Two.</p></sec></sec>"
        "<sec><title>Second</title><sec><title>Deep</title>"
        "<sec><title>Deeper</title><p>Three.</p></sec></sec></sec>"
        "</body></article>"
    )

    assert [section.section_id for section in result.sections] == [
        f"{DOI}#sec-1",
        f"{DOI}#sec-1.1",
        f"{DOI}#sec-2",
        f"{DOI}#sec-2.1",
        f"{DOI}#sec-2.1.1",
    ]
    assert [section.parent_section_id for section in result.sections] == [
        None,
        f"{DOI}#sec-1",
        None,
        f"{DOI}#sec-2",
        f"{DOI}#sec-2.1",
    ]
    assert [section.depth for section in result.sections] == [1, 2, 1, 2, 3]
    assert [paragraph.section_id for paragraph in result.paragraphs] == [
        f"{DOI}#sec-1",
        f"{DOI}#sec-1.1",
        f"{DOI}#sec-2.1.1",
    ]


def test_direct_paragraph_indices_ignore_interleaved_child_sections() -> None:
    """Only direct paragraph children advance an owning section's index."""
    _, result = _parse(
        "<article><body><sec><p>One.</p><sec><p>Nested.</p></sec>"
        "<p>Two.</p></sec></body></article>"
    )

    assert [paragraph.paragraph_index for paragraph in result.paragraphs] == [
        1,
        1,
        2,
    ]
    assert [section.paragraph_count for section in result.sections] == [2, 1]


def test_heading_preserves_inline_text_and_whitespace_in_path() -> None:
    """Heading text is verbatim and path extends its parent's path."""
    _, result = _parse(
        "<article><body><sec><title> First <italic>naïve</italic>  </title>"
        "<sec><title>Child</title><p>Fake.</p></sec></sec></body></article>"
    )

    assert result.sections[0].original_heading == " First naïve  "
    assert result.sections[0].section_path == (" First naïve  ",)
    assert result.sections[1].section_path == (" First naïve  ", "Child")


def test_untitled_and_duplicate_headings_keep_positional_ids() -> None:
    """Missing or blank headings use the label and titles never define IDs."""
    _, result = _parse(
        "<article><body><sec><p>One.</p></sec>"
        "<sec><title>  </title><p>Two.</p></sec>"
        "<sec><title>Same</title><p>Three.</p></sec>"
        "<sec><title>Same</title><p>Four.</p></sec></body></article>"
    )

    assert [section.section_path for section in result.sections[:2]] == [
        ("(untitled)",),
        ("(untitled)",),
    ]
    assert [section.section_id for section in result.sections[2:]] == [
        f"{DOI}#sec-3",
        f"{DOI}#sec-4",
    ]


def test_empty_section_is_retained_and_warns() -> None:
    """A section with no direct paragraphs or child sections remains visible."""
    _, result = _parse(
        "<article><body><sec><title>Empty</title></sec></body></article>"
    )

    assert result.sections[0].paragraph_count == 0
    assert f"empty-section: {DOI}#sec-1" in result.warnings


def test_body_paragraph_runs_break_only_at_section_siblings() -> None:
    """A skipped body child does not split an implicit paragraph group."""
    document, result = _parse(
        "<article><body><p>One.</p><fig/><p>Two.</p>"
        "<sec><p>Inside.</p></sec><p>Three.</p><p>Four.</p>"
        "</body></article>"
    )

    assert [section.section_id for section in result.sections] == [
        f"{DOI}#body-p-1",
        f"{DOI}#sec-1",
        f"{DOI}#body-p-3",
    ]
    assert [section.paragraph_count for section in result.sections] == [2, 1, 2]
    assert [paragraph.paragraph_index for paragraph in result.paragraphs] == [
        1,
        2,
        1,
        1,
        2,
    ]
    assert result.sections[0].section_path == ("(untitled)",)
    assert document.resolve(
        result.sections[0].source_locator
    ) is document.root.find("./body/p")
    assert (
        document.resolve(result.sections[2].source_locator)
        is list(document.root.find("./body"))[4]
    )


def test_structural_skipped_kinds_count_once_and_warn_if_unlisted() -> None:
    """Skipped block children and paragraph omissions share one count map."""
    _, result = _parse(
        "<article><body><unknown><fig/></unknown><sec><fig><p>Hidden</p>"
        "</fig><p>A<fig/>B.</p></sec></body></article>"
    )

    assert result.skipped_element_kinds == {"unknown": 1, "fig": 2}
    assert any(
        warning.startswith("unlisted-element: unknown in ")
        for warning in result.warnings
    )
    assert not any("Hidden" in warning for warning in result.warnings)


def test_plain_abstract_precedes_body_and_counts_direct_paragraphs() -> None:
    """The first untyped abstract owns its direct paragraphs before body."""
    document, result = _parse(
        "<article><front><article-meta><abstract abstract-type='short'>"
        "<p>Ignored.</p></abstract><abstract><p>Abstract one.</p>"
        "<p>Abstract two.</p></abstract></article-meta></front>"
        "<body><sec><p>Body one.</p></sec></body></article>"
    )

    assert [section.section_id for section in result.sections] == [
        f"{DOI}#abstract",
        f"{DOI}#sec-1",
    ]
    assert [paragraph.section_id for paragraph in result.paragraphs] == [
        f"{DOI}#abstract",
        f"{DOI}#abstract",
        f"{DOI}#sec-1",
    ]
    assert result.abstract_paragraph_count == 2
    assert result.sections[0].normalized_type == "abstract"
    assert result.sections[0].paragraph_count == 2
    assert document.resolve(
        result.sections[0].source_locator
    ) is document.root.find("./front/article-meta/abstract[2]")


def test_structured_abstract_hierarchy_and_aggregate_count() -> None:
    """Nested abstract sections keep abstract type, parent IDs, and depth."""
    _, result = _parse(
        "<article><front><article-meta><abstract><p>Direct.</p>"
        "<sec><title>First</title><p>Child.</p><sec><title>Deep</title>"
        "<p>Deep.</p></sec></sec><sec><title>Second</title><p>Last.</p>"
        "</sec></abstract></article-meta></front><body/></article>"
    )

    assert [section.section_id for section in result.sections] == [
        f"{DOI}#abstract",
        f"{DOI}#abstract.1",
        f"{DOI}#abstract.1.1",
        f"{DOI}#abstract.2",
    ]
    assert [section.parent_section_id for section in result.sections] == [
        None,
        f"{DOI}#abstract",
        f"{DOI}#abstract.1",
        f"{DOI}#abstract",
    ]
    assert [section.depth for section in result.sections] == [1, 2, 3, 2]
    assert [section.normalized_type for section in result.sections] == [
        "abstract",
        "abstract",
        "abstract",
        "abstract",
    ]
    assert [section.paragraph_count for section in result.sections] == [
        1,
        1,
        1,
        1,
    ]
    assert result.abstract_paragraph_count == 4
    assert result.sections[2].section_path == ("(untitled)", "First", "Deep")


def test_structured_container_without_direct_p_is_not_empty_section() -> None:
    """Child sections satisfy the abstract container's structural presence."""
    _, result = _parse(
        "<article><front><article-meta><abstract><sec><p>Child.</p>"
        "</sec></abstract></article-meta></front><body/></article>"
    )

    assert result.sections[0].paragraph_count == 0
    assert result.abstract_paragraph_count == 1
    assert f"empty-section: {DOI}#abstract" not in result.warnings
    assert "empty-abstract" not in result.warnings


def test_empty_abstract_and_empty_child_section_warn() -> None:
    """An abstract with no paragraphs warns, including its empty child sec."""
    _, result = _parse(
        "<article><front><article-meta><abstract><sec><title>None</title>"
        "</sec></abstract></article-meta></front><body/></article>"
    )

    assert result.abstract_paragraph_count == 0
    assert "empty-abstract" in result.warnings
    assert f"empty-section: {DOI}#abstract.1" in result.warnings
    assert f"empty-section: {DOI}#abstract" not in result.warnings


def test_missing_primary_abstract_warns_without_records() -> None:
    """Typed abstracts alone do not supply a primary abstract."""
    _, result = _parse(
        "<article><front><article-meta><abstract abstract-type='short'>"
        "<p>Typed.</p></abstract></article-meta></front><body/>"
        "</article>"
    )

    assert result.sections == ()
    assert result.paragraphs == ()
    assert result.abstract_paragraph_count == 0
    assert "missing-abstract" in result.warnings


def test_abstract_structural_skips_are_reported() -> None:
    """Unknown direct abstract children are counted and warned once."""
    _, result = _parse(
        "<article><front><article-meta><abstract><unknown><fig/></unknown>"
        "<p>Visible.</p></abstract></article-meta></front><body/></article>"
    )

    assert result.skipped_element_kinds == {"unknown": 1}
    assert any(
        warning.startswith("unlisted-element: unknown in ")
        for warning in result.warnings
    )


def test_all_emitted_locators_round_trip_including_implicit_group() -> None:
    """Abstract, body, and implicit-group anchors resolve in one source tree."""
    document, result = _parse(
        "<article><front><article-meta><abstract><p>Abstract.</p>"
        "<sec><p>Nested.</p></sec></abstract></article-meta></front>"
        "<body><p>Loose.</p><sec><p>Body.</p></sec></body></article>"
    )

    for section in result.sections:
        assert document.resolve(section.source_locator) is not None
    for paragraph in result.paragraphs:
        assert document.resolve(paragraph.source_locator) is not None
    assert document.resolve(
        result.sections[2].source_locator
    ) is document.root.find("./body/p")


def test_body_sections_use_sec_type_and_numbered_heading_tables() -> None:
    """Real body sections use exact sec-type or normalized heading matches."""
    _, result = _parse(
        "<article><body><sec sec-type=' Intro '><title>Local opening</title>"
        "<p>One.</p></sec><sec><title>2.1 Materials and Methods</title>"
        "<p>Two.</p></sec><sec><title>3) Results</title><p>Three.</p>"
        "</sec></body></article>"
    )

    assert [section.normalized_type for section in result.sections] == [
        "introduction",
        "methods",
        "results",
    ]
    assert result.unclassified_headings == {}


def test_nearest_explicit_ancestor_governs_three_nested_levels() -> None:
    """An inherited middle section does not replace the explicit ancestor."""
    _, result = _parse(
        "<article><body><sec><title>Methods</title><sec><title>Local A</title>"
        "<sec><title>Local B</title><sec><title>Local C</title>"
        "<p>Detail.</p></sec></sec></sec></sec></body></article>"
    )

    assert [section.normalized_type for section in result.sections] == [
        "methods",
        "methods",
        "methods",
        "methods",
    ]
    assert result.unclassified_headings == {
        "Local A": 1,
        "Local B": 1,
        "Local C": 1,
    }


def test_explicit_other_resets_inheritance_for_descendants() -> None:
    """Supporting material and its unmatched child stay outside Methods."""
    _, result = _parse(
        "<article><body><sec><title>Methods</title>"
        "<sec sec-type='supplementary-material'><title>Supplement</title>"
        "<sec><title>Local detail</title><p>Detail.</p></sec></sec>"
        "<sec><title>Supporting Information</title><p>Extra.</p></sec>"
        "</sec></body></article>"
    )

    assert [section.normalized_type for section in result.sections] == [
        "methods",
        "other",
        "other",
        "other",
    ]
    assert result.unclassified_headings == {"Local detail": 1}


def test_type_conflict_keeps_raw_values_and_document_order() -> None:
    """Only differing dual matches emit conflicts with original values."""
    _, result = _parse(
        "<article><body><sec sec-type=' RESULTS '><title>  Methods  </title>"
        "<p>One.</p></sec><sec sec-type='methods'>"
        "<title>Materials and Methods</title><p>Two.</p></sec>"
        "<sec sec-type='discussion'><title>Conclusions</title>"
        "<p>Three.</p></sec></body></article>"
    )

    assert [section.normalized_type for section in result.sections] == [
        "methods",
        "methods",
        "conclusions",
    ]
    assert result.type_conflicts == (
        TypeConflict(f"{DOI}#sec-1", " RESULTS ", "  Methods  "),
        TypeConflict(f"{DOI}#sec-3", "discussion", "Conclusions"),
    )


def test_discussion_heading_overrides_plos_conclusions_sec_type() -> None:
    """SYNTHETIC PLOS pattern keeps discussion inheritance and conflict data."""
    _, result = _parse(
        "<article><body><sec sec-type='conclusions'><title>Discussion</title>"
        "<sec><title>Subsection</title><p>SYNTHETIC detail.</p></sec>"
        "</sec></body></article>"
    )

    assert [section.normalized_type for section in result.sections] == [
        "discussion",
        "discussion",
    ]
    assert result.type_conflicts == (
        TypeConflict(f"{DOI}#sec-1", "conclusions", "Discussion"),
    )
    assert result.unclassified_headings == {"Subsection": 1}


def test_unmatched_heading_with_sec_type_match_is_explicit() -> None:
    """SYNTHETIC sec-type fallback does not count an unmatched heading."""
    _, result = _parse(
        "<article><body><sec sec-type='conclusions'>"
        "<title>Conclusions and next steps</title>"
        "<p>SYNTHETIC body.</p></sec></body></article>"
    )
    assert result.sections[0].normalized_type == "conclusions"
    assert result.unclassified_headings == {}
    assert result.type_conflicts == ()


def test_heading_text_preserves_inline_text_and_whitespace() -> None:
    """SYNTHETIC title text is concatenated verbatim across inline markup."""
    section = ET.fromstring(
        synthetic_xml(
            "<sec><title>  SYNTHETIC <italic>mixed</italic>  title\n</title>"
            "<p>Body.</p></sec>"
        )
    )
    assert heading_text(section) == "  SYNTHETIC mixed  title\n"


def test_heading_text_without_direct_title_is_empty() -> None:
    """SYNTHETIC missing titles have an empty verbatim heading."""
    section = ET.fromstring(synthetic_xml("<sec><p>Body.</p></sec>"))
    assert heading_text(section) == ""


def test_unmatched_heading_counts_include_inherited_and_blank_titles() -> None:
    """Only real unmatched body sections appear in the paper report."""
    _, result = _parse(
        "<article><front><article-meta><abstract><sec><title>Unknown</title>"
        "<p>Abstract.</p></sec></abstract></article-meta></front>"
        "<body><p>Loose.</p><sec><title>Methods</title>"
        "<sec><title>  Local   detail  </title><p>One.</p></sec>"
        "<sec><title>Local detail</title><p>Two.</p></sec>"
        "<sec><title>  </title><p>Three.</p></sec>"
        "<sec sec-type='supplementary-material'><title>Extra</title>"
        "<p>Four.</p></sec></sec></body></article>"
    )

    assert result.unclassified_headings == {
        "Local detail": 2,
        "(untitled)": 1,
    }
    assert result.sections[0].normalized_type == "abstract"
    assert result.sections[1].normalized_type == "abstract"
    assert result.sections[2].normalized_type == "other"


def test_histogram_counts_abstract_body_and_implicit_sections_sorted() -> None:
    """Each emitted section contributes once to the sorted histogram."""
    _, result = _parse(
        "<article><front><article-meta><abstract><p>Abstract.</p>"
        "<sec><title>Results</title><p>Still abstract.</p></sec>"
        "</abstract></article-meta></front><body><p>Loose.</p>"
        "<sec><title>Results</title><p>Result.</p></sec>"
        "<sec><title>Methods</title><p>Method.</p></sec>"
        "</body></article>"
    )

    assert result.normalized_type_histogram == {
        "abstract": 2,
        "methods": 1,
        "other": 1,
        "results": 1,
    }
    assert list(result.normalized_type_histogram) == sorted(
        result.normalized_type_histogram
    )
    assert result.unclassified_headings == {}


def test_back_matter_lists_only_direct_approved_containers() -> None:
    """Repeated known back children are listed once and never emitted."""
    _, result = _parse(
        "<article><body><sec><p>Body.</p></sec></body>"
        "<back><ref-list><p>Hidden reference.</p></ref-list>"
        "<ack><p>Hidden acknowledgement.</p></ack>"
        "<fn-group><p>Hidden note.</p></fn-group>"
        "<ack><p>Hidden again.</p></ack><unknown><p>Hidden.</p></unknown>"
        "</back></article>"
    )

    assert result.back_matter_containers == ("ack", "fn-group", "ref-list")
    assert len(result.sections) == 1
    assert [paragraph.text for paragraph in result.paragraphs] == ["Body."]


def test_absent_back_matter_has_empty_container_tuple() -> None:
    """A paper without back matter reports no back containers."""
    _, result = _parse(
        "<article><body><sec><p>Body.</p></sec></body></article>"
    )

    assert result.back_matter_containers == ()
