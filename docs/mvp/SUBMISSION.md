# SciScope MVP: Capstone submission

Lean-mode MVP track. **Nothing here is ACCEPTED.** Every number below is quoted from a file
in this repository; where a value comes from a gitignored local file, that is said.

## 1. What is submitted

The integrated MVP: a React frontend and a Python backend over a 17-paper PLOS ONE honey bee
corpus, with **real Postgres/pgvector retrieval** and a **real OpenAI model**, serving four
workflows on one shared RAG path: `research_question`, `evidence_comparison`,
`conflicting_evidence`, `research_gap` (API: [API_CONTRACT.md](API_CONTRACT.md)). A
zero-config **Demo (fake) mode** needs no database and no network; the UI shows a Demo badge.

The submission is the commit tagged `capstone-submission` on `main`. The tag is created
after the merge; the file deliberately contains no SHA. To see it:

```powershell
git rev-parse capstone-submission
```

## 2. Exact data package

Source: [DEMO_DB.md](DEMO_DB.md) and [data/pilot/delivery_manifest.json](../../data/pilot/delivery_manifest.json).

| Item | Value |
| --- | --- |
| Archive | `pilot-delivery.zip` (six files, extracted to `data/delivery/pilot/`) |
| Archive SHA256 | `6FA27AFAF334D6A87BE30A04F3D15A9573696C7C03DDCC5205C23D508F239F2C` |
| Counts | 17 papers, 319 sections, 728 chunks, 728 embeddings (1536-dimension vectors) |
| Embedding set | provider `openai`, model `text-embedding-3-small`, 1536 dimensions, `float32-le`, declared normalization `l2` |
| Manifest | `schema_version` / `contract_version` `0.3.0`, `status` `draft` |
| Processing versions | `chunking-v1`, locator `jats:v1`, template `embedding-text-v1`, taxonomy `v0` |

SHA256 of the extracted files (from the manifest; I re-computed each with `sha256sum` on the
local `data/delivery/pilot/` and they match):

| File | SHA256 |
| --- | --- |
| `papers.jsonl` | `2e3b1a920bc123325f78d62fa18f2164acac1dad9b20cc8b41f102a4f72fc9a1` |
| `sections.jsonl` | `b41e3ef3f4930cedcca6607ead5ee96b1df1d7e400011b99d77d7eee01644721` |
| `chunks.jsonl` | `77dac1d542d8dc4f55c205ae3db2e92a4906091963760aed38f22b9d0005fde1` |
| `vectors.f32` | `68fbcee7cda50686c528f32a5078c7b8133d0e1ddce826358d3740a0aa2fa98d` |
| `embedding_manifest.json` | `99185d5db2f57726ea2224dfb66b67c413252ad6abb120e58e4c01498561ca60` |

**The zip is not in git** (`data/delivery/` is gitignored; archive bytes are not
deterministic, so the hash identifies one specific file). The delivery package
`pilot-delivery.zip` (SHA256 as above) is attached to the GitHub release
`capstone-submission`; it is not stored in git. Compare its hash before extracting:

```powershell
Get-FileHash pilot-delivery.zip -Algorithm SHA256
```

## 3. Reproducing from a clean checkout

**Prerequisites:** Git, Python 3.12 managed by `uv`, Node.js LTS, and for live mode Docker
Desktop, the data package above, and an OpenAI API key and answer model name (values only in
the gitignored `.env`; never commit it). Env variable names: [RUN_BACKEND.md](RUN_BACKEND.md).

**Fake mode** (no DB, no network, no key; commands from [README.md](../../README.md)):

```powershell
uv sync --locked
$env:PYTHONPATH = "src"
uv run --locked python -m sciscope.api.server       # http://127.0.0.1:8000
# second terminal
cd frontend
npm ci
npm run dev                                         # http://localhost:5173, badge: Demo
```

Check: `curl.exe http://127.0.0.1:8000/api/health` responds. The frontend also runs without a
backend with `$env:VITE_API_MODE = 'fixtures'; npm run dev`.

**Live mode:**

1. Build the database following [DEMO_DB.md](DEMO_DB.md): `.env` with `POSTGRES_DB`
   (must be `sciscope_test_005`), `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_PORT`,
   `DATABASE_URL`, plus `OPENAI_API_KEY` and `OPENAI_ANSWER_MODEL`;
   `docker compose up -d db` (wait for `healthy`); extract the zip; `validate-delivery`;
   `alembic upgrade head`; `scripts/mvp_import_pilot.py`; `verify_pilot`.
   Expected: `validate-delivery` reports 17/319/728/728 with failures 0, and `verify_pilot`
   prints `"status": "PASS"`.
2. Start the backend:
   ```powershell
   $env:PYTHONPATH = "src"
   $env:RETRIEVAL_BACKEND = "postgres"
   $env:AI_PROVIDER = "openai"
   uv run --locked --env-file .env python -m sciscope.api.server
   ```
3. Start the frontend as above. Expected: badge **Live**.

**Smoke command** (five development questions; needs the explicit live opt-in; makes paid
OpenAI calls):

```powershell
$env:SCISCOPE_LIVE_OPENAI = "1"
uv run --locked --env-file .env python scripts/mvp_smoke.py
```

Expected: one line per question, `http=200`, `citations_in_evidence=True`,
`origins=real/real`, `ids_in_text=false`; four `answered` and `gq-ins-001`
`insufficient_evidence` (section 4).

**Offline checks** (no network, no paid calls): `uv run --locked ruff check .` and
`$env:PYTHONPATH = "src"; uv run --locked python -m pytest -q`. Last recorded result in [EVIDENCE.md](../../EVIDENCE.md): `ruff`
passed; `pytest` 3399 passed, 3 skipped, 36 errors, where the 36 errors are DB-gated
fixtures that need `SCISCOPE_TEST_DATABASE_URL` (see section 7).

## 4. Live smoke summary

Five development questions (from `evals/golden_questions.v0.json`), real Postgres retrieval,
real OpenAI model, one run each, at head `136a2c5`. Per-question latencies are from the
local, gitignored `scratch/imp01_full_smoke.log` (read, not rerun); the committed record is
[EVAL_RESULTS.md](EVAL_RESULTS.md) (IMP-01) and [EVIDENCE.md](../../EVIDENCE.md).

| Question | Workflow | HTTP / status | Evidence / claims | Citations inside evidence | Latency |
| --- | --- | --- | --- | --- | --- |
| `gq-sp-001` | `research_question` | 200 / answered | 5 / 2 | yes | 3.1 s |
| `gq-cmp-001` | `evidence_comparison` | 200 / answered | 10 / 5 | yes | 10.3 s |
| `gq-conf-001` | `conflicting_evidence` | 200 / answered | 10 / 4 | yes | 6.0 s |
| `gq-gap-001` | `research_gap` | 200 / answered | 10 / 4 | yes | 8.5 s |
| `gq-ins-001` | `research_question` | 200 / insufficient_evidence | 5 / 0 | yes | 1.7 s |

Latency range in this run: 1.7-10.3 s. `gq-cmp-001` repeated five times took 5.7-8.1 s (EVAL_RESULTS.md), so single-run latency
varies; [DEMO_SCRIPT.md](DEMO_SCRIPT.md) now quotes roughly 2-11 s. `ids_in_text=false` and real/real
metadata on all five. The `gq-ins-001` outcome is the expected one (the corpus has nothing on
glyphosate and gut microbiota). Answer content was read by the AI assistant (Claude Code); two answers (EV-01 and
EV-04) were compared with the source papers by one human reader (EVAL_RESULTS.md, last section).

## 5. Behaviour without support

From [EVAL_RESULTS.md](EVAL_RESULTS.md), live, one run each:

| Case | Input | App returns |
| --- | --- | --- |
| EV-05 | off-domain: "capital of Australia" | 200, `insufficient_evidence`, no answer or claims; 5 nearest-neighbour passages still shown as evidence |
| EV-07 | unclear: "How does it affect them?" | 200, `insufficient_evidence`, 0 claims, 5 evidence items |
| EV-08 | half-supported comparison: virus vs glyphosate sugar-water sensitivity | 200, `insufficient_evidence`; 10 evidence items from 2 papers, none mentions glyphosate |
| EV-09 | not in corpus: glyphosate and gut microbiota (`gq-ins-001`) | 200, `insufficient_evidence`, 0 claims |

`no_results` did **not** occur live: retrieval has no score floor, so an off-domain question
still gets its five nearest chunks and the model declines. That path is covered by offline
tests only.

**Known weakness:** the app does not say *why* it declines. An unclear question (EV-07), a
missing half of a comparison (EV-08), an off-domain question (EV-05) and an uncovered topic
(EV-09) all return the same `insufficient_evidence`, and there is no clarifying-question
feature. EV-06 (a follow-up sent alone) is not supported by design: the app is stateless, and
a continuation field is rejected with 422.

## 6. Key negative checks (EV-11 to EV-16)

Offline, no paid call; 79 test items, 79 passed. Run with `$env:PYTHONPATH = "src"; uv run --locked python -m pytest <ids> -q`.
Full node ids are listed in [EVAL_RESULTS.md](EVAL_RESULTS.md) (section "Pytest node ids for EV-11 .. EV-16");
the files below hold them. "Simulated" means the real provider/route code driven by a scripted
transport, not a real failing provider.

| Case | What is checked | Test files (node ids in EVAL_RESULTS.md) | Result |
| --- | --- | --- | --- |
| EV-11 | Blank, too long, missing or mistyped question; bad `request_id`; extra fields `filters`, `top_k`, `mode`, `conversation_id`; non-JSON; unknown workflow: 422 `invalid_request`, sanitized, no service invoked | `tests/backend/test_eval_cases.py::test_ev11_*`, `test_question_api_v2.py::test_v2_rejects_invalid_or_unsupported_request_values`, `test_request_ids_and_validation.py` | PASS (deterministic) |
| EV-12 | Model output not JSON, extra key, truncated, or a refusal: fails closed, HTTP 500 `response_contract_failure`, no model text returned | `test_eval_cases.py::test_ev12_*`, `test_openai_provider.py::test_malformed_refused_or_truncated_output_fails` | PASS (simulated) |
| EV-13 | Model cites a chunk id that was not supplied: rejected, one identical retry, then 500; a grounded retry is accepted | `test_eval_cases.py::test_ev13_*`, `test_openai_provider.py::test_ungrounded_output_retries_once_then_fails`, `test_response_validation.py::test_answered_outcome_rejects_invalid_citation_identities`, `test_agentic_retrieval.py::test_citing_a_chunk_outside_the_union_is_rejected` | PASS (simulated) |
| EV-14 | Unknown tool `drop_tables`, extra tool arguments, more than 3 tool calls, scope-widening request fields, unimplemented workflow | `test_agentic_retrieval.py::test_hostile_arguments_change_only_the_query_text`, `::test_parallel_calls_beyond_the_limit_are_never_searched`, `::test_session_enforces_the_limit_against_a_faulty_planner`, `test_openai_provider.py::test_unimplemented_workflow_fails_before_any_network_call` | PASS (simulated + deterministic) |
| EV-15 | Timeout: 504, no retry. 429: 503 after 2 backoff retries. `insufficient_quota`: not retried. 5xx handled | `test_eval_cases.py::test_ev15_*`, `test_openai_provider.py::test_transport_timeout_maps_to_dependency_timeout`, `::test_transient_failures_retry_twice_then_unavailable`, `::test_non_retryable_errors_map_to_provider_unavailable`, `test_question_api_v2.py::test_v2_preserves_the_controlled_timeout_contract` | PASS (simulated) |
| EV-16 | Agentic stage 1 fails (tool error, HTTP 400, timeout, truncated, zero tool calls, empty union): falls back to single-shot retrieval and still answers | `test_agentic_retrieval.py::test_stage1_errors_fall_back_to_single_shot`, `::test_zero_tool_calls_falls_back`, `::test_empty_union_falls_back`, `::test_fallback_retrieval_failure_is_todays_error`, `::test_fake_planner_outage_falls_back` | PASS (simulated) |

All paths are under `tests/backend/`. Related live case EV-10 (one synthetic poisoned passage,
one run): canary, made-up id and system-prompt echo were absent. EVAL_RESULTS.md calls it the
weakest live case; it does not show the defence holds against other wording or models.

## 7. Known limits

- Only five development questions were exercised live; they were also used throughout
  development, so they are not independent test data.
- The corpus is the 17-paper pilot (728 chunks). The tool says nothing about wider literature.
- Retrieval was compared only on the same five development questions ([RETRIEVAL_V2_RESULTS.md](../person2/RETRIEVAL_V2_RESULTS.md)); there is no held-out retrieval result.
- Live answer content was read by the AI assistant (Claude Code) only, except EV-01 and EV-04, checked against the
  papers by one human reader.
- Agentic retrieval is opt-in (`SCISCOPE_AGENTIC_RETRIEVAL=1`), affects `evidence_comparison`
  only, and shows **no measured quality gain** (`gq-cmp-001`: three runs, about +3 s;
  EV-04 one run, 12.0 s).
- One DB-gated test fails on its fixture precondition: on a disposable pilot-only database,
  `tests/ingestion/test_replacement.py::test_valid_replacement_prunes_old_corpus_and_keeps_audit`
  expects 3 `delivery_imports`, finds 2 (172 passed, 1 failed). Not investigated or changed.
  The DB-gated tests are skipped or error without `SCISCOPE_TEST_DATABASE_URL`.
- EV-12, EV-13, EV-15 and EV-16 are simulated failures; no real OpenAI rate limit or timeout
  was observed.
- Not done: security/privacy review, formal acceptance, human verification of tasks.

## 8. Evidence map

| Rubric area | Where to look |
| --- | --- |
| Spec / plan | Lean mode, no Spec Kit artefacts for the MVP track (explicit owner approval, [EVIDENCE.md](../../EVIDENCE.md) "MVP track"). Scope and design: [PRODUCT_SCOPE.md](../PRODUCT_SCOPE.md), [ARCHITECTURE.md](../ARCHITECTURE.md), [API_CONTRACT.md](API_CONTRACT.md); earlier feature specs in [specs/](../../specs/) |
| App | Backend [src/sciscope/api/](../../src/sciscope/api/) and [src/sciscope/question_service/](../../src/sciscope/question_service/); frontend [frontend/src/](../../frontend/src/); demo screenshots [demo/](demo/) |
| Sources / data | [DEMO_DB.md](DEMO_DB.md), [data/pilot/delivery_manifest.json](../../data/pilot/delivery_manifest.json), [data/pilot/](../../data/pilot/) reports and selection, [DATA_CONTRACT.json](../DATA_CONTRACT.json) |
| Workflow | [RUN_BACKEND.md](RUN_BACKEND.md), [DEMO_SCRIPT.md](DEMO_SCRIPT.md), [DEVELOPMENT_WORKFLOW.md](../DEVELOPMENT_WORKFLOW.md), [EVIDENCE.md](../../EVIDENCE.md) |
| Evaluation | [EVAL_CASES.md](EVAL_CASES.md), [EVAL_RESULTS.md](EVAL_RESULTS.md), [scripts/mvp_eval.py](../../scripts/mvp_eval.py), [scripts/mvp_smoke.py](../../scripts/mvp_smoke.py), [tests/backend/test_eval_cases.py](../../tests/backend/test_eval_cases.py) |
| Security | EV-10 to EV-16 (sections 6 and EVAL_RESULTS.md), [text_sanitizer.py](../../src/sciscope/question_service/text_sanitizer.py), grounding rules in [openai_provider.py](../../src/sciscope/question_service/openai_provider.py), secret scan note in EVAL_RESULTS.md; no secrets in git (`.env` ignored, [.env.example](../../.env.example) names only). No formal security review |
| Run / submit | This file, [README.md](../../README.md) MVP quickstart, [RUN_BACKEND.md](RUN_BACKEND.md), [DEMO_DB.md](DEMO_DB.md) |
| Contributions | [CONTRIBUTIONS.md](CONTRIBUTIONS.md) |
