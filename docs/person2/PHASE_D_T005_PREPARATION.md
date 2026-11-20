# Phase D T005 Preparation

**Status:** Preparation baseline and initial preflight report are retained as
history; current T005 readiness passed on 2026-11-20.
**Scope:** Offline inspection and synthetic verification only. No protected
Golden records, query-cache files, databases, embeddings, or retrieval outputs
were accessed in this preparation.

## T005 completion update (2026-11-20)

The later explicit user authorization covered query embedding generation for
both frozen held-out cohorts, with no monetary cap, solely for the required
`text-embedding-3-small` vectors. The authorization receipt is
`evals/protected/phase_d_authorizations/t005_embedding_generation_user_approval.json`;
it records a direct conversation excerpt and is not a cryptographic signature.
The dataset file hashes and frozen partition digests were checked against the
existing T005 identities before held-out question text was loaded. Only the
allowlisted v0-HO (16) and v1-HO (6) records were sent to the embedding API.
No text was printed or included in reports.

The initial cache search found no compatible vectors. Generation produced 22
vectors in 3 calls (626 prompt tokens; 626 total tokens), with actual cost
USD 0.00001252 under the configured USD 0.02 per million input-token price.
Both cohort manifests and every vector passed the existing verifier for exact
question association, frozen dataset/corpus/partition/embedding-set identity,
model/dimensions/configuration, cache integrity, finite values, and normalized
nonzero norms. The cache and detailed vector identities remain under
Git-ignored `data/embeddings/phase-d-query/`; the protected text-free reports
are `evals/protected/phase_d_t005_readiness_report.json` and
`evals/protected/phase_d_t005_embedding_generation_report.json`.

**Current T005 readiness: PASS.** The API operation did not authorize retrieval.
T006 subsequently received a separate explicit authorization and completed; see the current results and evidence summary. No database
write, migration, tuning, or evaluation occurred. Earlier preparation findings
below describe the pre-generation state and are retained as an audit trail.

## T005 requirements and gates

T005 is the read-only readiness check for query vectors corresponding to the
protected held-out cohorts. It must verify the exact frozen dataset, cohort,
partition, corpus and active embedding-set identities; each question-to-query
hash association; provider/model/configuration; cache and vector provenance;
vector integrity; and the expected 1536-dimensional embedding space. The
acceptance criteria are AC-019 through AC-022, AC-034, and AC-044. T005 does
not generate vectors or run retrieval.

The task plan requires a separate explicit authorization naming the intended
held-out cohort(s) before any protected question text or derived question hash
is read. That authorization permits read-only preflight only. T006 requires a
second, distinct authorization for retrieval after T005 succeeds. Missing or
invalid vectors stop the affected dense/hybrid arms; they are not counted as
retrieval failures and may not be silently removed from denominators. Any
generation proposal needs separate approval with exact model, calls, cost
estimate, and hard spending cap.

## Baseline and corpus inspection

The frozen baseline remains unchanged: `text-embedding-3-small`, 1536
dimensions, empty query and passage prefixes, dense cosine retrieval, English
lexical retrieval, RRF with the registered constant, and MiniLM disabled. The
frozen corpus identity remains `pilot17-xml-1fff1573b610` (17 papers, 319
sections, 728 chunks, 728 embeddings). No retrieval setting, partition, or
corpus file was modified.

The baseline and corpus identity are documented in
[`PHASE_D_BASELINE_FREEZE.md`](PHASE_D_BASELINE_FREEZE.md). The local passage
embedding cache and its manifest are not evidence that compatible query
vectors exist. No protected cache path, manifest, entry, question text, or
question hash was inspected. Therefore query-vector availability is **unknown**;
this report does not claim vectors are present or absent. The previously
documented Windows read-only database identity/count preflight is relied on;
no database connection was needed for this preparation.

## Code and configuration findings

### Brief implementation research

Two internal designs were considered: make the existing combined validator
accept an optional retrieval record, or add a standalone preflight validator
while keeping the combined retrieval validator strict. The separate validator
was selected because the T005 and T006 call paths remain explicit and a
preflight success cannot be confused with retrieval authorization. Both paths
reuse the same sanitized record parser and approval/population checks; no new
dependency or external service is needed. These checks validate approval
record structure and binding. They do not independently prove that the stated
owner approval occurred; the operator must retain the actual approval evidence
as required by the execution policy.

- `src/sciscope/evaluation/embeddings.py` contains a read-only verifier for a
  versioned query-cache manifest and its exact vector entries. It binds records
  to question IDs and normalized text hashes, provider-input hashes, dataset,
  corpus, partition and embedding-set identities, model/configuration, entry
  checksums, vector checksums, finite values, nonzero norm, and a norm tolerance.
  It returns IDs and hashes, not vector values.
- The frozen expected query configuration is OpenAI
  `text-embedding-3-small`, response model ID identical, 1536 dimensions,
  empty prefixes, and `float32-le`. A valid verified cache would avoid paid
  calls. The generic passage cache alone does not establish the required
  question-level provenance.
- No query-vector generation entry point is part of the inspected evaluation
  path. No cache was assumed and no generation was attempted.
- The gate-flow defect was corrected under the owner's narrow authorization.
  `require_preflight_authorization` now validates a single T005 approval and
  binds it to an explicitly named cohort; it validates purpose, owner approval,
  evidence digest, UTC timestamp, dataset version, and partition digest.
  `require_evaluation_authorizations` still requires two distinct, valid,
  matching T005/T006 records. The CLI has separate preflight-only and
  retrieval-authorization check modes; the T005 mode rejects retrieval-record
  input, and legacy `--check-authorizations` remains an alias for the strict
  two-record retrieval check. Neither mode accesses protected data. Dataset,
  partition, and corpus identity checks in the query-cache verifier are
  unchanged.

## Offline verification performed

Native Windows PowerShell, repository `.venv`, Python 3.12 environment:

| Command | Result |
| --- | --- |
| `$env:PYTHONPATH='.;src'; .\.venv\Scripts\pytest.exe -p no:cacheprovider tests/evaluation tests/retrieval --ignore=tests/retrieval/test_postgres_core.py --ignore=tests/retrieval/test_postgres_lookup.py --ignore=tests/retrieval/test_phase_c_pipeline.py -q` | PASS, exit 0, 150 passed |
| `$env:PYTHONPATH='.;src'; .\.venv\Scripts\pytest.exe -p no:cacheprovider tests/evaluation/test_phase_d_embeddings.py tests/evaluation/test_phase_d_runner.py -q` | PASS, exit 0, 9 passed |
| `.\.venv\Scripts\ruff.exe check src tests scripts` | PASS, exit 0 |
| `.\.venv\Scripts\ruff.exe format --check src tests scripts` | PASS, exit 0, 168 files formatted |
| `.\.venv\Scripts\mypy.exe src/sciscope/evaluation src/sciscope/retrieval src/sciscope/database` | PASS, exit 0, 25 source files |

The specific 9-test result is included in the 150-test suite. These checks
validate synthetic/offline behavior only; they do not establish real query
cache readiness or authorize protected-data access.

## Readiness decision and next steps

**Offline implementation readiness:** PASS, including the authorization
gate-flow correction and its synthetic tests.
**Protected query-vector readiness:** NOT CHECKED (cohort-named authorization
has not been granted for this operation, and protected files remain unopened).
**Paid API need:** UNKNOWN. If authorized preflight finds a complete compatible
cache, no paid generation is needed. If it finds any miss or invalid entry,
stop and present the exact prerequisites and a separately authorized,
hard-capped generation proposal. Never substitute another model or omit
questions.
**Retrieval evaluation:** NOT RUN.

Required sequence:

1. Obtain explicit authorization naming `v0-HO` and/or `v1-HO` for read-only
   query text/cache-vector readiness checks. This authorizes only the specified
   cohort preflight, not vector generation or retrieval.
2. Verify the cache and emit only the protected, IDs-and-hashes-only readiness
   report. If anything is missing or unverifiable, stop and request separate
   paid-operation authorization before generation.
3. After T005 passes, obtain a distinct explicit T006 authorization before any
   retrieval evaluation.

T005 remains open. No acceptance criterion is marked passed by these
preparation checks.

Read-only corpus delivery recheck during this preparation: the local draft manifest reports 17 papers, 319 sections, 728 chunks, and 728 vectors; all five payload SHA-256 and byte-length entries matched (PASS). No payload or manifest was modified. The manifest remains marked `draft`.

### Authorization-gate correction (2026-11-20)

The owner authorized only the T005/T006 gate-flow correction. A standalone T005
validator and CLI mode were added, while the strict T006 two-record matching
requirement remains. Synthetic tests cover missing, malformed, wrong-purpose,
forged, wrong-cohort, dataset/partition mismatch, premature/reused retrieval
records, UTC timestamp validation, and sanitized errors. This validates the
local gate implementation only; no real approval record was created or
validated, no protected cohort was named in an authorization artifact, and no
protected data was accessed. T005 readiness remains unchecked.

## Post-correction verification (2026-11-20)

After the separate gate correction, the full native Windows offline evaluation/retrieval suite passed: 181 passed, exit 0. This includes 33 authorization and CLI tests. Ruff check passed, formatting check passed (168 files), and mypy passed (25 source files). No database-backed suites were run in this correction, no protected data or cache was accessed, and no retrieval evaluation occurred.

Exact commands (PowerShell, repository `.venv`):

- `$env:PYTHONPATH='.;src'; .\.venv\Scripts\pytest.exe -p no:cacheprovider tests/evaluation tests/retrieval --ignore=tests/retrieval/test_postgres_core.py --ignore=tests/retrieval/test_postgres_lookup.py --ignore=tests/retrieval/test_phase_c_pipeline.py -q` — PASS, exit 0, 181 passed.
- `.\.venv\Scripts\pytest.exe -p no:cacheprovider tests/evaluation/test_phase_d_runner.py -q` — PASS, exit 0, 33 passed (included in 181).
- `.\.venv\Scripts\ruff.exe check src tests scripts` — PASS, exit 0.
- `.\.venv\Scripts\ruff.exe format --check src tests scripts` — PASS, exit 0, 168 files formatted.
- `.\.venv\Scripts\mypy.exe src/sciscope/evaluation src/sciscope/retrieval src/sciscope/database` — PASS, exit 0, 25 source files.

These checks establish gate implementation behavior only. AC-034 and protected
query-vector readiness remain open until the explicitly authorized operational
preflight is performed. No approval record was created or checked.
