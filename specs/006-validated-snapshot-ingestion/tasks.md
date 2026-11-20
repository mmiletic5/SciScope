---
description: "Implementation tasks for validated snapshot ingestion"
---

# Tasks: Validated Snapshot Ingestion

**Input**: Design documents from `/specs/006-validated-snapshot-ingestion/`

**Tests**: Mandatory. Every behavior task follows recorded RED → GREEN →
REFACTOR → VERIFY; database behavior requires real PostgreSQL/pgvector.
All Person 2 commands and database tests run natively on Windows PowerShell
against PostgreSQL 17/pgvector 0.8.7. Do not introduce Docker, WSL, or Linux.

## Phase 1: Setup

- [x] T001 Define typed `importer.v1` request/result/error behavior and its RED contract tests in `src/sciscope/ingestion/contract.py` and `tests/ingestion/test_import_contract.py`, matching every operation and sanitized error rule in `contracts/importer-v1.md`

## Phase 2: Foundational

- [x] T002 Implement the pre-write adapter over delivery 0.3.0 and observe the full corrupt/incomplete/incompatible RED matrix in `src/sciscope/ingestion/validate.py` and `tests/ingestion/test_snapshot_validation.py`, without modifying `data/delivery/` or duplicating its schema
- [x] T003 Implement manifest-entry-ordered streaming float32-le decoding in `src/sciscope/ingestion/vectors.py` only after RED cases in `tests/ingestion/test_vector_decoding.py` prove reordered ownership, exact 1536 dimensions, duplicate/missing IDs, truncation, trailing bytes, and nonfinite rejection

## Phase 3: User Story 1 - Import a complete validated snapshot (Priority: P1)

**Goal**: Atomically initialize an empty database from a complete delivery.

**Independent Test**: A valid synthetic snapshot produces exact records, one
active audit, zero orphans, and independently verified vector ownership.

- [x] T004 [US1] Write and observe RED initial-import, provenance, audit, count, ownership, and in-transaction verification tests in `tests/ingestion/test_initial_import.py`, `tests/ingestion/test_provenance.py`, and `tests/ingestion/test_audit.py`, then implement the smallest transactional GREEN in `src/sciscope/ingestion/service.py`

## Phase 4: User Story 2 - Reimport or replace safely (Priority: P2)

**Goal**: Make identical input a no-op and different input an explicit guarded replacement.

**Independent Test**: Database fingerprints prove no-op stability and complete
old-to-new replacement with no absent old row remaining active.

- [x] T005 [US2] Write and observe RED initialize/replace state-table, expected-digest conflict, historical-reactivation, audit-immutability, and stale-row-pruning tests in `tests/ingestion/test_idempotency.py` and `tests/ingestion/test_replacement.py`, then implement GREEN compare-and-swap replacement in `src/sciscope/ingestion/service.py`

## Phase 5: User Story 3 - Recover from failures and concurrent attempts (Priority: P3)

**Goal**: Prove rollback, serialization, retry, and independent reconciliation.

**Independent Test**: Every injected failure preserves the old complete
fingerprint; two real connections cannot both mutate; retry is safe.

- [x] T006 [US3] Write and observe RED stage-by-stage rollback, interruption/retry, and synchronized two-connection lock tests in `tests/ingestion/test_rollback.py` and `tests/ingestion/test_concurrency.py`, then implement fail-fast transaction advisory locking and failure-safe GREEN behavior in `src/sciscope/ingestion/service.py`
- [x] T007 [US3] Implement an importer-independent read-only reconciliation CLI in `src/sciscope/ingestion/verify_pilot.py` after RED tests prove complete ID, provenance, orphan, dimension, and little-endian float32 byte comparison behavior in `tests/ingestion/test_verify_pilot.py`
- [x] T008 [US3] Run real-pilot initialization, identical no-op, complete synthetic replacement, forced rollback, concurrency, independent all-728-vector reconciliation, full regression, Ruff, mypy, Alembic, diff, and working-tree checks from `quickstart.md`; obtain explicit human acceptance and update only actual results in `EVIDENCE.md`, `PROJECT_TODO.md`, and this file

## Dependencies & Execution Order

- Accepted Feature 005 is a hard prerequisite.
- T001 defines the behavior used by every later task.
- T002 and T003 are foundational and may prepare RED tests in parallel, but
  both must be GREEN before T004.
- T004 precedes T005; T005 precedes concurrency/recovery T006.
- T007 may begin after T003/T004 but cannot be accepted before T005/T006.
- T008 depends on T001–T007 and stops Phase A for human verification.

## Parallel Opportunities

Validation RED work in T002 and vector-decoding RED work in T003 touch separate
modules. After initial import exists, independent verifier RED work in T007 can
proceed alongside replacement test preparation, but final acceptance remains
ordered.

## Implementation Strategy

Complete the typed contract and validation foundation first. Deliver initial
import as the independently testable MVP, then no-op/replacement, then recovery
and reconciliation. Preserve actual RED/GREEN evidence. Do not start Phase B
retrieval automatically after Feature 006 acceptance.

## Historical implementation progress (superseded by acceptance update below)

Feature 005 is explicitly human-accepted. Feature 006 is authorized for implementation. T001-T003 code and focused automated checks are present; the contract/validation/vector-focused checks and Ruff/format/mypy checks pass. T004-T008 remain incomplete. Real PostgreSQL lock contention passed on the confirmed `sciscope_test_005` database. The pilot import stopped before writes with `EMBEDDING_CONFIGURATION_MISMATCH`; see `EVIDENCE.md` and `research.md` for the accepted Feature 005 numeric column versus delivery `"l2"` method mismatch. No Feature 006 task is human-accepted, and no task checkbox is marked complete pending the feature's final independent verification gate.

## Historical verification correction (superseded by acceptance update below)

After the earlier progress entry, the additional vector digest regression and pure verifier checks passed; the focused offline Feature 006 set now reports 18 passed. The complete existing non-database/non-ingestion regression command `python -m pytest --ignore=tests/database --ignore=tests/ingestion -q -p no:cacheprovider` passed 2,590 tests with 2 skipped in 59.50 seconds. Final whole-project Ruff check passed, whole-project Ruff format check passed (187 files), `mypy src` passed (53 source files), `python -m alembic heads` reported exactly `f005_pgvector_foundation (head)`, and `git diff --check` passed. Alembic `current` and `check` were deliberately not run because default `DATABASE_URL` targets protected main `sciscope`; the ingestion suite fixture verifies the exact test database without migrating it. Feature 006 DB-backed import/idempotency/replacement/rollback/verifier acceptance remains blocked by the normalization contract question documented above.

## Feature 006 implementation and acceptance update (2026-11-19)

The owner approved the explicit no-migration mapping: the numeric `embedding_sets.normalization_declared` value records validated target norm `1.0`, while the JSON manifest preserves method string `"l2"`. Real PostgreSQL tests passed: `tests/ingestion` 38 passed; combined `tests/database tests/ingestion` 82 passed. All used preflight-confirmed `sciscope_test_005` as `sciscope`, PostgreSQL 17.12, pgvector 0.8.7, and were rollback-scoped except for the explicitly recorded committed pilot initialization in `EVIDENCE.md`. Offline regression passed 2,590 with 2 skipped. Ruff check, Ruff format check (187 files), mypy (53 source files), Alembic single-head check, Alembic online current/check, and `git diff --check` passed. The owner independently ran the full suite (2,672 passed, 2 skipped, zero failures/errors in 106.73 seconds) and `scripts/verify_feature006_readonly.ps1` (10/10 PASS; all mismatch counters zero). Feature 006 is human-accepted; T001-T008 and P3-03/P3-04 are complete.
