# Feature Specification: Shared Retrieval Service Integration

**Feature Branch**: `feature/p4-09-backend-retrieval-integration`
**Created**: 2026-11-22
**Status**: APPROVED 2026-11-22 by Person 3 (Backend & AI) for T012-A and beginning T012-B offline work only. Concrete v2 HTTP implementation, database access, mode activation, and final feature acceptance remain separately gated.
**Input**: P4-09 request to connect the accepted Feature 011 question backend to the accepted Feature 007 public retrieval facade.

## Authority and boundaries

Feature 011 and Feature 007 are accepted only within their recorded scopes. This draft covers the adapter and application integration between them. It does not amend either accepted feature, adopt either retrieval contract beyond this feature's approved scope, assert a retrieval-mode winner, enable a live answer provider, or complete other Phase 4 backlog items. See [`research.md`](research.md) for repository facts and evidence.

The owner approval gate in `docs/DEVELOPMENT_WORKFLOW.md` was recorded on 2026-11-22 for the planning scope and T012-B offline work. Decisions D012-01 through D012-05 remain traceable; their stated implementation, review, database, mode-selection, and acceptance gates still apply.

## Proposed versioned HTTP contract — DRAFT only

`POST /api/v1/questions` and every accepted v1 success/error JSON shape remain
unchanged for fake-only behavior. The proposed real-retrieval endpoint is
`POST /api/v2/questions`, returning `api_version: "v2"`. The request remains
compatible with v1: `workflow`, `question`, and optional `request_id`; retrieval
configuration remains server-owned and is never a caller input. This is a new
wire contract, not an additive v1 field change, and needs explicit approval
before implementation or consumer migration.

Proposed answered v2 response:

```json
{
  "api_version": "v2",
  "request_id": "ui-42",
  "workflow": "research_question",
  "status": "answered",
  "answer": "Answer text from the configured answer provider.",
  "claims": [{"claim_id": "claim-1", "text": "Claim text.", "citation_chunk_ids": ["chunk-1"]}],
  "evidence": [{"chunk_id": "chunk-1", "doi": "10.0000/example", "source_locator": "section:1", "passage": "Exact retrieved passage.", "paper_title": "Paper title"}],
  "corpus": {"delivery_digest": "sha256:...", "source_contract_version": "0.3.0", "corpus_version": "pilot17"},
  "metadata": {
    "retrieval": {"configured_origin": "real", "executed": true, "is_test_data": false},
    "answer_provider": {"configured_origin": "fake", "executed": true, "is_test_data": true}
  }
}
```

Proposed no-results v2 response keeps `answer: null`, empty `claims` and
`evidence`, and the returned corpus identity. For a configured fake provider,
its metadata is `{"configured_origin":"fake", "executed":false,
"is_test_data":true}`: configuration and fixture status are reported, but
provider execution is not claimed. A retrieval failure uses the existing closed error category and
message vocabulary with v2 metadata; for example:

```json
{
  "api_version": "v2",
  "request_id": "ui-42",
  "error": {"code": "retrieval_unavailable", "message": "The requested dependency is currently unavailable.", "retryable": true},
  "metadata": {
    "retrieval": {"configured_origin": "real", "executed": true, "is_test_data": false},
    "answer_provider": {"configured_origin": "fake", "executed": false, "is_test_data": true}
  }
}
```

The v2 models must be closed and strict. They validate the same request ID and
question limits as v1, response-local unique citation membership, nonempty
evidence/provenance fields, and no-results invariants. They do not infer
scientific support from citation membership. Consumers migrate by explicitly
calling v2 and validating its separately published response schema; v1 clients
continue receiving the exact accepted fake-only contract. Compatibility tests
must assert both the unchanged v1 JSON key sets and all v2 success/error states.

## User Scenarios & Testing

### User Story 1 — Receive retrieved source evidence (Priority: P1)

As a research workflow client, I can submit a validated research question and receive the exact retrieved source passages and their corpus provenance so that any downstream answer can use the correct evidence.

**Why this priority**: It connects the accepted retrieval boundary to the accepted question backend without coupling the HTTP layer to database internals.

**Independent Test**: An offline test injects a public retrieval-service stub, sends a question through the in-process question API, and verifies the request ID, version/mode configuration, evidence fields, corpus identity, and response-local citation checks.

**Acceptance Scenarios**:

1. **Given** a valid question and explicit approved retrieval settings, **when** the request is handled, **then** the adapter forwards the question and request ID and issues one public retrieval request with those settings.
2. **Given** a public retrieval response with results, **when** the adapter maps it, **then** it preserves each stable chunk ID, DOI, source locator, exact text, paper title, and all three corpus identity fields without synthesis or rewriting.
3. **Given** an empty retrieval response, **when** the question service handles it, **then** it returns the approved no-results behavior with empty evidence, no answer or claims, and the retrieval response's corpus identity; it does not claim that the literature contains no evidence.
4. **Given** a retrieval result, **when** a fake answer provider returns claims, **then** citation IDs can resolve only to evidence IDs in that same response; duplicate or nonexistent IDs fail closed.

### User Story 2 — Distinguish synthetic and real components (Priority: P1)

As a client, I can tell whether retrieved evidence and an answer came from synthetic or real components, and whether the data belongs to a test environment, so I do not mistake a fake answer for a verified result or real source text for a fixture.

**Why this priority**: Feature 011 requires both metadata flags to be true for every response, which cannot truthfully describe every real-retrieval scenario.

**Independent Test**: Contract tests cover synthetic retrieval plus fake provider, real retrieval plus fake provider, real retrieval plus real provider, and isolated test database versus live deployment metadata.

**Acceptance Scenarios**:

1. **Given** the existing fake-only dependencies, **when** the accepted question API handles a request, **then** its currently accepted response values and behavior remain unchanged unless a separately approved HTTP extension specifies otherwise.
2. **Given** real retrieval and a fake answer provider, **when** a response is created, **then** metadata identifies the retrieval component as real and the answer component as synthetic; aggregate markers do not hide either origin.
3. **Given** real retrieval and a configured real answer provider in a live environment, **when** a response is created, **then** no component is marked mock or test data solely because of the retrieval adapter.
4. **Given** an isolated test database, **when** metadata is produced, **then** the test-data marker identifies that environment even when the stored source records are not synthetic fixtures.

### User Story 3 — Receive safe, stable failures (Priority: P1)

As a client, I receive a stable sanitized error when retrieval cannot fulfill the request, with retry guidance that matches the failure and without database, provider, or local implementation details.

**Why this priority**: The public retrieval facade returns typed errors that do not have a one-to-one mapping in the accepted Feature 011 HTTP model.

**Independent Test**: Offline stubs raise each public retrieval error and controlled timeout; the API response is checked for the approved status/code/message/retryability/request ID and absence of sensitive details.

**Acceptance Scenarios**:

1. **Given** an invalid caller question, **when** existing API validation rejects it, **then** the accepted sanitized request-validation response remains unchanged.
2. **Given** an invalid adapter-generated request or unsupported server-selected retrieval version, **when** the adapter rejects it, **then** it is classified as a server-side configuration/contract failure rather than blamed on the caller.
3. **Given** each typed retrieval error, **when** it crosses the question API boundary, **then** it maps according to the approved error table without exposing exception text, SQL, credentials, connection strings, vectors, paths, or stack traces.
4. **Given** the retrieval service or provider reports a controlled timeout, **when** handled, **then** the API uses the approved timeout response; there is no hidden retry or mode fallback.

### User Story 4 — Compose dependencies without hidden resources (Priority: P2)

As an application owner, I can compose a real-retrieval application explicitly while keeping imports and fake-only tests free of database connections and provider initialization.

**Why this priority**: The current application factory is intentionally inert, and no engine ownership or disposal behavior is currently assigned to it.

**Independent Test**: Import and factory tests use sentinels to prove there is no connection/provider initialization at import or app construction; lifecycle tests verify only the declared owner disposes resources.

**Acceptance Scenarios**:

1. **Given** fake-only dependencies, **when** the app is imported and created, **then** no database connection, embedding client, live provider, listener, or external operation starts.
2. **Given** an explicitly composed real retrieval dependency, **when** a request is processed, **then** only the injected public service and approved settings are used.
3. **Given** an owner-controlled application shutdown, **when** the owning composition root is closed, **then** its engine is disposed after checked-out connections are returned; borrowed resources are not disposed by a non-owner.
4. **Given** any configured retrieval mode or version is unavailable, **when** the request is processed, **then** it fails explicitly and never silently switches mode or version.

## Edge Cases

- The retrieval response has zero results but valid corpus identity; the question service must preserve the accepted no-results distinction.
- An adapter-generated request fails validation because server configuration is invalid; it must not become a caller-input `422` by accident.
- The retrieval response contains duplicate chunk IDs, a missing corpus identity, empty source metadata, or a response request ID that differs from the request; fail closed without returning partial evidence.
- A claim has a duplicate citation ID, cites a result not present in its response, or has no citation; fail closed. Membership does not prove scientific support.
- An embedding configuration mismatch or unavailable embedder occurs in dense/hybrid mode; do not fall back to lexical retrieval.
- A transient database or embedder failure is distinguished from non-retryable server configuration and internal errors using the typed error's retryability value where applicable.
- The isolated test database has no active corpus or its identity, role, revision, extension, or corpus counts do not match the approved gate; stop before retrieval and perform no migration or write.
- A test process exits with an engine connection checked out; do not dispose the engine until the connection is returned.
- Unknown HTTP error codes/metadata fields are rejected by a frontend client; the compatibility decision must be resolved with Person 4 before response schema changes.

## Requirements

### Functional Requirements

- **FR-001**: The question backend MUST receive retrieval through an injected adapter that implements the existing question-service retrieval protocol and delegates only to the public `RetrievalService` boundary.
- **FR-002**: The adapter MUST forward the validated question and request ID unchanged.
- **FR-003**: The adapter MUST construct a public retrieval request using an explicitly approved retrieval contract version, mode, top-k, and any approved filter/ranking settings. It MUST NOT expose retrieval mode as a public request field unless a separate reviewed contract explicitly requires that behavior.
- **FR-004**: The application MUST NOT select an implicit retrieval version or mode before the approved comparative evidence and Person 2 review support the choice. The application settings MUST fail closed when an explicit configuration is missing or invalid.
- **FR-005**: Dense and hybrid configurations MUST identify a compatible query embedder/provider/model/configuration explicitly. The system MUST NOT create or call an embedding provider implicitly or silently fall back to another mode.
- **FR-006**: The adapter MUST preserve the exact returned chunk ID, DOI, source locator, passage text, paper title, delivery digest, source-contract version, and corpus version. It MUST NOT synthesize identifiers, citations, article metadata, passages, or scientific claims.
- **FR-007**: The question service MUST retain the existing empty-retrieval behavior: no answer, no claims, empty evidence, and valid response-level corpus identity. Empty retrieval MUST NOT be represented as a scientific insufficiency finding.
- **FR-008**: Answer claims MUST cite only response-local evidence IDs. Duplicate, empty, or nonexistent citation IDs MUST fail closed. Citation membership MUST NOT be described as scientific support or answer correctness.
- **FR-009**: The proposed v2 response MUST distinguish retrieval and answer component configured origins, execution state, and test-data status truthfully. v1 MUST retain its literal-true fake-only metadata and exact shape. The v2 endpoint/schema remains subject to explicit approval.
- **FR-009a**: A component marked `executed: false` MUST NOT be presented as having produced output. Empty retrieval and retrieval failures report the configured answer-provider origin but `executed: false`; answer-provider failures report retrieval execution truthfully and provider `executed: true`.
- **FR-010**: Existing Feature 011 fake-only behavior and its accepted responses MUST remain unchanged unless an explicit, reviewed extension approves the change. The accepted Feature 011 specification and implementation MUST NOT be retroactively re-scoped.
- **FR-011**: Every public retrieval error code MUST have a documented HTTP status, stable public error code, sanitized message, exact typed retryability propagation, route-scoped request-ID behavior, and privacy-safe logging rule before implementation.
- **FR-012**: Caller-controlled invalid question input MUST remain distinct from invalid adapter-owned version/mode/configuration. Server-owned invalid configuration MUST NOT be reported as caller error.
- **FR-013**: Retrieval or provider timeouts MUST use the approved timeout behavior. The adapter MUST NOT add implicit retries, silently downgrade the retrieval mode, or suppress a retrieval error.
- **FR-014**: Public HTTP responses and logs MUST NOT expose credentials, database URLs, SQL, embedding vectors, private exception representations, local absolute paths, source passage content in error messages, or private stack traces to clients.
- **FR-015**: API/question-service DTOs MUST remain independent of SQL, ORM, private retrieval-core, database-driver, and connection types.
- **FR-016**: Importing the API or constructing a fake-only app MUST NOT connect to PostgreSQL, initialize an embedding provider, invoke a live answer provider, start a listener, or perform network I/O.
- **FR-017**: The application composition root MUST explicitly own each engine it creates and dispose of it safely at its declared lifecycle boundary. A component MUST NOT dispose a borrowed engine.
- **FR-018**: The retrieval evaluation MUST use only the five approved development questions and the approved retrieval evaluation protocol. The other 16 held-out Golden v0 questions MUST NOT be used for mode tuning or informal selection.
- **FR-019**: The mode evaluation MUST compare distinct supported retrieval behaviors under the same questions, corpus, configuration controls, cutoffs, repeated-run policy, and environment; it MUST report quality, latency, deterministic stability, and exact provenance separately.
- **FR-020**: The initial `retrieval.v1` lexical PostgreSQL smoke test, if authorized, MUST be documented as an integration smoke choice only and MUST NOT become the final application mode by implication.
- **FR-021**: PostgreSQL integration MUST use a separately authorized, exact-identity preflight against `sciscope_test_005`, PostgreSQL 17, the approved role, compatible pgvector, Alembic revision `f005_pgvector_foundation`, and the approved active pilot snapshot. It MUST perform only `READ ONLY`, `REPEATABLE READ` retrieval and source checks.
- **FR-022**: PostgreSQL verification MUST compare preflight and postflight identity/counts, preserve exact persisted provenance, and perform no migration, ingestion, snapshot replacement, paid provider call, or write.
- **FR-023**: Every implementation increment MUST preserve the actual RED failure and GREEN correction chronology, exact automated commands/results, independent owner-run commands/results, affected-owner decisions, and commit hashes in `docs/person3/P4_09_TEST_LOG.md`.
- **FR-024**: Feature completion MUST require passing approved automated checks, Person 2 and Person 4 reviews, applicable Person 1 source/provenance review, independent Person 3 manual verification, and explicit human `ACCEPTED`; automation alone MUST NOT complete the feature.

### Non-Functional Requirements

- **NFR-001**: Feature tests and CI MUST remain deterministic and offline; no paid provider, production database, or held-out evaluation input may be accessed.
- **NFR-002**: Any mode comparison MUST report observed latency without claiming a production latency guarantee; ranking scores MUST NOT be presented as confidence probabilities.
- **NFR-003**: All error and verification evidence MUST be reproducible without recording credentials or sensitive local configuration.
- **NFR-004**: New public behavior MUST remain small enough for focused review and must not alter Person 2 retrieval algorithms or the frozen corpus.

## Success Criteria

### Measurable Outcomes

- **SC-001**: In approved offline adapter tests, 100% of returned evidence records preserve the exact required source fields and corpus identity from the public response.
- **SC-002**: In approved citation tests, 100% of returned claim citation IDs resolve uniquely to same-response evidence, and every duplicate/nonmember case fails closed.
- **SC-003**: Tests cover all seven public retrieval error codes plus controlled timeout and demonstrate the approved sanitized status/code/retryability behavior for each.
- **SC-004**: Fake-only app import/factory tests record zero database connections, live provider initialization, external network calls, or listener startup.
- **SC-005**: The comparative report includes all five approved smoke question IDs, all distinct approved mode/version behaviors, per-question and aggregate results, and 100% exact provenance checks for returned hits; no held-out question IDs appear.
- **SC-006**: The guarded database test records pre/post identity and expected counts, verifies every retrieval transaction is read-only repeatable-read, and performs zero writes or schema changes.
- **SC-007**: Each implementation increment has separate Codex automated and owner-run manual records, required owner-review decisions, and an explicit decision; feature completion remains pending until the owner records `ACCEPTED`.

## Dependencies and assumptions

- Feature 011 and Feature 007 are accepted and merged at the stated baseline.
- Person 2 owns the public retrieval contract, retrieval error semantics, and comparison review. Person 4 owns frontend integration and reviews concrete visible metadata/error contract changes. Person 1 reviews only if source/provenance meaning changes. Person 2 and Person 4 have owner-reportedly delegated technical choices to Person 3; this is not approval of specific implementation or test results and does not replace required affected-owner review or acceptance.
- The local repository contains Person 2's existing five-question development comparison. It supports v1 dense as the leading candidate but does not establish a reliable general winner. No benchmark was run for this task.
- A supported HTTP server command, deployment setup, public API base URL, or production composition path is not established and is out of scope.

## Delegation and adopted design decisions

**Owner-reported delegation (2026-11-22):** Person 2 and Person 4 told the Person 3 owner that Person 3 may make technical choices within this feature, provided the solution is correct and retrieval choice uses the best available measured results. This is delegation, not approval of a specific implementation or test result. Person 3 is responsible for validation and approval. Concrete affected-owner review, independent verification, and explicit acceptance remain required by the workflow.

| ID | Adopted design | Remaining gate | State |
| --- | --- | --- | --- |
| D012-01 | `retrieval.v1` + `dense` is the leading measured candidate: it tied v1 hybrid on measured Recall@10 and MRR@10 with lower median latency. v1 lexical is permitted only for a separately authorized PostgreSQL wiring smoke test. No fallback. | Final application activation requires approved comparative evidence, compatible explicitly configured query embedder, and explicit Person 3 acceptance. Current five-question evidence does not establish a reliable general winner. | Candidate adopted; activation PENDING |
| D012-02 | Component-origin metadata distinguishes real/synthetic retrieval and real/fake answer provider, with test-data status separate. Preserve exact Feature 011 fake-only behavior. | Verify DTO and frontend compatibility. If additive fields break strict clients, prepare a separately versioned contract for approval. | Design adopted; compatibility verification PENDING |
| D012-03 | Use the draft sanitized mapping where compatible; preserve typed retryability; server-owned invalid configuration is server failure, not caller 422; expose no private details. | Verify exact HTTP status/code compatibility before implementation. | Design adopted; contract verification PENDING |
| D012-04 | Explicit composition-root ownership: creator owns Engine disposal; adapter does not dispose borrowed Engine; no implicit DB/provider initialization. | Validate actual composition/lifespan boundary in approved implementation. | Design adopted; implementation validation PENDING |
| D012-05 | Preserve exact source identifiers, DOI, locator, passage text, title, and corpus identity; do not reinterpret or synthesize. | Person 1 review only if source meaning or upstream contract changes. | Design adopted; conditional review |

These decisions support the approved planning scope and T012-B authorization. They do not approve concrete v2 implementation, select an active application mode, authorize database/provider access, or record feature acceptance.
