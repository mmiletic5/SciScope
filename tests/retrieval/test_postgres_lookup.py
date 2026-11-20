"""Read-only lookup integration tests against the accepted Phase A pilot."""

from __future__ import annotations

import pytest
from sqlalchemy import select, text

from sciscope.database.models import Chunk, DeliveryImport
from sciscope.retrieval._lookup import (
    EvidenceLookup,
    EvidenceLookupCode,
    EvidenceLookupFailure,
)


def _active_chunk(engine):
    with engine.connect() as connection:
        with connection.begin():
            connection.execute(text("SET TRANSACTION READ ONLY"))
            import_id = connection.execute(
                select(DeliveryImport.id).where(
                    DeliveryImport.is_active.is_(True)
                )
            ).scalar_one()
            row = connection.execute(
                select(
                    Chunk.chunk_id,
                    Chunk.doi,
                    Chunk.text,
                    Chunk.source_locator,
                    Chunk.spans,
                )
                .where(Chunk.delivery_import_id == import_id)
                .order_by(Chunk.chunk_id)
                .limit(1)
            ).one()
            return row


def test_lookup_paper_and_chunk_preserve_active_snapshot(
    retrieval_engine,
) -> None:
    """DOI and chunk selectors return exact active data plus corpus identity."""
    sample = _active_chunk(retrieval_engine)
    lookup = EvidenceLookup(retrieval_engine)

    paper = lookup.get_paper(sample.doi)
    chunk = lookup.get_chunk(sample.chunk_id)

    assert paper.paper.doi == sample.doi
    assert chunk.chunk.chunk_id == sample.chunk_id
    assert chunk.chunk.text == sample.text
    assert chunk.corpus.delivery_digest.startswith("sha256:")
    assert chunk.corpus.source_contract_version == "0.3.0"
    assert chunk.corpus.corpus_version.startswith("pilot17-xml-")


def test_locator_lookup_matches_primary_or_span_exactly(
    retrieval_engine,
) -> None:
    """Locator lookup returns all exact span owners in deterministic order."""
    sample = _active_chunk(retrieval_engine)
    lookup = EvidenceLookup(retrieval_engine)
    span_locator = sample.spans[0]["source_locator"]

    results = lookup.get_by_locator(sample.doi, span_locator)

    assert results
    assert [item.chunk.chunk_id for item in results] == sorted(
        item.chunk.chunk_id for item in results
    )
    assert any(
        item.chunk.source_locator == span_locator
        or any(
            span["source_locator"] == span_locator for span in item.chunk.spans
        )
        for item in results
    )
    assert all(
        item.corpus.delivery_digest == results[0].corpus.delivery_digest
        for item in results
    )
    assert lookup.get_by_locator(sample.doi, span_locator + ":missing") == ()


def test_doi_lookup_normalizes_input_and_reports_missing_paper(
    retrieval_engine,
) -> None:
    """DOI normalization is exact and misses have a stable not-found code."""
    sample = _active_chunk(retrieval_engine)
    lookup = EvidenceLookup(retrieval_engine)
    found = lookup.get_paper(sample.doi.upper())
    assert found.paper.doi == sample.doi
    with pytest.raises(EvidenceLookupFailure) as raised:
        lookup.get_paper("10.9999/phase-c-not-found")
    assert raised.value.code == EvidenceLookupCode.NOT_FOUND


def test_unknown_chunk_is_explicit_not_found(retrieval_engine) -> None:
    """An unknown exact identifier does not fall back to another snapshot."""
    candidate_id = "f" * 64
    with retrieval_engine.connect() as connection:
        exists = connection.execute(
            select(Chunk.chunk_id).where(Chunk.chunk_id == candidate_id)
        ).scalar_one_or_none()
    if exists is not None:
        pytest.skip(
            "chosen deterministic not-found identifier exists in fixture"
        )

    with pytest.raises(EvidenceLookupFailure) as raised:
        EvidenceLookup(retrieval_engine).get_chunk(candidate_id)
    assert raised.value.code == EvidenceLookupCode.NOT_FOUND


def test_lookup_transaction_is_repeatable_read_and_read_only(
    retrieval_engine,
) -> None:
    """Lookup snapshot transaction enforces the approved PostgreSQL mode."""
    with EvidenceLookup(retrieval_engine)._snapshot() as (connection, _corpus):
        isolation = connection.execute(
            text("SHOW transaction_isolation")
        ).scalar_one()
        read_only = connection.execute(
            text("SHOW transaction_read_only")
        ).scalar_one()
    assert isolation == "repeatable read"
    assert read_only == "on"
