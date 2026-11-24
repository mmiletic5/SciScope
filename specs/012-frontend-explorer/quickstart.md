# Feature 012 Quickstart and Validation Guide

This guide describes validation after the approved implementation is completed. It is not evidence that commands have been run. The fake backend command below is supplied by the project owner for local demos; the Person 3 integration handoff does not define an officially supported launcher.

## Prerequisites

- A terminal at the SciScope repository root (PowerShell, Git Bash, or another shell).
- Node.js `v24.20.0`, confirmed by `node --version`. Official Vite and Vitest minimums are lower; see [plan.md](plan.md#runtime-compatibility-check).
- Python `uv` environment and locked repository dependencies already set up according to [DEVELOPMENT_WORKFLOW.md](../../docs/DEVELOPMENT_WORKFLOW.md).
- Frontend dependencies installed from `frontend/package-lock.json` with `npm ci`.

## Start the default fake backend

In terminal 1, from the repository root:

```powershell
uv run --locked --with uvicorn python scratch/serve_fake.py
```

This is an owner-provided local demo procedure, not an official backend launcher. It serves only synthetic test data. No credentials or paid provider are required.

## Start the frontend

In terminal 2:

```bash
cd frontend
npm ci
npm run dev
```

Open the local Vite address printed by the dev server. The existing development proxy forwards `/api` calls to the backend on `127.0.0.1:8000`.

## Exercise fake response modes

Stop and restart terminal 1 with one of the supported options, then submit a question again:

```powershell
uv run --locked --with uvicorn python scratch/serve_fake.py --retrieval empty
uv run --locked --with uvicorn python scratch/serve_fake.py --provider insufficient_evidence
uv run --locked --with uvicorn python scratch/serve_fake.py --provider unavailable
uv run --locked --with uvicorn python scratch/serve_fake.py --provider timeout
uv run --locked --with uvicorn python scratch/serve_fake.py --retrieval unavailable
uv run --locked --with uvicorn python scratch/serve_fake.py --retrieval timeout
```

Expected visible states are answered by default; no relevant passages for `--retrieval empty`; declined/closest-passage state for `--provider insufficient_evidence`; retryable unavailable or dependency-timeout errors for the corresponding failure modes. All returned fake results remain clearly labeled as synthetic test data.

To check the Vite-proxy path when the backend is stopped, stop terminal 1 and submit a question. If the proxy returns HTTP 5xx with a non-envelope body, the frontend should show the retryable “Cannot reach the SciScope API. Is the backend running?” message.

The frontend's own 30-second request abort should be verified with a controlled mocked request in Vitest. Backend fake `timeout` modes return a dependency-timeout response and do not by themselves prove that the frontend waited 30 seconds and aborted.

## Automated checks (after implementation)

From `frontend/`:

```powershell
npm run lint
npm run typecheck
npm run test
npm run build
```

All component/client tests use mocked `fetch`; none contacts the backend or a live AI provider.

## Manual owner verification: Explorer demo gate

1. Submit a valid question against the default fake backend and confirm the answer, claim citation, source highlight, DOI link, provenance disclosure, and mock/test-data labels.
2. Restart the fake backend through each relevant mode above and confirm the no-results, insufficient-evidence, retryable outage, and dependency-timeout states.
3. Submit a long-running mocked request in the automated suite to verify 30-second abort behavior and the exact retryable timeout message.
4. Confirm notice dismissal lasts only for the current result and returns with the next mock response. Confirm the global mock badge starts visible, remains visible if either latest-response metadata value is true, and hides only after a response explicitly reports both false.
5. Keyboard-navigate every control, inspect visible focus, and confirm result announcements.
6. Check the app at 390 px viewport width for usable navigation and no horizontal overflow.
Record these Explorer results and explicit feature-owner acceptance in `EVIDENCE.md`. Keep T008 blocked until this Explorer gate is accepted.

## Manual preview verification (after T008)

After the preview screens are implemented, review each static preview for its required placeholders and disabled actions, with no invented scientific finding. Record acceptance in `EVIDENCE.md`.

Leave all Phase 5 backlog items unchecked until the automated checks and the owner-confirmed manual verification are recorded.
