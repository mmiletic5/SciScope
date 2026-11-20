# Quickstart: Verify Validated Snapshot Ingestion

All Person 2 steps in this guide run natively on Windows 10 x64 using Windows
PowerShell and the Feature 005 PostgreSQL 17/pgvector 0.8.7 installation.
Docker, WSL, Linux containers, and Bash are not used. Do not proceed until the
native Feature 005 compatibility gate is verified and required infrastructure
actions are explicitly authorized.

Feature 006 implementation and non-destructive test writes on
`sciscope_test_005` are authorized. The final acceptance command below is
read-only and intentionally verifies the committed pilot snapshot; it does not
run migrations or alter database state.

## Preconditions

- Feature 005 is human-accepted and its real database is healthy.
- Feature 006 implementation is approved; tests use the existing locked
  environment.
- `data/delivery/pilot/` contains the validated six-file package.
- The three committed source reports match the delivery manifest.
- No paid provider key or call is required.

## Confirm input before import

```powershell
$env:PYTHONPATH = "src"
uv run --locked python -m sciscope.pipeline.cli validate-delivery `
  --package-dir data/delivery/pilot `
  --parse-report data/pilot/parse_report.json `
  --chunk-report data/pilot/chunk_report.json `
  --embedding-report data/pilot/embedding_report.json
```

Expected exit 0 and exactly `17/319/728/728`, six files, zero failures. Any
other result stops the import; do not repair the delivered data.

## RED/GREEN automated suites

```powershell
uv run --locked pytest tests/ingestion/test_import_contract.py -q
uv run --locked pytest tests/ingestion/test_snapshot_validation.py -q
uv run --locked pytest tests/ingestion/test_vector_decoding.py -q
uv run --locked pytest tests/ingestion/test_initial_import.py -q
uv run --locked pytest tests/ingestion/test_idempotency.py -q
uv run --locked pytest tests/ingestion/test_replacement.py -q
uv run --locked pytest tests/ingestion/test_rollback.py -q
uv run --locked pytest tests/ingestion/test_concurrency.py -q
uv run --locked pytest tests/ingestion/test_provenance.py -q
uv run --locked pytest tests/ingestion/test_audit.py -q
uv run --locked pytest tests/ingestion/test_verify_pilot.py -q
```

Each database-owned suite must use real PostgreSQL/pgvector. Record the initial
legitimate RED and later GREEN for each approved task. Unavailable infrastructure
is BLOCKED, never a passing skip.

## Real-pilot initialization and reconciliation

The final CLI spelling is governed by `contracts/importer-v1.md` and its tests.
Run initialize against a clean database, then run the independent verifier:

```powershell
uv run --locked python -m sciscope.ingestion.verify_pilot `
  --package-dir data/delivery/pilot `
  --parse-report data/pilot/parse_report.json `
  --chunk-report data/pilot/chunk_report.json `
  --embedding-report data/pilot/embedding_report.json
```

Expected: 17 papers, 319 sections, 728 chunks, 728 vectors, and zero missing,
extra, provenance, dimension, vector-byte, or orphan mismatches. The verifier
must not call importer internals.

## Idempotency, replacement, rollback, and concurrency

- Re-run the identical pilot and prove `unchanged` plus a byte/logical database
  fingerprint and audit timestamps identical to the pre-run state.
- Use complete synthetic snapshots for changed replacement; never mutate the
  real pilot. Prove missing/mismatched expected digest is rejected.
- Inject failure after each mutation stage and prove the prior fingerprint is
  unchanged, then retry successfully.
- Coordinate two connections and prove exactly one owns the advisory lock while
  the other returns `IMPORT_IN_PROGRESS` with zero mutation.

## Full acceptance

The following command runs the independent read-only acceptance check from
VS Code PowerShell. It reads `.env` in-process, derives only the explicitly
authorized `sciscope_test_005` target, verifies the connected role is
`sciscope`, starts a read-only transaction, and prints no URL or credentials.
It does not contact or modify the main `sciscope` database.

```powershell
.\scripts\verify_feature006_readonly.ps1
```

Expected final line: `RESULT PASS 10/10`. Each of the ten named checks must say
`PASS`, with `mismatches=0/0/0/0/0/0`. Any `FAIL`, exception, different database
or role, or nonzero mismatch is a failed acceptance check. The expected pilot
counts are 17 papers, 319 sections, 728 chunks, and 728 vectors.

The user should independently run this check and provide its terminal output
and explicit acceptance. Automated results do not mark Feature 006 accepted.

```powershell
uv run --locked pytest tests/database tests/ingestion -q
uv run --locked pytest -q
uv run --locked ruff check . --no-cache
uv run --locked ruff format --check .
uv run --locked mypy src
uv run --locked alembic current
uv run --locked alembic check
git diff --check
git status --short
```

Record exact commands, versions, revision, image digest, delivery digest,
results, skips, failures, and explicit human acceptance in `EVIDENCE.md`.
