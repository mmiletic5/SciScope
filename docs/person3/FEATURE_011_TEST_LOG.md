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
| `git diff --check` | PASS, exit `0`. |

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

- **Implementation commit:** PENDING
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

- **Implementation commit:** PENDING
- **Changed files:** PENDING
- **RED command, expected failure, actual outcome:** NOT RUN
- **GREEN command and actual outcome:** NOT RUN
- **Additional verification commands/results:** NOT RUN
- **Negative and isolation checks:** NOT RUN
- **Warnings and unresolved issues:** PENDING
- **Human review/acceptance:** PENDING
- **Evidence status:** PENDING

## T006 — Validate evidence, citations, and corpus provenance fail-closed

- **Implementation commit:** PENDING
- **Changed files:** PENDING
- **RED command, expected failure, actual outcome:** NOT RUN
- **GREEN command and actual outcome:** NOT RUN
- **Additional verification commands/results:** NOT RUN
- **Negative and isolation checks:** NOT RUN
- **Warnings and unresolved issues:** PENDING
- **Human review/acceptance:** PENDING
- **Evidence status:** PENDING

## T007 — Orchestrate the three valid question outcomes

- **Implementation commit:** PENDING
- **Changed files:** PENDING
- **RED command, expected failure, actual outcome:** NOT RUN
- **GREEN command and actual outcome:** NOT RUN
- **Additional verification commands/results:** NOT RUN
- **Negative and isolation checks:** NOT RUN
- **Warnings and unresolved issues:** PENDING
- **Human review/acceptance:** PENDING
- **Evidence status:** PENDING

## T008 — Map controlled failures and complete offline API verification

- **Implementation commit:** PENDING
- **Changed files:** PENDING
- **RED command, expected failure, actual outcome:** NOT RUN
- **GREEN command and actual outcome:** NOT RUN
- **Additional verification commands/results:** NOT RUN
- **Negative and isolation checks:** NOT RUN
- **Warnings and unresolved issues:** PENDING
- **Human review/acceptance:** PENDING
- **Evidence status:** PENDING
