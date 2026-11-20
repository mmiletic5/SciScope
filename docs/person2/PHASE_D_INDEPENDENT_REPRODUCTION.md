# Phase D independent reproduction and review

**Status:** T008 and AC-038 remain open. This document supports independent
review; it does not accept or close either item.

## Review package

The complete private review archive is generated at:

`evals/protected/phase_d_final_review/phase_d_independent_review.zip`

It contains relevant Person 2 source, tests, dependency/configuration files,
frozen Golden v0/v1 records and annotations, source passages and locators,
frozen pilot delivery files, the T005/T006 evidence, the six T006 reports,
lexical/RRF diagnostics, AC/T001-T008 documentation, handoffs, and the manual
verification script and run logs. Protected question material is included
inside the archive for independent review and was not printed in the run log
or terminal. The archive excludes `.env`/credentials, query-vector cache entry
files, unrelated caches, and unavailable raw XML.

The in-archive `package_manifest.json` records SHA-256 and byte length for
each other archive member. The detached
`phase_d_independent_review.zip.manifest.json` records hashes for every ZIP
member, including `package_manifest.json`, and the SHA-256 of the complete
archive. The builder verifies member hashes and ZIP CRC integrity.

## Native Windows procedure

From the repository root in VS Code's Windows PowerShell terminal:

```powershell
./scripts/phase_d_manual_verification.ps1
```

The script uses the existing `.venv`, Python 3.12, and the native
`postgresql-x64-17` service. It records a timestamped `verification.log` and
`summary.json` under the Git-ignored
`evals/protected/phase_d_final_review/manual_verification/` directory.
Commands, exit codes, test summary counts, expected/observed diagnostic
counts/ranks, environment identifiers, and explicit skips are recorded.
Detailed child output is retained only in memory; console and log output are
limited to sanitized status summaries.

The script runs the offline `tests/evaluation` and `tests/retrieval` suite,
focused ranking/lexical tests, Ruff, Ruff formatting, mypy, and `git diff
--check`. It independently verifies the saved T006 report hashes, cohort/arm/
partition identities, macro Recall@K/Evidence Hit@K/MRR values recomputed from
eligible per-question records, frozen delivery payload hashes, and the two
query-cache manifest hashes/identities. It checks cache metadata only; it
does not read or emit vector values.

For PostgreSQL, the script performs a guarded, read-only preflight before the
integration suite and an identical postflight afterward. The preflight must
confirm database `sciscope_test_005`, role `sciscope`, PostgreSQL 17,
read-only transaction mode, corpus `pilot17-xml-1fff1573b610`, 17 papers,
319 sections, 728 chunks, 728 embeddings, and embedding set ID 115. Only the
inspected read-only Phase B/C PostgreSQL retrieval tests and fixed lexical
diagnostic probes are run. The full `tests/database` suite is included for
review but is not run against the frozen database: its shared fixture invokes
`alembic upgrade head`, and several schema tests write rows before rollback.

No protected retrieval is rerun. No API, migration, DDL, DML, tuning, or
corpus change is performed. A failed prerequisite is reported as FAIL and
dependent operations are explicitly SKIP; a skip prevents an overall PASS.

## Diagnostic interpretation

The eight lexical probes use fixed source-derived/public terms and known
source locators from the frozen pilot. They record expected versus observed
FTS candidate counts and target ranks in the protected run summary. A
synthetic RRF diagnostic compares the frozen fusion implementation with an
independent arithmetic oracle; it uses mock ranked lists and no corpus or
Golden question. Existing T008 findings remain descriptive: FTS returns
controlled exact-term candidates, may rank a numeric-only target beyond top
20, and AND semantics can over-constrain long cross-source queries. No
retrieval setting is changed, and no protected report is used to select a
configuration.

## Reproduction boundaries and limitations

- Offline tests, static checks, schema/source inspection, saved aggregate
  recomputation, hash checks, and synthetic RRF are reproducible with the
  included source and locked environment.
- Read-only retrieval integration tests and lexical probes require the
  existing native PostgreSQL 17 / pgvector 0.8.7 installation and frozen
  `sciscope_test_005` snapshot. They are not reproducible from the ZIP alone.
- Re-running dense/hybrid retrieval requires separate authorization, the
  frozen database, and protected query vectors. The ZIP contains query-cache
  manifests but intentionally excludes the 22 actual query-vector entries.
- Original raw scientific XML was unavailable. The package includes the
  frozen delivered source passages, DOI metadata, exact locators, and hashes
  needed to review the Golden records against the supplied corpus snapshot.
- ChatGPT approved all nine Golden v1 records from the supplied source packet;
  this is an AI review, not human verification or an independent search of all
  17 papers. The held-out cohorts are small. Q4/Q5 are false-conflict negative
  controls; no genuine-conflict sensitivity claim is supported.
- ChatGPT did not independently reproduce PostgreSQL. T006 reports contain
  aggregate and per-question evidence but not full lexical candidate lists.
- AC-038 remains partial: existing timings lack cold/warm labels and separate
  embedding/database/fusion-stage measurements. It cannot be repaired
  retroactively without new authorized instrumentation and a new run.

T008 remains open pending independent ChatGPT review of this package and the
owner's decision about whether a separate versioned lexical/hybrid improvement
cycle is needed.

## Windows verification record

The native Windows PowerShell command `./scripts/phase_d_manual_verification.ps1`
completed with overall PASS on 2026-11-20. The captured run is
`evals/protected/phase_d_final_review/manual_verification/20261120T121510Z/`.
Python 3.12.16 ran under PowerShell 5.1 on Windows 10 build 19045 with the
`postgresql-x64-17` service. The exact child commands, exit codes, and
sanitized summaries are in the run's `summary.json` and `verification.log`.

Results: 195 offline evaluation/retrieval tests passed with one database-only
Phase C test deselected; 9 focused lexical/RRF tests passed; all 13 inspected
read-only PostgreSQL retrieval integration tests passed. Ruff check, Ruff
format check, mypy, and `git diff --check` passed. Seven T006 artifacts and
all six cohort/arm reports passed integrity and identity checks; 90 saved
macro metric aggregations were independently recomputed; five frozen delivery
payloads and two query-cache manifests passed hash/identity checks. The eight
read-only lexical probes matched their preregistered expected candidate counts
and target ranks. The synthetic RRF result matched the independent oracle.
Database preflight and postflight both confirmed the same read-only frozen
pilot identity and embedding set 115. No held-out retrieval, database write,
migration, paid API call, or query-vector read was performed by this manual
verification.

Two initial harness starts stopped before tests: the first had a PowerShell
native-argument quoting issue; the second exposed missing source import path
setup. A subsequent full run passed tests and diagnostics but exposed two
harness checks that needed correction (PowerShell Git stderr capture and the
hybrid arm label in the saved-report auditor). All four sanitized run records
are retained. These issues did not modify the database or execute protected
retrieval. The final run after fixes is the reported complete verification.
