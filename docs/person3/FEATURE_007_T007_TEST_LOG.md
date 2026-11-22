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
