"""Guarded public-facade PostgreSQL integration coverage for T007-E."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, select, text

from sciscope.database.models import Chunk, DeliveryImport, Paper
from sciscope.retrieval import (
    RetrievalRequest,
    RetrievalResponse,
    RetrievalService,
)
from sciscope.retrieval.service import _compose_private_executor


@dataclass(frozen=True, slots=True)
class _ActiveSnapshot:
    """Read-only identity of the active corpus before or after retrieval."""

    import_id: int
    delivery_digest: str
    source_contract_version: str
    paper_count: int
    section_count: int
    chunk_count: int
    vector_count: int


@dataclass(frozen=True, slots=True)
class _SourceRecord:
    """Exact source fields stored for one active corpus chunk."""

    chunk_id: str
    text: str
    doi: str
    source_locator: str
    section_id: str
    section_path: list[object]
    title: str
    authors: list[object]
    journal: str
    publication_year: int
    language: str
    license: str
    source_url: str


def _active_snapshot(engine: Engine) -> _ActiveSnapshot:
    """Read active corpus identity in a repeatable, read-only transaction."""
    with engine.connect() as connection:
        with connection.begin():
            connection.execute(
                text(
                    "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
                )
            )
            isolation, read_only = connection.execute(
                text(
                    "SELECT current_setting('transaction_isolation'), "
                    "current_setting('transaction_read_only')"
                )
            ).one()
            assert isolation == "repeatable read"
            assert read_only == "on"
            row = connection.execute(
                select(
                    DeliveryImport.id,
                    DeliveryImport.delivery_digest,
                    DeliveryImport.contract_version,
                    DeliveryImport.paper_count,
                    DeliveryImport.section_count,
                    DeliveryImport.chunk_count,
                    DeliveryImport.vector_count,
                ).where(DeliveryImport.is_active.is_(True))
            ).one()
    return _ActiveSnapshot(*row)


def _source_record(
    engine: Engine, *, import_id: int, chunk_id: str
) -> _SourceRecord:
    """Read one response source from the active corpus without writes."""
    with engine.connect() as connection:
        with connection.begin():
            connection.execute(
                text(
                    "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"
                )
            )
            row = connection.execute(
                select(
                    Chunk.chunk_id,
                    Chunk.text,
                    Chunk.doi,
                    Chunk.source_locator,
                    Chunk.section_id,
                    Chunk.section_path,
                    Paper.title,
                    Paper.authors,
                    Paper.journal,
                    Paper.publication_year,
                    Paper.language,
                    Paper.license,
                    Paper.source_url,
                )
                .join(
                    Paper,
                    (Paper.delivery_import_id == Chunk.delivery_import_id)
                    & (Paper.doi == Chunk.doi),
                )
                .where(
                    Chunk.delivery_import_id == import_id,
                    Chunk.chunk_id == chunk_id,
                )
            ).one()
    return _SourceRecord(*row)


def test_public_service_reads_active_v1_lexical_corpus_read_only(
    retrieval_engine: Engine,
) -> None:
    """The public lexical facade preserves the active corpus without writes."""
    before = _active_snapshot(retrieval_engine)
    executor = _compose_private_executor(
        engine=retrieval_engine,
        embedder=None,
    )
    service = RetrievalService(executor=executor)
    request = RetrievalRequest(
        contract_version="retrieval.v1",
        request_id="public-postgres-v1-lexical",
        query_text="bee",
        mode="lexical",
        top_k=5,
    )

    first = service.retrieve(request)
    second = service.retrieve(request)

    assert isinstance(first, RetrievalResponse)
    assert first.contract_version == request.contract_version
    assert first.request_id == request.request_id
    assert first.retrieval.mode == request.mode
    assert first.retrieval.top_k == request.top_k
    assert first.embedding is None
    assert first.corpus.delivery_digest == before.delivery_digest
    assert (
        first.corpus.source_contract_version == before.source_contract_version
    )
    assert first.corpus.corpus_version.startswith("pilot17-xml-")
    assert first.results
    assert first == second

    assert [result.rank for result in first.results] == list(
        range(1, len(first.results) + 1)
    )
    for result in first.results:
        source = _source_record(
            retrieval_engine,
            import_id=before.import_id,
            chunk_id=result.chunk_id,
        )
        assert len(result.chunk_id) == 64
        assert result.chunk_id == source.chunk_id
        assert result.text == source.text
        assert result.doi == source.doi
        assert result.source_locator == source.source_locator
        assert result.section_id == source.section_id
        assert result.section_path == tuple(source.section_path)
        assert result.paper.title == source.title
        assert [
            (author.surname, author.given_names)
            for author in result.paper.authors
        ] == [
            (author["surname"], author["given_names"])
            for author in source.authors
        ]
        assert result.paper.journal == source.journal
        assert result.paper.publication_year == source.publication_year
        assert result.paper.language == source.language
        assert result.paper.license == source.license
        assert result.paper.source_url == source.source_url
        assert result.scores.lexical_rank is not None
        assert result.scores.lexical_score is not None
        assert result.scores.dense_rank is None
        assert result.scores.dense_similarity is None
        assert result.scores.fusion_score is None
        assert not hasattr(result, "citation")

    after = _active_snapshot(retrieval_engine)
    assert before == after
