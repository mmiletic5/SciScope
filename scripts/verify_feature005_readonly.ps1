$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $repositoryRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    Write-Error "Repository Python environment was not found."
    exit 2
}

Push-Location $repositoryRoot
try {
    @'
from pathlib import Path
import sys

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url


def main() -> int:
    """Run sanitized, read-only Feature 005 verification queries."""
    environment = {}
    for raw_line in Path(".env").read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        environment[key.strip()] = value.strip().strip('"').strip("'")

    configured_url = environment.get("DATABASE_URL")
    if not configured_url:
        print("FAIL: .env does not define DATABASE_URL")
        return 1

    target_url = make_url(configured_url).set(database="sciscope_test_005")
    engine = create_engine(target_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            database, role, server = connection.execute(
                text(
                    "SELECT current_database(), current_user, "
                    "current_setting('server_version_num')"
                )
            ).one()
            vector_version = connection.execute(
                text(
                    "SELECT extversion FROM pg_extension "
                    "WHERE extname = 'vector'"
                )
            ).scalar_one_or_none()
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one_or_none()
            vector_dimension = connection.execute(
                text(
                    "SELECT atttypmod FROM pg_attribute "
                    "WHERE attrelid = 'chunk_embeddings'::regclass "
                    "AND attname = 'embedding'"
                )
            ).scalar_one_or_none()
            tables = set(inspect(connection).get_table_names(schema="public"))
            application_tables = {
                "delivery_imports",
                "embedding_sets",
                "papers",
                "sections",
                "chunks",
                "chunk_embeddings",
            }
            counts = {
                name: connection.execute(
                    text(f'SELECT count(*) FROM public."{name}"')
                ).scalar_one()
                for name in sorted(application_tables)
            }
            active_imports = connection.execute(
                text("SELECT count(*) FROM delivery_imports WHERE is_active")
            ).scalar_one()
            orphan_count = connection.execute(
                text(
                    "SELECT "
                    "(SELECT count(*) FROM sections s LEFT JOIN papers p "
                    "USING (delivery_import_id, doi) WHERE p.doi IS NULL) + "
                    "(SELECT count(*) FROM chunks c LEFT JOIN papers p "
                    "USING (delivery_import_id, doi) WHERE p.doi IS NULL) + "
                    "(SELECT count(*) FROM chunks c LEFT JOIN sections s "
                    "USING (delivery_import_id, doi, section_id) "
                    "WHERE s.section_id IS NULL) + "
                    "(SELECT count(*) FROM chunk_embeddings e "
                    "LEFT JOIN chunks c USING (chunk_id, delivery_import_id) "
                    "WHERE c.chunk_id IS NULL) + "
                    "(SELECT count(*) FROM chunk_embeddings e "
                    "LEFT JOIN embedding_sets s ON "
                    "(e.embedding_set_id, e.delivery_import_id) = "
                    "(s.id, s.delivery_import_id) WHERE s.id IS NULL)"
                )
            ).scalar_one()
            forbidden_indexes = connection.execute(
                text(
                    "SELECT count(*) FROM pg_indexes "
                    "WHERE schemaname = 'public' AND ("
                    "indexdef ILIKE '% USING hnsw %' OR "
                    "indexdef ILIKE '% USING ivfflat %' OR "
                    "indexdef ILIKE '%to_tsvector%')"
                )
            ).scalar_one()

        checks = {
            "database is sciscope_test_005": database == "sciscope_test_005",
            "role is sciscope": role == "sciscope",
            "PostgreSQL major version is 17": str(server).startswith("17"),
            "pgvector version is 0.8.7": vector_version == "0.8.7",
            "migration revision is f005_pgvector_foundation": (
                revision == "f005_pgvector_foundation"
            ),
            "six application tables plus alembic_version exist": tables
            == application_tables | {"alembic_version"},
            "embedding column dimension is 1536": vector_dimension == 1536,
            "at most one active import exists": active_imports <= 1,
            "cross-table orphan count is zero": orphan_count == 0,
            "no FTS/HNSW/IVFFlat indexes exist": forbidden_indexes == 0,
        }
        for description, passed in checks.items():
            print(f'{"PASS" if passed else "FAIL"}: {description}')
        print(f"READ-ONLY table counts: {counts}")
        return 0 if all(checks.values()) else 1
    finally:
        engine.dispose()


try:
    raise SystemExit(main())
except Exception as error:
    # Do not print exception details because driver errors can contain URLs.
    print(f"FAIL: read-only verification could not complete ({type(error).__name__})")
    raise SystemExit(1) from None
'@ | & $pythonPath -
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
finally {
    Pop-Location
}
