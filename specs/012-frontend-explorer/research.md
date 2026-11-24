# Research: Frontend Research Question Explorer

**Date:** 2026-11-22  
**Owner:** Person 4  
**Purpose:** Check the existing product, API contract, frontend baseline, and maintained approaches before specifying Feature 012.

## Requested problem and unresolved decisions

Build the first SciScope frontend feature: a Research Question Explorer connected to the accepted Feature 011 fake-only question service, with static previews for three future workflows. The request already fixes the visual direction, primary interactions, fake-data boundary, testing approach, and major exclusions. This research does not authorize planning or implementation.

The decisions needing a plan are limited to component boundaries, exact friendly copy for individual known error codes, persistence behavior for a dismissed mock notice, and how frontend CI might be proposed without changing the Python workflow. The prompt requires the local demo command in the frontend README; the handoff says no launcher is officially supported. The spec therefore treats the supplied command as an owner-provided local demo procedure and not as a repository-supported backend launcher.

## Verified project facts

- The accepted Feature 011 service has one synchronous question workflow and a closed request contract. It accepts the research-question workflow, question, and optional valid request ID. It does not accept filters, provider, model, or retrieval-mode fields.
- The success response has `answered`, `no_results`, and `insufficient_evidence` states. Claims cite response-local evidence identities. Evidence has only `chunk_id`, `doi`, `source_locator`, `passage`, and `paper_title`; corpus provenance has `delivery_digest`, `source_contract_version`, and `corpus_version`. Mock metadata marks both `is_mock` and `is_test_data` true.
- The sanitized error contract includes a stable code, message, retryable flag, and request ID. Raw validation details and private exception text are intentionally excluded.
- The integration handoff explicitly says this backend baseline does not define a supported HTTP listener, port, frontend base URL, or launcher. The user's supplied `uv run --locked --with uvicorn python scratch/serve_fake.py` command is a user-provided local demo procedure and the handoff marks the launcher unsupported.
- The backend and retrieval source files were inspected read-only. The handoff checklist and models agree on the response-local citation join and the evidence/provenance field names.
- The frontend currently contains the generated Vite + React + TypeScript starter, Vite's `/api` proxy, and no application behavior or frontend test runner. `package.json` has React `^19.3.1`, Vite `^8.3.6`, and no React Router, Vitest, Testing Library, or JSX accessibility plugin. `node_modules/` already exists; no dependency installation was attempted.
- Golden Questions v0 contains English question prompts. Only prompt text is in scope for the example buttons; expected findings must remain excluded from the interface.
- Phase 5 backlog items are all unchecked. Feature 012 intentionally excludes metadata filters (P5-04), saved research (P5-12), and end-to-end tests (P5-14); no backlog completion is claimed during specification.

## Approaches compared

### Navigation state

| Approach | Verified facts | Advantages | Limitations and cost |
| --- | --- | --- | --- |
| Keep the selected view in application state | React documents keeping a single source of truth in the common parent and conditionally rendering views. | Fits four in-app sections; no additional package; minimal setup. | Views do not have separate addressable URLs or built-in browser history behavior. |
| Add a client-side router | React describes routing libraries as state-driven; the project does not currently include one. | Adds URL and browser-history navigation if those become requirements. | Adds dependency and configuration for routes not requested by this feature. |

**Recommendation:** Use simple application state to switch the four views. No direct-link, deep-link, or history requirement appears in the request, so a router would add setup without supporting a requested user journey. Revisit only if route URLs become an approved requirement.

### Frontend behavior tests

| Approach | Verified facts | Advantages | Limitations and cost |
| --- | --- | --- | --- |
| Vitest with Testing Library, user-event, and jsdom | Vitest documents that it is powered by Vite, uses the project Vite configuration by default, and supports a jsdom test environment. React Testing Library focuses tests on user-visible DOM behavior. user-event simulates browser-like interactions and documents v14 as its current recommended major. | Reuses the Vite setup, supports mocked `fetch`, and exercises accessible controls through realistic interactions. | Adds development dependencies and test configuration. Exact installed versions and licenses were not verified in the package registry during this research. |
| Jest with Testing Library | React Testing Library works with test runners and does not require a specific framework. | Familiar, broad ecosystem. | Requires a separate transform/configuration path for this Vite app and duplicates setup. |

**Recommendation:** Use Vitest, Testing Library, user-event, and jsdom, as requested. The official Vitest guide currently states requirements of Vite >= 6.4.0 and Node >= 22.12.0. The project's declared Vite version exceeds that Vite minimum; the Node runtime version still needs confirmation during planning/setup. No tests or packages were installed at this stage.

### Accessibility linting

`eslint-plugin-jsx-a11y` describes itself as a static JSX accessibility checker. Its maintained README documents a flat-config `flatConfigs.recommended` preset. The npm page and repository package metadata report version 6.10.2 and MIT license. The package's peer range is ESLint `^3` through `^9`; the existing frontend declares ESLint `^10.14.0`. The maintainers' ESLint 10 support request remains open. Therefore the requested recommended config cannot be added cleanly against the current declared ESLint major. The plan will propose aligning the frontend ESLint major to 9 rather than bypassing peer checks; that dependency change is part of the plan approval gate and must be validated before implementation.

**Recommendation:** Add the plugin's recommended flat config and align the frontend ESLint major to 9, which is inside the plugin's declared peer range. Retain keyboard, contrast, viewport, and manual review checks. The dependency alignment is proposed, not applied, and must pass dependency resolution and lint checks during approved implementation.

## Sources

### Repository sources (primary for this feature)

- `docs/person3/BACKEND_FRONTEND_INTEGRATION_HANDOFF.md`, especially sections 3–9 and the Person 4 integration checklist.
- `src/sciscope/api/http_models.py`, `src/sciscope/api/app.py`, `src/sciscope/api/routes.py`, and `src/sciscope/question_service/fakes.py` (read-only contract/source inspection).
- `docs/PRODUCT_SCOPE.md`, `docs/ARCHITECTURE.md`, `docs/DATA_MODEL.md`, `PROJECT_TODO.md`, and `evals/golden_questions.v0.json`.
- `frontend/package.json`, `frontend/vite.config.ts`, and the current generated starter source.
- `docs/DEVELOPMENT_WORKFLOW.md` and `.specify/memory/constitution.md`.

### External primary sources

- [React: Sharing State Between Components](https://react.dev/learn/sharing-state-between-components) — single-source-of-truth and lifting state guidance.
- [Vite: Getting Started](https://vite.dev/guide/) — current Node.js runtime requirements.
- [Vitest: Getting Started](https://vitest.dev/guide/) — Vite integration and current Vite/Node requirements.
- [Vitest: Migration Guide](https://vitest.dev/guide/migration/) — Vitest 5 compatibility minimums.
- [Testing Library: React Testing Library](https://testing-library.com/docs/react-testing-library/intro/) — user-facing DOM testing approach and framework flexibility.
- [Testing Library: user-event](https://testing-library.com/docs/user-event/intro/) — browser-like interaction simulation and recommended v14 usage.
- [eslint-plugin-jsx-a11y README](https://github.com/jsx-eslint/eslint-plugin-jsx-a11y) — flat-config recommended preset and static-check limitations.
- [eslint-plugin-jsx-a11y package metadata](https://github.com/jsx-eslint/eslint-plugin-jsx-a11y/blob/main/package.json) — version 6.10.2, MIT license, and ESLint peer dependency range.
- [Open ESLint 10 support issue](https://github.com/jsx-eslint/eslint-plugin-jsx-a11y/issues/1075) — maintainers' repo issue tracking ESLint 10 support.
- [eslint-plugin-jsx-a11y on npm](https://www.npmjs.com/package/eslint-plugin-jsx-a11y) — checked package version 6.10.2 and MIT license.

## Limitations and open questions

- npm package pages for Vitest, Testing Library, jsdom, and the IBM Plex Fontsource packages returned HTTP 403 during this research. Their current versions and licenses were therefore not verified here. Do not treat a package's existence as a verified compatibility result; check the lockfile/registry when dependency installation is approved.
- The project owner reports Node.js `v24.20.0`. Official Vite documentation requires Node `20.19+` or `22.12+`; official Vitest 5 documentation requires Node `22.12+` and Vite `6.4+`. The reported Node version satisfies both Node minimums; the existing Vite `8.3.6` satisfies the Vitest Vite minimum. This compatibility conclusion is based on the owner-provided runtime version and current official docs, not an independent local runtime command.
- The integration handoff is authoritative for the fake API but explicitly does not establish an official backend launcher. Person 3 should decide separately whether to document/support one.
- The current evidence contract lacks `authors`, `publication_year`, and `section_path`; request filters are also absent. Do not show or send those fields in Feature 012. These may be future contract questions for Person 3, along with real retrieval (P4-09) and Gemini integration (P4-10).
- A separate frontend CI job is a plan proposal only. The existing Python workflow must remain unchanged unless the team approves a separate CI change.

## Recommendation

The approved specification and current plan use a single-page, state-switched interface against only the accepted fake question contract. Keep all three future workflows static and visibly marked as previews. Use mocked service responses for automated behavior tests; reserve any real fake-backend browser run as optional and dependent on approval. Preserve all P5 task states until automated checks pass and the feature owner confirms manual verification.

## Implementation test research (2026-11-22)

- **Problem:** Implement the approved TypeScript view of Feature 011's question request, response discriminants, error envelope, and offline fixtures without changing the backend contract or embedding realistic-looking scientific claims.
- **Repository facts checked:** `data-model.md`, `contracts/question-service.md`, and the accepted Person 3 handoff agree on the request fields, three success states, six error codes, evidence fields, corpus provenance fields, and mock metadata. T001 installed Vitest 5, Testing Library, user-event, and jsdom; `frontend/vite.config.ts` now selects jsdom for these tests.
- **Approaches considered:** (1) TypeScript interfaces only with typecheck; (2) interfaces plus runtime tests over typed synthetic fixtures; (3) runtime schema dependency. The contract is owned by Pydantic and this task is frontend-only, so a new schema library would duplicate validation and expand scope.
- **Recommendation:** Use closed TypeScript unions/interfaces and Vitest assertions over clearly labeled, non-scientific fixtures. Run a small fixture test before implementation to capture the required shape, then typecheck. Test setup covers cleanup without adding another dependency.
- **Limitations:** TypeScript types do not validate network JSON at runtime; response validation belongs to T003's approved client task. No web research was needed because this internal implementation follows already-approved project contracts and tool selections; package installation was validated in T001.
