# Tasks: Fake-Only Backend Question API

**Feature branch**: `011-fake-backend-api`

**Status**: Feature approval recorded — T001 is authorized but not started; no task is complete.

## Preconditions and execution rule

Feature approval, the HTTP contract, feature-scoped P1-11/P1-14 disposition,
and exact dependency constraints are recorded in [plan.md](plan.md#approval-record).
Person 3 authorized T001 after that record is committed. T001 remains unstarted;
later tasks remain subject to the dependency order below. All eight tasks exclude
`retrieval.v2`, live Gemini/query
embedding, real retrieval/database, private `_RetrievalCore`, streaming, auth,
rate limiting, deployment, and scientific-answer evaluation.

## Dependency order

```text
approval gates -> T001 -> T002 -> T003 -> T004 -> T005 -> T006 -> T007 -> T008
```

The listed commands are future verification commands only. Each executable
increment must observe its RED test before its minimal GREEN implementation.

## Phase 1 — Environment preparation

### T001 — Establish the approved FastAPI test environment

- [ ] T001 Apply the approved FastAPI/Pydantic/HTTPX constraints and prepare `pyproject.toml`, `uv.lock`, and `tests/backend/__init__.py` for backend behavior tests.

  - **Owner**: Person 3.
  - **Goal and scope**: After dependency approval, add explicit FastAPI and
    Pydantic runtime dependencies plus explicit HTTPX development/test support.
    Resolve only the approved Python 3.12 lock graph; add no server runner,
    provider SDK, database configuration, or unrelated package.
  - **Requirements**: Enables FR-001–FR-007, FR-012, FR-015; NFR-001/NFR-004;
    SC-001/SC-005.
  - **Dependencies**: Approved specification, plan, feature-scoped shared
    contract disposition, and dependency constraints recorded in plan.md; no
    earlier Feature 011 task.
  - **Proposed source/test paths**: `pyproject.toml`, `uv.lock`,
    `tests/backend/__init__.py`.
  - **RED-first behavior test**: None. This is environment preparation, so a
    FastAPI RED test must not be required before approved test dependencies are
    installed.
  - **Baseline verification**: During T001, run `uv lock --check` and
    `uv run python -c "import fastapi, httpx, pydantic"`.
  - **Expected initial failure/reason**: No executable HTTP RED test: FastAPI
    and explicit HTTPX are absent from declared dependencies.
  - **Minimal GREEN implementation**: Dependency declaration/lock change and
    empty test package only; no feature behavior.
  - **Negative/security requirements**: Confirm no provider SDK, credential,
    network client, database connection, or unrelated dependency appears.
  - **Acceptance checkpoint**: Reviewed constraints/lock make the first offline
    HTTP RED test executable.
  - **Proposed small commit boundary**: `build(api): add approved API test dependencies`.

## Phase 2 — HTTP foundation

### T002 — Create the injectable app factory

- [ ] T002 Create `src/sciscope/api/app.py` and `src/sciscope/api/__init__.py` with a minimal FastAPI app factory using injectable sentinels, proved by `tests/backend/test_app_factory.py`.

  - **Owner**: Person 3.
  - **Goal and scope**: Establish the composition-root skeleton with opaque,
    injectable sentinel dependencies used only to prove construction and
    isolation. T002 requires no real retrieval/provider implementation or
    formal protocol; T005 introduces the typed interfaces/fakes and T007
    completes final question-service wiring. T002 creates no engine, provider,
    embedder, background worker, outgoing call, or listening server.
  - **Requirements**: FR-001, FR-006, FR-014–FR-017; NFR-001/NFR-004;
    SC-001/SC-005.
  - **Dependencies**: T001 and all approval gates.
  - **Proposed source/test paths**: `src/sciscope/api/__init__.py`,
    `src/sciscope/api/app.py`, `tests/backend/test_app_factory.py`.
  - **RED-first behavior test**: In-process `TestClient` constructs the minimal
    app with opaque sentinel objects and observes no external
    initialization/listener. It asserts no question success behavior.
  - **Expected RED failure**: `create_app` and the API package do not exist.
  - **Minimal GREEN implementation**: Factory skeleton and dependency
    container for inert sentinels only; no production question route or service
    invocation.
  - **Focused verification commands**: `uv run pytest tests/backend/test_app_factory.py`;
    `uv run ruff check src/sciscope/api tests/backend/test_app_factory.py`.
  - **Negative/security requirements**: Sentinels fail on database, network,
    provider, or `_RetrievalCore` construction/import.
  - **Acceptance checkpoint**: App factory is offline and accepts injected inert sentinels; formal fake dependencies are introduced in T005.
  - **Proposed small commit boundary**: `feat(api): add injectable app factory`.

### T003 — Define closed versioned HTTP schemas and input validation

- [ ] T003 [US1] Add Pydantic models in `src/sciscope/api/http_models.py` and RED schema tests in `tests/backend/test_http_models.py`.

  - **Owner**: Person 3.
  - **Goal and scope**: Define the request, three success states, error,
    metadata, evidence, claim, and corpus shapes. Enforce literal
    `research_question`, trimmed question length 1–2,000, no filters, and no
    unknown fields.
  - **Requirements**: FR-001, FR-002, FR-003, FR-005, FR-007–FR-009, FR-016; NFR-002;
    SC-001–SC-004.
  - **Dependencies**: T002 and all approval gates.
  - **Proposed source/test paths**: `src/sciscope/api/http_models.py`,
    `tests/backend/test_http_models.py`.
  - **RED-first behavior test**: Valid synthetic values contain every required
    field; blank/boundary-invalid questions, unknown keys, filters, unsupported
    workflow, absent metadata, and malformed source/corpus values are rejected.
  - **Expected RED failure**: The Pydantic schemas and closed-object settings
    do not exist.
  - **Minimal GREEN implementation**: Typed models and declarative validators;
    no route, provider, or database behavior.
  - **Focused verification commands**: `uv run pytest tests/backend/test_http_models.py`;
    `uv run mypy src/sciscope/api/http_models.py`.
  - **Negative/security requirements**: Reject unsupported filter/provider/model
    fields rather than ignoring them; fixtures contain no real article text.
  - **Acceptance checkpoint**: The public shape is closed, stable, and marked
    mock/test for every modeled outcome.
  - **Proposed small commit boundary**: `feat(api): define versioned question schemas`.

### T004 — Add request IDs and sanitized framework 422 translation

- [ ] T004 [US3] Add `src/sciscope/question_service/ids.py`, sanitized validation mapping, and an isolated test-only ASGI adapter in `tests/backend/`.

  - **Owner**: Person 3.
  - **Goal and scope**: Generate valid opaque IDs; preserve valid supplied IDs;
    generate IDs for omitted/invalid values; translate framework validation into
    the versioned sanitized `422 invalid_request` envelope.
  - **Requirements**: FR-003–FR-004, FR-012; NFR-002/NFR-003; SC-002/SC-004.
  - **Dependencies**: T003 and all approval gates.
  - **Proposed source/test paths**: `src/sciscope/question_service/__init__.py`,
    `src/sciscope/question_service/ids.py`, `src/sciscope/api/app.py`,
    `tests/backend/validation_asgi.py`,
    `tests/backend/test_request_ids_and_validation.py`.
  - **RED-first behavior test**: Test ID generation/validation directly.
    Exercise invalid requests through the test-only ASGI validation adapter;
    invalid IDs return `422` with a newly generated valid ID and no input echo,
    while malformed framework requests use the same envelope. The adapter
    exists only in test support and does not define a successful question
    response or a temporary production error outcome.
  - **Expected RED failure**: No ID policy or reusable sanitized
    `RequestValidationError` mapper exists; test adapter checks fail or receive
    the framework-native validation representation.
  - **Minimal GREEN implementation**: Narrow ID generator/validator and
    reusable sanitized request-validation handler. Keep the production
    question route out of T004; T007 adds final route/service wiring.
  - **Focused verification commands**: `uv run pytest tests/backend/test_request_ids_and_validation.py`;
    `uv run ruff check src/sciscope/api src/sciscope/question_service tests/backend/test_request_ids_and_validation.py`.
  - **Negative/security requirements**: Assert no raw question, invalid ID,
    `exc.errors()`, exception representation, or traceback is public. Confirm
    adapter is test-only and no temporary public error code or success response
    is introduced. Do not add a broad catch-all handler.
  - **Acceptance checkpoint**: ID policy tests and test-only ASGI validation
    tests run independently of retrieval/provider protocols; invalid requests
    return the safe versioned `422` fields.
  - **Proposed small commit boundary**: `feat(api): sanitize validation errors and request IDs`.

## Phase 3 — Fake protocols and output validation

### T005 — Add typed protocols and deterministic independent fakes

- [ ] T005 [US1] Add plain contracts/fakes in `src/sciscope/question_service/` and deterministic tests in `tests/backend/test_fake_dependencies.py`.

  - **Owner**: Person 3.
  - **Goal and scope**: Define typed retrieval/provider protocols and controlled
    outcome/failure values. Add independent fakes owning only synthetic evidence,
    provenance, metadata, states, and configured failure signals.
  - **Requirements**: FR-006–FR-009, FR-011, FR-014–FR-015, FR-017–FR-018;
    NFR-001/NFR-003/NFR-004; SC-001/SC-004/SC-005.
  - **Dependencies**: T004 and all approval gates.
  - **Proposed source/test paths**: `src/sciscope/question_service/contracts.py`,
    `src/sciscope/question_service/fakes.py`,
    `tests/backend/test_fake_dependencies.py`.
  - **RED-first behavior test**: Equivalent configuration/input is deterministic;
    retrieval/provider are independently replaceable; empty retrieval retains
    valid synthetic provenance; fakes signal unavailable/timeout offline.
  - **Expected RED failure**: Protocols, typed outcomes, and fake controls do
    not exist.
  - **Minimal GREEN implementation**: Plain contracts/fakes only; no FastAPI
    models, database, embedding, Gemini, or `_RetrievalCore` import.
  - **Focused verification commands**: `uv run pytest tests/backend/test_fake_dependencies.py`;
    `uv run mypy src/sciscope/question_service/contracts.py src/sciscope/question_service/fakes.py`.
  - **Negative/security requirements**: Fakes fail on attempted network/database/
    provider calls; identifiers/content are synthetic and mock/test flags true.
  - **Acceptance checkpoint**: Fakes provide deterministic provenance-preserving
    results and controlled failures with no live service.
  - **Proposed small commit boundary**: `feat(backend): add deterministic fake dependencies`.

### T006 — Validate evidence, citations, and corpus provenance fail-closed

- [ ] T006 [US1] Add `src/sciscope/question_service/validation.py` and output-validation RED tests in `tests/backend/test_response_validation.py`.

  - **Owner**: Person 3.
  - **Goal and scope**: Validate fake output before it crosses HTTP. Answered
    needs a nonempty answer, at least one claim, and unique response-local
    citations; validation is identity membership only, not scientific support.
  - **Requirements**: FR-008–FR-010, FR-013, FR-018; NFR-002/NFR-003;
    SC-002–SC-004.
  - **Dependencies**: T005 and all approval gates.
  - **Proposed source/test paths**: `src/sciscope/question_service/validation.py`,
    `tests/backend/test_response_validation.py`.
  - **RED-first behavior test**: Accept unique evidence/citations and separate
    corpus identity; reject empty answer/zero claims/no citation/non-member or
    duplicate citation/duplicate chunk ID/blank source or corpus field.
  - **Expected RED failure**: No validator exists, so malformed fake output is
    accepted or lacks a controlled failure signal.
  - **Minimal GREEN implementation**: Deterministic pure validator and typed
    contract-failure signal; no answer-quality assessment.
  - **Focused verification commands**: `uv run pytest tests/backend/test_response_validation.py`;
    `uv run ruff check src/sciscope/question_service/validation.py tests/backend/test_response_validation.py`.
  - **Negative/security requirements**: Invalid output is discarded and source/
    evidence text never appears in a public failure message.
  - **Acceptance checkpoint**: Every malformed output has a predictable
    fail-closed signal for `response_contract_failure`.
  - **Proposed small commit boundary**: `feat(backend): validate fake evidence and citations`.

## Phase 4 — Synchronous successful outcomes

### T007 — Orchestrate the three valid question outcomes

- [ ] T007 [US1] [US2] Add synchronous service/route behavior in `src/sciscope/question_service/service.py` and `src/sciscope/api/routes.py`, tested by `tests/backend/test_question_service.py` and `tests/backend/test_question_api.py`.

  - **Owner**: Person 3.
  - **Goal and scope**: Connect fakes and validation so valid requests produce
    deterministic non-streaming `answered`, `no_results`, or
    `insufficient_evidence` responses.
  - **Requirements**: FR-001, FR-005–FR-011, FR-013–FR-018; NFR-001–NFR-004;
    SC-001/SC-003–SC-005.
  - **Dependencies**: T006 and all approval gates.
  - **Proposed source/test paths**: `src/sciscope/question_service/service.py`,
    `src/sciscope/api/routes.py`, `src/sciscope/api/http_models.py`,
    `tests/backend/test_question_service.py`, `tests/backend/test_question_api.py`.
  - **RED-first behavior test**: In-process requests show required fields,
    mock/test markers, ID/provenance separation; answered has cited claims;
    no-results keeps valid provenance with empty evidence; insufficient preserves
    evidence/provenance but no answer/claims.
  - **Expected RED failure**: No service maps validated fake outcomes to public
    schemas.
  - **Minimal GREEN implementation**: Synchronous service and thin route only;
    no DB offload, prompt, live provider/retrieval, v2 selector, streaming, or filters.
  - **Focused verification commands**: `uv run pytest tests/backend/test_question_service.py tests/backend/test_question_api.py`;
    `uv run mypy src/sciscope/api src/sciscope/question_service`.
  - **Negative/security requirements**: Import/fixture guard prevents database,
    provider, embedding, and external network operations; all state responses
    retain `is_mock`/`is_test_data` true.
  - **Acceptance checkpoint**: All three success states are deterministic,
    offline, distinct, and contract conformant.
  - **Proposed small commit boundary**: `feat(api): serve deterministic question outcomes`.

## Phase 5 — Controlled failures and verification

### T008 — Map controlled failures and complete offline API verification

- [ ] T008 [US3] Complete controlled-failure mapping in `src/sciscope/api/app.py` and verify isolated integration in `tests/backend/test_question_api.py` before evidence recording.

  - **Owner**: Person 3.
  - **Goal and scope**: Map controlled fake unavailable/timeout signals to
    sanitized `503`/`504`, validator failure to `500 response_contract_failure`,
    and unexpected exceptions to sanitized `500 internal_error`. Preserve
    developer/test observability and separate implementation, broader checks,
    human acceptance, evidence updates, and documentation commit gates.
  - **Requirements**: FR-012–FR-018; NFR-001–NFR-004; SC-001–SC-005.
  - **Dependencies**: T007 and all approval gates.
  - **Proposed source/test paths**: `src/sciscope/api/app.py`,
    `src/sciscope/question_service/service.py`,
    `tests/backend/test_question_api.py`, then `EVIDENCE.md` and
    `PROJECT_TODO.md` only after actual automated and human verification.
  - **RED-first behavior test**: Controlled fakes yield exact 500
    `response_contract_failure`, 503, and 504 envelopes with valid IDs and
    metadata. For an unexpected defect, `TestClient(raise_server_exceptions=True)`
    raises it; `TestClient(raise_server_exceptions=False)` receives the
    versioned 500 `internal_error` envelope with no internal detail.
  - **Expected RED failure**: Controlled signals lack public mapping; unexpected
    defects lack the centralized sanitized response while preserving a
    separate developer-observable test path.
  - **Minimal GREEN implementation**: Narrow mapping for declared failures
    plus the centralized sanitized `500 internal_error` boundary; unexpected
    defects remain observable to tests/developers. No broad silent catch, retry,
    or fallback provider.
  - **Focused verification commands**: `uv run pytest tests/backend`;
    `uv run ruff check src/sciscope/api src/sciscope/question_service tests/backend`;
    `uv run ruff format --check src/sciscope/api src/sciscope/question_service tests/backend`;
    `uv run mypy src/sciscope/api src/sciscope/question_service`.
  - **Negative/security requirements**: Public errors exclude raw input, source
    passage, secrets, provider/database details, traceback, and framework data.
    Assert no listener, external network, DB, live provider, protected data, or
    `_RetrievalCore` import.
  - **Acceptance checkpoints**:
    1. **A — RED/GREEN implementation and focused checks**: Each T008 failure
       test is observed red for the missing mapping, then green after the narrow
       boundary is implemented; focused backend checks pass.
    2. **B — Broader automated verification**: Run only the separately approved
       broader repository checks; record PASS/FAIL/BLOCKED/NOT RUN precisely.
    3. **C — Human acceptance**: Present commands/results and acceptance criteria
       to the feature owner; wait for explicit acceptance. Automated success is
       not human acceptance.
    4. **D — Evidence/TODO synchronization**: Only after B passes and C is
       accepted, update `EVIDENCE.md`, this `tasks.md`, and `PROJECT_TODO.md`.
       Mark a task complete only after its own documented acceptance criteria,
       automated checks, and feature human acceptance are fulfilled.
    5. **E — Documentation commit**: After D is reviewed, propose one small
       documentation-only commit for evidence/task/backlog synchronization.
       Commit only when separately authorized.
  - **Proposed small commit boundary**: `feat(api): map sanitized controlled and unexpected errors`; a later documentation-only checkpoint may use `docs: record Feature 011 verification` after D and explicit commit authorization.

## Story completion and final gate

| Story | Completion | Independent proof |
| --- | --- | --- |
| US1 — validated question/evidence | T007 | Offline answered/no-results/insufficient tests with fakes only. |
| US2 — empty vs insufficient evidence | T007 | Separate state assertions, including empty-result provenance. |
| US3 — safe failure behavior | T008 | Sanitized 422/500/503/504 and unexpected-defect observability. |

The approval gates and exact dependency constraints are recorded in plan.md.
T001 authorization is limited as stated above. Task checkboxes remain
incomplete until each task's acceptance criteria, automated checks, and feature
human acceptance are fulfilled. Proposed commit boundaries do not authorize
commits in advance.
