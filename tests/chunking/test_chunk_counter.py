"""RED behavior tests for T001 token accounting and text templates."""

import pytest

from sciscope.chunking.config import (
    CONTEXT_TEXT_SEPARATOR,
    HEADING_SEPARATOR,
    TEMPLATE_VERSION,
    UNTITLED_LABEL,
    ChunkConfig,
    ConfigError,
    HeadingBudgetError,
    build_embedding_text,
    content_budget,
    heading_context,
)
from sciscope.chunking.counter import Utf8BytesDiv3Counter
from sciscope.jats.parser import UNTITLED_LABEL as JATS_UNTITLED_LABEL


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("", 0, id="T001-empty"),
        pytest.param("abcdefg", 3, id="T001-ascii"),
        pytest.param("é", 1, id="T001-two-byte"),
        pytest.param("€", 1, id="T001-three-byte"),
        pytest.param("😀", 2, id="T001-four-byte"),
    ],
)
def test_counter_utf8_ceiling(text: str, expected: int) -> None:
    """T001: count UTF-8 bytes in groups of three."""
    assert Utf8BytesDiv3Counter().count(text) == expected


def test_counter_version_and_determinism() -> None:
    """T001: expose a stable version and deterministic counts."""
    counter = Utf8BytesDiv3Counter()
    assert counter.counter_id == "utf8-bytes-div3-v1"
    assert counter.count("invented 😀") == counter.count("invented 😀")


@pytest.mark.parametrize("left", ["", "a", "é", "😀", "abc"])
@pytest.mark.parametrize("right", ["", "b", "€", "😀", "def"])
def test_counter_subadditive(left: str, right: str) -> None:
    """T001: joined text never exceeds the sum of part counts."""
    counter = Utf8BytesDiv3Counter()
    assert counter.count(left + right) <= (
        counter.count(left) + counter.count(right)
    )


def test_config_defaults() -> None:
    """T001: retain the approved provisional limits."""
    assert ChunkConfig() == ChunkConfig(
        operational_cap_tokens=384,
        content_target_min_tokens=200,
        content_target_max_tokens=350,
        soft_min_tokens=50,
        prefix_reserve_tokens=0,
        min_content_budget_tokens=32,
    )


@pytest.mark.parametrize(
    "changes",
    [
        pytest.param({"operational_cap_tokens": 0}, id="T001-cap-zero"),
        pytest.param({"operational_cap_tokens": 513}, id="T001-cap-high"),
        pytest.param({"prefix_reserve_tokens": -1}, id="T001-reserve-negative"),
        pytest.param(
            {"prefix_reserve_tokens": 384}, id="T001-reserve-equals-cap"
        ),
        pytest.param(
            {"content_target_min_tokens": 0}, id="T001-target-min-zero"
        ),
        pytest.param(
            {"content_target_min_tokens": 351}, id="T001-target-inverted"
        ),
        pytest.param({"soft_min_tokens": -1}, id="T001-soft-negative"),
        pytest.param(
            {"min_content_budget_tokens": 0}, id="T001-budget-min-zero"
        ),
    ],
)
def test_config_rejects_invalid(changes: dict[str, int]) -> None:
    """T001: invalid configuration raises the domain error."""
    with pytest.raises(ConfigError):
        ChunkConfig(**changes)


def test_template_constants_match_f002() -> None:
    """T001: shared sentinel and template literals stay stable."""
    assert UNTITLED_LABEL == JATS_UNTITLED_LABEL
    assert TEMPLATE_VERSION == "embedding-text-v1"
    assert HEADING_SEPARATOR == " > "
    assert CONTEXT_TEXT_SEPARATOR == "\n\n"
    assert heading_context((UNTITLED_LABEL,)) == ""


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        pytest.param(("Methods", "Samples"), "Methods > Samples", id="nested"),
        pytest.param(("(untitled)",), "", id="untitled-only"),
        pytest.param(
            ("(untitled)", "Background"), "Background", id="structured"
        ),
        pytest.param((), "", id="empty"),
        pytest.param((" ", "Results", ""), "Results", id="blank"),
    ],
)
def test_heading_context(path: tuple[str, ...], expected: str) -> None:
    """T001: synthetic and blank headings do not enter the template."""
    assert heading_context(path) == expected


@pytest.mark.parametrize(
    ("path", "prefix", "expected"),
    [
        pytest.param(("Methods",), "", "Methods\n\ncoined", id="heading"),
        pytest.param(
            ("Methods",),
            "passage: ",
            "passage: Methods\n\ncoined",
            id="prefix",
        ),
        pytest.param(("(untitled)",), "", "coined", id="no-context"),
        pytest.param(
            ("",), "passage: ", "passage: coined", id="prefix-no-context"
        ),
    ],
)
def test_build_embedding_text(
    path: tuple[str, ...], prefix: str, expected: str
) -> None:
    """T001: preserve the prefix and chunk text exactly."""
    assert build_embedding_text(path, "coined", prefix) == expected


def test_budget_subtracts_heading_and_reserve() -> None:
    """T001: count the full context separator as overhead."""
    config = ChunkConfig(prefix_reserve_tokens=3)
    counter = Utf8BytesDiv3Counter()
    expected = 384 - 3 - counter.count("Methods\n\n")
    assert content_budget(config, counter, ("Methods",)) == expected


def test_budget_without_heading() -> None:
    """T001: untitled paths spend no heading budget."""
    assert (
        content_budget(ChunkConfig(), Utf8BytesDiv3Counter(), ("(untitled)",))
        == 384
    )


@pytest.mark.parametrize(
    "heading_length",
    [
        pytest.param(34, id="T001-zero-budget"),
        pytest.param(37, id="T001-negative-budget"),
    ],
)
def test_budget_rejects_exhausted_heading(heading_length: int) -> None:
    """T001: zero or negative budgets reject the heading."""
    counter = Utf8BytesDiv3Counter()
    heading = "H" * heading_length
    with pytest.raises(HeadingBudgetError):
        content_budget(
            ChunkConfig(operational_cap_tokens=12, min_content_budget_tokens=1),
            counter,
            (heading,),
        )


def test_budget_bounds_complete_embedding_input() -> None:
    """T001: a reserved prefix and budgeted text fit the full cap."""
    counter = Utf8BytesDiv3Counter()
    config = ChunkConfig(prefix_reserve_tokens=3)
    path = ("Methods",)
    prefix = "passage: "
    budget = content_budget(config, counter, path)
    text = "x" * (budget * 3)
    assert counter.count(prefix) <= config.prefix_reserve_tokens
    assert counter.count(text) <= budget
    assert counter.count(build_embedding_text(path, text, prefix)) <= (
        config.operational_cap_tokens
    )
