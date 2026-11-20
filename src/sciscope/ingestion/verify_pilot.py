"""Read-only reconciliation independent of importer implementation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

from sqlalchemy import Connection, Engine, Table, select, text
from sqlalchemy.engine import make_url

from sciscope.database.config import DatabaseSettings
from sciscope.database.models import Base
from sciscope.database.session import create_database_engine
from sciscope.delivery.reader import iter_jsonl
from sciscope.delivery.validate import PackageReports, validate_package
from sciscope.ingestion.contract import ImportMode, ImportRequest

_PAPERS = Base.metadata.tables["papers"]
_SECTIONS = Base.metadata.tables["sections"]
_CHUNKS = Base.metadata.tables["chunks"]
_EMBEDDINGS = Base.metadata.tables["chunk_embeddings"]
_IMPORTS = Base.metadata.tables["delivery_imports"]
_SETS = Base.metadata.tables["embedding_sets"]


@dataclass(frozen=True, slots=True)
class VerificationResult:
    """Machine-readable mismatch counts with no source values or paths."""

    papers: int
    sections: int
    chunks: int
    vectors: int
    missing_ids: int
    extra_ids: int
    provenance_mismatches: int
    dimension_mismatches: int
    vector_byte_mismatches: int
    orphans: int

    @property
    def passed(self) -> bool:
        """Return whether all independently measured checks are clean."""
        return not any(
            (
                self.missing_ids,
                self.extra_ids,
                self.provenance_mismatches,
                self.dimension_mismatches,
                self.vector_byte_mismatches,
                self.orphans,
            )
        )


def verify_snapshot(
    connection: Connection, request: ImportRequest
) -> VerificationResult:
    """Compare every source entity and vector with the active DB snapshot.

    The implementation reads through delivery readers and SQLAlchemy Core; it
    does not import or call importer validation, streaming, or service code.
    The caller supplies an already verified database connection.
    """
    validation = validate_package(
        request.package_dir,
        PackageReports(
            request.parse_report, request.chunk_report, request.embedding_report
        ),
    )
    if validation.findings:
        raise ValueError("DELIVERY_INVALID")
    raw_manifest = validation.loaded.raw_files["delivery_manifest.json"]
    digest = "sha256:" + hashlib.sha256(raw_manifest).hexdigest()
    active = connection.execute(
        select(_IMPORTS.c.id, _IMPORTS.c.delivery_digest).where(
            _IMPORTS.c.is_active.is_(True)
        )
    ).one_or_none()
    if active is None:
        raise ValueError("NO_ACTIVE_IMPORT")
    if active.delivery_digest != digest:
        raise ValueError("ACTIVE_DIGEST_MISMATCH")
    import_id = cast(int, active.id)

    source_papers = tuple(iter_jsonl(request.package_dir / "papers.jsonl"))
    source_sections = tuple(iter_jsonl(request.package_dir / "sections.jsonl"))
    source_chunks = tuple(iter_jsonl(request.package_dir / "chunks.jsonl"))
    stored_papers = _stored(connection, _PAPERS, import_id)
    stored_sections = _stored(connection, _SECTIONS, import_id)
    stored_chunks = _stored(connection, _CHUNKS, import_id)
    paper_mismatch, paper_missing, paper_extra = _compare(
        source_papers, stored_papers, "doi", {}
    )
    section_mismatch, section_missing, section_extra = _compare(
        source_sections,
        stored_sections,
        "section_id",
        {"delivery_import_id": None},
    )
    chunk_map = {
        "xml_sha256": None,
        "content_tokens": "content_token_count",
        "omitted": "omissions",
        "token_counter_id": "token_counter_version",
    }
    chunk_mismatch, chunk_missing, chunk_extra = _compare(
        source_chunks, stored_chunks, "chunk_id", chunk_map
    )
    stored_paper_hashes = {
        cast(str, row["doi"]): cast(str, row["xml_sha256"])
        for row in stored_papers
    }
    chunk_xml_hash_mismatches = sum(
        row["xml_sha256"] != stored_paper_hashes.get(cast(str, row["doi"]))
        for row in source_chunks
    )
    entry_manifest_path = request.package_dir / "embedding_manifest.json"
    with entry_manifest_path.open("r", encoding="utf-8") as stream:
        embedding_manifest = json.load(stream)
    entries = embedding_manifest["entries"]
    expected_inputs = {
        entry["chunk_id"]: entry["input_sha256"] for entry in entries
    }
    stored_vectors = (
        connection.execute(
            select(
                _EMBEDDINGS.c.chunk_id,
                _EMBEDDINGS.c.input_sha256,
                _EMBEDDINGS.c.embedding,
            ).where(_EMBEDDINGS.c.delivery_import_id == import_id)
        )
        .mappings()
        .all()
    )
    actual_vectors: dict[str, Mapping[str, object]] = {
        cast(str, row["chunk_id"]): cast(Mapping[str, object], row)
        for row in stored_vectors
    }
    expected_ids = set(expected_inputs)
    actual_ids = set(actual_vectors)
    missing = (
        paper_missing
        + section_missing
        + chunk_missing
        + len(expected_ids - actual_ids)
    )
    extra = (
        paper_extra
        + section_extra
        + chunk_extra
        + len(actual_ids - expected_ids)
    )
    input_mismatches = sum(
        actual_vectors[chunk_id]["input_sha256"] != input_sha
        for chunk_id, input_sha in expected_inputs.items()
        if chunk_id in actual_vectors
    )
    dimensions_bad = connection.execute(
        select(text("count(*)"))
        .select_from(_EMBEDDINGS)
        .where(
            _EMBEDDINGS.c.delivery_import_id == import_id,
            text("vector_dims(embedding) <> 1536"),
        )
    ).scalar_one()
    vector_bytes = (request.package_dir / "vectors.f32").read_bytes()
    vector_mismatches = _compare_vector_bytes(
        entries, vector_bytes, actual_vectors
    )
    orphan_count = _orphan_count(connection, import_id)
    totals = {
        "papers": len(source_papers),
        "sections": len(source_sections),
        "chunks": len(source_chunks),
        "vectors": len(entries),
    }
    count_mismatches = sum(
        len(rows) != totals[name]
        for name, rows in (
            ("papers", stored_papers),
            ("sections", stored_sections),
            ("chunks", stored_chunks),
            ("vectors", stored_vectors),
        )
    )
    return VerificationResult(
        totals["papers"],
        totals["sections"],
        totals["chunks"],
        totals["vectors"],
        missing,
        extra,
        paper_mismatch
        + section_mismatch
        + chunk_mismatch
        + chunk_xml_hash_mismatches
        + input_mismatches
        + count_mismatches,
        int(dimensions_bad),
        vector_mismatches,
        orphan_count,
    )


def _stored(
    connection: Connection, table: Table, import_id: int
) -> list[dict[str, object]]:
    """Read an entity's complete active-import rows into ordinary mappings."""
    return [
        dict(row)
        for row in connection.execute(
            select(table).where(table.c.delivery_import_id == import_id)
        ).mappings()
    ]


def _compare(
    source: Sequence[Mapping[str, object]],
    stored: Sequence[Mapping[str, object]],
    key: str,
    renames: Mapping[str, str | None],
) -> tuple[int, int, int]:
    """Compare exact source fields and identity sets for one entity kind."""
    source_by_id = {str(row[key]): row for row in source}
    stored_by_id = {str(row[key]): row for row in stored}
    mismatches = 0
    for identifier in source_by_id.keys() & stored_by_id.keys():
        expected = source_by_id[identifier]
        actual = stored_by_id[identifier]
        for field, value in expected.items():
            column = renames.get(field, field)
            if column is None or actual.get(column) != value:
                if column is not None:
                    mismatches += 1
    return (
        mismatches,
        len(source_by_id.keys() - stored_by_id.keys()),
        len(stored_by_id.keys() - source_by_id.keys()),
    )


def _compare_vector_bytes(
    entries: Sequence[Mapping[str, object]],
    raw: bytes,
    stored: Mapping[str, Mapping[str, object]],
) -> int:
    """Repack every returned database vector as exact float32-le bytes."""
    dimensions = 1536
    row_bytes = dimensions * 4
    if len(raw) != len(entries) * row_bytes:
        return len(entries) or 1
    mismatch = 0
    for index, entry in enumerate(entries):
        chunk_id = cast(str, entry["chunk_id"])
        row = stored.get(chunk_id)
        if row is None:
            mismatch += 1
            continue
        values = cast(Sequence[float], row["embedding"])
        try:
            packed = struct.pack("<1536f", *(float(value) for value in values))
        except (OverflowError, struct.error, TypeError):
            mismatch += 1
            continue
        source = raw[index * row_bytes : (index + 1) * row_bytes]
        mismatch += packed != source
    return mismatch


def _orphan_count(connection: Connection, import_id: int) -> int:
    """Count any paper, section, chunk, embedding, or model-set orphan."""
    return cast(
        int,
        connection.execute(
            text(
                "SELECT "
                "(SELECT count(*) FROM sections s LEFT JOIN papers p "
                "ON p.delivery_import_id=s.delivery_import_id AND p.doi=s.doi "
                "WHERE s.delivery_import_id=:id AND p.doi IS NULL) + "
                "(SELECT count(*) FROM chunks c LEFT JOIN sections s "
                "ON s.delivery_import_id=c.delivery_import_id AND s.doi=c.doi "
                "AND s.section_id=c.section_id WHERE c.delivery_import_id=:id "
                "AND s.section_id IS NULL) + "
                "(SELECT count(*) FROM chunk_embeddings e LEFT JOIN chunks c "
                "ON c.delivery_import_id=e.delivery_import_id "
                "AND c.chunk_id=e.chunk_id LEFT JOIN embedding_sets es "
                "ON es.delivery_import_id=e.delivery_import_id "
                "AND es.id=e.embedding_set_id WHERE e.delivery_import_id=:id "
                "AND (c.chunk_id IS NULL OR es.id IS NULL))"
            ),
            {"id": import_id},
        ).scalar_one(),
    )


def _parser() -> argparse.ArgumentParser:
    """Build the verifier's stable command-line argument parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-dir", type=Path, required=True)
    parser.add_argument("--parse-report", type=Path, required=True)
    parser.add_argument("--chunk-report", type=Path, required=True)
    parser.add_argument("--embedding-report", type=Path, required=True)
    return parser


def main() -> int:
    """Run read-only reconciliation using DATABASE_URL without printing it."""
    args = _parser().parse_args()
    request = ImportRequest(
        args.package_dir,
        args.parse_report,
        args.chunk_report,
        args.embedding_report,
        ImportMode.INITIALIZE,
    )
    engine: Engine | None = None
    try:
        database_url = os.environ.get(
            "SCISCOPE_TEST_DATABASE_URL"
        ) or os.environ.get("DATABASE_URL", "")
        settings = DatabaseSettings.from_environment(
            {"DATABASE_URL": database_url}
        )
        if make_url(settings.url).database != "sciscope_test_005":
            raise ValueError("DATABASE_IDENTITY_MISMATCH")
        engine = create_database_engine(settings)
        with engine.connect() as connection:
            with connection.begin():
                connection.execute(text("SET TRANSACTION READ ONLY"))
                identity = connection.execute(
                    text(
                        "SELECT current_database() AS database_name, "
                        "current_user AS role_name"
                    )
                ).one()
                if (
                    identity.database_name != "sciscope_test_005"
                    or identity.role_name != "sciscope"
                ):
                    raise ValueError("DATABASE_IDENTITY_MISMATCH")
                result = verify_snapshot(connection, request)
        print(
            json.dumps(
                {
                    "status": "PASS" if result.passed else "FAIL",
                    **asdict(result),
                },
                sort_keys=True,
            )
        )
        return 0 if result.passed else 1
    except Exception as error:
        code = (
            str(error)
            if str(error)
            in {
                "DELIVERY_INVALID",
                "NO_ACTIVE_IMPORT",
                "ACTIVE_DIGEST_MISMATCH",
                "DATABASE_IDENTITY_MISMATCH",
            }
            else "VERIFICATION_FAILED"
        )
        print(json.dumps({"status": "FAIL", "code": code}, sort_keys=True))
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
