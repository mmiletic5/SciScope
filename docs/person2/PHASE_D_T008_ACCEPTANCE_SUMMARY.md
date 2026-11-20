# Phase D T008 Acceptance Summary

**State:** T005–T007 work and T008 evidence preparation are complete. This
summary records evidence status; it does not exercise the owner's final
acceptance authority. Acceptance checklist boxes remain open until that
decision. AC-038 is only partially evidenced by the existing run.

## Criterion inventory

Evidence references below use the detailed checklist at
`specs/009-phase-d-retrieval-evaluation/checklists/acceptance.md`; the listed
artifacts provide the supporting record. Except for AC-038, evidence is
recorded for each criterion. All checkboxes remain open pending final owner
acceptance, rather than implying acceptance from implementation alone.

| Criterion | Evidence status | Evidence |
| --- | --- | --- |
| AC-001 | Recorded | User approvals in protected T001/T002 execution history; checklist. |
| AC-002 | Recorded | `docs/person2/RETRIEVAL_EVALUATION_PROTOCOL.md`; `docs/person2/MASTER_PLAN.md`; decision history; unchanged constitution/shared evaluation plan. |
| AC-003 | Recorded | `docs/person2/PERSON1_HANDOFF.md`; `docs/person2/PERSON3_HANDOFF.md`. |
| AC-004 | Recorded | Protected Golden validation report; `docs/person2/PHASE_D_T004_REVIEW_AND_VERIFICATION.md`. |
| AC-005 | Recorded | Phase D plan/protocol; frozen baseline manifest; T004 review record. |
| AC-006 | Recorded | Protected v1 curation manifest and correction history; T004 review record. |
| AC-007 | Recorded | Protected v1 records/manifest; unchanged Golden schema; T004 review record. |
| AC-008 | Recorded | Protected v1 evidence annotations and validation report. |
| AC-009 | Recorded | Protected schema-validation report; T004 review record; unchanged `evals/golden_questions.schema.json`. |
| AC-010 | Recorded | Protected curation and source-coverage reports; T004 limitation disclosure. |
| AC-011 | Recorded | Protected T004 review ZIP and T004 verification record; raw-XML limitation disclosed. |
| AC-012 | Recorded | Independent ChatGPT T004 decisions Q1–Q9, recorded in T004 review documentation; model review, not human verification. |
| AC-013 | Recorded | Q4/Q5/Q6/Q9 correction provenance and final Q1–Q9 T004 decision record. |
| AC-014 | Recorded | T004 stop and subsequent explicit continuation authorization in execution history. |
| AC-015 | Recorded | Frozen baseline/partition manifest; protected T006 run manifest records no tuning. |
| AC-016 | Recorded | Synthetic partition/isolation tests; protected-data leak audit and package exclusions. |
| AC-017 | Recorded | Golden v0 unchanged; fixed 5/16 partition documented in protocol and protected cohort identities. |
| AC-018 | Recorded | Frozen v1 partition identities and protected T005/T006 manifests. |
| AC-019 | Recorded | T005 cohort approvals, readiness report, and query-cache manifests. |
| AC-020 | Recorded | T005 query-cache manifests and text-free generation/readiness reports. |
| AC-021 | Recorded | T005 vector/cache integrity validation and manifests. |
| AC-022 | Recorded | Fail-closed cache validation tests; explicit embedding authorization and usage report. |
| AC-023 | Recorded | Synthetic matcher tests and `src/sciscope/evaluation/matching.py`. |
| AC-024 | Recorded | Synthetic duplicate/overlap matcher oracles; metric tests. |
| AC-025 | Recorded | Matcher implementation and fallback-boundary tests. |
| AC-026 | Recorded | `tests/evaluation/test_phase_d_matching.py` and independent synthetic oracles. |
| AC-027 | Recorded | `tests/evaluation/test_phase_d_metrics.py`; bounded Recall and duplicate behavior assertions. |
| AC-028 | Recorded | Metric definitions in protocol; metrics tests; six cohort/arm reports. |
| AC-029 | Recorded | Six per-cohort/arm reports and v1 descriptive functionality summary; independent metric recomputation reported by ChatGPT. |
| AC-030 | Recorded with non-claim | Insufficient-evidence denominators/null metrics in reports; blinded false-support adjudication unavailable and explicitly NOT COMPUTED. |
| AC-031 | Recorded | Protected T006 manifest and six dense/lexical/hybrid reports; frozen run config. |
| AC-032 | Recorded | Baseline freeze manifest; T006 run manifest; reranker remains disabled. |
| AC-033 | Recorded | Separate v0 n=16 and v1 n=6 reports; no pooled result; small-sample limitations. |
| AC-034 | Recorded | Separate cohort-bound T005/T006 approval evidence and strict validator results. |
| AC-035 | Recorded | T005/T006 read-only pre/post database evidence for `sciscope_test_005`. |
| AC-036 | Recorded | T005/T006 read-only corpus counts and identity in readiness/run reports. |
| AC-037 | Recorded | Protected run manifest, cohort reports, `EVIDENCE.md`; package manifest/hashes. |
| AC-038 | **Partial** | Reports include repeated `retrieval_total` median/p95/max, but do not label cold/warm observations or separate retrieval stages. No missing characterization is inferred. See `docs/person2/PHASE_D_RESULTS.md`. |
| AC-039 | Recorded | T005 cache validation; T006 read-only pre/post checks; deterministic repeated ranked results; independent metric recomputation. |
| AC-040 | Recorded | Results and Person 1/Person 3/Phase E handoffs; provenance, cohort, small-sample, raw-XML, and non-claim disclosures. |
| AC-041 | Recorded; acceptance open | `EVIDENCE.md` and `PROJECT_TODO.md` report actual outcomes and retain final acceptance as open. |
| AC-042 | Recorded | `EVIDENCE.md` exact Windows commands/results; independent ChatGPT package/hash/metric review; user retains final acceptance. |
| AC-043 | Recorded | Git diff/status and execution evidence; Phases A–C, production database, shared schemas/contracts, and disabled reranker preserved. |
| AC-044 | Recorded | T005/T006 authorization, identity, read-only and leak evidence; no additional protected run attempted. Latency evidence gap is disclosed. |
| AC-045 | Recorded | T004 review gate and subsequent explicit continuation authorization; synthetic framework work preceded protected retrieval. |
| AC-046 | Recorded | Pre-generation baseline freeze and protected manifest. |
| AC-047 | Recorded | Functionality sidecar schema/validator and Person 3 handoff; no shared contract change. |
| AC-048 | Recorded | Protected v1 validation/manifests; Golden v0 unchanged; v1 remains `in_review` with truthful model-review provenance. |
| AC-049 | Recorded with procedural limitation | Protected workflow/leak audits, Git ignores, T006 manifest and final-package exclusion audit. Isolation is procedural, not OS-enforced. |

## Independent review evidence and limitations

The owner reports the independent ChatGPT reviewer verified all 84 ZIP payload
hashes, confirmed the six cohort/arm reports, and independently recomputed
macro Recall, Evidence Hit, and MRR from per-question results with matching
values. The reviewer observed identical dense/hybrid retrieval metrics and
zero lexical Recall@20 in both held-out cohorts. ChatGPT did not independently
reproduce PostgreSQL.

Remaining scientific and technical limits are small held-out cohorts (v0
n=16, v1 n=6), no human Golden v1 verification, unavailable original raw XML,
no genuine-conflict sensitivity measurement, no answer-generation quality
evaluation, and no cold/warm or stage-separated latency characterization.
The delivery manifest remains `draft`. These limitations are disclosed; they
do not justify tuning the frozen baseline after viewing held-out outcomes.

## Read-only lexical diagnostic

The frozen lexical path applies PostgreSQL English
`websearch_to_tsquery` to query text and `to_tsvector('english', Chunk.text)`
to corpus chunks, filters by the active corpus and request filters, ranks with
`ts_rank_cd`, and returns at most top-k 20. It does not use query embeddings.
The strict evaluation matcher requires normalized DOI plus an exact source
locator/span, with only the preregistered same-section and exact-quotation
fallback. Existing PostgreSQL tests verify deterministic English FTS for a
controlled term and an empty result for an English stop-word-only query.

Saved evaluation reports contain metrics and total latency, but no lexical
candidate lists, candidate counts, or per-result match diagnostics. Therefore
the existing evidence cannot determine whether zero lexical Recall arose from
empty FTS candidate sets or candidates that did not match annotated evidence
units. Protected questions/results were not reopened for tuning and retrieval
was not rerun. No configuration change is proposed; lexical zero Recall is an
observed result and limitation.

## Owner decision

The diagnostic recommends deciding whether to initiate a separate versioned,
source-grounded lexical/hybrid diagnostic cycle. This summary does not authorize
that cycle or alter the current baseline. The owner must record that decision
before T008 can be marked accepted. AC-038's limitation remains explicit; no
additional protected evaluation is authorized by this summary.

## T008 verification commands

Native Windows PowerShell, Python 3.12 `.venv`, `PYTHONPATH=.;src`:

```powershell
$env:PYTHONPATH='.;src'
.\.venv\Scripts\python.exe -m pytest tests/evaluation tests/retrieval -q -p no:cacheprovider --ignore=tests/retrieval/test_postgres_core.py --ignore=tests/retrieval/test_postgres_lookup.py -k 'not test_lookup_ranking_and_context_keep_exact_snapshot_evidence'
.\.venv\Scripts\ruff.exe check src tests scripts
.\.venv\Scripts\ruff.exe format --check src tests scripts
.\.venv\Scripts\mypy.exe src/sciscope/evaluation src/sciscope/retrieval src/sciscope/database scripts/phase_d_run_retrieval_evaluation.py scripts/phase_d_generate_query_vectors.py scripts/phase_d_package_review_evidence.py
git diff --check
```

Recorded current results: pytest 195 passed, 1 database-dependent case
deselected, exit 0; Ruff check passed; Ruff format check passed for 177 files
with a non-fatal cache-write warning; mypy passed for 30 source files;
`git diff --check` passed with only existing CRLF normalization advisories.
The 13 PostgreSQL integration tests were not rerun in this T008 update; the
earlier accepted T004 results and T006 read-only execution evidence remain the
database verification record. One initial offline invocation had a setup
error for a database-dependent Phase C lookup test; a subsequent invocation
without the PostgreSQL ignores had 12 expected fixture-setup errors. The
successful command above excludes the two PostgreSQL integration modules and
the remaining database-fixture lookup case; it does not claim those tests
passed in this turn.

## Subsequent Windows manual verification record

The preceding status is historical and is superseded for native Windows test
execution by the completed manual verification run at
`evals/protected/phase_d_final_review/manual_verification/20261120T121510Z/`.
That run passed 195 offline evaluation/retrieval tests (one database-only
Phase C case deselected), 9 focused lexical/RRF tests, and all 13 inspected
read-only PostgreSQL retrieval integration tests. Ruff check/format, mypy,
saved artifact and corpus-payload hashes, 90 aggregate metric recomputations,
two query-cache manifest checks, eight read-only lexical probes, synthetic RRF
oracle comparison, and database pre/postflight all passed. Exact commands and
exit codes are in the machine-readable run summary and log.

This updates the verification record only. It does not close T008 or AC-038.
AC-038 remains partial because the saved run lacks cold/warm labels and
embedding/database/fusion-stage timings. No held-out retrieval was rerun.
Final owner acceptance and the decision about a separate lexical/hybrid
improvement cycle remain pending.
