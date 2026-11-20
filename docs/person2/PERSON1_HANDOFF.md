# Person 1 Handoff: Golden v1 and T005 Readiness

**Status:** Person 2 completed T005 query-vector readiness and the separately
authorized T006 retrieval for both frozen held-out cohorts. This handoff is
informational; Person 1 approval is not a dependency for internal Person 2
completion.

## Provenance and evidence

Golden v1 remains the ChatGPT-reviewed, AI-generated/AI-assisted nine-question
Person 2 dataset, with truthful model-review provenance and no claim of
independent human verification. Q4/Q5 remain false-conflict negative controls.
The protected records and source packet have not been rewritten during T005.
The original raw XML was unavailable during curation; source passages and
locators derive from the frozen local pilot delivery, whose manifest remains
marked `draft`.

The v1 partition slots were checked against the protected freeze and separate
partition files. The v0 5-development/16-held-out partition was recomputed
from the approved protocol development allowlist and the 21 IDs in the frozen
v0 dataset. No prior standalone v0 partition-digest manifest is present; the
new deterministic digest and its derivation are recorded in protected T005
authorization/evidence files without changing membership.

The read-only preflight confirmed `sciscope_test_005`, role `sciscope`,
PostgreSQL 17, one active corpus import, counts 17/319/728/728, and the frozen
embedding-set identity. T005 generated and verified 22 query vectors using 3
OpenAI embedding calls (626 prompt tokens; actual cost USD 0.00001252) under
the owner's explicit no-cap authorization. T006 then ran all three frozen
retrieval modes for v0-HO (n=16) and v1-HO (n=6), with two identical-result
repetitions per question/arm. Pre/post database identity and counts matched;
no writes or migrations occurred.

## Follow-up options

The retrieval reports and run manifest are under Git-ignored `evals/results/`
and `evals/protected/`. They distinguish cohorts and answerability
denominators. Original raw XML was unavailable; the source passage and locator
limitations remain as documented. Golden v1 was AI-assisted and received
ChatGPT model review, not human verification.

Detailed results and exact limitations are in
`docs/person2/PHASE_D_RESULTS.md`, the protected run manifest
`evals/protected/phase_d_t006_run_manifest.json`, and the final review package.

## T008 diagnostic and independent review update

The owner reports ChatGPT verified all final-package payload hashes and
independently recomputed macro Recall, Evidence Hit, and MRR with matching
values. The reviewer confirmed six cohort/arm reports, but did not independently
reproduce PostgreSQL. Lexical Recall@20 was zero in both held-out cohorts.
Read-only source-corpus probes show lexical matching can find exact scientific
terms, RNA, Varroa destructor, and a methods term; a numeric-only term had its
expected chunk ranked below top 20, and a synthetic long cross-source query
produced no candidates under English FTS AND semantics. These probes are
diagnostics, not Golden results. The exact held-out zero-recall cause is
unknown because result reports omit candidates and match diagnostics.

The three separately partitioned v1 development records contain no
numeric-value query under the documented feature scan; the five v0 development
records could not be scanned by the existing allowlist utility, which failed
closed, so no coverage claim is made for them. A separate, versioned,
source-grounded lexical/hybrid diagnostic set is recommended before any
improvement cycle. No frozen setting changed. AC-038 is partial: the run has
repeated total-retrieval latency summaries but no cold/warm labels or stage
breakdown.
