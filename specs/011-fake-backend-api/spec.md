# Feature Specification: Fake-Only Backend Question API

**Feature Branch**: `011-fake-backend-api`

**Created**: 2026-11-21

**Status**: Draft — pending human and cross-owner review
**Input**: Person 3 Phase 1E request for the first fake-only backend API
feature.

## Status and authority

This is a draft feature specification. It neither approves a shared HTTP or
retrieval contract nor authorizes dependency changes, tests, or implementation.
The feature must still pass the repository sequence of research, specification,
plan, tasks, explicit approval, RED tests, and implementation
([`AGENTS.md`](../../AGENTS.md); [constitution, Delivery Gates](../../.specify/memory/constitution.md);
[`docs/DEVELOPMENT_WORKFLOW.md`, Stages A–F](../../docs/DEVELOPMENT_WORKFLOW.md)).

The source research for this feature is
[`research.md`](research.md). Its FastAPI/Pydantic version, compatibility, and
license observations are **NOT VERIFIED** because no external verification was
performed. The draft interface below is therefore a **PROPOSED Person 3 API
contract**, not an approved replacement for the proposed `retrieval.v1` or the
Person 2-owned `retrieval.v2` boundary.

## Clarifications

### Session 2026-11-21

- A valid supplied `request_id` is preserved; an omitted ID receives a newly
  generated, valid opaque ID. An invalid supplied ID returns `422`, is never
  echoed as trusted metadata, and its sanitized error envelope instead carries
  a newly generated, valid opaque ID.
- Framework-generated request-validation errors are transformed into this
  draft API's versioned, sanitized `422` envelope. They do not expose raw
  input, exception details, stack traces, or framework-internal structures.
- An `answered` output fails closed with `response_contract_failure` when its
  answer or any required evidence, citation, source-metadata, or corpus-
  provenance value is empty, missing, malformed, or inconsistent. Citation
  membership remains an identity check only; it does not establish scientific
  support for a claim.
- The feature permits an in-process ASGI HTTP test client, but permits no
  outgoing external network call, database connection, real provider call, or
  listening server during offline tests.
- An `answered` response contains at least one claim, and every such claim has
  at least one valid citation to response-local evidence.
- A `no_results` response still preserves valid synthetic corpus provenance,
  even though its evidence list is empty.

## User Scenarios & Testing

### User Story 1 — Ask a validated research question (Priority: P1)

As a frontend client, I can submit one `research_question` request and receive
a deterministic, clearly synthetic answer package whose claims link only to
the evidence returned for that request.

**Why this priority**: It establishes the smallest independently testable
backend-to-frontend contract without a database, a provider credential, or a
live scientific-answer claim.

**Independent Test**: An offline client sends a valid request to an in-process
application configured with known fake retrieval and fake answer dependencies.
It verifies the complete versioned success schema, fixture response values,
mock/test metadata, corpus identity, and claim-to-evidence membership.

**Acceptance Scenarios**:

1. **Given** deterministic fake dependencies that return synthetic evidence,
   **when** a client sends a valid `research_question`, **then** it receives a
   `200` response with status `answered`, a nonempty request ID, `is_mock` and
   `is_test_data` set to `true`, the configured fake corpus provenance, and
   only fixture-derived content. Its nonempty claims list has at least one
   valid citation per claim.
2. **Given** fake answer output that cites returned chunk IDs, **when** the
   service validates the output, **then** each cited `chunk_id` occurs exactly
   once in the response evidence collection and retains that evidence item's
   DOI, source locator, exact passage, and corpus provenance.
3. **Given** a valid request with an allowed caller-supplied request ID,
   **when** it is processed, **then** the identical value appears in the
   response and error envelope for that request.
4. **Given** an omitted request ID, **when** a valid request is processed,
   **then** the response carries a newly generated valid opaque request ID.

---

### User Story 2 — Distinguish empty retrieval from insufficient evidence (Priority: P1)

As a frontend client, I can distinguish an empty retrieval result from a
synthetic fixture policy that says returned evidence is insufficient, without
either outcome claiming that the scientific literature lacks evidence.

**Why this priority**: Person 2's handoff states that an empty retrieval result
and scientific answerability are separate decisions
([`docs/person2/RETRIEVAL_V2_PERSON3_HANDOFF.md`, “Empty and insufficient-evidence behavior”](../../docs/person2/RETRIEVAL_V2_PERSON3_HANDOFF.md)).

**Independent Test**: Offline fakes separately produce an empty retrieval set
and a nonempty set marked insufficient by a synthetic policy. The test checks
the two distinct success responses without examining any real corpus or model.

**Acceptance Scenarios**:

1. **Given** fake retrieval returns no evidence, **when** a valid request is
   processed, **then** the service returns `200` with status `no_results`, an
   empty evidence list, no claims, no answer, and valid synthetic corpus
   provenance.
2. **Given** fake retrieval returns evidence and the configured fake policy
   marks it insufficient, **when** a valid request is processed, **then** the
   service returns `200` with status `insufficient_evidence`, no claims, and no
   answer while preserving the returned evidence and corpus provenance.
3. **Given** either outcome, **when** it is displayed or logged by a consumer,
   **then** the response makes no assertion that evidence is absent from the
   literature or that a scientific conclusion is valid.

---

### User Story 3 — Receive safe, actionable contract failures (Priority: P2)

As a frontend client, I receive a versioned and sanitized error envelope for
invalid input or an injected fake dependency failure, and no hidden dependency
or provider detail is exposed.

**Why this priority**: The first contract must be safe to integrate and test
before live retrieval or AI-provider behavior is considered.

**Independent Test**: Offline requests with malformed input and fakes configured
to fail produce the specified HTTP class, error code, request ID, and no
exception text, secrets, prompt, or evidence passage in the error envelope.

**Acceptance Scenarios**:

1. **Given** a malformed, blank, too-long, unsupported-workflow, unknown-field,
   or invalid-request-ID request, **when** it is submitted, **then** the
   service returns the versioned, sanitized `422` validation error envelope.
   An invalid supplied request ID is not echoed; the envelope carries a newly
   generated valid opaque request ID instead.
2. **Given** fake retrieval or fake answer generation returns a configured
   unavailable failure, **when** a valid request is processed, **then** the
   service returns `503` with a stable, retryable error code and no internal
   detail.
3. **Given** fake retrieval or fake answer generation reaches its explicitly
   simulated time limit, **when** a valid request is processed, **then** the
   service returns `504` with a stable, retryable error code and no internal
   detail.
4. **Given** output fails local citation or response-shape validation, **when**
   the service handles it, **then** it returns `500` with a non-retryable
   sanitized contract-failure code and does not return the invalid output.
5. **Given** the framework detects request validation failure before application
   handling, **when** it produces its native validation representation, **then**
   the API transforms it into the same versioned, sanitized `422` error
   envelope without raw input or framework detail.
6. **Given** an `answered` fake output has an empty or invalid answer, claims
   without citations, absent or duplicate citation IDs, duplicate evidence
   chunk IDs, missing/invalid corpus provenance, or missing/invalid required
   source metadata, **when** it is validated, **then** the API fails closed
   with the `500` `response_contract_failure` envelope.
7. **Given** an unexpected internal exception occurs, **when** the public
   request boundary handles it, **then** the client receives HTTP `500` with
   code `internal_error`, a sanitized generic message, `retryable: false`, a
   valid request ID, and mock/test metadata, with no exception or source/input
   details. A test client configured with `raise_server_exceptions=True` still
   raises the original defect for developer diagnosis.

### Edge Cases

- A question made only of whitespace is invalid after trimming.
- A question at either permitted length boundary is accepted; one outside the
  boundary is rejected without calling either fake dependency.
- An omitted request ID is valid and results in an opaque server-issued request
  ID. A supplied request ID must match `^[A-Za-z0-9._:-]{1,128}$`; an invalid
  supplied value receives `422`, is never echoed, and is replaced only in the
  sanitized error envelope by a newly generated valid opaque ID.
- JSON values with unsupported fields, public metadata filters, additional
  workflows, or a mismatched API version are rejected. This feature does not
  silently ignore them.
- Duplicate evidence `chunk_id` values, missing corpus identity, a citation to
  an absent `chunk_id`, duplicate citation IDs within a claim, or a claim with
  no citation is a contract failure; the invalid provider output is not exposed.
- An empty retrieval result is a successful `no_results` response. It is not an
  `insufficient_evidence` result and is not a provider/retrieval failure.
- The fixture may deliberately produce `insufficient_evidence`; that status is
  a testable synthetic policy result, not a scientific-answerability judgment.
- An `answered` result requires a nonempty answer string; a claim requires one
  or more unique response-local citation IDs. `chunk_id`, every required source
  metadata field, and every corpus-provenance field must be nonempty strings.
  A missing, non-string, blank, duplicate, or non-member value is invalid.

## Proposed HTTP Contract

All fields and paths in this section are **DRAFT PROPOSALS** until Person 3,
Person 4, and the normal shared-contract approval gate accept them. No existing
approved HTTP contract defines these names: P1-11 (versioned API contracts) and
P1-14 (human approval of shared architecture/contracts) are unchecked
([`PROJECT_TODO.md`, Phase 1](../../PROJECT_TODO.md)).

### Endpoint

`POST /api/v1/questions`

The path version and `api_version: "v1"` response field make the public
contract version explicit. This endpoint is non-streaming. It supports only
the `research_question` workflow and has no public metadata-filter field.

### Request

```json
{
  "workflow": "research_question",
  "question": "Synthetic fixture question?",
  "request_id": "ui-42"
}
```

| Field | Required | Draft validation policy |
| --- | --- | --- |
| `workflow` | yes | Exact literal `research_question`. |
| `question` | yes | JSON string whose trimmed length is 1–2,000 Unicode characters. The original string is never included in an error envelope or unsafe log. |
| `request_id` | no | If supplied, it must match `^[A-Za-z0-9._:-]{1,128}$` and is preserved. If omitted, the service issues a newly generated valid opaque ID. An invalid supplied value receives `422`, is not echoed, and its error envelope has a newly generated valid opaque ID. |

The request is a closed object: unsupported fields, including filters, are a
validation error. The request body does not carry an API-version field because
the proposed path selects the version.

### Answered success response

```json
{
  "api_version": "v1",
  "request_id": "ui-42",
  "workflow": "research_question",
  "status": "answered",
  "answer": "Synthetic answer from the configured fake provider.",
  "claims": [
    {
      "claim_id": "claim-1",
      "text": "Synthetic claim from the configured fake provider.",
      "citation_chunk_ids": ["fixture-chunk-001"]
    }
  ],
  "evidence": [
    {
      "chunk_id": "fixture-chunk-001",
      "doi": "10.0000/fixture.001",
      "source_locator": "Synthetic source locator",
      "passage": "Synthetic exact fixture passage.",
      "paper_title": "Synthetic fixture paper"
    }
  ],
  "corpus": {
    "delivery_digest": "synthetic-fixture-digest",
    "source_contract_version": "synthetic-fixture-v1",
    "corpus_version": "synthetic-fixture-v1"
  },
  "metadata": {
    "is_mock": true,
    "is_test_data": true
  }
}
```

This example is synthetic and does not represent article prose, a corpus
record, or a scientific result. `chunk_id` is the evidence identity for this
first API contract. It is distinct from the response-level `corpus` identity.
The exact retrieval result provides the evidence's DOI, locator, and passage;
they must not be reconstructed from a generated claim. That direction follows
the Person 2 handoff ([`docs/person2/RETRIEVAL_V2_PERSON3_HANDOFF.md`, “Result evidence and citations”](../../docs/person2/RETRIEVAL_V2_PERSON3_HANDOFF.md)).

### Successful non-answer states

Both are `200` responses with the same top-level fields and mock/test metadata
as an answered response.

| `status` | `answer` | `claims` | `evidence` | Meaning |
| --- | --- | --- | --- | --- |
| `no_results` | `null` | `[]` | `[]` | Fake retrieval returned no eligible fixture evidence. |
| `insufficient_evidence` | `null` | `[]` | Preserved nonempty retrieval evidence | A configured fake policy declined to create an answer from returned fixture evidence. |

### Sanitized error response

```json
{
  "api_version": "v1",
  "request_id": "ui-42",
  "error": {
    "code": "invalid_request",
    "message": "The request does not meet this API version's validation rules.",
    "retryable": false
  },
  "metadata": {
    "is_mock": true,
    "is_test_data": true
  }
}
```

| Condition | Draft HTTP status | Draft error code | `retryable` |
| --- | --- | --- | --- |
| Request validation failure | 422 | `invalid_request` | `false` |
| Fake retrieval unavailable | 503 | `retrieval_unavailable` | `true` |
| Fake provider unavailable | 503 | `provider_unavailable` | `true` |
| Simulated dependency timeout | 504 | `dependency_timeout` | `true` |
| Internal output/citation contract failure | 500 | `response_contract_failure` | `false` |
| Unexpected internal exception | 500 | `internal_error` | `false` |

Every success response requires `api_version`, `request_id`, `workflow`,
`status`, `answer`, `claims`, `evidence`, `corpus`, and `metadata`. Every error
response requires `api_version`, `request_id`, `error`, and `metadata`. The
only permitted error-envelope request ID is a valid opaque ID generated by the
service or a valid caller-supplied ID; an invalid supplied ID is never echoed.
Framework-generated validation errors use the same `422` envelope and field
requirements as other request-validation errors. Error messages must not expose
raw input, exception representations, stack traces, framework-internal
representations, credentials, provider configuration, question text, evidence
passage text, or full retrieval output. The centralized unexpected-exception
boundary returns the same required error-envelope fields with code
`internal_error` and a sanitized generic message; it never returns success or
silently suppresses the defect. With `raise_server_exceptions=True`, the
in-process test client must still surface the unexpected exception to tests.

## Requirements

### Functional Requirements

- **FR-001**: The feature MUST expose exactly one non-streaming, versioned
  question operation supporting only `research_question`.
- **FR-002**: The operation MUST accept a closed request object containing
  `workflow`, `question`, and optionally `request_id`; it MUST reject public
  metadata filters and unknown fields for this feature.
- **FR-003**: The operation MUST apply the proposed strict question and
  request-ID validation rules before it calls retrieval or answer generation.
  Framework-generated validation errors MUST be transformed into the same
  versioned, sanitized `422` error envelope.
- **FR-004**: A request without `request_id` MUST receive a nonempty opaque
  server-issued ID; a valid caller-provided ID MUST be preserved in its outcome.
  An invalid supplied ID MUST receive `422`, MUST NOT be echoed as trusted
  metadata, and its error envelope MUST carry a newly generated valid opaque
  ID.
- **FR-005**: The operation MUST return the proposed versioned success shape
  for `answered`, `no_results`, and `insufficient_evidence` states. An
  `answered` state MUST contain at least one claim.
- **FR-006**: The feature MUST obtain retrieval and answer-generation behavior
  through independently injectable fake dependencies. Default feature tests
  MUST need neither credentials, an outgoing external network call, a database
  connection, PostgreSQL, a real provider, nor a live embedding service. An
  in-process ASGI HTTP test client is permitted; it MUST NOT start a listening
  server.
- **FR-007**: Configured fake dependencies MUST produce deterministic synthetic
  fixtures for equivalent test inputs and configurations. Their output MUST be
  explicitly marked with structured `is_mock: true` and `is_test_data: true`
  metadata.
- **FR-008**: Each evidence record MUST use a unique nonempty `chunk_id` as its
  identity and preserve nonempty-string DOI, source locator, exact passage,
  and paper title values returned by fake retrieval.
- **FR-009**: Each response MUST contain corpus/snapshot provenance separately
  from `chunk_id`, with nonempty-string delivery digest, source-contract
  version, and corpus version values supplied by the fake retrieval fixture,
  including when `no_results` has an empty evidence list.
- **FR-010**: Every citation in every returned claim MUST reference a unique
  `chunk_id` present in the same response's evidence collection. A claim MUST
  have at least one citation, an `answered` outcome MUST have a nonempty answer
  string, and the response MUST not contain duplicate evidence identities. An
  empty/invalid answer, missing/invalid required source metadata or corpus
  provenance, missing citations, non-member citation IDs, duplicate citation
  IDs within one claim, or duplicate evidence `chunk_id` values MUST fail closed
  with the `response_contract_failure` envelope. This membership validation
  MUST NOT be presented as proof that a claim is scientifically supported.
- **FR-011**: The feature MUST return `no_results` only when its retrieval
  dependency returns no evidence. It MUST return `insufficient_evidence` only
  when its configured fake policy selects that state from returned evidence.
  Neither status MUST assert that the literature lacks evidence.
- **FR-012**: The feature MUST return the proposed sanitized error envelope and
  HTTP mapping for validation, unavailable dependency, timeout, and output
  contract failures, including framework-generated request-validation errors.
  Unexpected internal exceptions MUST return HTTP `500` with code
  `internal_error`, a sanitized generic message, `retryable: false`, a valid
  request ID, and mock/test metadata; they MUST NOT return success or internal
  details.
- **FR-013**: The feature MUST not return invalid or unvalidated fake provider
  output to a client.
- **FR-014**: The feature MUST not depend on Person 2's private
  `_RetrievalCore` in the HTTP/application contract. It MAY later consume an
  approved public retrieval facade through an adapter after its contract and
  integration approval.
- **FR-015**: The feature MUST not make outgoing external network calls,
  database connections, live Gemini calls, query-embedding calls, PostgreSQL
  retrieval calls, or database writes. Offline tests MAY use an in-process ASGI
  HTTP test client and MUST NOT start a listening server.
- **FR-016**: The feature MUST not stream responses, expose authentication,
  rate-limiting, deployment, or production-operation behavior.
- **FR-017**: The feature MUST neither select nor enable `retrieval.v2`.
  `retrieval.v2` is Person 2-owned, opt-in, and requires Person 3 integration
  review ([`docs/contracts/retrieval-v2.md`](../../docs/contracts/retrieval-v2.md);
  [`docs/person2/RETRIEVAL_V2_PERSON3_HANDOFF.md`, “Selection and compatibility”](../../docs/person2/RETRIEVAL_V2_PERSON3_HANDOFF.md)).
- **FR-018**: The feature MUST make no claim about scientific answer quality,
  citation entailment, corpus completeness, or real-provider performance.

### Nonfunctional Requirements

- **NFR-001**: All first-feature acceptance checks MUST be runnable offline
  with deterministic fakes and synthetic fixture data.
- **NFR-002**: The public responses and errors MUST be serializable, have
  stable required-field presence for each declared state, and be validated
  before they cross the HTTP boundary. Success responses always carry
  `api_version`, `request_id`, `workflow`, `status`, `answer`, `claims`,
  `evidence`, `corpus`, and `metadata`; errors always carry `api_version`,
  `request_id`, `error`, and `metadata`.
- **NFR-003**: Error handling and ordinary observability MUST avoid credentials,
  secret-bearing configuration, real provider output, raw question text, and
  raw evidence passages unless a later reviewed privacy/logging contract
  explicitly permits such data. Unexpected defects MUST remain observable to
  developers and offline tests, while the public response contains no exception
  detail, traceback, input, or source data.
- **NFR-004**: The feature's scope MUST remain usable without a listening
  server, database connection, container runtime, or external service during
  offline testing. An in-process ASGI HTTP test client is allowed.

### Key Entities

- **Question request**: A closed client input for one `research_question`, with
  a validated question and optional correlation ID.
- **Question outcome**: One of `answered`, `no_results`, or
  `insufficient_evidence`; it is a successful application response state.
- **Evidence record**: A response-local retrieved passage identified by
  `chunk_id`, carrying citation/source details without substituting it for
  corpus identity.
- **Claim**: Synthetic fake-provider output whose citation IDs must resolve to
  response-local evidence records.
- **Corpus provenance**: Response-level identity describing the fixture corpus
  or future snapshot separately from individual evidence identities.
- **Error envelope**: A versioned, sanitized outcome for a failed request or
  dependency/contract operation.
- **Mock/test metadata**: Structured declaration that the response came from
  fake dependencies and synthetic test data.

## Scope Boundaries

### Included

- A draft contract for one non-streaming question endpoint and one workflow.
- Strict input, response, citation-membership, provenance, and error behavior.
- Independently injectable deterministic fake retrieval and fake answer
  generation behavior, assessed only through offline acceptance checks.

### Excluded

- Live Gemini or any other live AI provider; credentials; real query embeddings;
  real PostgreSQL retrieval; database mutation; direct `_RetrievalCore` use;
  `retrieval.v2` enablement; streaming; production deployment; authentication;
  rate limiting; protected evaluation data; and scientific answer evaluation.
- Outgoing external network calls, database connections, and a listening server
  during offline tests.
- Public metadata filters, additional workflows, real-corpus answer generation,
  and any change to Person 2 retrieval source, contracts, or schema.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Offline acceptance checks cover all three successful outcome
  states (`answered`, `no_results`, and `insufficient_evidence`) using only
  synthetic fakes and fixtures, with zero external provider, database, or
  network operations.
- **SC-002**: Offline acceptance checks cover every declared invalid-request
  category and every declared sanitized dependency/contract failure category.
- **SC-003**: In all answered fixture responses, 100% of claim citation IDs
  resolve to exactly one evidence record in the same response, and each cited
  record contains a `chunk_id`, DOI, locator, passage, and separate corpus
  provenance.
- **SC-004**: In all feature fixtures, 100% of success and error responses
  include a nonempty request ID and structured mock/test metadata indicating
  fake/test output.
- **SC-005**: The documented first-feature scope creates no requirement for a
  running database, an API credential, a provider call, or protected data.

## Backlog Mapping

This specification scopes future work only. It does **not** mark any task
complete.

| Backlog item | Relationship to this draft |
| --- | --- |
| P1-11 | Supplies the still-unapproved shared versioned API contract decision this draft proposes. |
| P1-14 | Requires human approval of the shared architecture and contract before implementation. |
| P4-01 | Future FastAPI application skeleton; only its first endpoint boundary is specified here. |
| P4-02 | Future request, success, and error API contracts; this draft proposes their first version. |
| P4-03 | Future approved Spec Kit artifacts and acceptance criteria; this is only the draft specification artifact. |
| P4-04–P4-08 | Future deterministic fake provider, fake behavior tests, marker fixture, integration, and offline tests. |
| P4-13–P4-15 | Future structured validation, citation validation, and insufficient-evidence behavior constrained by this draft. |
| P4-17 | Future input validation constrained by this draft. |
| P4-20 | Future provider/retrieval failure behavior constrained by this draft. |
| P4-09–P4-12, P4-16, P4-18–P4-19 | Remain outside this fake-only first feature because they concern real retrieval, Gemini, timeout/streaming, security operationalization, or real provider/token work. |
| P5-05 | Person 4's future fake-API frontend integration depends on an approved P4-02 contract. |

The underlying task IDs and dependencies remain unchecked in
[`PROJECT_TODO.md`, Phases 1, 4, and 5](../../PROJECT_TODO.md).

## Assumptions and Approval Gates

### Draft assumptions

- This feature is a development-only, fake-only contract slice. Its `is_mock`
  and `is_test_data` metadata is always `true`; it cannot be used to imply a
  real corpus or provider result.
- A future implementation may use FastAPI and Pydantic after a separately
  approved dependency plan. Neither package is a currently declared direct
  application dependency (`research.md`, “Dependency options”).
- The existing synchronous database/retrieval layer informs the later design,
  but this feature calls only fakes and creates no database lifecycle
  requirement (`research.md`, “Application lifecycle and sync route model”).

### Open shared-contract decisions

1. **Public retrieval facade (Person 2 owner/reviewer; Person 3 approval):**
   Person 2 has no exported public `RetrievalService`; the current core is
   private. Decide the public protocol, typed result/error surface, corpus
   identity fields, and version-selection ownership before real retrieval is
   connected. The fake protocol here must not become a de facto shared
   retrieval contract. ([`docs/person2/RETRIEVAL_V2_PERSON3_HANDOFF.md`,
   “Selection and compatibility”](../../docs/person2/RETRIEVAL_V2_PERSON3_HANDOFF.md))
2. **HTTP contract adoption (Persons 3 and 4, then P1-11/P1-14 human gate):**
   Approve, revise, or reject the proposed path, field names, validation limits,
   status names, HTTP status mapping, and error envelope before frontend work
   or implementation begins.
3. **Corpus identity compatibility (Person 2 owner/reviewer):** Confirm that
   future facade results can provide the separately preserved delivery digest,
   source-contract version, corpus version, DOI, locator, and exact passage
   needed by this API. The currently proposed `retrieval.v1` DTO is not itself
   an approval ([`docs/contracts/retrieval-v1.md`, status and contract sections](../../docs/contracts/retrieval-v1.md)).
4. **Dependency and framework decision (Person 3 plus human plan approval):**
   Verify official FastAPI/Pydantic Python 3.12 compatibility, licenses, and
   versions before adding direct dependencies or choosing an HTTP test client.
5. **Real integration and retrieval strategy (Person 2 and Person 3):** Keep
   real retrieval disabled. A later approved comparison must choose any
   retrieval version/mode and a compatible query embedder; no selection is
   implied by this fake-only feature.

## Consistency Notes

The proposed citation rule is intentionally narrower than scientific
faithfulness: it verifies response-local identity membership. Person 2's
handoff explicitly distinguishes this from relevance and answer correctness
([`docs/person2/RETRIEVAL_V2_PERSON3_HANDOFF.md`, “Result evidence and citations”](../../docs/person2/RETRIEVAL_V2_PERSON3_HANDOFF.md)).
Likewise, the current `retrieval.v1` document labels itself proposed and says
it does not approve P1-09, P1-11, or P1-14
([`docs/contracts/retrieval-v1.md`, “Status”](../../docs/contracts/retrieval-v1.md)).

No implementation, test, plan, task list, dependency change, shared-contract
edit, approval, or backlog completion is created by this specification.
