---
description: "Task list for honeybee corpus discovery and pilot selection protocol"
---

# Tasks: Honeybee Corpus Discovery & Pilot Selection

**Input**: Design documents from `specs/002-honeybee-corpus-discovery/`
**Prerequisites**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [quickstart.md](quickstart.md).
**Status**: Planning baseline and T001–T010 execution in dependency order approved as reported by Person 1 on 2026-11-14. T001 is DONE following explicit Person 1 acceptance and recorded source evidence. T002–T010 are authorized for this documentary development cycle; leave each unchecked until its own automated/source and human checks are complete. No production tests or code are authorized by this task list.

**Pre-execution gate**: Person 1 approved `spec.md`, `plan.md`, and this `tasks.md` and authorized T001–T010 in dependency order, reporting the relevant TEAM and Person 2 decisions obtained outside the repository. See [DECISIONS.md](../../docs/DECISIONS.md) for provenance. T001 was explicitly accepted on 2026-11-14. Remaining task dependencies, automated/source checks, and independent human verification remain mandatory. No shared-contract edit is approved.

**Execution snapshot (2026-11-14)**: T001 DONE. T002 and T004 are IN_PROGRESS
because four source-inspected scientific examples and query replay are not yet
available. T003, T005, T006, T008, and T009 have documentary deliverables ready
for task-specific human review but remain unchecked, including where an upstream
dependency remains open. T007 is IN_PROGRESS pending upstream source checks and
TEAM matrix review. T010 has a draft validation matrix and read-only analysis
but cannot complete before T002–T009 verification. `EVIDENCE.md` holds the
per-task statuses and exact checks; no T002–T010 human acceptance is recorded.

## Format: `[ID] [P?] [Story] Description`

Each line follows the official checkbox/ID/story form. Its `Owner`, `Depends`, `AC`, `Validate`, `Manual`, `Impact`, and `Backlog` clauses supply the repository-required task mapping. `[P]` is omitted because review decisions and source checks have dependencies.

## Phase 1: Setup and research

**Purpose**: Confirm publisher access and safe failure handling before operationally fixing the discovery procedure. The previous live PLOS check was BLOCKED; no task here is complete.

- [x] T001 [US2] After explicit feature-owner approval of `spec.md`, `plan.md`, and `tasks.md` and separate authorization for T001, run a bounded PLOS search/API connectivity check, verify one or two candidate metadata records and their individual JATS XML availability, and record exact requests, responses, status, observed DOIs, fields, pagination, article type, and failures in `research.md`. Owner: Person 1; Depends: pre-execution feature-owner approval and T001 authorization; FR: FR-003, FR-007, FR-010; AC: AC-02, AC-05, AC-08, AC-09; Validate: at most two candidate records, one connection, no corpus download; stop and record BLOCKED/FAIL on connection, parse, DOI, or XML uncertainty; Manual: reviewer repeats URLs, verifies source and license/provenance observations, and signs off before further selection; Impact: no shared schema change or final DOI/licensing policy decision; Backlog: P1-02.

**Checkpoint**: If live access fails, keep discovery operationally blocked and document the failure or seek a separately approved fallback.

## Phase 2: Foundational protocol

**Purpose**: Finalize rules before any pilot curation.

- [ ] T002 [US1] Finalize `spec.md` eligibility rubric for direct, conditional, generic, and other-species cases, with identifiable honeybee evidence threshold. Owner: Person 1; Depends: T001; FR: FR-001; AC: AC-01; Validate: apply rubric to four source-inspected examples and record reasons; Manual: TEAM reviews borderline comparative case and approves or rejects policy; Impact: no ingestion fields; Backlog: P1-01 (TEAM retains approval ownership).
- [ ] T003 [US1] Finalize publication-type and license readiness policy in `spec.md` and `research.md`, including primary research, the approved at-most-three labeled reviews in 20, corrections, editorials, front matter, full-text failures, and paper-specific reuse terms. Owner: Person 1; Depends: T002; FR: FR-002, FR-007; AC: AC-01, AC-05; Validate: decision table includes every type, primary-versus-review evidence, and unknown/failed state; Manual: TEAM verifies application of the approved review cap and source/license evidence; Impact: Person 2 receives only verified status; Backlog: P1-05 (TEAM retains approval ownership).
- [ ] T004 [US2] Freeze exact field-limited Boolean queries, page cap, stable sort, UTC recording, and screening/exclusion procedure in `plan.md`/`research.md` after T001. Owner: Person 1; Depends: T001, T002; FR: FR-003, FR-005; AC: AC-02, AC-08; Validate: second reviewer can repeat query and page IDs; Manual: reviewer checks query transcription and index-drift note; Impact: later acquisition consumes DOI candidates only; Backlog: P1-02, P1-15.

**Checkpoint**: A reviewer can reproduce discovery and distinguish scientifically relevant evidence from search hits.

## Phase 3: User Story 2 — Identity and bounded pilot protocol (Priority: P1)

**Goal**: A unique, auditable candidate list and representative pilot selection rule.

**Independent Test**: Review duplicate, malformed, and missing DOI cases plus a bounded selection rationale without generating a corpus.

- [ ] T005 [US2] Finalize DOI normalization/deduplication decision table in `data-model.md`, preserving every source DOI and search path. Owner: Person 1; Depends: T004; FR: FR-004; AC: AC-04; Validate: table covers bare/resolver, ASCII case, one-time URI decoding, non-ASCII preservation, malformed/conflict, and duplicate pages; Manual: Person 2 approves or rejects comparison and display semantics; Impact: possible P1-10 DOI rule proposal only, no schema edit; Backlog: P1-04, P2-03.
- [ ] T006 [US2] Finalize lightweight screening manifest fields/states and version rules in `data-model.md`, distinct from processed records. Owner: Person 1; Depends: T005; FR: FR-006; AC: AC-03, AC-04, AC-05; Validate: every FR-006 field and unknown/failure state maps to a manifest field; Manual: Person 2 checks ingestion handoff boundary; Impact: no new shared contract; Backlog: P1-15.
- [ ] T007 [US2] Finalize a first 3–5-paper manually inspected smoke-test protocol and a complete 20-eligible-paper target, counting accepted first-sample papers, with supported theme/JATS variation, labeled review minority, shortfall handling, selection/exclusion reasons, and no first-results shortcut. Owner: Person 1; Depends: T002, T003, T004, T006; FR: FR-005; AC: AC-03, AC-08; Validate: proposed selection matrix and count rules are internally consistent without fabricated papers; Manual: TEAM approves or rejects sample/target and review cap; Impact: pilot acquisition and curation require later explicit authorization; Backlog: P1-15, P2-24.

**Checkpoint**: Pilot protocol can be approved without claiming that any paper has already been selected.

## Phase 4: User Story 3 — Shared contract and golden readiness (Priority: P2)

**Goal**: Make downstream decisions explicit before source processing and evaluation.

**Independent Test**: Person 2 can review gaps and golden source anchors from a field-level note.

- [ ] T008 [US3] Review `docs/DATA_CONTRACT.json` field by field against `data-model.md` and record only minimal compatible DOI/provenance/locator proposals in `plan.md`. Owner: Person 1; Depends: T006; FR: FR-008, FR-009; AC: AC-06, AC-07; Validate: check DOI, type, language, subjects, nullability, XML path/hash, sections/locators, fallback when `@id` is absent, and versions; Manual: Person 2 accepts or rejects each gap and locator encoding before any shared edit; Impact: shared schema remains unchanged here; Backlog: P1-04, P1-10, P2-10.
- [ ] T009 [US3] Record `evals/golden_questions.schema.json` locator, negative-case, ID-uniqueness, and label-rubric gaps and acceptance prerequisites for 5–10 future human-verified questions in `plan.md`. Owner: Person 1; Depends: T007, T008; FR: FR-009; AC: AC-07; Validate: distinguish JSON Schema field/conditional checks from dataset-level unique-ID, DOI/corpus, and pinned-XML locator checks without inventing source text; Manual: Person 2 reviews relevance rubric and schema proposals; Impact: no golden records or schema edits; Backlog: P1-12, P2-22, P2-23, P3-13.
- [ ] T010 [US3] Verify the completed Feature 002 deliverables, reconcile the final validation matrix and `quickstart.md`, run cross-artifact consistency review, and present actual task evidence for post-execution human acceptance. Owner: Person 1; Depends: T001–T009 and their applicable verification; FR: FR-010; AC: AC-09; Validate: source-check outcomes, checklist, FR→AC→task coverage, 3–5-to-20 count consistency, `git diff --check`, and Spec Kit analysis, reporting failures and blocked checks honestly; Manual: after Person 2 and TEAM decisions relevant to completed work, the feature owner explicitly accepts or rejects the finished deliverables; Impact: final feature acceptance gate, not initial execution authorization; Backlog: P1-15.

## Dependency order and execution policy

Pre-execution feature-owner approval and explicit T001 authorization → T001 → T002/T003/T004 → T005/T006/T007 → T008/T009 → T010 → separate post-execution feature-owner acceptance. TEAM approval is required for eligibility, licensing, review minority, and complete-pilot acceptance; Person 2 reviews DOI and source-locator semantics and golden handoff. Their unresolved decisions block dependent tasks, not the bounded T001 observation after its own approval gate. No parallel execution is assumed. The next feature, **Pilot XML & Golden Evaluation Dataset**, may start only after the pilot protocol and shared handoff are approved. Future Python behavior tasks, if separately authorized, must start with offline behavior tests, show RED, implement the smallest approved behavior, then show GREEN; documentary/manual tasks use source and reviewer validation instead of artificial unit tests. No item is marked complete by this plan.
