# Phase B Retrieval Research

**Status:** Approved Person 2 internal implementation baseline (2026-11-19); shared-contract and migration approvals remain separate.

## Repository facts

Accepted Phase A state is recorded at 17 papers, 319 sections, 728 chunks, and 728 vectors. The schema stores exact chunk text, normalized DOI, journal, publication year, raw language, source URL/license, XML digest, normalized section type/path, source locator, spans, chunk hash, active delivery identity, and `vector(1536)` embedding set metadata. There is no retrieval module/test suite or FTS column/index. P1-09 and shared P1-11/P1-14 contract gates remain open. The canonical retrieval contract draft is `docs/contracts/retrieval-v1.md`.

## Authoritative documentation research (2026-11-19)

- pgvector v0.8.7 documents `<=>` as cosine distance and `1 - distance` as cosine similarity. Exact nearest-neighbor search is default and provides perfect recall. ANN indexes trade recall for speed; filtering is applied after approximate scans and can reduce returned matches. Exact search is the sound baseline for the present 728 vectors; do not add ANN in Phase B. [pgvector v0.8.7](https://github.com/pgvector/pgvector/tree/v0.8.7)
- PostgreSQL 17 supports explicit text-search configurations, weighted `tsvector`, `websearch_to_tsquery`, and `ts_rank_cd`. `websearch_to_tsquery` accepts user search text without syntax errors. `ts_rank_cd` includes proximity, but built-in ranking uses no global information and is not calibrated confidence. Proposed default: explicit English configuration, chunk text only, `ts_rank_cd` descending. [Text search controls](https://www.postgresql.org/docs/17/textsearch-controls.html)
- PostgreSQL recommends GIN for regular FTS. Expression indexes require explicit configuration and query expressions must match. Proposed GIN expression index on chunk text; its schema migration is separately gated. [Tables/indexes](https://www.postgresql.org/docs/17/textsearch-tables.html), [index types](https://www.postgresql.org/docs/17/textsearch-indexes.html)
- PostgreSQL 17 `REPEATABLE READ` holds one transaction snapshot across statements; `READ COMMITTED` obtains snapshots per statement. Proposed read-only `REPEATABLE READ` retrieval transaction makes active snapshot and result metadata consistent. [SET TRANSACTION](https://www.postgresql.org/docs/17/sql-set-transaction.html)
- PostgreSQL 17 ordinary `CREATE INDEX` runs transactionally and allows reads but blocks table writes for the build; `CREATE INDEX CONCURRENTLY` avoids write-blocking but cannot run in a transaction and has extra scans/failure cleanup. At the 728-row pilot, ordinary migration create/drop is the simpler recommendation with a planned quiet migration window. [CREATE INDEX](https://www.postgresql.org/docs/17/sql-createindex.html)
- PostgreSQL 17 stored generated columns occupy table storage and are computed on writes; adding one to an existing table rewrites the table and indexes. That is unnecessary overhead for the single Phase B FTS expression. [Generated columns](https://www.postgresql.org/docs/17/ddl-generated-columns.html), [ALTER TABLE](https://www.postgresql.org/docs/17/sql-altertable.html)

These sources verify engine capabilities, not team agreement on API or metadata semantics. No new package is recommended.

## Options and recommendation

Exact cosine over the delivered vectors + PostgreSQL English FTS + RRF is the least-complex approach aligned with the fixed corpus and stack. ANN now is unjustified without scale/latency evidence; an external BM25 system adds dependencies/operations and changes ranking semantics. Use RRF to combine ranks without pretending dense and lexical score scales match. Candidate pool and tie behavior are specified in the contract draft.

### FTS representation/index alternatives

| Option | Correctness/reproducibility | Pilot/growth trade-off | Decision |
|---|---|---|---|
| Compute `to_tsvector` per query, no index | Correct with explicit config and exact expression; easiest initial code | Full scan is acceptable to validate 728 chunks but grows linearly and makes routine lexical search less scalable | Keep as migration-independent test fallback only, not production target |
| GIN expression index on English `to_tsvector(text)` | Correct when query uses the same explicit `'english'::regconfig` expression; no duplicated search column | Smaller/simpler schema footprint; index computes on writes and stores lexemes. Appropriate for immutable snapshot corpus and avoids stored vector duplication | **Recommend**, additive migration required |
| Stored generated `tsvector` + GIN | Correct and auto-maintained; query need not repeat expression | Adds column/storage, table rewrite/locking consideration when added to populated table; no demonstrated benefit at 728 chunks | Reject for v1 simplicity; reconsider only if expression maintenance or multiple query paths justify it |

### Proposed migration shape (not authorized)

After the existing `f005_pgvector_foundation` revision, add a new Alembic
revision that creates only `ix_chunks_fts_english`:

```sql
CREATE INDEX ix_chunks_fts_english
ON chunks USING GIN (to_tsvector('english'::regconfig, text));
```

No table/column/data rewrite and no Phase A migration edit. Query predicate
must use the same explicit configuration/expression. Use ordinary transactional
`CREATE INDEX` in the migration: predictable Alembic rollback and straightforward
Windows/PostgreSQL support; it takes a table lock that blocks writes to
`chunks` during build. The corpus is only 728 rows and ingestion already
serializes complete imports; schedule migration without concurrent ingestion.
Avoid `CREATE INDEX CONCURRENTLY` because it cannot run in a normal transaction,
needs Alembic autocommit handling and has more complex invalid-index recovery,
without a write-availability requirement established here. Downgrade drops
only this index; upgrade failure rolls back transactionally. Validate on a
disposable/rollback-scoped `sciscope_test_005` migration test after verifying
the actual database identity, assert catalog expression/method, run EXPLAIN
as an informative check (planner may choose a sequential scan at this size),
exercise query equivalence, and verify downgrade/re-upgrade. Do not migrate
until explicit schema approval and Phase B feature approval.

## Ownership and remaining confirmations

- **Person 2 approved technical direction:** ADR-009 exact cosine/no ANN; ADR-010 English FTS with `websearch_to_tsquery`, `ts_rank_cd`, chunk text only; ADR-011 RRF k=60/one-based ranks/bounded pools/tie policy; AND/OR filter baseline; read-only repeatable-read; parameterized SQL, validation, sanitized errors/no fallback. GIN index preferred, migration unapproved.
- **Person 1:** confirm current source metadata/locator rules are sufficient and no additional persisted fields are needed. Do not change ingestion contract from retrieval assumptions.
- **Person 3:** confirm neutral service boundary, adapter ownership/configuration, error-to-HTTP mapping, and Phase B field scope.
- **Person 4:** confirm filter semantics and exact-value controls are usable in UI.
- **Team:** P1-11/P1-14 and Golden partition review. P1-09 is Person 2-owned but shared metadata meaning/UI representation needs P1/P3/P4 review.
- **Schema approver:** approve the proposed additive FTS index migration before any migration implementation.

## Facts versus gaps

Guaranteed Phase A persisted fields are those listed above, nonempty under the accepted model, with normalized DOI and fixed normalized section taxonomy. `publication_year` is persisted as an integer; language and journal source strings are preserved. Source locator is required and bound to the XML digest. The exact UI-facing canonical filter values, journal aliases, missing-value UX, API owner confirmation, and FTS migration are not established by existing approvals. See the dependency matrix and handoff in `plan.md`.
