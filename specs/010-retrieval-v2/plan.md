# Implementation Plan: Retrieval v2 BM25 and Reranking

**Branch**: `010-retrieval-v2` | **Date**: 2026-11-20 | **Spec**: [spec.md](spec.md)

**Status**: Approved for implementation by owner on 2026-11-20.

## Summary

Preserve all v1 behavior. Add an opt-in v2 lexical path using `rank-bm25` BM25Okapi against active chunk texts and a v2 hybrid path combining it with dense retrieval through existing RRF. The existing pinned MiniLM adapter is independently configurable at service construction and reranks the full candidate pool when enabled, before final top-k and existing context-token selection. Compare reranked and unreranked v2 plus v1 only on the approved development population (at most eight questions); do not inspect protected cohorts. Execution note: only the five previously approved Golden v0 development vectors were present in the compatible local artifact, so the completed comparison uses those five and does not generate the three planned Golden v1 development vectors.

## Technical Context

**Language/Version**: Python 3.12, native Windows PowerShell.  
**Primary Dependencies**: pinned `rank-bm25`; existing `sentence-transformers`/CPU PyTorch; `ir-measures` with compatible `pytrec-eval-terrier` wheel for nDCG verification.  
**Storage**: existing read-only PostgreSQL 17/pgvector frozen snapshot; no schema/migration.  
**Testing**: test-first pytest; synthetic BM25/RRF/rerank oracles, read-only `sciscope_test_005` integration only after safety preflight; Ruff, format, mypy.  
**Target Platform**: native Windows 10 x64 and existing `.venv`.  
**Performance**: measure, do not predeclare an improvement target; report BM25 build/query and reranker timing separately and compare same candidates and settings.  
**Constraints**: protected holdouts inaccessible; no paid API, DB mutation, or v1 changes; offline inference with pinned local model.

## Constitution Check

- Spec/research/plan before implementation: completed; owner approval received 2026-11-20.
- Tests first, failing behavior demonstrated before implementation.
- Shared interface: owner approved additive `retrieval.v2`; keep current strict v1 contract unchanged. Person 3 application integration remains gated on their approval.
- Native Windows, no paid services, DB read-only, no secret exposure.
- Record actual commands and outcomes in `EVIDENCE.md`; keep `PROJECT_TODO.md` synchronized; do not close before independent user verification.

## Proposed Interface Decision (approval required)

Approved path: use `contract_version: "retrieval.v2"` to select the v2 profile; keep the existing request/response field shape and `dense`, `lexical`, `hybrid` mode names. Under `retrieval.v2`, `lexical` means BM25Okapi and `hybrid` means dense + BM25Okapi + existing RRF. Reranker selection is an internal Person 2 service-construction setting, not a new request field; compare both no-op and MiniLM arms. `retrieval.v1` remains behavior compatible. The owner approved the versioned contract on 2026-11-20; do not modify Person 3 code or enable v2 in their app without their integration approval.

## Architecture and flow

```text
same validated dev query / active read-only snapshot
  ├─ existing dense top candidate pool
  └─ BM25Okapi over active filtered chunk texts
          ↓
existing RRF over branch ranks, deterministic unique chunk IDs
          ↓ bounded merged union
existing MiniLMCrossEncoderReranker (pinned local checkpoint)
          ↓
existing stable ranking / final top-k / token-budget selection
```

BM25 index is in-memory for the request or cached only with an explicit corpus/import identity key; no persistent index and no cache of protected question content. Apply identical eligible corpus/filter constraints. Reranker scores may determine order only; chunk identity, source provenance, and DOI stay sourced from the database snapshot. Any requested reranker error fails explicitly; no baseline fallback.

## Planned file changes

- Modify `src/sciscope/retrieval/_core.py` to add private v2 branch orchestration and preserve the v1 path.
- Modify `src/sciscope/retrieval/_validation.py` only for the approved v2 selector/version boundary; retain v1 strictness.
- Add `src/sciscope/retrieval/_bm25.py` as minimal `rank-bm25` adapter with stable chunk mapping, tokenization policy, and deterministic ties.
- Reuse `src/sciscope/retrieval/_ranking.py`, `_reranking.py`, `_quality.py`, and existing token-budget selector; only minimal integration changes.
- Add evaluation adapter/runner under `src/sciscope/evaluation/` or `scripts/` only after confirming existing runner reuse.
- Add focused tests under `tests/retrieval/` and `tests/evaluation/`; no Golden record changes.
- Add optional locked dependencies to `pyproject.toml`/`uv.lock` only after Windows resolution verification.
- Add a v2 run manifest/report under Git-ignored `evals/protected/` or `evals/runs/` according to current data-handling policy; no protected questions/results in tracked files.
- Update `docs/person2/` v2 runbook/results and `EVIDENCE.md`, `PROJECT_TODO.md`; preserve Phase C/D historical evidence.
- Shared contract and Person 3 handoff files only after explicit contract approval.

## Dependency and download gates

1. Feature spec/plan and additive shared `retrieval.v2` contract approved by owner on 2026-11-20.
2. Resolve/test `uv` through the installed trusted executable without bypassing Windows controls.
3. Install only pinned, free dependencies after approval. `rank-bm25` is a small universal wheel; `ir-measures` has a CPython 3.12 Windows wheel via `pytrec-eval-terrier`.
4. Model cache was absent. Owner approved downloading the approximately 90.9 MB `model.safetensors` plus required tokenizer/config files at a pinned immutable model revision; verify SHA-256 and license. No runtime auto-download.
5. Reuse only existing compatible query vectors/candidate artifacts; do not generate embeddings. If actual candidate generation requires absent query vectors, stop and seek separate approval rather than use paid calls or substitutes.

## Ordered tasks

| ID | Task | Dependencies | Deliverables and acceptance | Estimate |
|---|---|---|---|---:|
| V2-01 | Approve specification, plan, and v2 selection/interface route | Owner approval | Decision recorded; no contract touched before approval | 10 min |
| V2-02 | Resolve native dependency/tool readiness | V2-01 | Exact pinned dependency resolution; verified uv; no unauthorized download | 20–45 min |
| V2-03 | Write failing synthetic contract/BM25/RRF/rerank tests | V2-01 | Tests cover empty corpus, duplicate/ties, filters, score validation, rank union, v1 unchanged | 45–75 min |
| V2-04 | Implement minimal BM25Okapi adapter | V2-03 | Active corpus/filter mapping and deterministic scores/order pass tests | 45–75 min |
| V2-05 | Integrate v2 hybrid and rerank order | V2-04, approved selector; checkpoint authorization | Full RRF union is reranked before top-k/token budget; no v1 changes | 60–100 min |
| V2-06 | Implement/reuse development comparison harness | V2-05 | Per-question/macro metrics, DOI attribution, latency, config manifest; n≤8 dev only. Completed run uses n=5 because only those approved cached vectors were available; do not fill the gap with generated vectors without authorization. | 45–75 min |
| V2-07 | Run development comparison, regression, and read-only integration | V2-02..06; existing DB authorization | Actual before/after, no holdout access, pre/post DB invariants | 60–100 min |
| V2-08 | Fix, document, package handoff, independent owner verification | V2-07 | Quality checks, exact evidence, v1 unchanged, independent PowerShell output | 45–75 min |

Estimates total 5–8 hours excluding model/dependency downloads, uv repair, model cold initialization, failed test debugging, or DB outage. The user prioritizes a working deliverable before 18:00 CET; actual feasibility depends on execution time and measured development-set results.

## Verification and safety

- Unit: independent toy-corpus oracle for Okapi scores/ranks, BM25/RRF union/ties, reranker input order and output validation, top-k-after-rerank, tokenizer budget ordering, filters, DOI/source provenance.
- Integration: native Windows read-only test DB; confirm database identity `sciscope_test_005`, frozen corpus and 17/319/728/728 counts before/after; no writes.
- Regression: complete existing retrieval/evaluation tests, Phase A–C relevant checks, Ruff, formatter, mypy; explicitly compare v1 output serialization/rank results to pre-change fixtures.
- Evaluation: only allowlisted development IDs; same frozen query, gold, filters, corpus/config for both arms; per-question results; no tuning loops or model selection using held-out information.
- Stop on corpus drift, missing vector/candidate prerequisites, model/package hash mismatch, unsafe DB fixture behavior, v1 regression, protected-data exposure, shared contract not approved, or any requirement for paid APIs/database writes.

## Risks and non-claims

Eight questions are a small, previously exposed development set; selection can overfit them. Development results are diagnostic only. Phase C's negative MiniLM finding remains historical evidence. nDCG is new and must have independently checked relevance/denominator semantics. BM25 tokenization and English-only behavior may underperform domain abbreviations or multilingual content. No held-out performance, significance, broad scientific generalization, or production superiority claim is permitted.

## Handoff

If the versioned interface is approved, provide Person 3 the request selection/version, unchanged response shape, operational requirements, typed errors, model/runtime requirements, example, and compatibility/regression evidence. No Person 3 code is included absent its owner integration acceptance.

Implementation and measured development results are documented in
[`../../docs/person2/RETRIEVAL_V2_RESULTS.md`](../../docs/person2/RETRIEVAL_V2_RESULTS.md)
and the Person 3 interface handoff in
[`../docs/person2/RETRIEVAL_V2_PERSON3_HANDOFF.md`](../../docs/person2/RETRIEVAL_V2_PERSON3_HANDOFF.md).
The code and local checks are complete; v2 application enablement and final
owner acceptance remain pending.
