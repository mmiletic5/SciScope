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

- **Implementation commit:** PENDING
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

- **Implementation commit:** PENDING
- **Changed files:** PENDING
- **RED command, expected failure, actual outcome:** NOT RUN
- **GREEN command and actual outcome:** NOT RUN
- **Additional verification commands/results:** NOT RUN
- **Negative and isolation checks:** NOT RUN
- **Warnings and unresolved issues:** PENDING
- **Human review/acceptance:** PENDING
- **Evidence status:** PENDING

## T004 — Add request IDs and sanitized framework 422 translation

- **Implementation commit:** PENDING
- **Changed files:** PENDING
- **RED command, expected failure, actual outcome:** NOT RUN
- **GREEN command and actual outcome:** NOT RUN
- **Additional verification commands/results:** NOT RUN
- **Negative and isolation checks:** NOT RUN
- **Warnings and unresolved issues:** PENDING
- **Human review/acceptance:** PENDING
- **Evidence status:** PENDING

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
