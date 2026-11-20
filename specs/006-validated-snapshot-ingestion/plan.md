# Implementation Plan: Validated Snapshot Ingestion

**Branch**: `006-validated-snapshot-ingestion` | **Date**: 2026-11-18 | **Spec**: [spec.md](spec.md)

**Input**: Approved Phase A Feature 006 specification for P3-03 and P3-04.

## Summary

Build a deterministic importer over delivery contract 0.3.0. Validate complete
snapshots before writes, stream little-endian vectors by authoritative manifest
chunk ID, import in one transaction, make identical imports true no-ops, guard
replacement with explicit intent and expected active digest, serialize writers
with a fail-fast advisory lock, and independently reconcile the real pilot.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Feature 005 database stack; existing
`sciscope.delivery` validator/reader; no additional dependency proposed

**Storage**: Accepted Feature 005 PostgreSQL 17/pgvector 0.8.7 schema

**Testing**: pytest unit and mandatory real PostgreSQL integration tests;
independent real-pilot verifier; deterministic failure injection

**Target Platform**: Native Windows 10 x64, Windows PowerShell, Python 3.12,
and native PostgreSQL 17/pgvector 0.8.7 as required by Person 2. Docker, WSL,
Linux containers, Bash-only scripts, and Linux-only dependencies are excluded.

**Project Type**: Typed Python ingestion library and offline verification CLI

**Performance Goals**: Pilot import is deterministic; vector decoding remains
bounded by one row/batch rather than full Python-float materialization

**Constraints**: No data mutation, embedding regeneration, live/paid API,
partial delivery merge, retrieval implementation, or silent fallback

**Scale/Scope**: Current 17/319/728/728 pilot plus compatible complete expanded
snapshots using the same contract and 1536-dimensional embedding configuration

## Constitution Check

- **Specification and Approval**: PASS. Feature artifacts and owner approval
  precede tests or implementation.
- **Test-First Delivery**: PASS. Every behavior has explicit RED/GREEN and real
  database acceptance; human verification remains required.
- **Scientific Provenance**: PASS. Exact DOI, locators, metadata, hashes, spans,
  text, processing versions, input hashes, and vector bytes are reconciled.
- **Shared Contracts**: PASS. Delivery 0.3.0 is consumed unchanged. Replacement
  is labeled a Person 2 policy. `importer.v1` isolates future callers.
- **Secure, Reviewable Code**: PASS. Eight tasks, typed English Python, sanitized
  errors, no credentials or paid calls.

Post-design recheck: PASS. Contract, operation model, and quickstart resolve all
implementation decisions without a constitution exception.

## Data flow

```text
six delivery files + three matching reports
  -> existing delivery validation
  -> importer compatibility/completeness validation
  -> exact manifest-byte delivery digest
  -> manifest-ordered streaming vector decoder
  -> database transaction + advisory lock
  -> locked active-state compare-and-swap
  -> for replacement, prune old corpus inside the transaction first
  -> load new inactive snapshot in bounded batches
  -> in-transaction counts/sets/orphan/dimension verification
  -> switch active audit
  -> one commit
  -> independent source/database reconciliation
```

## Validation and mapping

Reuse public delivery validation semantics. Import-specific validation requires
contract 0.3.0, complete status, exact current embedding configuration, DOI
already normalized, unique IDs, exact chunk/vector ID-set equality, and explicit
operation validity. Never write repaired files or normalized record copies.

The vector decoder walks `embedding_manifest.entries`; each entry consumes one
exact 6144-byte row. It rejects short/trailing/nonfinite/wrong-dimension data.
Chunk-file order is irrelevant. Batches reduce memory but never commit.

## Transaction and concurrency

- Validate bytes before mutation.
- Begin transaction; call
  `pg_try_advisory_xact_lock(1396918611, 1229803604)`, whose keys encode ASCII
  `SCIS`/`IMPT`. Contention is `IMPORT_IN_PROGRESS`.
- Re-read active digest under the lock and apply the state table in
  `data-model.md`.
- Insert new audit inactive. For replacement, remove old corpus rows before
  inserting the new corpus, then load and verify all new rows before switching
  active flags. The accepted Feature 005 schema has global entity keys, so
  overlapping DOI, section, and chunk identities cannot coexist during staging.
  This physical order remains invisible until commit under PostgreSQL MVCC; any
  failure rolls back and restores the previously committed snapshot.
- Commit once. Any exception rolls back to the old committed fingerprint.
- The partial unique active index is defense in depth; PostgreSQL MVCC exposes
  old or new committed corpus, never intermediate state.

## Independent reconciliation

The verifier cannot import or call importer internals. It reads source records
through delivery readers, queries the database read-only, compares complete ID
sets and exact scientific fields, asserts zero SQL orphans and vector dimension
1536, and compares every database vector after little-endian float32 repacking
with its manifest-owned binary row.

Expected pilot summary: 17 papers, 319 sections, 728 chunks, 728 vectors, and
zero missing IDs, extra IDs, provenance mismatches, wrong dimensions,
vector-byte mismatches, or orphans.

## RED/GREEN test design

1. Contract/error tests precede interface implementation.
2. Corrupt/incomplete/model/ID/vector matrices precede validation and decoding.
3. Initial import test reaches RED on a real migrated database before service
   code; GREEN requires independent state assertions.
4. No-op and explicit replacement matrices precede replacement logic.
5. Failure injection after every mutation stage and a two-connection barrier
   precede transaction/concurrency implementation.
6. Real pilot acceptance is last and never substitutes for synthetic negative
   cases. Every observed result is recorded honestly.

## Project Structure

### Documentation (this feature)

```text
specs/006-validated-snapshot-ingestion/
├── checklists/requirements.md
├── contracts/importer-v1.md
├── data-model.md
├── plan.md
├── quickstart.md
├── research.md
├── spec.md
└── tasks.md
```

### Planned implementation (not created by this documentation task)

```text
src/sciscope/ingestion/
tests/ingestion/
```

**Structure Decision**: Isolate import contract, validation adapter, vector
stream, transactional service, and verifier under `sciscope.ingestion`. Reuse
`sciscope.delivery` without changing delivered bytes or creating a second
contract definition.

## Verification and stop boundary

Run [quickstart.md](quickstart.md) after Feature 005 acceptance and explicit
infrastructure authorization. Record focused RED/GREEN, real-pilot results,
full regression, Ruff, mypy, diff, and human acceptance. Stop after Feature 006;
do not start retrieval Phase B automatically.
