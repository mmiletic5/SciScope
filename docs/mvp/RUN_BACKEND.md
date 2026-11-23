# Running the MVP backend

Configuration comes from environment variables only (see `API_CONTRACT.md`).
Invalid configuration stops startup with a message that names the variable,
never its value. There is no silent fallback to another provider or mode.

## Start

The project is not installed as a package (`package = false`), so set
`PYTHONPATH` once per PowerShell session before running `python -m` or uvicorn:

```powershell
$env:PYTHONPATH = "src"
```

`scripts/mvp_smoke.py` adds `src` to `sys.path` itself and needs no variable.

```powershell
# Zero config: fake retrieval + fake provider, no DB, no network (Demo mode)
uv run --locked python -m sciscope.api.server

# Same, loading variables from a local .env (never commit it)
uv run --locked --env-file .env python -m sciscope.api.server

# Real retrieval (hybrid) + fake provider
$env:RETRIEVAL_BACKEND = "postgres"   # needs DATABASE_URL and OPENAI_API_KEY
uv run --locked --env-file .env python -m sciscope.api.server

# Real retrieval, lexical only (no embedding key needed)
$env:RETRIEVAL_BACKEND = "postgres"; $env:RETRIEVAL_MODE = "lexical"

# Real answer provider (needs OPENAI_API_KEY and OPENAI_ANSWER_MODEL)
$env:AI_PROVIDER = "openai"

# uvicorn directly
uv run --locked uvicorn sciscope.api.server:create_server_app --factory --port 8000
```

Failure diagnostics (off by default): `$env:SCISCOPE_DEBUG_FRAMES = "1"` makes
the server log, on stderr, only the traceback frames (`path:line function`) and
the exception class name for `response_contract_failure` and unexpected errors.
It never logs messages, locals, or request/response content.

Defaults: host `127.0.0.1`, port `8000` (`HOST` / `PORT`).

## Environment variable names

| Name | Values / default |
| --- | --- |
| `AI_PROVIDER` | `fake` (default) or `openai` |
| `OPENAI_API_KEY` | required for `AI_PROVIDER=openai` and for hybrid retrieval |
| `OPENAI_ANSWER_MODEL` | required for `AI_PROVIDER=openai`; no default |
| `OPENAI_BASE_URL`, `OPENAI_TIMEOUT_SECONDS` | optional |
| `RETRIEVAL_BACKEND` | `fake` (default) or `postgres` |
| `RETRIEVAL_MODE` | `hybrid` (default) or `lexical`; used with `postgres` |
| `DATABASE_URL` | required for `postgres` |
| `CORS_ORIGINS` | comma list; default `http://localhost:5173,http://127.0.0.1:5173` |
| `HOST`, `PORT` | `127.0.0.1`, `8000` |

## Try it

```powershell
curl.exe http://127.0.0.1:8000/api/health

curl.exe -X POST http://127.0.0.1:8000/api/v2/questions `
  -H "Content-Type: application/json" `
  -d '{\"workflow\":\"research_question\",\"question\":\"Why do bees dance?\"}'
```

## Known limits

- Only `research_question` is implemented; `/api/health` lists only implemented
  workflows (the fixture lists all four until the other workflows land).
- Retrieval profile is fixed: `retrieval.v2`, `top_k` 5, no filters. The
  candidate pool of 50 applies in hybrid mode only, because the retrieval
  contract rejects ranking options for lexical mode.
- `/api/v1/questions` returns a 500 `internal_error` when the server uses
  component metadata (all server modes); use v2.
- Fake mode reports retrieval origin `synthetic` and provider origin `fake`,
  both `is_test_data: true`.
- Health reports configured origins only; it does not probe the DB or OpenAI.
- Live OpenAI and Postgres paths are unit-tested offline only; they have not been
  verified end to end by this change.
