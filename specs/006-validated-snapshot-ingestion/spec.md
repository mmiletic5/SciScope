# Feature Specification: Validated Snapshot Ingestion

**Feature Branch**: `006-validated-snapshot-ingestion`

**Created**: 2026-11-18

**Status**: Human-accepted by Person 2 owner on 2026-11-19 after independent full-suite and read-only verification

**Input**: Approved Person 2 Phase A baseline for P3-03 and P3-04.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Import a complete validated snapshot (Priority: P1)

As the Person 2 owner, I can import the current complete delivery into an empty
database without altering scientific data or regenerating embeddings.

**Why this priority**: A correct initial corpus is the foundation for every
later retrieval and citation result.

**Independent Test**: Import a valid complete synthetic snapshot into a clean
real database and independently reconcile every record and vector against the
source package.

**Acceptance Scenarios**:

1. **Given** an empty migrated database and a valid complete delivery, **When**
   initialization runs, **Then** exactly one active snapshot is committed with
   all papers, sections, chunks, embeddings, and provenance.
2. **Given** an invalid, incomplete, corrupt, or incompatible delivery, **When**
   initialization is attempted, **Then** it fails before corpus mutation.
3. **Given** a valid delivery, **When** vectors are decoded, **Then** every row
   is owned by `embedding_manifest.entries[i].chunk_id`, never chunk-file
   position.

---

### User Story 2 - Reimport or replace safely (Priority: P2)

As the Person 2 owner, I can reimport the identical snapshot as a true no-op or
explicitly replace the active corpus with a different complete snapshot without
exposing mixed or stale evidence.

**Why this priority**: Corpus evolution must not duplicate data, retain removed
evidence, or destroy a newer active snapshot accidentally.

**Independent Test**: Import one snapshot, repeat it, then replace it with a
different valid snapshot using the expected active digest and independently
prove audit, corpus, and vector state after each operation.

**Acceptance Scenarios**:

1. **Given** the incoming digest equals the active digest, **When** either mode
   runs, **Then** it returns `unchanged` and mutates no row or audit timestamp.
2. **Given** a different digest and initialize mode, **When** import runs,
   **Then** it fails with `REPLACEMENT_REQUIRED`.
3. **Given** a different complete snapshot and matching expected active digest,
   **When** explicit replacement runs, **Then** the new corpus becomes active
   atomically and absent old chunks/vectors are no longer visible.
4. **Given** a missing or stale expected active digest, **When** replacement is
   attempted, **Then** it fails without changing the active corpus.

---

### User Story 3 - Recover from failures and concurrent attempts (Priority: P3)

As a maintainer, I can prove that validation, database, verification,
interruption, or concurrent-import failures cannot mix snapshots or remove the
previous active corpus.

**Why this priority**: Transactional recovery and serialization turn a correct
happy path into a reliable ingestion system.

**Independent Test**: Inject failure at every mutation stage and coordinate two
real database connections; compare complete database fingerprints before and
after failure and retry.

**Acceptance Scenarios**:

1. **Given** an active corpus, **When** any replacement stage fails, **Then** the
   transaction rolls back and the old database fingerprint remains identical.
2. **Given** one importer holds the ingestion lock, **When** another starts,
   **Then** the second receives `IMPORT_IN_PROGRESS` and performs no mutation.
3. **Given** a failed or interrupted import, **When** the valid operation is
   retried, **Then** it completes or returns an idempotent no-op.

### Edge Cases

- All six files exist but a report, count, hash, ID set, or model fact differs.
- Manifest status is partial or contract version is not 0.3.0.
- Vector file is truncated, has trailing bytes, contains a nonfinite float, or
  disagrees with the manifest dimension.
- Chunk order differs from vector-entry order at nearly every position.
- Two valid but different replacements start concurrently.
- The active corpus changes after an operator reads its digest but before
  replacement begins.
- A historically used digest is intentionally activated again.
- Database verification fails after inserts but before activation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The importer MUST treat delivery contract/schema version 0.3.0 as
  the authoritative current input format and reject unsupported versions.
- **FR-002**: The importer MUST require the complete six-file package, three
  matching reports, complete embedding status, exact hashes/sizes/counts, and
  exact cross-record and chunk/vector ID sets before mutation.
- **FR-003**: The importer MUST require OpenAI `text-embedding-3-small`, 1536
  dimensions, `float32-le`, and empty current passage/query prefixes.
- **FR-004**: Delivered embeddings MUST be preserved without regeneration or
  paid API calls.
- **FR-005**: Vector row `i` MUST belong only to embedding-manifest entry `i`'s
  chunk ID and input hash; chunk-file position MUST NOT establish ownership.
- **FR-006**: DOI, source locators, section IDs, XML/text hashes, spans, chunk
  text, citation metadata, ordered arrays, and processing versions MUST be
  stored without silent alteration or repair.
- **FR-007**: Initial import MUST require initialize mode and an empty active
  corpus, except that identical active reimport returns an unchanged result.
- **FR-008**: A different active snapshot MUST require explicit replace mode
  and an expected active digest equal to the locked current digest.
- **FR-009**: Validation and replacement MUST occur with one database commit;
  any failure MUST leave the previous committed active corpus unchanged.
- **FR-010**: Imports MUST be serialized with a transaction-scoped advisory
  lock; a concurrent attempt MUST fail without mutation as `IMPORT_IN_PROGRESS`.
- **FR-011**: Successful activations MUST retain consistent immutable audit
  records; identical no-op and failed imports MUST NOT create false activations.
- **FR-012**: After replacement, no absent old paper, section, chunk, or vector
  MAY remain in the active corpus.
- **FR-013**: The importer MUST verify counts, ownership, dimensions, and zero
  orphans inside the transaction before activation.
- **FR-014**: An independent verifier MUST compare source and database state
  without calling importer internals, including all vector binary rows.
- **FR-015**: Real PostgreSQL/pgvector tests MUST cover success, rollback,
  idempotency, replacement, and concurrency; mocks alone are insufficient.
- **FR-016**: Errors MUST use stable sanitized codes and MUST NOT expose article
  text, vector values, credentials, or local absolute paths.

### Key Entities

- **Import Request**: Package/report locations, explicit operation mode, and
  optional expected active digest.
- **Import Result**: Activated/imported/no-op identity and exact stored counts.
- **Validated Snapshot**: Immutable pre-write representation of a complete,
  compatible delivery and its computed digest.
- **Active Corpus**: The one committed snapshot visible to later retrieval.
- **Import Audit**: Immutable successful activation identity and metadata.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The real pilot imports to exactly 17 papers, 319 sections, 728
  chunks, and 728 vectors with zero orphans.
- **SC-002**: All 728 stored vectors have 1536 dimensions and byte-match their
  manifest-owned source rows after little-endian float32 repacking.
- **SC-003**: Independent reconciliation reports zero missing/extra identities,
  provenance mismatches, dimension mismatches, and vector-byte mismatches.
- **SC-004**: Identical reimport leaves a complete database fingerprint and
  audit timestamps unchanged.
- **SC-005**: Valid changed-snapshot replacement removes every absent old record
  and exposes one internally consistent new active corpus.
- **SC-006**: Every injected validation/import/verification failure leaves the
  previous database fingerprint unchanged and permits a safe retry.
- **SC-007**: In a synchronized two-connection test, exactly one importer owns
  the lock and the other makes zero database changes.
- **SC-008**: Full automated checks and explicit human verification are recorded
  before P3-03 or P3-04 is marked complete.

## Assumptions

- All Person 2 implementation, integration tests, importer operations, and
  reconciliation run natively on Windows 10 x64/PowerShell. The Feature 005
  PostgreSQL 17/pgvector 0.8.7 native compatibility gate must be satisfied
  first. Docker, WSL, Linux containers, and Linux-only dependencies are not
  permitted for this workflow.

- Delivery 0.3.0 does not itself authorize destructive replacement; replacement
  is an explicit Person 2 operation guarded by the expected active digest.
- Each accepted package is a complete snapshot only after all contract and
  completeness validation passes.
- Feature 005 is implemented and human-accepted before Feature 006 begins.
- Retrieval reads only committed state; PostgreSQL MVCC provides old-or-new
  visibility across the replacement commit.
