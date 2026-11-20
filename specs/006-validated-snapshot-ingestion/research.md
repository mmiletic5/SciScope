# Research: Validated Snapshot Ingestion

## Required Person 2 execution platform

Feature 006 runs only on native Windows 10 x64/PowerShell with the PostgreSQL
17/pgvector 0.8.7 instance established by Feature 005. All snapshot validation,
transactional import, lock/contention, rollback, reconciliation, and integration
tests remain real-database checks. Docker/WSL/Linux are excluded. Native Feature
005 compatibility is a prerequisite and has not yet been demonstrated; this
constraint does not weaken any importer behavior or data-integrity criterion.

## Existing solution and observed data

The implemented delivery subsystem already provides strict LF-only JSONL
reading, exact-size finite little-endian float32 loading, manifest-entry chunk
mapping, and full package validation. Phase A should reuse its contract and
validation semantics rather than create a competing data format.

Fresh planning observations for `data/delivery/pilot/`:

- Validator exit 0: 17 papers, 319 sections, 728 chunks, 728 vectors, six
  files, zero failures.
- Model is OpenAI `text-embedding-3-small`; dimensions are 1536; prefixes are
  empty; dtype is `float32-le`.
- Vector size is exactly 4,472,832 bytes.
- Chunk-file and embedding-entry positions differ at 727 of 728 positions.
- Delivery hashes match the manifest. These are read-only observations; no
  database import has been run.

## Decisions

### R1 — Validate before writes

**Decision**: Run the existing complete delivery validator, require contract
0.3.0 and a complete embedding set, then perform importer-specific compatibility
and ID-set checks before opening the mutation transaction.

**Rationale**: The existing validator is the authoritative producer/consumer
boundary. Import-specific checks add operation and database requirements without
modifying delivered data.

**Alternative**: Relying on database constraints alone would discover defects
after mutation begins and cannot validate package hashes or binary ownership.

### R2 — Stream vector rows by manifest entry

**Decision**: Iterate embedding-manifest entries and read one fixed 1536-float
little-endian row per entry. Emit `(chunk_id, input_sha256, vector)` in manifest
order and insert bounded batches inside one transaction.

**Rationale**: This preserves authoritative ownership and avoids materializing
future expanded corpora as Python float tuples. Existing validation still
checks the package before streaming.

**Alternative**: Joining `chunks.jsonl` and vectors by position is demonstrably
wrong for 727 pilot rows. Loading all widened Python floats is acceptable for
the pilot but unnecessarily constrains expansion.

### R3 — Explicit compare-and-swap replacement

**Decision**: Use `INITIALIZE` and `REPLACE` modes. A different active digest
requires `REPLACE` plus the exact expected active digest. Same active digest is
a true no-op. Compute digest from exact delivery-manifest bytes.

**Rationale**: Contract 0.3.0 describes a valid package but does not itself
authorize deletion. Explicit intent and expected-state comparison prevent an
ambiguous or stale operator action from replacing evidence.

**Alternatives**: Automatic different-digest replacement is too destructive.
Incremental merge needs producer change/tombstone semantics that do not exist.

### R4 — One transaction with fail-fast serialization

**Decision**: Acquire the transaction-scoped PostgreSQL advisory lock
`pg_try_advisory_xact_lock(1396918611, 1229803604)` before re-reading active
state. The two signed 32-bit keys encode ASCII `SCIS` and `IMPT`. On contention,
return `IMPORT_IN_PROGRESS`. Insert/verify/activate and old-corpus pruning use
one transaction and one commit.

**Rationale**: The lock serializes the application operation while the database
unique-active constraint provides defense in depth. Fail-fast behavior is
deterministic and retryable without an unbounded wait.

**Alternatives**: Process-local locks fail across processes. A blocking lock
can hang operators. Serializable isolation alone does not express one importer
and requires more retry policy.

### R5 — Compact audit, current corpus only

**Decision**: Retain immutable successful activation and embedding-set metadata,
but delete old corpus rows when replacing. Failed attempts and identical no-ops
do not create activation rows.

**Rationale**: This matches the approved compact audit and prevents stale rows
from becoming visible without indefinitely duplicating vector storage.

### R6 — Independent all-row verification

**Decision**: A verifier separate from importer internals compares every source
entity and all vector rows. Database-returned floats are repacked as
little-endian float32 before comparison with manifest-owned source bytes.

**Rationale**: Counts and samples cannot prove ownership. Full reconciliation
is feasible for the 728-vector pilot and creates the correct acceptance bar.

## External assumptions, not blockers

- The package is considered a complete snapshot only when the explicit
  operation and all completeness checks pass.
- Person 2 independently defines replacement behavior; this is not claimed as
  unrecorded team agreement.
- Person 3 may later consume retrieval interfaces, but ingestion exposes a
  stable Python contract without backend dependency.

## Remaining validation

All importer/database tests, advisory-lock behavior, binary database roundtrip,
real-pilot import, and clean retry are NOT RUN. They are Feature 006 acceptance
work. No paid API or embedding regeneration is needed.

## Implementation research update (2026-11-19): normalization field mismatch

Inspected the entire usage surface for `normalization_declared`, the Feature 005 model and migration, embedding producer and validator, delivery contract, data contract JSON, relevant plans, and database fixtures. The producer writes the method string `"l2"`; F003 and delivery schemas require exactly that string, and validation interprets it as a method. The Feature 005 SQLAlchemy model and initial migration define `normalization_declared` as Float. The only DB test assignment found uses numeric `1.0`; it is a synthetic fixture, not a documented interpretation. Feature 005's data-model says only "declared value" and does not explain its numeric meaning. No code yet consumes the numeric column.

Facts: the method (`l2`) and a numeric target norm (for example, 1.0) are distinct values. The exact source manifest preserves the method in JSONB. Nothing in the persisted contract explicitly declares a numeric target norm. Therefore the importer refuses to invent that scalar and returns `EMBEDDING_CONFIGURATION_MISMATCH` before inserting records. No schema or migration was changed.

Smallest no-schema-change proposal, subject to owner approval: explicitly define the existing Float column as the declared target L2 norm, persist 1.0 for the approved L2-normalized model, and continue preserving the producer's method string as `embedding_manifest.normalization.declared = "l2"`. Document the two separate semantics and test both persisted values. This requires no migration and preserves existing numeric rows, but adds an explicit interpretation not currently stated in Feature 005 documentation. If the owner rejects that inference, the semantically exact alternative is a forward Alembic migration that adds a `normalization_method` text field and revises the numeric column's nullability/meaning; existing rows must be backfilled only from their embedded manifests, and synthetic rows without that field must remain distinguishable. No migration is justified until the intended numeric meaning is approved.

## Implementation research update (2026-11-19): snapshot replacement ordering

Feature 005 models declare globally unique paper DOI, section ID, chunk ID, and section/ordinal constraints. A replacement package overlaps those global keys, so staging duplicate new rows before deleting old corpus rows cannot satisfy the accepted constraints. The importer instead prunes old corpus rows inside the same transaction before inserting replacements; PostgreSQL MVCC keeps the previously committed snapshot visible to other transactions until commit, and rollback restores it on failure. Audit and embedding-set history remain. This changes only internal statement ordering; the externally atomic old-or-new behavior and fixed schema remain intact.

## Owner decision (2026-11-19): normalization method and target norm

The owner approved the explicit no-migration mapping. Repository evidence: `src/sciscope/embedding/store.py` emits method `"l2"`; `src/sciscope/embedding/validate.py` rejects other methods and checks every measured vector norm against `1.0` within the configured tolerance. The delivery schema requires `"l2"` as a string. The accepted database Float remains the numeric target norm. The importer stores `1.0` in that scalar and preserves the source method unchanged in the embedding manifest JSONB and delivery-manifest audit. Tests assert both values separately. This is not a cast or equivalence between the method identifier and numeric target. No schema or migration change is made.
