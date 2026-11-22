---
description: "Ordered Phase B task checklist; feature and schema gates remain explicit"
---

# Tasks: Phase B Retrieval Core

**Input**: Design documents in `/specs/007-phase-b-retrieval-core/`

**Status:** Person 2 internal retrieval core was accepted and closed 2026-11-19.
T007-A through T007-F were completed and **Feature 007 was owner-confirmed
accepted on 2026-11-22**. The final acceptance includes owner-reported Person 2
review and native Windows guarded-integration PASS; the Windows terminal output
was not retained. The acceptance is limited to T007's public-facade scope. It
does not complete broader P1 tasks, adopt either shared contract beyond that
scope, or approve the separate GIN migration.

**Execution and acceptance note (2026-11-19):** The owner independently reported preflight PASS on `sciscope_test_005`, 47 retrieval tests passed, Feature 005 read-only verification PASS, Feature 006 verification PASS 10/10 with zero mismatches, and preserved active pilot counts 17/319/728/728. The owner explicitly human-accepted and closed P3-05 through P3-08. T002-T006 are complete. PostgreSQL behavior tests passed, though a pre-implementation RED run for those database-specific tests was not observed; this limitation and the unrun activation-concurrency, smoke, and latency checks are documented in `EVIDENCE.md` and `spec.md`. As of that acceptance, the shared facade, cross-team contract adoption, and schema migration remained gated; the current T007 scope-limited approval record does not alter that historical evidence.

## Phase 1: Feature approval and contract tests

- [x] T001 [Person 2] Record the owner's explicit approval of the Feature 007 specification and internal Person 2 implementation plan. At that time, this did not approve shared retrieval.v1 adoption, P1-09/P1-11/P1-14, or the GIN migration.
- [x] T002 [Person 2] Add internal behavior fixtures and RED conformance cases for validation, vector compatibility, and deterministic ranking; implement deterministic fake embeddings and independent ranking oracles. Do not publish production DTO/service models until the shared-interface gate in T007 is recorded.

## Phase 2: Retrieval branches and shared semantics

- [x] T003 [Person 2] Implement exact cosine retrieval, output validation, active embedding compatibility, read-only REPEATABLE READ behavior, and provenance mapping; real PostgreSQL behavior tests pass. The database-specific pre-implementation RED run and committed concurrent-activation scenario were not observed/performed; see acceptance limitations.
- [x] T004 [Person 2] Implement and verify English `websearch_to_tsquery` + `ts_rank_cd` over chunk text and no-lexeme empty behavior. The optional GIN migration is separate and remains unapproved; no schema change was made.
- [x] T005 [Person 2] Implement and verify the shared internal filter predicate across dense, lexical, and hybrid paths using the documented proposed baseline. At the internal-core acceptance, shared P1-09 adoption remained pending; the current T007 scope-limited approval record preserves those semantics without completing broader P1-09.
- [x] T006 [Person 2] Implement and verify bounded candidate pools, union by chunk ID, RRF k=60, component ranks/scores, top-k cutoff, and deterministic total tie order using independent ranking oracles.

## Phase 3: Gated shared facade and integration follow-up

- [x] T007 [Person 3; Person 2 reviewer] The amended public-facade scope, delegated implementation, provenance review, public contracts/service, offline conformance, guarded integration evidence, and final feature acceptance are recorded in `docs/person3/FEATURE_007_T007_TEST_LOG.md` and `EVIDENCE.md`. P4-09 remains separate and unimplemented.
  - [x] T007-A [Person 3; Person 2 reviewer] Recorded the project-owner-reported Persons 1–4 agreement, delegation, public-facade scope, affected-owner reviews, T007-scope P1-09/P1-11/P1-14 gate, and completion criteria.
  - [x] T007-B [Person 3; Person 2 reviewer] Added driver-independent versioned public DTOs, typed sanitized errors, public exports, and service-boundary contract tests; committed as `df104b966c1a5725f50f1f8845f79366fa5c6b9f`.
  - [x] T007-C [Person 3; Person 2 reviewer] Added `RetrievalService`, injected query-embedder protocol, response/provenance mapping, error translation, and private-core composition; committed as `d2262668dbb4afbf2ad5a34c9423a0db7244d55e`.
  - [x] T007-D [Person 3; Person 2 reviewer] Added offline public-facade conformance coverage with no database, network, paid-provider, or private-consumer import; committed as `6c7748147fb0c3a47d26f8a0deb4dbdd58764a4f`.
  - [x] T007-E [Person 3; Person 2 reviewer] Added the guarded public-facade integration test and recorded authorized Ubuntu migration/import/test evidence, owner-reported Person 2 review, and owner-reported native Windows PASS. Windows terminal output was not retained; no unobserved output is claimed. The review-ready package was committed as `97ea843407e0424a388a7206f182b5c72a4f4f08`.
  - [x] T007-F [Person 3] Maintained the chronological log, recorded final offline verification, received explicit feature-level owner acceptance, and synchronized evidence/task/backlog status in this separately authorized documentation finalization.
- [ ] T008 [Person 2] After the shared facade gate is satisfied, complete cross-contract conformance, the five-question smoke, warm/cold observations, and integration handoff. Do not access the 16 held-out questions during tuning. This task is not part of the accepted private core closure.

## Dependencies and execution order

T001-T006 are complete for the accepted private retrieval core. T007 is complete
and Feature 007 is owner-confirmed accepted. Broader P1 task completion and
shared-contract status remain unchanged. The optional GIN migration is separate
and requires schema authorization; correctness does not depend on it. T008
remains a gated integration follow-up.
