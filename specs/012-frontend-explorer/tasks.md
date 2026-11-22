# Tasks: Frontend Research Question Explorer

**Input**: Approved design documents in `specs/012-frontend-explorer/`

**Prerequisites**: Approved `spec.md` and `plan.md`; `research.md`, `data-model.md`, `contracts/`, and `quickstart.md`.

**Organization**: Eight sequential tasks. User Story 1 and User Story 2 must be completed, tested, and reach the Explorer demo-ready gate before any User Story 3 preview-screen task starts.

**Test-first rule**: For each behavior task, write the behavior test first, run it and record RED for the missing behavior, implement the smallest change, then rerun to GREEN. No task is complete without its stated automated verification. Do not use a live backend or paid AI call in automated tests.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Configure the existing frontend toolchain for the approved feature without implementing feature behavior.

- [ ] T001 Align frontend dependencies and configure test/check scripts in `frontend/package.json`, `frontend/package-lock.json`, `frontend/eslint.config.js`, and `frontend/src/test/setup.ts` (Owner: Person 4; Depends on: none; include the requested IBM Plex Fontsource packages, Vitest, Testing Library, user-event, jsdom, and `eslint-plugin-jsx-a11y`; align `eslint` and `@eslint/js` to compatible v9 releases; enable the plugin's recommended flat config; provide `test`, `lint`, `typecheck`, and `build` scripts; verify dependency resolution without peer overrides and run lint/typecheck/build).

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Define the frontend's typed contract and reusable synthetic fixtures before story work.

- [ ] T002 Add exact question-service request, success, error, and mock metadata types plus typed offline fixtures in `frontend/src/api/types.ts` and `frontend/src/api/fixtures.ts` (Owner: Person 4; Depends on: T001; `question` is trimmed length 1–2,000; `request_id` matches `^[A-Za-z0-9._:-]{1,128}$`; statuses are `answered`, `no_results`, and `insufficient_evidence`; error codes are `invalid_request`, `retrieval_unavailable`, `provider_unavailable`, `dependency_timeout`, `response_contract_failure`, and `internal_error`; evidence contains `chunk_id`, `doi`, `source_locator`, `passage`, `paper_title`; corpus contains `corpus_version`, `source_contract_version`, `delivery_digest`; metadata flags are booleans in the UI model and current fake values are both true; run `npm run typecheck`; no backend contract changes).

**Checkpoint**: Test tooling and contract types are ready. Proceed sequentially through the Explorer stories; do not start preview screens before T007 passes.

## Phase 3: User Story 1 - Ask a research question and inspect its sources (Priority: P1)

**Goal**: Complete the working question flow, including request handling, answer rendering, citations, source cards, and provenance.

**Independent Test**: With mocked service responses, submit a valid question and verify input, loading, answered output, citation/source mapping, DOI behavior, and corpus provenance.

### Tasks for User Story 1

- [ ] T003 [US1] Write API-client and request-ID behavior tests first in `frontend/src/api/client.test.ts` and `frontend/src/lib/requestId.test.ts`, covering all success statuses (`answered`, `no_results`, `insufficient_evidence`), known error envelopes, fetch rejection, HTTP 5xx HTML/empty/malformed/success-shaped bodies as retryable API-unreachable, malformed HTTP 200 and 4xx bodies as generic nonretryable errors, and timeout abort/message/reference; record RED, then implement `frontend/src/api/client.ts`, `frontend/src/lib/requestId.ts`, and any fixture/type refinements (Owner: Person 4; Depends on: T002; verify with `npm run test -- src/api/client.test.ts src/lib/requestId.test.ts`).
- [ ] T004 [US1] Write form behavior tests first in `frontend/src/features/explorer/QuestionForm.test.tsx` for trimmed 1–2,000 validation, counter, examples that fill without submitting, request submission, pending disablement, and loading announcement; record RED, then implement `frontend/src/features/explorer/QuestionForm.tsx` and initial/empty/loading integration in `frontend/src/features/explorer/ExplorerPage.tsx` (Owner: Person 4; Depends on: T003; verify with `npm run test -- src/features/explorer/QuestionForm.test.tsx`).
- [ ] T005 [US1] Write answer/citation/source behavior tests first in `frontend/src/features/explorer/AnswerView.test.tsx` and `frontend/src/lib/citations.test.ts` for claim order, duplicate and unknown IDs, uncited evidence, citation scroll/highlight, DOI safety, source-location disclosure, and provenance; record RED, then implement `frontend/src/lib/citations.ts`, `frontend/src/features/explorer/AnswerView.tsx`, and `frontend/src/components/SourceCard.tsx`/`CitationMarker.tsx` as needed (Owner: Person 4; Depends on: T004; verify with `npm run test -- src/features/explorer/AnswerView.test.tsx src/lib/citations.test.ts`).

**Checkpoint**: User Story 1 is independently tested and usable through the Research question view.

## Phase 4: User Story 2 - Understand empty, uncertain, synthetic, and failed results (Priority: P2)

**Goal**: Complete the remaining result/error states, retry rules, synthetic-data notice and badge behavior, and timeout presentation.

**Independent Test**: Use mocked responses for no-results, insufficient evidence, every error class, proxy-generated 5xx bodies, network rejection, and timeout; verify exact state copy, retry behavior, reference, question retention, and metadata-driven notice/badge behavior.

### Tasks for User Story 2

- [ ] T006 [US2] Write result-state and header tests first in `frontend/src/features/explorer/ResultStates.test.tsx` and `frontend/src/components/Header.test.tsx` for `no_results`, `insufficient_evidence`, each known error code, fetch rejection, HTTP 5xx without a valid error envelope, malformed HTTP 200/4xx responses, retry visibility, retained questions, response-scoped notice dismissal, badge default/either-true/both-false metadata rules, and the 30-second retryable timeout; record RED, then implement `frontend/src/features/explorer/ResultStates.tsx`, `frontend/src/components/StatusPanel.tsx`, `frontend/src/components/MockNotice.tsx`, and `frontend/src/components/Header.tsx` as needed (Owner: Person 4; Depends on: T003–T005; verify with `npm run test -- src/features/explorer/ResultStates.test.tsx src/components/Header.test.tsx`).

**Checkpoint**: User Stories 1 and 2 now cover all connected Explorer behavior. Complete T007 and pass its automated and owner demo checks before starting T008.

## Phase 5: Explorer Demo-Ready Gate (User Stories 1 and 2)

**Purpose**: Finish the Explorer shell and verify it is ready to demo before any preview-screen work.

- [X] T007 Finish the Explorer app shell and implement FR-015–FR-017 in `frontend/src/App.tsx`, `frontend/src/components/Navigation.tsx`, `frontend/src/styles/tokens.css`, `frontend/src/styles/global.css`, and `frontend/src/index.css`, including semantic landmarks, active-page announcement, polite result announcements, busy state, keyboard-visible focus, the approved palette/type/spacing, 4.5:1 contrast, reduced motion, and 390 px overflow behavior; add setup/check commands and the owner-provided backend demo procedure to `frontend/README.md`; then run `npm run lint`, `npm run typecheck`, `npm run test`, and `npm run build` in `frontend/` and record results (Owner: Person 4; Depends on: T006; Story 1 and 2 flows only—do not implement preview screens here).

**Explorer demo gate**: Before T008 starts, the owner follows the Explorer portion of `quickstart.md`, confirms the default answered flow and representative empty/error behavior against the fake backend, and records the observed result. All four automated commands in T007 must pass. If either condition fails, fix and repeat T007; do not begin preview screens.

**Current gate status (2026-11-22)**: All four automated commands pass and Milena (Person 4) accepted the Explorer walkthrough. T007 is complete. T008 implementation and automated checks now pass, including the shared single-`<main>` landmark; keep T008 open pending feature-owner manual review.

## Phase 6: User Story 3 - Preview the other research workflows (Priority: P3)

**Goal**: Add static, placeholder-only previews after the connected Explorer has passed T007's demo-ready gate.

**Independent Test**: Navigate to each preview and verify its labels, placeholders, disabled draft actions, accessibility, and absence of invented scientific claims.

### Tasks for User Story 3

- [ ] T008 Write preview navigation/screen tests first in `frontend/src/features/previews/Previews.test.tsx` for the exact banner, comparison rows Stressor/Control group/Measure/Sample/Result/Claim source with two `[paper selected from results]` columns, Position A/Position B and Experimental conditions/Sample/Methods cards, and “What is missing”/“What was found” plus “Draft hypothesis · model suggestion · not a verified finding” and its disabled Save/Edit/Dismiss actions; record RED, then implement `frontend/src/features/previews/ComparisonPreview.tsx`, `frontend/src/features/previews/ConflictsPreview.tsx`, `frontend/src/features/previews/GapsPreview.tsx`, and activate preview navigation in `frontend/src/components/Navigation.tsx` (Owner: Person 4; Depends on: T007; run the preview test, then rerun `npm run lint`, `npm run typecheck`, `npm run test`, and `npm run build`; record final checks in `EVIDENCE.md` and keep Phase 5 master backlog items unchecked pending final owner acceptance).

## Dependencies and Execution Order

```text
T001 -> T002 -> T003 -> T004 -> T005 -> T006 -> T007 -> T008
                                  User Story 1 ───────┘
                                             User Story 2 ──┘
                                                        Explorer demo gate
                                                        (hard prerequisite)
                                                        -> User Story 3
```

- **Setup (T001)** precedes all other tasks.
- **Foundational (T002)** precedes the user stories.
- **User Story 1 (T003–T005)** is completed and tested before User Story 2.
- **User Story 2 (T006)** builds on the working Explorer and closes its result-state behavior.
- **Explorer demo-ready gate (T007)** requires Story 1 and 2 tests plus all four frontend checks and owner-reported demo verification.
- **User Story 3 (T008)** is blocked until T007 passes. No preview screen work may be pulled earlier.
- **Parallel opportunities**: none are marked. The user requested serial story grouping, and shared app/config files plus the demo gate make parallel execution more likely to conflict than help.

## Independent Test Criteria

- **User Story 1**: With mocked `fetch`, a valid question can be submitted and the answered result, claim-linked numbered evidence, uncited passages, source highlight, safe DOI link, and provenance can be verified independently.
- **User Story 2**: With mocked response/error bodies, no-results, insufficient-evidence, retryable/nonretryable errors, proxy 5xx without an error envelope, malformed HTTP 200/4xx, fetch rejection, result-scoped dismissal, badge metadata rules, and the 30-second abort can be verified independently.
- **User Story 3**: After the Explorer gate, each preview can be opened and checked for its specified placeholder structure and disabled actions without any backend call.

## Implementation Strategy

1. Complete setup and foundational contract/types (T001–T002).
2. Finish and test the Research Question Explorer (T003–T006).
3. Pass the demo-ready gate and record the owner's Explorer demo result (T007).
4. Only then write preview tests and implement the static preview screens (T008).
5. Run the complete frontend check set after previews and record results. Keep tasks incomplete until their tests/checks and feature-owner acceptance are honestly recorded.

## Notes

- Every task has Owner Person 4, dependencies, concrete file paths, and verification criteria.
- Tests for behavior tasks must be written and shown failing before the implementation step in the same task.
- The two proxy regression cases are explicitly included in T003 and T006: HTTP 5xx without a valid API error envelope is retryable API-unreachable; malformed HTTP 200/4xx is a generic nonretryable error.
- No live backend call is used by automated tests. Manual demo calls use only the owner-provided fake backend command.
- The project owner approved the task list on 2026-11-22 and authorized implementation through T007. Keep T008 blocked until the owner reports a successful Explorer manual walkthrough after T007.
