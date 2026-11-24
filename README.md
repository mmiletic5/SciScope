# SciScope

SciScope is a planned honeybee research assistant. This repository currently
contains the initial specification workflow, evaluation framework, and
development tooling. It does **not** contain a running application, corpus,
embeddings, AI provider, or scientific answers. The proposed product has a
Research Question Explorer, Evidence Comparison, Conflicting Evidence Finder,
and Research Gap & Hypothesis Assistant, all using one shared RAG system. See
[product scope](docs/PRODUCT_SCOPE.md) and [architecture](docs/ARCHITECTURE.md).

## MVP quickstart

The MVP track (lean mode, not ACCEPTED) adds a local backend and a React
frontend over a 17-paper PLOS ONE honey bee corpus. API:
[docs/mvp/API_CONTRACT.md](docs/mvp/API_CONTRACT.md). Demo plan:
[docs/mvp/DEMO_SCRIPT.md](docs/mvp/DEMO_SCRIPT.md).

1. **Database:** follow [docs/mvp/DEMO_DB.md](docs/mvp/DEMO_DB.md) (Docker,
   `pilot-delivery.zip`, `alembic upgrade head`, `scripts/mvp_import_pilot.py`,
   `verify_pilot`). Reset: `docker compose down -v`.
2. **Environment variable names** (values go in the gitignored `.env`, never in git):
   `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_PORT`,
   `DATABASE_URL`, `OPENAI_API_KEY`, `OPENAI_ANSWER_MODEL`, `AI_PROVIDER`,
   `RETRIEVAL_BACKEND`, `RETRIEVAL_MODE`, `SCISCOPE_AGENTIC_RETRIEVAL` (opt-in,
   default `0`). Full table in
   [docs/mvp/RUN_BACKEND.md](docs/mvp/RUN_BACKEND.md).
3. **Backend, live mode** (real retrieval and OpenAI answers):
   ```powershell
   $env:PYTHONPATH = "src"
   $env:RETRIEVAL_BACKEND = "postgres"
   $env:AI_PROVIDER = "openai"
   uv run --locked --env-file .env python -m sciscope.api.server
   ```
4. **Backend, zero-config fake mode** (no DB, no network; the UI shows a Demo badge):
   ```powershell
   $env:PYTHONPATH = "src"
   uv run --locked python -m sciscope.api.server
   ```
5. **Frontend** (proxies `/api` to `http://127.0.0.1:8000`):
   ```powershell
   cd frontend
   npm ci
   npm run dev
   # offline, no backend needed:
   $env:VITE_API_MODE = 'fixtures'; npm run dev
   ```

Known limits: the corpus is 17 papers; answers are generated from retrieved
passages and may be wrong; retrieval quality is not verified; only five
development questions were exercised live. See the "Known limits" sections of
`docs/mvp/DEMO_DB.md` and `docs/mvp/RUN_BACKEND.md`.

## Windows PowerShell prerequisites

Install these on **each developer computer**, outside this repository:

| Tool | Purpose | Install information |
| --- | --- | --- |
| Git | Branches and pull requests | [Git for Windows](https://git-scm.com/download/win) |
| Python 3.12 | Project interpreter, installed outside Git | [uv-managed Python](https://docs.astral.sh/uv/concepts/python-versions/) or [Python downloads](https://www.python.org/downloads/windows/) |
| uv | Local environment and lockfile | [uv installation](https://docs.astral.sh/uv/getting-started/installation/) |
| Codex | Spec Kit skills and coding workflow | [Codex setup](DEVELOPMENT_SETUP.md) |
| Node.js LTS | Future React tooling | [Node.js downloads](https://nodejs.org/en/download) |
| Docker Desktop | Future PostgreSQL/Compose services | [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/) |

Open a new PowerShell window after installation and check:

```powershell
git --version
uv --version
uv python list --only-installed
node --version
docker --version
specify --version
```

The `py` launcher is optional and may be absent even when uv has a managed
Python installation. If no Python 3.12 appears in uv's installed list, install
it on this computer with `uv python install 3.12` or the Python installer.
Check `codex --version` if you use the terminal CLI. The Codex IDE extension
can run the repository skills even when `codex` is not on PowerShell's `PATH`;
install the CLI separately using the
[official Windows instructions](https://learn.chatgpt.com/docs/codex/cli.md#windows)
if terminal use is needed.

Install the official Spec Kit CLI using its
[installation instructions](https://github.com/github/spec-kit), if missing.
This repository was initialized with Spec Kit 1.4.0 and Codex integration;
the local `$speckit-*` skills are in `.agents/skills/`. Check your active Codex
model in the model picker/session status. `.codex/config.toml` proposes
`gpt-6-luna`; it does not change an already running session. The coding
assistant model is separate from the application's AI provider.

## Local environment and dependencies

Python itself must be installed on each computer, either by uv or a separate
installer; it is not committed to Git. `.venv/` is the ignored project-local
environment. `.python-version` selects Python 3.12, and `pyproject.toml`
limits the project to that minor version until dependency compatibility is
reviewed. From the repository root, after Python 3.12 is available to uv:

```powershell
uv python list --only-installed
uv sync --locked
uv run --locked python --version
```

`uv sync` creates `.venv` if needed. An existing `.venv` created by `uv run`
can be used; no manual deletion is needed. If you deliberately require a
separately installed Python, first verify that uv can discover it, then use
`--no-managed-python` with the uv commands. `uv.lock` exists on `main`;
routine commands use `--locked`.

The lockfile records exact versions; all routine installs and CI use `--locked`,
so dependency changes need an intentional lockfile update. `pyproject.toml` has
only bootstrap
development tools (Ruff, pytest, mypy, and JSON Schema validation). Application
dependencies are added only through approved features. Earlier local setup
blockers are recorded in [EVIDENCE.md](EVIDENCE.md); the existence of the
lockfile does not establish that local sync or CI has passed.

Create a secret-free local configuration:

```powershell
Copy-Item .env.example .env
git check-ignore -v .env
```

`.env` is ignored and must never be committed. `AI_PROVIDER=fake` needs no API
key. The fake provider is a **future feature**, so there is no app to run in
fake mode yet. Once implemented, live Gemini will require an explicit provider
selection and valid key. Routine tests and CI must make no paid AI calls.

## Checks and manual verification

After dependency sync, run the applicable checks:

```powershell
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy .
uv run --locked pytest
```

There are no Python application files or feature tests in the bootstrap;
`mypy .` and `pytest` become meaningful when an approved feature adds them.
Validate both draft JSON Schemas after syncing:

```powershell
@'
import json
from pathlib import Path
from jsonschema import Draft202012Validator

for name in ("docs/DATA_CONTRACT.json", "evals/golden_questions.schema.json"):
    schema = json.loads(Path(name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    print(f"PASS: {name}")
'@ | uv run --locked python -
```

CI runs the available bootstrap checks and, when
tests exist, runs them with `AI_PROVIDER=fake` using the committed lockfile.

Manual verification is separate from automation. The task owner should follow
the exact commands and acceptance checks in the feature's `tasks.md`, inspect
the result, and record the observed outcome and explicit acceptance or
rejection in [EVIDENCE.md](EVIDENCE.md). No bootstrap task is marked complete
before that human confirmation.

## Feature workflow and skills

Use Codex chat skill invocations with a **dollar prefix**, such as
`$speckit-specify`. This is the installed Codex skill syntax, confirmed in the
[Spec Kit Codex integration documentation](https://github.github.com/spec-kit/integrations/codex.html)
and local `.agents/skills/speckit-*/SKILL.md` files. Invoke:

1. `$solution-research` before feature specifications and feature tests.
2. `$speckit-specify` to draft a feature specification; `$speckit-clarify` for
   essential unresolved decisions.
3. `$speckit-plan` for the technical plan, `$speckit-tasks` for small,
   owner-assigned tasks, and `$speckit-analyze` for consistency review.
4. Present the specification and plan for explicit human approval.
5. After approval, invoke `$google-python-engineering` for any Python work and
   `$speckit-implement` for one approved task at a time. Write a behavior test,
   observe RED, implement, and observe GREEN.
6. Run automatic checks; obtain manual human verification; record evidence;
   then update the feature tasks and [PROJECT_TODO.md](PROJECT_TODO.md).

The complete workflow is **Research → Spec → Plan → Tasks → Approval → RED
tests → Implementation → GREEN tests → Automatic verification → Human
verification → Evidence → DONE**. The
[development workflow](docs/DEVELOPMENT_WORKFLOW.md) and
[constitution](.specify/memory/constitution.md) define the gates. The two
repository-local skills supplement the official Spec Kit skills.

## Branches, review, and ownership

Keep `main` stable. Create a feature branch, submit a pull request using the
[PR template](.github/pull_request_template.md), and request at least one
reviewer. CI must pass before merge. Any shared contract change requires
review by affected module owners. Never commit credentials, local corpora,
model caches, embeddings, or local databases. Follow the
[team ownership map](docs/TEAM_OWNERSHIP.md),
[draft decisions](docs/DECISIONS.md), and
[evaluation plan](docs/EVALUATION_PLAN.md). The current
[golden dataset schema](evals/golden_questions.schema.json) defines a format,
not verified scientific data.
