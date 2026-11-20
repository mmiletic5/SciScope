# Phase D T004 Review and Verification Record

**Date:** 2026-11-20  
**Scope:** Person 2 T004 only; no T005/T006 work is authorized by this record.  
**T004 status:** PASS. Later Phase D work remains stopped pending separate
explicit user authorization.

## Independent ChatGPT scientific review

The user reported independent ChatGPT review of all nine Golden v1 revision 2
records. The recorded decisions are:

| Question | Decision |
| --- | --- |
| Q1 | APPROVE |
| Q2 | APPROVE |
| Q3 | APPROVE |
| Q4 | APPROVE |
| Q5 | APPROVE |
| Q6 | APPROVE |
| Q7 | APPROVE |
| Q8 | APPROVE |
| Q9 | APPROVE |

The review found the questions scientifically consistent with the supplied
passages from the frozen derived corpus and the amended methodology. Q4 and Q5
are valid false-conflict negative controls for the Conflicting Evidence Finder;
they are not genuine conflicts. Golden v1 does not measure genuine-conflict
detection sensitivity. The review confirmed matching package hashes, packet
integrity and Golden schema validity, all 19 evidence quotations in the supplied
passages, and the frozen 3-development/6-held-out partition.

The external review reported 59 Phase D evaluation tests passing in its
container. It also reported 215 broader tests passing and one failure caused by
the implementation archive omitting `.gitignore`. That original implementation
archive was `phase_d_implementation_verification_r2.zip`, SHA-256
`7f8fbce298cf4e953f665cbe0584f7316a3c0272a0fc38ebf8a5a720ea0e4900`. The
omission is corrected in the final archive below. The review was model-based,
not human verification. It did not have original raw XML, did not independently
re-search the complete frozen corpus, and did not reproduce the entire project
regression. The independent container did not report exit codes; those are
therefore recorded as unavailable.

Golden question, evidence, annotation, provenance, and partition files were not
regenerated or rewritten after approval. Their existing packet records retain
the status they had when the review packet was frozen; this review disposition
is recorded here separately. No human-authored or human-verified status is
claimed.

## Final protected artifacts

- Golden review packet:
  `evals/protected/golden_v1_review/golden_v1_chatgpt_review_packet_r2.zip`  
  SHA-256: `6c8fb1deae63398e99950080750d6c52746cc1d871710711c6624b926ddd205f`.
- Corrected implementation verification archive (includes root `.gitignore`):
  `evals/protected/golden_v1_review/phase_d_implementation_verification_r2.zip`  
  SHA-256: `80ffaaa0e1d20fe01a5c5b2139f23b88e8d169e1664b9073a718efc6b2e5930a`.
  It contains 202 hashed code, test, schema, configuration, dependency, and
  test-execution documentation members. This review report is maintained
  alongside the archive to avoid a self-referential archive hash.
- The original raw XML is unavailable locally. Evidence excerpts were verified
  against the frozen derived chunks and source identity metadata; no raw-XML
  byte-level verification is claimed.

## Native Windows verification

Environment: Windows PowerShell, Python 3.12.16, PostgreSQL 17.12 Windows
service `postgresql-x64-17`, localhost port 5432, pgvector 0.8.7. The local
project `DATABASE_URL` was read in memory, retargeted only to the exact test
database, and never printed or persisted as `SCISCOPE_TEST_DATABASE_URL`.

The 13 requested PostgreSQL retrieval integration tests use
`tests/retrieval/conftest.py::retrieval_engine`, which checks the exact database,
role, PostgreSQL/pgvector versions, migration revision, and one active import.
The tests issue retrieval/lookup reads only; retrieval transactions are
read-only. They do not call the separate `tests/database/conftest.py` fixture
that runs Alembic migrations or the transaction fixture that writes synthetic
rows and rolls them back. No PostgreSQL integration test created, dropped,
truncated, deleted, or updated data.

Read-only preflight and postflight verified `sciscope_test_005`, role `sciscope`,
PostgreSQL 17, pgvector 0.8.7, migration revision `f005_pgvector_foundation`,
and the seven expected public tables. Active corpus counts remained 17 papers,
319 sections, 728 chunks, and 728 embeddings. Whole-database totals remained two
imports (one active), 18 papers, 320 sections, 729 chunks, and 729 embeddings;
the extra rows belong to the pre-existing inactive synthetic import. No counts
changed across the integration run.

Commands and exit codes:

| Command / verification | Result |
| --- | --- |
| `.\.venv\Scripts\pytest.exe -p no:cacheprovider tests/evaluation tests/retrieval --ignore=tests/retrieval/test_postgres_core.py --ignore=tests/retrieval/test_postgres_lookup.py --ignore=tests/retrieval/test_phase_c_pipeline.py -q` | 150 passed, 0 failed, exit 0 |
| PowerShell/Python URL guard below, then `pytest.main(['-p','no:cacheprovider','tests/retrieval/test_postgres_core.py','tests/retrieval/test_postgres_lookup.py','tests/retrieval/test_phase_c_pipeline.py','-q'])` | 13 passed, 0 failed, exit 0 |
| `.\.venv\Scripts\ruff.exe check src tests scripts` | Pass, exit 0 |
| `.\.venv\Scripts\ruff.exe format --check src tests scripts` | 168 files already formatted, exit 0 |
| `.\.venv\Scripts\mypy.exe src/sciscope/evaluation src/sciscope/retrieval src/sciscope/database` | 25 source files checked, pass, exit 0 |
| Golden v1 protected validator | 9 records; 3/0/2/1/3 categories; 3/6 partitions; 19 evidence references; 10 source DOIs; leak scan 194 files; no Golden v0 access or tuning; pass |
| Frozen delivery manifest/payload audit | All five payload hashes, byte counts, and record counts match; derived 17-source identity digest matches `pilot17-xml-1fff1573b610`; no files modified |
| Extracted-package `.gitignore` regression | `tests/chunking/test_chunk_output.py::test_processed_data_is_ignored_but_chunk_report_is_not`: 1 passed, exit 0 |
| Extracted-package offline evaluation/retrieval regression | 150 passed, 0 failed, exit 0 |

Exact native PowerShell invocation for the PostgreSQL suite (the wrapper reads
the existing `.env` URL in memory, verifies the source database is local
`sciscope`, targets only `sciscope_test_005`, and never prints or persists the
derived URL):

```powershell
$env:PYTHONPATH='.;src'
@'
import os, sys
from pathlib import Path
from sqlalchemy.engine import make_url
from sciscope.database.config import DatabaseSettings
lines = Path('.env').read_text(encoding='utf-8').splitlines()
raw = next(x.split('=', 1)[1].strip().strip('"\'')
           for x in lines if x.strip().startswith('DATABASE_URL='))
source = make_url(raw)
if source.database != 'sciscope' or source.host not in ('localhost', '127.0.0.1') or source.port not in (None, 5432):
    print('TESTS_BLOCKED: local source database guard failed')
    sys.exit(2)
url = DatabaseSettings(url=source.set(database='sciscope_test_005').render_as_string(hide_password=False)).url
if make_url(url).database != 'sciscope_test_005':
    print('TESTS_BLOCKED: exact test database guard failed')
    sys.exit(2)
os.environ['SCISCOPE_TEST_DATABASE_URL'] = url
import pytest
raise SystemExit(pytest.main([
    '-p', 'no:cacheprovider',
    'tests/retrieval/test_postgres_core.py',
    'tests/retrieval/test_postgres_lookup.py',
    'tests/retrieval/test_phase_c_pipeline.py', '-q'
]))
'@ | .\.venv\Scripts\python.exe -
```

The protected validation and corpus-audit commands were Python here-strings
piped to `.\.venv\Scripts\python.exe -`; they emitted only counts, Boolean
integrity results, and hashes, not question text or credentials.

The 44-test `tests/database` collection was not run as part of the requested
13-test retrieval integration check. Its session fixture invokes
`alembic upgrade head`; although read-only inspection showed the database is
already at the sole migration head, that separate schema suite was not needed
to establish T004 retrieval verification. No database mutation authorization
was exercised or required.

## Acceptance boundary

T004's scientific review and requested offline/retrieval verification passed,
with the limitations above. This does not mean Golden v1 is human-verified or
that Phase D is complete. Do not start T005, query-vector preflight, T006, or
held-out retrieval evaluation until the user explicitly authorizes continuation
and any separate required gates are satisfied.
