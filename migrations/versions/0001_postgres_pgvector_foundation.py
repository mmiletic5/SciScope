"""Create the reviewed Feature 005 PostgreSQL schema."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "f005_pgvector_foundation"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the extension and six feature-owned tables."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    extension_version = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
            )
        )
        .scalar_one()
    )
    if extension_version != "0.8.7":
        raise RuntimeError("SciScope requires pgvector extension version 0.8.7")

    op.create_table(
        "delivery_imports",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("delivery_digest", sa.String(length=71), nullable=False),
        sa.Column("schema_version", sa.Text(), nullable=False),
        sa.Column("contract_version", sa.Text(), nullable=False),
        sa.Column("paper_count", sa.Integer(), nullable=False),
        sa.Column("section_count", sa.Integer(), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False),
        sa.Column("vector_count", sa.Integer(), nullable=False),
        sa.Column("processing_versions", postgresql.JSONB(), nullable=False),
        sa.Column("delivery_manifest", postgresql.JSONB(), nullable=False),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "delivery_digest ~ '^sha256:[0-9a-f]{64}$'",
            name="ck_delivery_imports_digest",
        ),
        sa.CheckConstraint(
            "schema_version <> '' AND contract_version <> '' "
            "AND jsonb_typeof(processing_versions) = 'object' "
            "AND jsonb_typeof(delivery_manifest) = 'object'",
            name="ck_delivery_imports_json_objects",
        ),
        sa.CheckConstraint(
            "paper_count >= 0 AND section_count >= 0 "
            "AND chunk_count >= 0 AND vector_count >= 0",
            name="ck_delivery_imports_nonnegative_counts",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_delivery_imports"),
    )
    op.create_index(
        "uq_delivery_imports_one_active",
        "delivery_imports",
        ["is_active"],
        unique=True,
        postgresql_where=sa.text("is_active"),
    )

    op.create_table(
        "embedding_sets",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("delivery_import_id", sa.BigInteger(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("dimensions", sa.Integer(), nullable=False),
        sa.Column("dtype", sa.Text(), nullable=False),
        sa.Column(
            "passage_prefix", sa.Text(), server_default="", nullable=False
        ),
        sa.Column("query_prefix", sa.Text(), server_default="", nullable=False),
        sa.Column("normalization_declared", sa.Float(), nullable=False),
        sa.Column("normalization_observed_min", sa.Float(), nullable=False),
        sa.Column("normalization_observed_max", sa.Float(), nullable=False),
        sa.Column("normalization_tolerance", sa.Float(), nullable=False),
        sa.Column("chunk_sha256", sa.String(length=64), nullable=False),
        sa.Column("vector_sha256", sa.String(length=64), nullable=False),
        sa.Column("embedding_model_revision", sa.Text(), nullable=True),
        sa.Column("embedding_manifest", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint(
            "provider = 'openai' AND model = 'text-embedding-3-small' "
            "AND dimensions = 1536 AND dtype = 'float32-le' "
            "AND passage_prefix = '' AND query_prefix = ''",
            name="ck_embedding_sets_fixed_model",
        ),
        sa.CheckConstraint(
            "normalization_tolerance > 0",
            name="ck_embedding_sets_positive_tolerance",
        ),
        sa.CheckConstraint(
            "chunk_sha256 ~ '^[0-9a-f]{64}$' "
            "AND vector_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_embedding_sets_hashes",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(embedding_manifest) = 'object'",
            name="ck_embedding_sets_manifest_object",
        ),
        sa.ForeignKeyConstraint(
            ["delivery_import_id"],
            ["delivery_imports.id"],
            name="fk_embedding_sets_delivery_import_id_delivery_imports",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_embedding_sets"),
        sa.UniqueConstraint(
            "delivery_import_id", name="uq_embedding_sets_delivery_import_id"
        ),
        sa.UniqueConstraint(
            "id",
            "delivery_import_id",
            name="uq_embedding_sets_id_delivery_import_id",
        ),
    )

    op.create_table(
        "papers",
        sa.Column("doi", sa.Text(), nullable=False),
        sa.Column("delivery_import_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("authors", postgresql.JSONB(), nullable=False),
        sa.Column("journal", sa.Text(), nullable=False),
        sa.Column("publication_date", sa.Text(), nullable=False),
        sa.Column("publication_year", sa.Integer(), nullable=False),
        sa.Column("article_type", sa.Text(), nullable=False),
        sa.Column("subjects", postgresql.JSONB(), nullable=False),
        sa.Column("license", sa.Text(), nullable=False),
        sa.Column("language", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("retrieved_at", sa.Text(), nullable=False),
        sa.Column("xml_sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "doi = lower(doi) AND doi ~ '^10\\.[0-9]{4,9}/[^[:space:]]+$'",
            name="ck_papers_normalized_doi",
        ),
        sa.CheckConstraint(
            "xml_sha256 ~ '^[0-9a-f]{64}$'", name="ck_papers_xml_hash"
        ),
        sa.CheckConstraint(
            "title <> '' AND journal <> '' AND article_type <> '' "
            "AND source_url <> '' AND "
            "jsonb_typeof(authors) = 'array' AND authors <> '[]'::jsonb "
            "AND jsonb_typeof(subjects) = 'array'",
            name="ck_papers_ordered_arrays",
        ),
        sa.CheckConstraint(
            "license <> '' AND language <> ''",
            name="ck_papers_nonempty_license_language",
        ),
        sa.CheckConstraint(
            "publication_year > 0", name="ck_papers_positive_year"
        ),
        sa.ForeignKeyConstraint(
            ["delivery_import_id"],
            ["delivery_imports.id"],
            name="fk_papers_delivery_import_id_delivery_imports",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("doi", name="pk_papers"),
        sa.UniqueConstraint(
            "delivery_import_id", "doi", name="uq_papers_delivery_import_id_doi"
        ),
    )
    op.create_index(
        "ix_papers_publication_year", "papers", ["publication_year"]
    )
    op.create_index("ix_papers_journal", "papers", ["journal"])
    op.create_index(
        "ix_papers_lower_language", "papers", [sa.text("lower(language)")]
    )

    op.create_table(
        "sections",
        sa.Column("section_id", sa.Text(), nullable=False),
        sa.Column("delivery_import_id", sa.BigInteger(), nullable=False),
        sa.Column("doi", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("xml_sha256", sa.String(length=64), nullable=False),
        sa.Column("section_path", postgresql.JSONB(), nullable=False),
        sa.Column("original_heading", sa.Text(), nullable=False),
        sa.Column("normalized_type", sa.Text(), nullable=False),
        sa.Column("source_locator", sa.Text(), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("paragraph_count", sa.Integer(), nullable=False),
        sa.Column("parent_section_id", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "jsonb_typeof(section_path) = 'array' "
            "AND section_path <> '[]'::jsonb",
            name="ck_sections_section_path",
        ),
        sa.CheckConstraint(
            "title <> '' AND section_id <> '' AND source_locator <> '' "
            "AND normalized_type IN ('abstract', 'introduction', 'methods', "
            "'results', 'results_discussion', 'discussion', "
            "'conclusions', 'other')",
            name="ck_sections_required_values_and_type",
        ),
        sa.CheckConstraint(
            "xml_sha256 ~ '^[0-9a-f]{64}$' AND depth > 0 "
            "AND paragraph_count >= 0",
            name="ck_sections_valid_section",
        ),
        sa.ForeignKeyConstraint(
            ["delivery_import_id", "doi"],
            ["papers.delivery_import_id", "papers.doi"],
            name="fk_sections_delivery_import_id_papers",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["delivery_import_id", "doi", "parent_section_id"],
            [
                "sections.delivery_import_id",
                "sections.doi",
                "sections.section_id",
            ],
            name="fk_sections_delivery_import_id_sections",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.PrimaryKeyConstraint("section_id", name="pk_sections"),
        sa.UniqueConstraint(
            "delivery_import_id",
            "doi",
            "section_id",
            name="uq_sections_delivery_import_id_doi_section_id",
        ),
    )
    op.create_index("ix_sections_doi", "sections", ["doi"])
    op.create_index("ix_sections_parent", "sections", ["parent_section_id"])
    op.create_index(
        "ix_sections_normalized_type", "sections", ["normalized_type"]
    )
    op.create_index(
        "ix_sections_import_doi", "sections", ["delivery_import_id", "doi"]
    )
    op.create_index(
        "ix_sections_import_doi_parent",
        "sections",
        ["delivery_import_id", "doi", "parent_section_id"],
    )

    op.create_table(
        "chunks",
        sa.Column("chunk_id", sa.String(length=64), nullable=False),
        sa.Column("delivery_import_id", sa.BigInteger(), nullable=False),
        sa.Column("doi", sa.Text(), nullable=False),
        sa.Column("section_id", sa.Text(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("chunk_kind", sa.Text(), nullable=False),
        sa.Column("normalized_type", sa.Text(), nullable=False),
        sa.Column("section_path", postgresql.JSONB(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("text_sha256", sa.String(length=64), nullable=False),
        sa.Column("spans", postgresql.JSONB(), nullable=False),
        sa.Column("source_locator", sa.Text(), nullable=False),
        sa.Column("content_token_count", sa.Integer(), nullable=False),
        sa.Column("hard_split", sa.Boolean(), nullable=False),
        sa.Column("omissions", postgresql.JSONB(), nullable=False),
        sa.Column("chunking_version", sa.Text(), nullable=False),
        sa.Column("token_counter_version", sa.Text(), nullable=False),
        sa.Column("template_version", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "chunk_id ~ '^[0-9a-f]{64}$' AND text_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_chunks_hashes",
        ),
        sa.CheckConstraint(
            "ordinal > 0 AND content_token_count > 0 "
            "AND chunk_kind = 'paragraph'",
            name="ck_chunks_positive_counts",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(section_path) = 'array' "
            "AND section_path <> '[]'::jsonb "
            "AND jsonb_typeof(spans) = 'array' AND spans <> '[]'::jsonb "
            "AND jsonb_typeof(omissions) = 'array' "
            "AND normalized_type IN ('abstract', 'introduction', 'methods', "
            "'results', 'results_discussion', 'discussion', "
            "'conclusions', 'other')",
            name="ck_chunks_ordered_arrays",
        ),
        sa.CheckConstraint("text <> ''", name="ck_chunks_nonempty_text"),
        sa.ForeignKeyConstraint(
            ["delivery_import_id", "doi"],
            ["papers.delivery_import_id", "papers.doi"],
            name="fk_chunks_delivery_import_id_papers",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["delivery_import_id", "doi", "section_id"],
            [
                "sections.delivery_import_id",
                "sections.doi",
                "sections.section_id",
            ],
            name="fk_chunks_delivery_import_id_sections",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("chunk_id", name="pk_chunks"),
        sa.UniqueConstraint(
            "chunk_id",
            "delivery_import_id",
            name="uq_chunks_chunk_id_delivery_import_id",
        ),
        sa.UniqueConstraint(
            "section_id", "ordinal", name="uq_chunks_section_id_ordinal"
        ),
    )
    op.create_index("ix_chunks_doi", "chunks", ["doi"])
    op.create_index("ix_chunks_section", "chunks", ["section_id"])
    op.create_index("ix_chunks_normalized_type", "chunks", ["normalized_type"])
    op.create_index(
        "ix_chunks_delivery_import_id", "chunks", ["delivery_import_id"]
    )
    op.create_index(
        "ix_chunks_import_doi", "chunks", ["delivery_import_id", "doi"]
    )
    op.create_index(
        "ix_chunks_import_doi_section",
        "chunks",
        ["delivery_import_id", "doi", "section_id"],
    )

    op.create_table(
        "chunk_embeddings",
        sa.Column("embedding_set_id", sa.BigInteger(), nullable=False),
        sa.Column("chunk_id", sa.String(length=64), nullable=False),
        sa.Column("delivery_import_id", sa.BigInteger(), nullable=False),
        sa.Column("input_sha256", sa.String(length=64), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.CheckConstraint(
            "input_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_chunk_embeddings_input_hash",
        ),
        sa.ForeignKeyConstraint(
            ["embedding_set_id", "delivery_import_id"],
            ["embedding_sets.id", "embedding_sets.delivery_import_id"],
            name="fk_chunk_embeddings_embedding_set_id_embedding_sets",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id", "delivery_import_id"],
            ["chunks.chunk_id", "chunks.delivery_import_id"],
            name="fk_chunk_embeddings_chunk_id_chunks",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "embedding_set_id", "chunk_id", name="pk_chunk_embeddings"
        ),
    )
    op.create_index(
        "ix_chunk_embeddings_delivery_import_id",
        "chunk_embeddings",
        ["delivery_import_id"],
    )
    op.create_index(
        "ix_chunk_embeddings_embedding_set_import",
        "chunk_embeddings",
        ["embedding_set_id", "delivery_import_id"],
    )
    op.create_index(
        "ix_chunk_embeddings_chunk_import",
        "chunk_embeddings",
        ["chunk_id", "delivery_import_id"],
    )


def downgrade() -> None:
    """Drop feature tables but retain the shared vector extension."""
    op.drop_table("chunk_embeddings")
    op.drop_table("chunks")
    op.drop_table("sections")
    op.drop_index("ix_papers_lower_language", table_name="papers")
    op.drop_index("ix_papers_journal", table_name="papers")
    op.drop_index("ix_papers_publication_year", table_name="papers")
    op.drop_table("papers")
    op.drop_table("embedding_sets")
    op.drop_index(
        "uq_delivery_imports_one_active", table_name="delivery_imports"
    )
    op.drop_table("delivery_imports")
