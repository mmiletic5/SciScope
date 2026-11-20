---
description: "Implementation tasks for PostgreSQL and pgvector foundation"
---

# Tasks: PostgreSQL and pgvector Foundation

**Input**: Design documents from `/specs/005-postgres-pgvector-foundation/`

**Tests**: Mandatory. Every behavior task follows recorded RED â†’ GREEN â†’
REFACTOR â†’ VERIFY and real PostgreSQL is required for database-owned behavior.

**Verification update (2026-11-19):** Feature 005 is human-accepted. The user reports both independent read-only PowerShell procedures passed 10/10 checks. Automated upgrade, downgrade, re-upgrade, migration consistency, database tests, schema, vector, and integrity results are recorded in `EVIDENCE.md`. T001–T007 are complete; lifecycle database retained for read-only review.

## Phase 1: Setup

- [x] T001 Record Python dependency resolution and native Windows PostgreSQL 17/pgvector 0.8.7 installation prerequisites in `research.md`, `pyproject.toml`, and `uv.lock`; verify metadata before locking and do not install/start infrastructure without owner authorization

## Phase 2: Foundational

- [x] T002 Implement typed secret-safe database configuration, synchronous SQLAlchemy/psycopg engine setup, and pgvector connection registration in `src/sciscope/database/config.py`, `src/sciscope/database/session.py`, and RED-first `tests/database/test_configuration.py`
- [x] T003 Implement the Alembic environment, PostgreSQL-17/pgvector-0.8.7 preflight, and single initial revision in `alembic.ini`, `migrations/env.py`, and `migrations/versions/` after RED migration tests exist in `tests/database/test_migrations.py`; extension provisioning on native Windows requires an administrator, while migrations run as least-privilege `sciscope`

## Phase 3: User Story 1 - Reproduce the database environment (Priority: P1)

**Goal**: Produce a healthy, version-identified, secret-safe environment.

**Independent Test**: Validate configuration and, after authorization, prove
the service reports PostgreSQL 17 and pgvector 0.8.7.

- [x] T004 [US1] Complete RED/GREEN environment behavior and health/version integration coverage on native Windows in `tests/database/test_configuration.py` and `tests/database/test_environment.py`, recording native setup/runtime blockers as BLOCKED rather than skipped or passed

## Phase 4: User Story 2 - Create a constrained scientific schema (Priority: P2)

**Goal**: Create the six-table model with database-owned integrity.

**Independent Test**: Valid synthetic records succeed and each invalid
nullability, uniqueness, DOI/hash, same-import FK, hierarchy, active-import, and
1535/1537-dimension case fails on real PostgreSQL with zero orphans.

- [x] T005 [US2] Write and observe RED schema, relationship, catalog, and vector-dimension matrices in `tests/database/test_schema_constraints.py`, `tests/database/test_schema_relationships.py`, `tests/database/test_schema_catalog.py`, and `tests/database/test_vector_schema.py` for every verbatim rule in `data-model.md`
- [x] T006 [US2] Implement SQLAlchemy metadata and the reviewed migration GREEN in `src/sciscope/database/models.py` and `migrations/versions/`, including six tables, exact `vector(1536)`, composite same-import FKs, deferrable section parent FK, one-active partial unique index, required B-tree indexes, and no FTS/HNSW/IVFFlat index

## Phase 5: User Story 3 - Reproduce and inspect migration state (Priority: P3)

**Goal**: Prove migration lifecycle and hand off verified Feature 005 state.

**Independent Test**: Clean/repeated upgrade, one head, disposable
downgrade/re-upgrade, catalog equality, full checks, and human acceptance.

- [x] T007 [US3] Run focused and full verification from `specs/005-postgres-pgvector-foundation/quickstart.md`, obtain explicit human acceptance, and append actual PASS/FAIL/BLOCKED/NOT RUN results to `EVIDENCE.md` and synchronize only P3-01/P3-02 in `PROJECT_TODO.md` and this file

## Dependencies & Execution Order

- T001 precedes dependency or environment implementation.
- T002 and T003 are foundational; T004 depends on both.
- T005 must reach legitimate RED before T006; T006 reaches GREEN.
- T007 depends on T001â€“T006 and stops the feature for human verification.
- Feature 006 implementation depends on accepted Feature 005.

## Parallel Opportunities

After T003, configuration-focused T004 and RED schema-matrix preparation in
T005 touch different files, but schema implementation cannot begin before the
corresponding RED results are reviewed.

## Implementation Strategy

Complete only one task or tightly coupled RED/GREEN pair at a time. Preserve
all failures and corrections in evidence. Do not begin Feature 006
implementation automatically after Feature 005 acceptance.
