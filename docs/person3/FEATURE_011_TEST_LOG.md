# Feature 011 Test and Verification Log

**Owner:** Person 3 (Backend & AI)
**Feature:** Fake backend API
**Purpose:** Chronological working record for actual Feature 011 task evidence.
The final `EVIDENCE.md` update will summarize only verified records from this
document after the required feature-level human acceptance.

## Logging rules

1. Record tests immediately after each task.
2. Preserve RED failures and unexpected failures.
3. Never replace a failed run with a later PASS.
4. Separate actual execution from reported results.
5. Distinguish automated checks from human approval.
6. Record commits only after they exist.
7. Never claim unexecuted tests passed.
8. The final `EVIDENCE.md` will summarize verified records from this document.

## T001 — Establish the approved FastAPI test environment

- **Implementation commit:** `e9bd8e06b419cf76ff634606cc696cde0ed4bf82`
- **Changed files:**
  - `pyproject.toml`
  - `uv.lock`
  - `tests/backend/__init__.py`
- **Approved constraints:**
  - `fastapi>=0.115,<1`
  - `pydantic>=2.7,<3`
  - `httpx>=0.27,<0.29`
- **Resolved versions:** FastAPI `0.165.0`, Pydantic `2.14.4`, HTTPX
  `0.28.1`, and Starlette `1.10.0`.
- **Environment:** Python `3.12.16` (uv-managed); uv `0.13.9`.

### Automated verification

The results in this section are prior Codex execution reports. They were not
rerun while creating this log. Each reported command exited `0`.

| Command or check | Reported result |
| --- | --- |
| `uv lock --check` | PASS |
| `uv run --locked python --version` | PASS; reported Python `3.12.16` |
| `uv run --locked python -c "import fastapi, httpx, pydantic"` | PASS |
| `from fastapi.testclient import TestClient` import verification | PASS; reported module `starlette.testclient` |
| `git diff --check` | PASS |

### User-executed manual verification

The following results were supplied by the user and were not independently
rerun for this record.

| Command | Observed result |
| --- | --- |
| `uv lock --check` | `Resolved 97 packages in 3ms`; PASS |
| `uv run --locked python -c "import fastapi, pydantic, httpx; print('Dependencies OK')"` | `Dependencies OK`; PASS |

### Scope and notes

- T001 is dependency and test-environment preparation. No RED behavior test
  applies to this task.
- No API behavior was implemented or tested.
- No live provider, database, or application network operations were
  performed.
- The original resolver output contained a nonblocking upstream package-version
  normalization warning: `>= '2.7'` was normalized to `>= 2.7`.

### Human review and evidence status

- **Human review/acceptance:** The user reported that the T001 implementation
  passed human review before the implementation commit. Verifier identity,
  date, and detailed acceptance observations were not provided.
- **Evidence status:** Reported automated verification recorded; this log entry
  is not a replacement for the final feature-level human verification or the
  later `EVIDENCE.md` update.

## T002 — Create the injectable app factory

- **Implementation commit:** `dc366ab84d73d16fa50f4b6b239675ad344462ca`
- **Task objective:** Create an offline FastAPI composition-root skeleton that
  accepts and stores opaque injected retrieval and provider sentinels without
  invoking them or registering question behavior.
- **Changed files:**
  - `src/sciscope/api/__init__.py`
  - `src/sciscope/api/app.py`
  - `tests/backend/test_app_factory.py`
  - `docs/person3/FEATURE_011_TEST_LOG.md`

### RED result

- **Command:** `uv run --locked pytest tests/backend/test_app_factory.py`
- **Actual outcome:** Exit `2`; zero tests collected; one collection error;
  zero failed tests.
- **Failure reason:** `ModuleNotFoundError: No module named 'sciscope.api'` at
  `from sciscope.api.app import create_app`.

### GREEN result

- **Command:** `uv run --locked pytest tests/backend/test_app_factory.py`
- **Actual outcome:** PASS, exit `0`; one test collected and one passed.

### Additional verification

| Command | Actual outcome |
| --- | --- |
| `uv run --locked ruff check src/sciscope/api tests/backend/test_app_factory.py` | PASS, exit `0`; all checks passed. |
| `uv run --locked ruff format --check src/sciscope/api tests/backend/test_app_factory.py` | Initial attempt reported one test file would be reformatted. The individual subcommand exit code was not separately captured because the grouped command continued; the final rerun PASSed, exit `0`, with three files already formatted. |
| `uv run --locked mypy src/sciscope/api` | PASS, exit `0`; no issues in two source files. |
| `git diff --check` | Initial and post-review PASS, exit `0`; no whitespace errors. |

### User-executed manual verification

The following results were supplied by the user and were not independently
rerun for this record.

- **Initial command:** `uv run --locked python -c "from sciscope.api import
  create_app; ..."`
  - **Observed result:** FAIL — `ModuleNotFoundError: No module named
    'sciscope'`.
- **Corrected command:** `PYTHONPATH=src uv run --locked python -c "from
  sciscope.api import create_app; ..."`
  - **Observed result:** `App: FastAPI`; routes
    `['/openapi.json', '/docs', '/docs/oauth2-redirect', '/redoc']`; PASS.
  - **Explanation:** Pytest config sets `pythonpath=["src"]`, while direct
    Python invocation requires `PYTHONPATH=src` because the project is not
    installed as a package.
- **Shared backend-test command:** `uv run --locked pytest tests/backend/ -v`
  - **Observed result:** `23 passed in 0.37s`, comprising one T002 app-factory
    test and 22 T003 HTTP-model tests. This is a shared result and does not
    supply a separate T003 acceptance decision.

### Negative and isolation checks

- The injected retrieval and provider sentinels were not called during app
  construction or while entering and leaving an in-process `TestClient`
  context.
- The test observed no imports of `sciscope.database.session`,
  `sciscope.embedding.provider`, or `sciscope.retrieval._core`.
- The application has no `/api/v1/questions` route. The test issued no HTTP
  request and started no listening server.

### Warnings and unresolved issues

- The initial formatter check reported a parenthesization change in
  `tests/backend/test_app_factory.py`; the required layout was applied and the
  final formatter check passed.
- T002 does not define formal dependency protocols, fake implementations,
  schemas, validation, or question endpoint behavior; those remain scoped to
  later approved tasks.

- **Human review/acceptance:** ACCEPTED based on the submitted source files,
  test, and reported verification results. This records the supplied human
  review only; it does not claim independent runtime verification beyond the
  Codex checks recorded above.
- **Evidence status:** Implementation checks and task-level human review
  recorded; final feature-level human acceptance remains pending.

## T003 — Define closed versioned HTTP schemas and input validation

- **Implementation commit:** `be4ea3ccbb3004119914a80e9d78830566505e6f`
- **Task objective:** Define closed versioned Pydantic schemas for the approved
  request, three success states, error envelope, evidence, claims, corpus
  provenance, and mock/test metadata.
- **Changed files:**
  - `src/sciscope/api/http_models.py`
  - `tests/backend/test_http_models.py`
  - `docs/person3/FEATURE_011_TEST_LOG.md`

### RED result

- **Command:** `uv run --locked pytest tests/backend/test_http_models.py`
- **Actual outcome:** Exit `2`; zero tests collected; one collection error;
  zero failed tests.
- **Failure reason:** `ModuleNotFoundError: No module named
  'sciscope.api.http_models'` during test-module import.

### GREEN result

- **Command:** `uv run --locked pytest tests/backend/test_http_models.py`
- **Actual outcome:** PASS, exit `0`; 22 tests collected and 22 passed.

### Additional verification

| Command | Actual outcome |
| --- | --- |
| `uv run --locked ruff check src/sciscope/api/http_models.py tests/backend/test_http_models.py` | Initial attempt FAILed, exit `1`: one import-order issue and one overlong test line. The import-only Ruff fixer and line-wrap correction were applied; final rerun PASSed, exit `0`. |
| `uv run --locked ruff format --check src/sciscope/api/http_models.py tests/backend/test_http_models.py` | First reached attempt FAILed, exit `1`: two test function signatures would be reformatted. The indicated layouts were applied; final rerun PASSed, exit `0`, with two files already formatted. |
| `uv run --locked mypy src/sciscope/api/http_models.py` | PASS, exit `0`; no issues in one source file. |
| `uv run --locked pytest tests/backend/ -v` | PASS, exit `0`; 23 tests passed in 0.58s, including the T002 app-factory test and 22 T003 HTTP-model tests. |
| `uv run --locked pytest tests/backend/ -v` | PASS, exit `0`; 23 tests passed in 0.41s during the manual-evidence documentation review. |
| `git diff --check` | PASS, exit `0`. |

### User-executed manual verification

The following results were supplied by the user and were not independently
rerun for this record.

1. **Valid request**

   **Command:**

   ```sh
   PYTHONPATH=src uv run --locked python -c "from sciscope.api.http_models import QuestionRequest; q = QuestionRequest(workflow='research_question', question='  What is RAG?  '); print('Workflow:', q.workflow); print('Question:', q.question)"
   ```

   **Observed result:** `Workflow: research_question`; `Question: What is RAG?`;
   PASS.

2. **Blank question rejection**

   **Command:**

   ```sh
   PYTHONPATH=src uv run --locked python -c "from pydantic import ValidationError; from sciscope.api.http_models import QuestionRequest; exec(\"try:\n QuestionRequest(workflow='research_question', question='   ')\n print('FAIL: blank question accepted')\nexcept ValidationError:\n print('PASS: blank question rejected')\")"
   ```

   **Observed result:** `PASS: blank question rejected`; PASS.

3. **Unsupported field rejection**

   **Command:**

   ```sh
   PYTHONPATH=src uv run --locked python -c "from pydantic import ValidationError; from sciscope.api.http_models import QuestionRequest; exec(\"try:\n QuestionRequest.model_validate({'workflow':'research_question','question':'What is RAG?','provider':'gemini'})\n print('FAIL: unsupported provider accepted')\nexcept ValidationError:\n print('PASS: unsupported provider rejected')\")"
   ```

   **Observed result:** `PASS: unsupported provider rejected`; PASS.

### Negative and isolation checks

- Request tests reject unsupported workflows; blank, overlength, and non-string
  questions; invalid request IDs; and public `filters`, `provider`, and `model`
  fields.
- Model tests reject missing payloads, blank evidence and corpus fields, empty
  claim citations, false mock metadata, unsupported error codes, and unknown
  response fields.
- All fixtures are synthetic. No route, database, provider, retrieval, or
  network operation is invoked by these schema tests.

### Warnings and unresolved issues

- No blocker remains. The initial Ruff lint and formatter failures above were
  corrected and preserved in this record.
- Request-ID generation and sanitized framework `422` mapping remain T004.
  Cross-record citation membership, duplicate checks, and state-specific
  output validation remain T006.

- **Human review/acceptance:** ACCEPTED based on the submitted source files,
  automated tests, and user-executed manual checks. This is task-level
  acceptance only; it does not establish production readiness or final
  feature-level acceptance.
- **Evidence status:** Implementation checks and task-level human review
  recorded; final feature-level human acceptance remains pending.

## T004 — Add request IDs and sanitized framework 422 translation

- **Implementation commit:** `60f6cac9fed4166c41d39a4b5abd21923bc2c64b`
- **Task objective:** Generate and validate opaque request IDs, then translate
  framework request-validation failures to the approved sanitized `422`
  envelope without adding a production question route.
- **Changed files:**
  - `src/sciscope/api/app.py`
  - `src/sciscope/question_service/__init__.py`
  - `src/sciscope/question_service/ids.py`
  - `tests/backend/validation_asgi.py`
  - `tests/backend/test_request_ids_and_validation.py`
  - `docs/person3/FEATURE_011_TEST_LOG.md`

### RED result

- **Command:** `uv run --locked pytest
  tests/backend/test_request_ids_and_validation.py`
- **Actual outcome:** Exit `2`; zero tests collected; one collection error;
  zero failed tests.
- **Failure reason:** `ModuleNotFoundError: No module named
  'sciscope.question_service'` while importing the planned request-ID module.

### GREEN result

- **Command:** `uv run --locked pytest
  tests/backend/test_request_ids_and_validation.py`
- **Actual outcome:** PASS, exit `0`; five tests collected and five passed.

### Additional verification

| Command | Actual outcome |
| --- | --- |
| Focused T004 suite after the first implementation attempt | FAIL, exit `2`; test collection could not import `tests.backend.validation_asgi` because `tests` is not an importable package. The test-only import was corrected to `backend.validation_asgi`. |
| Focused T004 suite after the adapter-import correction | FAIL, exit `1`; four tests passed and one assertion incorrectly treated the safe deterministic ID `generated-json` as parser-detail leakage. The assertion was narrowed to the malformed body and FastAPI JSON-error code. |
| `uv run --locked pytest tests/backend/test_request_ids_and_validation.py` | Final PASS, exit `0`; five tests passed in 0.42s. |
| `uv run --locked pytest tests/backend/ -v` | Initial PASS for 28 tests in 0.49s; subsequent Ruff command caused the grouped verification to exit `1`. Final PASS, exit `0`; 28 tests passed in 0.44s. |
| `uv run --locked ruff check src/sciscope/api/app.py src/sciscope/question_service tests/backend/validation_asgi.py tests/backend/test_request_ids_and_validation.py` | Initial FAIL, exit `1`; 18 import-order or line-length findings. Ruff fixed three import-order findings; formatter and manual line wraps resolved the remaining findings. Final PASS, exit `0`. |
| `uv run --locked ruff format --check src/sciscope/api/app.py src/sciscope/question_service tests/backend/validation_asgi.py tests/backend/test_request_ids_and_validation.py` | Final PASS, exit `0`; five files already formatted. |
| `uv run --locked mypy src/sciscope/api/app.py src/sciscope/question_service` | PASS, exit `0`; no issues in three source files. |
| `git diff --check` | PASS, exit `0`. |
| Final commit verification: `uv run --locked pytest tests/backend/ -v` | PASS, exit `0`; 28 tests passed in 0.47s. |
| Final commit verification: Ruff check and format check on the T004 source and test paths | PASS, exit `0`; all checks passed and five files already formatted. |
| Final commit verification: `uv run --locked mypy src/sciscope/api/app.py src/sciscope/question_service` and `git diff --check` | PASS, exit `0`; no issues in three source files and no whitespace errors. |

### User-executed manual verification

The following results were supplied by the user and were not independently
rerun for this record. All checks used `PYTHONPATH=src:tests uv run --locked
python`, an in-process FastAPI `TestClient`, and the test-only
`backend.validation_asgi.create_validation_app` adapter.

1. **Valid caller request ID** — A `POST /__test__/validation` request with a
   blank question and `request_id=mateja-test-001` returned HTTP `422`. The
   response request ID was `mateja-test-001`, the error code was
   `invalid_request`, and the mock metadata was
   `{'is_mock': True, 'is_test_data': True}`. **PASS:** the valid caller ID was
   preserved.
2. **Invalid caller request ID** — A `POST /__test__/validation` request with
   `request_id="invalid request ID"` and an injected ID factory returning
   `generated-safe-id` returned HTTP `422` with request ID
   `generated-safe-id`. **PASS:** the invalid caller ID was safely replaced.
3. **Malformed JSON** — A `POST /__test__/validation` request with body
   `{invalid-json` and an injected ID factory returning `generated-json`
   returned HTTP `422`, error code `invalid_request`, and request ID
   `generated-json`. **PASS:** malformed JSON was safely handled.

The user confirmed that these assertions held: HTTP `422` was returned; the
approved error code was used; caller IDs were preserved or safely replaced;
invalid IDs and malformed JSON text were not reflected; and no FastAPI
`detail` field was exposed.

### Negative and isolation checks

- A valid caller request ID is preserved in the `422` envelope; missing or
  malformed IDs receive generated valid replacement IDs, and an invalid ID is
  not echoed.
- Invalid JSON, blank question data, unsupported workflow, and unsupported
  fields are returned only as the approved four-field versioned envelope with
  `is_mock` and `is_test_data` fixed to `true`.
- Tests assert that raw question text, filters, unsupported workflow values,
  malformed JSON, FastAPI JSON-error code, and `detail` are absent from the
  public response.
- The temporary validation route exists only in `tests/backend/validation_asgi.py`;
  the production app still has no `/api/v1/questions` route. No external
  provider, database, retrieval, or listening server is started.

### Warnings and unresolved issues

- The prior focused-test and Ruff failures above were corrected and retained
  in this record. No verification blocker remains.
- T004 adds only the validation boundary. Fake dependencies belong to T005;
  output/citation validation belongs to T006; and the production question route
  and success behavior belong to T007.

- **Human review/acceptance:** ACCEPTED at task level based on the submitted
  implementation, automated verification, and three successful user-executed
  manual checks. Final Feature 011 acceptance remains PENDING.
- **Evidence status:** Implementation checks and task-level human acceptance
  recorded; final Feature 011 acceptance pending.

## T005 — Add typed protocols and deterministic independent fakes

- **Implementation commit:** `706c2681faac006f792e5467eea8fcf2ec55e155`
- **Task objective:** Define plain immutable retrieval/provider contracts and
  deterministic, independently injectable fake dependencies with synthetic
  evidence, provenance, metadata, success states, and controlled failures.
- **Changed files:**
  - `src/sciscope/question_service/contracts.py`
  - `src/sciscope/question_service/fakes.py`
  - `tests/backend/test_fake_dependencies.py`
  - `docs/person3/FEATURE_011_TEST_LOG.md`

### RED result

- **Command:** `uv run --locked pytest tests/backend/test_fake_dependencies.py`
- **Initial environment outcome:** BLOCKED before collection because the
  sandboxed `uv` cache could not create a temporary file under
  `/home/maki/.cache/uv`; the same command was rerun with access to the
  existing cache.
- **Actual outcome:** Exit `2`; zero tests collected; one collection error.
- **Failure reason:** `ModuleNotFoundError: No module named
  'sciscope.question_service.contracts'` during test-module import. This was
  the expected missing-contract failure.

### GREEN result

- **Command:** `uv run --locked pytest tests/backend/test_fake_dependencies.py`
- **Actual outcome:** PASS, exit `0`; eight tests collected and eight passed.

### Additional verification

| Command | Actual outcome |
| --- | --- |
| `uv run --locked pytest tests/backend/ -v` | PASS, exit `0`; 36 tests passed in 0.51s. |
| `uv run --locked mypy src/sciscope/question_service/contracts.py src/sciscope/question_service/fakes.py` | PASS, exit `0`; no issues in two source files. |
| `uv run --locked ruff check src/sciscope/question_service/contracts.py src/sciscope/question_service/fakes.py tests/backend/test_fake_dependencies.py` | Initial FAIL, exit `1`; 12 findings: a missing initializer docstring, unsorted imports, and line-length violations. After manual corrections, it FAILed again with one remaining import-order finding. `uv run --locked ruff check --fix src/sciscope/question_service/fakes.py` applied that import-only correction; final rerun PASSed, exit `0`. |
| `uv run --locked ruff format --check src/sciscope/question_service/contracts.py src/sciscope/question_service/fakes.py tests/backend/test_fake_dependencies.py` | Initial FAIL, exit `1`; `fakes.py` and `test_fake_dependencies.py` would be reformatted. The required layouts were applied; final rerun PASSed, exit `0`, with three files already formatted. |
| `git diff --check` | PASS, exit `0`. |
| Post-review `uv run --locked pytest tests/backend/ -v` | PASS, exit `0`; 36 tests passed in 0.54s. |
| Post-review `uv run --locked mypy src/sciscope/question_service/contracts.py src/sciscope/question_service/fakes.py` | PASS, exit `0`; no issues in two source files. |
| Post-review Ruff check and format check on T005 source and test paths | PASS, exit `0`; all checks passed and three files were already formatted. |

### User-executed manual verification

The following results were supplied by the user and were not independently
rerun for this record. All checks used `PYTHONPATH=src uv run --locked python`.

1. **Deterministic synthetic retrieval** — Two `FakeRetrieval` calls with an
   equivalent question and request ID returned equal results. The user
   confirmed `first == second`, `is_mock == True`, `is_test_data == True`, and
   one evidence item. Observed chunk ID: `synthetic-chunk-001`; paper:
   `Synthetic Fixture Paper`; DOI: `10.0000/synthetic.001`; passage:
   `Synthetic fixture passage for deterministic backend testing.`
   **PASS:** deterministic synthetic retrieval.
2. **Fake provider and empty retrieval** — The provider received synthetic
   retrieval evidence and returned an answered outcome. The user confirmed
   `status == answered`, the cited chunk ID matched supplied evidence, empty
   retrieval evidence was `()`, a corpus delivery digest was present, and mock
   metadata was true. Observed answer: `Synthetic fixture answer for
   deterministic backend testing.`; citation:
   `('synthetic-chunk-001',)`; empty retrieval evidence: `()`.
   **PASS:** citation identity and empty retrieval.
3. **Controlled timeout** — `FakeRetrieval(mode="timeout")` raised a
   `DependencyFailure` with code `DEPENDENCY_TIMEOUT`. Observed failure code:
   `dependency_timeout`. **PASS:** controlled offline timeout.

### Negative and isolation checks

- Tests assert separate runtime-checkable retrieval and provider protocols,
  independent fake substitution, deterministic equal outputs, structured
  mock/test metadata, synthetic evidence source fields, and corpus provenance
  for both evidence and empty retrieval outcomes.
- Tests assert answered fake output cites the supplied synthetic evidence ID,
  and parameterize controlled retrieval/provider unavailable and timeout
  signals.
- Fake modules import only Python standard-library modules and
  `sciscope.question_service.contracts`; tests inspect their sources for no
  FastAPI, Pydantic, or `sciscope.retrieval` coupling. No database, network,
  embedding, Gemini, provider SDK, or private retrieval-core operation occurs.

### Warnings and unresolved issues

- The initial cache-permission block and Ruff/format failures above were
  corrected and retained in this record.
- T005 defines plain fake contracts only. Output validation, cross-record
  citation checks, service orchestration, HTTP response mapping, and the
  production question route remain scoped to T006–T008.

- **Human review/acceptance:** ACCEPTED based on submitted implementation,
  automated tests, and successful user-executed manual checks. Final Feature
  011 acceptance remains PENDING.
- **Evidence status:** Automated checks recorded; feature-level human
  acceptance and final `EVIDENCE.md` update remain pending.

## T006 — Validate evidence, citations, and corpus provenance fail-closed

- **Implementation commit:** `590d48a478fb9e0086a7ac1933403e25eb8867e5`
- **Task objective:** Validate synthetic retrieval/provider output before it
  crosses the HTTP boundary and produce a deterministic fail-closed signal for
  malformed evidence, citation, provenance, metadata, or state values.
- **Changed files:**
  - `src/sciscope/question_service/validation.py`
  - `tests/backend/test_response_validation.py`
  - `docs/person3/FEATURE_011_TEST_LOG.md`

### RED result

- **Command:** `uv run --locked pytest tests/backend/test_response_validation.py`
- **Actual outcome:** Exit `2`; zero tests collected; one collection error.
- **Failure reason:** `ModuleNotFoundError: No module named
  'sciscope.question_service.validation'` during test-module import. This was
  the expected missing-validator failure.

### GREEN result

- **Command:** `uv run --locked pytest tests/backend/test_response_validation.py`
- **Initial outcome:** PASS, exit `0`; 16 tests collected and 16 passed.
- **Final outcome:** PASS, exit `0`; 17 tests collected and 17 passed after
  adding the symmetric false-`is_test_data` metadata case.

### Contract review

- **Claim-ID uniqueness decision:** No approved Feature 011 requirement makes
  `claim_id` unique across claims. The public HTTP `Claim` model requires only
  a nonempty `claim_id` (`src/sciscope/api/http_models.py`), while
  `spec.md` FR-008 requires unique evidence `chunk_id` values and FR-010
  requires unique citation IDs within one claim. The T006 task likewise names
  unique evidence/citations and duplicate citation/chunk-ID rejection.
- **Result:** No claim-ID uniqueness test or validation change was added; doing
  so would expand the approved T006 contract.

### Additional verification

| Command | Actual outcome |
| --- | --- |
| `uv run --locked pytest tests/backend/ -v` | Initial PASS, exit `0`; 52 tests passed in 0.67s. Final PASS, exit `0`; 53 tests passed in 0.53s. |
| `uv run --locked mypy src/sciscope/question_service/validation.py` | PASS, exit `0`; no issues in one source file. |
| `uv run --locked ruff check src/sciscope/question_service/validation.py tests/backend/test_response_validation.py` | Initial FAIL, exit `1`; eight line-length findings. After correction and formatting, it FAILed once more with one test-docstring line-length finding. Final rerun PASSed, exit `0`. |
| `uv run --locked ruff format --check src/sciscope/question_service/validation.py tests/backend/test_response_validation.py` | Initial FAIL, exit `1`; `test_response_validation.py` would be reformatted. `uv run --locked ruff format tests/backend/test_response_validation.py` reformatted one file; final rerun PASSed, exit `0`, with two files already formatted. |
| `git diff --check` | PASS, exit `0`; no whitespace errors. |
| Final-review `uv run --locked pytest tests/backend/test_response_validation.py -v` | PASS, exit `0`; 17 tests passed in 0.05s. |
| Final-review `uv run --locked pytest tests/backend/ -v` | PASS, exit `0`; 53 tests passed in 0.52s. |
| Final-review mypy, Ruff check, and Ruff format check on T006 source/test paths | PASS, exit `0`; no type issues, all lint checks passed, and two files were already formatted. |

### User-executed manual verification

The following results were supplied by the user and were not independently
rerun for this record. All checks used `PYTHONPATH=src uv run --locked python`.

1. **Valid evidence and citation** — The user retrieved deterministic
   synthetic evidence and generated a fake provider answer.
   `validate_answered_outcome()` completed without raising an exception.
   Observed evidence ID: `synthetic-chunk-001`; cited ID:
   `('synthetic-chunk-001',)`. **PASS:** valid evidence and citation accepted.
2. **Unknown citation rejection** — The user replaced the original provider
   claim with a claim referencing `nonexistent-chunk`.
   `validate_answered_outcome()` raised the expected
   `ResponseContractFailure`. Observed failure code:
   `response_contract_failure`. **PASS:** nonexistent citation rejected.
3. **State-specific validation** — The user verified that empty retrieval was
   accepted by `validate_no_results_outcome()`, nonempty retrieval with a
   provider insufficient-evidence outcome was accepted by
   `validate_insufficient_evidence_outcome()`, and an answered provider
   outcome with empty retrieval was rejected by
   `validate_answered_outcome()`. Observed results: **PASS:** empty retrieval
   accepted as no_results; **PASS:** insufficient evidence accepted;
   **PASS:** answer without evidence rejected.

### Negative and isolation checks

- Valid answered output preserves the original fixture evidence, citation ID,
  and corpus value; validation returns no substituted or invented data.
- Tests reject missing, unknown, and duplicate citation IDs; duplicate evidence
  IDs; blank evidence identity/source fields; blank corpus provenance fields;
  and false mock metadata.
- Tests reject answered output with a blank or absent answer or zero claims,
  no-results output with evidence, and insufficient-evidence output that has
  an answer or claims. All invalid combinations raise only
  `ResponseContractFailure` with code `response_contract_failure`.
- The pure validator imports only `question_service.contracts`; it performs no
  HTTP, network, database, embedding, provider, Gemini, or private retrieval
  operation.

### Warnings and unresolved issues

- Initial Ruff and format failures above were corrected and retained in this
  record.
- T006 validates response-local identity and shape only. It does not assess
  citation entailment or scientific answer quality, and it does not map the
  controlled failure to HTTP; those concerns remain in later approved tasks.

- **Human review/acceptance:** ACCEPTED at task level based on the reviewed
  implementation, approved contract requirements, 17 passing focused tests,
  53 passing backend tests, and three successful user-executed manual
  verification scripts. Final Feature 011 acceptance remains PENDING.
- **Evidence status:** Automated checks recorded; feature-level human
  acceptance and final `EVIDENCE.md` update remain pending.

## T007 — Orchestrate the three valid question outcomes

- **Implementation commit:** `33563e25155abcfe2e524d50f2591d99c7dd85a9`
- **Task objective:** Orchestrate the fake retrieval and provider dependencies
  into the approved answered, no-results, and insufficient-evidence outcomes,
  validate each result, and expose the versioned success endpoint.
- **Changed files:**
  - `src/sciscope/question_service/service.py`
  - `src/sciscope/api/routes.py`
  - `src/sciscope/api/app.py`
  - `tests/backend/test_question_service.py`
  - `tests/backend/test_question_api.py`
  - `tests/backend/test_app_factory.py`
  - `docs/person3/FEATURE_011_TEST_LOG.md`

### RED result

- **Command:** `uv run --locked pytest tests/backend/test_question_service.py tests/backend/test_question_api.py`
- **Actual outcome:** Exit `2`; four tests collected and one collection error.
- **Failure reason:** `ModuleNotFoundError: No module named
  'sciscope.question_service.service'` while importing the service tests. This
  was the expected missing-orchestration failure.

### GREEN result

- **Command:** `uv run --locked pytest tests/backend/test_question_service.py tests/backend/test_question_api.py`
- **Intermediate outcome:** Exit `1`; six passed and two failed because the
  no-results outcome lacked `claims` and the insufficient-evidence outcome
  lacked `answer`. The outcome contracts were completed with the approved
  empty/null state values.
- **Final outcome:** PASS, exit `0`; eight tests passed in 0.51s.

### Additional verification

| Command | Actual outcome |
| --- | --- |
| `uv run --locked pytest tests/backend/ -v` | Initial FAIL, exit `1`; 60 passed and one failed because the former app-factory test asserted that the now-approved question route was absent. The assertion was updated to verify route registration while retaining the no-initialization isolation check. Final PASS, exit `0`; 61 tests passed in 0.69s. |
| `uv run --locked mypy src/sciscope/api src/sciscope/question_service` | Initial FAIL, exit `1`; 22 route type errors from untyped shared HTTP-model mapping and string-name casts. Explicit typed mapping helpers corrected the errors. Final PASS, exit `0`; no issues in 10 source files. |
| `uv run --locked ruff check src/sciscope/api/app.py src/sciscope/api/routes.py src/sciscope/question_service/service.py tests/backend/test_app_factory.py tests/backend/test_question_service.py tests/backend/test_question_api.py` | Initial FAIL, exit `1`; 14 findings, including imports and line lengths. A subsequent run found one remaining import-order issue, corrected with `ruff check --fix` on `routes.py`; the final test-name line was then shortened. Final PASS, exit `0`; all checks passed. |
| `uv run --locked ruff format --check src/sciscope/api/app.py src/sciscope/api/routes.py src/sciscope/question_service/service.py tests/backend/test_app_factory.py tests/backend/test_question_service.py tests/backend/test_question_api.py` | Initial FAIL, exit `1`; two test files required formatting. `uv run --locked ruff format tests/backend/test_question_service.py tests/backend/test_question_api.py` reformatted one file. Final PASS, exit `0`; six files already formatted. |
| `git diff --check` | PASS, exit `0`; no whitespace errors after this log update. |

### Outcome and isolation coverage

- The service accepts injected `RetrievalService` and `AnswerProvider`
  protocols. The route obtains those dependencies from the app factory state;
  no hidden dependency globals are used.
- Answered output retains deterministic synthetic evidence, response-local
  citation identity, corpus provenance, and mock/test metadata. The output is
  validated before HTTP-model conversion.
- Empty retrieval produces `no_results`, retains valid synthetic provenance,
  contains no answer, claims, or evidence, and skips provider invocation.
- Nonempty retrieval plus a provider decline produces
  `insufficient_evidence`, preserving evidence and provenance with no
  fabricated answer or claims.
- Tests cover supplied and generated request IDs, closed success schemas, and
  the fail-closed validator rejecting an invalid provider answer before output.
  They use only fakes; no database, network, embedding, Gemini, external
  provider, or Person 2 retrieval implementation is accessed.

### User-executed manual verification

The following checks were performed directly by the user and were not
independently rerun for this record. All used
`PYTHONPATH=src uv run --locked python`, FastAPI `TestClient`, and explicitly
injected `FakeRetrieval` and `FakeAnswerProvider` dependencies.

1. **Answered HTTP outcome** — `POST /api/v1/questions` with workflow
   `research_question`, request ID `manual-t007-001`, and a valid research
   question returned HTTP `200` with status `answered`. Observed answer:
   `Synthetic fixture answer for deterministic backend testing.`; evidence:
   `synthetic-chunk-001`; citations: `['synthetic-chunk-001']`.
   **PASS:** answered HTTP outcome. The user also confirmed the request ID was
   preserved, the citation matched the evidence chunk ID, and `is_mock` and
   `is_test_data` were true.
2. **No-results HTTP outcome** — `POST /api/v1/questions` with injected
   `FakeRetrieval(mode="empty")` and `FakeAnswerProvider()` returned HTTP `200`
   with status `no_results` and generated request ID `generated-t007-002`.
   Observed evidence: `[]`; corpus delivery digest:
   `synthetic-delivery-digest-v1`; source contract version:
   `synthetic-source-contract-v1`; corpus version:
   `synthetic-corpus-v1`. **PASS:** no-results HTTP outcome. The user also
   confirmed `answer is None`, claims and evidence were empty, and the corpus
   delivery digest was present.
3. **Insufficient-evidence HTTP outcome** — `POST /api/v1/questions` with
   `FakeRetrieval()` and
   `FakeAnswerProvider(mode="insufficient_evidence")` returned HTTP `200` with
   status `insufficient_evidence`, `answer: None`, `claims: []`, and evidence
   count `1`. **PASS:** insufficient-evidence HTTP outcome. The user also
   confirmed the answer and claims were empty, retrieved evidence remained
   present, and mock metadata was true.

### Final contract review and verification

- **Contract review:** PASS. The approved T007 contract in `spec.md`,
  `plan.md`, and `tasks.md` is met: the app exposes only the approved
  `POST /api/v1/questions` success behavior; its closed response union permits
  only `answered`, `no_results`, and `insufficient_evidence`. The app factory
  retains explicit dependency injection, preserves supplied valid request IDs,
  generates omitted IDs through its injected factory, and retains the T004
  sanitized `422` handler. The service skips provider invocation for empty
  retrieval, validates all success outcomes before HTTP conversion, and
  preserves synthetic corpus provenance and mock/test metadata. No external
  provider, embedding, database, network, or Person 2 retrieval dependency is
  introduced. No additional approved requirement gap was found.
- `uv run --locked pytest tests/backend/test_question_service.py tests/backend/test_question_api.py -v`: PASS, exit `0`; eight tests passed in 0.57s.
- `uv run --locked pytest tests/backend/ -v`: PASS, exit `0`; 61 tests passed in 0.89s.
- `uv run --locked mypy src/sciscope/api src/sciscope/question_service`: PASS, exit `0`; no issues in 10 source files.
- `uv run --locked ruff check src/sciscope/api/app.py src/sciscope/api/routes.py src/sciscope/question_service/service.py tests/backend/test_app_factory.py tests/backend/test_question_service.py tests/backend/test_question_api.py`: PASS, exit `0`; all checks passed.
- `uv run --locked ruff format --check src/sciscope/api/app.py src/sciscope/api/routes.py src/sciscope/question_service/service.py tests/backend/test_app_factory.py tests/backend/test_question_service.py tests/backend/test_question_api.py`: PASS, exit `0`; six files already formatted.
- **Additional failures or corrections:** None during this final review.

### Warnings and unresolved issues

- The RED failure and all intermediate test, type, lint, and formatting
  failures above were corrected and retained in this record.
- T007 handles valid success outcomes only. T008 remains responsible for
  mapping controlled dependency and validation failures to HTTP errors.
- **Human review/acceptance:** ACCEPTED at task level based on reviewed
  implementation, approved contract requirements, 8 passing focused tests, 61
  passing backend tests, and three successful user-executed manual HTTP
  verification scripts. Final Feature 011 acceptance remains PENDING.
- **Evidence status:** Automated checks, task-level human acceptance, and the
  local implementation commit are recorded; final Feature 011 acceptance and
  final `EVIDENCE.md` update remain pending.

## T008 — Map controlled failures and complete offline API verification

- **Implementation commit:** PENDING
- **Task objective:** Map declared fake dependency and response-contract
  failures to the approved sanitized HTTP envelopes, add the required
  unexpected-exception boundary, and verify the API entirely offline.
- **Changed files:**
  - `src/sciscope/api/app.py`
  - `src/sciscope/api/routes.py`
  - `tests/backend/test_question_api.py`
  - `docs/person3/FEATURE_011_TEST_LOG.md`

### Approved failure mapping

| Origin | HTTP status | Public code | Retryable |
| --- | --- | --- | --- |
| Fake retrieval unavailable | `503` | `retrieval_unavailable` | `true` |
| Fake provider unavailable | `503` | `provider_unavailable` | `true` |
| Fake retrieval or provider timeout | `504` | `dependency_timeout` | `true` |
| Invalid retrieval/provider output | `500` | `response_contract_failure` | `false` |
| Unexpected internal exception | `500` | `internal_error` | `false` |

All responses use the closed `ErrorResponse` envelope with `api_version`, a
valid request ID, `error`, and mock/test metadata. A valid caller ID is
preserved after request parsing; an omitted ID uses the injected factory. The
approved documents require sanitized messages but prescribe no literal message
for these categories, so the tests assert nonempty static messages and absence
of raw input, exception, provider, and invalid-output detail.

### RED result

- **Command:** `uv run --locked pytest tests/backend/test_question_api.py -v`
- **Actual outcome:** Exit `1`; 10 tests collected, four existing success tests
  passed, and six T008 tests failed. Controlled fake failures returned the
  framework's un-mapped `500` response, the initially intended invalid-output
  fixture returned `200`, and an unexpected defect returned plain `Internal
  Server Error` rather than the required JSON envelope.
- **Intermediate test correction:** The first invalid-output fixture used a
  nonempty answer, which is valid under the approved validator and therefore
  returned `200`. It was replaced before GREEN with an invalid private citation
  identity; this exercised the approved contract-failure path.

### GREEN result

- **Command:** `uv run --locked pytest tests/backend/test_question_api.py -v`
- **Actual outcome:** PASS, exit `0`; 10 tests passed in 0.79s.
- **Behavior:** The app installs narrow handlers for `DependencyFailure` and
  `ResponseContractFailure`, plus the approved centralized unexpected-error
  boundary. The route stores its resolved request ID on request state before
  invoking the service, enabling every post-validation failure envelope to
  preserve or generate the correct ID. With
  `raise_server_exceptions=True`, unexpected defects still raise to the test;
  with it disabled, the client receives the sanitized `500 internal_error`
  envelope.

### Additional verification

| Command | Actual outcome |
| --- | --- |
| `uv run --locked pytest tests/backend/ -v` | PASS, exit `0`; 67 tests passed in 0.92s. |
| `uv run --locked mypy src/sciscope/api src/sciscope/question_service` | Initial FAIL, exit `1`; one app request-state return type error. A string type guard corrected it. Final PASS, exit `0`; no issues in 10 source files. |
| `uv run --locked ruff check src/sciscope/api/app.py src/sciscope/api/routes.py tests/backend/test_question_api.py` | Initial FAIL, exit `1`; unsorted imports, three line-length findings, and one `getattr` finding. After the type-safe response helper and layout corrections, a final import-order finding and long test name remained. `uv run --locked ruff check --fix src/sciscope/api/app.py` applied the import-only correction; final PASS, exit `0`; all checks passed. |
| `uv run --locked ruff format --check src/sciscope/api/app.py src/sciscope/api/routes.py tests/backend/test_question_api.py` | Initial FAIL, exit `1`; `test_question_api.py` would be reformatted. `uv run --locked ruff format src/sciscope/api/app.py src/sciscope/api/routes.py tests/backend/test_question_api.py` reformatted one file. Final PASS, exit `0`; three files already formatted. |
| `git diff --check` | PASS, exit `0`; no whitespace errors. |

### Failure mapping and isolation coverage

- Parameterized in-process HTTP tests cover retrieval unavailable and timeout,
  provider unavailable and timeout, valid caller-ID preservation, generated-ID
  fallback, the exact approved status/code/retryability mappings, closed
  envelope fields, and fixed mock/test metadata.
- Invalid provider output with a private citation is discarded and maps to
  `response_contract_failure`; private question and invalid-output values do
  not appear in the public response.
- The unexpected-defect test confirms both required modes: the default test
  client raises the original `RuntimeError`, while
  `raise_server_exceptions=False` returns only the sanitized `internal_error`
  envelope. No exception text or private question appears publicly.
- Tests inject only deterministic fakes and run through FastAPI's in-process
  `TestClient`; no listener, network, database, pgvector, embedding, Gemini,
  provider SDK, or Person 2 retrieval implementation is accessed.

### User-executed manual verification

The following checks were run directly by the user with FastAPI `TestClient`
and explicitly injected fake dependencies. They were not independently rerun
for this record.

1. **Controlled dependency failures** — The user exercised retrieval
   unavailable (HTTP `503`, `retrieval_unavailable`), retrieval timeout (HTTP
   `504`, `dependency_timeout`), provider unavailable (HTTP `503`,
   `provider_unavailable`), and provider timeout (HTTP `504`,
   `dependency_timeout`). **PASS:** all controlled dependency failures. The
   user also confirmed `retryable` was `True`, caller request ID
   `manual-t008-001` was preserved, `is_mock` and `is_test_data` were true,
   private question text was absent, and the error response contained only the
   four approved top-level fields.
2. **Invalid response contract** — An injected fake provider returned a claim
   referencing a nonexistent private chunk ID. Observed HTTP `500`, code
   `response_contract_failure`, `retryable: False`, and request ID
   `manual-t008-002`. **PASS:** invalid response contract rejected safely. The
   user also confirmed the generated request ID was preserved and neither the
   invalid chunk ID nor private question text was exposed.
3. **Unexpected internal error** — An injected retrieval dependency raised a
   `RuntimeError` with private exception text. Observed HTTP `500`, code
   `internal_error`, and `retryable: False`. **PASS:** unexpected error
   sanitized. **PASS:** unexpected exception remains observable. The user also
   confirmed generated request ID `manual-t008-003`, absence of the private
   exception and question text, and propagation of the original `RuntimeError`
   with the default `TestClient` configuration.

### Final contract review and verification

- **Contract review:** PASS. `DependencyFailure` maps retrieval/provider
  availability and timeout codes to the approved `503`/`504` status,
  public-code, and retryability combinations. `ResponseContractFailure` maps
  fail-closed output to non-retryable `500 response_contract_failure`; the
  centralized `Exception` boundary maps unexpected defects to non-retryable
  `500 internal_error` while TestClient's default mode preserves developer
  observability. Each path uses the closed `ErrorResponse` envelope, fixed
  mock/test metadata, a preserved or generated valid request ID, and static
  sanitized messages. Existing T004 tests retain sanitized `422` coverage and
  T007 tests retain all three valid success outcomes. No external integration
  or Person 2 retrieval code is used. No approved requirement gap was found.
- `uv run --locked pytest tests/backend/test_question_api.py -v`: PASS, exit
  `0`; 10 tests passed in 0.66s.
- `uv run --locked pytest tests/backend/ -v`: PASS, exit `0`; 67 tests passed
  in 0.85s.
- `uv run --locked mypy src/sciscope/api src/sciscope/question_service`: PASS,
  exit `0`; no issues in 10 source files.
- `uv run --locked ruff check src/sciscope/api/app.py src/sciscope/api/routes.py tests/backend/test_question_api.py`: PASS, exit `0`; all checks passed.
- `uv run --locked ruff format --check src/sciscope/api/app.py src/sciscope/api/routes.py tests/backend/test_question_api.py`: PASS, exit `0`; three files already formatted.
- **Additional failures or corrections:** None during this final review.

### Warnings and unresolved issues

- The RED failures, invalid-fixture correction, and mypy/Ruff/format failures
  above were corrected and retained in this record.
- The approved contract specifies sanitization requirements but not literal
  controlled-failure message text. The implementation uses fixed generic
  messages and tests enforce the required absence of internal details. No
  additional public code or mapping was introduced.
- **Human review/acceptance:** ACCEPTED at task level based on the reviewed
  implementation, approved contract requirements, 10 passing focused HTTP
  tests, 67 passing backend tests, and three successful user-executed manual
  verification scripts. Final Feature 011 acceptance remains PENDING.
- **Evidence status:** Automated checks recorded; task-level human review and
  implementation commit remain pending. Final Feature 011 acceptance and final
  `EVIDENCE.md` update remain pending.
