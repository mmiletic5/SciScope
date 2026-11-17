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

### F002 — JATS parser, sections, and locators (T001–T008)

- **Owner:** Person 1
- **Feature specification and plan:** `specs/002-jats-parser-locators/{spec.md,plan.md,tasks.md,research.md}`, approved 2026-11-15 by Person 1, including the taxonomy mapping table. Amended 2026-11-15 with Person 1's approval after the real-data run: the normalized-heading table takes precedence over the `sec-type` table (spec FR-005 and the taxonomy section of plan.md).
- **Current state:** DONE
- **Files changed:** `src/sciscope/jats/{__init__,locator,parser,classify,source,cli}.py`, `tests/jats/{conftest,jats_fixtures,test_locator,test_parser,test_classify,test_source,test_jats_cli}.py`, `data/pilot/parse_report.json`, `.gitignore` (`data/processed/`), `PROJECT_TODO.md`, `specs/002-jats-parser-locators/*`. The generated `data/processed/pilot/{sections,paragraphs}.jsonl` are gitignored.
- **Tests created or updated:** `tests/jats/*` (labeled synthetic JATS only, offline). Per-file test counts: NOT RECORDED.
- **RED result:** Observed locally by Person 1 per group (short summaries only; full outputs NOT RECORDED): Group A (T001–T004) 57 failed, all `NotImplementedError`; T005 66 failed and 59 passed; T006 55 failed and 195 passed; T007 together with the precedence amendment 34 failed and 252 passed.
- **GREEN result:** Person 1 reported all tests passing after each group (outputs NOT RECORDED). Final full run in Person 1's terminal on 2026-11-15: `uv run --locked python -m pytest tests -q` → 286 passed in 3.53s.
- **Other automated checks:** `uv run --locked ruff check . --no-cache` → All checks passed!; `uv run --locked ruff format --check .` → 71 files already formatted; `uv run --locked mypy src` → Success: no issues found in 15 source files. `git check-ignore data/processed/pilot/sections.jsonl` and `git status --short`: Person 1 reported OK; output NOT RECORDED. CI on the feature PR (#4): all checks passed on commit 2de1046 (GitHub Actions on the PR; checks as shown by GitHub: Bootstrap checks / checks (pull_request)Successful in 10s). The file-based CLI tests use `tmp_path`, which the Codex sandbox could not run; they were run only in Person 1's terminal.
- **Known issues and prior attempts:** Real-data finding: PLOS tags the Discussion section with `sec-type="conclusions"` in 11 of the 12 papers that have a Discussion. With the original rule (`sec-type` first) the first committed report showed 29 sections of type `conclusions` and 10 of type `discussion`; after the amendment (heading first) the regenerated report shows abstract 23, introduction 17, methods 148, results 73, results_discussion 5, discussion 36, conclusions 3, other 14 (319 sections); the 11 disagreements remain listed in `type_conflicts`. Skipped element totals in the first committed `parse_report.json`: `fig` 82, `table-wrap` 39, `supplementary-material` 91, `disp-formula` 9, `list` 1, `inline-formula` 1. That report also had 14 `empty-section` warnings; their number equals the 14 `other` Supporting Information sections, but per-section correspondence was NOT VERIFIED. One body `<list>` (10.1371/journal.pone.0018808) is omitted from section text and counted under `list`; two `<list>` elements in `<back>` of 10.1371/journal.pone.0228161 are outside F002 scope (back matter is not parsed). Person 1's raw-XML search found 1 `<list>` in a body and 2 in a back, and no paragraph record has `list` in `omitted`, which explains the survey count of 2 against the report count of 1. Back-matter containers (`ack` in 16 papers, `ref-list` in 17) are listed in the report but not emitted. Tables, figure captions, references, formulas and lists are omitted and counted; their handling is deferred to F003. A quote copied from a PLOS article web page (rather than from console output) and checked with `check-quote`: NOT RUN. The pilot has no body-level paragraphs and no untitled sections; those paths are covered by synthetic tests only. The F004 contract reconciliation items listed in plan.md remain open.
- **Awaiting human confirmation:** No

#### Human evidence

- **Verifier:** Person 1
- **Verification date:** 2026-11-15
- **Exact manual commands or actions:** The plan.md PowerShell command set in Person 1's terminal: full pytest, `ruff check . --no-cache`, `ruff format --check .`, `mypy src`; measurement of the largest raw XML; two consecutive `parse` runs with `Get-FileHash` and `Compare-Object`; `verify-roundtrip`; listing of sections with `normalized_type` `other` from `sections.jsonl`; `show` outlines of three papers compared with their PLOS article pages; a raw-XML search for `<list>`; `show --abstract` and `check-quote` on 10.1371/journal.pone.0000395.
- **Observed outcome:** Largest raw XML: `10.1371%2Fjournal.pone.0228161.xml`, 223133 bytes; `MAX_XML_BYTES` is 4,194,304 (4 MiB), the smallest power-of-two MiB, at least 4, that is at least 16 times the largest file. SC-001: `parse` reported `Succeeded: 17; failed: 0`, and the committed report lists at least one abstract paragraph and body sections for all 17 papers. SC-002: `verify-roundtrip` → `Checked: 319 sections, 585 paragraphs across 17 papers; mismatches: 0`. SC-003: `Compare-Object` of two consecutive runs was empty; SHA256 in the order sections.jsonl, paragraphs.jsonl, parse_report.json: B41E3EF3F4930CEDCCA6607EAD5EE96B1DF1D7E400011B99D77D7EEE01644721, 4DF2C9A0133A2A70B07BD2CE6EB454B12148010D5B7C3FFC501DE1C821CF1080, 3BD0A61310EDF49FE00ECF9C31489110197C80E786AD9C5333D7ECDF0A63B426. SC-004: covered by automated offline tests with a synthetic wrong-digest file; not a manual check. SC-005: 14 sections of type `other`, all headed "Supporting Information"/"Supporting information"; Person 1 accepted the mapping and the result. SC-006: Person 1 compared outlines of 10.1371/journal.pone.0018808, 10.1371/journal.pone.0148740 and 10.1371/journal.pone.0037017 with their PLOS article pages and reported them consistent; per-paper counts NOT RECORDED. SC-007: on the abstract paragraph of 10.1371/journal.pone.0000395 (locator ending `/article[1]/front[1]/article-meta[1]/abstract[1]/p[1]`): the verbatim first sentence → `OK`, `matches: 1`, exit code 0; the same sentence with one word altered → `error: quote-absent`, exit 1; with a lower-cased first letter → `quote-absent`, exit 1; with extra spaces → `OK`, exit 0; the abstract section locator (without `/p[1]`) → `OK` with the paragraph locator reported, exit 0; a locator shortened to `front` → `error: invalid-target`, exit 2; a literal `<locator>` placeholder → `error: locator-malformed`, exit 2.
- **Explicit decision:** ACCEPTED — Person 1 explicitly accepted SC-001..SC-007 on 2026-11-15 (statement supplied by Person 1 in chat).
- **Final status:** DONE

### F003 — Section-aware chunking and embeddings (T001–T008)

- **Owner:** Person 1
- **Feature specification and plan:** `specs/003-chunking-embeddings/{spec.md,plan.md,tasks.md,research.md}`, approved 2026-11-15 by Person 1, subject to corrections A-E; Option A (paragraph chunks only) approved 2026-11-15.
- **Current state:** DONE
- **Files changed:** `src/sciscope/chunking/*`, `src/sciscope/embedding/*`, `src/sciscope/pipeline/{__init__,cli}.py`, `tests/chunking/*`, `tests/embedding/*`, `data/pilot/chunk_report.json`, `data/pilot/embedding_report.json`, `specs/003-chunking-embeddings/*`, `.gitignore` (commit e44e094 added `chunk_sample.txt`; intentionally kept, not reverted), `EVIDENCE.md`, `.env.example`, `docs/{DECISIONS,CHUNKING_STRATEGY,ARCHITECTURE}.md`, and `PROJECT_TODO.md`. Gitignored and generated locally: `data/processed/pilot/chunks.jsonl`, `data/embeddings/pilot/{vectors.f32,manifest.json,cache/}`. The committed embedding report is data/pilot/embedding_report.json.
- **Tests created or updated:** `tests/chunking/*` and `tests/embedding/test_embed_{provider,transport,store,pipeline,validate}.py` plus fixtures; labeled synthetic, offline, fake transport; no real article prose, no network, no key. Per-file test counts: NOT RECORDED.
- **RED result:** Group C Phase 1: `uv run --locked python -m pytest tests -q` -> 292 failed, 484 passed in 16.61s. Group D Phase 2 first run: 10 failed, 917 passed (all 10 "Environment read" failures, see Known issues). RED counts for Groups A, B and Group D Phase 1: NOT RECORDED.
- **GREEN result:** Final full run in Person 1's terminal on 2026-11-17: `uv run --locked python -m pytest tests -q` -> 928 passed. Run time: NOT RECORDED.
- **Other automated checks:** Person 1's terminal, 2026-11-17, plan.md command set: `ruff check .` PASS (All checks passed); `ruff format --check .` PASS (109 files already formatted); `mypy src` PASS (no issues found in 35 source files); `git diff --check` PASS (clean). Whether `ruff check` was run with `--no-cache`: NOT RECORDED. `validate --chunks-only` PASS: 728 chunks, 319 sections, 17 papers, 0 failures. Full `validate` PASS. CI on the feature PR (#5): first run FAILED (see Known issues); second run on branch commit e606f3a: PASS (checks); squash-merged as 705bc20.
- **Known issues and prior attempts:**
  - Group C Phase 1 RED exposed a Windows test bug (`git check-ignore --stdin` received "\r" because of text-mode stdin; failing assert in `test_embed_pipeline.py`); fixed in Group C Phase 2 (bytes to the subprocess, explicit decode).
  - Group D Phase 2 produced 10 failures "Environment read": tests patched `os.environ` globally with a raising spy and argparse/gettext reads locale variables; production code was correct. Fixed in Phase 2b with a recording environment that asserts no `OPENAI*` key is accessed, plus a static guard on the offline functions. Result 928 passed.
  - Commits: c267e41 (Group C Phase 2), 3d2d767 (tick T005/T006), 2980f27 (Group D WIP, 10 failing), 89b147b (Group D Phase 2b). Commits of Groups A and B: NOT RECORDED.
  - Estimator: B3 `utf8-bytes-div3-v1` is conservative on the pilot (reported usage 0.658 of the estimate) but has no per-input true-token bound; calibration is aggregate-only. Kept unchanged; cap 384 operational / 512 absolute unchanged.
  - Norm tolerance: observed norms 0.999368748..1.000662474 (maximum deviation about 6.6e-4); the validator tolerance stays 0.01 (about 15x headroom), deliberately not tightened toward float32 precision.
  - Hard splits: 2 of 728 chunks (one is a 1,250-character semicolon list in 10.1371/journal.pone.0037017); preferring `;` boundaries deferred.
  - Known limits recorded in plan.md and carried over: O(chunks x sections) `chunk_record` and O(chunks x paragraphs) `chunk-in-empty-section` scans (revisit around 500 papers in F005); a crash between a batch's cache-entry writes may double count usage (rare); `OPENAI_BASE_URL` set to an empty string gives `invalid-base-url`; an output path inside the cache directory is not checked; a partial set cut from a larger batch reports the larger batch's totals (visible through `provider_input_count`); the validator cannot prove offline that a vector belongs to its input text.
  - Not done / deferred: Golden v0 (PENDING; required before any model comparison, F005 quality check, retrieval evaluation or chunk-size decision); figure/table caption chunks (named follow-up after Golden v0); retrieval quality of chunks: NOT VERIFIED; D-004 local `multilingual-e5-small`: NOT RUN in F003; other journals than PLOS ONE: NOT VERIFIED. F004 handoff items (split JSONL on "\n" only, same provider/model/dimensions/query_prefix for queries, raw `(untitled)` in `section_path`, abstract chunks have no heading context) are listed in plan.md.
  - CI on the feature PR, first run: FAILED at `uv run --locked pytest` with a collection error in `tests/chunking/test_chunk_validate.py` (`ModuleNotFoundError: No module named 'tests'`). The file imported shared fixtures as `tests.embedding...`, which works under `python -m pytest` (adds the repo root to `sys.path`) but not under the bare `pytest` entry point that CI uses; local runs had used `python -m pytest`. Fixed by moving the file to `tests/embedding/test_chunk_validate.py` and importing the fixtures as `embed_validate_fixtures`, like the other embedding tests. After the fix both `uv run --locked pytest` and `uv run --locked python -m pytest tests` report 928 passed. Lesson: run the bare `uv run --locked pytest` before pushing.  
- **Awaiting human confirmation:** No

#### Human evidence

- **Verifier:** Person 1
- **Verification date:** 2026-11-17
- **Exact manual commands or actions:** The plan.md PowerShell command set in Person 1's terminal (full pytest, ruff check, ruff format --check, mypy src, `git diff --check`, `git status --short`; two consecutive `chunk` runs with `Get-FileHash`; `validate --chunks-only`; `embed --dry-run`; cold live `embed --provider openai --live`; warm rerun; `Compare-Object` of the three embedding files; full `validate`; norm summary); `Get-FileHash` over the five artifacts; trace with `python -m sciscope.jats.cli show` and `check-quote`, plus a negative control. A live probe `embed ... --live --limit 5` was run earlier the same day (probe norms 0.999657423..1.000201179).
- **Observed outcome:**
  - SC-001: 728 chunks over 319 sections of 17 papers; `validate --chunks-only` 0 failures (source-span coverage and section isolation checked by the validator).
  - SC-002: all inputs nonempty and within the 384 operational cap and 512 ceiling (validator); overflow handling before any network call is covered by offline tests.
  - SC-003: two chunk runs byte-identical; SHA256 `chunks.jsonl` 77DAC1D542D8DC4F55C205AE3DB2E92A4906091963760AED38F22B9D0005FDE1, `chunk_report.json` 475ABA74CF677E8CDD7CBA44707DCCF3124ADCCA36FF57E0DE5FAC0DD272FD6B (both unchanged since Group B). Cold live run: 101 API calls for 728 inputs, 0 retries. Warm run: 0 provider calls (console), and `Compare-Object` of `vectors.f32`, `manifest.json`, `embedding_report.json` between cold and warm was empty. SHA256 `vectors.f32` 68FBCEE7CDA50686C528F32A5078C7B8133D0E1DDCE826358D3740A0AA2FA98D, `manifest.json` 99185D5DB2F57726EA2224DFB66B67C413252AD6ABB120E58E4C01498561CA60, `embedding_report.json` B64819FA1487CA21B662E755D6D3E62E401E25D37809688C75E8D2D85180CC2F.
  - Calibration: aggregate reported `usage.total_tokens` 123740 vs estimated 188108, ratio 0.6578 (reported <= estimated, estimator ACCEPTED). Approximate cost: dry-run estimate 0.003762 USD; real about 0.0025 USD (123740 tokens at 0.02 USD per 1M tokens).
  - Model/dimensions: `text-embedding-3-small`, 1536; response model string matched.
  - `x-ratelimit-*` header values: NOT RECORDED.
  - Norms: min 0.999368748, max 1.000662474; full `validate` passed with tolerance 0.01.
  - SC-004: covered by automated offline tests (transient/permanent failures, malformed/short/out-of-order responses, cache resume/corruption, shape and norm checks, secret leakage); not a manual check.
  - SC-005: report contents contain counts and provenance without article prose, credentials or absolute paths (checked by the `report-impure` validator rule). Trace: chunk `86cf79fc1ec73244ad373940b8d5a48d98e1c4c1d49f66a7ba61a21907170e89` in section `10.1371/journal.pone.0000395#abstract`, xml_sha256 `ee0fc718e4c1c16b2d75347939f618091229ba8b26be6257c13bf29f8816668f`, locator ending `/article[1]/front[1]/article-meta[1]/abstract[1]/p[1]`; `show` printed that section and its first paragraph begins with the sampled quote (80 characters, taken from the chunk's first span start); `check-quote` -> `OK`, `matches: 1`, exit 0; negative control (quote plus " zzz") -> `error: quote-absent`, exit 1. The sampled chunk is an abstract chunk; a body-section chunk was not traced (NOT RUN).
  - SC-006: see decision.
- **Explicit decision:** ACCEPTED - Person 1 explicitly accepted SC-001..SC-006 on 2026-11-17 (statement supplied by Person 1 in chat).
- **Final status:** DONE
