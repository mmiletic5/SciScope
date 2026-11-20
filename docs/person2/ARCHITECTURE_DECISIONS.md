# Person 2 Architecture Decision Register

This register distinguishes requirements, the approved working baseline,
proposals that need phase approval, and shared decisions awaiting owner review.
Master-plan approval does not authorize implementation.

## Required or approved baseline

| ID | Status | Decision | Source or rationale |
| --- | --- | --- | --- |
| P2-ADR-001 | Required | Use OpenAI `text-embedding-3-small`, 1536 dimensions, and empty prefixes for the delivered pilot and compatible queries. | Organizer requirement and delivery manifest |
| P2-ADR-002 | Required | Preserve delivered vectors and resolve ownership by embedding-manifest `chunk_id`, never positional order. | Delivery contract and handoff |
| P2-ADR-003 | Approved baseline | Phases A-E collectively implement persistence, dense/lexical/hybrid retrieval, filtering, ranking, optional reranking evaluation, context selection, citations, and evaluation. | Master-plan approval 2026-11-18 |
| P2-ADR-004 | Superseded 2026-11-19 | Docker Compose was the earlier preferred local/CI environment. The permanent Person 2 requirement is native Windows PowerShell and PostgreSQL; Docker/WSL/Linux containers are excluded from Person 2 workflows. | Person 2 explicit architecture decision |
| P2-ADR-005 | Approved baseline | SQLAlchemy and Alembic over psycopg are the preferred persistence/migration stack; implementation remains unapproved. | User-selected planning preference |
| P2-ADR-006 | Approved baseline | Query embedding is injected through a Person 2 protocol. | User-selected planning preference |

## Proposed phase decisions

| ID | Status | Proposal | Approval needed |
| --- | --- | --- | --- |
| P2-ADR-007 | Superseded 2026-11-19 | The required versions remain PostgreSQL 17 and pgvector 0.8.7, but Person 2 must install PostgreSQL natively on Windows and build pgvector from upstream source against that server. The earlier official container image choice is not applicable to Person 2. | Person 2 permanent native Windows decision; compatibility rehearsal outstanding |
| P2-ADR-008 | Approved Phase A technical baseline; implementation unapproved | Treat delivery 0.3.0 as the current input format. Initialize explicitly; same active digest is a no-op; different digest requires explicit replace mode plus matching expected active digest; import and activation are atomic; incremental updates are deferred. | Feature 006 approved for documentation 2026-11-18 |
| P2-ADR-020 | Approved permanent Person 2 environment requirement, 2026-11-19 | All Person 2 work in Phases A–E and future features must run natively on Windows 10 x64/PowerShell. Preserve approved PostgreSQL 17, pgvector 0.8.7, Python 3.12, data contracts, algorithms, tests, and acceptance criteria. No Docker/Desktop, WSL, Linux distributions/containers, Bash-only scripts, or Linux-only dependencies. | Explicit Person 2 decision |
| P2-ADR-021 | Native approach researched; exact Win10 verification outstanding | Use PostgreSQL's EDB Windows installer, then build pgvector v0.8.7 from its official source using Visual Studio C++ tools and `nmake`, unless an official compatible Windows binary is verified later. | Native Windows compatibility rehearsal required |
| P2-ADR-009 | Proposed; Person 2 technical direction approved 2026-11-19; feature approval pending | Use exact pgvector cosine distance `<=>`, expose `1 - distance` similarity, and defer ANN. Exact search is the perfect-recall baseline for the 728-vector pilot; ANN can change results and filtered scans may under-return. | Phase B; see PostgreSQL/pgvector research in Feature 007 |
| P2-ADR-010 | Proposed; Person 2 technical direction approved 2026-11-19; schema migration pending | Use explicit PostgreSQL English FTS over chunk text only with `websearch_to_tsquery` and `ts_rank_cd`; rank is not calibrated confidence. Prefer GIN expression index on the matching English `to_tsvector`; no schema migration until separately approved. | Phase B; see Feature 007 research and migration proposal |
| P2-ADR-011 | Proposed; Person 2 technical direction approved 2026-11-19; shared contract pending | Deterministic RRF k=60, one-based ranks, reciprocal sum, candidate union by `chunk_id`, pool default `min(eligible_count, min(250, max(50, 5*top_k)))`, explicit pool 1..250 and >= top_k, final order by fusion descending, best branch rank ascending, chunk ID ascending. | Phase B; retrieval.v1 draft |
| P2-ADR-012 | Proposed shared semantics; Person 2 baseline approved 2026-11-19; cross-boundary confirmation pending | AND across categories, OR within categories; inclusive years; normalized type taxonomy; exact journal after input trim; case-insensitive exact language; trim/lowercase DOI exact; omitted unrestricted; explicit null/empty/blank/duplicate arrays invalid. Request normalization never rewrites persisted source values. | P1-09 and eventual Person 1/3/4 integration review |
| P2-ADR-013 | Approved Phase C scope (2026-11-19); production disabled | Implement optional no-op/fake/local MiniLM benchmark where local artifacts/runtime are available. Use approved diagnostic quality thresholds and bounded warm latency criteria; benchmark absence is documented if no compatible offline candidates/artifacts exist. Production remains disabled pending later approval. | Feature 008 approval; see spec/plan and research |
| P2-ADR-014 | Approved for Phase C isolation (2026-11-19) | Only `gq-sp-001`, `gq-cmp-001`, `gq-conf-001`, `gq-gap-001`, and `gq-ins-001` may be used in Phase C; all other 16 Golden v0 questions remain unopened/held for Phase D. | User approval and existing evaluation protocol |
| P2-ADR-022 | Approved for Phase C implementation (2026-11-19) | Deduplicate exact `(normalized DOI, primary source locator, exact text)` without modifying Phase B; apply configurable per-DOI cap default 2, with `None` disabling and integer 1–50 setting the cap. | Feature 008 approval |
| P2-ADR-023 | Approved for Phase C implementation (2026-11-19) | Context budgeting uses an injected deterministic tokenizer with exact configured identity match; no provider tokenizer is assumed. | Feature 008 approval |
| P2-ADR-024 | Approved for Phase C implementation (2026-11-19) | Evidence lookup supports exact normalized DOI, `(DOI, opaque locator)`, and lowercase chunk ID against one read-only active REPEATABLE READ snapshot with captured provenance. | Feature 008 approval |

## Cross-team decisions awaiting confirmation

| ID | Status | Decision awaiting confirmation | Required reviewers |
| --- | --- | --- | --- |
| P2-ADR-015 | Cross-team review | Person 2 owns injected query-embedder protocol and fake; proposed Person 3 ownership for live OpenAI adapter/config. | Persons 2 and 3 |
| P2-ADR-016 | Cross-team review | `retrieval.v1` request, response, error, score, and compatibility semantics become the shared backend contract. | Persons 2 and 3 |
| P2-ADR-017 | Cross-team review | Filter semantics support the intended frontend controls. | Persons 2, 3, and 4 |
| P2-ADR-018 | Person 2 decision; external assumption documented | Full-snapshot replacement is a Person 2 implementation policy. A package is complete only after full validation; replacement is explicit, compare-and-swap guarded, serialized with a transaction advisory lock, and preserves delivery bytes/provenance unchanged. | Person 2 Phase A baseline 2026-11-18 |
| P2-ADR-019 | Cross-team review | Golden smoke/held-out separation and Golden v1 curation protocol are accepted. | Persons 1 and 2 |

## Deferred decisions

- HNSW parameters and activation threshold await expanded-corpus measurements.
- BM25 would require a separately approved extension or external component.
- A concrete reranker is selected only after an approved benchmark.
- Incremental corpus delivery requires a new versioned producer/consumer
  contract, deletion semantics, and separate feature approval.

## Phase A implementation boundaries

- `importer.v1` is the stable Person 2 ingestion boundary; it exposes no ORM or
  driver types.
- All 728 pilot vectors must be verified by manifest chunk ID and original
  little-endian float32 bytes. Sampling cannot satisfy Phase A acceptance.
- Real PostgreSQL/pgvector migration, constraint, transaction, rollback, and
  concurrency tests are mandatory. Mocks cannot replace them.
- Native Windows PostgreSQL installation/service setup and database creation
  require explicit infrastructure authorization. Do not use Docker/WSL.
- Destructive operations remain separately authorized.
- Feature 005/006 code, migrations, dependencies, and tests require their
  feature-specific authorization.

