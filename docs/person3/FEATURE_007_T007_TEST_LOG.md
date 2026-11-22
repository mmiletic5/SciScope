# Feature 007 T007 Test and Verification Log

**Owner:** Person 3 (Backend & AI)
**Feature:** Public retrieval facade
**Purpose:** Chronological working record for actual T007 evidence. The final
`EVIDENCE.md` update will summarize only verified records after explicit
feature-level human acceptance.

## Logging rules

1. Record each RED, GREEN, static, regression, and manual check immediately.
2. Preserve failures and corrections; never replace a failed result.
3. Distinguish Codex-run checks from user-run verification and Person 2 review.
4. Record commit hashes only after the commits exist.
5. Do not mark a task complete from automated results alone.

## T007-B-01 — Public contract RED tests

- **Date:** 2026-11-22
- **Git baseline:** `007-public-retrieval-facade` at
  `1453cc723ca3bf642ff71d9429c3609de23472e3`; clean working tree and index.
- **Approved scope:** Offline RED tests for public, versioned retrieval DTOs,
  typed sanitized errors, root exports, provenance preservation, validation,
  immutability, and import isolation. No provider, database, private-core, or
  HTTP behavior is in scope.
- **Files introduced:**
  - `docs/person3/FEATURE_007_T007_TEST_LOG.md`
  - `tests/retrieval/test_public_contracts.py`
- **Workflow:** Write and run the focused RED tests before adding public source
  modules. GREEN, static checks, regressions, and manual verification have not
  started.
- **Human verification policy:** After automated GREEN checks, stop before a
  commit. Provide exact verification commands and expected outcomes for the
  user to run independently. Record the observed results, date, and explicit
  ACCEPTED or REJECTED decision before committing.
- **Required review:** Person 2 must review retrieval-owned source and contract
  changes before any T007-B commit. Person 1 provenance/source-mapping review
  remains required for later public-result mapping.

### RED result

- **Initial command:** `uv run --locked pytest
  tests/retrieval/test_public_contracts.py`
  - **Actual outcome:** BLOCKED before collection; exit `2`.
  - **Observed reason:** uv could not create a temporary file under
    `/home/maki/.cache/uv` because the sandbox filesystem was read-only.
  - **Correction:** Reran the identical command with permission to write uv's
    local cache. This environmental attempt is retained and is not the RED
    result.
- **RED command:** `uv run --locked pytest
  tests/retrieval/test_public_contracts.py`
  - **Actual outcome:** FAIL; exit `1`; 27 tests collected, 27 failed, and 0
    passed in 0.31 seconds.
  - **Representative failure:** `_public_api()` imported
    `sciscope.retrieval` and reported all required public exports missing:
    `Author`, `CorpusIdentity`, `EmbeddingConfig`, `PaperMetadata`,
    `RankingOptions`, `RetrievalErrorCode`, `RetrievalException`,
    `RetrievalFilters`, `RetrievalMetadata`, `RetrievalRequest`,
    `RetrievalResponse`, `RetrievalResult`, and `RetrievalScore`.
  - **Why this is meaningful:** The test module collected successfully and
    each case failed at the intended public-boundary assertion. No database,
    provider, network, Docker, or private-core behavior was invoked.
- **GREEN:** Not started.
- **Independent human verification:** Pending.
- **Person 2 review:** Pending.
- **T007-B acceptance:** Pending.

- **Documentation correction:** The first untracked-file whitespace check found
  one trailing blank line in this log. It was removed; no test or source
  behavior changed.

### Next intended GREEN boundary

Add only the approved public DTO/error modules and root exports, preserving
the documented v1/v2 fields and validation. Do not start the facade/service
(T007-C), cross-service conformance (T007-D), database verification, or a
commit in this increment.
## T007-B-02 — RED test quality corrections

- **Date:** 2026-11-22
- **Scope:** Correct only two public-contract test assertions before GREEN.
  The T007-B-01 RED evidence above remains unchanged.
- **Changes:**
  - Added `NormalizedType` and `RetrievalMode` to the required root export
    assertions. The retrieval.v1 public Python API explicitly declares both;
    retrieval.v2 preserves the same DTO shape.
  - Changed the invalid-request helper to accept an expected request ID. The
    invalid-request-ID cases now require `None`, because the documented error
    envelope makes `request_id` null when it is missing or invalid. Other
    invalid request tests retain the valid default request ID assertion.
- **RED command:** `uv run --locked pytest
  tests/retrieval/test_public_contracts.py`
  - **Actual outcome:** FAIL; exit `1`; 27 tests collected, 27 failed, and 0
    passed in 0.33 seconds.
  - **Representative failure:** `_public_api()` reports the intended missing
    public exports, including the newly required `NormalizedType` and
    `RetrievalMode` names.
  - **Why this remains meaningful:** Collection succeeded and every failure
    occurs at the missing approved public-contract exports. No database,
    provider, network, Docker, or private-core behavior was invoked.
- **GREEN:** Not started.
- **Independent human verification:** Pending.
- **Person 2 review:** Pending.
- **T007-B acceptance:** Pending.

## T007-B-03 — Public contract GREEN implementation

- **Date:** 2026-11-22
- **Files changed:**
  - `src/sciscope/retrieval/contracts.py` (new public DTOs and boundary
    validation)
  - `src/sciscope/retrieval/errors.py` (new shared public error taxonomy and
    sanitized exception)
  - `src/sciscope/retrieval/__init__.py` (supported public exports)
  - `src/sciscope/retrieval/_errors.py` (private `RetrievalFailure`
    compatibility through the public error definitions)
  - `tests/retrieval/test_public_contracts.py` (mechanical Ruff import and
    line formatting only after the approved RED assertions were written)
  - `docs/person3/FEATURE_007_T007_TEST_LOG.md`
- **Implementation:** Added frozen, slotted public DTOs for the documented
  v1/v2 field shapes. `RetrievalRequest` validates and canonicalizes request
  values before any provider or database use. It accepts only explicit
  `retrieval.v1`/`retrieval.v2`, fails unknown versions closed, retains a valid
  request ID for other failures, and omits an invalid request ID. Filters use
  immutable tuples and the existing accepted DOI normalization utility. Public
  imports use neither the private retrieval core nor database/ORM modules.
  Private callers retain the same `RetrievalErrorCode` identity and
  `RetrievalFailure` behavior by subclassing the public typed exception.

### Focused GREEN result

- **Command:** `uv run --locked pytest
  tests/retrieval/test_public_contracts.py`
  - **Actual outcome:** PASS; exit `0`; 27 collected, 27 passed, 0 failed in
    0.16 seconds.
  - **Final rerun after static corrections:** PASS; exit `0`; 27 collected,
    27 passed, 0 failed in 0.23 seconds.

### Static checks and regressions

- **Initial Ruff lint:** `uv run --locked ruff check --no-cache
  src/sciscope/retrieval tests/retrieval/test_public_contracts.py`
  - **Actual outcome:** FAIL; exit `1`; 20 style/import-order findings in the
    new modules and T007-B test file.
- **Initial formatter check:** `uv run --locked ruff format --check
  src/sciscope/retrieval tests/retrieval/test_public_contracts.py`
  - **Actual outcome:** FAIL; exit `1`; `contracts.py` and the public-contract
    test required formatting.
- **Initial mypy:** `uv run --locked mypy src/sciscope/retrieval`
  - **Actual outcome:** FAIL; exit `1`; three type-narrowing findings in the
    new DTO filter canonicalization plus three `_errors.py` export findings.
- **Corrections:** Added type-safe tuple casts after runtime string checks,
  declared the private error-module exports, and applied only mechanical Ruff
  formatting/import-order fixes. `RetrievalFailure` also retains its prior
  error-code exception display value while exposing the shared public typed
  fields. No retrieval algorithm, database, provider, ranking, or test
  assertion behavior changed.
- **Final Ruff lint:** `uv run --locked ruff check --no-cache
  src/sciscope/retrieval tests/retrieval/test_public_contracts.py`
  - **Actual outcome:** PASS; exit `0`; all checks passed.
- **Final formatter check:** `uv run --locked ruff format --check
  src/sciscope/retrieval tests/retrieval/test_public_contracts.py`
  - **Actual outcome:** PASS; exit `0`; 13 files already formatted.
- **Final mypy:** `uv run --locked mypy src/sciscope/retrieval`
  - **Actual outcome:** PASS; exit `0`; no issues in 12 source files.
- **Private error compatibility:** `uv run --locked pytest
  tests/retrieval/test_errors.py`
  - **Actual outcome:** PASS; exit `0`; 2 collected, 2 passed in 0.36 seconds.
- **Final focused compatibility rerun:** `uv run --locked pytest
  tests/retrieval/test_public_contracts.py tests/retrieval/test_errors.py`
  - **Actual outcome:** PASS; exit `0`; 29 collected, 29 passed in 0.38
    seconds.
- **Requested private validation regression:** `uv run --locked pytest
  tests/retrieval/test_validation.py`
  - **Actual outcome:** BLOCKED; exit `2`; collection failed because
    `tests.retrieval.conftest` could not import the repository's `tests`
    namespace. The same result persisted after the DTO/error corrections;
    this was not a retrieval assertion failure.
- **Validation regression with repository root on the import path:**
  `PYTHONPATH=. uv run --locked pytest tests/retrieval/test_validation.py`
  - **Actual outcome:** PASS; exit `0`; 30 collected, 30 passed in 0.41
    seconds. This confirms the direct-command failure is an import-path setup
    limitation rather than a regression in the approved public contract work.

- **Independent human verification:** Pending.
- **Person 2 review:** Pending.
- **Human acceptance:** Pending.
- **Commit:** Not created.

## T007-B-04 — Independent Human Verification

- **Date recorded:** 2026-11-22
- **Evidence source:** The project owner reports independently executing the
  following checks and observing the results recorded here. These are human-run
  verification results, not Codex-executed results.
- **Public contracts and private error compatibility:** `uv run --locked
  pytest tests/retrieval/test_public_contracts.py tests/retrieval/test_errors.py`
  - **Actual outcome reported by owner:** PASS; 29 passed.
- **Private validation:** `PYTHONPATH=. uv run --locked pytest
  tests/retrieval/test_validation.py`
  - **Actual outcome reported by owner:** PASS; 30 passed.
- **Ruff lint:** `uv run --locked ruff check --no-cache
  src/sciscope/retrieval tests/retrieval/test_public_contracts.py`
  - **Actual outcome reported by owner:** PASS.
- **Ruff formatter:** `uv run --locked ruff format --check
  src/sciscope/retrieval tests/retrieval/test_public_contracts.py`
  - **Actual outcome reported by owner:** PASS; 13 files formatted correctly.
- **Mypy:** `uv run --locked mypy src/sciscope/retrieval`
  - **Actual outcome reported by owner:** PASS; 12 source files checked.
- **Whitespace check:** `git diff --check`
  - **Actual outcome reported by owner:** PASS; no reported errors.
- **Full offline retrieval regression:** `PYTHONPATH=. uv run --locked pytest
  tests/retrieval -q --ignore=tests/retrieval/test_postgres_core.py
  --ignore=tests/retrieval/test_postgres_lookup.py
  --ignore=tests/retrieval/test_phase_c_pipeline.py`
  - **Actual outcome reported by owner:** PASS; 117 passed in 0.43 seconds.
  - **Scope limitation:** The explicitly ignored PostgreSQL tests and phase-C
    pipeline test were not run and are not claimed as passing.
- **Earlier broad regression attempt:** The owner reports 117 passed with 15
  setup errors because `SCISCOPE_TEST_DATABASE_URL` was unset. The command was
  not supplied in the owner report. These are database-environment setup errors,
  not retrieval assertion failures; no database tests are claimed as passing.
- **Git status reported by owner:** Only the six expected T007-B files changed;
  nothing was staged or committed.
- **Team context:** The owner reports that Person 2 previously approved the
  agreed T007 scope internally and delegated implementation and technical
  decisions to Person 3. This records the reported scope agreement; it does
  not fabricate completion of a separate code review.
- **Person 2 code review:** Pending where required by the repository workflow.
- **Human acceptance:** Pending; the owner has reported verification results
  but has not provided an explicit T007-B acceptance decision.
- **Commit:** Not created.

## T007-B-06 — Nested DTO immutability RED/GREEN fix

- **Date:** 2026-11-22
- **Defect:** Frozen public DTOs accepted mutable lists for
  `PaperMetadata.authors`, `RetrievalResult.section_path`,
  `RetrievalResponse.results`, and `RetrievalResponse.warnings`.
- **Contract interpretation:** The canonical Python API declares each affected
  field as a tuple and does not authorize mutable-list canonicalization. This
  increment therefore requires tuple-only inputs and raises the approved
  sanitized `INVALID_REQUEST` error for lists.
- **RED tests added:** Parameterized tuple-preservation and mutable-list
  rejection coverage for all four affected fields in
  `tests/retrieval/test_public_contracts.py`.
- **RED command:** `uv run --locked pytest
  tests/retrieval/test_public_contracts.py`
  - **Actual outcome:** FAIL; exit `1`; 35 collected, 31 passed, 4 failed in
    0.27 seconds.
  - **Representative failure:**
    `test_response_dtos_reject_mutable_nested_collections[authors]` failed
    because `PaperMetadata` accepted a list and did not raise
    `RetrievalException`.
  - **Why this is meaningful:** Each failure corresponds to one documented
    mutable nested collection and occurs because the DTO retains the list;
    valid surrounding provenance fixtures constructed successfully. No
    database, provider, network, Docker, or private-core operation ran.
- **GREEN:** Not started.
- **Independent human verification:** Pending after correction.
- **Person 2 code review:** Pending.
- **Human acceptance:** Pending.
- **Commit:** Not created.

### GREEN completion

- **Implementation changed:** `src/sciscope/retrieval/contracts.py` now
  requires exact tuples for `PaperMetadata.authors`,
  `RetrievalResult.section_path`, `RetrievalResponse.results`, and
  `RetrievalResponse.warnings`. It validates the documented element types and
  warning literal before retaining each tuple. No list reference can be
  retained; valid tuples preserve ordering, source values, and provenance.
- **Focused GREEN command:** `uv run --locked pytest
  tests/retrieval/test_public_contracts.py tests/retrieval/test_errors.py`
  - **Actual outcome:** PASS; exit `0`; 37 collected, 37 passed in 0.42
    seconds.
- **Private validation regression:** `PYTHONPATH=. uv run --locked pytest
  tests/retrieval/test_validation.py`
  - **Actual outcome:** PASS; exit `0`; 30 collected, 30 passed in 0.37
    seconds.
- **Offline retrieval regression:** `PYTHONPATH=. uv run --locked pytest
  tests/retrieval -q --ignore=tests/retrieval/test_postgres_core.py
  --ignore=tests/retrieval/test_postgres_lookup.py
  --ignore=tests/retrieval/test_phase_c_pipeline.py`
  - **Actual outcome:** PASS; exit `0`; 125 passed in 0.70 seconds. The count
    is eight higher than the prior owner-reported run because the four new
    parameterized tuple-preservation and four mutable-list rejection cases are
    included. PostgreSQL and phase-C tests remained explicitly excluded.
- **Initial Ruff lint:** `uv run --locked ruff check --no-cache
  src/sciscope/retrieval tests/retrieval/test_public_contracts.py`
  - **Actual outcome:** FAIL; exit `1`; three formatting-only findings in the
    new immutability code/tests.
- **Initial formatter check:** `uv run --locked ruff format --check
  src/sciscope/retrieval tests/retrieval/test_public_contracts.py`
  - **Actual outcome:** FAIL; exit `1`; the public-contract test required
    formatting.
- **Correction:** Shortened two docstrings and wrapped two test expressions;
  no behavior or assertion changed. `uv run --locked ruff format
  src/sciscope/retrieval tests/retrieval/test_public_contracts.py` then
  reported 13 files unchanged.
- **Final Ruff lint:** `uv run --locked ruff check --no-cache
  src/sciscope/retrieval tests/retrieval/test_public_contracts.py`
  - **Actual outcome:** PASS; exit `0`; all checks passed.
- **Final formatter check:** `uv run --locked ruff format --check
  src/sciscope/retrieval tests/retrieval/test_public_contracts.py`
  - **Actual outcome:** PASS; exit `0`; 13 files already formatted.
- **Final mypy:** `uv run --locked mypy src/sciscope/retrieval`
  - **Actual outcome:** PASS; exit `0`; no issues found in 12 source files.
- **Independent human verification:** Pending after this correction.
- **Person 2 code review:** Pending.
- **Human acceptance:** Pending.
- **Commit:** Not created.

## T007-B-07 — Corrected Independent Human Verification

- **Date reported:** 2026-11-22
- **Evidence source:** The project owner reports independently executing the
  following checks after T007-B-06. These are user-run observations, not
  Codex-executed results.
- **Focused public contracts and private errors:** `uv run --locked pytest
  tests/retrieval/test_public_contracts.py tests/retrieval/test_errors.py`
  - **Actual outcome reported by owner:** PASS; 37 passed in 0.35 seconds.
- **Private validation:** `PYTHONPATH=. uv run --locked pytest
  tests/retrieval/test_validation.py`
  - **Actual outcome reported by owner:** PASS; 30 passed in 0.29 seconds.
- **Offline retrieval regression:** `PYTHONPATH=. uv run --locked pytest
  tests/retrieval -q --ignore=tests/retrieval/test_postgres_core.py
  --ignore=tests/retrieval/test_postgres_lookup.py
  --ignore=tests/retrieval/test_phase_c_pipeline.py`
  - **Actual outcome reported by owner:** PASS; 125 passed in 0.44 seconds.
  PostgreSQL integration tests and the phase-C pipeline test were not executed.
- **Ruff lint:** `uv run --locked ruff check --no-cache
  src/sciscope/retrieval tests/retrieval/test_public_contracts.py`
  - **Actual outcome reported by owner:** PASS; all checks passed.
- **Ruff format:** `uv run --locked ruff format --check
  src/sciscope/retrieval tests/retrieval/test_public_contracts.py`
  - **Actual outcome reported by owner:** PASS; 13 files already formatted.
- **Mypy:** `uv run --locked mypy src/sciscope/retrieval`
  - **Actual outcome reported by owner:** PASS; no issues in 12 source files.
- **Whitespace check:** `git diff --check`
  - **Actual outcome reported by owner:** PASS; no errors reported.
- **Scope check:** `git status --short`
  - **Actual outcome reported by owner:** only the six expected T007-B files
    changed; nothing staged or committed.
- **Prior evidence:** T007-B-01 through T007-B-06 RED, GREEN, correction, and
  independent-verification records are preserved above.
- **Person 2 code review:** Pending. The recorded scope approval and delegation
  do not represent review of the implemented retrieval-owned source changes.
- **Human acceptance:** Pending; no explicit T007-B acceptance decision has
  been reported.
- **Commit:** Not created.

## T007-B-08 — Code Review, Human Acceptance and Commit Preparation

- **Date recorded:** 2026-11-22
- **Person 2 code review:** The project owner reports that Person 2 reviewed
  `contracts.py`, `errors.py`, `__init__.py`, and `_errors.py`, confirmed
  successful completion, and permitted T007-B to be finalized. This is an
  owner-reported review confirmation; Codex did not directly observe the review.
- **Final independent verification:** The owner-reported results in T007-B-07
  remain the final independent verification: 37 focused tests, 30 private
  validation tests, and 125 offline retrieval regression tests passed; Ruff
  lint and formatting, mypy, and whitespace checks passed.
- **Codex final offline verification:**
  - `uv run --locked pytest tests/retrieval/test_public_contracts.py tests/retrieval/test_errors.py`
    - **Actual outcome:** PASS; exit `0`; 37 passed in 0.44 seconds.
  - `PYTHONPATH=. uv run --locked pytest tests/retrieval/test_validation.py`
    - **Actual outcome:** PASS; exit `0`; 30 passed in 0.47 seconds.
  - `PYTHONPATH=. uv run --locked pytest tests/retrieval -q --ignore=tests/retrieval/test_postgres_core.py --ignore=tests/retrieval/test_postgres_lookup.py --ignore=tests/retrieval/test_phase_c_pipeline.py`
    - **Actual outcome:** PASS; exit `0`; 125 passed in 0.84 seconds.
  - `uv run --locked ruff check --no-cache src/sciscope/retrieval tests/retrieval/test_public_contracts.py`
    - **Actual outcome:** PASS; exit `0`; all checks passed.
  - `uv run --locked ruff format --check src/sciscope/retrieval tests/retrieval/test_public_contracts.py`
    - **Actual outcome:** PASS; exit `0`; 13 files already formatted.
  - `uv run --locked mypy src/sciscope/retrieval`
    - **Actual outcome:** PASS; exit `0`; no issues found in 12 source files.
- **Database integration:** PostgreSQL-backed tests were not executed.
- **Human acceptance:** **ACCEPTED**. The project owner explicitly authorized
  T007-B completion.
- **Scope disposition:** T007-B is accepted for this scoped commit. Feature 007
  remains open; T007-C and later increments remain pending.
- **Commit:** Not yet created; commit preparation is authorized.

## T007-C-02A — Public Facade RED Tests

- **Date recorded:** 2026-11-22
- **Baseline:** Branch `007-public-retrieval-facade` at
  `df104b966c1a5725f50f1f8845f79366fa5c6b9f`.
- **Approved scope:** Initial offline public-facade tests only: public exports,
  the public `QueryEmbedder` protocol, fresh-process import isolation,
  constructor injection, and public-request forwarding through an injected
  driver-independent executor. No response/error mapping, provider, ranking,
  transaction, or provenance-mapping behavior is covered in this increment.
- **Files introduced:** `tests/retrieval/test_public_service.py`.
- **RED command:** `uv run --locked pytest
  tests/retrieval/test_public_service.py`; actual attempts and outcome appear
  below.
- **GREEN:** Not started.
- **Independent human verification:** Pending.
- **Person 2 implementation review:** Pending.
- **Person 1 provenance review:** Pending for the later response-mapping
  increment.
- **Commit:** Not created.
- **Initial RED attempt:** `uv run --locked pytest
  tests/retrieval/test_public_service.py` exited `1` with 5 failed, 0 passed.
  Four failures were the intended missing public exports. The fresh-process
  import-isolation test instead failed with `ModuleNotFoundError: No module
  named 'sciscope'`; this was a test subprocess import-path setup defect, not
  missing facade behavior.
- **Correction:** Added `src` to the fresh subprocess import path, matching the
  established public-contract isolation test. No production file was changed.
- **Actual RED command:** `uv run --locked pytest
  tests/retrieval/test_public_service.py`
  - **Actual outcome:** exit `1`; 5 collected, 5 failed, 0 passed.
  - **Representative failure:** `Missing public retrieval exports:
    ['RetrievalService', 'QueryEmbedder']`.
  - **Import-isolation result:** after the subprocess-path correction, it fails
    for the intended missing public facade exports, rather than environment
    setup.
- **RED conclusion:** Verified. All failures are caused by the absent approved
  T007-C public facade and exports; GREEN implementation has not started.

## T007-C-02B — Minimal Public Facade GREEN

- **Date recorded:** 2026-11-22
- **Implementation scope:** Added the import-safe public
  `sciscope.retrieval.service` module and root-package exports. `QueryEmbedder`
  is a public protocol with a keyword-only public `EmbeddingConfig`; the
  concrete `RetrievalService` stores a driver-independent injected executor and
  forwards the exact request once, returning its exact public response.
- **Files added or modified:** `src/sciscope/retrieval/service.py` and
  `src/sciscope/retrieval/__init__.py`; the existing T007-C-02A test and log
  remain in scope.
- **Focused GREEN:** `uv run --locked pytest
  tests/retrieval/test_public_service.py`
  - **Actual outcome:** PASS; exit `0`; 5 collected, 5 passed in 0.11 seconds.
- **Public import isolation:** PASS through the fresh-process focused test; the
  root public import did not load SQLAlchemy, pgvector, supported database
  drivers, or `sciscope.retrieval._core`.
- **Static checks:**
  - Initial `ruff check` and `ruff format --check` found only line-length and
    formatting issues in the new service/test files. Mypy passed. Applied only
    mechanical formatting and docstring wrapping; no test assertion was
    weakened and no runtime behavior changed.
  - `uv run --locked ruff check --no-cache src/sciscope/retrieval tests/retrieval/test_public_service.py`
    - **Actual outcome:** PASS; exit `0`; all checks passed.
  - `uv run --locked ruff format --check src/sciscope/retrieval tests/retrieval/test_public_service.py`
    - **Actual outcome:** PASS; exit `0`; 14 files already formatted.
  - `uv run --locked mypy src/sciscope/retrieval`
    - **Actual outcome:** PASS; exit `0`; no issues found in 13 source files.
- **Offline regressions:**
  - `uv run --locked pytest tests/retrieval/test_public_contracts.py tests/retrieval/test_errors.py`
    - **Actual outcome:** PASS; exit `0`; 37 passed in 0.54 seconds.
  - `PYTHONPATH=. uv run --locked pytest tests/retrieval/test_validation.py`
    - **Actual outcome:** PASS; exit `0`; 30 passed in 0.38 seconds.
  - `PYTHONPATH=. uv run --locked pytest tests/retrieval -q --ignore=tests/retrieval/test_postgres_core.py --ignore=tests/retrieval/test_postgres_lookup.py --ignore=tests/retrieval/test_phase_c_pipeline.py`
    - **Actual outcome:** PASS; exit `0`; 130 passed in 0.81 seconds.
- **Database integration:** Not executed. PostgreSQL-backed tests, Docker,
  provider calls, and external network access were not used.
- **Deferred scope:** No private-core composition, response/provenance mapping,
  error translation, provider behavior, or retrieval algorithm was implemented.
- **Independent human verification:** Pending.
- **Person 2 implementation review:** Pending.
- **Person 1 provenance review:** Pending for the later response-mapping
  increment.
- **Commit:** Not created.

## T007-C-02C — Independent Human Verification

- **Date reported:** 2026-11-22
- **Evidence source:** The project owner reports independently running the
  following checks after T007-C-02B. These are owner-run observations, not
  Codex-executed results.
- **Facade tests:** `uv run --locked pytest
  tests/retrieval/test_public_service.py`
  - **Actual outcome reported by owner:** PASS; 5 passed in 0.10 seconds.
- **Public contracts and private errors:** `uv run --locked pytest
  tests/retrieval/test_public_contracts.py tests/retrieval/test_errors.py`
  - **Actual outcome reported by owner:** PASS; 37 passed in 0.35 seconds.
- **Private validation:** `PYTHONPATH=. uv run --locked pytest
  tests/retrieval/test_validation.py`
  - **Actual outcome reported by owner:** PASS; 30 passed in 0.29 seconds.
- **Offline retrieval regression:** `PYTHONPATH=. uv run --locked pytest
  tests/retrieval -q --ignore=tests/retrieval/test_postgres_core.py
  --ignore=tests/retrieval/test_postgres_lookup.py
  --ignore=tests/retrieval/test_phase_c_pipeline.py`
  - **Actual outcome reported by owner:** PASS; 130 passed in 0.51 seconds.
- **Ruff lint:** The owner reports PASS; all checks passed.
- **Ruff formatter:** The owner reports PASS; 14 files already formatted.
- **Mypy:** The owner reports PASS; no issues in 13 source files.
- **Whitespace check:** `git diff --check`
  - **Actual outcome reported by owner:** PASS; no errors reported.
- **Scope check:** `git status --short`
  - **Actual outcome reported by owner:** only the four expected T007-C files
    changed; nothing staged or committed.
- **Database integration:** Database-backed tests were not run and are not
  claimed as passing.
- **Prior evidence:** The T007-C-02A RED and T007-C-02B GREEN entries are
  preserved above.
- **Deferred increments:** T007-C-03 and T007-C-04 have not started.
- **Person 2 code review:** Pending.
- **Person 1 provenance review:** Pending.
- **T007-C human acceptance:** Pending.
- **Commit:** Not created.

## T007-C-03A — Response Mapping and Error Translation RED

- **Date recorded:** 2026-11-22
- **Baseline:** Branch `007-public-retrieval-facade` at
  `df104b966c1a5725f50f1f8845f79366fa5c6b9f`; the four existing T007-C files
  were changed and the staging index was empty.
- **Tests added:** Five deterministic cases in
  `tests/retrieval/test_public_service.py`: exact private-response mapping for
  `retrieval.v1` and `retrieval.v2`, empty-result mapping with corpus identity,
  private `RetrievalFailure` translation, and unexpected-exception
  sanitization. Existing T007-C-02 pass-through tests remain unchanged.
- **Confirmed private shapes:** `_Response` contains `contract_version`,
  `request_id`, `mode`, `top_k`, `candidate_pool_size`, `applied_filters`,
  `rrf_constant`, `_Corpus`, optional `_EmbeddingConfig`, tuple of `_Hit`, and
  warnings. `_Hit` contains rank, stable chunk/source fields, ordered section
  path, `paper` dictionary, and `_Score`. `_Corpus` contains delivery/source
  contract/corpus identity plus embedding metadata. Private filters are
  `InternalFilters`; `RetrievalFailure` has public code, request ID, and
  retryable fields while retaining its private class identity.
- **Selected internal adapter boundary:** retain
  `RetrievalService(executor=...)` and its public fake-executor behavior. Add
  private mapping and exception-translation helpers inside `service.py` in the
  later GREEN step; they will map an actual private `_Response` only after the
  executor returns, with private imports deferred until retrieval execution.
- **RED command:** `uv run --locked pytest
  tests/retrieval/test_public_service.py`
  - **Actual outcome:** exit `1`; 10 collected, 5 passed, 5 failed.
  - **Expected mapping failures:** private `_Response` was returned unchanged,
    so it was not a public `RetrievalResponse` for both v1 and v2 provenance
    tests and for the empty-result test.
  - **Expected failure-translation failure:** private `RetrievalFailure` was
    propagated instead of becoming a fresh `RetrievalException`.
  - **Expected sanitization failure:** a `ValueError` containing a database URL
    was propagated rather than becoming a sanitized internal retrieval error.
- **Fixture corrections:** None. Private dataclass fields, paper dictionary
  keys, filters, and exception constructor arguments were read from repository
  source before test creation.
- **GREEN:** Not started.
- **Independent human verification:** Pending.
- **Person 2 implementation review:** Pending.
- **Person 1 provenance review:** Pending.
- **Commit:** Not created.

## T007-C-03B — Response Mapping and Error Translation GREEN

- **Date recorded:** 2026-11-22
- **Implementation:** Updated only `src/sciscope/retrieval/service.py` to map
  private `_Response` values after executor execution. The public pass-through
  behavior remains exact for an existing `RetrievalResponse`. Private imports
  occur only inside mapping/error paths, not during public package import.
- **Mapping decisions:** `_Corpus` maps to `CorpusIdentity`; optional
  `_EmbeddingConfig` maps to `EmbeddingConfig`; `InternalFilters` maps to
  `RetrievalFilters`; `_Hit`, its ordered paper-author dictionaries, and
  `_Score` map to immutable `RetrievalResult`, `PaperMetadata`, `Author`, and
  `RetrievalScore`. Contract version, mode, values, ranks, warnings, source
  identifiers, source text, source strings, corpus identity, and score values
  are copied exactly without normalization, fallback, synthesis, or recompute.
- **Error translation:** a private `RetrievalFailure` becomes a fresh public
  `RetrievalException` containing only its approved code, request ID,
  retryability, and stable public message. Any other executor or mapping error
  becomes nonretryable `RETRIEVAL_INTERNAL_ERROR` using the request ID, raised
  without exception chaining. No retry or second executor call is made.
- **Focused GREEN:** `uv run --locked pytest
  tests/retrieval/test_public_service.py`
  - **Actual outcome:** PASS; exit `0`; 10 passed in 0.43 seconds.
- **Compatibility and offline regressions:**
  - `uv run --locked pytest tests/retrieval/test_public_contracts.py tests/retrieval/test_errors.py`
    - **Actual outcome:** PASS; exit `0`; 37 passed in 0.47 seconds.
  - `PYTHONPATH=. uv run --locked pytest tests/retrieval/test_validation.py`
    - **Actual outcome:** PASS; exit `0`; 30 passed in 0.43 seconds.
  - `PYTHONPATH=. uv run --locked pytest tests/retrieval -q --ignore=tests/retrieval/test_postgres_core.py --ignore=tests/retrieval/test_postgres_lookup.py --ignore=tests/retrieval/test_phase_c_pipeline.py`
    - **Actual outcome:** PASS; exit `0`; 135 passed in 0.65 seconds.
- **Static checks:**
  - Initial static run found test-file line-length/formatting issues and three
    private-string to public-literal type-boundary issues in `service.py`.
    Corrected only test formatting and explicit type narrowing; no test
    assertion, private core, algorithm, filter, or ranking behavior changed.
  - `uv run --locked ruff check --no-cache src/sciscope/retrieval tests/retrieval/test_public_service.py`
    - **Actual outcome:** PASS; exit `0`; all checks passed.
  - `uv run --locked ruff format --check src/sciscope/retrieval tests/retrieval/test_public_service.py`
    - **Actual outcome:** PASS; exit `0`; 14 files already formatted.
  - `uv run --locked mypy src/sciscope/retrieval`
    - **Actual outcome:** PASS; exit `0`; no issues found in 13 source files.
- **Import isolation:** PASS through the fresh-process public-service test; no
  private core, SQLAlchemy, pgvector, supported driver, database connection, or
  provider initialization occurs from public import.
- **Database integration:** PostgreSQL-backed tests were not executed.
- **Deferred scope:** Private-core composition and T007-C-04 conformance work
  have not started.
- **Independent human verification:** Pending.
- **Person 2 code review:** Pending.
- **Person 1 provenance review:** Pending.
- **T007-C human acceptance:** Pending.
- **Commit:** Not created.

## T007-C-03C — Independent Human Verification

- **Date reported:** 2026-11-22
- **Evidence source:** The project owner reports independently running the
  following verification after T007-C-03B. These are owner-run observations,
  not Codex-executed results.
- **Public facade:** `uv run --locked pytest
  tests/retrieval/test_public_service.py`
  - **Actual outcome reported by owner:** PASS; 10 passed in 0.34 seconds.
- **Public contracts and private errors:** `uv run --locked pytest
  tests/retrieval/test_public_contracts.py tests/retrieval/test_errors.py`
  - **Actual outcome reported by owner:** PASS; 37 passed in 0.37 seconds.
- **Private validation:** `PYTHONPATH=. uv run --locked pytest
  tests/retrieval/test_validation.py`
  - **Actual outcome reported by owner:** PASS; 30 passed in 0.29 seconds.
- **Offline retrieval regression:** `PYTHONPATH=. uv run --locked pytest
  tests/retrieval -q --ignore=tests/retrieval/test_postgres_core.py
  --ignore=tests/retrieval/test_postgres_lookup.py
  --ignore=tests/retrieval/test_phase_c_pipeline.py`
  - **Actual outcome reported by owner:** PASS; 135 passed in 0.54 seconds.
- **Ruff lint:** The owner reports PASS; all checks passed.
- **Ruff formatter:** The owner reports PASS; 14 files already formatted.
- **Mypy:** The owner reports PASS; no issues in 13 source files.
- **Whitespace check:** `git diff --check`
  - **Actual outcome reported by owner:** PASS; no output or errors.
- **Scope check:** `git status --short`
  - **Actual outcome reported by owner:** only the four expected T007-C files
    changed; nothing staged or committed.
- **Database integration:** PostgreSQL-backed tests were not run and are not
  claimed as passing.
- **Prior evidence:** Earlier T007-C RED/GREEN evidence is preserved above.
- **Person 2 code review:** Pending.
- **Person 1 provenance review:** Pending.
- **T007-C human acceptance:** Pending.
- **Commit:** Not created.

## T007-C-04A — Private-Core Composition RED

- **Date:** 2026-11-22
- **Baseline:** Branch `007-public-retrieval-facade`, HEAD
  `df104b966c1a5725f50f1f8845f79366fa5c6b9f`; the index was empty. The
  existing T007-C worktree contained only this log, `__init__.py`,
  `service.py`, and `test_public_service.py`.
- **Tests added:** Private-core composition coverage in
  `tests/retrieval/test_public_service.py` for canonical public-request to raw
  private-request conversion, omission of unset filter categories and absent
  ranking, explicit v1/v2 and dense/lexical/hybrid forwarding, the
  public-to-private embedder-config bridge, private `_Response` flow through
  the existing public mapper, and lazy core construction with exact engine and
  reranker dependencies.
- **Confirmed private interfaces:** `_RetrievalCore(engine, embedder, *,
  reranker=None)` accepts raw request keys `contract_version`, `request_id`,
  `query_text`, `mode`, `top_k`, optional `filters`, and optional `ranking`;
  its `retrieve()` method returns `_Response`. The private embedder accepts
  `_EmbeddingConfig` as its keyword-only `config` argument. The public
  embedder accepts the parallel public `EmbeddingConfig`.
- **Selected internal boundary:** The RED tests require the unexported
  `service.py` seams `_PrivateCoreExecutor`, `_PrivateEmbedderBridge`, and
  `_compose_private_executor`. They retain the approved public
  `RetrievalService(executor=...)` signature.
- **Initial test-fixture correction:** The initial optional-ranking fixture
  used lexical mode with `RankingOptions(candidate_pool_size=None)`. The
  existing public contract correctly rejects any ranking object outside hybrid
  mode. The fixture was corrected to use hybrid mode; no production code was
  changed.
- **RED command:** `uv run --locked pytest
  tests/retrieval/test_public_service.py`
  - **Actual outcome:** FAIL; exit `1`; 19 collected, 10 passed, 9 failed in
    0.58 seconds.
  - **Representative expected failures:** `AttributeError` because
    `sciscope.retrieval.service` has no `_PrivateCoreExecutor`,
    `_PrivateEmbedderBridge`, or `_compose_private_executor`.
  - **RED interpretation:** The prior 10 public-facade and mapping tests stay
    green. The new failures demonstrate only the missing approved private-core
    composition bridge, after the fixture correction removed the unrelated
    contract-validation failure.
- **Lexical coverage boundary:** Existing offline core coverage in
  `tests/retrieval/test_core_offline.py::test_lexical_mode_never_calls_embedder`
  remains the evidence that lexical retrieval skips query embedding. This
  increment does not duplicate core algorithm behavior or execute a database.
- **Provider-error boundary:** The public `QueryEmbedder` protocol has no
  approved typed transient provider-error signal. No speculative provider-error
  test or fallback was added; this remains a deferred live-adapter contract
  decision.
- **Database integration:** PostgreSQL-backed tests were not run.
- **GREEN:** Not started.
- **Independent human verification:** Pending.
- **Person 2 implementation review:** Pending.
- **Person 1 provenance review:** Pending.
- **T007-C human acceptance:** Pending.
- **Commit:** Not created.

## T007-C-04B — Private-Core Composition GREEN

- **Date:** 2026-11-22
- **Implementation scope:** Modified only `src/sciscope/retrieval/service.py`
  for production behavior. Added unexported `_private_request_value`,
  `_PrivateCoreExecutor`, `_PrivateEmbedderBridge`, and
  `_compose_private_executor`.
- **Request bridge:** `_PrivateCoreExecutor` converts a validated public
  `RetrievalRequest` to the private core's documented dictionary keys and calls
  `core.retrieve()` once. It omits `filters` when absent or fully unset,
  excludes every `None` filter category, and omits `ranking` unless a
  candidate-pool size is present. It preserves the public canonical contract
  version, request ID, query text, mode, top-k, filters, and candidate-pool
  size exactly.
- **Embedder bridge:** `_PrivateEmbedderBridge` converts the private
  `_EmbeddingConfig` to a fresh immutable public `EmbeddingConfig`, preserving
  provider, model, dimensions, and query prefix. It passes text unchanged,
  invokes the injected public embedder once per bridge call, and returns its
  vector unchanged. It performs no embedding during construction.
- **Lazy composition:** `_compose_private_executor` lazily imports
  `_RetrievalCore`, wraps a supplied public embedder only when present, passes
  the supplied engine and reranker through unchanged, and returns a private
  executor. Public imports remain independent of the private core and database
  modules. Construction does not open a connection, execute retrieval, invoke
  an embedder, or invoke a reranker.
- **Response and errors:** Existing `RetrievalService` mapping and
  sanitization behavior was not rewritten. Private responses continue through
  the already verified mapper; public responses remain pass-through values.
- **Initial focused GREEN:** `uv run --locked pytest
  tests/retrieval/test_public_service.py`
  - **Actual outcome:** PASS; exit `0`; 19 passed in 0.38 seconds.
- **Initial compatibility checks:**
  - `uv run --locked pytest tests/retrieval/test_public_contracts.py
    tests/retrieval/test_errors.py`
    - **Actual outcome:** PASS; exit `0`; 37 passed in 0.44 seconds.
  - `PYTHONPATH=. uv run --locked pytest tests/retrieval/test_validation.py`
    - **Actual outcome:** PASS; exit `0`; 30 passed in 0.56 seconds.
  - `PYTHONPATH=. uv run --locked pytest tests/retrieval/test_core_offline.py
    tests/retrieval/test_v2_bm25.py`
    - **Actual outcome:** PASS; exit `0`; 13 passed in 0.40 seconds.
  - `PYTHONPATH=. uv run --locked pytest tests/retrieval -q
    --ignore=tests/retrieval/test_postgres_core.py
    --ignore=tests/retrieval/test_postgres_lookup.py
    --ignore=tests/retrieval/test_phase_c_pipeline.py`
    - **Actual outcome:** PASS; exit `0`; 144 passed in 0.65 seconds.
- **Initial static-check correction:** Ruff reported two line-length findings
  in the authorized files and an unused public-import setup value in the test.
  Mypy reported that the deliberately driver-independent `object` composition
  inputs did not satisfy private `Engine` and `Reranker` annotations. Corrected
  only the test setup, formatting, and local internal type narrowing at the
  private-core construction boundary. No public API, test assertion, core,
  algorithm, filter, ranking, SQL, or database behavior changed.
- **Final verification after correction:**
  - `uv run --locked pytest tests/retrieval/test_public_service.py`
    - **Actual outcome:** PASS; exit `0`; 19 passed in 0.50 seconds.
  - `uv run --locked pytest tests/retrieval/test_public_contracts.py
    tests/retrieval/test_errors.py`
    - **Actual outcome:** PASS; exit `0`; 37 passed in 0.45 seconds.
  - `PYTHONPATH=. uv run --locked pytest tests/retrieval/test_validation.py`
    - **Actual outcome:** PASS; exit `0`; 30 passed in 0.45 seconds.
  - `PYTHONPATH=. uv run --locked pytest tests/retrieval/test_core_offline.py
    tests/retrieval/test_v2_bm25.py`
    - **Actual outcome:** PASS; exit `0`; 13 passed in 0.30 seconds.
  - `PYTHONPATH=. uv run --locked pytest tests/retrieval -q
    --ignore=tests/retrieval/test_postgres_core.py
    --ignore=tests/retrieval/test_postgres_lookup.py
    --ignore=tests/retrieval/test_phase_c_pipeline.py`
    - **Actual outcome:** PASS; exit `0`; 144 passed in 0.70 seconds.
  - `uv run --locked ruff check --no-cache src/sciscope/retrieval
    tests/retrieval/test_public_service.py`
    - **Actual outcome:** PASS; exit `0`; all checks passed.
  - `uv run --locked ruff format --check src/sciscope/retrieval
    tests/retrieval/test_public_service.py`
    - **Actual outcome:** PASS; exit `0`; 14 files already formatted.
  - `uv run --locked mypy src/sciscope/retrieval`
    - **Actual outcome:** PASS; exit `0`; no issues found in 13 source files.
- **Import isolation:** The fresh-process public import test remains part of
  the focused suite and passed. It confirms that public import does not load
  `_core`, SQLAlchemy, pgvector, supported PostgreSQL drivers, or a provider.
- **Database integration:** PostgreSQL-backed tests were not executed.
- **Provider-error boundary:** The public `QueryEmbedder` protocol still has
  no approved typed transient provider-error signal. No speculative provider
  error handling, fallback, or live-provider behavior was added.
- **Independent human verification:** Pending.
- **Person 2 code review:** Pending.
- **Person 1 provenance review:** Pending.
- **T007-C human acceptance:** Pending.
- **Commit:** Not created.

## T007-C-04C — Final Independent Human Verification and Team Review Acceptance

- **Date reported:** 2026-11-22
- **Verification source:** The project owner independently ran the following
  checks in a local terminal. These are owner-run observations, not
  Codex-executed results.
- **Public facade:** `uv run --locked pytest
  tests/retrieval/test_public_service.py`
  - **Actual owner-reported outcome:** PASS; 19 passed in 0.34 seconds.
- **Public contracts and private errors:** `uv run --locked pytest
  tests/retrieval/test_public_contracts.py tests/retrieval/test_errors.py`
  - **Actual owner-reported outcome:** PASS; 37 passed in 0.36 seconds.
- **Private validation:** `PYTHONPATH=. uv run --locked pytest
  tests/retrieval/test_validation.py`
  - **Actual owner-reported outcome:** PASS; 30 passed in 0.30 seconds.
- **Private core offline and BM25:** `PYTHONPATH=. uv run --locked pytest
  tests/retrieval/test_core_offline.py tests/retrieval/test_v2_bm25.py`
  - **Actual owner-reported outcome:** PASS; 13 passed in 0.30 seconds.
- **Offline retrieval regression:** `PYTHONPATH=. uv run --locked pytest
  tests/retrieval -q --ignore=tests/retrieval/test_postgres_core.py
  --ignore=tests/retrieval/test_postgres_lookup.py
  --ignore=tests/retrieval/test_phase_c_pipeline.py`
  - **Actual owner-reported outcome:** PASS; 144 passed in 0.52 seconds.
- **Ruff lint:** `uv run --locked ruff check --no-cache
  src/sciscope/retrieval tests/retrieval/test_public_service.py`
  - **Actual owner-reported outcome:** PASS; all checks passed.
- **Ruff formatter:** `uv run --locked ruff format --check
  src/sciscope/retrieval tests/retrieval/test_public_service.py`
  - **Actual owner-reported outcome:** PASS; 14 files already formatted.
- **Mypy:** `uv run --locked mypy src/sciscope/retrieval`
  - **Actual owner-reported outcome:** PASS; no issues found in 13 source
    files.
- **Whitespace check:** `git diff --check`
  - **Actual owner-reported outcome:** PASS; no output or errors.
- **Scope check:** `git status --short`
  - **Actual owner-reported outcome:** the expected four T007-C files changed:
    this log, `src/sciscope/retrieval/__init__.py`,
    `src/sciscope/retrieval/service.py`, and
    `tests/retrieval/test_public_service.py`. Nothing was staged or committed.
- **Environment limitations:** PostgreSQL-backed integration tests were not
  executed. No live embedding provider calls were made or claimed as passing.
- **Prior evidence:** All prior RED/GREEN and human-verification records are
  preserved above.
- **Person 1 provenance/source-mapping review:** ACCEPTED (owner-reported).
  The project owner reports that Person 1 internally reviewed and accepted the
  T007-C provenance and source-mapping changes. Codex did not directly witness
  this review.
- **Person 2 retrieval-owned source review:** ACCEPTED (owner-reported). The
  project owner reports that Person 2 internally reviewed and accepted the
  T007-C retrieval-owned implementation. Codex did not directly witness this
  review.
- **Review-gate disposition:** Based on the owner-reported confirmations, the
  previously pending Person 1 and Person 2 T007-C review gates are satisfied.
  The earlier scope approval and implementation delegation are not repeated
  here.
- **T007-C owner acceptance:** Pending; no final owner acceptance is inferred
  from verification or team-review acceptance.
- **Commit:** Not created.

## T007-C-05 — Final Owner Acceptance and Commit Authorization

- **Date:** 2026-11-22
- **Source:** Explicit project-owner decision.
- **Exact decision:** `T007-C ACCEPTED`.
- **Acceptance:** The project owner accepts the completed T007-C public
  retrieval-facade implementation and authorizes one focused T007-C commit.
  Push is not authorized.
- **Evidence reference:** The independent owner verification and the
  owner-reported Person 1 and Person 2 review acceptances are recorded in
  T007-C-04C above.
- **Verified coverage:** 19 public-facade tests, 37 public-contract/error
  tests, 30 validation tests, 13 private-core/BM25 tests, and 144 offline
  retrieval-regression tests passed. Ruff lint, Ruff formatting, and mypy
  passed.
- **Person 1 provenance/source-mapping review:** ACCEPTED (owner-reported),
  as recorded in T007-C-04C.
- **Person 2 retrieval-owned source review:** ACCEPTED (owner-reported), as
  recorded in T007-C-04C.
- **Limitations:** PostgreSQL-backed integration tests were not executed, and
  live embedding-provider behavior was not exercised. The public
  `QueryEmbedder` protocol has no approved typed transient provider-error
  signal; this concern remains deferred and is not represented as resolved.
- **Feature status:** T007-C acceptance does not complete Feature 007. T007-D
  and final feature-level acceptance remain pending.
- **Commit:** Pending final Codex verification; no commit hash is recorded
  before it exists.

## T007-C-05 — Final Pre-Commit Verification

- **Date:** 2026-11-22
- **Verification source:** Codex executed the following final offline checks.
  These results are separate from the owner-run verification recorded in
  T007-C-04C.
- `uv run --locked pytest tests/retrieval/test_public_service.py`
  - **Actual outcome:** PASS; exit `0`; 19 passed in 0.49 seconds.
- `uv run --locked pytest tests/retrieval/test_public_contracts.py
  tests/retrieval/test_errors.py`
  - **Actual outcome:** PASS; exit `0`; 37 passed in 0.46 seconds.
- `PYTHONPATH=. uv run --locked pytest tests/retrieval/test_validation.py`
  - **Actual outcome:** PASS; exit `0`; 30 passed in 0.55 seconds.
- `PYTHONPATH=. uv run --locked pytest tests/retrieval/test_core_offline.py
  tests/retrieval/test_v2_bm25.py`
  - **Actual outcome:** PASS; exit `0`; 13 passed in 0.33 seconds.
- `PYTHONPATH=. uv run --locked pytest tests/retrieval -q
  --ignore=tests/retrieval/test_postgres_core.py
  --ignore=tests/retrieval/test_postgres_lookup.py
  --ignore=tests/retrieval/test_phase_c_pipeline.py`
  - **Actual outcome:** PASS; exit `0`; 144 passed in 0.81 seconds.
- `uv run --locked ruff check --no-cache src/sciscope/retrieval
  tests/retrieval/test_public_service.py`
  - **Actual outcome:** PASS; exit `0`; all checks passed.
- `uv run --locked ruff format --check src/sciscope/retrieval
  tests/retrieval/test_public_service.py`
  - **Actual outcome:** PASS; exit `0`; 14 files already formatted.
- `uv run --locked mypy src/sciscope/retrieval`
  - **Actual outcome:** PASS; exit `0`; no issues found in 13 source files.
- `git diff --check`
  - **Actual outcome:** PASS; exit `0`; no output or errors.
- **Final scope before staging:**
  `docs/person3/FEATURE_007_T007_TEST_LOG.md`,
  `src/sciscope/retrieval/__init__.py`,
  `src/sciscope/retrieval/service.py`, and
  `tests/retrieval/test_public_service.py` only.
- **Acceptance:** Final T007-C owner acceptance was already explicitly
  authorized before this verification.
- **Limitations:** PostgreSQL-backed integration tests and live embedding
  provider behavior were not exercised. The typed transient provider-error
  contract remains deferred.
- **Commit:** Pending staging and commit at the time of this entry.
