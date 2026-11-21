# Person 3 Phase 0 Baseline and Verification Record

**Owner:** Person 3 (Backend & AI)
**Scope:** Documentation-only Phase 0 record. No Person 3 backend, RAG,
FastAPI, provider, API contract, or frontend implementation is authorized by
this document.

## 1. Authority, evidence sources, and boundaries

This record preserves two distinct evidence sources:

1. **Prior Codex read-only audit:** reported inspection conclusions from the
   completed Phase 0 and Phase 0B safety audit. Those conclusions are not
   represented as independently rerun terminal verification in this document.
2. **User-executed terminal evidence:** setup, static checks, offline tests,
   database preparation, migration, import, retrieval integration, and final
   database checks supplied by the user for this record. Exact results below
   are attributed to that evidence; this documentation session did not rerun
   them.

No credentials, connection strings, API keys, protected evaluation material,
or Git-ignored evaluation results are copied here. The test database is named
only where needed to identify its approved isolation boundary.

The governing workflow remains research -> specification -> plan -> tasks ->
approval -> RED/GREEN behavior tests -> automated verification -> human
verification -> evidence/backlog synchronization. The constitution is still
draft pending team ratification. This record neither approves implementation
nor marks any backlog item complete.

## 2. Repository and Git baseline

| Item | Reported / independently checked state |
| --- | --- |
| Repository | `/home/maki/Desktop/SciScope` |
| Branch | `main` |
| Baseline HEAD | `c70507e7c686214528b69aab4566786320c5f43c` |
| Environment | Ubuntu Linux |
| Working tree | Clean before the documentation-only update |
| Person 3 scope | Backend and AI integration only; Person 1 and Person 2 modules remain owned by their respective owners |

The documentation assistant independently rechecked the repository root,
branch, HEAD, and clean working tree at the start of this documentation task.
No source, test, dependency, migration, Docker, environment, Person 1, or
Person 2 file is changed by this update.

## 3. Prior Codex Phase 0 audit (reported, not rerun here)

The earlier read-only audit reported the following:

- Person 1 provides ingestion-related delivery, JATS parsing, chunking, and
  embedding artifacts.
- Person 2 provides PostgreSQL/pgvector persistence, snapshot ingestion,
  retrieval, lookup, ranking, reranking, context selection, and retrieval
  evaluation components.
- Retrieval has a private `_RetrievalCore`; the public facade and Person 3
  integration contracts remain review items.
- Person 3 backend/RAG implementation has not started. P4-01 through P4-21
  remain unchecked.
- Cross-owner shared-interface and architecture decisions require review before
  dependent backend implementation.
- Offline deterministic tests were separated from database-dependent tests;
  protected evaluation material was not authorized for inspection or execution.

These findings establish handoff context only. See `docs/contracts/retrieval-v1.md`,
`docs/contracts/retrieval-v2.md`, `docs/person2/RETRIEVAL_V2_PERSON3_HANDOFF.md`,
and the applicable Person 2 plans for their current contract and approval status.

## 4. Environment and toolchain setup (user-executed evidence)

| Item | Result |
| --- | --- |
| Initial system Python | 3.10.12 |
| uv | 0.13.9 |
| Installed interpreter | CPython 3.12.16 |
| Environment setup | `uv sync --locked --python 3.12` succeeded |
| Local environment | `.venv` created with 87 locked dependencies |
| Source changes during setup | None reported |

The setup is local development preparation. It does not complete P0-04, does
not establish a feature approval, and does not authorize Person 3 code work.

## 5. Static verification (user-executed evidence)

| Command | Result |
| --- | --- |
| `uv run --locked --no-sync ruff check . --no-cache` | PASS — All checks passed. |
| `uv run --locked --no-sync ruff format --check .` | PASS — 286 files already formatted. |
| `MYPY_CACHE_DIR=/tmp/sciscope-mypy-baseline uv run --locked --no-sync mypy src` | PASS — no issues in 78 source files. |

These results are static verification of the existing checkout, not proof of
backend API behavior or generated-answer quality.

## 6. Offline baseline test matrix (user-executed evidence)

Each row is a separate successful pytest run. The total is an arithmetic sum,
not a single whole-suite invocation.

| Test selection | Passed | Scope |
| --- | ---: | --- |
| `tests/jats tests/chunking` | 409 | Synthetic/local parser and chunking behavior |
| `tests/plos_pilot` | 67 | Mocked/local acquisition behavior |
| `tests/embedding` | 449 | Offline fakes and synthetic embedding behavior |
| `tests/delivery` | 1,664 | Synthetic delivery-package behavior |
| `tests/test_golden_schema.py` | 3 | Local schema checks |
| Person 2 offline retrieval selection | 90 | Deterministic retrieval, ranking, validation, and fake paths |
| `tests/ingestion/test_import_contract.py` | 8 | Pure importer contract/state logic |
| `tests/evaluation` | 118 | Synthetic evaluation behavior only |
| `tests/ingestion/test_snapshot_validation.py` and `tests/ingestion/test_vector_decoding.py` | 8 | Local snapshot/vector validation |
| **Offline total** | **2,816** | Sum of the distinct runs above |

The actual local-run command structure used `env -i` with explicit
`PATH`, `HOME`, and `TMPDIR`; `PYTHONDONTWRITEBYTECODE=1`;
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`; `AI_PROVIDER=fake`; pytest
`-p no:cacheprovider`; and temporary `--basetemp` directories. This reduces
inherited-environment and cache contamination. It is **not** a network sandbox
or a general filesystem-isolation guarantee.

Synthetic evaluation tests are not protected held-out evaluations. No protected
held-out result, answer-quality conclusion, or scientific-performance claim is
established by this matrix.

### Earlier offline diagnostics

| Attempt | Observed result | Resolution / interpretation |
| --- | --- | --- |
| Initial isolated JATS/chunking run | 408 passed, 1 failed | Temporary snapshot lacked `.gitignore`; corrected environment rerun passed 409. |
| Initial isolated embedding run | 448 passed, 1 failed | Temporary snapshot lacked Git metadata needed by `git check-ignore`; local repository rerun passed 449. |

These were test-environment artifacts, not demonstrated application defects.
They are retained rather than rewritten as clean-first-run results.

## 7. PostgreSQL test environment and migration (user-executed evidence)

| Item | Result |
| --- | --- |
| Docker | 29.1.4 |
| Docker Compose | v5.0.1 |
| Database service | `sciscope-db-1`, healthy |
| PostgreSQL | 17.11 |
| pgvector | 0.8.7 available and installed |
| Development database | `sciscope`, verified with zero public application tables |
| Dedicated test database | `sciscope_test_005` |
| Migration revision | `f005_pgvector_foundation` |
| Migration target | Dedicated test database only; migration exit code 0 |

Independent post-migration verification reported `alembic_version` at
`f005_pgvector_foundation`, vector extension `0.8.7`, and these six application
tables: `papers`, `sections`, `chunks`, `chunk_embeddings`, `embedding_sets`,
and `delivery_imports`, plus `alembic_version`.

## 8. Configuration failure chronology and correction (user-executed evidence)

1. The first ingestion PostgreSQL attempt produced three fixture setup errors,
   executed zero tests, and exited 1 because the test database URL was rejected.
2. Initial Docker Compose config/ps commands failed with `invalid hostPort: 5432`.
3. Investigation found eight CRLF line endings in the local ignored `.env`, no
   standalone carriage-return characters, and a carriage return appended to the
   parsed test-database name. Exact comparison failed; the inherited port value
   also retained a carriage return.
4. The local ignored `.env` was converted from CRLF to LF. A backup was made
   outside the repository. Previously inherited stale shell values were cleared
   and reloaded. No credential or URL value is recorded here.
5. `docker compose config --quiet` subsequently succeeded when the stale port
   variable was unset or overridden; exact test-database comparison then
   succeeded and the subsequent ingestion tests passed.

**Root cause:** local environment/configuration formatting and stale inherited
process values. This does not demonstrate an importer or retrieval defect.

## 9. Ingestion integration and rollback checks (user-executed evidence)

Environment: PostgreSQL 17.11 with pgvector 0.8.7; guarded real-database
fixtures restricted to `sciscope_test_005`; existing pilot delivery inputs; no
external AI call.

| Command selection | Result |
| --- | --- |
| `tests/ingestion/test_initial_import.py` | 3 passed in 6.30s, exit 0 |
| `tests/ingestion/test_rollback.py` | 8 passed in 41.87s, exit 0 |

Independent SQL verification after both selections reported zero rows in
`papers`, `sections`, `chunks`, `chunk_embeddings`, `embedding_sets`, and
`delivery_imports`. The development database remained at zero application
tables. This independently supports rollback behavior for those runs.

## 10. Pilot snapshot validation and deliberate test-DB initialization

The following local pilot inputs were reported present:

- `data/delivery/pilot/delivery_manifest.json`
- `data/delivery/pilot/embedding_manifest.json`
- `data/delivery/pilot/papers.jsonl`
- `data/delivery/pilot/sections.jsonl`
- `data/delivery/pilot/chunks.jsonl`
- `data/delivery/pilot/vectors.f32`
- `data/pilot/parse_report.json`
- `data/pilot/chunk_report.json`
- `data/pilot/embedding_report.json`

Existing `validate_snapshot` reported PASS, exit 0, with 728 embedding entries
and delivery digest
`sha256:998241789fd9675853962bdfdf98b15b0991bc4cda103413b0abc470666af9d2`.

After explicit guarded preflight, `ImportMode.INITIALIZE` was deliberately run
against the previously empty **test** database. Reported outcome:

| Check | Result |
| --- | --- |
| Snapshot validation / database preflight | PASS / PASS |
| Import outcome | `imported` |
| Papers / sections / chunks / vectors | 17 / 319 / 728 / 728 |
| Active delivery imports | 1 |
| Active delivery digest | Matches the validated digest above |
| Embedding sets / delivery imports | 1 / 1 |
| Development database application tables | 0 |

This is an intentional persistent initialization of the isolated test database,
not a rollback-only test and not a source-code modification. The local delivery
digest is not a substitute for, or a claim about, a separate `corpus_id`.

## 11. Retrieval and pipeline integration (user-executed evidence)

With the active pilot snapshot installed:

| Test selection | Result |
| --- | --- |
| `tests/retrieval/test_postgres_core.py` and `tests/retrieval/test_postgres_lookup.py` | 14 passed in 2.38s, exit 0 |
| `tests/retrieval/test_phase_c_pipeline.py` | 1 passed in 0.79s, exit 0 |

The pipeline test covers retrieval -> lookup -> ranking -> deterministic fake
reranking -> context selection while preserving evidence IDs, exact text, and
source locators. It did not call a real model or regenerate pilot embeddings.

Final independent database verification reported one active snapshot, the same
validated delivery digest, 17 papers, 319 sections, 728 chunks, 728 chunk
embeddings, and zero public application tables in the development database.

## 12. Consolidated verification matrix

| Category | Passed | Qualification |
| --- | ---: | --- |
| Offline baseline groups | 2,816 | Sum of separate successful pytest commands |
| PostgreSQL initial-import tests | 3 | Separate run |
| PostgreSQL rollback tests | 8 | Separate run |
| PostgreSQL retrieval core and lookup | 14 | Separate run |
| PostgreSQL pipeline integration | 1 | Separate run |
| **Aggregate** | **2,842** | `2,816 + 3 + 8 + 14 + 1`; not a single pytest invocation |

No failed application assertion remained in the final reported runs. Earlier
environment/sandbox failures are documented in Section 6 and Section 8.

## 13. Limitations, unresolved decisions, and next steps

- No Person 3 backend/RAG, FastAPI endpoint, API contract, or answer-generation
  behavior has started or been verified.
- No Gemini integration, real OpenAI/Gemini paid call, paid embedding generation,
  protected held-out evaluation, production deployment, or performance validation
  occurred in this Phase 0 record.
- The 17-paper pilot is not the full scientific corpus. These results do not
  establish user-facing factual accuracy, answer quality, citation faithfulness,
  or scientific validity.
- The public retrieval facade and Person 3 HTTP/API contract remain subject to
  Person 2, Person 3, Person 4, and team review. P1-11/P1-14 and the relevant
  contract-adoption gates remain open in repository documentation.
- `retrieval.v2` application enablement remains pending Person 3 integration
  review; this record does not enable it.
- P4-01 through P4-21 remain unchecked. `PROJECT_TODO.md` is unchanged because
  it has no dedicated Person 3 baseline-verification item, and broad foundation
  items cannot be closed without the required acceptance workflow.

### Credential-safe reproduction guidance

Before any future approved rerun, begin with the governing documents and this
record. Use a dedicated test database only, explicit identity preflight, and
the project’s fake-provider default. Provision credentials outside the Codex
environment; never print them, pass them into evidence, or rely on them for
offline tests. Do not run protected evaluation, live-provider, migration, or
snapshot-import commands without their separate approvals. Preserve exact
commands, exit codes, failures, and post-run Git state in `EVIDENCE.md` as work
progresses.

### Required next human checkpoint

Review this reported evidence, confirm the documentation classification and
isolated test-database state, then decide whether to authorize a separate
Person 3 Spec Kit research/specification phase. That future phase must resolve
the public retrieval boundary, HTTP error mapping, API contract, and provider
ownership before implementation.

## Appendix A — Verified command recipes and execution evidence

The recipes in this appendix are transcribed from the user's previous
successful terminal runs. They are execution evidence for the results recorded
above; they were **not** run by Codex during either documentation session.
They are Bash examples for the reported Ubuntu environment, not an
authorization to repeat tests, mutate a database, or access provider services.

### A.1 Static checks

```bash
uv run --locked --no-sync ruff check . --no-cache
```

Observed: PASS — all checks passed.

```bash
uv run --locked --no-sync ruff format --check .
```

Observed: PASS — 286 files already formatted.

```bash
MYPY_CACHE_DIR=/tmp/sciscope-mypy-baseline \
uv run --locked --no-sync mypy src
```

Observed: PASS — no issues in 78 source files.

### A.2 Common offline pytest structure

The following is a parameterized template for the separate selections in the
[offline baseline test matrix](#6-offline-baseline-test-matrix-user-executed-evidence).
`TEST_SELECTION` and `pytest-GROUP` are explicit placeholders; this block is
not presented as one literal command that was executed.

```bash
cd /home/maki/Desktop/SciScope

env -i \
  PATH="/usr/bin:/bin" \
  HOME="/tmp/sciscope-local-tests" \
  TMPDIR="/tmp/sciscope-local-tests" \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  AI_PROVIDER=fake \
  .venv/bin/python -m pytest \
    -q \
    -p no:cacheprovider \
    --basetemp=/tmp/sciscope-local-tests/pytest-GROUP \
    TEST_SELECTION
```

The reported selections and counts are retained in the main matrix: 409 JATS /
chunking, 67 PLOS pilot, 449 embedding, 1,664 delivery, 3 golden-schema, 90
offline retrieval, 8 importer-contract, 118 synthetic evaluation, and 8 local
snapshot/vector tests, totaling 2,816. The environment cleanup is not a
network sandbox or a complete filesystem isolation mechanism.

### A.3 PostgreSQL ingestion tests

The test URL was configured securely before these commands and was required to
target exactly `sciscope_test_005`. No URL or password is reproduced here. The
environment assignments and pytest invocation are deliberately in the same
`env` command.

```bash
env -i \
  PATH="/usr/bin:/bin" \
  HOME="/tmp/sciscope-local-tests" \
  TMPDIR="/tmp/sciscope-local-tests" \
  PYTHONPATH="src:tests/ingestion" \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  AI_PROVIDER=fake \
  SCISCOPE_TEST_DATABASE_URL="$SCISCOPE_TEST_DATABASE_URL" \
  .venv/bin/python -m pytest \
    -q \
    -p no:cacheprovider \
    --basetemp=/tmp/sciscope-local-tests/pytest-ingestion-initial \
    tests/ingestion/test_initial_import.py
```

Observed: 3 passed in 6.30s, exit 0.

```bash
env -i \
  PATH="/usr/bin:/bin" \
  HOME="/tmp/sciscope-local-tests" \
  TMPDIR="/tmp/sciscope-local-tests" \
  PYTHONPATH="src:tests/ingestion" \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  AI_PROVIDER=fake \
  SCISCOPE_TEST_DATABASE_URL="$SCISCOPE_TEST_DATABASE_URL" \
  .venv/bin/python -m pytest \
    -q \
    -p no:cacheprovider \
    --basetemp=/tmp/sciscope-local-tests/pytest-ingestion-rollback \
    tests/ingestion/test_rollback.py
```

Observed: 8 passed in 41.87s, exit 0. The user's earlier independent SQL
verification after these rollback-scoped selections reported:

```text
papers|0
sections|0
chunks|0
chunk_embeddings|0
embedding_sets|0
delivery_imports|0
DATABASE_CHECK_EXIT_CODE=0
```

### A.4 PostgreSQL retrieval integration

These selections use the same isolated environment structure as A.3, except
that `PYTHONPATH=src`. They require the guarded test URL and exactly one active
pilot snapshot in `sciscope_test_005`.

```bash
env -i \
  PATH="/usr/bin:/bin" \
  HOME="/tmp/sciscope-local-tests" \
  TMPDIR="/tmp/sciscope-local-tests" \
  PYTHONPATH="src" \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  AI_PROVIDER=fake \
  SCISCOPE_TEST_DATABASE_URL="$SCISCOPE_TEST_DATABASE_URL" \
  .venv/bin/python -m pytest \
    -q \
    -p no:cacheprovider \
    --basetemp=/tmp/sciscope-local-tests/pytest-retrieval-postgres \
    tests/retrieval/test_postgres_core.py \
    tests/retrieval/test_postgres_lookup.py
```

Observed: 14 passed in 2.38s, exit 0.

```bash
env -i \
  PATH="/usr/bin:/bin" \
  HOME="/tmp/sciscope-local-tests" \
  TMPDIR="/tmp/sciscope-local-tests" \
  PYTHONPATH="src" \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  AI_PROVIDER=fake \
  SCISCOPE_TEST_DATABASE_URL="$SCISCOPE_TEST_DATABASE_URL" \
  .venv/bin/python -m pytest \
    -q \
    -p no:cacheprovider \
    --basetemp=/tmp/sciscope-local-tests/pytest-retrieval-pipeline \
    tests/retrieval/test_phase_c_pipeline.py
```

Observed: 1 passed in 0.79s, exit 0.

### A.5 Independent read-only database verification

The following reported checks use `psql` through the named local container and
contain no connection URL or password. They are recorded here as prior
user-executed evidence, not run by Codex.

```bash
docker exec sciscope-db-1 \
  psql -v ON_ERROR_STOP=1 -U sciscope -d sciscope_test_005 -Atc \
  "SELECT COUNT(*), MIN(delivery_digest)
   FROM delivery_imports WHERE is_active = TRUE;"
```

Observed:

```text
1|sha256:998241789fd9675853962bdfdf98b15b0991bc4cda103413b0abc470666af9d2
```

```bash
docker exec sciscope-db-1 \
  psql -v ON_ERROR_STOP=1 -U sciscope -d sciscope_test_005 -Atc \
  "SELECT 'papers', COUNT(*) FROM papers
   UNION ALL SELECT 'sections', COUNT(*) FROM sections
   UNION ALL SELECT 'chunks', COUNT(*) FROM chunks
   UNION ALL SELECT 'chunk_embeddings', COUNT(*) FROM chunk_embeddings;"
```

Observed:

```text
papers|17
sections|319
chunks|728
chunk_embeddings|728
```

```bash
docker exec sciscope-db-1 \
  psql -v ON_ERROR_STOP=1 -U sciscope -d sciscope -Atc \
  "SELECT COUNT(*) FROM pg_tables WHERE schemaname = 'public';"
```

Observed: `0`.

### A.6 Environment/setup failure chronology and correction

These are environment/setup failures, not implementation TDD RED results. No
failure-inducing commands are supplied or requested.

| Environment/setup failure | Correction | Successful subsequent check |
| --- | --- | --- |
| Initial isolated JATS/chunking snapshot lacked `.gitignore` (408 passed, 1 failed). | Corrected the temporary snapshot. | Rerun: 409 passed. |
| Initial isolated embedding snapshot lacked Git metadata needed by `git check-ignore` (448 passed, 1 failed). | Reran in the actual repository. | Rerun: 449 passed. |
| Initial ingestion fixture setup rejected the test URL (3 setup errors, 0 tests, exit 1). | Converted the local ignored `.env` from eight CRLF lines to LF; cleared/reloaded stale shell values; verified exact parsed test-database name. | Initial-import selection: 3 passed; rollback selection: 8 passed. |
| Compose initially reported `invalid hostPort: 5432`. | Unset or overrode inherited `POSTGRES_PORT`, which contained `5432` followed by a carriage return. | `docker compose config --quiet` passed. |

The evidence does not claim automatic shell-startup configuration was
permanently fixed. It records the observed correction in that terminal context.

### A.7 Final result qualification

```text
2,816 offline
+    3 ingestion initial
+    8 ingestion rollback
+   14 retrieval PostgreSQL
+    1 retrieval pipeline
= 2,842 passed
```

This is an aggregate across separate successful runs. No single 2,842-test
pytest invocation occurred. The final test database was intentionally populated
with the validated pilot snapshot; it must not be described as empty.

No API call, test, database mutation, or source-code change occurred during
this documentation refinement.
