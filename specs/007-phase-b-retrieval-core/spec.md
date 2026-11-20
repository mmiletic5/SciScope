# Feature Specification: Phase B Retrieval Core

**Feature Branch**: `007-phase-b-retrieval-core`  
**Created**: 2026-11-19  
**Status**: Person 2 internal retrieval core (P3-05 through P3-08) human-accepted and closed (2026-11-19); shared contract, facade, and migration gates remain pending.  
**Input**: Owner approval of the Person 2 retrieval core scope and implementation plan.

## User Scenarios & Testing

### User Story 1 — Retrieve exact dense neighbors (Priority: P1)

As a research workflow, I can retrieve the most similar stored evidence chunks for a query so relevant source passages are available with their provenance.

**Why this priority**: Dense retrieval is the semantic baseline and a direct prerequisite for hybrid retrieval.

**Independent Test**: Seed a real PostgreSQL test snapshot with vectors of known cosine ordering and verify ranked chunk IDs, scores, provenance, and deterministic ties.

**Acceptance Scenarios**:

1. **Given** compatible query and corpus embedding metadata, **When** dense retrieval runs, **Then** it returns the exact top-k by cosine similarity from only the active snapshot.
2. **Given** equal cosine scores, **When** the same request runs repeatedly, **Then** order is stable by the approved tie rule.
3. **Given** incompatible, zero-norm, wrong-dimension, or non-finite query vectors, **When** dense retrieval is requested, **Then** the private core raises a sanitized typed exception and no lexical fallback occurs.

### User Story 2 — Retrieve lexical matches and apply shared filters (Priority: P1)

As a research workflow, I can find keyword matches and constrain them with metadata filters consistently across all modes.

**Why this priority**: PostgreSQL FTS and agreed filter semantics provide transparent lexical retrieval and predictable scope controls.

**Independent Test**: Against the accepted corpus plus isolated fixtures, verify lexical ranking and each filter category independently and in combinations.

**Acceptance Scenarios**:

1. **Given** searchable English text, **When** lexical mode runs, **Then** PostgreSQL FTS returns matches ordered by `ts_rank_cd` with stable ties.
2. **Given** multiple filter categories and values, **When** retrieval runs, **Then** categories combine with AND and values within a category combine with OR, subject to the approved canonical matching rules.
3. **Given** omitted filters, **When** retrieval runs, **Then** the category is unrestricted; invalid bounds or explicitly empty/null arrays return `INVALID_REQUEST`.
4. **Given** valid filters excluding all rows, **When** retrieval runs, **Then** it returns an empty result with `EMPTY_RESULT`, not a failure or fallback.

### User Story 3 — Retrieve deterministic hybrid results (Priority: P1)

As a research workflow, I can combine semantic and lexical rankings so complementary evidence is returned in one stable list.

**Why this priority**: Hybrid retrieval is the Phase B integration outcome consumed by later ranking and backend work.

**Independent Test**: Use fixed dense and lexical result lists to verify RRF score, candidate union, cutoff, and deterministic ordering.

**Acceptance Scenarios**:

1. **Given** dense and lexical candidate lists, **When** hybrid mode runs, **Then** each candidate receives the sum of `1/(k + one-based branch rank)` for each branch in which it appears.
2. **Given** a candidate appears in both lists, **When** fusion runs, **Then** it appears once with both component ranks/scores.
3. **Given** equal fusion values, **When** results are emitted, **Then** ties follow the approved stable tie policy.
4. **Given** one branch fails, **When** hybrid retrieval runs, **Then** the private core raises a typed exception; no silent single-branch fallback occurs.

### User Story 4 — Consume a versioned shared retrieval boundary (Priority: P1)

As a downstream consumer, I can eventually call one versioned, driver-independent retrieval interface and receive typed outcomes, source provenance, and active corpus identity. The public shared facade is gated separately; the approved implementation scope is the private Person 2 retrieval core.

**Independent Test**: Contract tests exercise request/response examples, all modes, errors, and fake embedding without importing database internals.

**Acceptance Scenarios**:

1. **Given** a valid `retrieval.v1` request, **When** the service returns results, **Then** it echoes request identity, mode, effective filters, active delivery/corpus identity, embedding configuration, scores/ranks, and exact source locator/DOI provenance.
2. **Given** unsupported versions or malformed inputs, **When** validated by the private core, **Then** a typed exception with a stable code and sanitized message is raised.
3. **Given** no active corpus, **When** retrieval is requested, **Then** `CORPUS_NOT_LOADED` is returned.

## Edge Cases

- No active snapshot, active snapshot switched during a request, or no compatible embedding set.
- Empty/whitespace query; `top_k` below/above limits; reversed year bounds; invalid normalized type; duplicate filter values; explicit hybrid pool smaller than `top_k`.
- FTS query reduced to no lexemes (successful empty lexical branch); web-search punctuation/quotes remain parser-safe.
- Non-finite/out-of-range database/query vector, dimension mismatch, and equal or zero cosine values.
- No candidates, fewer eligible candidates than top-k, fewer eligible candidates than the effective default pool, or candidate only in one hybrid branch.
- Database outage, embedder timeout/provider failure, malformed embedding response, and internal query error.
- Snapshot activation during retrieval; every statement and provenance field must reflect one active snapshot identity.
- SQL injection attempts through text and filters; oversized inputs and error messages containing secret/path/data.

## Requirements

### Functional Requirements

- **FR-001**: The private Phase B core MUST implement dense, lexical, and hybrid modes in accordance with the proposed `retrieval.v1` semantics; publishing the shared service boundary remains a separate integration gate.
- **FR-002**: Dense mode MUST use exact cosine distance over stored pilot vectors and compatible query vectors; HNSW/approximate retrieval is out of scope.
- **FR-003**: Query embedding MUST be injected through a protocol and match active provider, model, dimensions, and query prefix; tests MUST use deterministic fakes and never call a paid provider.
- **FR-004**: Lexical mode MUST use PostgreSQL English full-text search via `websearch_to_tsquery` and `ts_rank_cd` over chunk text only. Scores are ordering signals, not confidence. The proposed GIN expression-index migration is separately gated.
- **FR-005**: All modes MUST apply one shared filter implementation before ranking. Categories combine with AND; values in one category combine with OR.
- **FR-006**: Filters MUST include inclusive publication-year bounds, normalized section types, journals, languages, and DOIs. Year bounds must be ordered. Types use the fixed taxonomy; journal matches exact persisted values after input trim; language matches case-insensitively; DOI input follows accepted F001 prefix/URL/punctuation/lowercase normalization then exact matching. Omitted categories are unrestricted; null, empty, blank, or post-normalization duplicate arrays are invalid. These are Person 2 proposed shared semantics; adoption remains subject to P1-09/P1-11/P1-14 review.
- **FR-007**: Hybrid mode MUST use bounded branch candidate lists and deterministic RRF with constant 60, one-based ranks, formula `sum(1/(60 + rank))`, pool default `min(eligible_count, max(50, 5 * top_k))` capped at 250, union by chunk ID, top-k output. Ties: fusion score descending, best branch rank ascending, chunk ID ascending.
- **FR-008**: Dense, lexical, and fused score fields MUST be documented as ranking signals, not probabilities. Results MUST retain branch ranks/scores needed to explain fusion.
- **FR-009**: Retrieval MUST use a read-only PostgreSQL `REPEATABLE READ` transaction and read only records belonging to the active `delivery_imports` row and its compatible `embedding_sets`; response provenance MUST describe that same snapshot.
- **FR-010**: Each result MUST preserve exact chunk text and include DOI, digest-bound source locator, section identity/path/type, chunk ID, and the minimum paper metadata defined in the canonical contract, without synthesizing scientific claims.
- **FR-011**: Responses MUST identify the active delivery digest, source contract/corpus version, and embedding provider/model/dimensions/prefix used.
- **FR-012**: Validation, provider, database, missing-corpus, mismatch, and internal failures MUST use stable sanitized typed codes. No silent fallback, provider switching, or suppression of requested behavior is allowed.
- **FR-013**: SQL MUST parameterize user values; errors/logs MUST exclude credentials, full connection strings, local absolute paths, vectors, and article text.
- **FR-014**: The fixed development smoke subset MUST remain exactly `gq-sp-001`, `gq-cmp-001`, `gq-conf-001`, `gq-gap-001`, and `gq-ins-001`. The remaining 16 Golden v0 questions MUST remain held out from tuning and must not be run as an informal benchmark.
- **FR-015**: Implementation and verification MUST run using native Windows PowerShell, existing Python/uv and PostgreSQL environment. No Docker/WSL. Planning itself performs no database mutation.
- **FR-016**: Existing accepted Phase A source, schema, pilot data, and evidence MUST remain unchanged except explicitly approved additive Phase B changes.

### Retrieval contract reference

The canonical proposed request, response, errors, validation, filter normalization, provenance, ownership, and examples are in [`docs/contracts/retrieval-v1.md`](../../docs/contracts/retrieval-v1.md). It remains a Person 2 reference proposal pending shared-owner contract adoption; the private core does not publish this shared facade. Limits: request ID 1–128 allowed ASCII characters; trimmed nonblank query up to 2,000 characters; `top_k` 1–50; filter lists up to 100; hybrid candidate pool 1–250 and >= `top_k`.

Phase B response excludes timing, token selection/budget, reranker fields, evidence lookup, HTTP status mapping, and answer-generation fields. Person 3 owns HTTP adaptation and orchestration.

### Measurable Outcomes

- **SC-001**: Exact dense result IDs and cosine distances/similarities match a known-vector oracle; repeated tied queries return identical ordering.
- **SC-002**: FTS query parsing, English lexeme behavior, ranks, no-lexeme result, and tied ordering match explicit real-PostgreSQL fixtures.
- **SC-003**: Every filter has positive, negative, boundary, omission, invalid, and combination coverage in dense, lexical, and hybrid modes.
- **SC-004**: Hybrid candidate union, RRF scores, pool bound, top-k truncation, and ties match an independent deterministic oracle, including explicit pool < top_k rejection.
- **SC-005**: Synchronized activation during embedder execution and during retrieval proves every result/provenance field comes from exactly one final repeatable-read snapshot; activation does not block on retrieval reads.
- **SC-006**: Fake embedder tests cover call/no-call by mode, no-corpus preflight, config match/mismatch, malformed/zero-norm vectors, and unavailable provider with no fallback.
- **SC-007**: Only the five smoke IDs run in the development subset; the other 16 Golden v0 questions are absent from tuning inputs.
- **SC-008**: Existing full regression/static checks and real PostgreSQL retrieval checks pass; no main database operation or paid call occurs. Independent read-only user verification and explicit human acceptance are required before completion.
- **SC-009**: Record non-gating median/p95 database retrieval observations by mode on the 728-chunk pilot with warm/cold conditions and environment metadata; no arbitrary latency SLO or retrieval-quality claim is inferred.

### Acceptance record

The owner independently verified the internal retrieval core on 2026-11-19 and explicitly accepted P3-05 through P3-08. Reported evidence: read-only preflight passed for `sciscope_test_005`; all 47 retrieval tests passed; Feature 005 read-only verification passed; Feature 006 verification passed 10/10 with zero mismatches; active pilot counts remained 17/319/728/728. This closes the private Person 2 retrieval core only.

Known limits are retained: synchronized committed activation was not simulated (the read-only `REPEATABLE READ` and snapshot provenance checks passed); PostgreSQL branch tests did not have a separately observed pre-implementation RED run; the five-question smoke was deferred behind the shared facade gate; and non-gating warm/cold latency observations were not recorded. The 16 held-out Golden v0 questions remain untouched. These limits do not reopen the owner's accepted internal scope; they remain relevant to future integration/evaluation work. The shared `retrieval.v1` contract/facade, P1-09/P1-11/P1-14, and GIN migration are not approved by this acceptance.

## Assumptions

- Phase A closure and pilot data in `sciscope_test_005` remain accepted and authoritative.
- Current pilot embeddings are preserved and query embeddings must be compatible with the fixed embedding metadata.
- Person 2 has approved technical direction for ADR-009 through ADR-012 baseline, transaction/security posture; this does not mark ADRs as team-approved or approve P1-09 shared metadata/UI semantics, retrieval.v1 adoption, or schema migration.
- Person 1/3/4 and team review remain obligations before claiming shared contract adoption or completing dependent integrations. They do not prevent isolated Person 2 implementation after this feature spec/plan is approved. Separate FTS migration approval remains required only for the index migration.
- Phase B does not include reranking, diversity/duplicate policy, context selection, evidence lookup, held-out evaluation, latency benchmarking, FastAPI endpoint, or frontend controls.
