# Phase D Operational Runbook

## Current boundary

T004 is accepted. T005 passed for both cohorts with 22/22 verified query
vectors after explicitly authorized generation. T006 was separately authorized
and completed on the frozen read-only test corpus. T007/T008 reporting,
handoffs, read-only lexical diagnostics, and package review are recorded.
Final owner acceptance remains pending, and AC-038's cold/warm/stage timing
characterization is explicitly partial.

The T005 approval records and detailed identity digests are Git-ignored under
`evals/protected/phase_d_authorizations/`. The embedding-generation receipt
authorizes query-vector generation only and is not T006 authorization. The
protected readiness and usage reports are
`evals/protected/phase_d_t005_readiness_report.json` and
`evals/protected/phase_d_t005_embedding_generation_report.json`.

## Resume sequence

1. T005 passed. Both per-cohort manifests and entries were verified with
   `verify_query_cache_manifest` against dataset, partition, corpus, active
   embedding-set, model/provider/dimension/prefix/dtype, question mapping,
   cache/vector integrity, finite-value, and norm requirements.
2. T006 used the strict T005/T006 approval pair for each cohort and the
   read-only `sciscope_test_005` connection. It ran dense, lexical FTS, and
   hybrid RRF with cached vectors, top_k 20, and two exact-result repetitions.
   No tuning or configuration changes occurred.
3. Cohort-separated reports record per-question metrics, denominators,
   repeated latency, and configuration/environment identity. A protected
   summary also reports descriptive v1 functionality strata; no pooled result
   or functionality-specific performance claim is made.
4. T007/T008: completed reporting/handoffs, protected package hash checks,
   independent metric recomputation review, and read-only lexical diagnostics
   are recorded. The owner retains final acceptance; do not rerun protected
   retrieval as part of routine verification.

## Native Windows authorization-check examples

These commands structurally validate records only; they do not access the
database, protected question text, or vector cache. Paths below refer to
owner-created authorization artifacts and must not be fabricated by an
operator.

```powershell
$env:PYTHONPATH='.;src'
.\.venv\Scripts\python.exe scripts\phase_d_retrieval_evaluation.py `
  --check-preflight-authorization `
  --preflight-authorization evals\protected\phase_d_authorizations\t005_v1-held-out_approval.json `
  --cohort v1-held-out
```

The later T006 structural check requires two separate records:

```powershell
$env:PYTHONPATH='.;src'
.\.venv\Scripts\python.exe scripts\phase_d_retrieval_evaluation.py `
  --check-retrieval-authorizations `
  --preflight-authorization evals\protected\phase_d_authorizations\t005_v1-held-out_approval.json `
  --retrieval-authorization evals\protected\phase_d_authorizations\t006_v1-held-out_approval.json
```

The structural check only validates approvals. The already completed T006
execution command was:

```powershell
$env:PYTHONPATH='.;src'
.\.venv\Scripts\python.exe scripts\phase_d_run_retrieval_evaluation.py --run-authorized
```

The runner now refuses to execute again after a T006 run manifest exists.
