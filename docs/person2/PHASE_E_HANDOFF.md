# Phase E Handoff: Person 2 Retrieval Evaluation

**Status:** Handoff prepared after T005 readiness and explicitly authorized
T006 retrieval. Phase D awaits independent technical review and final user
acceptance.

Person 2 preserved the frozen corpus identity
`pilot17-xml-1fff1573b610`, `sciscope_test_005`, the accepted dense/lexical/hybrid
RRF settings, and the disabled MiniLM decision. The read-only database
preflight passed. T005 generated and verified all 22 query vectors across
v0-HO and v1-HO, with actual provider usage/cost recorded in protected
reports. A separate T006 approval authorized the frozen dense, lexical, and
hybrid retrieval arms; results are preserved separately by cohort.

Retrieval metrics and latency are available in the Git-ignored cohort reports.
They are retrieval-only results and make no answer-quality claims. The
required macro metric definitions and population rules remain in
`specs/009-phase-d-retrieval-evaluation/plan.md`; the current measured status
is in `docs/person2/PHASE_D_RESULTS.md`. Q4/Q5 remain Conflict Finder
false-conflict negative controls; Golden v1 does not measure genuine-conflict
sensitivity.

Before Phase E relies on the retrieval estimate:

1. Review the independent T004 source-review limitations and T005/T006
   evidence package.
2. Keep v0-HO (n=16) and v1-HO (n=6) separate; any pooled result is optional
   descriptive only and was not produced.
3. Treat v1 functionality strata as descriptive scenario coverage, not a
   robust function-specific estimate. Golden v1 does not measure genuine
   conflict detection sensitivity.

This handoff is descriptive; it is not an evaluation result or a shared
contract change.

## T008 lexical/hybrid diagnostic evidence

Read-only diagnostics used only public frozen-pilot source chunks to form
queries. Exact scientific terms, RNA, feeding, and named entities retrieved
their expected source chunk; a numeric-only query's expected chunk ranked 31
and fell outside top 20. A long cross-source query produced zero candidates,
and PostgreSQL's `querytree` showed the positive lexemes connected with AND. A
longer single-source query retrieved its expected chunk. Thus lexical FTS works
for controlled terms, while long query composition and the fixed cutoff can
exclude relevant chunks in these synthetic probes. No held-out question/result
was opened, no configuration was selected, and retrieval was not rerun.

RRF unit tests with independent rank oracles show dense-only, lexical-only,
overlapping, and deduplicated chunk candidates pass through deterministic
fusion. The three v1 development questions have sparse numeric-query coverage
(0/3); the five v0 development records could not be safely scanned by the
existing allowlist utility, which failed closed. The development set is not a
purpose-built lexical stress set for exact terms, acronyms, numeric values and
units, methods, named entities, and long multi-concept questions. Recommend a
separate versioned, source-grounded diagnostic-only set before a
lexical/hybrid improvement cycle. This does not alter Golden or the current
baseline. AC-038 remains partial: no cold/warm labels or stage-separated
latency was recorded.
