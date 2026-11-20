# Research: PostgreSQL and pgvector Foundation

## Problem and verified repository state

Phase A needs a real database foundation for P3-01 and P3-02. At the original
planning audit there were no database dependencies, migrations, schema, or
Compose file. A later Feature 005 implementation attempt added code and Compose
artifacts; their state and limitations are in `EVIDENCE.md`. The project
requires Python 3.12.16. This research task did not execute a server, extension
build, or database compatibility command.

The delivery contract and pilot require OpenAI `text-embedding-3-small`, 1536
dimensions, preserved vectors, and manifest-entry chunk ownership. The existing
validator freshly reported 17 papers, 319 sections, 728 chunks, 728 vectors,
six files, and zero failures. This verifies input data, not a database.

## Decisions

### R1 — Native Windows database environment (approved 2026-11-19)

**Decision**: Person 2 development and verification must run natively on
Windows 10 x64/PowerShell. Preserve PostgreSQL 17 and pgvector 0.8.7. Do not
require Docker/Desktop, WSL, Linux, containers, or Bash-only tooling.

**Verified facts**: PostgreSQL's official Windows download page provides an
EDB-certified installer and lists PostgreSQL 17, tested on Windows Server 2019
and 2022; it says comparable desktop Windows releases can generally be expected
to work, but does not list Windows 10 as a tested platform. The official
pgvector upstream instructions describe a Windows source build with Visual
Studio C++ support, `nmake`, and the PostgreSQL installation's development
files. The upstream `setup-pgvector` repository documents the v0.8.7 build
steps. No official precompiled Windows pgvector binary/package was verified.

**Approach**: EDB PostgreSQL 17 Windows installer plus pinned pgvector v0.8.7
source compiled against that exact server installation. This is the smallest
native approach that preserves all fixed database requirements. It requires a
matching Visual Studio C++ toolchain and administrator-level install steps;
those are not executed by this documentation research.

**Risks and unknowns**: Exact Windows 10 build 19045 x64 install/service
behavior, EDB build availability, compiler compatibility, extension install
paths, and PostgreSQL/pgvector integration remain unverified. Reproducibility
requires an authorized rehearsal and recorded installer/build identities.
If this fails, stop and present the smallest alternative for explicit approval;
do not silently fall back to containers or change versions.

**Extension privilege on the verified local installation**: Person 2 reports
that this Windows PostgreSQL installation denied extension creation to the
`sciscope` application role. A PostgreSQL administrator must provision
`vector` in a database before migrations run as `sciscope`. Do not grant the
application role SUPERUSER or extension-install privileges. This is an
installation-specific observation, not a claim that every PostgreSQL build
requires superuser for every trusted extension.

**Sources**: [PostgreSQL Windows downloads](https://www.postgresql.org/download/windows/),
[PostgreSQL 17 platform notes](https://www.postgresql.org/docs/17/installation-platform-notes.html),
[pgvector Windows build instructions](https://github.com/pgvector/pgvector#installation),
[pgvector v0.8.7 Windows CI setup](https://github.com/pgvector/setup-pgvector).

The earlier Feature 005 attempt added `compose.yaml` and selected Docker
Compose. That approach is superseded for Person 2. The file remains untouched
because this task is documentation-only; Person 2 must not use it. Reconcile it
only in an authorized implementation/configuration change.

### R2 — Database and migration stack

**Decision**: Declare narrow compatible ranges and lock exact resolution with
uv: SQLAlchemy `>=2.0.58,<2.1`, Alembic `>=1.20.1,<2`,
`psycopg[binary]>=3.3.9,<4`, and pgvector-python `>=0.5.1,<0.6`.

**Rationale**: SQLAlchemy 2.0 has a dedicated psycopg 3 dialect; Alembic is its
established migration system; pgvector-python documents SQLAlchemy and psycopg
3 registration. Published metadata for these selected releases supports Python
3.12 or a lower minimum compatible with Python 3.12.

**Alternatives considered**: Raw psycopg migrations duplicate established
revision management. Psycopg 2 is legacy for new code. SQLAlchemy 2.1 is newer
but unnecessary for the approved scope. Async access adds complexity without a
Phase A requirement.

**Sources**: [SQLAlchemy PostgreSQL dialect](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html),
[SQLAlchemy 2.0.58](https://pypi.org/project/SQLAlchemy/2.0.58/),
[Alembic 1.20.1](https://pypi.org/project/alembic/),
[psycopg 3.3.9](https://pypi.org/project/psycopg/),
[pgvector-python 0.5.1](https://pypi.org/project/pgvector/0.5.1/).

**Verification limit**: Package metadata and official documentation were
accessible on 2026-11-18/19. Dependencies were not installed together and no
native Windows PostgreSQL integration test was run; runtime compatibility
remains NOT RUN.

SQLAlchemy and Alembic publish universal Python wheels. Psycopg 3 offers a
platform-independent `psycopg` package and an optional binary extra; pgvector-
python provides SQLAlchemy/psycopg adapters. This is package-platform evidence,
not proof that the compiled server extension or combined runtime works on
Windows 10. Exact resolved Windows wheels and the complete locked environment
still require `uv lock`/sync validation.

### R3 — Vector storage and indexing

**Decision**: Store one `vector(1536)` per chunk embedding. Add no HNSW,
IVFFlat, or full-text index in Feature 005.

**Rationale**: The dimension is fixed by the delivered embedding generation.
The database typmod provides an independent constraint. Exact retrieval is the
approved later baseline; approximate indexes require measured need.

### R4 — Provenance-preserving relational model

**Decision**: Use six tables: `delivery_imports`, `embedding_sets`, `papers`,
`sections`, `chunks`, and `chunk_embeddings`. Preserve scientific scalar values
exactly and ordered structured fields as JSONB arrays. Use composite foreign
keys with import identity to prohibit cross-snapshot relationships.

**Rationale**: The model matches the actual flat delivery while retaining a
separate embedding set and compact import audit. JSONB arrays preserve order
without inventing author/span entities before retrieval needs them.

### R5 — Migration rollback boundary

**Decision**: A disposable downgrade removes feature-owned schema but leaves
the shared vector extension. Downgrade of a database containing accepted corpus
data is a destructive operation requiring explicit owner authorization.

## Licenses and maintenance

SQLAlchemy, Alembic, and pgvector-python publish MIT licenses. Psycopg publishes
LGPL-3.0-only metadata. PostgreSQL and pgvector retain their upstream licenses.
No dependency is added by this documentation task; `uv.lock` remains unchanged.

## Remaining validation

- Native Windows PostgreSQL 17 installation, pgvector v0.8.7 source build,
  server version, and extension version: NOT RUN; requires explicit
  infrastructure authorization.
- Combined dependency installation and import smoke: NOT RUN.
- Alembic migration behavior and real constraint tests: NOT RUN.
- These are implementation verification gates, not unresolved design choices.
