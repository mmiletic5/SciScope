# Phase B Internal Closure and Shared Gates Checklist

**Status:** Person 2 internal retrieval core accepted and closed 2026-11-19. Unchecked shared-contract and schema items remain proposals/gates, not approvals.

## Person 2 technical direction (approved by owner)

- [x] Exact cosine; no ANN in Phase B (ADR-009 direction).
- [x] English FTS, `websearch_to_tsquery`, `ts_rank_cd`, chunk text only (ADR-010 direction).
- [x] Deterministic RRF k=60, one-based ranks, bounded candidate pools, documented ties (ADR-011 direction).
- [x] AND filter categories / OR values as proposed baseline (ADR-012 direction; shared confirmation pending).
- [x] Read-only `REPEATABLE READ`, parameterized SQL, strict validation, sanitized errors, no silent mode fallback.
- [x] Prefer GIN expression index; migration remains separately unapproved.

## Shared integration obligations (not recorded as approved)

- [ ] Person 1 confirms persisted metadata/provenance guarantees and locator stability.
- [ ] Person 3 confirms retrieval.v1 DTO/error contract, HTTP boundary, and live embedder ownership/configuration.
- [ ] Person 4 confirms filter semantics are usable in UI controls.
- [ ] Team confirms P1-11/P1-14 shared contract gates and five/16 Golden partition governance.
- [ ] Schema approver explicitly approves or defers additive GIN migration.

## Feature and implementation gates

- [x] Canonical contract and spec/plan/tasks synchronized as a Person 2 reference proposal.
- [ ] At eventual integration, record Person 1/3/4 and team review without changing their task states by inference.
- [ ] Before exposing the public service facade, record P1-11/P1-14 and affected-owner review; until then keep Person 2 core behind a private boundary.
- [x] Spec Kit cross-artifact consistency analysis completed; remaining external gates are documented.
- [x] User explicitly approves Person 2 internal Feature 007 implementation scope and plan (2026-11-19); shared contract and migration remain unapproved.
- [x] After approval: offline behavior tests observed RED before implementation and returned GREEN.
- [x] Native Windows real PostgreSQL integration checks completed against confirmed `sciscope_test_005` (read-only retrieval suite; Phase A writes rollback-scoped).
- [x] Final automated checks passed: selected full regression, Ruff, format, mypy, compileall, Feature 005/006 read-only verifiers.
- [x] Owner independently verified the internal retrieval core and explicitly accepted P3-05 through P3-08 on 2026-11-19; evidence is recorded in `EVIDENCE.md`.

## Accepted scope boundary

- [x] Private internal exact dense, English FTS, shared filter implementation, deterministic RRF, validation, and provenance behavior verified and accepted.
- [ ] Public shared `RetrievalService` facade and `retrieval.v1` adoption; gated on P1-11/P1-14 and affected-owner review.
- [ ] Cross-team filter/metadata/API confirmations, optional GIN migration, five-question smoke, and warm/cold observations remain pending; the 16 held-out Golden questions remain untouched.
