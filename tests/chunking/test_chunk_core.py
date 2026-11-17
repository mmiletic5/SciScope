"""RED behavior tests for T002 section chunking."""

import random

import pytest

from sciscope.chunking.config import (
    ChunkConfig,
    ChunkingError,
    HeadingBudgetError,
    build_embedding_text,
)
from sciscope.chunking.core import (
    Chunk,
    SourceParagraph,
    SourceSection,
    chunk_section,
    chunk_sections,
)
from sciscope.chunking.counter import Utf8BytesDiv3Counter
from sciscope.chunking.split import largest_end_within_limit, sentence_spans

DOI = "10.0000/invented"
WORDS = ("velora", "cendrix", "torvex", "lumara", "nestrin", "kulvo")
COUNTER = Utf8BytesDiv3Counter()


def words(n: int) -> str:
    """Return a repeatable string with exactly 2n B3 tokens."""
    # n copies of six-byte "amber" use 6n - 1 bytes including spaces.
    # ceil((6n - 1) / 3) = 2n.
    return " ".join(["amber"] * n)


def synthetic_text(seed: int, count: int) -> str:
    """Generate fixed-seed prose from invented words only."""
    generator = random.Random(seed)
    return " ".join(generator.choice(WORDS) for _ in range(count))


def section(
    section_id: str = "s1",
    path: tuple[str, ...] = ("Methods",),
    normalized_type: str = "methods",
) -> SourceSection:
    """Create a synthetic DOI-bearing section."""
    return SourceSection(DOI, section_id, path, normalized_type)


def paragraph(
    text: str, index: int = 1, section_id: str = "s1"
) -> SourceParagraph:
    """Create a synthetic DOI-bearing paragraph."""
    return SourceParagraph(
        DOI, section_id, index, text, f"loc-{section_id}-{index}"
    )


def small_config(**changes: int) -> ChunkConfig:
    """Create a validated small-token configuration for boundary tests."""
    values = {
        "operational_cap_tokens": 96,
        "content_target_min_tokens": 5,
        "content_target_max_tokens": 20,
        "soft_min_tokens": 0,
        "prefix_reserve_tokens": 0,
        "min_content_budget_tokens": 1,
    }
    values.update(changes)
    return ChunkConfig(**values)


def assert_span_coverage(
    chunks: list[Chunk], paragraphs: list[SourceParagraph]
) -> None:
    """Check exact non-whitespace coverage and source order."""
    for source in paragraphs:
        spans = [
            span
            for chunk in chunks
            for span in chunk.spans
            if span.source_locator == source.source_locator
        ]
        assert spans == sorted(spans, key=lambda span: span.start)
        covered: set[int] = set()
        for span in spans:
            assert 0 <= span.start < span.end <= len(source.text)
            assert (
                source.text[span.start : span.end].strip()
                == (source.text[span.start : span.end])
            )
            positions = set(range(span.start, span.end))
            assert not covered.intersection(positions)
            covered.update(positions)
        if spans:
            assert spans[0].start == len(source.text) - len(
                source.text.lstrip()
            )
            assert spans[-1].end == len(source.text.rstrip())
        expected = {
            i for i, char in enumerate(source.text) if not char.isspace()
        }
        assert expected.issubset(covered)
        assert all(source.text[i].isspace() for i in covered - expected)
        for left, right in zip(spans, spans[1:], strict=False):
            assert source.text[left.end : right.start].strip() == ""


@pytest.mark.parametrize(
    ("path", "kind"),
    [
        pytest.param(("(untitled)",), "abstract", id="T002-plain-abstract"),
        pytest.param(
            ("(untitled)", "Background"),
            "abstract",
            id="T002-structured-abstract",
        ),
        pytest.param(("(untitled)",), "other", id="T002-implicit-group"),
        pytest.param(("(untitled)",), "methods", id="T002-untitled-section"),
        pytest.param(("Oddity",), "other", id="T002-other-section"),
    ],
)
def test_section_types_include_own_text(
    path: tuple[str, ...], kind: str
) -> None:
    """T002: Option A includes every section type with text."""
    identifier = (
        f"{DOI}#body-p-3"
        if kind == "other" and path == ("(untitled)",)
        else "s1"
    )
    source = section(identifier, path, kind)
    chunks = chunk_section(
        source,
        [paragraph("amber cobalt", section_id=identifier)],
        small_config(),
        COUNTER,
    )
    assert len(chunks) == 1
    assert chunks[0].heading_path == tuple(
        part for part in path if part.strip() and part != "(untitled)"
    )
    assert chunks[0].normalized_type == kind


def test_parent_child_isolation_and_section_order() -> None:
    """T002: nested sections remain independent in source order."""
    parent = section("parent", ("Methods",))
    child = section("child", ("Methods", "Samples"))
    sources = [paragraph("amber", 1, "parent"), paragraph("cobalt", 1, "child")]
    chunks = chunk_sections([parent, child], sources, small_config(), COUNTER)
    assert [(item.section_id, item.ordinal) for item in chunks] == [
        ("parent", 1),
        ("child", 1),
    ]
    assert [item.text for item in chunks] == ["amber", "cobalt"]


def test_blank_and_empty_paragraphs_are_skipped() -> None:
    """T002: blank records produce no span or embedding input."""
    sources = [paragraph(""), paragraph(" \t ", 2), paragraph("amber", 3)]
    chunks = chunk_section(section(), sources, small_config(), COUNTER)
    assert [item.text for item in chunks] == ["amber"]
    assert [span.paragraph_index for span in chunks[0].spans] == [3]


def test_section_without_paragraphs_has_no_chunks() -> None:
    """T002: a section with no own text emits nothing."""
    assert chunk_section(section(), [], small_config(), COUNTER) == []


def test_small_paragraphs_pack_with_separator() -> None:
    """T002: fitting paragraphs join with two line feeds."""
    chunks = chunk_section(
        section(),
        [paragraph("amber"), paragraph("cobalt", 2)],
        small_config(),
        COUNTER,
    )
    assert len(chunks) == 1
    assert chunks[0].text == "amber\n\ncobalt"


def test_fitting_paragraph_is_never_split_to_fill() -> None:
    """T002: a whole fitting paragraph starts the next chunk."""
    # 14 + 12 tokens, with a separator, exceeds the target of 20.
    sources = [paragraph(words(7)), paragraph(words(6), 2)]
    chunks = chunk_section(section(), sources, small_config(), COUNTER)
    assert len(chunks) == 2
    assert chunks[0].text == sources[0].text
    assert len(chunks[1].spans) == 1
    span = chunks[1].spans[0]
    assert span.paragraph_index == 2
    assert (span.start, span.end) == (0, len(sources[1].text))


def test_heading_overhead_lowers_effective_max() -> None:
    """T002: a long heading leaves less content capacity."""
    source = paragraph(synthetic_text(3, 10))
    plain = chunk_section(
        section(path=("(untitled)",)),
        [source],
        small_config(operational_cap_tokens=30),
        COUNTER,
    )
    headed = chunk_section(
        section(path=("Heading " * 8,)),
        [source],
        small_config(operational_cap_tokens=30),
        COUNTER,
    )
    assert len(headed) > len(plain)


def test_heading_budget_error() -> None:
    """T002: a heading that consumes capacity is rejected."""
    with pytest.raises(HeadingBudgetError):
        chunk_section(
            section(path=("H" * 300,)),
            [paragraph("amber")],
            small_config(),
            COUNTER,
        )


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("et al. Amber follows.", id="et-al"),
        pytest.param("Fig. Amber follows.", id="fig"),
        pytest.param("Figs. Amber follows.", id="figs"),
        pytest.param("Tab. Amber follows.", id="tab"),
        pytest.param("Eq. Amber follows.", id="eq"),
        pytest.param("Ref. Amber follows.", id="ref"),
        pytest.param("e.g. Amber follows.", id="eg"),
        pytest.param("i.e. Amber follows.", id="ie"),
        pytest.param("vs. Amber follows.", id="vs"),
        pytest.param("cf. Amber follows.", id="cf"),
        pytest.param("ca. Amber follows.", id="ca"),
        pytest.param("approx. Amber follows.", id="approx"),
        pytest.param("no. Amber follows.", id="no"),
        pytest.param("sp. Amber follows.", id="sp"),
        pytest.param("spp. Amber follows.", id="spp"),
        pytest.param("var. Amber follows.", id="var"),
        pytest.param("subsp. Amber follows.", id="subsp"),
        pytest.param("Dr. Amber follows.", id="dr"),
        pytest.param("A. mellifera follows.", id="genus"),
        pytest.param("V. destructor follows.", id="species"),
        pytest.param("J. K. Smith follows.", id="initials"),
        pytest.param("Value 0.05 mg", id="decimal"),
    ],
)
def test_sentence_protected_cases(text: str) -> None:
    """T002: protected periods do not make a sentence boundary."""
    spans = sentence_spans(text)
    assert len(spans) == 1
    assert text[spans[0][0] : spans[0][1]] == text


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("Amber. Cobalt.", id="period"),
        pytest.param("Amber? Cobalt.", id="question"),
        pytest.param("Amber! Cobalt.", id="exclamation"),
        pytest.param('Amber." Cobalt.', id="closing-quote"),
        pytest.param("Amber.) Cobalt.", id="closing-bracket"),
        pytest.param("p < 0.05. Cobalt.", id="p-value"),
        pytest.param("5 mg. Cobalt.", id="units"),
        pytest.param("Amber. 2 cobalt.", id="digit"),
    ],
)
def test_sentence_real_boundaries(text: str) -> None:
    """T002: punctuation and following starter make two spans."""
    spans = sentence_spans(text)
    assert len(spans) == 2
    assert text[spans[0][0] : spans[0][1]].strip() != ""
    assert text[spans[1][0] : spans[1][1]].strip() != ""
    assert text[spans[0][1] : spans[1][0]].isspace()


def test_sentence_spans_trim_and_cover_non_whitespace() -> None:
    """T002: sentence spans skip only boundary whitespace."""
    text = "  Amber.  Cobalt!  "
    spans = sentence_spans(text)
    assert [text[start:end] for start, end in spans] == ["Amber.", "Cobalt!"]
    covered = {index for start, end in spans for index in range(start, end)}
    assert covered == {
        index for index, char in enumerate(text) if not char.isspace()
    }


def test_oversize_paragraph_uses_sentence_boundaries() -> None:
    """T002: long paragraphs split into complete sentence pieces."""
    text = "Amber cobalt dapple. Ember fable brindle. Cobalt amber dapple."
    chunks = chunk_section(
        section(),
        [paragraph(text)],
        small_config(content_target_max_tokens=9),
        COUNTER,
    )
    assert len(chunks) >= 2
    assert all(not item.hard_split for item in chunks)
    assert_span_coverage(chunks, [paragraph(text)])


@pytest.mark.parametrize(
    "text",
    [
        pytest.param(synthetic_text(11, 30), id="with-whitespace"),
        pytest.param("amber" * 30, id="without-whitespace"),
    ],
)
def test_oversize_sentence_hard_split(text: str) -> None:
    """T002: oversize sentences use bounded source offsets and flag chunks."""
    source = paragraph(text)
    chunks = chunk_section(
        section(), [source], small_config(content_target_max_tokens=8), COUNTER
    )
    assert len(chunks) > 1
    assert all(item.hard_split for item in chunks)
    assert_span_coverage(chunks, [source])


def test_hard_split_helper_finds_largest_prefix() -> None:
    """T002: helper returns the maximal offset inside the limit."""
    text = "ambercobalt"
    end = largest_end_within_limit(text, 0, 2, COUNTER)
    assert COUNTER.count(text[:end]) <= 2
    assert COUNTER.count(text[: end + 1]) > 2


def test_orphan_merges_with_previous_when_budget_allows() -> None:
    """T002: short trailing chunks merge under the hard budget."""
    chunks = chunk_section(
        section(),
        [paragraph(synthetic_text(9, 8)), paragraph("amber", 2)],
        small_config(soft_min_tokens=8),
        COUNTER,
    )
    assert len(chunks) == 1


def test_first_orphan_merges_with_next_when_budget_allows() -> None:
    """T002: a short first chunk merges forward when permitted."""
    sources = [paragraph("amber"), paragraph(synthetic_text(9, 8), 2)]
    chunks = chunk_section(
        section(), sources, small_config(soft_min_tokens=8), COUNTER
    )
    assert len(chunks) == 1


def test_orphan_stays_when_merge_exceeds_budget() -> None:
    """T002: orphan merging never exceeds the heading-adjusted budget."""
    # Heading overhead is 3: cap 19 leaves 16 content tokens.
    # 15 words split into 8 and 7 words: 16 and 14 tokens.
    # The final 3 words cost 6 tokens; merging costs 20 > 16.
    chunks = chunk_section(
        section(),
        [paragraph(words(15)), paragraph(words(3), 2)],
        small_config(
            operational_cap_tokens=19,
            content_target_max_tokens=16,
            soft_min_tokens=8,
        ),
        COUNTER,
    )
    assert len(chunks) == 3
    assert [chunk.content_tokens for chunk in chunks] == [16, 14, 6]


def test_adjacent_same_paragraph_spans_join_without_separator() -> None:
    """T002: adjacent slices of one paragraph join verbatim."""
    text = "amber" * 30
    chunks = chunk_section(
        section(),
        [paragraph(text)],
        small_config(content_target_max_tokens=8, soft_min_tokens=8),
        COUNTER,
    )
    assert any(len(item.spans) > 1 for item in chunks)
    for item in chunks:
        if len(item.spans) > 1:
            assert item.text == "".join(
                text[span.start : span.end] for span in item.spans
            )


def test_span_offsets_reproduce_chunk_text() -> None:
    """T002: every chunk text is reconstructed from source slices."""
    sources = [paragraph("amber cobalt"), paragraph("dapple ember", 2)]
    chunks = chunk_section(section(), sources, small_config(), COUNTER)
    by_locator = {source.source_locator: source.text for source in sources}
    for item in chunks:
        pieces = [
            by_locator[span.source_locator][span.start : span.end]
            for span in item.spans
        ]
        assert item.text == "\n\n".join(pieces)
        assert item.content_tokens == COUNTER.count(item.text)


def test_seeded_corpus_coverage_and_no_overlap() -> None:
    """T002: every non-whitespace character appears once in order."""
    sources = [
        paragraph(f"  {synthetic_text(seed, 35)}  ", seed + 1)
        for seed in range(4)
    ]
    chunks = chunk_section(section(), sources, small_config(), COUNTER)
    assert_span_coverage(chunks, sources)


def test_all_embedding_inputs_fit_operational_cap() -> None:
    """T002: heading and prefix included, every final input fits."""
    sources = [
        paragraph(synthetic_text(seed, 24), seed + 1) for seed in range(4)
    ]
    config = small_config(prefix_reserve_tokens=3)
    chunks = chunk_section(section(), sources, config, COUNTER)
    assert all(
        COUNTER.count(
            build_embedding_text(item.heading_path, item.text, "passage: ")
        )
        <= config.operational_cap_tokens
        for item in chunks
    )


def test_embedding_inputs_fit_when_heading_budget_binds() -> None:
    """T002: a binding heading budget caps every final input."""
    # cap 30 - reserve 3 - heading overhead 3 = 24 content tokens.
    sources = [paragraph(words(20), index) for index in range(1, 4)]
    config = small_config(
        operational_cap_tokens=30,
        content_target_max_tokens=30,
        prefix_reserve_tokens=3,
    )
    chunks = chunk_section(section(), sources, config, COUNTER)
    assert all(
        COUNTER.count(
            build_embedding_text(item.heading_path, item.text, "passage: ")
        )
        <= 30
        for item in chunks
    )
    assert any(item.content_tokens == 24 for item in chunks)


def test_sentence_lowercase_follower_is_not_boundary() -> None:
    """T002: lowercase text after a period stays in one span."""
    text = "Amber. cobalt follows."
    assert sentence_spans(text) == [(0, len(text))]


def test_chunking_is_deterministic() -> None:
    """T002: identical inputs yield equal ordered chunks."""
    sources = [paragraph(synthetic_text(42, 40))]
    first = chunk_section(section(), sources, small_config(), COUNTER)
    second = chunk_section(section(), sources, small_config(), COUNTER)
    assert first == second


def test_hard_split_uses_whitespace_at_prefix_end() -> None:
    """T002 carry-over RED: prefix-end whitespace is a split boundary."""
    chunks = chunk_section(
        section(path=()),
        [paragraph("ab cdefghijk lm")],
        small_config(
            content_target_min_tokens=2,
            content_target_max_tokens=4,
            soft_min_tokens=0,
        ),
        COUNTER,
    )
    assert [chunk.text for chunk in chunks] == ["ab cdefghijk", "lm"]
    assert [chunk.hard_split for chunk in chunks] == [True, True]


@pytest.mark.parametrize(
    "sources",
    [
        pytest.param(
            [paragraph("amber", section_id="missing")], id="unknown-section"
        ),
        pytest.param(
            [paragraph("amber"), paragraph("cobalt")], id="duplicate-index"
        ),
        pytest.param(
            [paragraph("amber", 2), paragraph("cobalt", 1)],
            id="decreasing-index",
        ),
        pytest.param(
            [SourceParagraph("10.0000/other", "s1", 1, "amber", "loc-1")],
            id="doi-mismatch",
        ),
    ],
)
def test_chunk_sections_rejects_invalid_sources(
    sources: list[SourceParagraph],
) -> None:
    """T002: reject unknown, unordered, and cross-DOI paragraphs."""
    with pytest.raises(ChunkingError):
        chunk_sections([section()], sources, small_config(), COUNTER)
