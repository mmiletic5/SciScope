# Implementation Plan: Phase C Retrieval Quality and Evidence Selection

**Branch**: `008-phase-c-quality` | **Date**: 2026-11-19 | **Spec**: [spec.md](spec.md)

**Status**: Approved for implementation on 2026-11-19, subject to the approved refinements recorded in the spec and this plan.

**Execution correction and benchmark result (2026-11-19):** use only the repository-local `.venv\Scripts\python.exe` (Python 3.12.16), not system Python or uv. The fail-closed read-only preflight passed for `sciscope_test_005` and active pilot counts 17/319/728/728. The optional MiniLM runtime/checkpoint and five-question inputs were subsequently installed/acquired/generated under the approved constraints. The actual pinned-model benchmark completed; its quality and warm-latency gates failed. Keep production reranking disabled and record the exact result in `EVIDENCE.md`. Independent feature acceptance remains open.

## Summary

Compose a private Phase C post-processing layer after the accepted Phase B result: exact returned-evidence duplicate suppression, deterministic ranking/diversity, optional local reranker interface and diagnostic benchmark, exact-tokenizer context selection, and exact active-snapshot evidence lookup. Keep Feature 007, Phase A schema/data, and the proposed public `retrieval.v1` facade unchanged.

## Architecture

```text
accepted private Phase B retrieve(query, options)
  -> unchanged ordered base candidates (RRF remains solely Phase B-owned)
  -> Phase C exact returned-evidence duplicate suppression
  -> no-op default OR explicitly selected reranker
  -> stable reranker/base tie ordering
  -> deterministic per-DOI diversity cap
  -> optional exact-tokenizer whole-passage context selection

accepted active Phase A snapshot
  -> private read-only REPEATABLE READ lookup by DOI / (DOI, locator) / chunk ID
  -> exact stored values + captured delivery/corpus provenance

five approved smoke questions + unchanged candidate pool
  -> RRF-only versus pinned local CrossEncoder reranking
  -> match/metric and latency report + immutable run manifest
  -> recommendation only; production remains disabled without separate approval
```

Do not add a general `retrieval.v1` facade field or mutate the shared draft. Phase C private dataclasses/protocols consume the private Phase B response/result shapes; any future wire exposure waits for P1-11/P1-14 and affected-owner review.

## Technical Context

**Language/Version**: Python 3.12; PowerShell 7/Windows PowerShell-compatible commands.  
**Primary Dependencies**: Existing application dependencies; proposed optional Sentence Transformers/PyTorch for benchmark adapter only, version-locked after Windows rehearsal.  
**Storage**: Existing PostgreSQL 17 / pgvector 0.8.7 tables, no schema change.  
**Testing**: pytest unit/contract tests first (RED), then existing real PostgreSQL tests on verified `sciscope_test_005`; full relevant regression, Ruff, format, mypy, compile.  
**Target Platform**: Native Windows 10 x64, PowerShell, Python 3.12/uv. No Docker, WSL, Linux, or Bash.  
**Project Type**: Python library/private service components and offline CLI benchmark tooling.  
**Performance Goals**: Reranker screen gate as FR-009: warm p95 <= 2x RRF-only ranking p95 and <= 1,000 ms on recorded reference machine; cold load reported separately. Context and lookup correctness have no arbitrary latency target.  
**Constraints**: Exact Phase B behavior preserved; no paid calls; benchmark offline after artifact acquisition; pilot data and Phase A/B evidence preserved; no migrations or main DB access; five Golden IDs only.

## Constitution Check

- Research before final specification and tests: satisfied by this `research.md`.
- Explicit spec/plan approval before code: required; still pending.
- Test-first and observed RED before implementation: required.
- Research provenance and held-out isolation: covered by run manifest and fixed five-question input allowlist.
- Shared contract and owner boundaries: new behavior stays private; no unreviewed facade edits.
- Native platform, least-privilege database, no paid calls: explicitly constrained.
- Human acceptance and `EVIDENCE.md`/`PROJECT_TODO.md` updates: required before tasks can be closed.

## Exact component contracts and defaults

### Ranker

- Input is a unique ordered sequence of Phase B results; retain immutable `base_rank` as one-based input position. Do not change the accepted private `_Hit`, query, or Feature 007. Do not call `_ranking.py` or recompute RRF in Phase C.
- Exact duplicate evidence key: `(doi, source_locator, text)` using exact values already present in each `_Hit`. Repeated `chunk_id` and missing required fields are errors. Within each duplicate group retain lowest `(base_rank, chunk_id.lower())`. This identifies exact repeated returned evidence; it does not claim to deduplicate partial overlaps whose text/locator differ.
- `NoOpReranker` returns input IDs/order and no synthetic score. `DeterministicFakeReranker` uses an injected ID->finite score mapping. Optional protocol accepts query + ordered `(chunk_id,text)` and returns one score for every candidate. Validate exact set and cardinality; rank score descending, then base rank ascending, then lowercase chunk ID.
- Diversity runs after optional reranking, max 2 selected evidence units per normalized DOI by default, in order. `max_per_doi=None` explicitly disables the cap; integer 1–50 sets it. Record deterministic omission reason `doi_cap`. Do not relax cap when paper count is low.

### Benchmark

- Candidate input is exactly Phase B's first 50 RRF candidates (or all available if fewer) per question; dedupe must not cause candidate refill from deeper Phase B retrieval. Reranker only permutes these IDs.
- Compare RRF order versus reranked order on same five question IDs, corpus digest, query text, matching function, filters, candidates, and K. Include per-question type and denominators. Use current protocol's evidence matching and Recall@K / Evidence Hit@K / applicable MRR.
- Freeze model repository, immutable revision, checkpoint hash, package lock, CPU/thread/batch settings before first scored run. Smoke set may validate wiring only; no parameter/model search using its outcomes.
- Record source commit, corpus/delivery hash, exact five IDs + question-file hash, candidate IDs/hash, filters, matching revision, model revision/weight SHA-256, dependency versions/lock hash, OS/build/hardware, CPU thread count, command, timestamp, offline flag, repetitions, cold-load and warm inference durations, median/p95/max/failures, all metrics and counters.
- Warm latency repetitions: 5 full fixed smoke-set passes after one unscored warm-up; report each pass and aggregate median/p95. Cold model-load is timed once and reported separately. Query embedding/DB latency remains the same shared Phase B candidate generation and is separately recorded or excluded consistently for both arms.
- **Candidate input blocker:** no compatible cached query vectors or stored five-question hybrid RRF candidate lists are recorded in the repository. The pilot query embedding identity is OpenAI `text-embedding-3-small`; Phase C cannot create those vectors with a paid/live call. A measured reranker quality comparison therefore requires an existing compatible offline candidate artifact or explicit authorization of a non-paid source of vectors. Do not fake hybrid candidates or substitute an embedding model. Independent implementation and harness work can proceed after spec approval, but T004's scored comparison remains blocked until this input exists.
- FR-009 thresholds are diagnostic screening criteria only. Latency is bounded as a measured reranker cost, not claimed to improve total RAG latency. No phase claim of statistical significance is made from n=5. A passing diagnostic enables only a recommendation for separate review; production remains disabled.
- Network disabled for benchmark execution. If checkpoint/dependency unavailable, record blocker and still complete no-op/benchmark protocol tests; do not substitute a different model without approval.

### Context selection

- Input: post-diversity evidence sequence; explicit integer `budget_tokens >= 0`; injected immutable counter with `counter_id`; expected downstream `counter_id` must match exactly.
- One pass in rank order; use `TokenCounter.count(text)` on exact original text only. Include item when `cost <= remaining`; else omit as `exceeds_remaining_budget` and continue. Zero-token count is permitted for deterministic fake tests, but production counter returning nonpositive for nonempty text is an error.
- Return selected original records, exact counted total, input budget, `counter_id`, and ordered omissions with ID/reason/cost. Caller allocates system/prompt overhead before setting evidence budget. No truncation.

### Lookup

- Private API paths: `get_paper(doi)`, `get_by_locator(doi, source_locator)`, and `get_chunk(chunk_id)`. All read-only.
- DOI uses Phase B accepted normalization; locator is required nonempty valid Unicode string and exact opaque equality; chunk ID must match `[0-9a-f]{64}` exactly.
- Locator query matches `chunks.source_locator == locator OR any spans element has exact source_locator`; combine with DOI and captured active import. Sort all locator results by `chunk_id ASC`. DOI and chunk lookups return 0/1 record. Never return rows from inactive imports.
- Open one transaction in read-only `REPEATABLE READ`, capture active import and digest once, query target and provenance in that snapshot, and close. Return provenance on all found results. Not found is a typed `NOT_FOUND` result; invalid selector is `INVALID_REQUEST`; database/invariant failure is typed internal error. No fuzzy matching or fallback.

## Data and compatibility

No new database entity or column is needed. Read existing `Paper`, `Section`, `Chunk`, and active `DeliveryImport` fields. Persist benchmark manifests/reports as JSON under `evals/runs/` only after explicit implementation approval; generated benchmark outputs must not contain query/passages/secrets beyond the already supplied eval fixture references. No write to the pilot database is needed for lookup; PostgreSQL integration fixtures must rollback.

Potential private files (final exact paths subject to task approval; no Feature 007 file is changed):

```text
src/sciscope/retrieval/_quality.py       # ranker, duplicate policy, diversity
src/sciscope/retrieval/_reranking.py     # protocol, no-op, fake, validation
src/sciscope/retrieval/_context.py       # token counter protocol and selector
src/sciscope/retrieval/_lookup.py        # snapshot-scoped selectors
src/sciscope/evaluation/rerank.py        # offline benchmark and manifest
tests/retrieval/test_quality.py
tests/retrieval/test_reranking.py
tests/retrieval/test_context.py
tests/retrieval/test_lookup.py
tests/retrieval/test_postgres_lookup.py
tests/evaluation/test_rerank_benchmark.py
```

These are proposed targets only; no files created yet.

## Dependency and approval matrix

| Work item | Internal implementation independent? | Shared dependency/blocker |
|---|---|---|
| Exact returned-evidence dedupe, stable order, diversity | Yes after Phase C approval; relies on accepted Phase B result only | Owner approval of proposed duplicate key and cap; no external owner blocks private implementation |
| No-op/fake reranker contracts and validator | Yes | Feature approval; no new runtime dependency |
| Local reranker benchmark adapter | Adapter/benchmark harness yes; measured model run only after locally pinned weights and locked native-compatible packages | User approval of candidate/model and dependency group; verify local checkpoint availability and Windows install |
| Five-question hybrid candidates | No current compatible precomputed artifact was found; offline harness can be developed | Compatible cached OpenAI query vectors and saved Phase B candidate lists, or explicit non-paid compatible source; paid/live embedding is out of scope |
| Token selection core | Yes with injected token counter | Downstream generator must supply/approve exact counter identity before production wiring; no facade change |
| DOI/locator/chunk internal lookup | Yes using existing schema | Person 1 review before making any broader source-locator stability claim; no schema change |
| Public DTO/API exposure | No | P1-11/P1-14 plus Person 3 and affected-owner review; remains outside Phase C plan |

## Implementation Order

1. **Preflight (no mutation):** inspect environment, dependency lock, accepted working tree, pilot counts/evidence references, and target DB identity read-only. Confirm no pending Feature 007 edits. Do not retrieve held-out Golden records.
2. **Ranking contracts and tests (P3-09):** create independent oracle fixtures; observe RED; implement exact returned-evidence dedupe, stable sort, cap, exclusion reports; run focused pure tests.
3. **Reranker interface and benchmark harness (P3-10):** add no-op/fake and protocol validation tests, then benchmark loader/manifest/metrics/latency tests. Keep dependency optional and reranker disabled. Verify only fixed five IDs are loadable.
4. **Offline candidate/checkpoint feasibility gate:** confirm compatible precomputed five-question query vectors and Phase B hybrid candidate lists exist without paid calls; then verify Python 3.12/Windows 10 package compatibility and local checkpoint identity. If any required artifact/dependency is unavailable, record the blocker and keep the benchmark harness/no-op only; do not substitute a model or vector source. Run the benchmark with network disabled only after this gate.
5. **Context budget selection (P3-11):** define counter interface and tests first; implement ranked-order greedy whole-item selection and exact counter identity enforcement.
6. **Snapshot evidence lookup (P3-12):** pure selector validation/oracles first, then real PostgreSQL lookup integration on verified `sciscope_test_005`; use read-only transactions and rollback-scoped fixture setup only if writes are necessary.
7. **Integration regression:** chain Phase B result -> quality layer -> context; verify provenance unchanged, exercise lookup and concurrent snapshot visibility where safe. No public contract, schema, or Phase B modifications.
8. **Evidence and acceptance:** relevant full regression/static/native database checks, reconcile 17/319/728/728 read-only, update `EVIDENCE.md` and backlog statuses (leave unchecked pending user acceptance), provide user read-only PowerShell independent verification and await output/explicit acceptance.

## Verification Strategy

- Pure tests use independent order, duplicate-key, token sum, and lookup identity oracles; include ties, identical and distinct DOI/locator/text tuples, NaN/Inf, exact-fit/one-over, Unicode, missing IDs, and deterministic repeats.
- Contract/benchmark tests patch network/model loading to fail if called, validate offline manifests and enforce exact five-ID allowlist. Add a test that the 16 IDs cannot be loaded through the Phase C harness without reading the held-out records.
- PostgreSQL tests validate DOI, primary locator, span locator, chunk ID, unknown/stale IDs and snapshot consistency against exactly verified `sciscope_test_005`. No schema migration. Never query or mutate `sciscope`.
- Native checks use PowerShell plus `uv run --locked`; final commands and outcomes go in evidence. No tests are to be run during this planning checkpoint.
- Human acceptance is distinct from passing automated tests and must be recorded before marking tasks complete.

## Risks and mitigations

- **Small diagnostic n:** Five questions cannot establish general reranker quality. Keep thresholds only as a screening rule; reserve 16 for Phase D and require later broader held-out evaluation before adoption.
- **Latency/hardware variation:** record exact reference machine/runtime and separate cold from warm; no extrapolation to production hardware.
- **Model artifact drift:** pin revision and hash; no online auto-update; offline run fails on mismatch.
- **Tokenizer mismatch:** require explicit matching identity and leave contract exposure gated.
- **Locator semantics:** exact persisted string and spans only; do not parse opaque locator syntax or promise cross-delivery stability beyond recorded digest.
- **Existing working tree may contain unrelated edits:** inspect and preserve; do not reset/overwrite.

## Non-goals

No Phase A/B reimplementation or code change; no RRF changes; no DB migration/index; no model training or prompt/model sweep; no public retrieval.v1 fields/endpoints; no 16 held-out question access; no pilot expansion or re-embedding; no provider/network-paid inference; no main database changes; no commit/push/MR.

## Approval gates

1. **Satisfied 2026-11-19:** user approved Phase C spec/plan and settled duplicate key, configurable cap/default/disable, benchmark approach and diagnostic thresholds, bounded-latency interpretation, tokenizer injection, lookup semantics, and downstream proposed handoff scope.
2. Before optional model execution, verify the already available local dependency/checkpoint identity. Do not download packages or weights; if unavailable, complete independent components and report the precise blocker.
3. Before shared facade exposure, receive applicable P1-11/P1-14 and affected-owner review.
4. Before marking any Phase C deliverable accepted, automated checks and independent human verification are complete.

## Current execution status

Repository and architecture decisions are approved; execution is blocked before T001's observed RED gate because the approved Python/uv environment cannot run under the current host execution policy. Do not use Python 3.10, install alternate packages, download dependencies/model weights, bypass the execution restriction, or contact a database without an executable approved runtime and the existing database test fixture's successful identity preflight.
