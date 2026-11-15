# SciScope Evidence Ledger

This ledger records verification evidence; it does not grant approval or replace
feature specifications and task lists. Preserve earlier attempts, failures, and
corrections when appending new evidence. Do not infer human acceptance from
automated results or an assistant report.

## Status definitions

| State | Meaning |
| --- | --- |
| `PLANNED` | Work is recorded but has not started. |
| `IN_PROGRESS` | Work has started; required validations are incomplete. |
| `AUTO_VALIDATED` | Relevant automated checks passed; human verification remains. |
| `AWAITING_MANUAL_VERIFICATION` | Automated checks passed and the owner has been asked to verify. |
| `DONE` | Automated checks passed and explicit human acceptance is recorded. |
| `BLOCKED` | Work or a required check cannot proceed; the blocker is recorded. |

## Record template

Copy this section for each implemented task. Use `N/A` only when a field does
not apply and explain why. Use `NOT RUN` when a check was not attempted.

### [Task ID] — [Feature name and task title]

- **Owner:** Person 1 / Person 2 / Person 3 / Person 4 / TEAM
- **Feature specification and plan:** [paths and approved revision]
- **Current state:** PLANNED / IN_PROGRESS / AUTO_VALIDATED / AWAITING_MANUAL_VERIFICATION / DONE / BLOCKED
- **Files changed:** [paths]
- **Tests created or updated:** [paths, or N/A with reason]
- **RED result:** [command, actual result, and important output; or N/A with reason]
- **GREEN result:** [command, actual result, and important output; or N/A with reason]
- **Other automated checks:** [each exact command, PASS / FAIL / BLOCKED / NOT RUN, and important output]
- **Known issues and prior attempts:** [append; do not erase failures]
- **Awaiting human confirmation:** Yes / No

#### Human evidence

- **Verifier:** [name or role as supplied by the verifier; do not invent]
- **Verification date:** [date when known]
- **Exact manual commands or actions:** [commands/actions actually performed]
- **Observed outcome:** [verifier's report]
- **Explicit decision:** ACCEPTED / REJECTED / NOT PROVIDED
- **Final status:** [state consistent with evidence]

## Bootstrap documentation checks

This section records only checks actually run for the Part 2 documentation
bootstrap. It is not a task completion record and contains no human verification.

- **Scope:** Development workflow, evidence ledger, project backlog, evaluation
  plan, evaluation instructions, and JSON Schema.
- **Automated checks:**
  - `python --version` — BLOCKED: Python was not found; Windows suggested the
    Microsoft Store alias. Python-based checks were unavailable.
  - Initial `node -e` schema-check attempt — FAIL: PowerShell passed the script
    with quoting removed, producing a JavaScript syntax error. The check was
    rerun using a PowerShell here-string.
  - PowerShell here-string piped to `node` — PASS: Ajv Draft 2020-12
    `validateSchema` and compilation succeeded; an empty bootstrap dataset
    object with no scientific records validated against the schema. Ajv 8.17.1
    was available through the globally installed Angular CLI dependency.
- **Human verification:** NOT PROVIDED
- **Status:** AWAITING MANUAL VERIFICATION

The successful schema-check command was:

```powershell
@'
const fs = require('node:fs');
const Ajv2020 = require('<GLOBAL_NPM_ROOT>/@angular/cli/node_modules/ajv/dist/2020').default;
const addFormats = require('<GLOBAL_NPM_ROOT>/@angular/cli/node_modules/ajv-formats').default;
const schema = JSON.parse(fs.readFileSync('evals/golden_questions.schema.json', 'utf8'));
const ajv = new Ajv2020({ allErrors: true });
addFormats(ajv);
if (!ajv.validateSchema(schema)) {
  console.error(ajv.errors);
  process.exit(1);
}
const validate = ajv.compile(schema);
const emptyDataset = { dataset_version: 'bootstrap-empty', corpus_version: 'unpopulated', questions: [] };
if (!validate(emptyDataset)) {
  console.error(validate.errors);
  process.exit(1);
}
console.log('PASS: Draft 2020-12 schema validates and compiles; empty bootstrap dataset shape is valid.');
'@ | node
```

## Part 3 bootstrap checks (all three parts)

This is a bootstrap validation record, not feature completion or human
acceptance. Parts 1 and 2 are visible in `git log --name-status -4`; Part 3
changes remain uncommitted. Existing Part 2 workflow and evaluation documents
were reviewed and preserved.

| Check | Status | Actual observation |
| --- | --- | --- |
| `git status --short` before edits; `git log --oneline -12` | PASS | Working tree was clean; four commits through `0bcc259` were present. |
| `specify --version` | PASS | `specify 1.4.0`. Codex integration metadata and nine skill paths are present. |
| `codex --version` | PASS | `codex-cli 0.167.0-alpha.4.1`; command warned about inaccessible temporary alias cleanup. Active session model was not verified. |
| Spec Kit manifest hash check with `Get-FileHash -Algorithm SHA256` | PASS | All nine Codex skill files matched `.specify/integrations/codex.manifest.json`. |
| Presence review: constitution, `AGENTS.md`, local skills, workflow, README, `.env.example`, TODO, evidence, and `pyproject.toml` | PASS | All listed files exist. Presence is not team approval or runtime verification. |
| `python --version` | BLOCKED | Windows reported Python was not found and suggested the Microsoft Store alias. |
| `py -3.12 --version` | BLOCKED | PowerShell reported `py` is not recognized. |
| `uv venv .venv --python 3.12 --no-managed-python --no-python-downloads` | BLOCKED | `error: Could not acquire lock` / `failed to open file <UV_CACHE_DIR>\.lock: Access is denied. (os error 5)`. No workaround attempted. |
| `uv lock --no-managed-python --no-python-downloads` and `uv sync --locked --no-managed-python --no-python-downloads` | NOT RUN | Stopped after uv cache access blocker; `uv.lock` and `.venv` are absent. |
| `git check-ignore -v .env` | PASS | `.gitignore:2:.env` matched after copying `.env.example` to local `.env`. The file remains untracked and ignored. |
| Draft 2020-12 schemas via local Node/Ajv | PASS after one failed script attempt | Both `docs/DATA_CONTRACT.json` and `evals/golden_questions.schema.json` validated and compiled; an empty golden dataset shape validated. First attempt failed because the same schema ID was compiled twice in one Ajv instance; rerun reused the compiled validator. No scientific record was created. |
| Markdown local link check via Node | PASS | Local links in 14 Markdown files resolved. |
| `git diff --check` | PASS | No tracked-file whitespace errors reported. |
| Node whitespace/newline check | PASS | 18 changed or relevant files had final newlines and no trailing whitespace. |
| `git check-ignore -v .venv/ data/raw/example.xml data/embeddings/example.npy model_cache/example.bin` | PASS | All sample local artifact paths matched `.gitignore`; no corpus or model was created. |
| Python Ruff, pytest, mypy checks | NOT RUN | Python 3.12 and dependencies unavailable; there are no feature Python files or tests yet. |
| GitHub Actions CI run and YAML parser validation | NOT RUN | Workflow is uncommitted and no local YAML parser was found. Locked CI sync will fail until `uv.lock` is generated. |
| Human verification | NOT RUN | No human outcome or acceptance has been supplied. |

The successful Part 3 schema check was a PowerShell here-string piped to Node:

```powershell
@'
const fs = require('node:fs');
const Ajv2020 = require('<GLOBAL_NPM_ROOT>/@angular/cli/node_modules/ajv/dist/2020').default;
const addFormats = require('<GLOBAL_NPM_ROOT>/@angular/cli/node_modules/ajv-formats').default;
const ajv = new Ajv2020({allErrors: true});
addFormats(ajv);
let goldenValidate;
for (const path of ['docs/DATA_CONTRACT.json', 'evals/golden_questions.schema.json']) {
  const schema = JSON.parse(fs.readFileSync(path, 'utf8'));
  if (!ajv.validateSchema(schema)) throw new Error(`${path}: ${JSON.stringify(ajv.errors)}`);
  const validate = ajv.compile(schema);
  if (path.startsWith('evals/')) goldenValidate = validate;
  console.log(`PASS: ${path} Draft 2020-12 schema validates and compiles`);
}
if (!goldenValidate({dataset_version:'bootstrap-empty', corpus_version:'unpopulated', questions:[]})) {
  throw new Error('Empty golden dataset shape failed');
}
console.log('PASS: empty golden dataset shape');
'@ | node
```

After Python is available to uv and cache access works on a developer
computer, run the exact commands in the [README](README.md): generate
`uv.lock`, sync with `--locked`, and run the applicable checks. Obtain explicit
human review before marking any master backlog item done.

## Developer follow-up on Part 3 setup

The developer supplied these PowerShell results after the initial bootstrap
report. They are recorded separately from the earlier sandbox results; no
explicit human acceptance was supplied.

| Command | Status | Developer-reported result |
| --- | --- | --- |
| `py -3.12 --version` | BLOCKED | `py` was not recognized by PowerShell. |
| `specify --version` | PASS | `specify 1.4.0`. |
| `codex --version` | BLOCKED | `codex` was not recognized in this PowerShell session. The earlier Codex executable check ran in the agent environment. |
| `uv venv .venv --python 3.12 --no-managed-python --no-python-downloads` | BLOCKED | `No interpreter found for Python 3.12 in search path or registry`; uv said a managed download was available but downloads were set to `never`. |
| `uv lock --no-managed-python --no-python-downloads` | BLOCKED | Same `No interpreter found for Python 3.12` error. |
| `uv sync --locked --no-managed-python --no-python-downloads` | BLOCKED | Same `No interpreter found for Python 3.12` error. |
| `git check-ignore -v .env` | PASS | `.gitignore:2:.env` matched. |
| `uv run --locked ruff check .` | BLOCKED | Reported `Using CPython 3.12.16` and `Creating virtual environment at: .venv`, then stopped because `uv.lock` was missing. This does not show that Ruff ran. |
| `uv run --locked ruff format --check .` | BLOCKED | Stopped because `uv.lock` was missing. The formatter did not run. |
| `git diff --check` | PASS | No output was reported. |
| `git status --short` | PASS | Listed the uncommitted Part 3 files; `.venv` and `.env` were absent from the list. |

The agent subsequently confirmed that `.venv` exists and `uv.lock` does not.
Its own `uv python list --only-installed` attempt was BLOCKED by the same uv
cache `.lock` access error as the original sandbox run.
The interpreter source behind `Using CPython 3.12.16` was not established by
the supplied output; `uv python list --only-installed` can identify available
installations. The README now permits uv-managed Python on each developer
computer and lists `uv lock` followed by `uv sync --locked`. Locked checks,
dependency resolution, and CI remain unverified. Human acceptance: NOT PROVIDED.

## 2026-11-14 lockfile note

`uv.lock` now exists on `main`.

### F001 — PLOS pilot acquisition (T001–T008)

- **Owner:** Person 1
- **Feature specification and plan:** `specs/001-plos-pilot-acquisition/{spec.md,plan.md}`, approved 2026-11-14 by Person 1.
- **Current state:** DONE
- **Files changed:** `src/sciscope/plos_pilot/{__init__,config,doi,search,selection,metadata,download,cli}.py`, `src/sciscope/__init__.py`, `tests/plos_pilot/*` (conftest and test_config/doi/search/selection/download/metadata/cli), `data/pilot/{candidates.jsonl,screening.tsv,selection.tsv,manifest.jsonl,metadata.jsonl}`. Raw XML (17 files under `data/raw/plos/`) is local and gitignored.
- **Tests created or updated:** `tests/plos_pilot/*` (conftest and test_config/doi/search/selection/download/metadata/cli).
- **RED result:** Implementation groups A and B: exact per-group RED outputs NOT RECORDED. Fix round R1/R2 (2026-11-15): RED was observed locally for the new tests; three first stopped at `FileExistsError` caused by a bug in a test helper, which Codex then corrected.
- **GREEN result:** Person 1 ran implementation groups A and B tests locally and reported all passing. Fix round R1/R2: `uv run --locked pytest tests/plos_pilot/test_download.py tests/plos_pilot/test_metadata.py tests/plos_pilot/test_search.py -q` → 32 passed in 1.80s.
- **Other automated checks:** Fix round R1/R2: `uv run --locked ruff check .` → All checks passed; `uv run --locked ruff format --check .` → 54 files already formatted; `uv run --locked mypy src` → Success: no issues found in 9 source files. `git diff --check` and `git status --short`: Person 1 reported OK; output NOT RECORDED. Full `uv run --locked pytest -q` after the fix round: NOT REPORTED. CI on the feature PR (#2): first run FAILED at `uv run --locked ruff check .` with I001 (unsorted imports) in `tests/plos_pilot/test_cli.py`. The same check had passed locally because the ruff cache hid the error; `ruff check . --no-cache` reproduced it. Fixed by a follow-up commit (`ruff check --fix . --no-cache`), after which CI passed and the PR was squash-merged as 17279c6. Lesson: run ruff with `--no-cache` before pushing.
- **Known issues and prior attempts:** Live conflict path (same DOI, changed bytes): NOT RUN live; covered only by offline tests. Journal routes other than PLOS ONE: NOT VERIFIED (only PLOS ONE is configured). Eleven of the 870 candidates have a blank journal field in Solr (all PLOS ONE DOIs), so the downloader cannot route them; deferred. Observations for the later data-contract feature: language is stored as `EN`; license is sometimes free text instead of a URL; the first subjects value is `Research Article`.
- **Awaiting human confirmation:** No

#### Human evidence

- **Verifier:** Person 1
- **Verification date:** 2026-11-15
- **Exact manual commands or actions:** Live search and download in Person 1's terminal on 2026-11-14; human screening and selection; fix-round live check on 2026-11-15.
- **Observed outcome:** Live search used six query arms (title/abstract × `Apis mellifera`, `honey bee`, `honeybee`) with `doc_type:full` and `article_type:"research article"` filters. Per-arm counts matched the earlier observations; 870 unique candidates, 23 requests, and request spacing ≥ 6 s. Person 1 reviewed 24 candidates: 17 `measured_mellifera`, 2 `comparative_mellifera`, 2 `other_species_only`, and 3 `species_ambiguous`. The assistant proposed the initial shortlist, and Person 1 confirmed each decision. Abstracts were read for all 17 selected papers. Methods were read for the 3 candidates described as "honey bee" without a species; Person 1 recorded them as `species_ambiguous` and did not select them. The selection contains 17 DOIs, all `measured_mellifera`, all PLOS ONE (prefix `10.1371/journal.pone.`), with 8 human-assigned topics. First live download: Accepted 17, Duplicate 0, Conflict 0, Failed 0, Pending 0. Repeat live download: Accepted 0, Duplicate 17. Manifest `xml_sha256` equals the SHA256 of the local raw file for 17 of 17. Front matter has language `EN` and article type `research-article` for all 17. Licenses: 11 entries use `http://creativecommons.org/licenses/by/4.0/` and 6 are free-text CC BY statements. R1 live check (2026-11-15): one raw XML (`10.1371/journal.pone.0037017`) was deleted and download re-run; Person 1 reported OK (file restored, duplicate path). Details beyond "OK": NOT RECORDED.
- **Explicit decision:** ACCEPTED — Person 1 explicitly accepted SC-001..SC-004 on 2026-11-15 (statement supplied by Person 1 in chat).
- **Final status:** DONE
