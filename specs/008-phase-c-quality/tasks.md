# Tasks: Phase C Retrieval Quality and Evidence Selection

**Input**: Design documents from `/specs/008-phase-c-quality/`  
**Status**: CLOSED 2026-11-19 after independent owner verification and explicit acceptance. The P3-10 held-out isolation criterion is a documented, owner-approved historical exception and remains NOT PASSED.

The eight tasks below are ordered for a short safe path and include test-first behavior and an acceptance check. T001–T007 record implementation and automated verification. T008 records the independent human-acceptance gate. No task includes schema changes or public facade adoption.

## Phase 1: Ranking and reranker decision tooling

- [x] **T001 [P3-09]** Added failing pure behavior tests in `tests/retrieval/test_quality.py` for exact `(doi, source_locator, text)` duplicate identity, deterministic representative, base-order preservation, ties, repeated candidate IDs, per-DOI cap, and exclusion reasons; observed RED before implementation. **Accept:** independent oracle matches every deterministic result and edge case. Verified 9 focused tests pass.
- [x] **T002 [P3-09]** Implemented private ranking/duplicate/diversity component in `src/sciscope/retrieval/_quality.py`, consuming existing Phase B results without editing Feature 007 or duplicating retrieval/RRF. **Accept:** T001 passes, repeat fixtures are identical, provenance/text are unchanged.
- [x] **T003 [P3-10]** Added failing protocol/benchmark tests in `tests/retrieval/test_reranking.py` and `tests/evaluation/test_rerank_benchmark.py`; implemented no-op/fake/score validation and offline benchmark harness in `src/sciscope/retrieval/_reranking.py` and `src/sciscope/evaluation/rerank.py`, including explicit objective quality/regression/latency assessment. Enforced exact five-ID allowlist, metrics/manifest, and disabled default. **Accept:** bad IDs/scores fail; external model loading is local-only; held-out IDs are never accepted; metadata and metrics are reproducible.
- [x] **T004 [P3-10]** Installed the compatible CPU-only local reranking stack into the existing Python 3.12.16 `.venv`, pinned and hash-verified the trusted MiniLM checkpoint, generated the five approved query vectors with one bounded OpenAI embeddings request, and saved real Phase B top-50 candidate lists. Ran the five-question benchmark with five warm repetitions. The objective quality/regression/latency gates failed; the result and limitations are recorded in `EVIDENCE.md`, and production remains disabled. **Accept:** measurement is reproducible and the no-go result is reported without changing thresholds or using held-out questions.

## Phase 2: Context selection and exact evidence lookup

- [x] **T005 [P3-11]** Added failing tests in `tests/retrieval/test_context.py`; implemented exact `TokenCounter` identity contract and deterministic ranked-order whole-item budget selector in `src/sciscope/retrieval/_context.py`. **Accept:** no output exceeds budget; exact-fit/overflow/continue behavior, omission order, identity mismatch, text and provenance preservation match oracle. Verified 10 focused tests pass.
- [x] **T006 [P3-12]** Added failing selector/unit and real-PostgreSQL tests in `tests/retrieval/test_lookup.py` and `tests/retrieval/test_postgres_lookup.py`; implemented private `get_paper`, `get_by_locator`, and `get_chunk` in `src/sciscope/retrieval/_lookup.py`. **Accept:** exact values and not-found/error distinctions match fixtures; read-only REPEATABLE READ behavior and same-snapshot provenance pass on confirmed `sciscope_test_005` only.

## Phase 3: Integration and close-out

- [x] **T007 [P3-09..P3-12]** Added integration regression composing an accepted Phase B lexical result, private ranking, optional reranker off/on fake, context selector, and lookup provenance; ran native Windows focused/full applicable suite, Ruff, formatting, mypy, compile, and read-only pilot verifier. **Accept:** all selected checks pass; no schema change was made; accepted pilot remains 17/319/728/728; limitations are documented.
- [x] **T008 [P3-09..P3-12]** Updated `PROJECT_TODO.md`, `EVIDENCE.md`, this checklist, and `final-audit.md`; supplied read-only PowerShell verification instructions and criteria; owner independently reported passing checks and explicitly accepted Phase C, including the documented historical exception. The held-out isolation criterion remains NOT PASSED and is not represented as a successful control. MiniLM remains disabled. **Accept:** owner verification and acceptance are recorded; P3-09 through P3-12 are closed with the exception visible; Phase C stops without starting Phase D.

## Dependency order

T001 -> T002 -> T003 -> T004; T005 and T006 can proceed after the approved shared internal result shape is set and are independently implementable; T007 depends on T002/T003/T005/T006 and T004 outcome; T008 depends on T007. Public shared DTO/API work is excluded and remains blocked on P1-11/P1-14 review.
