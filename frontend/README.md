# SciScope Frontend

React + Vite + TypeScript. The Research Question Explorer talks to the **API v2** (`POST /api/v2/questions`, `GET /api/health`) defined in [`docs/mvp/API_CONTRACT.md`](../docs/mvp/API_CONTRACT.md). Tests mock `fetch`; none of them contacts a backend or a live AI provider.

## Requirements

- Node.js `v24.20.0` (the project owner's reported version).
- npm, included with Node.js.

## Install and run

From the repository root, use a terminal such as Git Bash or PowerShell:

```bash
cd frontend
npm ci
npm run dev
```

The dev server forwards `/api` to the backend at `http://127.0.0.1:8000`. If the backend is not running, the header shows "Backend offline" and a search ends in a retryable "Cannot reach the SciScope API" state.

## API v2 notes

- Types: `src/api/types.v2.ts` is an unmodified copy of `docs/mvp/api-types.v2.ts` (contract mirror). `src/api/types.ts` only adds aliases and the per-workflow client timeouts. Do not edit the mirror; change the contract first.
- Client: `submitQuestion(question, requestId, workflow = 'research_question')` sends the `workflow` field. Client timeout is 30 s for `research_question` and 60 s for `evidence_comparison`, `conflicting_evidence` and `research_gap`. `fetchHealth()` reads `/api/health` (5 s timeout).
- Validation: `src/api/validate.ts` strictly checks the envelope, per-component metadata, the per-workflow payloads and the citation invariants (every `citation_chunk_ids` entry non-empty, unique, and present in the same response's `evidence[]`; status/answer/claims/evidence rules). Anything invalid becomes the client error `invalid_response`. The response `workflow` must match the requested one.
- Mode badge (header): `Live` only if `isLiveMode(metadata)` holds (both components real, executed, not test data); otherwise `Demo (fake provider)` or `Demo (synthetic data)`. Before the first question the badge comes from `GET /api/health` (configured origins only); if health fails it shows `Backend offline`. A question response then overrides it with what actually ran.
- The Explorer currently runs `research_question` only. The other three workflows are supported by the client and validators, but have no screen yet (the Comparison, Conflicts and Gaps views are still static previews).

## Fixture mode (offline development)

```bash
VITE_API_MODE=fixtures npm run dev        # Git Bash / macOS / Linux
$env:VITE_API_MODE = 'fixtures'; npm run dev   # PowerShell
```

In fixture mode no request is sent. After a short fake delay (about 0.4 s) the client returns the answered contract fixture for the requested workflow, validated like a live response, and `/api/health` returns the health fixture. The fixtures are copies of `docs/mvp/fixtures/*.json` in `src/api/fixtures/v2/`; refresh them from `docs/mvp/fixtures/` if the contract changes. The default mode is live.

## Checks

Run from `frontend/`:

```bash
npm run lint
npm run typecheck
npm run test
npm run build
```

Vitest uses jsdom and the local fixtures. No test requires a service key, paid provider, or running backend. On Windows, run `npm run test` from PowerShell: Git Bash can start the shell with a lower-case drive letter (`c:`), which makes Vitest fail with "failed to find the current suite".
