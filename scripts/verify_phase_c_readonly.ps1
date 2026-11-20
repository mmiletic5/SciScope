$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$pythonPath = Join-Path $repositoryRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Repository-local Python was not found."
}

Push-Location $repositoryRoot
try {
    @'
from pathlib import Path
import os
import re
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


def main() -> int:
    """Verify test database identity and active pilot counts read-only."""
    url = os.environ.get("SCISCOPE_TEST_DATABASE_URL")
    if not url:
        for raw_line in Path(".env").read_text(encoding="utf-8").splitlines():
            match = re.match(r"^\s*SCISCOPE_TEST_DATABASE_URL\s*=(.*)$", raw_line)
            if match:
                url = match.group(1).strip().strip('"').strip("'")
                break
    if not url or make_url(url).database != "sciscope_test_005":
        print("FAIL target database preflight")
        return 1

    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            with connection.begin():
                connection.execute(text("SET TRANSACTION READ ONLY"))
                identity = connection.execute(
                    text(
                        "SELECT current_database(), current_user, "
                        "current_setting('server_version_num')"
                    )
                ).one()
                extension = connection.execute(
                    text("SELECT extversion FROM pg_extension WHERE extname='vector'")
                ).scalar_one_or_none()
                revision = connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one_or_none()
                active_id = connection.execute(
                    text("SELECT id FROM delivery_imports WHERE is_active")
                ).scalar_one_or_none()
                counts = connection.execute(
                    text(
                        "SELECT "
                        "(SELECT count(*) FROM papers WHERE delivery_import_id=:id), "
                        "(SELECT count(*) FROM sections WHERE delivery_import_id=:id), "
                        "(SELECT count(*) FROM chunks WHERE delivery_import_id=:id), "
                        "(SELECT count(*) FROM chunk_embeddings WHERE delivery_import_id=:id)"
                    ),
                    {"id": active_id},
                ).one() if active_id is not None else (0, 0, 0, 0)
                ok = (
                    identity[0] == "sciscope_test_005"
                    and identity[1] == "sciscope"
                    and str(identity[2]).startswith("17")
                    and extension == "0.8.7"
                    and revision == "f005_pgvector_foundation"
                    and active_id is not None
                    and tuple(counts) == (17, 319, 728, 728)
                )
                if not ok:
                    print("FAIL read-only database identity or pilot counts")
                    return 1
                print("PASS read-only identity: sciscope_test_005 / sciscope / PostgreSQL 17 / pgvector 0.8.7")
                print("PASS schema revision: f005_pgvector_foundation")
                print("PASS active pilot counts: papers=17 sections=319 chunks=728 embeddings=728")
                print("RESULT PASS 3/3")
                return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
'@ | & $pythonPath -
    if ($LASTEXITCODE -ne 0) {
        throw "Phase C read-only verification failed with exit code $LASTEXITCODE."
    }
} finally {
    Pop-Location
}
