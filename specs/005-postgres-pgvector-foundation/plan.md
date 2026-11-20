# Implementation Plan: PostgreSQL and pgvector Foundation

**Branch**: `005-postgres-pgvector-foundation` | **Date**: 2026-11-18 | **Spec**: [spec.md](spec.md)

**Input**: Approved Phase A Feature 005 specification for P3-01 and P3-02.

## Summary

Create a reproducible PostgreSQL 17/pgvector 0.8.7 environment and a constrained
six-table scientific evidence schema. Use SQLAlchemy 2.0, psycopg 3,
pgvector-python, and Alembic; prove migrations and constraints with real
PostgreSQL tests before ingestion begins.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: SQLAlchemy `>=2.0.58,<2.1`, Alembic
`>=1.20.1,<2`, `psycopg[binary]>=3.3.9,<4`, pgvector-python
`>=0.5.1,<0.6`; exact transitive resolution deferred to approved `uv lock`

**Storage**: Native PostgreSQL 17 with pgvector 0.8.7; record installer and
source-build identities rather than a container image digest

**Testing**: pytest unit tests plus mandatory real PostgreSQL/pgvector
integration tests; mocks cannot substitute for migration or constraint checks

**Target Platform**: Native Windows 10 x64, Windows PowerShell, Python 3.12;
PostgreSQL 17 with pgvector 0.8.7 installed natively. No Docker, WSL, Linux
container, Bash-only, or Linux-only dependency. PostgreSQL/extension
installation and service/database use require explicit infrastructure
authorization.

**Project Type**: Python library foundation with migration and environment tooling

**Performance Goals**: No retrieval latency target; clean migration and pilot-
scale constraint checks must complete deterministically

**Constraints**: No credentials in Git/evidence; no paid API; no application,
retrieval, ingestion, FTS, or approximate-index implementation in this feature

**Scale/Scope**: Six tables supporting the 17-paper pilot and later complete
snapshots without a schema redesign for planned metadata filtering

## Constitution Check

- **Specification and Approval**: PASS. Research, specification, plan, and
  tasks are separate artifacts; implementation waits for owner authorization.
- **Test-First Delivery**: PASS. Tasks require recorded real-database RED before
  schema/migration GREEN and one later human verification.
- **Scientific Provenance**: PASS. The model preserves delivered identifiers,
  source locators, metadata, hashes, processing versions, and vector ownership.
- **Shared Contracts**: PASS. Delivery 0.3.0 is referenced, not modified.
  Retrieval interfaces remain outside scope.
- **Secure, Reviewable Code**: PASS. Planned Python is typed and English-only;
  secrets remain local; the feature is seven tasks.

Post-design recheck: PASS. The data model, quickstart, and task gates add no
constitution exception.

## Architecture and data flow

```text
approved local configuration
  -> native Windows PostgreSQL/pgvector environment
  -> version preflight
  -> Alembic single-head migration
  -> constrained relational/vector schema
  -> catalog and real-database integration verification
  -> Feature 006 ingestion boundary
```

SQLAlchemy declarative metadata represents schema intent. Alembic revisions are
the deployment authority. Psycopg 3 is the synchronous driver; pgvector-python
registers vector adaptation on connections. Raw SQL is limited to extension,
catalog/version, partial-index, and advisory features that require explicit
PostgreSQL semantics.

## Migration and rollback design

- Preflight requires PostgreSQL major 17.
- A PostgreSQL administrator provisions `vector` in a new database because the
  native Windows installation denies extension creation to the least-privilege
  `sciscope` application role. The migration uses `IF NOT EXISTS` and verifies
  extversion 0.8.7; it does not require granting superuser to the application.
- One initial revision creates the six tables in dependency order.
- A repeated upgrade to the same head is a no-op.
- Disposable downgrade removes owned objects in reverse order but retains the
  extension. Accepted-data downgrade is an explicitly destructive operation.
- Autogeneration output is reviewed against `data-model.md`; drift fails
  `alembic check`.

## RED/GREEN test design

1. Write configuration behavior tests and observe RED before configuration code.
2. Write clean/repeated/downgrade migration tests and observe RED before the
   Alembic environment and revision exist.
3. Write catalog and constraint matrices before completing schema definitions.
4. Run each RED against real PostgreSQL when the behavior is database-owned.
5. Implement the smallest GREEN behavior, refactor, rerun focused tests, then
   run full Feature 005 and regression checks.

Required cases: server/extension mismatch; one head; clean and repeated upgrade;
disposable downgrade/re-upgrade; every PK/FK/unique/check/nullability rule;
same-import hierarchy; one active import; vector dimensions 1535/1536/1537;
zero orphans; required indexes; absence of HNSW/IVFFlat/FTS.

## Error and security boundaries

- Configuration errors are actionable but never echo credentials.
- Database connection and version failures are explicit; no fallback database.
- Evidence records server, extension, installer/compiler, source tag, and
  migration versions, not passwords or URLs containing passwords.
- Infrastructure checks not executed are BLOCKED or NOT RUN, never PASS.

## Project Structure

### Documentation (this feature)

```text
specs/005-postgres-pgvector-foundation/
├── checklists/requirements.md
├── data-model.md
├── plan.md
├── quickstart.md
├── research.md
├── spec.md
└── tasks.md
```

### Planned implementation (not created by this documentation task)

```text
alembic.ini
compose.yaml
migrations/
src/sciscope/database/
tests/database/
```

**Structure Decision**: Keep database configuration, SQLAlchemy metadata, and
session/vector registration in `sciscope.database`; keep migrations and tests
at repository-standard top-level locations. Feature 006 receives a separate
ingestion package.

## Verification and acceptance

Run the commands in [quickstart.md](quickstart.md) only after infrastructure
authorization. Record exact PostgreSQL, pgvector, installer/build, migration,
test, Ruff, mypy, diff, and working-tree results. Feature 005 stops awaiting explicit human
verification before any Feature 006 implementation.
