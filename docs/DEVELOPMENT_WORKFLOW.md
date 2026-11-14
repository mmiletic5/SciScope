# SciScope Development Workflow

This workflow applies to future SciScope features. It follows the repository
constitution and the official Spec Kit workflow configured in this repository.
It does not authorize implementation; each feature still needs explicit human
approval of its specification and plan.

## Small change track

Documentation, configuration, and single-file changes can proceed without Spec Kit
artifacts. Run a meaningful check for the change and request PR review.

## Feature size

Keep a feature to at most eight tasks. Use `spec.md`, `plan.md`, `tasks.md`, and a
short `research.md`. Add `data-model.md`, `quickstart.md`, or `contracts/` only
when the plan justifies them.

## Required feature artifacts

Keep feature artifacts in the feature directory created by Spec Kit. Before
implementation, that directory must contain:

- A short `research.md` including facts, unknowns, sources,
  alternatives, and the recommendation.
- `spec.md` with problem and scope, functional and non-functional requirements,
  acceptance criteria, edge cases, failure scenarios, and out-of-scope behavior.
- `plan.md` with architecture, dependencies, module boundaries, data contracts,
  decisions, error handling, test approach, risks, and integration points.
- `tasks.md` with stable task IDs, owners (`Person 1`, `Person 2`, `Person 3`,
  `Person 4`, or `TEAM`), deliverables, dependencies, tests, and verification
  steps. Preserve the official Spec Kit task format and checklist compatibility.

Use the repository's Spec Kit skills and templates. Do not replace their
feature-artifact workflow with entries in the master backlog.

## Stage A — Research

1. Invoke `$solution-research` before specifying a feature and again before
   finalizing a specification if its scope changes. Invoke it before writing
   feature behavior tests.
2. Inspect the relevant code, specifications, contracts, and dependencies.
3. Check authoritative sources when web access is available. Compare relevant
   approaches and record verified facts separately from assumptions and gaps.
4. Record findings, source links, limitations, a recommendation, and unresolved
   questions in `research.md` when the feature workflow uses that artifact.
5. Do not invent evidence, source details, compatibility claims, or answers.

## Stage B — Specification

1. Use `$speckit-specify` to create or update `spec.md`.
2. State the user problem, scope, functional and non-functional requirements,
   testable acceptance criteria, edge cases, failure scenarios, and exclusions.
3. Use Given/When/Then criteria where useful.
4. Use `$speckit-clarify` for essential missing decisions. Record answers in the
   specification; if a necessary decision is unresolved, stop that dependent
   work and ask the responsible team member.
5. Keep scientific claims and data requirements traceable to actual sources.

## Stage C — Plan

Use `$speckit-plan` to create `plan.md`. Address architecture, dependencies,
module boundaries, data contracts, technical decisions, error handling, tests,
risks, and integration points. Identify affected module owners and obtain their
agreement on shared contracts before dependent integration work.

## Stage D — Tasks and consistency

1. Use `$speckit-tasks` to create dependency-ordered tasks in `tasks.md`.
2. Give every task a stable ID, one of the approved owners, a concrete
   deliverable, dependencies, tests, and verification steps.
3. Keep at most eight tasks, each small enough to review and implement
   independently. Preserve the official Spec Kit task syntax and update
   `PROJECT_TODO.md` with corresponding master-backlog entries.
4. Run `$speckit-analyze` and resolve or document the reported inconsistencies
   before presenting the plan for approval.

## Stage E — Human approval gate

Present `spec.md`, `plan.md`, `tasks.md`, research findings, and open questions
to the team. Request explicit approval of the specification and plan. Stop
before implementation and before writing feature behavior tests until approval
is recorded. Research or a backlog entry is not implementation approval.

## Stage F — Test-driven implementation

After approval, work on one approved task at a time:

1. Invoke `$solution-research` before feature behavior tests.
2. Write a behavior test for an acceptance criterion.
3. Run it and record a RED result. Confirm it fails because the expected
   behavior is missing, not because setup or the test environment is broken.
4. Implement the smallest change that satisfies the approved task.
5. Run the test to GREEN, then refactor safely and repeat for the next task.
6. For documentation or configuration tasks, use meaningful validation checks
   instead of artificial unit tests.

Python changes must follow `$google-python-engineering`, the Google Python Style
Guide, repository configuration, and the approved plan. Keep automated tests
offline and prohibit paid AI calls. Use the fake provider by default; live
providers require explicit configuration.

## Stage G — Automated verification

Run checks relevant to the change and record the exact commands and important
output in `EVIDENCE.md`. Give each check one of these honest results:

- `PASS` — the command completed successfully and the intended check ran.
- `FAIL` — the intended check ran and reported a failure.
- `BLOCKED` — the check could not run because of a stated blocker.
- `NOT RUN` — the check was not attempted.

Never describe a skipped or unavailable check as passing. Keep previous attempts
and failures when adding later results.

## Stage H — Human verification

Once per feature, give the feature owner the exact Windows PowerShell commands,
expected results, manual actions, and relevant acceptance criteria. Ask the owner
to report the observed outcome and explicit acceptance or rejection. Stop with
the feature awaiting human verification; automated success and an assistant
report do not count as human confirmation.

## Stage I — Evidence and completion

Once per feature, after explicit human confirmation, update `EVIDENCE.md`, the feature
`tasks.md`, and `PROJECT_TODO.md`. Preserve the automatic and human evidence,
including failures and corrections. Mark a task `[x]` in the master backlog
and `DONE` in evidence only when its automated checks succeeded and the feature's
human acceptance is recorded. Otherwise leave it incomplete or blocked and state why.
Summarize remaining work and wait for the next instruction.

## Definition of Done

A task is done only when its approved scope is implemented; its acceptance
checks and relevant automated checks pass; the feature owner has explicitly
accepted the feature's manual verification; evidence is recorded; and feature
and master task states are synchronized. A feature is not done merely because
its code merges, its tests pass, or an assistant reports success.
