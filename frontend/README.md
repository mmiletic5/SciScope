# SciScope Frontend

The Research Question Explorer is the connected frontend workflow. It uses the accepted Feature 011 fake question API through Vite's existing `/api` proxy. Service and app-flow tests mock `fetch`; they do not contact a backend or live AI provider.

## Requirements

- Node.js `v24.20.0` (the project owner's reported version).
- npm, included with Node.js.
- For a backend demo only: the repository's configured `uv` environment.

## Install and run

From the repository root, use a terminal such as Git Bash or PowerShell:

```bash
cd frontend
npm ci
npm run dev
```

Open the local Vite URL printed in the terminal. The development server forwards `/api` to `http://127.0.0.1:8000`.

## Checks

Run from `frontend/`:

```bash
npm run lint
npm run typecheck
npm run test
npm run build
```

Vitest uses jsdom and the local offline fixtures. No test requires a service key, paid provider, or running backend.

## Fake backend demo

The Feature 011 handoff does not define an officially supported HTTP launcher. The following command is the owner-provided local demo procedure and serves synthetic test data only. From the repository root, start it in terminal 1:

```bash
uv run --locked --with uvicorn python scratch/serve_fake.py
```

In terminal 2, start the frontend as described above. The default response is answered. To try a different fake response, stop terminal 1 and restart with one of these options:

```bash
uv run --locked --with uvicorn python scratch/serve_fake.py --retrieval empty
uv run --locked --with uvicorn python scratch/serve_fake.py --provider insufficient_evidence
uv run --locked --with uvicorn python scratch/serve_fake.py --provider unavailable
uv run --locked --with uvicorn python scratch/serve_fake.py --provider timeout
uv run --locked --with uvicorn python scratch/serve_fake.py --retrieval unavailable
uv run --locked --with uvicorn python scratch/serve_fake.py --retrieval timeout
```

When the backend is stopped, submitting a question exercises the Vite proxy's retryable API-unreachable state. A client-side 30-second timeout is tested with a controlled pending fetch in Vitest; backend timeout modes return a service error and do not simulate that client timer.
