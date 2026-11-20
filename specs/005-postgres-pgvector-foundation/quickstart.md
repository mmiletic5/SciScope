# Native Windows Quickstart: PostgreSQL and pgvector Foundation

This is a procedure to use only after explicit authorization to install native
database software, build/install the extension, start the service, and create a
disposable test database. Routine approved non-destructive operations on
`sciscope_test_005` are covered by the standing Person 2 policy in `AGENTS.md`.
The main `sciscope` database remains protected. No Docker, WSL, Linux
containers, or Bash are used.

## Prerequisites

- Windows 10 Pro build 19045 x64, Windows PowerShell.
- Python 3.12.16 and the repository's locked uv environment.
- PostgreSQL 17 x64 Windows installer from the PostgreSQL download page's EDB
  link. The official page lists Windows Server 2019/2022 as tested and says
  comparable desktop Windows should generally work; Windows 10 build 19045 is
  not explicitly listed as tested.
- Visual Studio C++ build tools with x64 native tools, Git, and `nmake`.
- Explicit authorization before installing software, starting the service, or
  creating a database.

## Install PostgreSQL and build pgvector

Download PostgreSQL 17 from
[postgresql.org/download/windows](https://www.postgresql.org/download/windows/)
and follow its EDB Windows installer link. Record installer version and SHA256
in evidence. Include server development headers and command-line tools.

Open **x64 Native Tools Command Prompt for Visual Studio** (the upstream build
uses `cmd.exe` because `vcvars64.bat` initializes its environment). Set
`PGROOT` to the actual PostgreSQL 17 install path and run the upstream build for
the fixed pgvector tag:

```bat
set "PGROOT=C:\Program Files\PostgreSQL\17"
cd %TEMP%
git clone --branch v0.8.7 https://github.com/pgvector/pgvector.git
cd pgvector
nmake /NOLOGO /F Makefile.win
nmake /NOLOGO /F Makefile.win install
```

This source build is the researched native route. No official precompiled
Windows pgvector package was confirmed. Do not claim compatibility until this
build succeeds against the installed PostgreSQL and its extension control/SQL
files load successfully.

Start the PostgreSQL Windows service through the Windows Services UI or an
authorized PowerShell service command. Set local credentials outside Git.
Create a separately named disposable test database only after verifying its
resolved server/instance and obtaining authorization. Create the extension
in each new database using a PostgreSQL administrator account:
`CREATE EXTENSION IF NOT EXISTS vector;`. On this Windows installation the
application role `sciscope` does not have permission to create the extension.
Do not grant it SUPERUSER or extension-install privileges. Keep extension
provisioning with the administrator; grant the application role only the
database connection and schema/table permissions needed to run the application
and migrations. Confirm `SHOW server_version;` starts with `17.` and the
extension catalog reports `0.8.7` before using the least-privilege application
connection for Alembic.

## Python environment

```powershell
uv --version
uv run --locked python --version
uv run --locked python -c "import sqlalchemy, alembic, psycopg, pgvector; print(sqlalchemy.__version__, alembic.__version__, psycopg.__version__, pgvector.__version__)"
```

Use the approved package ranges in `pyproject.toml`; do not update the lock or
environment without the feature authorization governing that work.

## Migration and acceptance

Set `DATABASE_URL` in ignored `.env` using the PostgreSQL psycopg URL. Never
copy credentials into console transcripts or evidence. Set
`SCISCOPE_TEST_DATABASE_URL` only to the separately verified disposable test
database.

```powershell
uv run --env-file .env --locked alembic upgrade head
uv run --env-file .env --locked alembic upgrade head
uv run --env-file .env --locked alembic current
uv run --env-file .env --locked alembic heads
uv run --env-file .env --locked alembic check
uv run --env-file .env --locked pytest tests/database -q
uv run --env-file .env --locked pytest -q
uv run --locked ruff check . --no-cache
uv run --locked ruff format --check .
uv run --locked mypy src
git diff --check
```

The current initial revision is `f005_pgvector_foundation`. The offline test
suite guards all revision identifiers against Alembic's default 32-character
version-column limit.

Tests must use real native PostgreSQL/pgvector. Prove clean and repeated
upgrade, one head, six-table catalog, all constraints/indexes, same-import
relationships, accepted 1536 and rejected 1535/1537 dimensions, zero orphans,
secret-safe behavior, and no FTS/HNSW/IVFFlat indexes. Downgrade/re-upgrade is
allowed only in a separately authorized disposable database. Record Windows,
installer, compiler, PostgreSQL, extension, migration, and tool versions and
actual PASS/FAIL/BLOCKED/NOT RUN results. Do not report a missing native setup
as a skip or success.

Lifecycle regression was run on the dedicated `sciscope_test_005_lifecycle`
database: upgrade, downgrade to base, and re-upgrade passed. The downgrade
removed all six application tables and cleared the Alembic revision row; the
Alembic-owned `alembic_version` table remained empty, and pgvector 0.8.7
remained installed. The database is retained for independent verification.

## Independent final acceptance check

After implementation and automated verification, independently confirm the
installed Feature 005 state from a VS Code PowerShell terminal with this
read-only command:

```powershell
.\scripts\verify_feature005_readonly.ps1
```

The script reads `.env` internally, overrides only the database component to
`sciscope_test_005`, confirms the connected database and role, and issues only
read-only queries. It never prints connection details or exception messages.
Pass requires all ten checks to print `PASS`, including PostgreSQL 17, pgvector
0.8.7, revision `f005_pgvector_foundation`, the six tables plus
`alembic_version`, vector dimension 1536, no more than one active import, zero
orphans, and no FTS/HNSW/IVFFlat indexes. The current expected table counts are
one row per application table from an inactive synthetic test fixture; no pilot
delivery was imported. Any `FAIL`, script error, unexpected database, or missing
output is a failed verification and should be reported verbatim without sharing
credentials. Automated insert/rejection behavior is covered by pytest and is not
repeated by this read-only check.

For the retained lifecycle database, independently verify the post-re-upgrade
state with:

```powershell
.\scripts\verify_feature005_lifecycle_readonly.ps1
```

Pass requires all ten checks to print `PASS`, database and owner
`sciscope_test_005_lifecycle` / `sciscope`, PostgreSQL 17, pgvector 0.8.7,
revision `f005_pgvector_foundation`, the six application tables plus
`alembic_version`, vector dimension 1536, zero rows in the six corpus tables,
zero orphans, and no FTS/HNSW/IVFFlat indexes. This procedure is read-only.

## Compatibility gate

The native connection, initial and repeated migration, Alembic metadata check,
real constraint matrix, vector insertion/round-trip, dimension rejection,
catalog comparison, and no-orphan checks have been exercised on
`sciscope_test_005`; see `EVIDENCE.md` for actual results. A synthetic inactive
test import (one row in each application table) remains in that test database
from an earlier non-rollback test run; no pilot delivery has been imported.
Downgrade/re-upgrade was verified on the retained dedicated lifecycle database;
final human acceptance remains outstanding. If native compatibility fails, stop and request
approval for the smallest alternative; do not introduce Docker/WSL or alter
fixed requirements.
