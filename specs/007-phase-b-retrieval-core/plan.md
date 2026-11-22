# Implementation Plan: Phase B Retrieval Core

**Branch**: `007-phase-b-retrieval-core` | **Date**: 2026-11-19 | **Spec**: [spec.md](spec.md)

**Status:** As of 2026-11-19, Person 2 internal retrieval core (P3-05 through P3-08) was human-accepted and closed after owner-reported independent verification; shared contract, public facade, and schema gates remained open. The current T007 scope-limited approval record is stated below.

## Approved T007 public-facade amendment — scope-limited approval record

The project owner reports that all four team members (Persons 1–4) discussed
and agreed upon the proposed T007 public-facade amendment and its shared
integration direction. This user-reported human approval records the amended
T007 scope only. It does not authorize work beyond that scope, change the
acceptance of T002–T006, mark the broader P1-09/P1-11/P1-14 backlog tasks
complete, or change either shared contract's status.

Person 2 has delegated T007 implementation responsibility to Person 3. Person
2 remains an affected-module reviewer for every retrieval-owned source and
contract change. Person 1 reviews the public preservation of source metadata,
source locators, stable chunk IDs, and corpus provenance. The owner-reported
four-person agreement records the T007-scope P1-09 filter-semantics
confirmation and affected-owner/TEAM agreement for the P1-11/P1-14 facade
gate; it does not complete the broader P1 tasks in `PROJECT_TODO.md`. Person
3 owns later HTTP adaptation; P4-09 is excluded from T007. Because full
`retrieval.v1` compatibility includes the documented metadata filters, the
agreed facade continues to preserve those filter semantics.

Within the approved T007 scope, the public facade will expose only driver-independent DTOs,
typed sanitized exceptions, an injected query-embedder protocol, and a
`RetrievalService` boundary. Its public contract will accept the documented
`retrieval.v1` and `retrieval.v2` selectors and preserve their existing
semantics. It will not expose SQLAlchemy, ORM, connection, or private-core
types. A composition root owns database-engine lifecycle and injects it into a
concrete facade; the facade must not read environment configuration, create
credentials, or open database connections at import time.

The amendment preserves all retrieval algorithms, filters, rankings,
repeatable-read transaction behavior, database/schema behavior, and v1/v2
compatibility. It does not select a default retrieval mode, create a live query
embedding adapter, enable Gemini, or revise Feature 011's fake-only HTTP
metadata. Those choices remain separate approvals.

### Proposed T007 implementation increments

The following increments remain unchecked until their respective work is
performed and accepted. The dedicated
chronological record for implemented work will be
`docs/person3/FEATURE_007_T007_TEST_LOG.md`; it is not created by this
documentation-only amendment. `EVIDENCE.md` and `PROJECT_TODO.md` remain
unchanged until automated checks and feature-level human acceptance are
recorded.

| Increment | Goal and proposed files | RED then minimal GREEN | Verification and review | Proposed commit boundary |
|---|---|---|---|---|
| T007-A | Record the approved delegation, P1-09/P1-11/P1-14 gates, scope, reviews, and completion criteria in `specs/007-phase-b-retrieval-core/{spec,plan,tasks}.md`. | Documentation review; no behavior RED test. | Person 2, Person 1, Person 3, and required TEAM review. | `docs(retrieval): approve public facade amendment` |
| T007-B | After final review of T007-A, use the recorded T007-scope P1-09/P1-11/P1-14 and affected-owner agreement to add public DTOs and typed sanitized errors in proposed `src/sciscope/retrieval/{contracts,errors}.py`, exports in `__init__.py`, and `tests/retrieval/test_public_contracts.py`. Broader P1 completion is not a prerequisite. | RED: public imports and v1/v2 DTO/error conformance tests fail because the public API does not exist. GREEN: immutable public values validate/marshal without database or private-type imports. | Focused pytest, Ruff, formatter, and mypy; Person 2 reviews public contract compatibility. | `feat(retrieval): expose versioned retrieval contracts` |
| T007-C | Add proposed `src/sciscope/retrieval/service.py` and `tests/retrieval/test_public_service.py` for the facade and injected embedder seam. | RED: public service/fake conformance tests fail. GREEN: facade maps public values to the existing core and maps only sanitized public outcomes/errors, without changing private algorithms. | Focused checks; Person 2 verifies no algorithm, transaction, or database-lifecycle behavior changed. | `feat(retrieval): add public retrieval facade` |
| T007-D | Add offline conformance coverage in `tests/retrieval/test_public_contracts.py` and `test_public_service.py`. | RED: unsupported version, empty result, typed failure, fake-embedder, and no-private-import assertions fail. GREEN: deterministic fixtures pass with no database, network, paid provider, or private consumer import. | Focused tests plus applicable retrieval regression, Ruff, formatter, and mypy; Person 3 verifies consumer usability and Person 2 reviews conformance. | `test(retrieval): cover public facade conformance` |
| T007-E | Optionally verify the public facade through a proposed `tests/retrieval/test_public_postgres.py`. | No artificial database RED run. GREEN only after separately authorized guarded read-only execution against `sciscope_test_005`. | Explicit database authorization, read-only preflight, focused integration test, and human-observed result. | `test(retrieval): verify public facade on pilot` |
| T007-F | Complete the dedicated log, obtain feature-level human acceptance, then synchronize approved evidence/task/backlog records. | No artificial behavior test. | Preserve all prior results and corrections; update central records only after explicit acceptance. | Separate authorized documentation commit. |

Future Python work must invoke the repository's Google Python engineering skill.
Before each feature behavior-test increment, rerun solution research as required
by the repository workflow.

## Summary and architecture

Deliver a driver-independent retrieval subsystem with exact cosine, English PostgreSQL FTS, common filters, and deterministic RRF. `docs/contracts/retrieval-v1.md` is the only detailed contract source. Person 2 owns the Python service, validation, SQL, ranking, and provenance mapping. Person 3 consumes the protocol and owns HTTP orchestration/answer generation. Person 4 maps controls to request filters. Person 1 remains authority for persisted source metadata and locators.

```text
Person 1 delivery 0.3.0
  -> accepted Phase A active snapshot (immutable source values)
  -> Person 2 RetrievalService.retrieve(v1)
       -> injected QueryEmbedder for dense/hybrid only
       -> one shared filter predicate
       -> exact cosine and/or English chunk-text FTS
       -> RRF for hybrid
  -> response with exact chunk/source provenance + active snapshot identity
  -> Person 3 orchestration / answer generation / HTTP adapter
  -> Person 4 UI maps controls and displays citations/errors
```

## Contract boundaries

- Person 1 provides validated delivery metadata. Person 2 consumes fields as persisted and never rewrites them. DOI is lowercase-normalized; language (`EN`/`en`) and journal preserve source text. Section type is from the fixed taxonomy. Source locator is opaque and digest-bound. Nonempty DOI, title/authors, journal/year, language/license/URL, XML digest, normalized section/path, chunk ID/text/source locator/spans/hashes, delivery identity, and embedding configuration are guaranteed by accepted Phase A model/validator. Person 1 confirms semantics/stability; no upstream change is presumed.
- Person 2 provides `RetrievalService.retrieve(RetrievalRequest) -> RetrievalResponse | RetrievalError`, DTOs only, no ORM/connection values. Request and output fields/errors are specified in the contract document. Use deterministic fake embedder and fake service stubs for consumer work.
- Person 3 supplies query text/mode/top-k/filters and handles typed errors. The injected embedder protocol is owned by Person 2; live adapter/config ownership is proposed for Person 3. Person 3 maps errors to HTTP and owns later answer generation, citation validation, and decline behavior.
- Person 4 provides only user-selected filter values. Person 2 defines stable metadata filter values and validation; UI shows invalid request categories without leaking SQL/database errors. UI requests never include SQL/ORM names.

## Approved Person 2 defaults versus pending approval

**Person 2 technical approval in this turn:** ADR-009 exact cosine/no ANN; ADR-010 English FTS on chunk text only with `websearch_to_tsquery`/`ts_rank_cd`; ADR-011 RRF constant 60, one-based ranks, bounded pools, deterministic ties; AND across filter categories/OR within a category as baseline; read-only `REPEATABLE READ`; parameterized SQL, strict validation, sanitized errors, no mode fallback. GIN expression index preferred, but no migration is approved.

**External integration obligations, not internal design gaps:** the current approval record satisfies the T007-scope P1-09/P1-11/P1-14 and affected-owner agreement. `retrieval.v1` remains proposed and broader P1 task completion remains pending in repository records. Person 1 validates source assumptions; Person 3 validates consumer compatibility and eventual live adapter ownership; Person 4 validates UI mapping. The five/16 Golden partition remains the fixed plan. GIN migration requires separate schema approval. These are status/governance boundaries, not unresolved routine technical choices.

## Dependency and decision matrix

| Decision/dependency | Proposed resolution and rationale | Owner | Impacted components | Person 2 independent? | Required confirmation | Later-change consequence |
|---|---|---|---|---|---|---|
| P1-04 metadata fields | Use accepted delivery 0.3.0 and schema; immutable fields listed above; no added derived fields. | Person 1 | ingestion, DB mapping, retrieval provenance | Yes, implementation can consume existing fields; no changes upstream | Person 1 confirms field meanings and locator stability | New fields/meaning require delivery contract and migration/version review |
| P1-09 filters | Categories AND, values OR; years inclusive; section type enum; DOI uses accepted F001 prefix/URL/punctuation/lowercase normalization; language case-insensitive exact; journal trimmed input then exact case-sensitive stored value; omit unrestricted, null/empty invalid. | Person 2; Persons 1–4 agreement recorded for T007 | retrieval, API, UI | T007 facade work may proceed after T007-A review; broader task remains open | Broader P1-09 completion remains separate | Semantic change requires retrieval.v2 or explicit compatibility decision |
| ADR-009 dense | Exact pgvector cosine `<=>`; similarity `1-distance`; no ANN. | Person 2 | retrieval/query tests | Yes | None beyond feature approval | ANN later changes recall/ordering and needs measured approval |
| ADR-010 FTS | English config, `websearch_to_tsquery`, `ts_rank_cd`, chunk text only; score is not confidence. | Person 2 | SQL, retrieval contract, evaluation | Algorithm can start; indexed acceleration is blocked | Team can review reproducibility; schema approval for GIN index | Search fields/config/rank change alters lexical behavior and benchmark comparability |
| FTS index/migration | Add `ix_chunks_fts_english` GIN expression index on `to_tsvector('english'::regconfig, text)` in a new revision after F005; no stored column. Ordinary transactional index create/drop; migration blocked until separately authorized. | Person 2 recommendation | accepted schema/migration | Retrieval logic yes; migration no | Separate explicit schema approval | Query expression/config must match; production lexical scan stays linear if deferred |
| ADR-011 RRF | k=60, 1-based ranks, sum reciprocal contributions; effective pool min(eligible, max(50,5*top_k)), hard cap 250; tie by score, best branch rank, chunk ID. | Person 2 | retrieval.v1, hybrid, evaluation | Yes | Person 3 accepts response semantics | Any change alters ordering and evaluation reproducibility |
| ADR-012 filter semantics | AND categories/OR values; inclusive years; exact normalized type and journal; case-insensitive language; normalized DOI; omitted unrestricted; null/empty invalid. | Person 2 technical baseline; Persons 1–4 confirmation recorded for T007 | retrieval, backend DTO, UI | T007 facade work may proceed after T007-A review | Broader P1-09 completion remains separate | Change affects filters and retrieval.v1 compatibility |
| ADR-013 reranker | Out of Phase B; optional reranking remains Phase C and disabled absent benchmark. | Person 2 roadmap | later ranking | Yes; exclude now | No Phase B confirmation | Adding now expands contract and benchmarking scope |
| ADR-014 Golden partition | Five smoke IDs only; 16 other Golden v0 held for Phase D. | Person 2 proposed; Person 1/team governance | smoke/evaluation | Code may wire fixed IDs | External confirmation later; do not alter data now | Repartition invalidates prior comparability |
| P1-11/P1-14 + ADR-016 | Use the documented `retrieval.v1`/`retrieval.v2` boundaries for the approved T007 facade; stable DTO/errors, HTTP mapping remains adapter. | Persons 1–4 agreement recorded for T007 | backend and API integration | T007 facade work may proceed after T007-A review; contract status remains unchanged | Broader P1-11/P1-14 completion remains separate | Breaking change requires retrieval.v2 and coordinated adapters |
| ADR-015 embedder owner | Person 2 defines protocol and fake; propose Person 3 owns live provider adapter/secret config. | Persons 2/3 | AI config, query path | Fake/protocol independent; live path blocked | Person 3 explicitly agrees | Ownership/config changes can affect deployment and secrets handling |
| ADR-017 UI filters | UI uses category values and year bounds; API/server authoritative validation. | Persons 2/3/4 | UI controls, request DTO | Core independent | Person 4 confirms exact-match semantics workable | UI may need affordance/option changes |
| ADR-018 Phase A snapshot policy | Existing accepted policy unchanged; retrieval reads committed active snapshot, never changes it. | Person 2 | ingestion/retrieval transaction | Yes | None for retrieval; no writes | Snapshot semantics change risks mixed provenance |
| ADR-019 smoke/holdout | Run only five fixed smoke IDs in Phase B; 16 others remain held out for Phase D. | Persons 1/2/team | smoke tests/evaluation governance | Smoke wiring independent; partition change blocked | Person 1/team confirms governance | Repartitioning invalidates comparability and requires new version/audit |

## Error and UI behavior

The Python service returns `RetrievalResponse` or raises `RetrievalException`; it does not return error objects. Contract-level codes are `INVALID_REQUEST`, `UNSUPPORTED_CONTRACT_VERSION`, `CORPUS_NOT_LOADED`, `EMBEDDING_CONFIGURATION_MISMATCH`, `EMBEDDING_UNAVAILABLE`, `DATABASE_UNAVAILABLE`, and `RETRIEVAL_INTERNAL_ERROR`. A valid zero-hit request is successful with `EMPTY_RESULT` warning. Person 4 maps invalid filter/query to editable input, empty result to no matching evidence, unavailable corpus to service-not-ready, and transient provider/database errors to retry guidance. Person 3 translates exception to transport/HTTP. Exact UI copy and HTTP status values remain consumer choices, not unresolved Person 2 technical semantics.

## Implementation and testing plan

- Pure contract tests: JSON fixtures validate request/response/error shape and compatibility without DB/provider imports. A deterministic fake embedder returns configured vectors and records received config; a fixed `RetrievalService` stub lets Person 3/4 develop independently.
- SQL tests on real PostgreSQL: known-vector exact ordering/scores, FTS configuration/query/ranks, each filter and combinations, parameterization, ties, zero results, and one active snapshot across concurrent replacement. Use read-only transaction tests or rollback-scoped fixtures; main DB is never a target.
- RRF unit tests use fixed branch result lists and independent arithmetic oracle.
- Smoke: only `gq-sp-001`, `gq-cmp-001`, `gq-conf-001`, `gq-gap-001`, `gq-ins-001`; diagnostic only. Do not run the other 16 for tuning/benchmark claims.
- Native Windows PowerShell and existing Python/PostgreSQL only. After feature approval, use test-first RED/GREEN, regression/static checks and user independent read-only verification; do not mark complete before acceptance.

## Non-gating performance characterization

Record pilot row counts, PostgreSQL/pgvector versions, OS/runtime context, warm/cold classification, and repeated median/p95 database durations by mode using deterministic offline query vectors. Report observations only; no numeric latency target or quality claim is set. Query-embedding duration is omitted from fake-based measurements and no live provider is called. A later Phase D benchmark owns reproducible quality/latency comparison. For the optional GIN migration, EXPLAIN/catalog checks verify index eligibility; PostgreSQL may correctly choose a sequential scan at 728 chunks, so index use is not an acceptance condition at pilot size.

## Safe-to-start versus blocked tasks

**Independent after feature spec/plan approval:** contract example fixtures and deterministic fakes; internal request validation prototypes; pure RRF; exact dense query tests/implementation against current schema; FTS correctness tests using the explicit expression; provenance mapping from accepted schema. Do not publish production shared DTO/service models until P1-11/P1-14 owner review. The GIN migration is separable from retrieval correctness.

**Gated or pending:** T002-T006 internal implementation and verification are complete and owner-accepted behind the private boundary. The recorded T007-scope agreement covers publication of the planned facade without changing `retrieval.v1` status or broader P1 completion. Applying the GIN migration requires separate schema approval. Live adapter implementation remains gated on ownership/configuration confirmation. Five-question smoke, cross-contract conformance, and warm/cold observations remain integration follow-ups; the 16 held-out questions remain untouched. Any later database verification must target exactly `sciscope_test_005`, use read-only preflight, and avoid printing or persisting credentials.

## Risks

- The old retrieval-v1 draft included later-phase lookup, reranker, token selection, and timing fields; the revised Phase B contract removes them. If an actual consumer depends on those fields, that is a compatibility issue to resolve before shared contract adoption.
- `journal` is persisted as source string without canonical aliases. The reference design uses exact matching after request trim; future canonical aliases require an explicit metadata contract extension.
- English FTS is correct for the English Golden smoke, not a multilingual retrieval claim. Unsupported languages are not translated or silently routed to another config.
- GIN migration is not authorized. If delayed, correctness can be tested without it, but performance remains unclaimed.
- Exact search is a correctness baseline; no latency SLO is established.

## Integration handoff package

Canonical contract and examples: [`docs/contracts/retrieval-v1.md`](../../docs/contracts/retrieval-v1.md). Consumers use JSON fixtures and protocol stubs, never import Person 2 ORM modules. Contract-test expectations, `FakeQueryEmbedder`, and fixed retrieval-service stubs are specified there. The current owner-reported Persons 1–4 agreement records the T007-scope approval of metadata/provenance review, the public facade, and UI mapping. Later HTTP integration, live embedder ownership, and P4-09 remain separate.

## Implementation and remaining approval checkpoints

The owner approved the specification and plan and human-accepted the internal retrieval core on 2026-11-19. T002-T006 are complete. The current approval record satisfies the T007-scope P1-11/P1-14 and affected-owner facade gate; T007-B follows final T007-A review. The proposed GIN migration remains blocked on separate schema approval. Direct committed concurrent activation is not exercised because it would require persistent changes visible to other database clients; repeatable-read mode and single-snapshot provenance are tested. See the specification acceptance record and `EVIDENCE.md` for exact verification and remaining limits.
