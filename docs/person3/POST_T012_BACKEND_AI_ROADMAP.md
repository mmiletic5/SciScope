# Post-Feature-012 Backend & AI Roadmap

## 1. Purpose and starting baseline

This is a planning and handoff document for Person 3's remaining Backend & AI
work after the accepted T001–T005 increments of Feature 012. It is not an
approval to implement a later task, call a provider, connect to PostgreSQL, or
activate a retrieval configuration.

- **Starting branch:** `feature/p4-09-backend-retrieval-integration`
- **Starting commit:** `db8ff76820d26c1329964736fc9da5fe4f5ed8af`
  (`docs: update post-T005 backend and frontend handoffs`)
- **Feature 012 state:** T001–T005 are accepted; T006–T008 remain pending.
  P4-09 remains in progress and its master backlog checkbox remains unchecked.
- **Evidence boundary:** The accepted v1 API is fake-only. The accepted v2 API
  is an explicitly injected offline boundary. Neither constitutes production
  retrieval, live-provider, or deployment verification.

Authoritative task states remain in
[`PROJECT_TODO.md`](../../PROJECT_TODO.md) and
[`Feature 012 tasks`](../../specs/012-shared-retrieval-integration/tasks.md).
The chronological Feature 012 evidence is in
[`P4_09_TEST_LOG.md`](P4_09_TEST_LOG.md).

## 2. Verified foundation available for reuse

| Area | Accepted implementation | Limits that still apply |
| --- | --- | --- |
| Fake question API | Feature 011 provides injected fake retrieval/provider contracts and exact v1 behavior. | It does not prove real retrieval, scientific support, deployment, or live-provider behavior. |
| Public retrieval boundary | Feature 007 exports `RetrievalService`, request/response DTOs, modes, filters, ranking, corpus identity, and typed sanitized errors. | Retrieval core, database schema, ranking algorithms, and corpus ownership remain Person 2 responsibilities. |
| Question adapter | Feature 012 T003 adds `PublicRetrievalAdapter` and immutable `RetrievalAdapterSettings`; it maps public responses to internal evidence/provenance and fails closed. | It has not yet been verified in the complete v2 question flow with the public facade and fake provider together. |
| HTTP boundary | Feature 012 T004 adds separately versioned `/api/v2/questions`, typed error mapping, route-scoped IDs, local citation validation, and component metadata. | V2 is only registered with explicit valid metadata and has not been proven against PostgreSQL or a live provider. |
| Composition/lifecycle | Feature 012 T005 adds a public retrieval factory and `create_application`, with explicit dependencies and owned/borrowed Engine rules. | The lease covers handler dispatch through handler completion only; it does not cover streaming iteration, post-response background tasks, ASGI draining, real Engine behavior, or deployment shutdown. |

Primary reusable modules are:

- [`src/sciscope/question_service/contracts.py`](../../src/sciscope/question_service/contracts.py)
- [`src/sciscope/question_service/service.py`](../../src/sciscope/question_service/service.py)
- [`src/sciscope/question_service/validation.py`](../../src/sciscope/question_service/validation.py)
- [`src/sciscope/question_service/retrieval_adapter.py`](../../src/sciscope/question_service/retrieval_adapter.py)
- [`src/sciscope/retrieval/__init__.py`](../../src/sciscope/retrieval/__init__.py)
- [`src/sciscope/retrieval/factory.py`](../../src/sciscope/retrieval/factory.py)
- [`src/sciscope/api/app.py`](../../src/sciscope/api/app.py)
- [`src/sciscope/api/composition.py`](../../src/sciscope/api/composition.py)
- [`src/sciscope/api/http_models_v2.py`](../../src/sciscope/api/http_models_v2.py)
- [`src/sciscope/api/routes_v2.py`](../../src/sciscope/api/routes_v2.py)

## 3. Feature 012 completion dependencies

### T006 / 012-F — cross-story offline integration

T006 is the next planned increment. It needs contract review followed by
behavior-first offline coverage for v2 success using injected fakes, no-results
without a provider call, insufficient evidence, response-local citations,
explicit version/mode forwarding, truthful component metadata, independent
`is_test_data`, no mode fallback, and unchanged v1 behavior. The test-file
scope must be chosen after inspecting the accepted implementation; this roadmap
does not reserve a filename or count.

Required gates are: genuine RED, independent Person 3 RED verification,
separately authorized minimal GREEN work, focused/backend/public-retrieval and
static checks, concrete Person 2 public-retrieval-boundary review, concrete
Person 4 v2/frontend-compatibility review, independent Person 3 GREEN,
explicit acceptance, and a separately authorized focused commit.

### T007 / 012-G — guarded PostgreSQL verification

T007 requires separate explicit database authorization before any database
operation. The approved development IDs are `gq-sp-001`, `gq-cmp-001`,
`gq-conf-001`, `gq-gap-001`, and `gq-ins-001`. A later run must verify the
exact database and role identity, server and pgvector versions, Alembic
revision, active snapshot/corpus identity, expected counts, read-only
repeatable-read transactions, exact returned provenance, relevant deterministic
behavior, and equal pre/post database state. It must not migrate, ingest, write,
tune on held-out questions, call a paid provider, or activate a mode
implicitly.

The five-question comparison is development evidence, not a reliable global
winner. Person 2 must review the evidence before an explicit Person 3
mode-selection decision. A leading candidate is not a production default.

### T008 / 012-H — evidence and final feature gate

T008 needs final approved regression/static verification, preserved RED/GREEN
chronology, separated Codex and owner evidence, T006/T007 outcomes, Person 2
and Person 4 decisions, and Person 1 review only if source/provenance meaning
changes. Person 3 must explicitly accept or reject the feature; task/backlog,
CI/PR, and evidence reconciliation follow that decision. Feature 012 cannot be
automatically accepted.

## 4. Remaining Phase 4 roadmap

Backlog checkboxes in `PROJECT_TODO.md` remain unchecked. “Foundation” below
means accepted code or evidence is reusable; it does not mean the backlog item
is accepted.

| Task | Current foundation | Remaining acceptance gap and dependencies |
| --- | --- | --- |
| P4-10 — explicitly configured Gemini provider | Fake `AnswerProvider`, typed question outcomes, explicit composition and v2 metadata exist. | Needs its own approved specification/plan, explicit non-secret configuration, an injected Gemini implementation, fake-only tests, a separate live-provider authorization for any real call, Person 4 contract review if user-visible behavior changes, and human acceptance. Depends on P4-04 and P4-09; P4-09 itself still requires T006–T008. |
| P4-11 — provider abstraction suitable for future OpenAI | `AnswerProvider` protocol and fake provider establish a narrow current boundary. | Needs a provider-neutral approved contract covering capabilities, structured output, errors, timeouts, retries, token usage, and provider selection. It must not imply an OpenAI client or live call. Depends on P4-04. |
| P4-12 — query understanding behavior | Explicit server-owned retrieval settings and v2 request validation exist. | Needs a new specification that decides scope, inputs/outputs, scientific and privacy limits, model/provider policy, and interaction with server-owned retrieval configuration. Depends on completed P4-09 and P4-10. |
| P4-13 — structured AI response validation | Existing response-local citation membership and question output validators are available. | Needs a provider response schema, strict parser/validator, failure semantics, and behavior tests for malformed output. It must distinguish schema validity from scientific correctness. Depends on P4-02 and P4-10. |
| P4-14 — citation identifier and source validation | Stable evidence IDs, DOI/locator fields, response-local citation membership, and exact adapter mapping exist. | Needs lookup/identifier validation against the Person 2-owned stable-source capability and structured-provider output. It must preserve source values and define malformed/missing citation handling. Depends on P3-12 and P4-13. |
| P4-15 — insufficient-evidence response behavior | Fake and v2 flows already represent `insufficient_evidence`; T006 still needs complete composition coverage. | Needs a formal threshold/policy tied to evaluated retrieval and validated provider output, with no fabricated claims. Depends on P3-13, P4-13, and P4-14. |
| P4-16 — timeout and retry policies | Controlled dependency timeout maps to a sanitized v2 response; typed retrieval retryability is preserved. | Needs explicit per-dependency budgets, cancellation/retry rules, idempotency policy, observability, and no-fallback guarantees. Retries must be bounded and separately tested. Depends on P4-10. |
| P4-17 — request input validation | v1/v2 have closed request models, request-ID validation, and 422 envelopes. | Needs a formal audit/specification of all intended input limits and normalization/privacy policy. Do not broaden accepted v1/v2 schemas without contract review. Depends on P4-02. |
| P4-18 — API rate limiting | FastAPI boundaries exist. | Needs product/security requirements, identity strategy, store/algorithm, proxy/deployment assumptions, error/retry headers, tests, and Person 4 review of UI behavior. Depends on P4-01. |
| P4-19 — token usage recording | No live-provider metering has been accepted; component metadata is not token accounting. | Needs a provider-neutral accounting schema, unit/price/version policy, privacy/redaction rules, failure semantics, storage ownership, and tests. Depends on P4-10 and P4-13. |
| P4-20 — explicit provider and retrieval failure handling | Typed retrieval mapping, controlled failures, and offline composition exist. | Needs a unified approved error taxonomy across real provider, retrieval, timeout/retry, and user-facing v2 behavior; no internal leakage and no silent alternate dependency. Depends on completed P4-09, P4-10, and P4-16. |

## 5. P4-08 and P4-21 acceptance dependencies

| Task | Current position | Required next evidence |
| --- | --- | --- |
| P4-08 — backend integration tests | Feature 011 and Feature 012 have separate accepted offline suites, but P4-08 remains unchecked in the master backlog. | Reconcile its intended scope against the accepted Feature 011 evidence and later P4-09 integration. If work remains, create a small approved feature/task scope and behavior tests. Do not check it merely because related tests exist. |
| P4-21 — approved feature acceptance criteria, RED/GREEN tests, recorded verification | Feature 011 has accepted RED/GREEN and human evidence within its fake-only scope; Feature 012 has only T001–T005 accepted. | Requires an explicit traceability review over P4-03 through P4-07 and any remaining Phase 4 feature scope, preserved RED/GREEN/human evidence, and a human acceptance decision. It cannot be inferred from historical tests or commits. |

## 6. Relevant Phase 8 evaluation dependencies

| Evaluation task | Person 3 dependency | Gate |
| --- | --- | --- |
| P8-05 — citation identifier and DOI validity | Depends on P4-14 and Person 2's P8-01 dataset/benchmark foundation. | Needs approved identifiers, corpus provenance, and evaluated rules; no invented DOI correctness. |
| P8-06 — citation support against source passages | Depends on P2-23 and P8-05. | Requires source-passage comparison methodology and a distinction between identifier validity and claim support. |
| P8-07 — insufficient-evidence behavior tests | Depends on P4-15 and P8-01. | Requires an approved evidence policy and benchmark context; empty retrieval is not automatically scientific insufficiency. |
| P8-09 — token usage evaluation | Depends on P4-19. | Cannot begin until accounting semantics and live-provider boundary are approved. |
| P8-11 — provider, database, and API error scenarios | Depends on P4-16 and P4-20. | Requires controlled, safe scenario design and separately authorized database/provider work where applicable. |
| P8-01 through P8-04, P8-10, P8-12, P8-13 | Person 2 or TEAM owned, but they constrain Person 3's later behavior and evaluation. | Coordinate on datasets, retrieval benchmarks, latency, security, and regression definitions; do not run benchmarks under this roadmap. |

## 7. Suggested work packages and order

1. **Finish Feature 012:** T006 offline integration, then separately authorized
   T007 guarded database verification, then T008 evidence/reviews/decision.
2. **Reconcile Phase 4 acceptance debt:** review P4-08/P4-21 against accepted
   Feature 011 and completed Feature 012 increments; create a new approved
   scope only for work that remains.
3. **Provider boundary design:** specify P4-11 before P4-10 implementation so
   provider selection, response schema, timeouts, retryability, token
   accounting, and secret handling have one agreed boundary.
4. **Explicit live-provider increment:** specify P4-10, use fakes for all
   RED/GREEN work, and obtain separate authorization before any credential use
   or live request.
5. **Output integrity:** specify and implement P4-13, P4-14, then P4-15 with
   Person 2 source/retrieval input and Person 4 visible-contract review.
6. **Operational controls:** specify P4-16, P4-17, P4-18, P4-19, and P4-20 in
   dependency order; retain offline tests and isolated contract reviews.
7. **Evaluation:** begin the Person 3 Phase 8 work only after the prerequisite
   benchmark, data, provider, and validation tasks have their own approvals.

Each work package must use the Spec Kit sequence: solution research, approved
specification/plan/tasks, behavior RED, separately authorized minimal GREEN,
automated/static checks, independent owner verification, affected-owner review,
explicit acceptance, evidence reconciliation, and an authorized focused commit.

## 8. Cross-owner review map

- **Person 2:** review public retrieval boundary changes, version/mode/filter/
  ranking behavior, corpus/source provenance, database authorization and
  read-only verification, citation lookup dependencies, and retrieval evidence
  used for mode selection.
- **Person 4:** review every new or changed v2 request/response/error/metadata
  shape, client-visible rate-limit behavior, and frontend handling assumptions.
  Prior Feature 012 reviews do not automatically approve later changes.
- **Person 1:** review only when data provenance/source meaning, datasets, or
  upstream contracts change.
- **Person 3:** owns Backend & AI implementation/evidence but does not self-
  authorize shared contract changes, database operations, or live provider use.

## 9. Offline-first, provider, and security requirements

Default development and CI must use injected fakes and in-memory/sentinel
resources. Offline tests must not load `.env`, read credentials, create a real
Engine, connect to PostgreSQL, initialize a live embedder/provider, start a
network listener, or consume AI tokens. A live-provider task requires a separate
explicit authorization after its approved specification and plan.

Before a live provider can be considered, its specification must define:

- explicit provider selection and dependency injection; no implicit fallback;
- secret acquisition outside source, logs, evidence, tests, and error bodies;
- request/response redaction, data-retention, and scientific-provenance limits;
- bounded rate limiting, retry policy, timeout/cancellation policy, and
  idempotency behavior;
- safe typed error mapping without credentials, prompts, vectors, stack traces,
  DSNs, or provider-private details;
- token/accounting semantics, provider/model/version attribution, storage owner,
  aggregation, and privacy policy; and
- fake-only deterministic tests, plus a separately authorized minimal live
  verification plan with spend/rate limits and human review.

## 10. Risks and unresolved decisions

1. Feature 012 has no selected or activated application retrieval mode; a
   five-question development comparison does not justify one.
2. T006 must verify the object graph and metadata behavior together before
   database work; otherwise offline pieces may remain incompatible.
3. T007 needs separate database authorization and authoritative identity/count
   preflight; existing guarded historical evidence does not authorize a new run.
4. The T005 HTTP lease has documented dispatch-only coverage. Streaming,
   background work, cancellation, ASGI draining, and production shutdown need
   their own scoped design if they become requirements.
5. No approved provider-neutral structured-output, retry, accounting, or
   rate-limit contract exists yet.
6. Citation membership is not scientific entailment or source-support proof.
7. Master backlog checkboxes for older Phase 4 tasks remain unreconciled with
   accepted Feature 011 evidence; that is documentation/acceptance work, not a
   basis to mark anything complete without review.

## 11. Future-agent handoff instructions

1. Start from the current branch/HEAD recorded above and inspect Git state before
   any work. Do not assume this roadmap authorizes implementation.
2. For Feature 012, begin only with the separately authorized T006 contract
   review and offline RED scope. Preserve v1 exactly and keep retrieval
   settings server-owned.
3. Read the Feature 012 artifacts, chronological log, backend handoff, frontend
   handoff, and the affected public contracts before choosing a test file or
   interface.
4. Obtain current, concrete Person 2 and Person 4 reviews for changes that
   affect their boundaries; do not reuse owner-reported earlier reviews as
   approval for new work.
5. Treat PostgreSQL, real Engines, credentials, live embedders, Gemini, OpenAI,
   network calls, benchmarks, ingestion, and mode activation as separately
   gated. Stop when the required authorization is absent.
6. Keep evidence append-only, distinguish owner-reported from Codex-run facts,
   and do not mark a master task complete without automated verification and
   explicit human acceptance.

## 12. Planning status

This document records a roadmap only. It does not modify task state, choose a
retrieval mode, authorize a provider, authorize database access, or assert
Feature 012 completion.
