# Phase D Evidence Summary for Independent Review

**Current status:** T004 accepted; T005 readiness PASS for v0-HO and v1-HO;
separately authorized T006 retrieval completed for both cohorts. T007 evidence
and handoffs are prepared. The owner reports independent ChatGPT review of the
final package and independent metric recomputation passed. T008 documentation
and read-only lexical diagnostics are complete. The owner decision on a
separate lexical/hybrid diagnostic cycle and final user acceptance remain
pending. Phase D is not yet accepted as complete.

## T005 verification

**Superseding completion evidence (2026-11-20):** The user separately
authorized missing-vector generation for the two frozen held-out cohorts, with
no monetary cap and no other paid or retrieval operation. Initial cache search
found no compatible vectors. Before loading text, the frozen dataset hashes
and partition digests matched the recorded cohort identities. Only the
allowlisted 16 v0-HO and 6 v1-HO questions were sent to the configured OpenAI
embedding endpoint. The text was not logged, emitted, or used for retrieval
or tuning. Both caches passed complete model/configuration/identity/mapping,
manifest/entry/vector integrity, dimensionality, finiteness, and norm checks.
Actual usage was 22 vectors, 3 API calls, 626 prompt/total tokens, and USD
0.00001252. The protected text-free generation report records cohort counts,
manifest digests, usage, and the approval receipt identity. Detailed vector
hashes stay only in the Git-ignored cohort cache manifests. Current T005 status
is PASS; T006 was subsequently separately authorized and completed.

- The current user message explicitly authorizes read-only preflight for both
  v0-HO and v1-HO. A Git-ignored receipt binds the exact authorization excerpt
  to its SHA-256 and labels it as a conversation source, not a digital
  signature. Two cohort-specific authorization records include the source
  reference and computed dataset, partition, corpus, and baseline identities.
- v1's frozen slot assignment was checked against its separate protected
  development/held-out files and exact counts. v0's fixed 5/16 split was
  reconstructed from the accepted protocol allowlist and frozen v0 dataset
  question-ID set. There is no pre-existing standalone v0 partition-digest
  manifest; the deterministic digest and this limitation are recorded in the
  protected report. Membership was not changed.
- Local payload hashes/byte counts passed for all five frozen delivery files.
  A local read-only PostgreSQL transaction confirmed `sciscope_test_005`, role
  `sciscope`, PostgreSQL 17, read-only mode, one active import, 17 papers, 319
  sections, 728 chunks, 728 embeddings, the frozen corpus identity, and the
  compatible active embedding set. No database writes or migrations occurred.
- At the initial preflight, `data/embeddings/phase-d-query` was absent and no `data/embeddings` directory
  exists. No query-cache manifest or entries were available at the registered
  location. Zero of 22 expected query vectors were verified; model/dimension,
  exact question association, provenance, norm, and cache integrity therefore
  remain unverifiable. The preflight stopped before question text was parsed
  for vector verification or sent to a provider. Dataset bytes were read to
  compute file SHA-256 values and question IDs were extracted solely to verify
  frozen partition membership. No text was printed, embedded, retrieved, or
  used for tuning.
- No retrieval evaluation was performed. The initial cache-missing statement
  above is historical and is superseded by the completion evidence above.

## Offline verification

Native Windows PowerShell, repository Python 3.12 `.venv`:

- Offline evaluation/retrieval suite: 181 passed, 0 failed, 0 skipped, exit 0.
  Three database-backed retrieval modules were excluded from this offline run.
- Focused authorization/CLI suite: 33 passed, exit 0 (included in the 181).
- Ruff check: passed, exit 0.
- Ruff format check: passed, 168 files formatted, exit 0.
- Mypy: passed, 25 source files, exit 0.
- `git diff --check`: passed; Git emitted only its CRLF normalization advisory
  for existing Markdown files.

During the correction, an intermediate full test run failed because the strict
T006 validator had not yet been updated to pass its expected cohort into the
new standalone T005 validator. The call was fixed and the full suite rerun
successfully. An exploratory partition-identity command also printed the v0
dataset-file and partition SHA-256 values to the local command-output stream
before the output was sanitized. It printed no question text or per-question
query hashes; those digests are not repeated in ordinary files or this
summary. The protected preflight report records the access/processing scope.

## Evaluation results and limitations at initial T005 preparation

No dense, lexical, or hybrid retrieval run occurred. All retrieval metrics,
metric denominators, latency, and held-out reproducibility values are **NOT
COMPUTED**. The cohort sizes (v0-HO n=16, v1-HO n=6) are membership counts,
not metric denominators. Q4/Q5 remain false-conflict negative controls; no
genuine-conflict sensitivity claim is supported. The delivery manifest remains
`draft`; raw XML was unavailable during Golden curation; ChatGPT's Golden
review is model review, not human verification.

Historical T005-preparation note: at that point the CLI checked authorization
artifacts only and T006 had not yet been authorized or run. The subsequently
implemented runner and completed authorized execution are documented below.

## T006 and T007 completion update (2026-11-20)

The user's separate T006 authorization covers both held-out cohorts and only the frozen dense, lexical, and hybrid retrieval modes on read-only sciscope_test_005. T005/T006 approval pairs passed the strict validator for both cohorts. The native PowerShell command was `$env:PYTHONPATH='.;src'; .\.venv\Scripts\python.exe scripts/phase_d_run_retrieval_evaluation.py --run-authorized` (PASS, exit 0). The run evaluated v0-HO n=16 and v1-HO n=6, each twice per arm; repeated ranked evidence signatures matched. Read-only DB pre/post checks passed and no writes or migrations occurred. The six cohort/arm reports, functionality summary, run manifest, and package evidence are protected/Git-ignored. Metrics are retrieval-only; no pooled result, robust functionality claim, generated-answer evaluation, or genuine-conflict sensitivity claim is made. The delivery-manifest/raw-XML and model-review limitations remain.

Final local checks: evaluation/offline retrieval suite 195 passed, 0 failed, 0 skipped; Ruff check passed; Ruff format check passed (177 files, one non-fatal cache-write warning); mypy passed for 29 files. See the top-level EVIDENCE.md addendum for actual commands and the protected result manifest.

## Independent review and T008 diagnostic update (2026-11-20)

The owner reports the independent ChatGPT reviewer verified all 84 package
payload hashes, confirmed all six cohort/arm reports, and independently
recomputed macro Recall, Evidence Hit, and MRR from per-question records with
matching results. The reviewer observed identical dense/hybrid metrics and
zero lexical Recall@20 for both held-out cohorts. This does not imply
statistical significance or general superiority.

Read-only code inspection confirmed the fixed lexical implementation uses
PostgreSQL English `websearch_to_tsquery` against `to_tsvector` over chunk text,
`ts_rank_cd`, existing metadata/corpus filters, and top-k 20. It is independent
of query embeddings. Existing integration tests cover deterministic FTS on a
controlled term and an empty stop-word-only query. The stored evaluation
reports do not preserve lexical candidate lists or locator-match diagnostics,
so the exact cause of zero lexical Recall cannot be isolated from existing
artifacts. No question text was inspected for tuning and no retrieval was
rerun.

Limitations: held-out samples are small; Golden v1 did not receive human
verification; original XML is unavailable; genuine-conflict sensitivity was
not measured; and ChatGPT did not independently reproduce PostgreSQL. The
evaluation stores only `retrieval_total` latency statistics and does not label
cold/warm runs or separate retrieval stages. AC-038 is not fully evidenced;
the existing run is not retroactively described as having those measurements.

## T008 lexical probe and coverage update (2026-11-20)

Eight unique source-derived synthetic queries were probed with SQL SELECTs in a PostgreSQL repeatable-read read-only transaction on the exact active frozen corpus. Expected chunk/DOI/locator mappings passed for Apis mellifera (rank 3/48), RNA (19/44), Varroa destructor (3/14), feeding (11/36), a longer single-source natural-language query (1/1), and 10 genes (1/17). A numeric-only 10 query produced 103 candidates and placed its expected source chunk at rank 31, beyond lexical top 20. A long cross-source query generated zero candidates; querytree showed all positive content terms conjoined by AND. No query used Golden content, and no result was used to tune or rerun retrieval. Probe construction and interpretation are tabulated in docs/person2/PHASE_D_RESULTS.md.

The three isolated v1 development questions were scanned without emitting text: 3/3 contained a Latin binomial pattern, 1/3 an uppercase acronym, 0/3 a numeric value, and 2/3 a method/assay term. The exact v0 five-question coverage scan was blocked when the existing allowlist scanners failed closed; no held-out record was decoded, and no v0 lexical-coverage conclusion is made. Existing development questions are smoke cases rather than a systematic lexical stress set. Recommend a separate versioned source-grounded diagnostic-only set before any lexical/hybrid improvement cycle; no set is created or configuration changed here.

A compatible development query-vector cache was not present, so hybrid branch behavior was verified with offline synthetic RRF rank-oracle tests: 9 focused retrieval tests passed. Existing T006 reports preserve metrics and aggregate total latency, not branch candidate lists. Dense/hybrid equality and lexical held-out zero Recall therefore remain observations with no specific causal attribution. AC-038 is partial because cold/warm labels and stage-separated latency were not recorded. The independent ChatGPT reviewer confirmed package hashes and recomputed metrics but did not independently reproduce PostgreSQL. Small cohorts, no human Golden v1 verification, unavailable original XML, and no genuine-conflict sensitivity measurement remain disclosed.
