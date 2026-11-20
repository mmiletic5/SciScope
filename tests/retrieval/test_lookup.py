"""Input validation tests for exact active-snapshot evidence lookup."""

from __future__ import annotations

from typing import cast

import pytest
from sqlalchemy import Engine

from sciscope.retrieval._lookup import (
    EvidenceLookup,
    EvidenceLookupCode,
    EvidenceLookupFailure,
)


def _lookup() -> EvidenceLookup:
    return EvidenceLookup(cast(Engine, None))


@pytest.mark.parametrize("doi", ["", "not-a-doi", "https://doi.org/"])
def test_invalid_doi_fails_before_database_access(doi: str) -> None:
    """Malformed DOI selectors produce a stable input error."""
    with pytest.raises(EvidenceLookupFailure) as raised:
        _lookup().get_paper(doi)
    assert raised.value.code == EvidenceLookupCode.INVALID_IDENTIFIER


@pytest.mark.parametrize("locator", ["", "\n"])
def test_empty_locator_fails_before_database_access(locator: str) -> None:
    """Opaque locators must be nonempty strings without normalization."""
    with pytest.raises(EvidenceLookupFailure) as raised:
        _lookup().get_by_locator("10.1234/example", locator)
    assert raised.value.code == EvidenceLookupCode.INVALID_IDENTIFIER


@pytest.mark.parametrize("chunk_id", ["A" * 64, "abc", "g" * 64])
def test_malformed_chunk_id_fails_before_database_access(chunk_id: str) -> None:
    """Chunk IDs must use the exact lowercase SHA-256 hex representation."""
    with pytest.raises(EvidenceLookupFailure) as raised:
        _lookup().get_chunk(chunk_id)
    assert raised.value.code == EvidenceLookupCode.INVALID_IDENTIFIER
