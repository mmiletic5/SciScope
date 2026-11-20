# Feature Specification: PostgreSQL and pgvector Foundation

**Feature Branch**: `005-postgres-pgvector-foundation`

**Created**: 2026-11-18

**Status**: Approved for later implementation; documentation only

**Input**: Approved Person 2 Phase A baseline for P3-01 and P3-02.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reproduce the database environment (Priority: P1)

As the Person 2 owner, I can create the same isolated database environment on
a supported development computer and verify its server and vector-extension
identity before storing scientific evidence.

**Why this priority**: Every schema and ingestion guarantee depends on a known,
real PostgreSQL/pgvector environment.

**Independent Test**: Starting from the documented prerequisites and an empty,
disposable environment, follow the quickstart and observe a healthy database
with the required server and extension versions without exposing credentials.

**Acceptance Scenarios**:

1. **Given** the approved prerequisites and local secret configuration, **When**
   the environment is started after explicit infrastructure authorization,
   **Then** it becomes healthy and reports PostgreSQL 17 and pgvector 0.8.7.
2. **Given** missing or unsafe configuration, **When** configuration is
   validated, **Then** startup is refused with an actionable error before data
   is created.

---

### User Story 2 - Create a constrained scientific schema (Priority: P2)

As the Person 2 owner, I can migrate a clean database to a schema that preserves
papers, section hierarchy, chunks, embedding metadata, vectors, and import
identity while rejecting invalid relationships and dimensions.

**Why this priority**: Scientific provenance must be enforced by the database,
not only trusted to application code.

**Independent Test**: Upgrade a clean real database, insert valid synthetic
records, and demonstrate that invalid DOI, hash, hierarchy, cross-import,
uniqueness, nullability, and vector-dimension cases fail without orphan rows.

**Acceptance Scenarios**:

1. **Given** a clean supported database, **When** migrations reach the single
   head, **Then** all approved tables, constraints, relationships, and indexes
   exist exactly once.
2. **Given** an invalid or cross-snapshot record, **When** it is inserted,
   **Then** a database constraint rejects it and the transaction can roll back.
3. **Given** a vector whose dimension is not 1536, **When** it is inserted,
   **Then** storage rejects it.

---

### User Story 3 - Reproduce and inspect migration state (Priority: P3)

As a maintainer, I can repeat upgrades, inspect the installed schema, and test a
downgrade only on a disposable database without silently removing the shared
extension or accepted corpus data.

**Why this priority**: Reproducible migrations and bounded rollback behavior
prevent environment drift and accidental data loss.

**Independent Test**: Upgrade twice, inspect the single head, downgrade and
re-upgrade a disposable database, and compare catalog state with the documented
model.

**Acceptance Scenarios**:

1. **Given** an already migrated database, **When** upgrade-to-head runs again,
   **Then** no schema change occurs.
2. **Given** a disposable migrated database, **When** downgrade-to-base runs,
   **Then** owned schema objects are removed and the shared vector extension is
   retained.
3. **Given** a non-disposable database with accepted evidence, **When** a
   destructive downgrade is contemplated, **Then** the documented safety gate
   requires explicit owner authorization.

### Edge Cases

- PostgreSQL is reachable but the server major or pgvector version differs.
- The migration graph contains multiple heads or model drift.
- Parent sections are inserted after children within one deferred transaction.
- A section parent belongs to another DOI or import.
- The same normalized DOI, section ID, chunk ID, or active import is duplicated.
- JSON arrays are empty where allowed but retain their delivered order.
- A credential-bearing URL is accidentally included in logs or evidence.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The native Windows environment MUST reproducibly provide
  PostgreSQL major 17 and pgvector extension version 0.8.7 using verified
  installer/source-build identities.
- **FR-002**: Local credentials MUST remain outside version control, command
  output, screenshots, and evidence.
- **FR-003**: Migrations MUST have one head, create the vector extension and
  approved schema, support repeated upgrade-to-head, and expose their revision.
- **FR-004**: The schema MUST represent delivery imports, embedding sets,
  papers, hierarchical sections, chunks, and chunk embeddings as defined in
  `data-model.md`.
- **FR-005**: Database constraints MUST enforce primary and foreign keys,
  same-import relationships, normalized DOI and digest shapes, required
  nullability, uniqueness, positive counts, and exactly 1536 vector dimensions.
- **FR-006**: Stored metadata MUST preserve exact delivered scientific scalar
  values and ordered arrays without normalization or silent repair.
- **FR-007**: At most one import MAY be active, while successful historical
  activation records remain identifiable.
- **FR-008**: Mandatory indexes MUST support relationship checks and planned
  metadata filters without adding FTS or approximate-vector behavior.
- **FR-009**: A disposable downgrade MUST remove feature-owned schema objects
  but MUST NOT drop the shared vector extension.
- **FR-010**: Real PostgreSQL/pgvector tests MUST prove migration and constraint
  behavior; mocks alone are insufficient.
- **FR-011**: Environment-dependent checks MUST be reported as PASS, FAIL,
  BLOCKED, or NOT RUN and never inferred from documentation.
- **FR-012**: Dense, lexical, and hybrid retrieval implementation MUST remain
  outside this feature, while their required provenance and filter fields are
  preserved.

### Key Entities

- **Delivery Import**: Immutable identity and activation audit for one accepted
  delivery snapshot.
- **Embedding Set**: Model, dimensions, prefixes, hashes, and normalization
  metadata for the snapshot's vectors.
- **Paper**: DOI-identified scientific work and exact delivered citation data.
- **Section**: DOI-bound hierarchy node with heading path and source locator.
- **Chunk**: Exact scientific evidence text, spans, locator, hashes, and
  deterministic ordinal.
- **Chunk Embedding**: One manifest-owned 1536-dimensional vector for a chunk.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A clean authorized environment reports PostgreSQL 17, pgvector
  0.8.7, one migration head, and a healthy status using the quickstart.
- **SC-002**: Migration upgrade succeeds twice without drift, and disposable
  downgrade/re-upgrade returns the same inspected schema.
- **SC-003**: Every listed invalid constraint and relationship case is rejected
  by a real database, with zero orphan rows afterward.
- **SC-004**: A 1536-dimensional vector is accepted and 1535- and
  1537-dimensional vectors are rejected.
- **SC-005**: Catalog inspection finds all required constraints and indexes and
  finds no HNSW, IVFFlat, or full-text index.
- **SC-006**: Automated checks and one explicit human verification are recorded
  before P3-01 or P3-02 is marked complete.

## Assumptions

- Person 2's development and verification environment is native Windows 10
  x64/PowerShell. Docker, WSL, Linux containers, and Linux-only dependencies
  are excluded from this feature's Person 2 workflow.
- PostgreSQL 17 remains the required server. The EDB Windows installer is the
  researched candidate; pgvector 0.8.7 is built from upstream source using
  Visual Studio C++ tools and `nmake`. Exact Windows 10 runtime compatibility
  is a verification gate, not an assumed fact.
- On this Windows installation, creating the extension requires a PostgreSQL
  administrator. The application role remains least-privileged; the
  administrator provisions the extension before the application migration.

- Native Windows 10 x64/PowerShell is mandatory for Person 2 development and
  verification; exact PostgreSQL 17/pgvector 0.8.7 compatibility must be
  demonstrated before the setup is called reproducible.
- The current corpus generation uses OpenAI `text-embedding-3-small` with 1536
  dimensions; a different dimension requires a future approved migration.
- This feature creates the foundation only and does not load the pilot.
- PostgreSQL operations run only after the owner authorizes infrastructure use.
