# Feature 007 T007-E Review and Windows Verification Handoff

## 1. Purpose and Scope

This handoff covers only the remaining T007-E acceptance gates:

1. Person 2 review of the public PostgreSQL integration test.
2. Independent execution of that guarded test on native Windows.

It does not authorize a migration, ingestion, environment change, database
write, provider call, or commit. It does not change the native Windows
requirement in Feature 007 FR-015.

## 2. Current Verified Evidence

The following results are recorded, not inferred:

| Evidence | Observed result |
| --- | --- |
| T007-E-10 | Ubuntu migration to `f005_pgvector_foundation` passed on PostgreSQL 17.12 with pgvector 0.8.7. |
| T007-E-11 | One authorized `INITIALIZE` import produced one active delivery import with 17 papers, 319 sections, 728 chunks, 728 vectors, and 1536 dimensions. Independent `verify_pilot` passed. |
| T007-E-12 | Codex ran `tests/retrieval/test_public_postgres.py`: 1 collected, 1 passed. The target was `sciscope_test_005`, role `sciscope`, over the approved Ubuntu socket. |
| T007-E-13 | The project owner independently reran the guarded Ubuntu test: 1 collected, 1 passed in 0.76 seconds; `git diff --check` reported no error. |

All details are chronological in
`docs/person3/FEATURE_007_T007_TEST_LOG.md`, sections T007-E-10 through
T007-E-13. These Ubuntu results do not establish native Windows compatibility.

## 3. Person 2 Review Checklist

Review `tests/retrieval/test_public_postgres.py` and record each item as
confirmed, finding, or not reviewed:

- [ ] Uses the public `RetrievalService`, `RetrievalRequest`, and
  `RetrievalResponse` boundary.
- [ ] Builds an explicit `retrieval.v1` lexical request.
- [ ] Requires no private import from consumer-facing application code; the
  test-side `_compose_private_executor` use is limited to wiring the real core.
- [ ] Relies on `tests/retrieval/conftest.py::retrieval_engine` identity guard
  before retrieval.
- [ ] Requires one active delivery import and checks active corpus/delivery
  identity.
- [ ] Asserts deterministic repeated results and consecutive ranks.
- [ ] Asserts lexical-only score fields and no embedding/provider invocation.
- [ ] Compares returned source/provenance values with independently read stored
  chunk and paper records.
- [ ] Asserts no synthesized citation attribute.
- [ ] Uses explicit `REPEATABLE READ READ ONLY` preflight and postflight
  transactions.
- [ ] Requires preflight and postflight active-corpus equality.
- [ ] Does not fabricate corpus data or weaken assertions for unavailable data.

Required review record:

- Reviewer:
- Date:
- Findings and required corrections:
- Disposition: **ACCEPTED** / **REJECTED**

No disposition is recorded by this handoff.

## 4. Native Windows Verification Procedure

Feature 007 FR-015 requires native Windows PowerShell with the existing
Python/uv and PostgreSQL environment; Docker and WSL are excluded. Follow the
existing [Feature 005 quickstart](../../specs/005-postgres-pgvector-foundation/quickstart.md).

Before running the test, the Windows verifier must confirm an approved isolated
`sciscope_test_005` database, role `sciscope`, PostgreSQL major 17, pgvector
0.8.7, Alembic revision `f005_pgvector_foundation`, exactly one active import,
and active corpus counts `17/319/728/728`. The fixture performs the version,
extension, revision, database, role, and active-import checks; the verifier
must also report the corpus counts. If any condition fails, stop without
migration, ingestion, or repair.

The Windows quickstart does not establish a reusable credential, database port,
or installation path for this handoff. Keep those values outside Git. It
establishes `SCISCOPE_TEST_DATABASE_URL` as the test-only configuration source.
The existing `scripts.phase_d_readonly_db_preflight.py` safely derives an
in-memory target from the local approved configuration and rejects an invalid
or non-test target.

From a native Windows PowerShell terminal at the repository root, with the
approved local configuration already present, run:

```powershell
$env:PYTHONPATH = '.;src'
$testDatabaseUrl = & .\.venv\Scripts\python.exe -c "from scripts.phase_d_readonly_db_preflight import _load_source_url, derive_test_database_url; print(derive_test_database_url(_load_source_url()), end='')"
if ($LASTEXITCODE -ne 0 -or -not $testDatabaseUrl) { throw 'TESTS_BLOCKED: approved test database configuration is unavailable' }
$env:SCISCOPE_TEST_DATABASE_URL = $testDatabaseUrl
uv run --locked pytest -v tests/retrieval/test_public_postgres.py
$testExitCode = $LASTEXITCODE
Remove-Item Env:SCISCOPE_TEST_DATABASE_URL -ErrorAction SilentlyContinue
exit $testExitCode
```

The command does not print the connection URL. It uses the established
test-target derivation rather than copying Ubuntu Unix-socket settings to
Windows. It must be executed only after the responsible authority confirms the
Windows database is approved and isolated. Any required migration, extension
provisioning, database creation, or pilot import is a separate authorized
operation and is not authorized by this handoff.

## 5. Windows Expected Results

The expected result is one collected test and one pass, with no failures or
skips. This is an expectation, not an observed Windows result.

The test must demonstrate a public `retrieval.v1` lexical response, deterministic
results and ranks, exact persisted provenance comparison, lexical-only scoring,
and unchanged active corpus identity/counts before and after execution. It must
not introduce a database write, provider call, migration, or ingestion.

The verifier must return the command's exit code and terminal summary; database
identity; PostgreSQL and pgvector versions; Alembic revision; active-import
count; corpus counts before and after; confirmation of read-only preflight and
postflight; and any failure output with credentials removed.

## 6. Review and Verification Evidence Template

```text
Reviewer/verifier:
Date:
Operating system:
Python version:
PostgreSQL version:
pgvector version:
Database identity:
Alembic revision:
Exact command:
Test collection:
PASS/FAIL/SKIP:
Active import:
Corpus counts before:
Corpus counts after:
Provenance verification:
Read-only verification:
Findings/blockers:
Decision: ACCEPTED / REJECTED
```

## 7. Remaining T007-E Acceptance Gates

The following remain pending until actual evidence is returned:

- Person 2 review.
- Native Windows verification.
- T007-E owner acceptance.
- Focused T007-E commit.
- Feature-level acceptance.

## 8. Handoff Back to Person 3

Return the completed Person 2 checklist and Windows evidence template with the
actual terminal results and explicit decision. Person 3 will append them to the
chronological T007 evidence log, preserve any failed attempt or correction, and
prepare the final owner-acceptance decision. Neither successful Ubuntu evidence
nor this handoff document completes T007-E.
