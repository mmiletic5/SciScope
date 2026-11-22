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
