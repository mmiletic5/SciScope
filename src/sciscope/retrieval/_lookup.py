"""Exact, active-snapshot evidence lookup for DOI and source identifiers."""

from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from sqlalchemy import Engine, or_, select
from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.sql import Select

from sciscope.database.models import Chunk, Paper, Section
from sciscope.plos_pilot.doi import normalize_doi
from sciscope.retrieval._core import (
    _Corpus,
    _read_corpus,
    _set_read_only_repeatable_read,
)
from sciscope.retrieval._errors import RetrievalErrorCode, RetrievalFailure

_CHUNK_ID = re.compile(r"^[0-9a-f]{64}$")


class EvidenceLookupCode(StrEnum):
    """Stable lookup failure identifiers."""

    INVALID_IDENTIFIER = "INVALID_IDENTIFIER"
    NOT_FOUND = "NOT_FOUND"
    CORPUS_NOT_LOADED = "CORPUS_NOT_LOADED"
    DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class EvidenceLookupFailure(RuntimeError):
    """Sanitized lookup error carrying a stable public code."""

    def __init__(self, code: EvidenceLookupCode) -> None:
        """Create the failure without retaining driver details."""
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True, slots=True)
class CorpusProvenance:
    """Snapshot identity captured in the lookup transaction."""

    import_id: int
    delivery_digest: str
    source_contract_version: str
    corpus_version: str


@dataclass(frozen=True, slots=True)
class PaperRecord:
    """Citation metadata for one exact DOI in the active snapshot."""

    doi: str
    title: str
    authors: tuple[Any, ...]
    journal: str
    publication_date: str
    publication_year: int
    article_type: str
    subjects: tuple[Any, ...]
    license: str
    language: str
    source_url: str
    retrieved_at: str
    xml_sha256: str


@dataclass(frozen=True, slots=True)
class EvidenceChunk:
    """Exact stored chunk and section/source metadata."""

    chunk_id: str
    doi: str
    section_id: str
    text: str
    source_locator: str
    spans: tuple[dict[str, Any], ...]
    section_path: tuple[Any, ...]
    normalized_type: str
    content_token_count: int


@dataclass(frozen=True, slots=True)
class PaperLookupResult:
    """Paper result paired with the snapshot that supplied it."""

    corpus: CorpusProvenance
    paper: PaperRecord


@dataclass(frozen=True, slots=True)
class ChunkLookupResult:
    """Chunk result paired with the snapshot that supplied it."""

    corpus: CorpusProvenance
    chunk: EvidenceChunk


class EvidenceLookup:
    """Read exact identifiers from one active snapshot per request."""

    def __init__(self, engine: Engine) -> None:
        """Bind the existing retrieval database engine."""
        self._engine = engine

    def get_paper(self, doi: str) -> PaperLookupResult:
        """Look up one paper by normalized DOI in the active snapshot."""
        normalized = self._doi(doi)
        with self._snapshot() as (connection, corpus):
            row = connection.execute(
                select(
                    Paper.doi,
                    Paper.title,
                    Paper.authors,
                    Paper.journal,
                    Paper.publication_date,
                    Paper.publication_year,
                    Paper.article_type,
                    Paper.subjects,
                    Paper.license,
                    Paper.language,
                    Paper.source_url,
                    Paper.retrieved_at,
                    Paper.xml_sha256,
                ).where(
                    Paper.delivery_import_id == corpus.import_id,
                    Paper.doi == normalized,
                )
            ).one_or_none()
            if row is None:
                raise EvidenceLookupFailure(EvidenceLookupCode.NOT_FOUND)
            paper = PaperRecord(
                doi=row.doi,
                title=row.title,
                authors=tuple(row.authors),
                journal=row.journal,
                publication_date=row.publication_date,
                publication_year=row.publication_year,
                article_type=row.article_type,
                subjects=tuple(row.subjects),
                license=row.license,
                language=row.language,
                source_url=row.source_url,
                retrieved_at=row.retrieved_at,
                xml_sha256=row.xml_sha256,
            )
            return PaperLookupResult(self._provenance(corpus), paper)

    def get_by_locator(
        self, doi: str, source_locator: str
    ) -> tuple[ChunkLookupResult, ...]:
        """Find chunks by exact primary or span locator for an exact DOI."""
        normalized = self._doi(doi)
        if not isinstance(source_locator, str) or not source_locator.strip():
            raise EvidenceLookupFailure(EvidenceLookupCode.INVALID_IDENTIFIER)
        with self._snapshot() as (connection, corpus):
            rows = connection.execute(
                self._chunk_statement(corpus.import_id)
                .where(
                    Chunk.doi == normalized,
                    or_(
                        Chunk.source_locator == source_locator,
                        Chunk.spans.contains(
                            [{"source_locator": source_locator}]
                        ),
                    ),
                )
                .order_by(Chunk.chunk_id.asc())
            ).all()
            return tuple(
                ChunkLookupResult(self._provenance(corpus), self._chunk(row))
                for row in rows
            )

    def get_chunk(self, chunk_id: str) -> ChunkLookupResult:
        """Look up a lowercase SHA-256 chunk ID in the active snapshot."""
        if not isinstance(chunk_id, str) or not _CHUNK_ID.fullmatch(chunk_id):
            raise EvidenceLookupFailure(EvidenceLookupCode.INVALID_IDENTIFIER)
        with self._snapshot() as (connection, corpus):
            row = connection.execute(
                self._chunk_statement(corpus.import_id).where(
                    Chunk.chunk_id == chunk_id
                )
            ).one_or_none()
            if row is None:
                raise EvidenceLookupFailure(EvidenceLookupCode.NOT_FOUND)
            return ChunkLookupResult(self._provenance(corpus), self._chunk(row))

    @staticmethod
    def _doi(value: str) -> str:
        try:
            return normalize_doi(value).doi
        except (TypeError, ValueError):
            raise EvidenceLookupFailure(
                EvidenceLookupCode.INVALID_IDENTIFIER
            ) from None

    @staticmethod
    def _chunk_statement(import_id: int) -> Select[Any]:
        return (
            select(
                Chunk.chunk_id,
                Chunk.doi,
                Chunk.section_id,
                Chunk.text,
                Chunk.source_locator,
                Chunk.spans,
                Chunk.section_path,
                Chunk.content_token_count,
                Section.normalized_type,
            )
            .join(
                Section,
                (Section.delivery_import_id == Chunk.delivery_import_id)
                & (Section.doi == Chunk.doi)
                & (Section.section_id == Chunk.section_id),
            )
            .where(Chunk.delivery_import_id == import_id)
        )

    @staticmethod
    def _chunk(row: Any) -> EvidenceChunk:
        return EvidenceChunk(
            chunk_id=row.chunk_id,
            doi=row.doi,
            section_id=row.section_id,
            text=row.text,
            source_locator=row.source_locator,
            spans=tuple(dict(span) for span in row.spans),
            section_path=tuple(row.section_path),
            normalized_type=row.normalized_type,
            content_token_count=row.content_token_count,
        )

    @staticmethod
    def _provenance(corpus: Any) -> CorpusProvenance:
        return CorpusProvenance(
            import_id=corpus.import_id,
            delivery_digest=corpus.delivery_digest,
            source_contract_version=corpus.source_contract_version,
            corpus_version=corpus.corpus_version,
        )

    @contextmanager
    def _snapshot(self) -> Iterator[tuple[Connection, _Corpus]]:
        try:
            with self._engine.connect() as connection:
                with connection.begin():
                    _set_read_only_repeatable_read(connection)
                    corpus = _read_corpus(
                        connection, request_id="evidence-lookup"
                    )
                    yield connection, corpus
        except EvidenceLookupFailure:
            raise
        except RetrievalFailure as error:
            code = (
                EvidenceLookupCode.CORPUS_NOT_LOADED
                if error.code == RetrievalErrorCode.CORPUS_NOT_LOADED
                else EvidenceLookupCode.INTERNAL_ERROR
            )
            raise EvidenceLookupFailure(code) from None
        except SQLAlchemyError as error:
            code = (
                EvidenceLookupCode.DATABASE_UNAVAILABLE
                if isinstance(error, OperationalError)
                else EvidenceLookupCode.INTERNAL_ERROR
            )
            raise EvidenceLookupFailure(code) from None
