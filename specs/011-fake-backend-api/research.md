# Person 3 Fake Backend API — Solution Research

**Status:** Initial research artifact only. No specification, plan, tasks, shared
contract, implementation, dependency change, or test is approved by this file.
All cross-owner API and retrieval contracts cited below remain proposed unless
their own source explicitly records approval.

## Problem and scope

Prepare the first Person 3 feature for an offline deterministic FastAPI question
endpoint with independently injected fake retrieval and fake AI provider. The
first feature is limited to one explicitly supported workflow and approved
filter fields. It must preserve evidence identity and corpus provenance, expose
explicit mock/test metadata, require no PostgreSQL or API credentials in its
tests, and not depend on Person 2's private `_RetrievalCore`.

This research follows the architecture direction supplied for Person 3 Phase
1D. It does not authorize implementation. The repository constitution requires
research, specification, plan, tasks, explicit human approval, and then
RED/GREEN behavior tests (`AGENTS.md`; `.specify/memory/constitution.md`, Core
Principles I–V and Delivery Gates; `docs/DEVELOPMENT_WORKFLOW.md`, Stages A–F).

## Evidence and repository constraints

- Project runtime is Python `>=3.12,<3.13`. Current declared runtime packages
  are Alembic, `ir-measures`, pgvector, psycopg, `rank-bm25`,
  `sentence-transformers`, and SQLAlchemy. FastAPI is absent from
  `pyproject.toml`; Pydantic is not a direct project dependency there.
  (`pyproject.toml`, `[project]` and `[dependency-groups]`.)
- The tracked `uv.lock` contains Pydantic 2.14.4 as a resolved package, but the
  project declaration does not make it an explicit application dependency.
  This lock observation is not an external compatibility or support statement.
  No FastAPI package record was found in the lockfile. Do not update either
  dependency file as part of this research.
- The architecture draft proposes Python 3.12, FastAPI/Pydantic and React /
  TypeScript, but says API shapes, failure behavior, and deployment topology
  remain open (`docs/ARCHITECTURE.md`, architecture and proposed stack sections).
- The default application provider is fake; live-provider selection must be
  explicit, credentials must not be committed or logged, and tests must make no
  paid calls (`.specify/memory/constitution.md`, Engineering Constraints;
  `DEVELOPMENT_SETUP.md`, provider setup section; `.env.example`).
- Person 3 Phase 0 says the backend, FastAPI route, public retrieval facade,
  Gemini adapter, and HTTP contract were not implemented or verified. It also
  says P1-11 and P1-14 remain open (`docs/person3/PHASE_0_BASELINE.md`, §§3,
  13; `EVIDENCE.md`, Person 3 Phase 0 entry).
- Relevant unchecked backlog scope includes P4-01–P4-08, P4-13–P4-15,
  P4-17, and P4-20; P4-09–P4-12 and P4-16/P4-18/P4-19 have broader retrieval,
  live provider, operational, or usage scope (`PROJECT_TODO.md`, Phase 4).
  First-feature scope and acceptance need a formal feature specification.
- No real article text, credentials, protected evaluation content, database,
  or local secret-bearing file was used for this research.

## Dependency options: FastAPI and Pydantic

Current package versions, compatibility, licenses, and maintenance status were
not checked against external authoritative sources because this session did not
use network access. Record them as **NOT VERIFIED**; do not infer compatibility
from the lockfile alone.

1. **FastAPI with explicit Pydantic v2 dependency constraints — recommended
candidate.** This follows the repository's proposed stack and gives the
first-feature API one framework for routing and request/response validation.
FastAPI and Pydantic should be direct dependencies if selected; relying on
transitive presence is not a stable contract. Before finalizing the spec or
editing dependencies, verify supported Python 3.12 and Pydantic compatibility
from official documentation/package metadata, then choose compatible bounded
versions and resolve the lockfile under the approved environment. Exact
versions and licenses: **NOT VERIFIED** here.
2. **FastAPI with Pydantic supplied transitively.** This avoids a direct
declaration but leaves application code dependent on an undeclared package.
Reject for an application that directly defines Pydantic request/response
models.
3. **A different/lightweight HTTP stack or direct Starlette use.** It might
reduce abstractions, but conflicts with the supplied FastAPI + Pydantic
architecture direction and creates a separate review decision. Defer unless
the official-source compatibility research finds a blocking issue.

Do not add an HTTP client/test package merely by assumption. The approved plan
should establish whether an in-process ASGI test client is available from the
selected dependency set or whether it requires an explicitly approved test
dependency. No installation or dependency synchronization is part of research.

## Application lifecycle and sync route model

The existing database engine is synchronous SQLAlchemy/psycopg
(`src/sciscope/database/session.py`, `create_database_engine`). Retrieval core
and its current `retrieve` method are synchronous (`src/sciscope/retrieval/_core.py`,
`_RetrievalCore.retrieve`), but they are private and must not become the HTTP
layer contract.

**Recommended candidate for the fake-only first feature:** build the app through
a factory that accepts provider/retrieval dependencies, constructs no database
connection or live provider by default, and disposes only resources it created
at shutdown. Use one synchronous handler/service path for deterministic fakes.
Keep the public protocol independent of FastAPI request objects. This avoids
introducing asynchronous DB work or a thread-pool policy before a real retrieval
integration is approved.

**Alternatives:**

- An `async def` endpoint that calls synchronous retrieval directly risks
  blocking the event loop when real DB work is later connected; reject unless
  blocking calls are explicitly offloaded.
- An async endpoint with thread-pool offload is a viable later integration
  option, but adds cancellation, capacity, shutdown, and error-propagation
  decisions not needed for fake-only tests.
- A synchronous endpoint is simplest with the present sync stack; if the chosen
  framework runs it in a worker pool, that runtime behavior and capacity still
  need source verification and approved tests. Framework/runtime version is
  **NOT VERIFIED** here.

Lifespan API, worker count, resource ownership, health/readiness semantics, and
deployment command remain open. No server should start in tests.

## Request, success, and error schema alternatives

No application endpoint or accepted HTTP schema exists. Retrieval-v1's request
shape is a **Person 2 reference design marked proposed**, not an HTTP question
contract (`docs/contracts/retrieval-v1.md`, status and Request DTO sections).
The first feature must not silently publish its fields as approved.

**PROPOSED schema direction for specification discussion:**

- One versioned, non-streaming POST for one explicitly selected workflow.
- Strict request object with a question string, one workflow discriminator, an
  optional request ID, and only filter fields approved for that workflow.
- The retrieval contract version is separate from the HTTP API version and is
  explicit at the service boundary. Do not include it in the public request
  unless the owners choose that as the agreed API mechanism.
- Success returns request ID, answer/result disposition, explicit mock/test
  metadata, corpus identity when retrieval supplies one, and evidence objects
  carrying chunk ID and exact source metadata.
- Error returns request ID when available plus a stable code, sanitized public
  message, and retryability only if owners accept that field.

No field name, route path, workflow enum value, HTTP status mapping, or numeric
input limit is approved by this research. The P1-11 shared API decision and
P1-14 human architecture/contract approval remain open (`PROJECT_TODO.md`,
Phase 1). Pydantic should reject unknown fields and malformed values after the
exact schema and limits are approved; repository retrieval-v1 validation is
not automatically the public question validation contract.

**Request ID alternatives:** caller-provided ID only; server-generated ID only;
or accept a caller ID and generate one when absent/invalid. Recommend the last
as a proposed usability/traceability policy, but the syntax, conflict behavior,
and whether invalid IDs reject versus replace need approval. Never echo an
unvalidated arbitrary value as trusted correlation metadata. The proposed
retrieval-v1 contract accepts 1–128 ASCII characters matching
`[A-Za-z0-9._:-]` and allows null when missing/invalid in its error envelope;
that is not automatically adopted by the HTTP API (`docs/contracts/retrieval-v1.md`,
request validation and error behavior sections).

## Dependency injection: fake retrieval and fake provider

The v1 proposal already describes a fixed fake retrieval service response stub
that supports development without Person 2 code or a database, plus an injected
fake query embedder for lexical/dense tests (`docs/contracts/retrieval-v1.md`,
Python API and errors section). The tracked example is explicitly synthetic and
demonstrates a `FakeRetrievalService` and mock-looking answer text
(`examples/phase_c_fake_handoff.py`, `FakeRetrievalService` and response builder).
Neither establishes a public application contract.

**Recommended candidate:** app factory receives two independent typed
dependencies: retrieval service and AI provider. Unit/API tests inject fixed
fakes separately, so each failure path can be exercised without PostgreSQL or
network. Fake outputs must be deterministic and evidence citations must be
limited to fixture retrieval IDs. Include explicit structured mock/test
metadata; do not use prose alone as a mock marker. Exact marker shape remains
open. No app-level default should instantiate a live provider, infer a real
credential, or silently switch from configured live mode to fake mode.

**Alternatives:**

- A single combined fake orchestrator is simpler but obscures which dependency
  failed and prevents independent injection; reject for the API boundary.
- Fake provider with real retrieval or real provider with fake retrieval
  requires external systems or credentials and is outside the first feature.
- Direct module-global singleton dependencies complicate isolation and lifecycle;
  prefer explicit app construction/dependency overrides.

## Citation identity, evidence provenance, and output validation

Prefer `chunk_id` as the first API evidence identity. Do not invent a separate
`evidence_id` unless the response needs to identify a claim-to-evidence link
distinct from a source chunk. A chunk identity is **not** corpus identity.
Preserve corpus provenance separately: delivery digest, source contract
version, and corpus version. Preserve each cited chunk's DOI, title, exact
source locator, exact passage text, and relevant section metadata from the same
retrieval response. These fields follow the proposed retrieval result/handoff,
not an approved public API schema (`docs/contracts/retrieval-v1.md`, response
DTO; `docs/person2/RETRIEVAL_V2_PERSON3_HANDOFF.md`, Result evidence and
citations).

The first feature's fake response validator should reject any citation ID not
present in that request's retrieval result and should not synthesize citation
metadata. Retrieval citation identity checks prove the response maps to a
returned chunk; they do not prove the passage supports a scientific claim.
The v2 handoff explicitly separates these judgments and prohibits fabricated
claims/citations (`docs/person2/RETRIEVAL_V2_PERSON3_HANDOFF.md`, Result evidence
and safe generation sections). The fake-only feature can test referential
integrity with synthetic fixtures; scientific entailment evaluation is out of
scope.

## No-results and insufficient-evidence semantics

The retrieval contracts define `EMPTY_RESULT` as successful retrieval with no
results and explicitly say it is not proof that the literature lacks evidence
(`docs/contracts/retrieval-v1.md`, Response DTO and UI categories;
`docs/contracts/retrieval-v2.md`, Error and data behavior;
`docs/person2/RETRIEVAL_V2_PERSON3_HANDOFF.md`, Empty and insufficient-evidence
behavior).

**PROPOSED distinction:** `no_results` represents an empty retrieval list;
`insufficient_evidence` represents a separate answer disposition after applying
an approved evidence-answerability policy. The fake provider may demonstrate
both states using synthetic fixtures, but must not imply that retrieval
emptiness establishes scientific absence. The first workflow's allowable
dispositions and whether its response includes a null answer, qualification,
or abstention remain specification decisions. Do not promise a general
scientific insufficiency classifier in this feature.

## Fake-only endpoint errors and failures

The Person 2 retrieval implementation uses typed sanitized errors such as
`INVALID_REQUEST`, `CORPUS_NOT_LOADED`, `DATABASE_UNAVAILABLE`, and
`RETRIEVAL_INTERNAL_ERROR` (`src/sciscope/retrieval/_errors.py`). The proposed
v1 contract says HTTP mapping belongs to Person 3 but supplies no status-code
table (`docs/contracts/retrieval-v1.md`, Error behavior and security).

For the fake-only endpoint, specify deterministic error cases for invalid
input, fake retrieval failure, fake provider failure, fake timeout, and
provider-output validation/citation mismatch. Map only approved public error
codes and messages; do not expose exception text, stack traces, secrets, or
local paths. Whether status codes use 4xx/5xx and which errors are retryable
must be explicitly decided in the feature spec/API contract. No retry loop,
live fallback, arbitrary timeout target, or production rate-limit behavior is
needed to demonstrate fake error paths.

## Security and operational boundaries

- No `.env`, credentials, protected evaluation artifacts, or real article
  passages may be used. Fake fixtures must be visibly synthetic.
- No live Gemini, query embedding, provider call, network operation, database
  access, migration, import, or server startup is part of this feature research.
- Avoid logging question text, article/evidence text, credentials, full
  database URLs, vectors, exception/stack details, or absolute paths. The
  retrieval-v1 proposal explicitly lists sensitive values excluded from logs
  (`docs/contracts/retrieval-v1.md`, Error behavior and security).
- Do not make production deployment, CORS origins, authentication, rate limits,
  or externally reachable health endpoints part of the fake-only feature.
  Decide only the app factory/lifecycle and minimal local health behavior
  needed for tests; defer production policy to a reviewed operational feature.
- Do not assume readiness requires PostgreSQL or an active corpus when the
  first app can run entirely with injected fakes. Define health/readiness
  semantics before implementation if endpoints are included.

## Public retrieval facade and shared-contract adoption

`retrieval.v1` is labeled a Person 2 reference design, proposed and not team
approved (`docs/contracts/retrieval-v1.md`, opening status). It proposes
Person 2-owned DTOs/protocol/errors and injected query embedder, while Person 3
owns HTTP and RAG orchestration (Ownership boundary and Python API sections).
Actual retrieval source remains private `_RetrievalCore`; its response object
states it is not the shared facade (`src/sciscope/retrieval/_core.py`, `_Response`
and `_RetrievalCore`).

`retrieval.v2`'s BM25 version boundary is Person 2-approved for their
implementation; the document explicitly leaves Person 3 application
integration pending (`docs/contracts/retrieval-v2.md`, status and compatibility
sections). The Person 2 handoff says the core is private and v2 is not enabled
in a shared app (`docs/person2/RETRIEVAL_V2_PERSON3_HANDOFF.md`, Selection and
compatibility). The first API feature should therefore use a fake retrieval
protocol and not claim to implement shared real retrieval integration.

Required before real retrieval integration: Person 2 review/adoption of a
public typed facade; exact request/response/error types and compatibility
policy; explicit retrieval version selection; query embedder protocol/fake
ownership; and separate approval for any Person 3 live query-embedding
adapter/config. Dense/hybrid must not be represented as executable in a
fake-only feature. For future real retrieval smoke integration, v1 lexical is
an embedding-free candidate, not a selected winner. Strategy selection needs
separate approved comparative evaluation.

## Alternatives rejected or deferred

- **Direct API import of `_RetrievalCore`:** reject because its module/types are
  private and the proposed shared facade has not been adopted.
- **Real retrieval or PostgreSQL in first-feature tests:** defer because the
  requested feature is fake-only and must run without a DB. Contract the
  boundary with fakes first.
- **v1 dense/hybrid by default:** reject for this feature because no compatible
  live query embedder is in scope. A test fake vector does not establish an
  approved live adapter or production query path.
- **Select v2 BM25 as the winning strategy:** defer. Person 2 approved v2 as an
  opt-in implementation boundary; neither that approval nor prior development
  measurements establish a general retrieval winner or Person 3 enablement.
- **Separate `evidence_id`:** defer unless requirements show that chunk IDs
  cannot serve as the evidence reference key. Keep corpus/snapshot identity in
  distinct provenance fields.
- **All workflows/all filters:** reject for first scope. P4/P5 backlog names
  several workflows, but no shared API schema or complete filter contract is
  approved (`PROJECT_TODO.md`, P1-09/P1-11/P1-14 and Phase 4/5).
- **Streaming, production auth, CORS, rate limits, deployment, live Gemini,
  live query embedding, and real-answer quality evaluation:** defer to their
  own approved scope. They are not needed to test deterministic fake flow.
- **Unverified version pin or silent dependency fetch:** reject. External
  compatibility and current versions are **NOT VERIFIED** in this research.

## Open decisions and approvals required

1. **Person 2:** approve/design the public typed retrieval facade and confirm
   ownership of its protocol, DTOs, error types, and query-embedder protocol/fake.
   Retrieval-v1 adoption remains proposed; v2 app integration remains pending.
2. **Person 3 + Person 4:** agree one first workflow, its request and success
   schema, request-ID policy, mock/test marker, and evidence response shape.
   Names and values must be decided in the spec, not inferred from examples.
3. **Person 2 + Person 3 + Person 4/team:** approve which filter fields are
   supported by that one workflow and whether they align with P1-09/P1-11.
4. **Person 3/team:** decide public error codes, HTTP status mapping, and
   retryability semantics; retrieval-v1 has no approved HTTP status table.
5. **Person 3:** decide app-factory/lifecycle and whether local health/readiness
   is in scope; keep sync behavior for fake-only flow unless a reviewed design
   establishes another requirement.
6. **Person 3 + team:** later research/approval for FastAPI/Pydantic versions,
   dependency constraints, Python 3.12 compatibility, licenses, test client,
   and lockfile impact. Current external verification is **NOT VERIFIED**.
7. **Separate later decision:** Gemini SDK/model/API and credentials require
   explicit provider approval; live query embedding separately requires a
   compatible model/provider/config decision. Neither belongs in the fake-only
   first feature.
8. **Human/team gate:** approve the eventual feature specification and plan
   before tests or implementation, consistent with the repository workflow.
   P1-11 and P1-14 remain open (`PROJECT_TODO.md`, Phase 1).

## Recommendation for the subsequent specification

Specify only one offline workflow endpoint, an app factory with injected
retrieval/provider protocols, deterministic fakes, strict approved request and
response validation, explicit mock/test metadata, citation ID membership
validation against the same fake retrieval result, exact provenance
serialization, and sanitized fake failure mapping. Use `chunk_id` as the
evidence reference key unless the approved user story demonstrates a separate
identity requirement. Keep corpus identity separate from chunk identity.

Exclude live Gemini, query embedding, direct private-core dependency, database
access, v2 enablement, production deployment/security policy, unapproved filter
fields, and scientific answer-quality claims. This is a research recommendation,
not an approved spec or implementation authorization.

When authorized, use the official Spec Kit workflow to create `spec.md`,
`plan.md`, and `tasks.md` in this feature directory; keep the feature to at most
eight tasks (`docs/DEVELOPMENT_WORKFLOW.md`, Required feature artifacts and
Stages B–E). Re-run solution research before finalizing any changed scope.

## Research method and verification limits

Inspected tracked governance, baseline, backlog, dependency declarations and
lockfile, retrieval contracts/implementation, Person 2 handoffs, and existing
Spec Kit feature artifacts. No external documentation was fetched, so current
FastAPI/Pydantic versions, compatibility, package licenses, support policies,
and test-client options are **NOT VERIFIED**. No packages were installed; no
tests, formatters, database operations, Docker, API/provider calls, protected
evaluation access, or secret reads occurred. This artifact does not change
`PROJECT_TODO.md` or `EVIDENCE.md`, and does not mark any task complete.
