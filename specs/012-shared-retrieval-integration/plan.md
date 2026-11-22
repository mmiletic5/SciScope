# Implementation Plan: Feature 012 — Shared Retrieval Integration

**Branch**: `feature/p4-09-backend-retrieval-integration`
**Baseline**: `7a8233bd029ba666274d8ecd902a84bfe6cf8fe6`
**Date**: 2026-11-22
**Spec**: [spec.md](spec.md)
**Status**: APPROVED 2026-11-22 by Person 3 (Backend & AI) for T012-A and beginning T012-B offline work. Concrete v2 HTTP work, affected-owner reviews, database access, mode activation, and final feature acceptance remain separately gated.

## Summary

Add a small injected adapter at the question-service boundary. It accepts the existing validated question and request ID, constructs one explicitly configured public `RetrievalRequest`, delegates through Feature 007's exported `RetrievalService`, and maps exact response evidence and corpus identity to the question-service outcome. Keep public HTTP models free of retrieval-private, ORM, SQL, and driver types. Keep fake-only construction inert. Apply the adopted component-origin metadata and sanitized retrieval error direction only after DTO/frontend compatibility is verified and any concrete frontend-visible changes receive the required review.

The initial PostgreSQL lexical smoke configuration is allowed only as a separately authorized test-only configuration. v1 dense is the leading measured candidate; final application activation remains **PENDING** because existing five-question measurements are development-only and narrow. No benchmark, final mode activation, database connection, provider call, or test is authorized by this draft.

## Adopted D012 design decisions

| Decision | Plan direction | Remaining gate |
| --- | --- | --- |
| D012-01 Retrieval | v1 dense leads the measured candidates; v1 lexical is test-only for a separately authorized PostgreSQL wiring smoke; no fallback. | Approved comparative evidence, compatible explicit query embedder, and explicit Person 3 acceptance before final application activation. |
| D012-02 Metadata | Separate retrieval and answer origins from test-data/environment status; preserve accepted fake-only values. | Verify existing DTO/frontend compatibility; separately version if additive fields break strict clients. |
| D012-03 Errors | Use sanitized mappings where compatible; preserve typed retryability; server-owned invalid configuration is a server failure. | Verify exact HTTP status/code compatibility; no private exception details. |
| D012-04 Lifecycle | Explicit composition root owns created Engine disposal; adapters do not dispose borrowed engines; no implicit DB/provider initialization. | Validate the concrete lifecycle boundary in the approved composition. |
| D012-05 Provenance | Preserve exact identifiers, DOI, locator, text, title, and corpus identity without interpretation or synthesis. | Person 1 review only if source meaning or upstream contract changes. |

Person 2/Person 4 delegation is owner-reported decision authority, not approval of a specific implementation or test outcome. Required affected-owner reviews, verification, and explicit acceptance remain separate.

## Technical Context

| Item | Draft plan |
| --- | --- |
| Language/runtime | Python 3.12; existing synchronous FastAPI and dataclass service layers. |
| Dependencies | Existing public retrieval DTOs/service, FastAPI, Pydantic, SQLAlchemy. No new dependency proposed. |
| Storage | Person 2-owned PostgreSQL/pgvector; no schema, migration, ingestion, or corpus changes. |
| Testing | Existing pytest suite; offline adapter/API tests and one separately authorized guarded PostgreSQL integration test. |
| Target | In-process application composition; no server command or deployment topology established. |
| Performance goals | None specified. Record retrieval latency observations only; no production SLO claim. |
| Configuration | Required explicit version, mode, top-k, optional filters/ranking, and compatible embedder config when dense/hybrid. No implicit default until evidence/reviews. |
| Constraints | Preserve Feature 011 fake-only behavior, Feature 007 public boundary, source identity, privacy, and independent manual verification. |

## Constitution Check

| Gate | Draft status |
| --- | --- |
| Spec Kit research/spec/plan/tasks and owner approval before behavior tests | Approved by Person 3 on 2026-11-22 for T012-B offline work. Concrete v2, database, provider, mode-selection, and acceptance gates remain separate. |
| Test-first RED/GREEN and truthful evidence | Planned per implementation increment. Planning task uses no artificial behavior tests. |
| Shared contract readiness | D012 design directions and Person 3 planning approval are recorded; compatibility verification and applicable affected-owner reviews remain pending before their concrete changes. |
| Source provenance | Exact fields mapped from public response; Person 1 review required if meaning changes. |
| Fake/live and secrets | Fake-only defaults remain offline; no implicit live provider, embedder, database, or credential. |
| Small, reviewed changes | Eight maximum tasks/increments; each focused. |
| Human verification | Person 3 independent Windows verification and explicit decision; automation alone does not complete feature. |
| Evidence/backlog | Append Feature 012 planning/status without changing Feature 007/011 history or checking P4-09 complete. |

**Gate result:** T012-A is approved and T012-B offline work may begin. Complete every stated compatibility, affected-owner review, mode-selection, and database gate before the dependent work it controls. This approval does not authorize T012-C through T012-H automatically.

## Proposed Architecture

### Adapter boundary

Proposed new module: `src/sciscope/question_service/retrieval_adapter.py`.

The adapter should implement the existing `question_service.contracts.RetrievalService` protocol and receive, through construction:

- The public `sciscope.retrieval.RetrievalService` instance.
- An immutable Person 3-owned settings value containing an explicit supported `contract_version`, `mode`, `top_k`, optional filters/ranking, and any non-secret reference needed to select the already-composed service/embedder.
- No database Engine, ORM model, SQL, private retrieval core, DBAPI connection, provider credential, or HTTP request object in the question-service protocol.

Per valid call, the adapter forwards the question and request ID unchanged, constructs exactly one validated public `RetrievalRequest`, invokes the public facade once, and converts the returned DTOs. The question API continues to depend on its injected protocol; it does not import Person 2's private core or construct the database itself. The application request must not expose retrieval mode as caller-controlled input unless a separate contract approval adds it.

Dense and hybrid require an explicitly configured embedder compatible with the corpus identity. The public query embedder protocol remains Person 2-owned; whether Person 3 owns a live embedding adapter/configuration is not approved here. This feature's tests use deterministic/offline fakes. Missing embedder or mismatch fails closed; it never triggers lexical fallback.

### Exact response mapping

| Public retrieval value | Question-service field | Rule |
| --- | --- | --- |
| `result.chunk_id` | `Evidence.chunk_id` | Preserve exact stable ID; do not derive a new ID. |
| `result.doi` | `Evidence.doi` | Preserve exact stored DOI. |
| `result.source_locator` | `Evidence.source_locator` | Preserve exact opaque locator. |
| `result.text` | `Evidence.passage` | Preserve exact retrieved passage text byte-for-byte/string-for-string. |
| `result.paper.title` | `Evidence.paper_title` | Preserve exact title. |
| `response.corpus.delivery_digest` | `CorpusProvenance.delivery_digest` | Preserve exactly. |
| `response.corpus.source_contract_version` | `CorpusProvenance.source_contract_version` | Preserve exactly. |
| `response.corpus.corpus_version` | `CorpusProvenance.corpus_version` | Preserve exactly. |
| `response.request_id` | `RetrievalOutcome` call identity | Require equality with forwarded request ID; do not substitute. |

Additional retrieval fields remain available internally in `RetrievalResponse`: retrieval version, embedding configuration, effective mode/top-k/filter/ranking/warning metadata, paper authors/journal/year/language/license/URL, section metadata, scores/ranks, and corpus identity. The accepted Feature 011 HTTP evidence model currently exposes only chunk ID, DOI, source locator, passage, and paper title; no additional bibliographic fields should be exposed without a separate reviewed response-contract change.

An empty `results` tuple becomes an empty `RetrievalOutcome.evidence` while retaining corpus provenance. It stays the question service's `no_results` outcome; the fake provider is not called. It is not equivalent to `insufficient_evidence` and not a claim about the literature.

### Metadata design — D012-02, proposed v2 only

Keep the accepted v1 `MockMetadata(is_mock=true, is_test_data=true)` unchanged.
The proposed closed v2 metadata object has one entry per component:

```json
{
  "retrieval": {"configured_origin": "real", "executed": true, "is_test_data": false},
  "answer_provider": {"configured_origin": "fake", "executed": true, "is_test_data": true}
}
```

`configured_origin` is only `synthetic`, `fake`, or `real`; it describes the
configured dependency, not a claim that it ran. `executed` describes whether
that component was called for this request. `is_test_data` describes the data
or fixture status applicable to that component, independently of the other
component. It must be set from explicit composition/test configuration, never
invented from a retrieval result.

| Scenario | Retrieval metadata | Answer-provider metadata |
| --- | --- | --- |
| Synthetic retrieval + fake provider | `synthetic`, executed true, test data true | `fake`, executed true, test data true |
| Real retrieval + fake provider | `real`, executed true, configured DB status | `fake`, executed true, configured provider-fixture status |
| Real retrieval + real provider | `real`, executed true, configured DB status | `real`, executed true, configured provider/data status |
| Isolated PostgreSQL test database | retrieval is `real`, executed true, test data true | determined independently by the configured provider |
| Empty retrieval | retrieval executed true; actual configured origin/status | configured origin, executed false; do not claim provider output |
| Retrieval failure before provider | retrieval executed true; actual configured origin/status | configured origin, executed false; do not claim provider output |
| Answer-provider failure | retrieval executed true; actual configured origin/status | configured origin, executed true; response has no invented answer/claims |

The internal metadata contract and validators are implemented before the public
adapter so a truthful `RetrievalOutcome` can exist. v2 response serialization is
implemented later. The proposed v2 endpoint/schema remains subject to explicit
approval; no v1 field is added.

### Error mapping — D012-03 design adopted; contract verification pending

The facade error includes a public message, request ID and a cause-specific `retryable` flag. Preserve the facade's retryability rather than inferring it from the code alone. Existing Feature 011 error codes remain unchanged. Use the mapping below where compatible with the accepted HTTP contract; verify exact compatibility before implementation. The delegation does not constitute Person 2/Person 4 review of this implementation or its test outcomes:

| Retrieval error | Proposed HTTP behavior | Candidate code/message | Retryability/request ID |
| --- | --- | --- | --- |
| `INVALID_REQUEST` | Adapter-owned configuration: `500`; caller question validation stays existing `422` | Adapter: existing `internal_error` generic message; caller: existing `invalid_request` message | Copy the typed value unchanged (currently expected false); preserve safe route-scoped request ID. |
| `UNSUPPORTED_CONTRACT_VERSION` | `500` because version is selected by server configuration, not this request body | Existing `internal_error`, generic sanitized text | Copy the typed value unchanged (currently expected false); preserve safe request ID. |
| `CORPUS_NOT_LOADED` | `503` | Existing `retrieval_unavailable`, generic sanitized retrieval text | Use typed `retryable` value (current core emits false); preserve request ID. |
| `EMBEDDING_CONFIGURATION_MISMATCH` | `503` | Existing `retrieval_unavailable`, generic sanitized retrieval text | Use typed flag (current core emits false); preserve request ID. |
| `EMBEDDING_UNAVAILABLE` | `503` | Existing `retrieval_unavailable`, generic sanitized retrieval text | Use typed flag (current core distinguishes missing embedder from transient `QueryEmbeddingUnavailable`); preserve request ID. |
| `DATABASE_UNAVAILABLE` | `503` | Existing `retrieval_unavailable`, generic sanitized retrieval text | Preserve typed flag (the core marks recognized transient database failures retryable); preserve request ID. |
| `RETRIEVAL_INTERNAL_ERROR` | `500` | Existing `internal_error`, generic sanitized text | Copy the typed value unchanged (currently expected false); preserve request ID. |
| Existing controlled `DEPENDENCY_TIMEOUT` | `504` | Existing `dependency_timeout`, existing sanitized timeout text | true as approved by Feature 011; preserve request ID. |

Mapping several retrieval errors to the existing `retrieval_unavailable` code preserves the existing public error vocabulary. The proposed v2 route gets a dedicated typed-retrieval exception handler before the generic exception handler. It receives the route-scoped request ID, maps only the approved code/status/message, and copies `RetrievalException.retryable` unchanged. It does not route typed errors through `DependencyFailure` or a generic handler. The existing caller-validation handler and controlled `DEPENDENCY_TIMEOUT` handler remain distinct. Do not expose retrieval exception reprs, SQL, credentials, DB URL, embedding vectors, question/passage text, local paths, or stack traces. Logs use request ID, approved public category, and safe operational context only; query text, evidence, credentials, and vectors are excluded. No retry loop or alternate mode is added.

### Composition and lifecycle — D012-04 design adopted

The production composition root is a required implementation dependency because
the repository exposes no approved production factory for an Engine-backed
public facade. It must create the Engine, compose an exported public
`RetrievalService` through an approved public construction/factory interface,
create the public-only question adapter, and inject that adapter into the v2
application factory. The adapter imports only `sciscope.retrieval` exports.
`_compose_private_executor` is private/test-side infrastructure and must not be
used by the production question adapter or treated as its approved API.

The composition-root creator owns Engine disposal after checked-out connections
are returned. Borrowed Engines are disposed only by their creator. Imports,
application factory construction, and fake-only paths remain inert. Dense/hybrid
composition needs an explicitly configured compatible `QueryEmbedder`; missing
or incompatible configuration fails closed with the mapped server error. No
server command or deployment topology is proposed. Validate the ownership
boundary against the actual host composition during implementation review.

## Retrieval-mode selection and evaluation plan

Existing evidence is documented in [`research.md`](research.md) and Person 2's [`RETRIEVAL_V2_RESULTS.md`](../../docs/person2/RETRIEVAL_V2_RESULTS.md). It compares the five-question development sample and explicitly disclaims reliable general quality conclusions. v1 dense is the leading candidate because it tied v1 hybrid on measured Recall@10 and MRR@10 with lower median latency. Final application activation remains **PENDING** approved comparative evidence, compatible explicit query embedder configuration, and Person 3 acceptance. v1 lexical is allowed only as a separately authorized PostgreSQL wiring smoke-test setting, not as an implicit application default.

Before selecting an application version/mode:

1. Use only `gq-sp-001`, `gq-cmp-001`, `gq-conf-001`, `gq-gap-001`, and `gq-ins-001`; do not read or tune on the other 16 Golden v0 questions. Any additional comparison beyond existing authorized evidence requires its own authorization and review.
2. Compare distinct behavior arms: v1 dense/lexical/hybrid and v2 lexical/hybrid. Record that v2 dense is behaviorally unchanged from v1 dense rather than presenting it as a distinct algorithm. Use one fixed corpus snapshot and dataset/relevance label revision.
3. Hold query text, filters, top-k (report K=5/10/20), hybrid candidate-pool settings, repetition count, software versions, environment, and embedder configuration constant where a comparison is meaningful. Dense and hybrid must use an explicitly named compatible query embedder; the five existing vectors can be reused only if their provenance/configuration matches and Person 2 authorizes it. No embedding provider is assumed or called implicitly.
4. Report Recall@K, Evidence Hit@K, and per-question values; report MRR@10 for positive-evidence questions only. Keep `gq-ins-001` out of positive relevance denominators and separately assess that empty retrieval is not misreported as scientific insufficiency.
5. Report median and p95 retrieval latency, repeatable ordered chunk IDs, and exact chunk/DOI/locator/text/corpus provenance for every returned hit. Keep source identity integrity distinct from retrieval relevance and citation support.
6. Preserve failures and all arms. Person 2 reviews comparative evidence; Person 3 chooses a server-side application setting only after approved evidence, compatible embedder configuration, and explicit Person 3 acceptance. If evidence remains insufficient, selection stays pending. A lexical v1 smoke configuration may be used only for the separately authorized PostgreSQL wiring smoke and is not an application default.

The five cases are too small and narrow for statistical significance or generalization claims. Do not invent a threshold or winner. Any future configurable modes remain server-owned configuration; they are not caller-controlled HTTP inputs under this scope.

## Error, citation, and privacy test boundaries

- Unit-test adapter request construction, exact forwarding, mapping, empty response, and all malformed-response cases with public service stubs; no PostgreSQL, network, or provider.
- Exercise `QuestionService` with the existing deterministic `FakeAnswerProvider` and adapter-produced evidence. Verify response-local citation membership, duplicate/nonmember rejection, and empty retrieval bypassing the provider.
- Test every public retrieval code, request-ID behavior, public HTTP status/code/message/retryability, safe logging, and `DependencyFailureCode.DEPENDENCY_TIMEOUT` according to approved mapping. Do not pass through the public retrieval exception message if it is not approved for the HTTP contract.
- Test each selected version/mode is forwarded exactly; missing/mismatched config raises a mapped error and never triggers fallback.
- Assert API imports, fake app construction, and offline tests do not call Engine creation/connect, query embedder, real answer provider, network, or server listener.
- Keep citation membership checks limited to identity. Scientific entailment/relevance remains outside acceptance claims for this feature.

### Required RED/GREEN test coverage map

The following coverage is a plan only; test files are not created in this task. Each item must first be expressed as a behavior test, observed RED for the missing approved behavior, and then recorded GREEN after the minimal implementation.

| # | Required behavior | Planned increment / test location |
| ---: | --- | --- |
| 1 | Internal metadata validation for origins, execution, and test-data state | T012-B, metadata/validation tests |
| 2 | Valid public `RetrievalRequest` construction with explicit settings | T012-C, `tests/backend/test_retrieval_adapter.py` |
| 3 | Exact request-ID preservation and response-ID consistency | T012-C, adapter tests |
| 4 | Exact evidence and corpus identity mapping | T012-C, adapter tests |
| 5 | Empty retrieval preserves no-results behavior and provider-not-invoked metadata | T012-C/T012-D, adapter/API tests |
| 6 | Truthful retrieval/answer metadata combinations and failure execution state | T012-B/T012-D, contract/API tests |
| 7 | Citation membership, duplicate rejection, and nonexistent-ID rejection | T012-C/T012-F, QuestionService/API tests |
| 8 | Invalid retrieval request classification (caller input versus adapter-owned config) | T012-D, v2 API tests |
| 9 | Unsupported retrieval version classified as server-owned configuration failure | T012-D, adapter/API tests |
| 10 | `CORPUS_NOT_LOADED` sanitized mapping | T012-D, adapter/API tests |
| 11 | `DATABASE_UNAVAILABLE` status/retryability mapping | T012-D, adapter/API tests |
| 12 | `EMBEDDING_CONFIGURATION_MISMATCH` mapping with no lexical fallback | T012-D/T012-F, adapter/API tests |
| 13 | `EMBEDDING_UNAVAILABLE` cause-specific retryability mapping | T012-D, adapter/API tests |
| 14 | `RETRIEVAL_INTERNAL_ERROR` sanitized mapping | T012-D, adapter/API tests |
| 15 | Existing controlled dependency timeout response | T012-D, adapter/API tests |
| 16 | Fake answer provider consumes adapter evidence with response-local claims | T012-F, `tests/backend/test_retrieval_http_integration.py` |
| 17 | No DB/embedder/provider/network/listener initialization in import/fake path | T012-E, app factory and integration tests |
| 18 | Exactly configured version/mode forwarded | T012-C/T012-F, adapter/integration tests |
| 19 | Missing/invalid mode configuration fails closed without fallback | T012-C/T012-F, adapter/integration tests |
| 20 | No synthesized source identifier, citation, passage, bibliographic field, or corpus identity | T012-C/T012-F, adapter/integration tests |

## PostgreSQL read-only integration gate

No database is accessed until the spec/plan is approved and a separate explicit database authorization is recorded. The guarded integration test should be placed under `tests/retrieval/` so the existing `retrieval_engine` fixture applies, for example `tests/retrieval/test_backend_adapter_postgres.py`. It may compose the public facade using the test-only private-core composition helper; production adapter imports remain public-only.

Preflight must verify all of the following before retrieval: exact database `sciscope_test_005`; approved role `sciscope`; PostgreSQL 17; compatible pgvector (expected 0.8.7); Alembic revision `f005_pgvector_foundation`; one expected active pilot snapshot; and expected counts of 17 papers, 319 sections, 728 chunks, and 728 vectors. Do not print or persist the URL/credentials. If any gate fails, abort before retrieval with no schema/data writes.

For each retrieval/source verification transaction, explicitly execute and assert `SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY`, then read the approved snapshot identity and exact persisted fields. The facade already uses read-only repeatable-read behavior, but the integration test must assert it rather than assume a generic fixture makes every transaction read-only. Compare preflight/postflight database identity, role, version, extension, Alembic revision, active import identity, counts, and corpus provenance. Verify returned IDs/DOI/locator/text/title resolve to the same active snapshot and repeated identical requests have deterministic results where the selected mode promises that. No migration, ingestion, activation, or provider call is allowed.

The planned command after the test exists is `uv run --locked pytest tests/retrieval/test_backend_adapter_postgres.py -q`. Owner execution must be an independent Windows PowerShell run; any Codex-run Ubuntu result is separately labeled. No database result is claimed by this plan.

## Proposed source/test/documentation structure

```text
specs/012-shared-retrieval-integration/
├── research.md
├── spec.md
├── plan.md
├── tasks.md
└── checklists/requirements.md

src/sciscope/question_service/
└── retrieval_adapter.py              # proposed public-facade adapter

src/sciscope/api/
├── http_models_v2.py                 # proposed, only after v2 contract approval
├── routes_v2.py                      # proposed `/api/v2/questions` boundary
├── app.py                            # only if approved lifecycle/composition changes
└── routes.py                         # preserve accepted v1 route and models unchanged

tests/backend/
├── test_retrieval_metadata.py        # proposed internal metadata/validation coverage
├── test_retrieval_adapter.py         # proposed offline public-facade request/mapping coverage
├── test_question_api_v2.py           # proposed v2 contract/error compatibility
└── test_retrieval_http_integration.py # proposed in-process fake/provider contract

tests/retrieval/
└── test_backend_adapter_postgres.py  # proposed guarded isolated DB check

docs/person3/
└── P4_09_TEST_LOG.md                 # append-only feature chronology
```

Paths are planning targets, not files created in this task except the spec/checklist/log artifacts. Do not modify Feature 007 or Feature 011 accepted records. Do not add a dependency, database migration, server command, or deployment instructions.

## Verification and manual checkpoints

Every behavior increment follows RED → minimal GREEN → focused automated checks → independent owner command/review → explicit decision → authorized focused commit. RED/GREEN commands are placeholders until tests are created after approval; no outcomes may be prefilled.

| Increment | Owner command (Windows PowerShell, after tests exist) | Expected observation/manual review | Review/decision |
| --- | --- | --- | --- |
| 012-A | No behavior-test command; review spec, plan, research, checklist, and decision register. | Confirm scope, metric protocol, metadata scenarios, all seven typed errors, and open questions are represented. | Person 2 retrieval/version/error review; Person 4 HTTP/metadata review; Person 1 if provenance meaning changes; explicit spec/plan approval. |
| 012-B | `uv run --locked pytest tests/backend/test_retrieval_metadata.py -q` | Independently inspect all component configuration, execution, and test-data scenarios; confirm v1 remains untouched. | Person 3 records outcome/decision; Person 4 only if a public shape is proposed. |
| 012-C | `uv run --locked pytest tests/backend/test_retrieval_adapter.py -q` | Inspect exact request forwarding and all preserved evidence/provenance fields. | Person 2 boundary review; owner records outcome/decision. |
| 012-D | `uv run --locked pytest tests/backend/test_question_api.py tests/backend/test_question_api_v2.py -q` | Inspect v2 sanitized responses, typed retryability, request IDs, no-provider-execution metadata, and unchanged v1 JSON shapes. | Person 2 + Person 4; explicit outcome. |
| 012-E | `uv run --locked pytest tests/backend/test_app_factory.py tests/backend/test_retrieval_http_integration.py -q` | Review inert imports/factory, no resource init, and documented owner/disposal boundary. | Person 3 manual verification; owner decision. |
| 012-F | `uv run --locked pytest tests/backend/ tests/retrieval/test_public_service.py tests/retrieval/test_public_contracts.py -q` | Confirm offline regression, fake provider integration, configured mode forwarding, and no fallback. | Person 2 + Person 4 review; owner decision. |
| 012-G | `uv run --locked pytest tests/retrieval/test_backend_adapter_postgres.py -q` | Independently review safe identity/count output, read-only isolation assertions, provenance mapping, determinism, and no state change. Run only after separate DB authorization. | Person 2 database/retrieval review; Person 3 Windows run; explicit decision. |
| 012-H | Re-run approved focused commands plus applicable `uv run --locked ruff check ...`, `uv run --locked ruff format --check ...`, `uv run --locked mypy ...`, and `git diff --check`. | Review final evidence chronology, mode-selection record, all failures/corrections, and no unapproved files. | Person 2/4 and applicable Person 1 decisions; Person 3 explicit `ACCEPTED` or `REJECTED`; no automatic completion. |

The exact changed paths and focused static-check command arguments must be finalized after approved tasks identify files. This plan is not an instruction to run any future command now.

## Risks and limitations

- Existing mode evidence is a five-query development comparison, not reliable general selection evidence; v1 dense is the leading candidate, while final application activation remains pending.
- Dense/hybrid activation requires an explicitly compatible query embedder configuration; no model is selected here.
- Feature 011 metadata types cannot represent mixed real/fake components. Verify DTO/frontend compatibility; preserve fake-only response values and use a separately approved version if additive fields are incompatible. Concrete frontend-visible changes require Person 4 review.
- Retrieval error codes do not map one-to-one to the current HTTP error enum. Grouping them can reduce actionable detail; adding specific codes may change the frontend contract.
- `retrieval.v1` is still labeled a proposed shared contract; Feature 007's accepted facade scope does not by itself approve broader v1 adoption.
- An adapter can preserve identity and exact text but cannot prove scientific support. The current citation validator checks identity membership only.
- Engine ownership and no-import-connect behavior must be tested against the explicit composition-root ownership decision without silently initializing resources.
- The existing fixture guards DB identity and active snapshot, but does not automatically make all test operations read-only; every transaction in the new integration test must enforce that boundary.

## Constitution re-check

No application or test code is changed in the planning task. Person 3 approved the specification and plan on 2026-11-22 and authorized T012-B offline work only. Tests remain fake/offline by default. No feature completion, backlog check-off, CI pass, database result, specific implementation review, human verification, or acceptance is claimed here.
