---
description: "Ordered Phase B task checklist; feature and schema gates remain explicit"
---

# Tasks: Phase B Retrieval Core

**Input**: Design documents in `/specs/007-phase-b-retrieval-core/`

**Status:** Person 2 internal retrieval core accepted and closed 2026-11-19. Shared retrieval.v1/facade, cross-team gates, and schema migration remain pending and unapproved. The proposed T007 amendment dated 2026-11-22 awaits human review and authorizes no implementation.

**Execution and acceptance note (2026-11-19):** The owner independently reported preflight PASS on `sciscope_test_005`, 47 retrieval tests passed, Feature 005 read-only verification PASS, Feature 006 verification PASS 10/10 with zero mismatches, and preserved active pilot counts 17/319/728/728. The owner explicitly human-accepted and closed P3-05 through P3-08. T002-T006 are complete. PostgreSQL behavior tests passed, though a pre-implementation RED run for those database-specific tests was not observed; this limitation and the unrun activation-concurrency, smoke, and latency checks are documented in `EVIDENCE.md` and `spec.md`. Shared facade, cross-team contract adoption, and schema migration remain gated.

## Phase 1: Feature approval and contract tests

- [x] T001 [Person 2] Record the owner's explicit approval of the Feature 007 specification and internal Person 2 implementation plan. This does not approve shared retrieval.v1 adoption, P1-09/P1-11/P1-14, or the GIN migration.
- [x] T002 [Person 2] Add internal behavior fixtures and RED conformance cases for validation, vector compatibility, and deterministic ranking; implement deterministic fake embeddings and independent ranking oracles. Do not publish production DTO/service models until the shared-interface gate in T007 is recorded.

## Phase 2: Retrieval branches and shared semantics

- [x] T003 [Person 2] Implement exact cosine retrieval, output validation, active embedding compatibility, read-only REPEATABLE READ behavior, and provenance mapping; real PostgreSQL behavior tests pass. The database-specific pre-implementation RED run and committed concurrent-activation scenario were not observed/performed; see acceptance limitations.
- [x] T004 [Person 2] Implement and verify English `websearch_to_tsquery` + `ts_rank_cd` over chunk text and no-lexeme empty behavior. The optional GIN migration is separate and remains unapproved; no schema change was made.
- [x] T005 [Person 2] Implement and verify the shared internal filter predicate across dense, lexical, and hybrid paths using the documented proposed baseline. Shared P1-09 adoption remains pending.
- [x] T006 [Person 2] Implement and verify bounded candidate pools, union by chunk ID, RRF k=60, component ranks/scores, top-k cutoff, and deterministic total tie order using independent ranking oracles.

## Phase 3: Gated shared facade and integration follow-up

- [ ] T007 [Person 3; Person 2 reviewer] Public facade work remains blocked until the proposed T007 amendment receives explicit human approval and P1-09/P1-11/P1-14 plus affected-owner contract adoption are recorded. Person 1 reviews public provenance/source metadata mapping. P4-09 remains separate and unimplemented.
  - [ ] T007-A [Person 3; Person 2 reviewer] Record the approved delegation, public-facade scope, affected-owner reviews, P1-09/P1-11/P1-14 shared-contract gates, and completion criteria in `specs/007-phase-b-retrieval-core/{spec,plan,tasks}.md`. This documentation draft is not approval; no behavior test, implementation, task completion, `EVIDENCE.md`, or `PROJECT_TODO.md` update occurs before explicit human approval.
  - [ ] T007-B [Person 3; Person 2 reviewer] After T007-A approval and P1-09/P1-11/P1-14 plus affected-owner contract adoption, write RED service-boundary tests in `tests/retrieval/test_public_contracts.py`, then add public driver-independent versioned DTOs and typed sanitized errors in `src/sciscope/retrieval/{contracts,errors}.py` plus `__init__.py` exports. Preserve documented v1 behavior and support explicit v2 selection; do not expose ORM, SQLAlchemy, connection, or private types. Verify `uv run --locked pytest tests/retrieval/test_public_contracts.py`, Ruff, formatting, and mypy. Obtain Person 2 contract review before commit.
  - [ ] T007-C [Person 3; Person 2 reviewer] After T007-B, write RED facade tests in `tests/retrieval/test_public_service.py`, then add a public `RetrievalService` facade and injected query-embedder protocol in `src/sciscope/retrieval/service.py`. Preserve algorithms, filters, ranking, read-only transactions, and database behavior; no live embedder, environment lookup, database connection at import, or private-type leakage. Verify focused pytest, Ruff, formatting, and mypy; obtain Person 2 source review before commit.
  - [ ] T007-D [Person 3; Person 2 reviewer] After T007-C, add offline conformance coverage for v1/v2 selection, unsupported versions, empty results, typed failures, deterministic fake embeddings, provenance, and consumer isolation. Confirm tests make no database, network, paid-provider, or private-consumer imports. Run focused and applicable retrieval regression/static checks; obtain Person 3 consumer and Person 2 conformance review before commit.
  - [ ] T007-E [Person 3; Person 2 reviewer] Only after separate authorization, add/run a guarded public-facade integration test against the designated read-only `sciscope_test_005` database. Verify preflight identity, read-only behavior, public result provenance, and no migration/write. Do not fabricate a RED database run. Record observed commands/results and obtain human verification before commit.
  - [ ] T007-F [Person 3] Maintain `docs/person3/FEATURE_007_T007_TEST_LOG.md` chronologically during implementation, including actual RED/GREEN results, corrections, verification commands/results, reviewers, dates, manual decisions, and existing commit hashes only. After automated success and explicit feature-level human acceptance, update `EVIDENCE.md`, synchronize justified task/backlog state, and make a separately reviewed/authorized documentation commit.
- [ ] T008 [Person 2] After the shared facade gate is satisfied, complete cross-contract conformance, the five-question smoke, warm/cold observations, and integration handoff. Do not access the 16 held-out questions during tuning. This task is not part of the accepted private core closure.

## Dependencies and execution order

T001-T006 are complete for the accepted private retrieval core. T007's public shared facade remains blocked until the T007 amendment is explicitly approved and P1-09/P1-11/P1-14 plus affected-owner contract adoption are recorded. The optional GIN migration is separate and requires schema authorization; correctness does not depend on it. T008 remains a gated integration follow-up. Person 1/3/4 task states are not changed by Person 2 except for the proposed delegation of T007 implementation responsibility, which remains pending approval.
