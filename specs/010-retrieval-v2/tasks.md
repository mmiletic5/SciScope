# Tasks: Retrieval v2 BM25 and Reranking

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md)

**Status**: Owner approved 2026-11-20. Implementation active; only evidence-backed tasks may be marked complete.

## Approval and setup

- [x] V2-01 Approve this spec/plan and decide the v2 Person 3 selection boundary. Exact acceptance: written owner decision; v1 stays unchanged. Evidence: explicit owner approval 2026-11-20.
- [x] V2-02 Verify native uv and resolve pinned Python 3.12 dependencies. Exact acceptance: dependencies import in the approved `.venv`, user-verified `uv run --locked` works, no host-control bypass. Evidence: user verification plus local imports for `rank-bm25`, `ir-measures`, and `sentence-transformers`; direct uv invocation from this agent process remains denied by Windows, so no bypass was attempted.
- [x] V2-03 Download and verify the approved model checkpoint. Exact acceptance: immutable revision, required files, directory hash, network-disabled load. Evidence: revision `233902d25c440f23af6f7d6e94d2946bac0bee0a`, directory SHA-256 `402c3a69514c2ccb83898cef29bdf468ec79da80fa091d9967b2de03e7e4adc0`, CPU inference passed with offline flags.

## Tests first

- [x] V2-04 Add failing tests for v1 invariance, v2 request validation, BM25 rank oracle, eligible filters, deterministic ties and empty results. Evidence: `tests/retrieval/test_validation.py`, `test_v2_bm25.py`; included in the 208-test offline run.
- [x] V2-05 Add failing tests for dense+BM25 RRF union, full candidate rerank before top-k, stable output provenance, reranker failures, and token-budget order. Evidence: `tests/retrieval/test_v2_bm25.py`; read-only PostgreSQL provenance tests in `test_postgres_core.py`; token order/budget synthetic oracle; focused tests passed.
- [x] V2-06 Add metric oracle tests for Recall@5/10/20, MRR@10, nDCG@10, insufficient-evidence denominators, DOI attribution and latency serialization. Evidence: `tests/evaluation/test_retrieval_v2_benchmark.py`; included in the 208-test offline run.

## Implementation

- [x] V2-07 Implement minimal BM25Okapi adapter over existing corpus rows with deterministic identity mapping. Evidence: `src/sciscope/retrieval/_bm25.py`, synthetic and PostgreSQL tests.
- [x] V2-08 Implement approved independent v2 selection boundary while preserving v1 contract and behavior. Evidence: version validation and both v1/v2 regression tests.
- [x] V2-09 Integrate existing dense and BM25 branches through existing RRF; rerank merged candidate pool before final top-k and token-budget selection. Evidence: synthetic full-union test, context budget order test, and read-only PostgreSQL v2 integration tests.
- [x] V2-10 Implement/reuse a fail-closed, dev-only comparison harness and manifests; never load protected cohorts. Evidence: `scripts/retrieval_v2_development_benchmark.py`; report under Git-ignored `.cache/`; allowlist is five approved v0 dev IDs only.

## Verification and handoff

- [x] V2-11 Run synthetic/offline evaluation and all applicable existing tests/static checks; fix routine failures. Evidence: 208 offline tests; Ruff check/format; mypy 25 source files. Exact commands/outcomes in `EVIDENCE.md`.
- [x] V2-12 Run read-only PostgreSQL integration on verified `sciscope_test_005`; verify frozen corpus before and after. Evidence: 14 retrieval/evidence-lookup tests passed using guarded local URL derivation; tests enforce read-only transactions; no migration/write. Exact command in `EVIDENCE.md`.
- [x] V2-13 Compare v1/v2 only on allowlisted development questions and report all per-question metrics, latency, limitations and no improvement claims unsupported by measurements. Evidence: `.cache/retrieval_v2/development-comparison.json`, SHA-256 `5d626be1a0f72a1b38cc5d7416e4b307a00ca80486bc2ce1b9ab8cbf388ba395`; summarized in `docs/person2/RETRIEVAL_V2_RESULTS.md`.
- [ ] V2-14 Update Person 2 documentation, `EVIDENCE.md`, `PROJECT_TODO.md`, and approved Person 3 handoff; provide exact native PowerShell independent verification and wait for explicit acceptance. Deliverables and evidence are prepared in `docs/person2/RETRIEVAL_V2_PERSON3_HANDOFF.md`, `RETRIEVAL_V2_RESULTS.md`, `EVIDENCE.md`, and `PROJECT_TODO.md`; pending owner independent review/acceptance and Person 3 integration review. Do not enable v2 in their application.
