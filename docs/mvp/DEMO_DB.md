# MVP demo database (local)

Recreates the pilot Postgres database (17 papers, 319 sections, 728 chunks,
728 vectors of 1536 dimensions) locally from `pilot-delivery.zip`.

## Prerequisites

- Docker with Compose (PostgreSQL 17 + pgvector 0.8.7 image, pinned by digest
  in `compose.yaml`), `uv`, PowerShell or Bash.
- `pilot-delivery.zip` with SHA256
  `6FA27AFAF334D6A87BE30A04F3D15A9573696C7C03DDCC5205C23D508F239F2C`
  (compare before extracting; archive bytes are not deterministic).
- Port 5432 free (otherwise set `POSTGRES_PORT=5433` and use the same port in
  `DATABASE_URL`).

## Steps

1. Create `.env` (gitignored; never commit it) with these keys:
   `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_PORT`,
   `DATABASE_URL`. `POSTGRES_DB` must be `sciscope_test_005` (`verify_pilot`
   and the import script hardcode that name). Use a random password.
2. Start the database and wait until healthy:
   ```powershell
   docker compose up -d db
   docker compose ps   # STATUS must show "healthy"
   ```
3. Extract the zip so the package lives in `data/delivery/pilot/` (six files;
   `data/delivery/` is gitignored). Check for path traversal first.
4. Validate the delivery (expects `17/319/728/728`, failures 0):
   ```powershell
   $env:PYTHONPATH = "src"
   uv run --locked python -m sciscope.pipeline.cli validate-delivery `
     --package-dir data/delivery/pilot `
     --parse-report data/pilot/parse_report.json `
     --chunk-report data/pilot/chunk_report.json `
     --embedding-report data/pilot/embedding_report.json
   ```
5. Migrate and import (load `.env` into the shell environment first; the
   importer and Alembic read `DATABASE_URL`):
   ```powershell
   uv run --locked alembic upgrade head
   uv run --locked python scripts/mvp_import_pilot.py
   ```
   Re-running is safe: an identical snapshot reports `unchanged`; a different
   one is refused and nothing is deleted.
6. Verify independently (must print `"status": "PASS"`):
   ```powershell
   uv run --locked python -m sciscope.ingestion.verify_pilot `
     --package-dir data/delivery/pilot `
     --parse-report data/pilot/parse_report.json `
     --chunk-report data/pilot/chunk_report.json `
     --embedding-report data/pilot/embedding_report.json
   ```

## Reset

```powershell
docker compose down -v   # deletes the data volume; then repeat from step 2
```

## Backend connection

Use `DATABASE_URL=postgresql+psycopg://<POSTGRES_USER>:<POSTGRES_PASSWORD>@127.0.0.1:<POSTGRES_PORT>/sciscope_test_005`.
Another checkout (for example the main one running the backend) is not
sharing this worktree's `.env`: copy `DATABASE_URL` into its own `.env`.
The container keeps running independently of the worktree.

## Known limits

- Retrieval quality is NOT VERIFIED (Golden v0 pending); this only proves the
  data is loaded intact.
- The package omits figures, tables, references and raw XML; no paragraphs.
- No vector index is created by the migration; search is exact scan, fine at
  728 rows.
- Database name `sciscope_test_005` is mandatory for the verifier.
- Compose is pinned to a digest, which resolved to PostgreSQL 17.11 and
  pgvector 0.8.7 when this was written.
- This is a local demo setup, not an ACCEPTED feature.
