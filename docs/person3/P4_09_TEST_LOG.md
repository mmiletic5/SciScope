# P4-09 Shared Retrieval Integration — Chronological Test Log

## Purpose and logging rules

This is the append-only-in-practice chronology for Feature 012 / P4-09. Add new entries at the end. Never erase or rewrite prior failures, blocked attempts, corrections, command outputs, or decisions. Correct a factual error in a new dated entry that links back to it.

- Separate **Codex-run** checks from **owner-run** checks. An assistant result is not independent human verification.
- Record exact command, date, platform/runtime, exit status, meaningful output, and scope. Use `PASS`, `FAIL`, `BLOCKED`, or `NOT RUN` honestly.
- Record failed attempts before corrections. Do not replace a failed/blocked line with a later passing result.
- Record owner/reviewer statements only when actually received; otherwise use `PENDING` or `NOT RECORDED`.
- Every implementation increment gets RED (behavior test fails for the missing behavior), smallest GREEN implementation, automated/static/regression results, independent Person 3 verification, affected-owner review, and an explicit decision. The planning increment has no artificial RED/GREEN test.
- Database entries must include safe identity and read-only evidence but never a connection string, password, token, or other secret.
- Record commit hashes only after commits exist and are authorized. This task creates no commit.
- A task is not complete without automated evidence and explicit human acceptance. Feature completion additionally requires the applicable reviews, clean CI/PR integration, and synchronized evidence/backlog state.

## Feature identity and baseline

- **Feature:** 012 — Shared Retrieval Service Integration (P4-09)
- **Owner:** Person 3 — Backend & AI
- **Branch:** `feature/p4-09-backend-retrieval-integration`
- **Baseline HEAD:** `7a8233bd029ba666274d8ecd902a84bfe6cf8fe6`
- **Feature 011:** accepted and merged; fake-only scope remains unchanged unless a reviewed extension is approved.
- **Feature 007:** accepted and merged; facade acceptance does not select Person 3 application version/mode.
- **Current state:** DRAFT / PLANNED. Specification and plan approval, all implementation tasks, database access, reviews, human verification, and final acceptance are pending.
- **Current retrieval selection:** `retrieval.v1` + `dense` is the leading measured candidate; final activation remains PENDING approved comparative evidence, compatible explicitly configured query embedder, and explicit Person 3 acceptance.
- **Current commit:** NONE.

## Status definitions

- **DRAFT** — artifacts or proposal are under review; not approved for dependent implementation.
- **PLANNED** — task is approved for planning but no implementation evidence is claimed.
- **RED** — the intended behavior test ran and failed because the specified behavior is absent.
- **GREEN** — the approved behavior implementation and intended test passed.
- **PASS / FAIL** — an automated check completed and passed / completed and reported a failure; retain both attempts.
- **BLOCKED** — the intended check could not run because a concrete prerequisite/authorization is absent.
- **NOT RUN** — no attempt was made.
- **ACCEPTED / REJECTED** — explicit human decision, recorded with decision-maker, date, and scope.

## Chronological entries

### 2026-11-22 — Planning and evidence setup (DRAFT)

- **Increment:** T012-A planning package; no implementation authorization.
- **Git baseline:** `7a8233bd029ba666274d8ecd902a84bfe6cf8fe6` on `feature/p4-09-backend-retrieval-integration`; preflight was clean.
- **Scope:** Create Feature 012 research/spec/plan/tasks, built-in Spec Kit requirements checklist, this log, and planning-only status notes in `PROJECT_TODO.md` and `EVIDENCE.md`.
- **Changed files:** To be confirmed after final diff inspection. No `src/` or `tests/` files are in scope.
- **RED behavior tests:** NOT RUN — planning/documentation increment; no artificial behavior test.
- **GREEN implementation/tests:** NOT APPLICABLE — no application implementation.
- **Automated documentation/static checks:** PENDING final execution and recording below.
- **Spec Kit quality analysis:** PENDING final cross-artifact review. The repository analysis skill is read-only; no generated analyzer output is asserted unless the tool actually runs.
- **Mode evidence reviewed:** Existing Person 2 five-question development comparison is summarized in `specs/012-shared-retrieval-integration/research.md`. It is insufficient to claim a reliable overall winner; no benchmark was run in this task. Application mode remains PENDING.
- **Database:** NOT CONNECTED. No migration, ingestion, query, or provider call.
- **Person 2 review:** PENDING.
- **Person 4 review:** PENDING.
- **Person 1 provenance review:** PENDING if mapping changes source/provenance meaning.
- **Person 3 independent manual verification:** PENDING.
- **Explicit decision:** PENDING — DRAFT; no ACCEPTED or REJECTED decision recorded.
- **Commit:** NONE.
- **Remaining risks:** Metadata field semantics/version compatibility, retrieval version/mode selection, per-error HTTP mapping, embedder ownership, and app/Engine lifecycle require recorded decisions.

### 2026-11-22 — T012-A delegated design decisions (DRAFT)

- **Owner-reported delegation:** Person 2 (Retrieval) and Person 4 (Frontend) told the Person 3 owner that Person 3 may make technical choices within this feature, provided the solution is correct and retrieval mode/version decisions use the best available measured results.
- **Delegation boundary:** This is owner-reported delegation only. Neither person reviewed or approved a specific implementation or test result. Person 3 is responsible for validation and approval. Delegation does not waive required affected-owner review of concrete shared-contract changes/results, independent verification, or explicit human acceptance.
- **D012-01 — Retrieval:** Adopted v1 dense as the leading measured candidate from the existing Person 2 comparison: it tied v1 hybrid on Recall@10 (0.875) and MRR@10 (0.521), with lower median latency (23.462 ms versus 162.734 ms). The five-question evidence does not establish a reliable general winner. Final application activation is PENDING approved comparative evidence, a compatible explicitly configured query embedder, and explicit Person 3 acceptance. v1 lexical is allowed only for a separately authorized PostgreSQL wiring smoke test; it is not the application default. No implicit mode fallback.
- **D012-02 — Metadata:** Adopt component-origin metadata for retrieval and answer provider, with test-data/environment status separate. Preserve accepted Feature 011 fake-only response values and behavior. Verify existing DTO and frontend compatibility before selecting wire fields. If additive fields break strict clients, prepare a separately approved versioned contract.
- **D012-03 — Errors:** Adopt the draft sanitized mapping where compatible with existing contracts; preserve typed retryability. Server-owned invalid retrieval configuration is a server/internal failure, not caller `422`. Do not expose private exception details. Exact HTTP compatibility remains to be checked before implementation.
- **D012-04 — Lifecycle:** Adopt explicit composition-root ownership: the creator owns Engine disposal after checked-out connections return; adapters do not dispose borrowed engines; imports, app construction, and fake-only paths do not initialize DB/providers implicitly. Validate against actual composition during implementation review.
- **D012-05 — Provenance:** Preserve exact source identifiers, DOI, locator, text, title, delivery digest, source-contract version, and corpus version without reinterpretation or synthesis. Request Person 1 review only if source meaning or upstream source contract changes.
- **Changed files:** `research.md`, `spec.md`, `plan.md`, `tasks.md`, `checklists/requirements.md`, and this log; `PROJECT_TODO.md` and `EVIDENCE.md` reconciliation is pending in this entry's continuation.
- **Automated checks / tests / database / provider:** NOT RUN at time of this entry. No source/test changes, benchmark, database connection, migration, ingestion, embedding, or provider call.
- **Person 2 / Person 4 specific implementation or test review:** NOT PERFORMED / NOT CLAIMED. The delegation statement is not review approval.
- **Person 1 review:** Not required unless provenance meaning/upstream contract changes.
- **Person 3 validation and explicit decision:** PENDING; no feature acceptance is inferred.
- **Commit:** NONE.
- **Remaining gates:** DRAFT spec/plan approval; approved comparative evidence; compatible configured query embedder; metadata/HTTP compatibility verification; concrete affected-owner reviews; independent human verification; explicit Person 3 acceptance.

## Planned increment record template

Append one copy for each T012-B through T012-H increment; retain all outcomes and corrections.

### YYYY-MM-DD — T012-? [short name] (PLANNED)

- **Owner / reviewers:**
- **Git baseline and branch:**
- **Spec requirement / task IDs:**
- **Scope and changed files:**
- **RED command, platform, exit code, actual failure:**
- **GREEN implementation, command, platform, exit code, actual result:**
- **Static/regression commands and results:**
- **Failures and corrections (chronological):**
- **Codex-run evidence:**
- **Owner-run exact command, date/platform/runtime, actual observation:**
- **Manual actions and acceptance criteria inspected:**
- **Database identity/read-only evidence (if authorized; no credentials):**
- **Retrieval-mode evaluation evidence (if applicable):**
- **Person 2 review, scope, date, decision:**
- **Person 4 review, scope, date, decision:**
- **Person 1 review, scope, date, decision (if applicable):**
- **Person 3 explicit decision: ACCEPTED / REJECTED / PENDING, date and scope:**
- **Commit hash (only after authorized creation):**
- **Remaining risks and limitations:**

### 2026-11-22 — Spec Kit and documentation verification (DRAFT)

- **Increment:** T012-A planning package validation; no implementation authorization.
- **Git baseline and branch:** `7a8233bd029ba666274d8ecd902a84bfe6cf8fe6`, `feature/p4-09-backend-retrieval-integration`; rechecked after documentation work.
- **Changed files:** `specs/012-shared-retrieval-integration/research.md`, `spec.md`, `plan.md`, `tasks.md`, `checklists/requirements.md`, `docs/person3/P4_09_TEST_LOG.md`, `PROJECT_TODO.md`, and `EVIDENCE.md`. `.specify/feature.json` is ignored local Spec Kit state pointing to the feature directory. No `src/` or `tests/` files changed.
- **Spec Kit template resolution:** Initial read-only resolver attempt failed during PowerShell startup with a `System.IO.IOException` creating its user module directory inside the sandbox. The elevated read-only retry of `spec-template` succeeded (resolved content length 4,556). Read-only resolutions then succeeded for `plan-template` (3,520), `tasks-template` (9,135), and `checklist-template` (2,033).
- **Spec Kit setup/prerequisite command:** `pwsh -NoProfile -Command '& { & ./.specify/scripts/powershell/setup-plan.ps1 -Json; & ./.specify/scripts/powershell/setup-tasks.ps1 -Json; & ./.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireSpec -RequireTasks -IncludeTasks }'` — PASS, exit `0`. Feature directory resolved to `specs/012-shared-retrieval-integration`; setup reported existing plan and did not overwrite it. The setup-plan JSON `BRANCH` field fell back to `012-shared-retrieval-integration`; an independent `git branch --show-current` confirmed the actual branch remained `feature/p4-09-backend-retrieval-integration`. No branch switch occurred.
- **Whitespace attempt and correction:** Initial targeted `rg -n '[\t ]+$' specs/012-shared-retrieval-integration docs/person3/P4_09_TEST_LOG.md` found Markdown hard-break trailing spaces in new metadata lines. Those spaces were removed. A subsequent whole-file scan also found one pre-existing historical hard-break in `EVIDENCE.md:245`; it was not modified. Final targeted new-artifact scan returned exit `1` with no matches (no trailing whitespace).
- **Diff whitespace:** `git diff --check` — PASS, exit `0` for tracked changes. The targeted whitespace scan above covers newly created, untracked Markdown files.
- **Links/task structure:** One-off standard-library documentation audit — PASS, exit `0`: six Markdown artifacts checked; all internal relative links resolve; eight sequential unchecked task IDs `T001`–`T008`; no link failures.
- **Structural audit command:** `python3 -c 'import re; from pathlib import Path; files=[Path("specs/012-shared-retrieval-integration/research.md"),Path("specs/012-shared-retrieval-integration/spec.md"),Path("specs/012-shared-retrieval-integration/plan.md"),Path("specs/012-shared-retrieval-integration/tasks.md"),Path("specs/012-shared-retrieval-integration/checklists/requirements.md"),Path("docs/person3/P4_09_TEST_LOG.md")]; missing=[(str(f),h) for f in files for h in re.findall(r"\]\(([^)]+)\)",f.read_text(encoding="utf-8")) if not h.startswith(("http://","https://","mailto:")) and not (f.parent / h.split("#",1)[0]).exists()]; tasks=Path("specs/012-shared-retrieval-integration/tasks.md").read_text(encoding="utf-8"); ids=re.findall(r"^- \[ \] (T\d{3}) ",tasks,re.M); assert ids==[f"T{i:03d}" for i in range(1,9)],ids; assert len(ids)<=8; assert not missing,missing; print(f"PASS: {len(files)} Markdown files; internal links resolve; {len(ids)} unchecked sequential tasks; no link failures")'`.
- **Spec Kit consistency/requirements analysis:** No standalone `speckit-analyze` executable was exposed; the repository analyzer skill was applied as a read-only manual cross-artifact review. Spec scope aligns with plan and task traceability; all 24 functional requirements map to tasks, and the plan includes all 20 requested RED/GREEN test behaviors. The eight tasks are ordered behind the approval gate; database authorization is explicit. No unsupported server/deployment assumptions or held-out-question tuning were found. D012-01 through D012-05 remain intentionally unresolved and are recorded as blockers, not silently selected decisions. This is manual analysis, not generated analyzer output.
- **Tests/static tools:** Pytest, Ruff, and mypy — NOT RUN; this is a planning/documentation increment with no behavior test or Python change. No behavior tests were added.
- **Database/providers:** NOT CONNECTED / NOT CALLED. No benchmark, migration, ingestion, query embedder, paid provider, or Gemini call.
- **Owner-run verification:** NOT RUN. Person 2 and Person 4 reviews, applicable Person 1 review, and Person 3 independent acceptance are PENDING.
- **Explicit decision:** PENDING — DRAFT; no ACCEPTED or REJECTED decision recorded.
- **Commit:** NONE. No staging, commit, push, or merge.
- **Remaining risks:** Mode selection, HTTP metadata compatibility, public error mapping, and lifecycle ownership still require recorded approvals. The five-question evaluation is development-only and insufficient to establish a reliable general mode winner.

## Future independent verification checkpoints

Commands below are planned for use only after the corresponding tests exist and the approved task is authorized. They are not claimed as executed.

| Increment | Planned Windows PowerShell command | Human checkpoint |
| --- | --- | --- |
| T012-A | No behavior test. Review `specs/012-shared-retrieval-integration/{research,spec,plan,tasks}.md` and D012 decisions. | Person 2/4 and applicable Person 1 record review; Person 3 records spec/plan approval. |
| T012-B | `uv run --locked pytest tests/backend/test_retrieval_metadata.py -q` | Inspect component origins, execution, test-data states, and unchanged v1 fake-only behavior. |
| T012-C | `uv run --locked pytest tests/backend/test_retrieval_adapter.py -q` | Inspect exact request ID, mode/version forwarding, source fields, and corpus identity. |
| T012-D | `uv run --locked pytest tests/backend/test_question_api.py tests/backend/test_question_api_v2.py -q` | Inspect v2 error responses, retryability, request IDs, no-provider-execution metadata, and unchanged v1 shapes. |
| T012-E | `uv run --locked pytest tests/backend/test_app_factory.py tests/backend/test_retrieval_http_integration.py -q` | Inspect fake-only inertness and explicit resource ownership/disposal. |
| T012-F | `uv run --locked pytest tests/backend/ tests/retrieval/test_public_service.py tests/retrieval/test_public_contracts.py -q` | Inspect offline regression, fake provider outcomes, explicit mode forwarding, and no fallback. |
| T012-G | `uv run --locked pytest tests/retrieval/test_backend_adapter_postgres.py -q` | Only after separate DB authorization. Independently verify exact database identity, counts, read-only repeatable-read behavior, persisted provenance, determinism, and pre/post equality. Label Codex/Ubuntu separately from owner/Windows. |
| T012-H | Approved focused pytest/static commands finalized from actual changed paths; at minimum `git diff --check`. | Person 3 records final ACCEPTED or REJECTED; Person 2/4 and applicable Person 1 decisions are recorded separately. |

## PostgreSQL evidence template

- **Authorization reference/date:**
- **Runner/date/platform:**
- **Database name / role / PostgreSQL version:** `sciscope_test_005` / `sciscope` / expected 17
- **pgvector version / Alembic revision:** expected 0.8.7 / `f005_pgvector_foundation`
- **Active snapshot and corpus identity:**
- **Preflight counts:** expected 17 papers / 319 sections / 728 chunks / 728 vectors
- **Transaction isolation and read-only observation for each operation:**
- **Test command and actual outcome:**
- **Exact source fields compared:**
- **Postflight identity/counts and pre/post comparison:**
- **Writes/migrations/ingestion/provider calls:** expected none; record observed evidence
- **Any mismatch/failure and correction:**
- **Independent owner-run Windows result:**

## Retrieval-mode evaluation record template

- **Person 2 authorization/review:**
- **Dataset/relevance-label version and five IDs:**
- **Corpus/active snapshot identity:**
- **Compared distinct version/mode arms:**
- **Query embedder/configuration identity (if dense/hybrid):**
- **Filters, top-k, candidate pools, repetitions, runtime environment:**
- **Recall@K / Evidence Hit@K / applicable MRR, per-question and aggregate:**
- **Median/p95 retrieval latency:**
- **Repeated ordered-ID stability:**
- **Exact provenance verification:**
- **Failures, limitations, and why evidence is or is not sufficient:**
- **Person 2 explicit review/decision:**
- **Person 3 application setting or PENDING decision:**

### 2026-11-22 — T012-A documentation reconciliation checks (DRAFT)

- **Scope:** Reconciled the delegated D012 design choices across the Feature 012 research, spec, plan, tasks, requirements checklist, this log, `PROJECT_TODO.md`, and `EVIDENCE.md`. No source or test files changed.
- **Changed files:** `specs/012-shared-retrieval-integration/research.md`, `spec.md`, `plan.md`, `tasks.md`, `checklists/requirements.md`, `docs/person3/P4_09_TEST_LOG.md`, `PROJECT_TODO.md`, and `EVIDENCE.md`.
- **Documentation consistency audit:** PASS — one-off Python standard-library audit checked 8 Markdown files; all relative links resolve; D012-01 through D012-05 are present in the research/spec/plan/log/evidence decision artifacts. During audit, missing explicit D012-01 and D012-05 labels in plan.md were found and corrected before the passing rerun.
- **Stale-language scan:** PASS — targeted `rg` scan for superseded all-pending and approval statements returned no matches in the decision documentation (historical earlier planning entry in EVIDENCE.md remains intact and is followed by this later record).
- **Whitespace:** `rg -n '[\t ]+$' specs/012-shared-retrieval-integration docs/person3/P4_09_TEST_LOG.md` — exit 1, no matches. `git diff --check` — PASS, exit 0.
- **Tests/static checks:** NOT RUN; documentation-only change. No tests created or executed.
- **Database/providers/benchmarks:** NOT RUN / NOT CONNECTED / NOT CALLED.
- **Person 2 / Person 4 specific implementation or test review:** NOT PERFORMED / NOT CLAIMED. Owner-reported delegation is not an implementation or test review.
- **Person 3 explicit feature decision:** PENDING; no implementation or feature acceptance.
- **Commit:** NONE. No staging, commit, push, or merge.
- **Remaining gates:** DRAFT spec/plan approval; approved comparative evidence and compatible explicit query embedder before final application-mode activation; metadata/HTTP compatibility verification; applicable concrete owner reviews; independent human verification; explicit Person 3 acceptance.

### 2026-11-22 — Final contract and task-order correction (DRAFT)

- **Scope:** Documentation-only reconciliation following the final read-only contract audit. No application or test behavior was added or changed.
- **HTTP versioning:** The accepted closed fake-only `/api/v1/questions` success and error shapes are preserved exactly. `POST /api/v2/questions` is a DRAFT proposal for real retrieval, with a separate closed schema, component metadata, response-local citation validation, corpus identity, no-results behavior, and compatibility tests. It requires explicit approval before implementation or consumer migration.
- **Metadata semantics:** Each component records configured origin, actual execution, and its own test-data status. Empty retrieval and retrieval failure report the configured answer-provider but `executed: false`; provider failure reports provider execution truthfully without an invented answer or claim.
- **Task order:** The eight unchecked tasks are sequentially T001 approval, T002 internal metadata, T003 public adapter, T004 v2 HTTP/errors, T005 composition/lifecycle, T006 offline integration, T007 separately authorized PostgreSQL evidence, and T008 close-out.
- **Errors and composition:** Typed retrieval failures are proposed to use a dedicated v2 handler that preserves the actual retryable value and route-scoped request ID without private details. The repository has no approved production Engine-backed public-facade factory; an explicit composition root is a required later implementation dependency, and the private test helper is not a production API.
- **Checks at entry creation:** PENDING until the final documentation checks below are run. Pytest, Ruff, mypy, benchmarks, databases, and providers remain NOT RUN.
- **Reviews / decision:** Person 2 and Person 4 delegation remains owner-reported only. No specific review, acceptance, or task completion is claimed. Person 3 formal spec/plan approval remains PENDING.
- **Commit:** NONE. No staging, commit, push, or merge.

### 2026-11-22 — Final contract and task-order documentation checks (DRAFT)

- **Scope and baseline:** Checked the eight Feature 012 planning artifacts on `feature/p4-09-backend-retrieval-integration` at `7a8233bd029ba666274d8ecd902a84bfe6cf8fe6`. The checked worktree contains only the expected Feature 012 planning/evidence files; the staging index is empty and no `src/` or `tests/` path is modified.
- **Checks:** `git diff --check` — PASS, exit `0`. `rg -n '[\\t ]+$' specs/012-shared-retrieval-integration docs/person3/P4_09_TEST_LOG.md PROJECT_TODO.md` — exit `1`, no trailing-whitespace matches. A standard-library link/task/contract audit — PASS: 8 documents checked, relative links resolve, exactly eight sequential unchecked IDs `T001`–`T008`, the v1/v2 decision is traceable, and all seven retrieval error codes occur in the plan.
- **Audit command:** `python3` standard-library audit over the Feature 012 documents, log, backlog, and evidence; it asserted the task order and the required v1/v2 and error-mapping terms. The full command was executed in the terminal for this entry.
- **Tests / services:** Pytest, Ruff, mypy, benchmarks, database access, migrations, ingestion, embedding/provider calls, and Gemini calls — NOT RUN.
- **Decision:** DRAFT / PENDING. These documentation checks do not approve T001, implementation, or the feature. No reviewer decision is inferred.
- **Commit:** NONE. No staging, commit, push, or merge.

### 2026-11-22 — T012-A formal planning approval (APPROVED)

- **Approver / date:** Person 3 — Backend & AI, 2026-11-22.
- **Decision and scope:** Feature 012 research, specification, plan, ordered T001–T008 workflow, and the authorization to begin T012-B offline RED/GREEN implementation are approved. T012-A required no artificial RED/GREEN behavior test. No application implementation has occurred in T012-A.
- **Restrictions preserved:** This approval does not authorize PostgreSQL access, retrieval benchmarks, live embedding/provider or Gemini calls, final retrieval-mode activation, changes to accepted v1 HTTP response shapes, automatic acceptance of later increments, push, or merge. The proposed v2 HTTP contract remains separately gated for concrete implementation and affected-owner review.
- **Evidence:** The prior dated entries retain the actual documentation checks: `git diff --check` passed; targeted trailing-whitespace scan had no matches; and the local link/task/contract audit passed. Pytest, Ruff, mypy, benchmarks, database access, and provider calls were not run.
- **Reviews and future verification:** Person 2 and Person 4 delegation remains owner-reported only; no concrete implementation or test approval is claimed. Each future increment still requires its recorded RED result, minimal GREEN change, Codex automated verification, independent Person 3 manual verification, applicable affected-owner review, explicit owner decision, chronological evidence, and an authorized focused commit.
- **T001 state:** COMPLETE as the approved planning/authorization gate. T002–T008 remain unchecked and unaccepted.
- **Initial commit:** `ea5e6f0` — `docs: approve Feature 012 integration plan`. The commit was amended only to retain this post-creation evidence; the final commit ID is reported from Git after the amendment.

### 2026-11-22 — Approval-record documentation checks (APPROVED)

- **Checks:** `git diff --check` — PASS, exit `0`. Local standard-library link/task/contract audit — PASS: 8 documents, all relative links resolved, ordered IDs `T001`–`T008`, only `T001` checked, all D012 decisions and seven retrieval errors traceable, v1 compatibility retained, and v2 separately gated.
- **Whitespace result:** `rg -n '[\\t ]+$' specs/012-shared-retrieval-integration docs/person3/P4_09_TEST_LOG.md PROJECT_TODO.md EVIDENCE.md` found only the known pre-existing historical Markdown hard break in `EVIDENCE.md:245`. No new Feature 012 or approval-record trailing whitespace was found; the historical line was preserved.
- **Scope result:** `git status --short`, tracked/untracked inspection, and source/test path checks showed only the eight approved planning/evidence files; no source/test modification or staged change existed before the authorized commit.
- **Tests / services:** NOT RUN. This is documentation verification only; it does not add a pytest, Ruff, mypy, benchmark, database, or provider result.

### 2026-11-22 — T002 / 012-B internal metadata RED tests (RED)

- **Git baseline / platform:** `503df57425cf939900a2f1322365362e9ea398e0` on `feature/p4-09-backend-retrieval-integration`; Linux `6.8.0-149-generic` x86_64, Python `3.10.12`, uv `0.13.9`.
- **Scope / changed files:** Added `tests/backend/test_retrieval_metadata.py` and appended this entry only. The test defines the approved internal `ComponentMetadata` and `QuestionMetadata` boundary expected by T012-B, covers the seven required scenarios, rejects unknown origins/non-boolean flags/missing component metadata, and includes a v1 fake-only route regression assertion. No production, API model, route, v2, database, or provider code changed.
- **Research/contract basis:** Before writing the test, Codex applied the repository solution-research and Google Python engineering guidance and inspected the approved Feature 012 artifacts plus the current question-service/API contracts and backend tests. The current implementation has only literal-true `MockMetadata`; `RetrievalOutcome` and `ProviderOutcome` each carry it independently, and `QuestionService` returns only retrieval metadata.
- **RED command, initial attempt:** `uv run --locked pytest tests/backend/test_retrieval_metadata.py -q` — BLOCKED before pytest by the sandboxed uv cache lock: `Could not create temporary file ... /home/maki/.cache/uv/... Read-only file system`. This was an environment restriction, not a test result.
- **RED command, actual run:** `uv run --locked pytest tests/backend/test_retrieval_metadata.py -q` — RED, exit `1`: 11 failed, 1 passed in `0.60s`. Every intended metadata scenario/validation failure identifies missing `QuestionMetadata` (`T012-B QuestionMetadata is not implemented`). The existing v1 fake-only route regression test passed. This demonstrates the approved contract behavior is absent rather than a fixture, syntax, or unrelated-import failure.
- **Existing regression baseline:** `uv run --locked pytest tests/backend -q --ignore=tests/backend/test_retrieval_metadata.py` — PASS, exit `0`: 67 passed in `0.75s`. No PostgreSQL-backed test, live provider, embedding provider, benchmark, migration, or ingestion was run.
- **Static checks and correction:** Initial `uv run --locked ruff check tests/backend/test_retrieval_metadata.py` found 12 E501 line-length errors and `uv run --locked ruff format --check tests/backend/test_retrieval_metadata.py` reported that the new test needed formatting. Only the new test file was reformatted manually; no behavior or production code changed. Rerun `uv run --locked ruff check tests/backend/test_retrieval_metadata.py && uv run --locked ruff format --check tests/backend/test_retrieval_metadata.py` — PASS: `All checks passed!` and `1 file already formatted`.
- **Repository verification:** `git diff --check` — PASS, exit `0`. Changed/untracked-path inspection shows only this test file and this append-only log entry; the index remains empty.
- **Independent owner verification:** PENDING. Planned Windows PowerShell RED command: `uv run --locked pytest tests/backend/test_retrieval_metadata.py -q`; the owner must record the actual output, platform, and decision separately.
- **GREEN implementation:** NOT STARTED. Expected later scope is the smallest internal component metadata/validation and question-service propagation change; accepted v1 HTTP models/routes and response shapes remain untouched.
- **Acceptance / commit:** Person 3 acceptance PENDING. T002 remains unchecked. Commit: NONE. No push, merge, database access, benchmark, live embedding/provider call, or Gemini call.
- **Remaining risks:** The RED suite intentionally names the proposed internal contract classes; GREEN must satisfy the approved semantics without turning real retrieval into mock metadata or fabricating provider execution/output. Concrete v2 HTTP work remains outside T012-B.

### 2026-11-22 — T002 RED correction: v1 error-envelope assertion (RED)

- **Failure and correction:** After adding the required v1 controlled-error regression assertion, the first rerun exposed a test expectation error: the accepted message is `The requested dependency is currently unavailable.`, not `A required dependency is unavailable.` The test expectation was corrected without changing production code.
- **Corrected RED command:** `uv run --locked pytest tests/backend/test_retrieval_metadata.py -q` — RED, exit `1`: 11 failed, 2 passed in `0.57s`. The two passing tests preserve existing v1 success and error contracts. The 11 failures remain the intended missing `QuestionMetadata` behavior, so the RED result is valid.
- **Corrected static checks:** `uv run --locked ruff check tests/backend/test_retrieval_metadata.py && uv run --locked ruff format --check tests/backend/test_retrieval_metadata.py` — PASS: `All checks passed!` and `1 file already formatted`.
- **State:** GREEN implementation remains NOT STARTED; independent owner RED verification, Person 3 acceptance, and a commit remain PENDING.

### 2026-11-22 — T002 independent Person 3 RED verification (OWNER-REPORTED)

- **Source / baseline:** Owner-provided terminal results on `feature/p4-09-backend-retrieval-integration` at `503df57425cf939900a2f1322365362e9ea398e0`.
- **Focused RED:** `uv run --locked pytest tests/backend/test_retrieval_metadata.py -q` — 11 failed, 2 passed in `0.53s`. The owner reports that all 11 failures identified the missing internal `QuestionMetadata` contract.
- **Existing backend baseline:** `uv run --locked pytest tests/backend -q --ignore=tests/backend/test_retrieval_metadata.py` — 67 passed in `0.68s`.
- **Owner runtime:** Operating system and Python version NOT RECORDED in the owner report.
- **Chronology state:** GREEN implementation NOT STARTED at this checkpoint. T002 acceptance PENDING. Commit: NONE. This owner-reported verification does not replace Codex-run evidence or approve implementation results.

### 2026-11-22 — T002 / 012-B internal metadata GREEN implementation (GREEN)

- **Baseline / Codex runtime:** `503df57425cf939900a2f1322365362e9ea398e0` on `feature/p4-09-backend-retrieval-integration`; Codex ran on Linux `6.8.0-149-generic` x86_64 with uv `0.13.9`. Host `python3` is `3.10.12`, but `pyproject.toml` requires Python `>=3.12,<3.13` and uv ran checks with Python `3.12.16`; no Python 3.10 result is treated as Python 3.12 evidence.
- **Owner RED evidence:** The preceding owner-reported entry records focused RED 11 failed / 2 passed in `0.53s` and existing backend 67 passed in `0.68s`; owner operating system and Python version remain NOT RECORDED.
- **Codex RED reconfirmation:** `uv run --locked pytest tests/backend/test_retrieval_metadata.py -q` — RED, exit `1`: 11 failed, 2 passed in `0.55s`, all missing `QuestionMetadata`. This followed the recorded earlier RED and did not replace it.
- **Implementation:** Changed `src/sciscope/question_service/contracts.py`, `validation.py`, and `service.py`, plus the authorized test/log. Added immutable `ComponentMetadata` (`configured_origin`, `executed`, `is_test_data`) and `QuestionMetadata` (`retrieval`, `answer_provider`), strict fail-closed validation through `ResponseContractFailure`, and question-service composition for answered/no-results outcomes. Existing literal-true `MockMetadata`, fake dependencies, v1 HTTP DTOs, routes, and app were not changed.
- **Validation boundary:** Malformed component metadata is accepted by frozen dataclass construction and rejected at the explicit internal validation boundary. The missing-component test also verifies constructor failure, and its wrong-component-type case verifies `ResponseContractFailure`; this is a minimal test correction that retains the negative assertion.
- **Focused GREEN:** `uv run --locked pytest tests/backend/test_retrieval_metadata.py -q` — PASS, exit `0`: 13 passed in `0.46s` (final run after the last type-boundary correction). The suite verifies success/no-results component propagation, provider non-invocation, failure-call attempt metadata objects, strict invalid-value rejection, unchanged v1 success/error responses, and absence of v2 route.
- **Backend regression:** `uv run --locked pytest tests/backend -q` — PASS, exit `0`: 80 passed in `0.66s` (final run). No PostgreSQL-backed test, live provider, embedding provider, benchmark, migration, ingestion, network/listener, or Gemini call was run.
- **Static checks / corrections:** First focused Ruff/mypy run found 8 undefined `ResponseContractFailure` references and import-order errors after the new defensive branches; the missing import/order were corrected. The second run had only one required blank line before the first class; it was corrected. Final `uv run --locked ruff check src/sciscope/question_service/contracts.py src/sciscope/question_service/validation.py src/sciscope/question_service/service.py tests/backend/test_retrieval_metadata.py && uv run --locked ruff format --check src/sciscope/question_service/contracts.py src/sciscope/question_service/validation.py src/sciscope/question_service/service.py tests/backend/test_retrieval_metadata.py` — PASS: `All checks passed!`, 4 files already formatted. Final `uv run --locked mypy src/sciscope/question_service/contracts.py src/sciscope/question_service/validation.py src/sciscope/question_service/service.py tests/backend/test_retrieval_metadata.py` — PASS: no issues in 4 source files.
- **v1 compatibility:** The two v1 assertions in the new test passed, and the full existing backend suite passed. Evidence covers v1 route existence, accepted success/error JSON, literal-true fake metadata, deterministic fake behavior through existing tests, and no v2 route. No broader guarantee beyond these executed checks is claimed.
- **Failure-path limitation:** Retrieval and provider failures still propagate their existing exceptions without a returned question outcome or HTTP failure metadata. The new internal metadata values can express the truthful attempted/not-invoked state when provided, but this increment does not implement the future v2 failure envelope or derive component metadata from hidden dependency configuration.
- **Repository / scope checks:** `git diff --check` — PASS before this append. Changed-path inspection showed only the three allowed question-service files, the allowed RED test, and this log; index empty. No secrets or dependency changes observed.
- **Independent owner GREEN verification:** PENDING. Person 3 must independently run the recorded focused/backend commands on their environment and record platform, Python version, results, and an explicit decision.
- **Acceptance / task state:** Person 3 T002 acceptance PENDING. T002 remains unchecked. Commit: NONE. No staging, commit, push, or merge.

### 2026-11-22 — T002 / 012-B — Independent Owner GREEN Verification and Formal Acceptance (ACCEPTED)

- **Approver / scope / authorization:** Person 3 — Backend & AI accepted T002 / 012-B, Internal Metadata Contracts and Validation Foundations, on 2026-11-22 and authorized one focused local commit. Acceptance covers immutable component/question metadata, strict fail-closed validation, independent origins/execution/test-data flags, answered/no-results propagation, v1 fake-only preservation, and approved offline RED/GREEN verification.
- **Owner verification source:** Owner-provided terminal results on `feature/p4-09-backend-retrieval-integration` at pre-commit HEAD `503df57425cf939900a2f1322365362e9ea398e0`. Owner Python runtime: `3.12.16`. Owner operating system and shell: NOT RECORDED.
- **Owner commands and results:** `uv run --locked pytest tests/backend/test_retrieval_metadata.py -q` — PASS, 13 passed in `0.38s`. `uv run --locked pytest tests/backend -q` — PASS, 80 passed in `0.68s`. `uv run --locked ruff check src/sciscope/question_service/contracts.py src/sciscope/question_service/validation.py src/sciscope/question_service/service.py tests/backend/test_retrieval_metadata.py` — PASS, `All checks passed!`. `uv run --locked ruff format --check src/sciscope/question_service/contracts.py src/sciscope/question_service/validation.py src/sciscope/question_service/service.py tests/backend/test_retrieval_metadata.py` — PASS, 4 files already formatted. `uv run --locked mypy src/sciscope/question_service/contracts.py src/sciscope/question_service/validation.py src/sciscope/question_service/service.py tests/backend/test_retrieval_metadata.py` — PASS, no issues in 4 source files. `git diff --check` — no error output reported; no independent owner exit code was supplied.
- **Paths / chronology:** The five expected T012-B paths are `contracts.py`, `validation.py`, `service.py`, `tests/backend/test_retrieval_metadata.py`, and this log. Earlier entries preserve the initial RED failures, uv cache restriction, test expectation correction, Codex RED reconfirmation, initial static failures, corrections, and Codex GREEN results.
- **Decision:** ACCEPTED — T012-B. T002 is complete. This does not authorize T012-C, v2 HTTP implementation, PostgreSQL access, retrieval mode activation/benchmarks, live embedding/provider or Gemini calls, or final Feature 012 acceptance.
- **Remaining limitation:** Retrieval/provider failures still propagate exceptions without a returned `QuestionOutcome` or v2 HTTP failure-metadata envelope. This is outside accepted T012-B scope and remains a dependency for later approved v2 HTTP/error integration.
- **Commit:** Authorized focused local commit pending final Codex verification. No push or merge authorized.

### 2026-11-22 — T003 / 012-C public RetrievalService adapter RED tests (RED)

- **Authorization / baseline:** Person 3 authorized T003 RED behavior-test work only. Baseline is `44a07b5ea9a39b1a09c8ad3ce387cfcd8fe3c867` on `feature/p4-09-backend-retrieval-integration`; the preflight found a clean worktree, empty index, checked T001/T002, unchecked T003–T008, no adapter module, and no changes to accepted v1 HTTP files.
- **Codex runtime:** Linux `6.8.0-149-generic` x86_64; uv `0.13.9`; `uv run --locked python --version` reported Python `3.12.16`.
- **Research and contract inspection:** Applied the repository solution-research and Google Python engineering guidance before tests. Inspected Feature 012 research/spec/plan/tasks/checklist, Feature 007 public contracts/tests, Feature 011 question-service contracts/validation/service/fakes, and T012-B metadata tests. Public adapter inputs use exported `sciscope.retrieval.RetrievalService.retrieve(RetrievalRequest) -> RetrievalResponse`; `RetrievalRequest` has explicit `contract_version`, `request_id`, `query_text`, `mode`, `top_k`, optional `RetrievalFilters`, and optional `RankingOptions`. Public results expose exact source fields and `CorpusIdentity` exposes the three required provenance values.
- **Scope / test coverage:** Added `tests/backend/test_retrieval_adapter.py` only. The 17 collected cases use real immutable public DTOs and an injected deterministic public-facade spy. They specify one-call explicit request forwarding; exact evidence/corpus mapping; response-ID/configuration mismatch rejection; empty result mapping with truthful real retrieval execution metadata and no fabricated provider metadata; duplicate/empty malformed public response rejection; wrong runtime DTO rejection; missing/invalid version/mode/top-k/filter/ranking failure without fallback; and inert injected construction. No private retrieval-core type, database, embedder, answer provider, network, listener, or HTTP route is used.
- **RED command / initial result:** `uv run --locked pytest tests/backend/test_retrieval_adapter.py -q` — RED, exit `1`: 17 failed in `0.32s`. The tests collected and constructed public DTOs, then each required the absent planned `sciscope.question_service.retrieval_adapter` module. This is an implementation-absence failure, not a syntax, fixture, import-of-private-core, database, or provider failure.
- **Test-only corrections:** Initial focused Ruff found 7 E501 errors and format check required formatting; initial mypy found 14 dynamic-boundary attribute errors because runtime-loaded future adapter values were typed as `object`. Corrected only the test's line wrapping and annotated the runtime lookup boundary as `Any`; no behavior or production code changed. A follow-up Ruff check found one remaining E501 docstring; it was corrected. The final RED rerun remained 17 failed in `0.27s` for the same missing adapter module.
- **Final RED command / result:** `uv run --locked pytest tests/backend/test_retrieval_adapter.py -q` — RED, exit `1`: 17 failed in `0.27s`; all failures are `ModuleNotFoundError: No module named 'sciscope.question_service.retrieval_adapter'`. No case passed unexpectedly. The behavior groups remain separately inspectable in the collected test functions and parametrized cases; GREEN must exercise their downstream assertions, not merely provide module/class names.
- **Offline regression baselines:** `uv run --locked pytest tests/backend -q --ignore=tests/backend/test_retrieval_adapter.py` — PASS, exit `0`: 80 passed in `0.84s`. `uv run --locked pytest tests/retrieval/test_public_service.py tests/retrieval/test_public_contracts.py tests/retrieval/test_errors.py -q` — PASS, exit `0`: 66 passed in `6.26s`. No PostgreSQL-backed test was run.
- **Static and repository checks:** Final `uv run --locked ruff check tests/backend/test_retrieval_adapter.py` — PASS, `All checks passed!`; `uv run --locked ruff format --check tests/backend/test_retrieval_adapter.py` — PASS, `1 file already formatted`; `uv run --locked mypy tests/backend/test_retrieval_adapter.py` — PASS, `Success: no issues found in 1 source file`. `git diff --check` is pending the final log append rerun.
- **Operations not run:** PostgreSQL access, retrieval benchmark, migration, ingestion, embedding-provider call, live answer-provider call, Gemini call, API v2 work, and GREEN adapter implementation — NOT RUN.
- **Reviews / acceptance:** Independent Person 3 RED verification PENDING. Person 2 concrete public-adapter boundary review PENDING. GREEN implementation NOT STARTED. Person 3 T003 acceptance PENDING. T003 remains unchecked. Commit: NONE.
- **Remaining ambiguity / limitation:** The public `RetrievalResponse` constructor validates collection types but does not itself reject duplicate chunk IDs or blank source/provenance strings; the approved adapter must provide that fail-closed mapping validation. The exact adapter settings class and exception type remain test-specified implementation details pending the required Person 2 boundary review; no HTTP status/error mapping is asserted here because that belongs to T012-D.

### 2026-11-22 — T003 / 012-C RED post-entry repository check

- **Repository check:** `git diff --check` — PASS, exit `0`, after the RED evidence append. Changed-path inspection confirms only `tests/backend/test_retrieval_adapter.py` (untracked) and this append-only log are changed; the index remains empty.

### 2026-11-22 — T003 / 012-C RED contract-coverage correction

- **Correction:** The forwarding assertion now supplies an already-valid question so it proves unchanged forwarding without conflating it with the public request DTO's documented whitespace canonicalization. The response-consistency group now separately covers unsupported response contract version and unexpected response mode.
- **Corrected RED command:** `uv run --locked pytest tests/backend/test_retrieval_adapter.py -q` — RED, exit `1`: 18 failed in `0.37s`. Each collected case still reaches the absent planned `sciscope.question_service.retrieval_adapter` module; no fixture/setup failure was introduced.
- **Corrected static checks:** `uv run --locked ruff check tests/backend/test_retrieval_adapter.py && uv run --locked ruff format --check tests/backend/test_retrieval_adapter.py && uv run --locked mypy tests/backend/test_retrieval_adapter.py` — PASS: `All checks passed!`; `1 file already formatted`; `Success: no issues found in 1 source file`.

### 2026-11-22 — T003 / 012-C independent RED verification and boundary confirmation (OWNER-REPORTED)

- **Owner RED verification:** Person 3 reported `uv run --locked pytest tests/backend/test_retrieval_adapter.py -q` on `feature/p4-09-backend-retrieval-integration` at `44a07b5ea9a39b1a09c8ad3ce387cfcd8fe3c867`: 18 failed in `0.31s`, each identifying the missing `sciscope.question_service.retrieval_adapter` module. Owner operating system and Python version: NOT RECORDED.
- **Owner-reported baselines:** `uv run --locked pytest tests/backend -q` — 80 passed in `0.67s`; `uv run --locked pytest tests/retrieval/test_public_service.py tests/retrieval/test_public_contracts.py tests/retrieval/test_errors.py -q` — 66 passed in `0.54s`.
- **Person 2 boundary confirmation:** Owner-reported only. Person 2 confirmed use of only public `sciscope.retrieval` exports; internal `RetrievalAdapterSettings`; retrieval-only adapter metadata; exact source/provenance preservation; fail-closed malformed-response handling; and no automatic retrieval-mode activation. No direct review transcript or Person 2 test execution is claimed.
- **Chronology state:** GREEN implementation NOT STARTED at this checkpoint. T003 acceptance PENDING. Commit: NONE.

### 2026-11-22 — T003 / 012-C metadata assertion correction (RED)

- **Test-only correction:** The successful-retrieval assertion incorrectly accessed `outcome.metadata.retrieval`, which would require `QuestionMetadata`. It now asserts direct retrieval-only `ComponentMetadata` fields: `configured_origin`, `executed`, and `is_test_data`, matching the approved adapter boundary. No coverage was removed; the empty-result assertions already used the direct component shape.
- **State:** Focused RED rerun pending. GREEN implementation remains NOT STARTED at this checkpoint.

### 2026-11-22 — T003 / 012-C initial GREEN correction

- **Initial GREEN command:** `uv run --locked pytest tests/backend/test_retrieval_adapter.py -q` — FAIL, exit `1`: 17 passed, 1 failed in `0.10s`.
- **Failure:** The empty-result test compared internal `CorpusProvenance` directly to public `CorpusIdentity`. The mapping correctly preserved all values, but these deliberately distinct dataclass types are not equal by type.
- **Test-only correction:** Replaced the invalid object-equality assertion with exact `delivery_digest`, `source_contract_version`, and `corpus_version` equality assertions. No production behavior was changed; exact empty-result provenance coverage is retained.

### 2026-11-22 — T003 / 012-C public RetrievalService adapter GREEN implementation (GREEN)

- **Baseline / Codex runtime:** `44a07b5ea9a39b1a09c8ad3ce387cfcd8fe3c867` on `feature/p4-09-backend-retrieval-integration`; Linux `6.8.0-149-generic` x86_64; uv `0.13.9`; uv Python `3.12.16`.
- **Owner evidence / boundary review:** The preceding owner-reported entry records the independent 18-failure RED result and 80/66 regression baselines. Person 2's confirmation is owner-reported only: public retrieval exports only, internal settings, retrieval-only adapter metadata, exact provenance, fail-closed mapping, and no automatic mode activation. No Person 2 test execution or direct review transcript is claimed.
- **Metadata test correction and Codex RED:** The successful-path metadata assertion was corrected from `QuestionMetadata` access to direct retrieval-only `ComponentMetadata` fields. Codex reconfirmed `uv run --locked pytest tests/backend/test_retrieval_adapter.py -q` — RED, exit `1`: 18 failed in `0.43s`, all due to the absent adapter module.
- **Implementation / changed paths:** Added `src/sciscope/question_service/retrieval_adapter.py`; updated the authorized adapter test and this log only. `RetrievalAdapterSettings` is frozen and slots-based, validates an explicit version/mode/top-k/filter/ranking configuration through public `RetrievalRequest` validation, and requires explicit real retrieval component metadata. `PublicRetrievalAdapter` stores an injected public facade, builds one public request, validates the public response before any partial mapping, preserves exact evidence/corpus fields, and returns retrieval-only `ComponentMetadata` with `executed=True`. It creates no database engine/session, embedder, answer provider, route, credentials lookup, or mode/version fallback.
- **Response boundary:** The adapter requires an exact public `RetrievalResponse`, matching request ID/version/mode/top-k/filter/ranking metadata, complete nonblank corpus/evidence source values, unique chunk IDs, and valid empty-result warnings. Invalid mapping data raises `ResponseContractFailure`; public facade errors continue to propagate for later T012-D handling.
- **Focused GREEN:** `uv run --locked pytest tests/backend/test_retrieval_adapter.py -q` — PASS, exit `0`: 18 passed in `0.09s`.
- **Backend regression:** `uv run --locked pytest tests/backend -q` — PASS, exit `0`: 98 passed in `0.94s`.
- **Public retrieval regression:** `uv run --locked pytest tests/retrieval/test_public_service.py tests/retrieval/test_public_contracts.py tests/retrieval/test_errors.py -q` — PASS, exit `0`: 66 passed in `0.65s`.
- **Static checks / correction:** Initial focused static command found one E501 line-length error in `retrieval_adapter.py:186`; the only correction split that condition across lines. Rerun `uv run --locked ruff check src/sciscope/question_service/retrieval_adapter.py tests/backend/test_retrieval_adapter.py && uv run --locked ruff format --check src/sciscope/question_service/retrieval_adapter.py tests/backend/test_retrieval_adapter.py && uv run --locked mypy src/sciscope/question_service/retrieval_adapter.py tests/backend/test_retrieval_adapter.py` — PASS: `All checks passed!`; `2 files already formatted`; `Success: no issues found in 2 source files`.
- **Operations not run:** PostgreSQL access, retrieval benchmark, migrations, ingestion, embedding/provider calls, Gemini/live answer-provider calls, API v2 work, and production mode activation — NOT RUN.
- **Remaining gates:** Independent Person 3 GREEN verification PENDING. Person 3 T003 acceptance PENDING. T003 remains unchecked. Commit: NONE. The adapter provides no answer-provider metadata or complete `QuestionOutcome`; combining component metadata and HTTP error envelopes remains later approved work.

### 2026-11-22 — T003 / 012-C — Independent Owner GREEN Verification and Formal Acceptance (ACCEPTED)

- **Approver / decision / scope:** Person 3 — Backend & AI, 2026-11-22, explicitly **ACCEPTED** T003 / 012-C, Public RetrievalService Adapter, and authorized one focused local commit. Acceptance covers frozen `RetrievalAdapterSettings`, injected public facade, one explicit request per call, explicit version/mode/top-k/filter/ranking, exact evidence/corpus mapping, retrieval-only metadata, fail-closed validation, empty results, no mode fallback, inert DB/provider behavior, and preserved v1 behavior.
- **Owner verification source:** Owner-provided terminal results on `feature/p4-09-backend-retrieval-integration` at pre-commit HEAD `44a07b5ea9a39b1a09c8ad3ce387cfcd8fe3c867`. Owner Python: `3.12.16`; owner operating system and shell: NOT RECORDED.
- **Owner commands and results:** `uv run --locked pytest tests/backend/test_retrieval_adapter.py -q` — PASS, 18 passed in `0.05s`. `uv run --locked pytest tests/backend -q` — PASS, 98 passed in `0.62s`. `uv run --locked pytest tests/retrieval/test_public_service.py tests/retrieval/test_public_contracts.py tests/retrieval/test_errors.py -q` — PASS, 66 passed in `0.52s`. Focused Ruff lint — PASS, `All checks passed!`; Ruff format — PASS, 2 files already formatted; mypy — PASS, no issues in 2 source files. `git diff --check` produced no error output; no owner exit code was supplied.
- **Person 2 review status:** OWNER-REPORTED PERSON 2 CONFIRMATION only. The reported boundaries are public exports only, internal settings, retrieval-only metadata, exact source/corpus provenance, fail-closed malformed-response handling, and no automatic mode activation. No direct review transcript, implementation-detail approval beyond that report, or Person 2 test result is claimed.
- **Chronology / corrections:** Prior entries retain the initial 18-failure RED, the retrieval-only metadata test correction, the initial 17-pass/1-fail corpus-type assertion, the correction to exact field comparison, Codex RED, and Codex GREEN/static results.
- **Changed paths:** `src/sciscope/question_service/retrieval_adapter.py`, `tests/backend/test_retrieval_adapter.py`, and this log. Task/evidence close-out updates are added under the authorized commit scope.
- **Limitations retained:** The adapter returns only retrieval `ComponentMetadata`; full `QuestionMetadata` composition, end-to-end real-adapter `QuestionService` integration, HTTP v2 error envelopes, and mapping public retrieval exceptions into approved v2 errors remain outside T012-C. Strict response warning/ranking validation needs later integration compatibility review. No final retrieval mode is selected or activated.
- **Decision / commit:** ACCEPTED — T003. T003 is eligible to be checked complete after final Codex verification. Commit: authorized focused local commit pending final Codex verification. T004–T008 and P4-09 remain incomplete.

### 2026-11-22 — T004 / 012-D versioned HTTP contract review and RED tests (RED)

- **Authorization / baseline:** Person 3 authorized contract review and offline RED behavior tests only for T004 / 012-D. Baseline is `86320097cbc09eac4785cc2ea8e2245c4d15084b` on `feature/p4-09-backend-retrieval-integration`. T001–T003 are complete; T004–T008 and P4-09 remain unchecked. No production implementation, staging, commit, push, merge, database access, benchmark, migration, ingestion, embedding provider, or live answer-provider call is authorized or performed.
- **Codex environment:** Linux `6.8.0-149-generic` x86_64; uv `0.13.9`; `uv run --locked python --version` reported Python `3.12.16`. The initial sandbox runtime check was blocked because uv could not create a cache lock on the read-only filesystem. The permitted elevated offline invocation completed; this environment evidence applies to Codex only, not independent owner verification.
- **Research and contracts inspected:** Applied the repository-required solution-research and Google Python engineering guidance before feature tests. The brief internal research inspected the approved Feature 012 artifacts, accepted Feature 011 API models/routes/app/tests, accepted T012-B/T012-C contracts, and the exported Feature 007 retrieval DTO/error contracts. No web research, dependency addition, or external service was used.
- **v1 compatibility facts:** `POST /api/v1/questions` remains the only registered question route. Its closed success key set is `api_version`, `request_id`, `workflow`, `status`, `answer`, `claims`, `evidence`, `corpus`, and `metadata`; its error key set is `api_version`, `request_id`, `error`, and `metadata`. v1 uses literal `api_version: "v1"` and `{"is_mock": true, "is_test_data": true}` metadata. The app factory stores injected dependencies inertly; it has no v2 route and does not initialize a retrieval engine, provider, or listener.
- **Proposed v2 review:** The Feature 012 documents propose a separately versioned, closed `POST /api/v2/questions` request compatible with v1 fields (`workflow`, `question`, optional `request_id`) while retaining retrieval settings as server-owned. Proposed answered output carries `api_version: "v2"`, workflow/status/answer, response-local claims and evidence, exact corpus identity, and separate retrieval/answer-provider `{configured_origin, executed, is_test_data}` metadata. Proposed no-results output has null answer, no claims/evidence, preserved corpus, and a configured but unexecuted provider. Proposed insufficient-evidence output has no answer or claims and preserves evidence. Citation identifiers must be unique and resolve only to evidence in the same response; membership does not establish scientific support.
- **Typed error review:** The proposed table maps `INVALID_REQUEST`, `UNSUPPORTED_CONTRACT_VERSION`, and `RETRIEVAL_INTERNAL_ERROR` to HTTP 500 / `internal_error` / `An internal error occurred.`; `CORPUS_NOT_LOADED`, `EMBEDDING_CONFIGURATION_MISMATCH`, `EMBEDDING_UNAVAILABLE`, and `DATABASE_UNAVAILABLE` to HTTP 503 / `retrieval_unavailable` / `The requested dependency is currently unavailable.`. Each typed `retryable` value and route-scoped request ID must be preserved. Existing controlled `DEPENDENCY_TIMEOUT` remains HTTP 504 / `dependency_timeout` / `The requested dependency timed out.` / retryable true. Caller-invalid request input remains 422; server-owned adapter configuration is not caller 422. No route may expose exception text, credentials, DSNs, SQL, vectors, paths, tracebacks, or private configuration.
- **Review gates and ambiguity:** Person 2 typed-retrieval error-boundary review is **PENDING**. Person 4 v2 HTTP request/response and frontend-compatibility review is **PENDING**. Prior Person 2 T012-C boundary confirmation and Person 4 technical delegation do not confirm either T012-D review. The v2 wire contract is explicitly labelled DRAFT and requires approval before GREEN implementation or consumer migration. The proposed documents do not specify component metadata values for validation that fails before dependencies are invoked; RED tests therefore assert only the stable 422 status for invalid v2 request bodies and do not invent an error metadata state. Final schema/error mapping approval remains required before implementation.
- **RED test file and scope:** Added only `tests/backend/test_question_api_v2.py`. It uses FastAPI `TestClient`, explicit in-memory retrieval/provider fixtures, and real public `RetrievalException` values. It covers proposed v2 answered, request validation/closed caller settings, no-results/provider-not-invoked metadata, insufficient evidence, all seven typed retrieval errors with retryability/request-ID/sanitization assertions, controlled timeout, and unchanged v1 success shape. It opens no database connection, initializes no engine/embedder/live provider, reads no credentials, and starts no listener.
- **Initial RED and correction:** `uv run --locked pytest tests/backend/test_question_api_v2.py -q` — FAIL, exit `1`: 14 failed, 1 passed in `0.68s`. The 14 failures were expected `404 Not Found` responses from the missing `/api/v2/questions` route; the v1 preservation assertion passed. Focused Ruff then found three E501 line-length errors in the new test only. The test-only correction split one context-manager setup and two docstrings; no behavioral assertion was weakened or removed.
- **Final RED:** `uv run --locked pytest tests/backend/test_question_api_v2.py -q` — FAIL, exit `1`: 14 failed, 1 passed in `0.95s`. Every failing proposed-v2 assertion still received `404 Not Found`, demonstrating missing v2 behavior rather than a fixture/import defect. The passing v1 assertion confirms the accepted v1 route remains intact.
- **Regression and static evidence:** `uv run --locked pytest tests/backend -q --ignore=tests/backend/test_question_api_v2.py` — PASS, exit `0`: 98 passed in `1.17s`. `uv run --locked pytest tests/retrieval/test_public_service.py tests/retrieval/test_public_contracts.py tests/retrieval/test_errors.py -q` — PASS, exit `0`: 66 passed in `0.80s`. `uv run --locked ruff check tests/backend/test_question_api_v2.py --no-cache && uv run --locked ruff format --check tests/backend/test_question_api_v2.py && uv run --locked mypy tests/backend/test_question_api_v2.py` — PASS, exit `0`: all checks passed, 1 file already formatted, and no mypy issues in 1 source file. `git diff --check` — PASS, exit `0` before this evidence entry.
- **Remaining gates:** GREEN implementation NOT STARTED. Independent Person 3 RED verification PENDING. Person 2 error-mapping review PENDING. Person 4 v2 contract review PENDING. T004 acceptance PENDING. Commit: NONE. Later T005 composition/lifecycle owns a production resource boundary; T006 owns broader end-to-end integration. T004 must not create or initialize either resource implicitly.

### 2026-11-22 — T004 / 012-D owner-reported RED verification and review confirmation

- **Owner verification source:** Person 3 reported independent offline execution on `feature/p4-09-backend-retrieval-integration` at `86320097cbc09eac4785cc2ea8e2245c4d15084b`. Owner operating system and shell are NOT RECORDED.
- **Owner RED and baselines:** `uv run --locked pytest tests/backend/test_question_api_v2.py -q` — 14 failed, 1 passed in `0.63s`; all 14 failures were HTTP 404 because `/api/v2/questions` did not exist, and the one pass covered existing v1 behavior. `uv run --locked pytest tests/backend -q --ignore=tests/backend/test_question_api_v2.py` — 98 passed in `0.69s`. `uv run --locked pytest tests/retrieval/test_public_service.py tests/retrieval/test_public_contracts.py tests/retrieval/test_errors.py -q` — 66 passed in `0.52s`. Focused Ruff lint, format, and mypy were owner-reported PASS; the owner reported no exit code for these commands.
- **Affected-owner review provenance:** Person 2 confirmed the proposed typed retrieval error mapping and boundary, OWNER-REPORTED only. Person 4 confirmed the proposed v2 HTTP contract and frontend compatibility, OWNER-REPORTED only. No review transcript, review date, independent reviewer test execution, or acceptance of implementation/test results is claimed.
- **Authorization state:** This prompt authorizes only limited T004 GREEN work after preflight and contract checks. T004 acceptance remains PENDING. Commit: NONE.

### 2026-11-22 — T004 / 012-D minimal v2 boundary GREEN implementation (GREEN)

- **Baseline / Codex environment:** `86320097cbc09eac4785cc2ea8e2245c4d15084b` on `feature/p4-09-backend-retrieval-integration`; Linux `6.8.0-149-generic` x86_64; uv `0.13.9`; uv Python `3.12.16`.
- **Contract reconciliation:** The v2 request is closed and contains only `workflow`, `question`, and optional `request_id`; retrieval settings remain server-owned. The separate v2 success response contains `api_version`, request ID, workflow, status, answer, claims, evidence, corpus, and component metadata. Typed retrieval and controlled dependency failures include component metadata only after the route has actually begun dependency invocation. Early Pydantic request validation returns the closed v2 error envelope without metadata, because no component configuration/execution state is truthfully available before dependencies are invoked. This preserves the existing 422 validation behavior without inventing flags.
- **Implementation / changed production paths:** Added `src/sciscope/api/http_models_v2.py` with closed strict v2 request, success, component-metadata, and sanitized-error models. Added `src/sciscope/api/routes_v2.py` with the separately registered `POST /api/v2/questions` route, exact internal-outcome mapping, and request-local invocation tracking. Updated `src/sciscope/api/app.py` only to accept explicit `v2_metadata`, register v2 only when that configuration is supplied, and branch v2 validation/dependency/typed-retrieval/contract/unexpected errors without changing v1 envelopes. No retrieval core, question-service contract/service/validation, provider, database, engine, credential, or mode selection code changed.
- **Request ID / error boundary:** Every v2 route stores the validated HTTP request ID before calling dependencies. The typed retrieval handler uses only this route-scoped ID, never `RetrievalException.request_id`. The added mismatch test raises `DATABASE_UNAVAILABLE` with `different-downstream-request-id` and verifies the public response uses `v2-request-001` and exposes neither the downstream ID nor the private message. The seven typed codes map as reviewed: `INVALID_REQUEST`, `UNSUPPORTED_CONTRACT_VERSION`, and `RETRIEVAL_INTERNAL_ERROR` to 500/`internal_error`; `CORPUS_NOT_LOADED`, `EMBEDDING_CONFIGURATION_MISMATCH`, `EMBEDDING_UNAVAILABLE`, and `DATABASE_UNAVAILABLE` to 503/`retrieval_unavailable`; typed retryability is copied exactly. Existing `DEPENDENCY_TIMEOUT` remains 504/`dependency_timeout`/retryable true.
- **Metadata and citation behavior:** Successes map validated `QuestionMetadata` exactly. Empty retrieval preserves corpus identity with retrieval executed true and provider executed false. The tracked wrappers record actual retrieval/provider calls before delegation, allowing typed retrieval failure to report retrieval true/provider false and provider failure to report both true. Response-contract failures omit execution metadata rather than guess the stage. Existing validation rejects unknown or duplicate citations, duplicate evidence IDs, malformed evidence, and malformed claims; v2 returns sanitized `response_contract_failure` without an answer when this occurs. Citation membership is never treated as proof of scientific correctness.
- **Test additions / correction:** Extended only `tests/backend/test_question_api_v2.py` with the requested downstream request-ID mismatch, retrieval failure/provider-not-invoked state, provider failure after invocation, and nonlocal citation rejection. The test helper now explicitly supplies v2 component configuration, which is required before v2 route registration. Initial GREEN test execution passed: `uv run --locked pytest tests/backend/test_question_api_v2.py -q` — PASS, exit `0`: 19 passed in `0.78s`.
- **Failures and corrections:** Initial focused Ruff found one missing `create_app` argument description and four E501 line-length issues; corrected only docstring/wrapping text. The next format check identified one blank-line formatting correction in the new test. The next mypy run found missing proxy/helper return annotations and an unnecessary narrowed metadata identity check; corrected annotations and cast only. A final Ruff import-order finding was corrected mechanically. No test assertion, contract mapping, production behavior, or scope was weakened.
- **Final Codex verification:** `uv run --locked python --version && uv run --locked pytest tests/backend/test_question_api_v2.py -q` — PASS, exit `0`: Python `3.12.16`; 19 passed in `0.74s`. `uv run --locked pytest tests/backend/test_question_api.py tests/backend/test_question_api_v2.py -q` — PASS, exit `0`: 29 passed in `0.97s`. `uv run --locked pytest tests/backend -q` — PASS, exit `0`: 117 passed in `1.01s`. `uv run --locked pytest tests/retrieval/test_public_service.py tests/retrieval/test_public_contracts.py tests/retrieval/test_errors.py -q` — PASS, exit `0`: 66 passed in `0.58s`. `uv run --locked ruff check src/sciscope/api/app.py src/sciscope/api/http_models_v2.py src/sciscope/api/routes_v2.py tests/backend/test_question_api_v2.py --no-cache && uv run --locked ruff format --check src/sciscope/api/app.py src/sciscope/api/http_models_v2.py src/sciscope/api/routes_v2.py tests/backend/test_question_api_v2.py && uv run --locked mypy src/sciscope/api/app.py src/sciscope/api/http_models_v2.py src/sciscope/api/routes_v2.py tests/backend/test_question_api_v2.py` — PASS, exit `0`: all checks passed; 4 files already formatted; no mypy issues in 4 source files.
- **Limitations / gates:** PostgreSQL, retrieval benchmarks, migrations, ingestion, embedding providers, live answer providers, Gemini, production composition, and retrieval-mode activation are NOT RUN / NOT IMPLEMENTED. The route is registered only through explicit injected dependencies and component configuration; it does not create an engine, compose a public retrieval service, or select a mode. Independent owner GREEN verification is PENDING. T004 formal acceptance is PENDING. T004 remains unchecked. Commit: NONE.

### 2026-11-22 — T004 / 012-D final configuration-validation correction

- **Correction:** Final implementation review added fail-closed `validate_question_metadata(v2_metadata)` before registering `/api/v2/questions`; malformed explicit component configuration cannot expose the v2 route. This is limited to the supplied v2 configuration and does not alter v1 construction.
- **Final rerun:** `uv run --locked pytest tests/backend/test_question_api_v2.py -q` — PASS, exit `0`: 19 passed in `0.66s`. Combined v1/v2 — PASS: 29 passed in `1.03s`. Backend — PASS: 117 passed in `1.01s`. Public retrieval — PASS: 66 passed in `0.57s`. Focused Ruff/format/mypy and `git diff --check` — PASS: all checks passed; 4 files already formatted; no mypy issues in 4 source files.
- **State:** No acceptance, task completion, staging, commit, push, merge, database/provider operation, or mode activation occurred.

### 2026-11-22 — T004 / 012-D — Independent Owner GREEN Verification and Formal Acceptance (ACCEPTED)

- **Approver / decision / scope:** Person 3 — Backend & AI explicitly **ACCEPTED** T004 / 012-D on 2026-11-22 and authorized exactly one focused local commit. Accepted scope: separate strict `POST /api/v2/questions`, explicit validated `v2_metadata` registration, truthful component metadata, answered/no-results/insufficient-evidence flows, seven typed public retrieval mappings, controlled timeout, typed retryability, route-scoped request-ID authority, response-local citation validation, sanitized failures, preserved v1 behavior, and offline deterministic verification.
- **Owner verification source:** Owner-provided terminal results at pre-commit `86320097cbc09eac4785cc2ea8e2245c4d15084b` on `feature/p4-09-backend-retrieval-integration`; owner Python was `3.12.16`. Owner operating system and shell are NOT RECORDED. `uv run --locked pytest tests/backend/test_question_api_v2.py -q` — PASS, 19 passed in `0.58s`; combined v1/v2 API tests — PASS, 29 passed in `0.77s`; backend — PASS, 117 passed in `0.90s`; public retrieval — PASS, 66 passed in `0.53s`. Owner-reported focused Ruff lint/format/mypy passed; `git diff --check` had no error output, with no independently observed owner exit code supplied.
- **Affected-owner reviews:** OWNER-REPORTED PERSON 2 CONFIRMATION: typed public retrieval mapping, error boundary, retryability preservation, and sanitized failures. OWNER-REPORTED PERSON 4 CONFIRMATION: separate v2 request/response contract, frontend compatibility, and v1 preservation. No direct transcripts, reviewer environment, reviewer tests, dates, or further approval are claimed.
- **Chronology / implementation:** Earlier entries preserve the 14-failed/1-passed RED, owner RED, initial static corrections, Codex GREEN, final fail-closed configuration-validation correction, and separate owner/Codex evidence. Changed paths are `src/sciscope/api/app.py`, `src/sciscope/api/http_models_v2.py`, `src/sciscope/api/routes_v2.py`, `tests/backend/test_question_api_v2.py`, and this log; authorized close-out updates add `specs/012-shared-retrieval-integration/tasks.md` and `EVIDENCE.md`.
- **Limitations preserved:** v2 is an offline boundary with injected dependencies. Production PublicRetrievalAdapter/app composition and Engine lifecycle remain T005; cross-component offline integration remains T006; PostgreSQL verification remains separately authorized T007. No final mode selection/activation, database, benchmark, migration, ingestion, embedding, Gemini, or live answer-provider operation occurred. Early validation failures and response-contract/unexpected failures omit metadata rather than fabricate execution state. Citation membership does not establish scientific validity. T004 is accepted; T005–T008 and P4-09 remain incomplete. Commit pending final Codex verification.
