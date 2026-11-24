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
| `SCISCOPE_AGENTIC_RETRIEVAL` | `0` (default) or `1`; opt-in agentic retrieval for `evidence_comparison` only |

## Agentic retrieval (opt-in, `evidence_comparison` only)

`$env:SCISCOPE_AGENTIC_RETRIEVAL = "1"` adds a stage before the normal
grounded answer call of `evidence_comparison`. With the flag unset or `0`
nothing changes. The API contract, fixtures and response fields stay the same.

1. **Stage 1 (tool loop):** the configured answer provider gets one function
   tool, `search_corpus(query)`. It may make at most 3 tool calls in total
   (parallel calls count; extra ones are not run) within a 20 s stage budget.
   Each call runs the workflow's own retrieval profile (same mode, `top_k`
   10, candidate pool, no filters); only the query text changes. Model
   queries are untrusted: control and format characters are removed,
   whitespace is collapsed, and the length is cut to 300 characters. Results
   go back to the model as boundary-delimited passage blocks, cut to 700
   characters each.
2. **Stage 2 (unchanged):** the per-search rankings are merged round-robin
   into a unique union of at most 12 chunks (and at most 60,000 passage
   characters, the provider's evidence cap). The union becomes the evidence
   of the existing grounded answer call: same schema enum of allowed
   chunk_ids, same validation, same sanitizer. The response `evidence` is the
   union, so citations can only name chunks that were actually retrieved.
3. **Fallback:** any stage 1 error, a budget overrun, zero tool calls, an
   empty union or a corpus change between searches falls back to today's
   single-shot retrieval of the original question.

With `AI_PROVIDER=fake`, stage 1 is a deterministic simulation: two scripted
searches, no network. With the synthetic retrieval, the answer is the same
as with the flag off.

The server logs one line per agentic request on stderr, with counts only:
`agentic_retrieval workflow=... rounds=... searches=... merged=...
fallback=yes|no reason=... latency_ms=...`. It never logs queries,
passages, prompts or keys.

Live comparison: `scripts/mvp_smoke.py --only gq-cmp-001 --repeat 3
--agentic` (without `--agentic` the script forces the flag to `0`).

## Try it

```powershell
curl.exe http://127.0.0.1:8000/api/health

curl.exe -X POST http://127.0.0.1:8000/api/v2/questions `
  -H "Content-Type: application/json" `
  -d '{\"workflow\":\"research_question\",\"question\":\"Why do bees dance?\"}'
```

## Known limits

- `/api/health` `workflows` lists the workflows of the configured provider:
  all four with `AI_PROVIDER=fake` and with `AI_PROVIDER=openai`. All four
  workflows are implemented for the fake and openai providers; live OpenAI
  behavior is verified only by the user's smoke run.
- The fake provider answers all four workflows from synthetic evidence of
  three synthetic papers (`10.0000/synthetic.*`, `is_test_data: true`). Its
  text is placeholder, not a finding.
- Retrieval profile per workflow: `retrieval.v2`, no filters, `top_k` 5 for
  `research_question` and 10 for the other three (one adapter per workflow).
  The candidate pool of 50 applies in hybrid mode only, because the retrieval
  contract rejects ranking options for lexical mode. Fake retrieval ignores
  the profile.
- Payload workflows are validated server-side (citations, subject DOIs,
  item and hypothesis rules); a comparison citing fewer than two papers, a
  conflicts answer without items or a gap analysis without gaps is returned
  as `insufficient_evidence`.
- `/api/v1/questions` returns a 500 `internal_error` when the server uses
  component metadata (all server modes); use v2.
- Fake mode reports retrieval origin `synthetic` and provider origin `fake`,
  both `is_test_data: true`.
- Health reports configured origins only; it does not probe the DB or OpenAI.
- Agentic retrieval (`SCISCOPE_AGENTIC_RETRIEVAL=1`):
  - Stage 2 keeps its own 60 s provider budget, so the worst case is
    about 20 s (stage 1) plus 60 s (stage 2) plus retrieval time. That is
    more than the 60 s the frontend allows.
  - Every search is a full retrieval (a query embedding plus a DB query in
    hybrid mode), and there are up to 3 searches plus up to 3 extra model
    calls.
  - On fallback, the original retrieval runs after the time stage 1 already
    spent.
  - If the fallback retrieval itself fails, the error response reports the
    answer provider as not executed, although stage 1 did call the model.
  - The union can hold up to 12 chunks, so `evidence` can be longer than
    the 10 of the normal profile.
  - Stage 1 sees passages cut to 700 characters.
  - Stage 1 always sends `reasoning_effort: "none"`, because the configured
    reasoning model accepts function tools on chat completions only with
    that value (the provider's own reasoning effort applies to stage 2
    only). A model that rejects `reasoning_effort` makes stage 1 fail, so
    every request falls back.
  - In the first live check (`gq-cmp-001` ×3) agentic found the same two
    papers as the single-shot path and took about 3 s longer.
  - The other three workflows ignore the flag.
- Live OpenAI and Postgres paths are unit-tested offline only; they have not been
  verified end to end by this change. `scripts/mvp_smoke.py` runs each dev
  question with its workflow and skips workflows the provider does not
  support.
