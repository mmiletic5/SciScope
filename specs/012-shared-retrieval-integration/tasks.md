---
description: "Ordered Feature 012 implementation checklist; all approval and database gates remain explicit"
---

# Tasks: Shared Retrieval Service Integration

**Input**: Design documents in `/specs/012-shared-retrieval-integration/`
**Status**: APPROVED planning package. T001–T005 are complete; T006–T008 remain incomplete. Each later gate remains explicit.

## Phase 1: Setup and shared contract approval

**Purpose**: Resolve decisions that affect shared boundaries before writing behavior tests.

- [x] T001 (012-A) Review and approve `specs/012-shared-retrieval-integration/{research,spec,plan,tasks}.md`; Owner: Person 3. Person 3 explicitly approved the planning package on 2026-11-22 and authorized T012-B offline work. Person 2/Person 4 delegation remains owner-reported only, not implementation/test approval. D012-01 through D012-05, the five-question evaluation protocol, response metadata compatibility, error mapping, and lifecycle ownership are recorded. No artificial RED/GREEN test. **Dependencies**: none. **Verification**: formal approval, documentation checks, and retained gates are recorded in `docs/person3/P4_09_TEST_LOG.md`; concrete affected-owner reviews and any unresolved gate block only dependent implementation.

## Phase 2: Internal metadata contracts and validation foundations

**Goal**: Make the question-service contract able to represent truthful component configuration, execution, and test-data state before real retrieval is adapted.

**Independent Test**: Offline contract tests cover all seven metadata scenarios, including provider-not-invoked and failed-provider states, while existing v1 fake-only values remain exact.

- [x] T002 (012-B) COMPLETE 2026-11-22 — Owner: Person 3. Added RED contract/validation tests and the smallest internal retrieval/answer-provider component metadata foundation for configured origin, execution, and independent test-data state across synthetic/fake, real/fake, real/real, isolated DB, empty retrieval, retrieval failure, and provider failure. Existing v1 HTTP models/routes remain unchanged. **Dependencies**: T001. **Verification**: Codex and independent Person 3 offline focused/backend, Ruff, mypy, and diff checks are recorded in `docs/person3/P4_09_TEST_LOG.md`; formal Person 3 decision is `ACCEPTED`. T003–T008 remain separately gated.

## Phase 3: User Story 1 — Public RetrievalService question adapter (Priority: P1)

**Goal**: Adapt the public facade to the now-truthful internal question retrieval protocol while preserving exact evidence and provenance.

**Independent Test**: Offline public-service stubs exercise request construction, mapping, empty results, malformed responses, and invalid settings without a database/provider.

- [x] T003 [US1] (012-C) COMPLETE 2026-11-22 — Owner: Person 3. Added public-boundary adapter RED tests and `src/sciscope/question_service/retrieval_adapter.py`: immutable explicit settings, one injected public-facade request, strict response/configuration validation, exact evidence/corpus mapping, and retrieval-only metadata. **Dependencies**: T001, T002. **Verification**: Codex and independent Person 3 focused/backend/public-retrieval/static checks are recorded in `docs/person3/P4_09_TEST_LOG.md`; Person 3 decision is `ACCEPTED`. Person 2 boundary confirmation is owner-reported only. T004–T008 remain separately gated.

## Phase 4: User Story 2/3 — Versioned HTTP integration and typed retrieval errors (Priority: P1)

**Goal**: Add only the proposed v2 HTTP contract while leaving accepted v1 behavior and JSON shapes untouched.

**Independent Test**: Offline stubs raise each public retrieval error; HTTP results are checked against the approved status/code/message/retryability/request-ID matrix.

- [x] T004 [US2] [US3] (012-D) COMPLETE 2026-11-22 — Owner: Person 3. Added the separately versioned `/api/v2/questions` models/routes, explicit validated `v2_metadata` opt-in, truthful component execution metadata, response-local citation failure handling, typed public retrieval error mapping, and route-scoped request-ID protection while preserving v1. **Dependencies**: T001–T003. **Verification**: Codex and independent Person 3 focused v2, v1/v2, backend, public retrieval, Ruff, format, mypy, and diff checks are recorded in `docs/person3/P4_09_TEST_LOG.md`; Person 3 decision is `ACCEPTED`. T005–T008 remain separately gated.

## Phase 5: User Story 4 — Compose dependencies without hidden resources (Priority: P2)

**Goal**: Wire real retrieval explicitly while fake-only imports/tests remain inert and resource ownership is clear.

**Independent Test**: Sentinels show no DB/provider/network/listener initialization during import, factory construction, or fake-only requests; lifecycle tests cover the approved creator/borrower disposal rule.

- [x] T005 [US4] (012-E) COMPLETE 2026-11-23 — Owner: Person 3. Person 3 decision: ACCEPTED. Add RED tests proving API import/app construction and fake-only requests are inert, and creator/borrower Engine disposal rules. Implement an approved explicit composition root that constructs/injects the exported public `RetrievalService`, adapter, and v2 app dependencies. Do not use the private `_compose_private_executor` as a production API; if no approved public service factory exists, record that dependency and stop before real composition. **Dependencies**: T001–T004. **Verification**: `uv run --locked pytest tests/backend/test_app_factory.py tests/backend/test_retrieval_composition.py tests/backend/test_application_lifecycle.py tests/backend/test_http_lifecycle.py -q`; `uv run --locked pytest tests/backend -q`; independent Person 3 lifecycle verification.

## Phase 6: Cross-story offline integration regression

**Purpose**: Verify the question backend, adapter, public retrieval stub, and fake answer provider together.

- [ ] T006 [US1] (012-F) Owner: Person 3. Add RED in-process cases for v2 fake-provider success, no-results/provider-not-invoked behavior, response-local citations, exact configured version/mode forwarding, all metadata execution states, and no fallback; implement only approved wiring. Run offline backend/public-facade regression without database/provider access. **Dependencies**: T002–T005. **Verification**: `uv run --locked pytest tests/backend/ tests/retrieval/test_public_service.py tests/retrieval/test_public_contracts.py -q`; Person 2/4 reviews and Person 3 HTTP verification.

## Phase 7: Approved mode comparison and guarded PostgreSQL integration

**Purpose**: Produce reviewed mode-selection evidence and verify exact mapping against the authorized isolated snapshot.

- [ ] T007 [US1] (012-G) Owner: Person 3. After separate explicit database authorization, add/run `tests/retrieval/test_backend_adapter_postgres.py` using only `gq-sp-001`, `gq-cmp-001`, `gq-conf-001`, `gq-gap-001`, and `gq-ins-001`; compare distinct supported version/mode behaviors under the approved fixed protocol. Assert exact database/role/server/extension/revision, expected active-snapshot counts, read-only repeatable-read transactions, exact persisted source/provenance, deterministic results where applicable, and unchanged pre/post state. No held-out questions, migration, ingestion, replacement, paid provider, or write. Person 2 reviews before Person 3 selects an application setting; if evidence is insufficient, keep selection pending. **Dependencies**: T001–T006 and separate database authorization. **Verification**: `uv run --locked pytest tests/retrieval/test_backend_adapter_postgres.py -q`; label Codex/Ubuntu and owner/Windows runs separately; owner reviews pre/post identity and results.

## Phase 8: Polish and human close-out

**Purpose**: Complete reviews and evidence without conflating automation and owner verification.

- [ ] T008 (012-H) Owner: Person 3. Run approved focused static/regression checks; append exact Codex/owner commands, failures/corrections, environment, review decisions, mode evidence, and authorized DB evidence to `docs/person3/P4_09_TEST_LOG.md` and `EVIDENCE.md`; synchronize task/backlog state only after required verification. Person 2/4 and applicable Person 1 decisions must be recorded; Person 3 records explicit `ACCEPTED` or `REJECTED`. **Dependencies**: T002–T007. **Verification**: independent Windows commands, human review, no completion without explicit acceptance.

## Dependencies and execution order

```text
T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008
```

- T001 is the planning/approval gate and uses review rather than artificial tests.
- T002–T007 each require behavior tests first, an actual RED result, minimal GREEN implementation, Codex automated/static checks, independent owner verification, and affected-owner review before an authorized focused commit.
- T007 is separately blocked on explicit database authorization; a guarded test is not authorization to connect.
- T008 is an evidence/human gate, not permission to auto-commit. PR integration remains required.
- Preserve each failed/blocked check and later correction chronologically.

## Acceptance traceability

| Spec coverage | Task |
| --- | --- |
| Decisions, feature approval, evaluation protocol, owner gates | T001 |
| FR-001–FR-008; request, exact mapping, no-results, citation membership | T003, T006 |
| FR-009–FR-010; metadata scenarios and Feature 011 compatibility | T002, T004 |
| FR-011–FR-014; seven errors, timeout, privacy and no fallback | T004, T006 |
| FR-015–FR-017; module boundaries, import safety and lifecycle | T005 |
| FR-018–FR-020; five-question evaluation and explicit mode configuration | T001, T006, T007 |
| FR-021–FR-022; isolated read-only database gate | T007 |
| FR-023–FR-024; chronology, reviews, manual verification and acceptance | T008 |
