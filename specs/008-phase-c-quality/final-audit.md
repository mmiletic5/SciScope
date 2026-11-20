# Phase C Final Acceptance Audit - Closed with Documented Exception

**Audit date:** 2026-11-19  
**State:** CLOSED by explicit Person 2 owner acceptance following independent
verification. P3-09..P3-12 and T008 are recorded complete. The historical P3-10
isolation criterion is an approved exception and remains NOT PASSED.

## P3-09 - Ranking, duplicate policy, diversity

**Technical result: PASS.** Phase C consumes existing ordered Phase B hits and
does not recompute dense/lexical scores or RRF. Exact duplicate identity is
`(doi, source_locator, exact text)`, retaining the first Phase B representative;
duplicate chunk IDs and empty identity fields fail. Equal reranker scores use
base rank then lowercase chunk ID. DOI cap defaults to 2, accepts 1-50, and
`None` disables it. Diversity follows optional score ordering and returns
explicit `duplicate_evidence`/`doi_cap` exclusions. Retained hit objects preserve
their source metadata. `test_quality.py`, `test_reranking.py`, and the Phase C
pipeline tests cover the behavior. A characterization regression now proves
malformed `spans` values are not parsed or used by ranking, as required by the
primary-locator duplicate contract.

## P3-10 - Reranking benchmark

**Benchmark result: COMPLETE; candidate outcome: NO-GO; production: DISABLED.**
The offline rerun used identical saved Phase B RRF top-50 candidate lists,
filters (none), labels, cutoffs, active corpus, and embeddings for both arms.
Only four positive questions enter positive macro metrics; the
insufficient-evidence question has no positive references and null positive
metrics. Five warm repetitions per question, cold load, candidate hashes,
per-question denominators, environment, commit, pinned model revision/SHA,
and dependency lock hash are recorded in
`.cache/phase_c_rerank/benchmark-result.json` and the local input artifact.
`benchmark-environment-win-py312.lock` pins the captured 68-package Windows
Python 3.12.16 environment.

Quality gates failed: macro MRR@10 was 0.520833 baseline versus 0.375 reranked;
Evidence Hit@5 was 1.000 versus 0.750. The final combined warm p95 was
3,855.29 ms versus the 1,000 ms cap and 1,081.22 ms (2x RRF p95). Cold load was
523.13 ms. No threshold was changed; the owner accepts MiniLM remaining off.
The offline CLI now separates `--prepare-inputs` from `--run`; `--run` refuses
missing inputs, sets Hugging Face/Transformers offline flags, loads the pinned
local checkpoint, and has no call path to the paid preparer. A test proves
missing inputs fail without calling the preparer. The benchmark was rerun in
this offline mode.

**Historical partition exception: APPROVED EXCEPTION; CRITERION NOT PASSED.** The first input-preparation
version deserialized the full Golden v0 JSON before selecting the five
allowlisted IDs. It did not print, manually inspect, embed, retrieve, score, or
tune on the other 16 records. The loader was fixed to decode allowlisted
question objects only, with a synthetic malformed-nonallowlisted regression
test, and later benchmark reruns reused only the five-record saved artifact.
That cannot undo the initial deserialization. The literal checklist criterion
that the other 16 questions were never loaded/read is not checked as passed.
The owner explicitly approved closure with this documented exception on
2026-11-19. No broader requirement or shared contract was revised.

**Final close-out correction (2026-11-19):** review found that the prior fixed
loader still used `Path.read_bytes()`, which materialized the entire file even
though it deserialized only allowlisted records. That implementation did not
satisfy the current-input streaming boundary. It is now replaced by a bounded
4,096-byte streaming scanner: nonallowlisted record content is discarded
without JSON deserialization, while only allowlisted record objects are
retained and decoded. At most 512 bytes before a record's ID are buffered;
nonallowlisted content after the ID is discarded as scanned. Synthetic tests
cover malformed nonallowlisted JSON, bounded reads, decoder isolation,
duplicate allowed IDs, and the pre-ID buffer bound. The scanner necessarily
reads the file stream to find/check all five IDs; this is distinct from
buffering the file, deserializing held-out records, or using their content.
The historical full-file deserialization remains an approved exception and
this checklist criterion remains NOT PASSED.

## P3-11 - Context and token budget

**Technical result: PASS.** Exact counter identity is required before counting;
selection greedily includes whole passages that fit, skips oversized passages
with explicit reasons while considering later items, includes exact fits, and
never exceeds the supplied evidence-only budget. Returned records and text are
unchanged, with total/budget/counter identity and ordered omissions. Prompt
overhead remains caller-reserved and no Gemini/OpenAI tokenizer is guessed.
Pure behavior coverage is in `tests/retrieval/test_context.py` and the pipeline
regression.

## P3-12 - Evidence lookup

**Technical result: PASS.** DOI normalization reuses the accepted helper;
locator matching is exact/opaque for primary or span locators; lowercase
64-hex chunk IDs select only the active import. Found results carry import ID,
delivery digest, source contract version, and corpus version from the same
read-only REPEATABLE READ snapshot. Native tests cover exact lookups,
not-found/invalid inputs, and `transaction_read_only`/isolation. They used only
preflight-confirmed `sciscope_test_005`.

## Project closure criteria

- Current read-only preflight: PASS 3/3; active pilot 17/319/728/728.
- Current focused retrieval/evaluation tests: 100 passed in 2.15 s.
- Current applicable project regression: 2,687 passed, 2 skipped in 92.67 s;
  migration-capable database/ingestion suites and Golden schema test excluded.
- Ruff check, Ruff format check (230 files), mypy (64 files), compileall, and
  `git diff --check`: pass.
- Final streaming-loader focused run: 22 tests passed in 0.48 s; Ruff check and
  format passed for the runner and regression tests; mypy passed for 64 source
  files; compileall and `git diff --check` passed. The benchmark and database
  were not rerun or accessed for this correction.
- User independently reported preflight PASS 3/3, preserved pilot counts,
  22 focused tests and static checks, and successful reproduction of the
  MiniLM no-go result. The owner explicitly accepted Phase C and approved the
  documented historical exception. The checklist and backlog record the
  disposition without marking the isolation criterion passed.
- The Phase D outline is a separate draft. No Phase D work or held-out access
  occurred during this audit.

## Closure disposition

The acceptance checklist marks technically satisfied criteria as passed and
labels the historical isolation criterion `APPROVED HISTORICAL EXCEPTION — NOT
PASSED`. The owner-provided independent verification and explicit acceptance
meet this private Person 2 feature's documented human-acceptance gate. The
constitution and Phase C plan require owner acceptance but do not require a
mentor or Person 1 approval for closing this internal scope. Person 1 review
remains necessary before making broader shared source-locator stability
claims; no such contract or schema change is included here. Shared
`retrieval.v1` and downstream handoff materials remain proposed and pending
owner review.

P3-09 through P3-12 and T008 are now closed. Phase C stops at this handoff;
Phase D has not started. MiniLM remains disabled after the measured no-go.

## Phase D dependencies identified

Phase D remains unapproved and unstarted. Before its feature spec/plan can be
approved, confirm Person 1's
P1-12/P2-23 Golden design and reference-verification status (their backlog
items remain unchecked); approve partitions, metrics/report format, and any
reranker diagnostic before held-out access; authorize any paid embedding spend
with a hard cap. The Phase D draft is
`docs/person2/PHASE_D_IMPLEMENTATION_PLAN.md`.
