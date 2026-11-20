"""Atomic PostgreSQL snapshot import, compare-and-swap, and verification."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from itertools import batched
from typing import Literal, cast

from sqlalchemy import Connection, Engine, delete, insert, select, text, update
from sqlalchemy.exc import SQLAlchemyError

from sciscope.database.models import Base
from sciscope.ingestion.contract import (
    ImportMode,
    ImportRequest,
    ImportResult,
)
from sciscope.ingestion.errors import ImportErrorCode, SnapshotImportError
from sciscope.ingestion.validate import ValidatedSnapshot, validate_snapshot
from sciscope.ingestion.vectors import iter_vector_rows

_LOCK_KEYS = (1396918611, 1229803604)
_PAPERS = Base.metadata.tables["papers"]
_SECTIONS = Base.metadata.tables["sections"]
_CHUNKS = Base.metadata.tables["chunks"]
_EMBEDDINGS = Base.metadata.tables["chunk_embeddings"]
_IMPORTS = Base.metadata.tables["delivery_imports"]
_SETS = Base.metadata.tables["embedding_sets"]
_Record = Mapping[str, object]
_Operation = Literal["initialize", "replace", "unchanged"]
_Outcome = Literal["imported", "replaced", "unchanged"]


class SnapshotImporter:
    """Import validated snapshots with one transaction and advisory lock."""

    def __init__(
        self,
        bind: Engine | Connection,
        *,
        failure_hook: Callable[[str], None] | None = None,
    ) -> None:
        """Create an importer using an engine or caller-owned connection.

        A caller-owned transaction is joined by a savepoint, allowing real
        database tests to roll back the complete operation at fixture teardown.
        """
        self._bind = bind
        self._failure_hook = failure_hook

    def import_snapshot(self, request: ImportRequest) -> ImportResult:
        """Validate and atomically initialize, replace, or reuse a snapshot."""
        snapshot = validate_snapshot(request)
        self._validate_request(request)
        if isinstance(self._bind, Engine):
            try:
                connection = self._bind.connect()
            except SQLAlchemyError:
                raise SnapshotImportError(
                    ImportErrorCode.DATABASE_UNAVAILABLE
                ) from None
            with connection:
                try:
                    with connection.begin():
                        return self._import_in_transaction(
                            connection, request, snapshot
                        )
                except SnapshotImportError:
                    raise
                except SQLAlchemyError:
                    raise SnapshotImportError(
                        ImportErrorCode.IMPORT_TRANSACTION_FAILED
                    ) from None
        connection = self._bind
        transaction = (
            connection.begin_nested()
            if connection.in_transaction()
            else connection.begin()
        )
        try:
            with transaction:
                return self._import_in_transaction(
                    connection, request, snapshot
                )
        except SnapshotImportError:
            raise
        except SQLAlchemyError:
            raise SnapshotImportError(
                ImportErrorCode.IMPORT_TRANSACTION_FAILED
            ) from None

    def _import_in_transaction(
        self,
        connection: Connection,
        request: ImportRequest,
        snapshot: ValidatedSnapshot,
    ) -> ImportResult:
        """Apply lock, state checks, load, verify, pruning, and activation."""
        lock_acquired = connection.execute(
            text("SELECT pg_try_advisory_xact_lock(:key1, :key2)"),
            {"key1": _LOCK_KEYS[0], "key2": _LOCK_KEYS[1]},
        ).scalar_one()
        if not lock_acquired:
            raise SnapshotImportError(ImportErrorCode.IMPORT_IN_PROGRESS)
        active = connection.execute(
            select(_IMPORTS.c.id, _IMPORTS.c.delivery_digest).where(
                _IMPORTS.c.is_active.is_(True)
            )
        ).one_or_none()
        active_digest = (
            cast(str, active.delivery_digest) if active is not None else None
        )
        operation = _determine_operation(
            request.mode,
            snapshot.delivery_digest,
            request.expected_active_digest,
            active_digest,
        )
        if operation == "unchanged":
            assert active is not None
            return self._result(
                connection,
                active.id,
                snapshot.delivery_digest,
                "unchanged",
                active_digest,
            )
        set_values = _embedding_set_values(snapshot)
        import_values = _import_values(snapshot)
        import_id = connection.execute(
            insert(_IMPORTS).values(**import_values).returning(_IMPORTS.c.id)
        ).scalar_one()
        self._fail("after_audit")
        connection.execute(
            insert(_SETS).values(**set_values, delivery_import_id=import_id)
        )
        if active is not None:
            # Feature 005 declares global entity primary/unique keys. Replacing
            # overlapping DOIs and chunk IDs therefore requires pruning inside
            # this transaction before inserting the new rows. MVCC still keeps
            # the previously committed snapshot visible until commit, and any
            # failure restores its rows through rollback.
            self._prune_old_corpus(connection, cast(int, active.id))
            self._fail("after_prune")
        connection.execute(
            insert(_PAPERS),
            [_paper_row(row, import_id) for row in snapshot.papers],
        )
        self._fail("after_papers")
        connection.execute(
            insert(_SECTIONS),
            [_section_row(row, import_id) for row in snapshot.sections],
        )
        self._fail("after_sections")
        connection.execute(
            insert(_CHUNKS),
            [_chunk_row(row, import_id) for row in snapshot.chunks],
        )
        self._fail("after_chunks")
        embedding_set_id = connection.execute(
            select(_SETS.c.id).where(_SETS.c.delivery_import_id == import_id)
        ).scalar_one()
        files = _mapping(snapshot.delivery_manifest["files"])
        vector_descriptor = _mapping(files["vectors.f32"])
        vector_rows = (
            {
                "embedding_set_id": embedding_set_id,
                "delivery_import_id": import_id,
                "chunk_id": chunk_id,
                "input_sha256": input_sha256,
                "embedding": vector,
            }
            for chunk_id, input_sha256, vector in iter_vector_rows(
                request.package_dir / "vectors.f32",
                snapshot.entries,
                dimensions=snapshot.dimensions,
                expected_sha256=cast(str, vector_descriptor["sha256"]),
            )
        )
        for batch in batched(vector_rows, 32):
            connection.execute(insert(_EMBEDDINGS), list(batch))
        self._fail("after_vectors")
        counts = _verify_import(connection, import_id, snapshot)
        self._fail("after_verify")
        previous_digest: str | None = None
        outcome: _Outcome = "imported"
        if active is not None:
            previous_digest = cast(str, active.delivery_digest)
            outcome = "replaced"
            connection.execute(
                update(_IMPORTS)
                .where(_IMPORTS.c.id == active.id)
                .values(is_active=False)
            )
        connection.execute(
            update(_IMPORTS)
            .where(_IMPORTS.c.id == import_id)
            .values(is_active=True)
        )
        self._fail("before_commit")
        return ImportResult(
            cast(int, import_id),
            snapshot.delivery_digest,
            outcome,
            previous_digest,
            counts["papers"],
            counts["sections"],
            counts["chunks"],
            counts["vectors"],
        )

    def _prune_old_corpus(self, connection: Connection, import_id: int) -> None:
        """Remove old corpus rows while retaining successful audit metadata."""
        connection.execute(
            delete(_EMBEDDINGS).where(
                _EMBEDDINGS.c.delivery_import_id == import_id
            )
        )
        connection.execute(
            delete(_CHUNKS).where(_CHUNKS.c.delivery_import_id == import_id)
        )
        connection.execute(
            delete(_SECTIONS).where(_SECTIONS.c.delivery_import_id == import_id)
        )
        connection.execute(
            delete(_PAPERS).where(_PAPERS.c.delivery_import_id == import_id)
        )

    def _validate_request(self, request: ImportRequest) -> None:
        """Reject malformed operation intent before acquiring database state."""
        if not isinstance(request.mode, ImportMode):
            raise SnapshotImportError(ImportErrorCode.ACTIVE_CORPUS_CONFLICT)
        expected = request.expected_active_digest
        if request.mode is ImportMode.INITIALIZE and expected is not None:
            raise SnapshotImportError(ImportErrorCode.ACTIVE_CORPUS_CONFLICT)
        if (
            request.mode is ImportMode.REPLACE
            and expected is not None
            and (
                len(expected) != 71
                or not expected.startswith("sha256:")
                or any(char not in "0123456789abcdef" for char in expected[7:])
            )
        ):
            raise SnapshotImportError(ImportErrorCode.ACTIVE_CORPUS_CONFLICT)

    def _fail(self, stage: str) -> None:
        """Run a deterministic test hook without leaking its exception text."""
        if self._failure_hook is None:
            return
        try:
            self._failure_hook(stage)
        except Exception:
            raise SnapshotImportError(
                ImportErrorCode.IMPORT_TRANSACTION_FAILED
            ) from None

    def _result(
        self,
        connection: Connection,
        import_id: int,
        digest: str,
        outcome: _Outcome,
        previous_digest: str | None,
    ) -> ImportResult:
        """Return counts from the existing active import without mutation."""
        counts = _verify_counts(connection, import_id)
        return ImportResult(
            import_id,
            digest,
            outcome,
            previous_digest,
            counts["papers"],
            counts["sections"],
            counts["chunks"],
            counts["vectors"],
        )


def _import_values(snapshot: ValidatedSnapshot) -> dict[str, object]:
    """Prepare immutable audit metadata without paths or local environment."""
    delivery = snapshot.delivery_manifest
    counts = _mapping(delivery["counts"])
    return {
        "delivery_digest": snapshot.delivery_digest,
        "schema_version": delivery["schema_version"],
        "contract_version": delivery["contract_version"],
        "paper_count": counts["papers"],
        "section_count": counts["sections"],
        "chunk_count": counts["chunks"],
        "vector_count": snapshot.embedding_manifest["vector_count"],
        "processing_versions": delivery["processing_versions"],
        "delivery_manifest": delivery,
        "is_active": False,
    }


def _determine_operation(
    mode: ImportMode,
    incoming_digest: str,
    expected_active_digest: str | None,
    active_digest: str | None,
) -> _Operation:
    """Apply the importer.v1 state table after acquiring the advisory lock."""
    if active_digest == incoming_digest:
        return "unchanged"
    if active_digest is None:
        if mode is ImportMode.INITIALIZE:
            return "initialize"
        raise SnapshotImportError(ImportErrorCode.ACTIVE_CORPUS_CONFLICT)
    if mode is ImportMode.INITIALIZE:
        raise SnapshotImportError(ImportErrorCode.REPLACEMENT_REQUIRED)
    if expected_active_digest != active_digest:
        raise SnapshotImportError(ImportErrorCode.ACTIVE_CORPUS_CONFLICT)
    return "replace"


def _embedding_set_values(snapshot: ValidatedSnapshot) -> dict[str, object]:
    """Prepare model metadata while preserving the complete source manifest."""
    delivery_set = _mapping(snapshot.delivery_manifest["embedding_set"])
    normalization = _mapping(delivery_set["normalization"])
    declared_method = normalization["declared"]
    if declared_method != "l2":
        raise SnapshotImportError(
            ImportErrorCode.EMBEDDING_CONFIGURATION_MISMATCH
        )
    return {
        "provider": delivery_set["provider"],
        "model": delivery_set["model"],
        "dimensions": delivery_set["dimensions"],
        "dtype": delivery_set["dtype"],
        "passage_prefix": delivery_set["passage_prefix"],
        "query_prefix": delivery_set["query_prefix"],
        # The accepted Float column stores the numeric target norm. The source
        # method string "l2" remains unchanged in embedding_manifest JSONB.
        "normalization_declared": 1.0,
        "normalization_observed_min": normalization["observed_norm_min"],
        "normalization_observed_max": normalization["observed_norm_max"],
        "normalization_tolerance": normalization["tolerance"],
        "chunk_sha256": delivery_set["chunks_sha256"],
        "vector_sha256": delivery_set["vectors_sha256"],
        "embedding_model_revision": delivery_set["embedding_model_revision"],
        "embedding_manifest": snapshot.embedding_manifest,
    }


def _paper_row(record: _Record, import_id: int) -> dict[str, object]:
    """Map an unchanged delivery paper into its relational row."""
    return {
        **record,
        "delivery_import_id": import_id,
    }


def _section_row(record: _Record, import_id: int) -> dict[str, object]:
    """Map a delivery section without changing source values."""
    return {**record, "delivery_import_id": import_id}


def _chunk_row(record: _Record, import_id: int) -> dict[str, object]:
    """Map delivery-specific field names to the approved database contract."""
    row = dict(record)
    row["delivery_import_id"] = import_id
    row["content_token_count"] = row.pop("content_tokens")
    row["omissions"] = row.pop("omitted")
    row["token_counter_version"] = row.pop("token_counter_id")
    return row


def _verify_import(
    connection: Connection,
    import_id: int,
    snapshot: ValidatedSnapshot,
) -> dict[str, int]:
    """Check source sets, ownership, dimensions, and orphan counts."""
    counts = _verify_counts(connection, import_id)
    expected_counts = {
        "papers": len(snapshot.papers),
        "sections": len(snapshot.sections),
        "chunks": len(snapshot.chunks),
        "vectors": len(snapshot.entries),
    }
    if counts != expected_counts:
        raise SnapshotImportError(ImportErrorCode.IMPORT_VERIFICATION_FAILED)
    identity_sources = (
        (_PAPERS, _PAPERS.c.doi, {str(row["doi"]) for row in snapshot.papers}),
        (
            _SECTIONS,
            _SECTIONS.c.section_id,
            {str(row["section_id"]) for row in snapshot.sections},
        ),
        (
            _CHUNKS,
            _CHUNKS.c.chunk_id,
            {str(row["chunk_id"]) for row in snapshot.chunks},
        ),
        (
            _EMBEDDINGS,
            _EMBEDDINGS.c.chunk_id,
            {str(row["chunk_id"]) for row in snapshot.entries},
        ),
    )
    for table, identity_column, expected_ids in identity_sources:
        actual_ids = set(
            connection.execute(
                select(identity_column).where(
                    table.c.delivery_import_id == import_id
                )
            ).scalars()
        )
        if actual_ids != expected_ids:
            raise SnapshotImportError(
                ImportErrorCode.IMPORT_VERIFICATION_FAILED
            )
    actual_embeddings: dict[str, str] = {
        cast(str, chunk_id): cast(str, input_sha256)
        for chunk_id, input_sha256 in connection.execute(
            select(
                _EMBEDDINGS.c.chunk_id,
                _EMBEDDINGS.c.input_sha256,
            ).where(_EMBEDDINGS.c.delivery_import_id == import_id)
        ).all()
    }
    expected_embeddings = {
        str(row["chunk_id"]): str(row["input_sha256"])
        for row in snapshot.entries
    }
    if actual_embeddings != expected_embeddings:
        raise SnapshotImportError(ImportErrorCode.IMPORT_VERIFICATION_FAILED)
    dimensions = connection.execute(
        select(text("count(*)"))
        .select_from(_EMBEDDINGS)
        .where(
            _EMBEDDINGS.c.delivery_import_id == import_id,
            text("vector_dims(embedding) <> 1536"),
        )
    ).scalar_one()
    if dimensions:
        raise SnapshotImportError(ImportErrorCode.IMPORT_VERIFICATION_FAILED)
    orphan_count = connection.execute(
        text(
            "SELECT "
            "(SELECT count(*) FROM sections s LEFT JOIN papers p "
            "ON p.delivery_import_id=s.delivery_import_id AND p.doi=s.doi "
            "WHERE s.delivery_import_id=:id AND p.doi IS NULL) + "
            "(SELECT count(*) FROM chunks c LEFT JOIN papers p "
            "ON p.delivery_import_id=c.delivery_import_id AND p.doi=c.doi "
            "LEFT JOIN sections s "
            "ON s.delivery_import_id=c.delivery_import_id "
            "AND s.doi=c.doi AND s.section_id=c.section_id "
            "WHERE c.delivery_import_id=:id "
            "AND (p.doi IS NULL OR s.section_id IS NULL)) + "
            "(SELECT count(*) FROM chunk_embeddings e LEFT JOIN chunks c "
            "ON c.delivery_import_id=e.delivery_import_id "
            "AND c.chunk_id=e.chunk_id WHERE e.delivery_import_id=:id "
            "AND c.chunk_id IS NULL)"
        ),
        {"id": import_id},
    ).scalar_one()
    if orphan_count:
        raise SnapshotImportError(ImportErrorCode.IMPORT_VERIFICATION_FAILED)
    return counts


def _verify_counts(connection: Connection, import_id: int) -> dict[str, int]:
    """Count the rows owned by one import ID."""
    tables = {
        "papers": _PAPERS,
        "sections": _SECTIONS,
        "chunks": _CHUNKS,
        "vectors": _EMBEDDINGS,
    }
    return {
        name: cast(
            int,
            connection.execute(
                select(text("count(*)"))
                .select_from(table)
                .where(table.c.delivery_import_id == import_id)
            ).scalar_one(),
        )
        for name, table in tables.items()
    }


def _mapping(value: object) -> Mapping[str, object]:
    """Narrow a previously validated mapping."""
    if not isinstance(value, Mapping):
        raise SnapshotImportError(ImportErrorCode.DELIVERY_INVALID)
    return value
