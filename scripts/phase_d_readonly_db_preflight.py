"""Verify the frozen Phase D test corpus using a read-only DB transaction."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import make_url

from sciscope.database.config import DatabaseSettings
from sciscope.database.session import create_database_engine

_EXPECTED_CORPUS = "pilot17-xml-1fff1573b610"
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def derive_test_database_url(raw_url: str) -> str:
    """Require a local source URL and return only the test-database target.

    Args:
        raw_url: A URL from SCISCOPE_TEST_DATABASE_URL or the local .env.

    Returns:
        A SQLAlchemy URL targeting `sciscope_test_005`.

    Raises:
        ValueError: If the source is remote, uses an unexpected database, or
            does not use the approved local PostgreSQL endpoint.
    """
    source = make_url(raw_url)
    if (
        source.host not in _LOCAL_HOSTS
        or source.port not in (None, 5432)
        or source.database not in {"sciscope", "sciscope_test_005"}
    ):
        raise ValueError("database URL failed local target guard")
    target = source.set(database="sciscope_test_005")
    if target.database != "sciscope_test_005":
        raise ValueError("database URL failed exact test target guard")
    return target.render_as_string(hide_password=False)


def _load_source_url() -> str:
    """Read the approved URL source without printing it."""
    test_url = os.environ.get("SCISCOPE_TEST_DATABASE_URL")
    if test_url:
        return test_url
    env_path = Path(".env")
    if not env_path.is_file():
        raise ValueError("local database URL source is unavailable")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        candidate = line.strip()
        if candidate.startswith("DATABASE_URL="):
            return candidate.split("=", 1)[1].strip().strip("\"'")
    raise ValueError("local database URL source is unavailable")


def run_read_only_preflight(raw_url: str) -> dict[str, Any]:
    """Check identity, counts, and active embedding metadata read-only."""
    target_url = derive_test_database_url(raw_url)
    engine = create_database_engine(DatabaseSettings(url=target_url))
    try:
        with engine.connect() as connection:
            with connection.begin():
                connection.execute(text("SET TRANSACTION READ ONLY"))
                identity = connection.execute(
                    text(
                        "SELECT current_database(), current_user, "
                        "current_setting('server_version_num'), "
                        "current_setting('transaction_read_only')"
                    )
                ).one()
                if (
                    identity[0] != "sciscope_test_005"
                    or identity[1] != "sciscope"
                    or not str(identity[2]).startswith("17")
                    or identity[3] != "on"
                ):
                    raise ValueError("database identity/read-only check failed")
                imports = connection.execute(
                    text(
                        "SELECT id, delivery_digest, paper_count, "
                        "section_count, "
                        "chunk_count, vector_count FROM delivery_imports "
                        "WHERE is_active"
                    )
                ).all()
                if len(imports) != 1:
                    raise ValueError("active import count check failed")
                active = imports[0]
                counts = {
                    name: connection.execute(
                        text(
                            f"SELECT count(*) FROM {table} "
                            "WHERE delivery_import_id=:import_id"
                        ),
                        {"import_id": active.id},
                    ).scalar_one()
                    for name, table in (
                        ("papers", "papers"),
                        ("sections", "sections"),
                        ("chunks", "chunks"),
                        ("embeddings", "chunk_embeddings"),
                    )
                }
                if counts != {
                    "papers": 17,
                    "sections": 319,
                    "chunks": 728,
                    "embeddings": 728,
                } or (
                    active.paper_count,
                    active.section_count,
                    active.chunk_count,
                    active.vector_count,
                ) != (17, 319, 728, 728):
                    raise ValueError("active corpus row counts mismatch")
                sets = connection.execute(
                    text(
                        "SELECT id, provider, model, dimensions, dtype, "
                        "passage_prefix, query_prefix, chunk_sha256, "
                        "vector_sha256 FROM embedding_sets "
                        "WHERE delivery_import_id=:import_id"
                    ),
                    {"import_id": active.id},
                ).all()
                if len(sets) != 1:
                    raise ValueError("active embedding set count mismatch")
                embedding_set = sets[0]
                if (
                    embedding_set.provider,
                    embedding_set.model,
                    embedding_set.dimensions,
                    embedding_set.dtype,
                    embedding_set.passage_prefix,
                    embedding_set.query_prefix,
                ) != (
                    "openai",
                    "text-embedding-3-small",
                    1536,
                    "float32-le",
                    "",
                    "",
                ):
                    raise ValueError("active embedding identity mismatch")
                papers = connection.execute(
                    text(
                        "SELECT doi, xml_sha256 FROM papers "
                        "WHERE delivery_import_id=:import_id ORDER BY doi"
                    ),
                    {"import_id": active.id},
                ).all()
                material = "".join(
                    f"{paper.doi}\t{paper.xml_sha256}\n" for paper in papers
                ).encode("utf-8")
                corpus_sha256 = hashlib.sha256(material).hexdigest()
                corpus_version = f"pilot{len(papers)}-xml-{corpus_sha256[:12]}"
                if corpus_version != _EXPECTED_CORPUS:
                    raise ValueError("active corpus identity mismatch")
                delivery_root = Path("data/delivery/pilot")
                delivery_path = delivery_root / "delivery_manifest.json"
                delivery = json.loads(delivery_path.read_text(encoding="utf-8"))
                expected_delivery = (
                    "sha256:"
                    + hashlib.sha256(delivery_path.read_bytes()).hexdigest()
                )
                if active.delivery_digest != expected_delivery:
                    raise ValueError("active delivery identity mismatch")
                if (
                    embedding_set.vector_sha256
                    != delivery["files"]["vectors.f32"]["sha256"]
                    or embedding_set.chunk_sha256
                    != delivery["files"]["chunks.jsonl"]["sha256"]
                ):
                    raise ValueError("embedding payload identity mismatch")
                return {
                    "status": "PASS",
                    "database": "sciscope_test_005",
                    "role": "sciscope",
                    "postgres_major": 17,
                    "transaction_read_only": True,
                    "active_imports": 1,
                    "embedding_set_id": embedding_set.id,
                    "counts": counts,
                    "corpus_version": corpus_version,
                    "embedding_provider": embedding_set.provider,
                    "embedding_model": embedding_set.model,
                    "embedding_dimensions": embedding_set.dimensions,
                    "embedding_dtype": embedding_set.dtype,
                    "empty_prefixes": True,
                }
    finally:
        engine.dispose()


def main() -> int:
    """Run the guarded preflight and print only non-secret status fields."""
    try:
        result = run_read_only_preflight(_load_source_url())
    except Exception:
        print("DB_PREFLIGHT=FAIL; details sanitized")
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
