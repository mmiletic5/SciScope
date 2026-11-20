param()

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Feature 006 verification requires the repository .venv Python."
}

Push-Location $repoRoot
try {
    @'
from pathlib import Path
import sys

sys.path.insert(0, "src")

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from sciscope.database.config import DatabaseSettings
from sciscope.database.session import create_database_engine
from sciscope.ingestion.contract import ImportMode, ImportRequest
from sciscope.ingestion.verify_pilot import verify_snapshot


def check(name: str, passed: bool) -> None:
    """Print a fixed-name PASS/FAIL line without data or credentials."""
    print(f"{'PASS' if passed else 'FAIL'} {name}")
    if not passed:
        raise SystemExit(1)


values: dict[str, str] = {}
for line in Path(".env").read_text(encoding="utf-8").splitlines():
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        continue
    key, value = stripped.split("=", 1)
    values[key.strip()] = value.strip().strip('"').strip("'")

source_url = values.get("DATABASE_URL")
if not source_url or make_url(source_url).database != "sciscope":
    print("FAIL configured source database precondition")
    raise SystemExit(1)
target_url = make_url(source_url).set(database="sciscope_test_005")
engine = create_database_engine(
    DatabaseSettings(url=target_url.render_as_string(hide_password=False))
)

request = ImportRequest(
    Path("data/delivery/pilot"),
    Path("data/pilot/parse_report.json"),
    Path("data/pilot/chunk_report.json"),
    Path("data/pilot/embedding_report.json"),
    ImportMode.INITIALIZE,
)
expected_tables = {
    "delivery_imports",
    "embedding_sets",
    "papers",
    "sections",
    "chunks",
    "chunk_embeddings",
}

try:
    with engine.connect() as connection:
        with connection.begin():
            connection.execute(text("SET TRANSACTION READ ONLY"))
            identity = connection.execute(
                text(
                    "SELECT current_database() AS database_name, "
                    "current_user AS role_name"
                )
            ).one()
            check(
                "database and least-privilege role",
                identity.database_name == "sciscope_test_005"
                and identity.role_name == "sciscope",
            )
            print(
                f"  database={identity.database_name} role={identity.role_name}"
            )

            versions = connection.execute(
                text(
                    "SELECT current_setting('server_version_num') AS server, "
                    "(SELECT extversion FROM pg_extension "
                    "WHERE extname='vector') AS vector"
                )
            ).one()
            check(
                "PostgreSQL 17 and pgvector 0.8.7",
                str(versions.server).startswith("17")
                and versions.vector == "0.8.7",
            )

            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one_or_none()
            check("single accepted Alembic revision", revision == "f005_pgvector_foundation")

            tables = set(inspect(connection).get_table_names())
            check("six Feature 005 application tables", expected_tables <= tables)

            active = connection.execute(
                text(
                    "SELECT id, delivery_digest, paper_count, section_count, "
                    "chunk_count, vector_count FROM delivery_imports "
                    "WHERE is_active"
                )
            ).all()
            check("exactly one active import", len(active) == 1)
            current = active[0]

            counts = connection.execute(
                text(
                    "SELECT "
                    "(SELECT count(*) FROM papers WHERE delivery_import_id=:id), "
                    "(SELECT count(*) FROM sections WHERE delivery_import_id=:id), "
                    "(SELECT count(*) FROM chunks WHERE delivery_import_id=:id), "
                    "(SELECT count(*) FROM chunk_embeddings "
                    "WHERE delivery_import_id=:id)"
                ),
                {"id": current.id},
            ).one()
            check(
                "pilot record counts 17/319/728/728",
                tuple(counts) == (17, 319, 728, 728)
                and (current.paper_count, current.section_count,
                     current.chunk_count, current.vector_count)
                == (17, 319, 728, 728),
            )

            embedding_set = connection.execute(
                text(
                    "SELECT es.provider, es.model, es.dimensions, es.dtype, "
                    "es.passage_prefix, es.query_prefix, "
                    "es.normalization_declared, "
                    "es.embedding_manifest->'normalization'->>'declared' "
                    "FROM embedding_sets es WHERE es.delivery_import_id=:id"
                ),
                {"id": current.id},
            ).one_or_none()
            check(
                "fixed embedding model and separate normalization values",
                embedding_set is not None
                and tuple(embedding_set[:6])
                == ("openai", "text-embedding-3-small", 1536,
                    "float32-le", "", "")
                and embedding_set.normalization_declared == 1.0
                and embedding_set[7] == "l2",
            )

            wrong_dimensions = connection.execute(
                text(
                    "SELECT count(*) FROM chunk_embeddings "
                    "WHERE delivery_import_id=:id "
                    "AND vector_dims(embedding) <> 1536"
                ),
                {"id": current.id},
            ).scalar_one()
            check("all stored vectors have dimension 1536", wrong_dimensions == 0)

            orphans = connection.execute(
                text(
                    "SELECT "
                    "(SELECT count(*) FROM sections s LEFT JOIN papers p "
                    "ON p.delivery_import_id=s.delivery_import_id "
                    "AND p.doi=s.doi WHERE s.delivery_import_id=:id "
                    "AND p.doi IS NULL) + "
                    "(SELECT count(*) FROM chunks c LEFT JOIN papers p "
                    "ON p.delivery_import_id=c.delivery_import_id "
                    "AND p.doi=c.doi LEFT JOIN sections s "
                    "ON s.delivery_import_id=c.delivery_import_id "
                    "AND s.doi=c.doi AND s.section_id=c.section_id "
                    "WHERE c.delivery_import_id=:id "
                    "AND (p.doi IS NULL OR s.section_id IS NULL)) + "
                    "(SELECT count(*) FROM chunk_embeddings e "
                    "LEFT JOIN chunks c ON c.delivery_import_id=e.delivery_import_id "
                    "AND c.chunk_id=e.chunk_id LEFT JOIN embedding_sets es "
                    "ON es.delivery_import_id=e.delivery_import_id "
                    "AND es.id=e.embedding_set_id "
                    "WHERE e.delivery_import_id=:id "
                    "AND (c.chunk_id IS NULL OR es.id IS NULL))"
                ),
                {"id": current.id},
            ).scalar_one()
            check("zero application foreign-key orphans", orphans == 0)

            result = verify_snapshot(connection, request)
            check(
                "independent all-record and all-vector reconciliation",
                result.passed
                and (result.papers, result.sections,
                     result.chunks, result.vectors)
                == (17, 319, 728, 728),
            )
            print(
                "  mismatches="
                f"{result.missing_ids}/{result.extra_ids}/"
                f"{result.provenance_mismatches}/"
                f"{result.dimension_mismatches}/"
                f"{result.vector_byte_mismatches}/{result.orphans}"
            )
    print("RESULT PASS 10/10")
finally:
    engine.dispose()
'@ | & $python -
    if ($LASTEXITCODE -ne 0) {
        throw "Feature 006 read-only verification failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
