"""Behavior tests for digest-bound JATS element locators."""

import hashlib
from xml.etree import ElementTree as ET

import pytest
from jats_fixtures import synthetic_xml

from sciscope.jats.locator import (
    DigestMismatchError,
    ForeignElementError,
    InvalidTargetError,
    MalformedLocatorError,
    PathNotFoundError,
    SourceDocument,
    local_name,
    locator_digest,
)


def test_local_name_strips_namespace() -> None:
    """Namespaced and plain elements expose their local names."""
    assert (
        local_name(ET.fromstring(synthetic_xml("<x:sec xmlns:x='urn:fake'/>")))
        == "sec"
    )
    assert local_name(ET.fromstring(synthetic_xml("<p/>"))) == "p"


def test_locator_digest_extracts_lowercase_digest_without_path_validation() -> (
    None
):
    """SYNTHETIC digest extraction checks only prefix and digest syntax."""
    digest = "a" * 64
    assert locator_digest(f"jats:v1:{digest}:/any/path") == digest


@pytest.mark.parametrize(
    "locator",
    [
        "jats:v1:{upper}:/article[1]",
        "jats:v2:{digest}:/article[1]",
        "other:v1:{digest}:/article[1]",
        "jats:v1:short:/article[1]",
        "jats:v1:{digest}",
        "jats:v1::/article[1]",
    ],
)
def test_locator_digest_rejects_invalid_prefix_or_digest(locator: str) -> None:
    """SYNTHETIC malformed locator heads raise the public error kind."""
    digest = "a" * 64
    with pytest.raises(MalformedLocatorError):
        locator_digest(locator.format(digest=digest, upper=digest.upper()))


def test_from_bytes_hashes_exact_input_and_exposes_root() -> None:
    """The digest binds the original bytes, including the synthetic marker."""
    xml_bytes = synthetic_xml("<article><body/></article>")
    document = SourceDocument.from_bytes(xml_bytes)

    assert document.sha256 == hashlib.sha256(xml_bytes).hexdigest()
    assert local_name(document.root) == "article"


def test_namespaced_paths_use_local_names_and_same_name_indices() -> None:
    """Other sibling kinds do not advance a section or paragraph index."""
    document = SourceDocument.from_bytes(
        synthetic_xml(
            "<j:article xmlns:j='urn:fake'><j:body><j:sec><j:p>A</j:p>"
            "<j:fig/><j:p>B</j:p></j:sec><j:title>Skip</j:title>"
            "<j:sec><j:p>C</j:p></j:sec></j:body></j:article>"
        )
    )
    body = next(iter(document.root))
    first_section, _, second_section = list(body)
    second_paragraph = list(first_section)[2]

    assert document.locator_for(second_paragraph).endswith(
        "/article[1]/body[1]/sec[1]/p[2]"
    )
    assert document.locator_for(second_section).endswith(
        "/article[1]/body[1]/sec[2]"
    )


def test_root_locator_is_anchored_but_not_a_resolvable_target() -> None:
    """The root can be located, while resolution accepts only units."""
    document = SourceDocument.from_bytes(synthetic_xml("<article/>"))
    root_locator = document.locator_for(document.root)

    assert root_locator == f"jats:v1:{document.sha256}:/article[1]"
    with pytest.raises(InvalidTargetError):
        document.resolve(root_locator)


def test_section_paragraph_and_abstract_locators_round_trip() -> None:
    """All three supported target kinds resolve to the original objects."""
    document = SourceDocument.from_bytes(
        synthetic_xml(
            "<article><front><article-meta><abstract><p>Fake.</p>"
            "</abstract></article-meta></front><body><sec><p>Fake.</p>"
            "</sec></body></article>"
        )
    )
    abstract = document.root.find("./front/article-meta/abstract")
    section = document.root.find("./body/sec")
    paragraph = document.root.find("./body/sec/p")

    for element in (abstract, section, paragraph):
        assert element is not None
        assert document.resolve(document.locator_for(element)) is element


def test_repeated_builds_produce_identical_locators() -> None:
    """Source positions and digests are stable across separate parses."""
    xml_bytes = synthetic_xml(
        "<article><body><sec><p>Fake.</p></sec></body></article>"
    )
    first = SourceDocument.from_bytes(xml_bytes)
    second = SourceDocument.from_bytes(xml_bytes)
    first_paragraph = first.root.find("./body/sec/p")
    second_paragraph = second.root.find("./body/sec/p")

    assert first_paragraph is not None
    assert second_paragraph is not None
    assert first.locator_for(first_paragraph) == second.locator_for(
        second_paragraph
    )
    assert first.locator_for(first_paragraph) == first.locator_for(
        first_paragraph
    )


def test_foreign_element_is_rejected() -> None:
    """An element from another parse cannot receive this document's digest."""
    xml_bytes = synthetic_xml("<article><body><sec/></body></article>")
    first = SourceDocument.from_bytes(xml_bytes)
    second = SourceDocument.from_bytes(xml_bytes)
    foreign_section = second.root.find("./body/sec")

    assert foreign_section is not None
    with pytest.raises(ForeignElementError):
        first.locator_for(foreign_section)


@pytest.mark.parametrize(
    "bad_locator",
    [
        "jats:v2:{digest}:/article[1]/body[1]/sec[1]",
        "other:v1:{digest}:/article[1]/body[1]/sec[1]",
        "jats:v1:{upper_digest}:/article[1]/body[1]/sec[1]",
        "jats:v1:short:/article[1]/body[1]/sec[1]",
        "jats:v1:{digest}:article[1]/body[1]/sec[1]",
        "jats:v1:{digest}:/article[0]/body[1]/sec[1]",
        "jats:v1:{digest}:/article[01]/body[1]/sec[1]",
        "jats:v1:{digest}:/article[-1]/body[1]/sec[1]",
        "jats:v1:{digest}:/article[1]/body[x]/sec[1]",
        "jats:v1:{digest}:/article[1]//sec[1]",
        "jats:v1:{digest}:/article[1]/body[1]/sec[1]:extra",
    ],
)
def test_malformed_locator_is_rejected(bad_locator: str) -> None:
    """Invalid version, digest syntax, and path grammar have one error kind."""
    document = SourceDocument.from_bytes(
        synthetic_xml("<article><body><sec/></body></article>")
    )
    locator = bad_locator.format(
        digest=document.sha256, upper_digest=document.sha256.upper()
    )

    with pytest.raises(MalformedLocatorError):
        document.resolve(locator)


def test_digest_mismatch_is_checked_before_path_traversal() -> None:
    """A valid foreign digest wins over a nonexistent element path."""
    document = SourceDocument.from_bytes(synthetic_xml("<article/>"))
    foreign_digest = "0" * 64 if document.sha256 != "0" * 64 else "1" * 64

    with pytest.raises(DigestMismatchError):
        document.resolve(f"jats:v1:{foreign_digest}:/article[1]/sec[999]")


@pytest.mark.parametrize(
    "path",
    ["/article[2]", "/other[1]", "/article[1]/body[1]/sec[2]"],
)
def test_well_formed_missing_path_is_rejected(path: str) -> None:
    """Syntactically valid paths without a matching node have a path error."""
    document = SourceDocument.from_bytes(
        synthetic_xml("<article><body><sec/></body></article>")
    )

    with pytest.raises(PathNotFoundError):
        document.resolve(f"jats:v1:{document.sha256}:{path}")


@pytest.mark.parametrize(
    "path", ["/article[1]/body[1]/title[1]", "/article[1]/body[1]/fig[1]"]
)
def test_existing_unsupported_target_is_rejected(path: str) -> None:
    """Titles and figures cannot serve as v1 resolved units."""
    document = SourceDocument.from_bytes(
        synthetic_xml(
            "<article><body><title>Fake</title><fig/></body></article>"
        )
    )

    with pytest.raises(InvalidTargetError):
        document.resolve(f"jats:v1:{document.sha256}:{path}")
