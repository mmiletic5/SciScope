"""SQLAlchemy metadata for the approved six-table persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for database-owned schema metadata."""

    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(table_name)s_%(column_0_N_name)s",
            "uq": "uq_%(table_name)s_%(column_0_N_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )


class DeliveryImport(Base):
    """Identity and activation audit for one immutable delivery."""

    __tablename__ = "delivery_imports"
    __table_args__ = (
        CheckConstraint(
            "delivery_digest ~ '^sha256:[0-9a-f]{64}$'", name="digest"
        ),
        CheckConstraint(
            "paper_count >= 0 AND section_count >= 0 "
            "AND chunk_count >= 0 AND vector_count >= 0",
            name="nonnegative_counts",
        ),
        CheckConstraint(
            "schema_version <> '' AND contract_version <> '' "
            "AND jsonb_typeof(processing_versions) = 'object' "
            "AND jsonb_typeof(delivery_manifest) = 'object'",
            name="json_objects",
        ),
        Index(
            "uq_delivery_imports_one_active",
            "is_active",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    delivery_digest: Mapped[str] = mapped_column(String(71), nullable=False)
    schema_version: Mapped[str] = mapped_column(Text, nullable=False)
    contract_version: Mapped[str] = mapped_column(Text, nullable=False)
    paper_count: Mapped[int] = mapped_column(Integer, nullable=False)
    section_count: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False)
    vector_count: Mapped[int] = mapped_column(Integer, nullable=False)
    processing_versions: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )
    delivery_manifest: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )


class EmbeddingSet(Base):
    """Fixed embedding model and manifest metadata for an import."""

    __tablename__ = "embedding_sets"
    __table_args__ = (
        UniqueConstraint("delivery_import_id"),
        UniqueConstraint("id", "delivery_import_id"),
        CheckConstraint(
            "provider = 'openai' AND model = 'text-embedding-3-small' "
            "AND dimensions = 1536 AND dtype = 'float32-le' "
            "AND passage_prefix = '' AND query_prefix = ''",
            name="fixed_model",
        ),
        CheckConstraint(
            "normalization_tolerance > 0", name="positive_tolerance"
        ),
        CheckConstraint(
            "chunk_sha256 ~ '^[0-9a-f]{64}$' "
            "AND vector_sha256 ~ '^[0-9a-f]{64}$'",
            name="hashes",
        ),
        CheckConstraint(
            "jsonb_typeof(embedding_manifest) = 'object'",
            name="manifest_object",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    delivery_import_id: Mapped[int] = mapped_column(
        ForeignKey("delivery_imports.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    dtype: Mapped[str] = mapped_column(Text, nullable=False)
    passage_prefix: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=""
    )
    query_prefix: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=""
    )
    # Numeric target L2 norm; the source method string is retained in JSONB.
    normalization_declared: Mapped[float] = mapped_column(nullable=False)
    normalization_observed_min: Mapped[float] = mapped_column(nullable=False)
    normalization_observed_max: Mapped[float] = mapped_column(nullable=False)
    normalization_tolerance: Mapped[float] = mapped_column(nullable=False)
    chunk_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    vector_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_model_revision: Mapped[str | None] = mapped_column(Text)
    embedding_manifest: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )


class Paper(Base):
    """Delivered paper citation and source identity."""

    __tablename__ = "papers"
    __table_args__ = (
        UniqueConstraint("delivery_import_id", "doi"),
        Index("ix_papers_publication_year", "publication_year"),
        Index("ix_papers_journal", "journal"),
        Index("ix_papers_lower_language", text("lower(language)")),
        CheckConstraint(
            "doi = lower(doi) AND doi ~ '^10\\.[0-9]{4,9}/[^[:space:]]+$'",
            name="normalized_doi",
        ),
        CheckConstraint("xml_sha256 ~ '^[0-9a-f]{64}$'", name="xml_hash"),
        CheckConstraint(
            "title <> '' AND journal <> '' AND article_type <> '' "
            "AND source_url <> '' AND "
            "jsonb_typeof(authors) = 'array' AND authors <> '[]'::jsonb "
            "AND jsonb_typeof(subjects) = 'array'",
            name="ordered_arrays",
        ),
        CheckConstraint(
            "license <> '' AND language <> ''", name="nonempty_license_language"
        ),
        CheckConstraint("publication_year > 0", name="positive_year"),
        ForeignKeyConstraint(
            ["delivery_import_id"], ["delivery_imports.id"], ondelete="CASCADE"
        ),
    )

    doi: Mapped[str] = mapped_column(Text, primary_key=True)
    delivery_import_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    authors: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    journal: Mapped[str] = mapped_column(Text, nullable=False)
    publication_date: Mapped[str] = mapped_column(Text, nullable=False)
    publication_year: Mapped[int] = mapped_column(Integer, nullable=False)
    article_type: Mapped[str] = mapped_column(Text, nullable=False)
    subjects: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    license: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_at: Mapped[str] = mapped_column(Text, nullable=False)
    xml_sha256: Mapped[str] = mapped_column(String(64), nullable=False)


class Section(Base):
    """DOI-bound source section hierarchy and locator."""

    __tablename__ = "sections"
    __table_args__ = (
        ForeignKeyConstraint(
            ["delivery_import_id", "doi"],
            ["papers.delivery_import_id", "papers.doi"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["delivery_import_id", "doi", "parent_section_id"],
            [
                "sections.delivery_import_id",
                "sections.doi",
                "sections.section_id",
            ],
            deferrable=True,
            initially="DEFERRED",
        ),
        CheckConstraint(
            "jsonb_typeof(section_path) = 'array' "
            "AND section_path <> '[]'::jsonb",
            name="section_path",
        ),
        CheckConstraint(
            "title <> '' AND section_id <> '' AND source_locator <> '' "
            "AND normalized_type IN ('abstract', 'introduction', 'methods', "
            "'results', 'results_discussion', 'discussion', "
            "'conclusions', 'other')",
            name="required_values_and_type",
        ),
        CheckConstraint(
            "xml_sha256 ~ '^[0-9a-f]{64}$' AND depth > 0 "
            "AND paragraph_count >= 0",
            name="valid_section",
        ),
        UniqueConstraint("delivery_import_id", "doi", "section_id"),
        Index("ix_sections_import_doi", "delivery_import_id", "doi"),
        Index(
            "ix_sections_import_doi_parent",
            "delivery_import_id",
            "doi",
            "parent_section_id",
        ),
        Index("ix_sections_doi", "doi"),
        Index("ix_sections_parent", "parent_section_id"),
        Index("ix_sections_normalized_type", "normalized_type"),
    )

    section_id: Mapped[str] = mapped_column(Text, primary_key=True)
    delivery_import_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    doi: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    xml_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    section_path: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    original_heading: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_locator: Mapped[str] = mapped_column(Text, nullable=False)
    depth: Mapped[int] = mapped_column(Integer, nullable=False)
    paragraph_count: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_section_id: Mapped[str | None] = mapped_column(Text)


class Chunk(Base):
    """Exact scientific evidence text and deterministic source metadata."""

    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint("chunk_id", "delivery_import_id"),
        ForeignKeyConstraint(
            ["delivery_import_id", "doi"],
            ["papers.delivery_import_id", "papers.doi"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["delivery_import_id", "doi", "section_id"],
            [
                "sections.delivery_import_id",
                "sections.doi",
                "sections.section_id",
            ],
            ondelete="CASCADE",
        ),
        UniqueConstraint("section_id", "ordinal"),
        CheckConstraint(
            "chunk_id ~ '^[0-9a-f]{64}$' AND text_sha256 ~ '^[0-9a-f]{64}$'",
            name="hashes",
        ),
        CheckConstraint(
            "ordinal > 0 AND content_token_count > 0 "
            "AND chunk_kind = 'paragraph'",
            name="positive_counts",
        ),
        CheckConstraint(
            "jsonb_typeof(section_path) = 'array' "
            "AND section_path <> '[]'::jsonb "
            "AND jsonb_typeof(spans) = 'array' AND spans <> '[]'::jsonb "
            "AND jsonb_typeof(omissions) = 'array' "
            "AND normalized_type IN ('abstract', 'introduction', 'methods', "
            "'results', 'results_discussion', 'discussion', "
            "'conclusions', 'other')",
            name="ordered_arrays",
        ),
        CheckConstraint("text <> ''", name="nonempty_text"),
        Index("ix_chunks_import_doi", "delivery_import_id", "doi"),
        Index(
            "ix_chunks_import_doi_section",
            "delivery_import_id",
            "doi",
            "section_id",
        ),
        Index("ix_chunks_doi", "doi"),
        Index("ix_chunks_section", "section_id"),
        Index("ix_chunks_normalized_type", "normalized_type"),
        Index("ix_chunks_delivery_import_id", "delivery_import_id"),
    )

    chunk_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    delivery_import_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    doi: Mapped[str] = mapped_column(Text, nullable=False)
    section_id: Mapped[str] = mapped_column(Text, nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_kind: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_type: Mapped[str] = mapped_column(Text, nullable=False)
    section_path: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    text_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    spans: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    source_locator: Mapped[str] = mapped_column(Text, nullable=False)
    content_token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    hard_split: Mapped[bool] = mapped_column(Boolean, nullable=False)
    omissions: Mapped[list[Any]] = mapped_column(JSONB, nullable=False)
    chunking_version: Mapped[str] = mapped_column(Text, nullable=False)
    token_counter_version: Mapped[str] = mapped_column(Text, nullable=False)
    template_version: Mapped[str] = mapped_column(Text, nullable=False)


class ChunkEmbedding(Base):
    """One fixed-dimension vector per embedding set and chunk."""

    __tablename__ = "chunk_embeddings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["embedding_set_id", "delivery_import_id"],
            ["embedding_sets.id", "embedding_sets.delivery_import_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["chunk_id", "delivery_import_id"],
            ["chunks.chunk_id", "chunks.delivery_import_id"],
            ondelete="CASCADE",
        ),
        CheckConstraint("input_sha256 ~ '^[0-9a-f]{64}$'", name="input_hash"),
        Index("ix_chunk_embeddings_delivery_import_id", "delivery_import_id"),
        Index(
            "ix_chunk_embeddings_embedding_set_import",
            "embedding_set_id",
            "delivery_import_id",
        ),
        Index(
            "ix_chunk_embeddings_chunk_import", "chunk_id", "delivery_import_id"
        ),
    )

    embedding_set_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chunk_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    delivery_import_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    input_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[Any] = mapped_column(Vector(1536), nullable=False)
