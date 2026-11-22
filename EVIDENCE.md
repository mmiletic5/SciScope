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

- **F001 correction observed during F004 (2026-11-18):** The committed `data/pilot/metadata.jsonl` is the source: language is 4 `"EN"` and 13 `"en"` (raw xml:lang), not `"EN 17/17"`. The original F001 record above is preserved.

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

### F004 — Data contract refresh and pilot delivery (T001–T007)

- **Owner:** Person 1; shared-contract and received-package reviewer: Person 2.
- **Feature specification and plan:** `specs/004-data-contract-delivery/{spec.md,plan.md,tasks.md,research.md}`; specification and plan approved by Person 1 on 2026-11-17, including R22, R28, R29, the D5 manifest-entry ID mapping amendment and paper-level abstract exclusion. T007 docs-only synchronization explicitly authorized on 2026-11-18.
- **Current state:** DONE.
- **Authorization and scope:** Groups A–F GREEN as supplied by Person 1; this session changes documentation and task state only. No source, tests, data, dependencies, network, live provider calls, staging, commit or push. T001–T006 checked at Person 1's explicit instruction; T007, P2-20 and P2-24 remain unchecked. These task ticks do not constitute feature acceptance. Stop after F004; no F005 or Golden work.
- **Files changed:** F004 implementation described in plan.md: `docs/DATA_CONTRACT.json`, `src/sciscope/delivery/{__init__,contract,papers,package,publish,validate,reader}.py`, delivery CLI wiring, `tests/delivery/*`, `.gitignore` and feature artifacts. This T007 session edits only `EVIDENCE.md`, `PROJECT_TODO.md`, `docs/{DATA_MODEL,DECISIONS,CHUNKING_STRATEGY,ARCHITECTURE,DELIVERY_GUIDE}.md` and `specs/004-data-contract-delivery/{plan,tasks}.md`. The generated six-file package and ZIP are gitignored; `data/pilot/delivery_manifest.json` is visible but UNTRACKED, left for the user to add/commit.
- **Research:** Applied `solution-research` for a brief internal check against the approved research/plan, single schema, declarative runtime shapes, reader, writer, validator and `_join_pieces`. Retain the existing flat six-file format, stdlib runtime and manifest-entry ID join; no new design or dependency. Applied `google-python-engineering` to read-only Python/example inspection. No network permitted: external documentation, current versions/licenses and installed pgvector compatibility were NOT VERIFIED in this session; earlier official-source research remains attributed to research.md/plan.md.
- **Tests created or updated:** NONE in this docs-only session. Groups A–F used the existing synthetic offline delivery tests; no paid AI test calls.
- **RED/GREEN checks:** The following are reported observations, not pytest reruns by this assistant. Person 1's environment: Windows PowerShell 5.1, Python 3.12, `uv run --locked`; focused command `uv run --locked python -m pytest tests/delivery -q`, whole-suite command `uv run --locked pytest -q`.

  | Group | RED | GREEN (delivery / whole suite unless noted) | Evidence distinction |
  | --- | --- | --- | --- |
  | A (T001–T002) | NOT RECORDED | Focused observed count NOT RECORDED / 1638 passed | User-reported local GREEN in Group B addendum; 710 focused is a prediction, not an observed count |
  | B (T003) | NOT RECORDED | Focused observed count NOT RECORDED / 1711 passed, 1 skipped | Combined A/B user-reported GREEN in Group C addendum; predicted RED not promoted to observation |
  | C (T004) | Whole suite: 483 failed, 1711 passed, 2 skipped | 1266 / 2194 passed, 2 skipped | Person 1 supplied observation |
  | D (T005 library) | 145 failed, derived by reviewer; user said only expected tests failed | 1411 / 2339 passed, 2 skipped | Exact user RED count NOT RECORDED; derivation identified explicitly |
  | E (T005 CLI/staging) | 122 failed (114 NotImplementedError + 8 AssertionError), 1411 / 2339 passed, 2 skipped | 1533 / 2461 passed, 2 skipped | Person 1 supplied observation |
  | F (T006) | New file: 110 failed, 2 passed; delivery: 1535 passed, whole suite: 2463 passed, each plus 110 failed and 2 skipped | Reader file: 129 passed; delivery: 1662 passed, 2 skipped; whole suite: 2590 passed, 2 skipped | Person 1 supplied observation |

  The two final Windows skips are symlink tests: this account lacks symlink privilege. They were skipped, not passed. Per-group timings and additional observed outputs not supplied above: NOT RECORDED.
- **Other automated checks / independent AI review:** Person 1 reports Claude on Linux, Python 3.13, at HEAD `3a49cb6`: whole suite 2592 passed; `mypy src` clean (42 files). Throwaway reference implementations for Groups C–F were kept outside the repository and diffed against Codex code. Differential fuzz: reader 5,500 cases; CLI argv 1,500 cases; no differences, exceptions or content leaks. This is independent AI review, NOT human verification and NOT branch CI. Post-documentation pytest, Ruff and mypy: NOT RUN in this session; exact user commands follow in the handoff. Static document/link/format and diff checks are recorded separately below.
- **Known issues and prior attempts:** Person 1's first body-trace helper reported `text-matches: False` because it joined every span with `"\n\n"`. The helper was corrected to preserve source characters between same-paragraph spans. This was a script error, not a data defect. Omitted content remains 223 skipped elements and 33 back-matter exclusions; abstract chunks lack heading context; exactly 2 hard splits; O(n²) validator scans; no offline proof of vector origin or retrieval-quality claim. Golden v0 is PENDING and out of scope.
- **Awaiting human confirmation:** No; Person 1 acceptance is recorded below. Person 2 PR review: NOT PERFORMED by team agreement (not a failure). Person 2's verification of the received extracted package: NOT RUN. Branch CI passed per Person 1 on 2026-11-18; the docs-only close-out CI result is NOT RECORDED, and Person 1 waits for it to be green before squash merge. Installed pgvector version is NOT VERIFIED. Live provider calls in F004: none (NOT RUN).

#### Human evidence

- **Verifier:** Person 1, as reported in the task instructions; assistant checks below are separate.
- **Verification date:** 2026-11-18 unless otherwise stated; exact dates for individual group test runs beyond the supplied record are NOT RECORDED.
- **Exact manual commands or actions:** Real-pilot `deliver`, `validate-delivery`, six-file hash comparison after rerunning `deliver`, manifest-copy hash comparison, missing-file/truncated-vector negative controls on a copy, guide block 1, local-XML source traces and reconstruction of every chunk. Archive command: `tar -a -c -f data/delivery/pilot-delivery.zip -C data/delivery pilot`; extraction with `tar -x -f` into a fresh temporary directory; then `validate-delivery --package-dir <temp>/pilot` using the three committed parse/chunk/embedding reports. Exact additional argv not supplied: NOT RECORDED.
- **Observed outcome:**
  - Real package `data/delivery/pilot/`: `validate-delivery` exit 0, `validated delivery papers: 17 sections: 319 chunks: 728 vectors: 728 files: 6 failures: 0`.
  - Repeated `deliver` on the same inputs: all six file hashes identical (`identical: True`), exit 0. Package manifest and `data/pilot/delivery_manifest.json` SHA256 identical (`True`); the latter is not yet tracked or claimed committed.

  | Package file | Bytes | SHA256 (Person 1 observation) |
  | --- | ---: | --- |
  | chunks.jsonl | 1,264,011 | 77DAC1D542D8DC4F55C205AE3DB2E92A4906091963760AED38F22B9D0005FDE1 |
  | delivery_manifest.json | 2,518 | 998241789FD9675853962BDFDF98B15B0991BC4CDA103413B0ABC470666AF9D2 |
  | embedding_manifest.json | 137,860 | 99185D5DB2F57726EA2224DFB66B67C413252AD6ABB120E58E4C01498561CA60 |
  | papers.jsonl | 23,145 | 2E3B1A920BC123325F78D62FA18F2164ACAC1DAD9B20CC8B41F102A4F72FC9A1 |
  | sections.jsonl | 211,478 | B41E3EF3F4930CEDCCA6607EAD5EE96B1DF1D7E400011B99D77D7EEE01644721 |
  | vectors.f32 | 4,472,832 | 68FBCEE7CDA50686C528F32A5078C7B8133D0E1DDCE826358D3740A0AA2FA98D |

  - Text comparison with existing evidence confirms `sections.jsonl` equals the F002 recorded hash; `chunks.jsonl`, `embedding_manifest.json` (F003 name `manifest.json`) and `vectors.f32` equal the F003 recorded hashes. This compares evidence text, not freshly read payload bytes.
  - Negative controls on a copy: missing `sections.jsonl` → `delivery-missing-file`, exit 2. `vectors.f32` truncated by one byte → exit 1, four failures: `delivery-integrity-mismatch`, `delivery-report-mismatch`, `vectors-sha-mismatch`, `vectors-size`.
  - Windows PowerShell 5.1 archive creation exit 0; SHA256 `6FA27AFAF334D6A87BE30A04F3D15A9573696C7C03DDCC5205C23D508F239F2C`. Archive bytes are NOT deterministic: this hash identifies this one file, which must be sent. Recreating it changes the hash and requires a new EVIDENCE line. Fresh-temp extraction exit 0 yielded six files with the sizes above. Extracted-package validation with the three committed reports exit 0, same success line (17/319/728/728, files 6, failures 0). Person 2's received extracted-package verification: NOT RUN.
  - Reader guide block 1: `vectors_by_chunk_id` returned 728 vectors × 1536 dimensions; every chunk ID has a vector. Chunk-file order differs from vector order at 727 of 728 positions; manifest-entry ID ownership is essential.
  - Abstract trace: chunk `86cf79fc1ec73244ad373940b8d5a48d98e1c4c1d49f66a7ba61a21907170e89`, `10.1371/journal.pone.0000395#abstract`, 1 span. Body trace: chunk `29ec463c4e1d3f4172ce42b0388445be08ca8d98df7a7e683dcc2fff7d77e04f`, `10.1371/journal.pone.0000395#sec-1`, 2 spans. Human-run guide helper used local XML in `data/raw/plos`; XML SHA256 matched. For both chunks, `check-quote` of the first span's slice exited 0; the same slice plus `" ZZZ"` exited 1 (negative control). No source prose is copied here.
  - All 728 chunk texts reconstructed from spans: 0 mismatches, 5 same-paragraph joins. Rule from `chunking/core.py::_join_pieces`: consecutive spans of the same paragraph retain the source characters between them; spans of different paragraphs join with `"\n\n"`. The initial body helper error and its correction are recorded above.

#### Criterion mapping and documentation review

| Criterion | Status and evidence |
| --- | --- |
| SC-001 | PASS — Person 1-run real-package and extracted-package validation, 17 papers / 319 sections / 728 chunks, 0 failures |
| SC-002 | PASS for reported six-file two-run identity and identical local manifest copy; committing that copy remains the user's action, NOT VERIFIED |
| SC-003 | PASS, automated synthetic coverage only for the full six-kind/partial-set matrix (Groups B–E GREEN); Person 1 also ran the two real-copy negative controls above |
| SC-004 | PASS — automated parity coverage GREEN (Groups A/C); branch CI `check_schema` passed per Person 1, reported on 2026-11-18 |
| SC-005 | PASS — Person 1-run reader 728 × 1536 with every chunk ID mapped; 727 positional mismatches explicitly observed |
| SC-006 | Static review PASS for no real article prose, actual credentials or actual machine absolute paths in the reviewed file set; existing literal examples described below. Human PR review and eventual committed manifest state NOT VERIFIED |
| SC-007 | PASS — static review of plan.md R01–R29 and draft 0.3.0 docs, including omitted content, versions, raw language, locators and manifest ID mapping |
| SC-008 | PASS — branch CI passed per Person 1 on 2026-11-18; Person 2 PR review: NOT PERFORMED by team agreement (not a failure); Person 1 acceptance recorded below |
| FR-010 | COMPLETE — evidence/docs/task state synchronized; branch CI pass and Person 1 acceptance recorded; Person 2 PR review not performed by team agreement. Person 2 received-package verification remains NOT RUN; docs-only close-out CI result NOT RECORDED, awaited before squash merge |

- **Assistant static review (this session):** Visible untracked manifest reviewed read-only: no article text, secrets, absolute paths, timestamps or self-hash; `Get-FileHash` equals `998241789FD9675853962BDFDF98B15B0991BC4CDA103413B0ABC470666AF9D2`. No package/data files were generated or changed. `git diff --name-only 8c51817..HEAD` at HEAD `3a49cb6` lists exactly `docs/DELIVERY_GUIDE.md`, `specs/004-data-contract-delivery/plan.md`, `src/sciscope/delivery/reader.py`, `tests/delivery/test_deliver_reader.py`; these and all nine documentation files edited here were inspected. They contain documentation, synthetic examples, hashes and identifiers, with no real article prose or actual credentials/machine absolute paths found. A literal Windows-path guard is present in the test/plan, and the historical plan contains an explicitly invented synthetic timestamp; documentation also has dated evidence. Thus literal timestamp/path-pattern absence across every reviewed file is NOT claimed. Timestamp/self-hash prohibition applies to the new manifest; retained paper `retrieved_at` and copied embedding `creation_date` are intentional upstream fields. No committed-state or exhaustive secret-scanner guarantee is claimed.
- **Documentation checks (assistant, 2026-11-18):** Direct local `.venv/Scripts/ruff.exe format --check` over the nine edited Markdown files → PASS, 9 files already formatted (not a locked-tool result). Static read-only checks → PASS: 18 relative links resolve, 9 Markdown Python blocks parse; guide is 114 lines / 828 words, DATA_MODEL is 72 lines; guide first-block/never-zip rules, required keywords, forbidden substrings and unchanged Python examples checked against the existing guide requirements. Committed metadata case-sensitive counts → 4 EN / 13 en. `git diff --check` → PASS. Source/test/data tracked diff → none; untracked manifest left unchanged. These are documentation checks, not pytest or CI; all six post-edit user commands are listed in plan.md, with locked pytest/Ruff/mypy NOT RUN here.
- **Explicit decision:** ACCEPTED - Person 1 explicitly accepted SC-001..SC-008 on 2026-11-18 (statement supplied by Person 1 in chat).
- **Final status:** DONE

#### CI and close-out

- **Source:** Facts supplied by Person 1 in chat on 2026-11-18; no network verification or local rerun by this assistant.
- **Branch CI:** Pull-request workflow `Bootstrap checks`, job `checks`: PASSED, reported by Person 1 on 2026-11-18. PR number: NOT RECORDED. CI run link/id: NOT RECORDED. Commit covered by the run: NOT RECORDED. The branch tip reviewed by Claude before the PR was `6ada8400c6e0eecfa427c66ee1714fc8aebf1c39`; this is not asserted to be the CI-covered commit. CI duration and per-step timings: NOT RECORDED.
- **Close-out CI:** This docs-only close-out commit triggers one more CI run on the same PR. Its result is NOT RECORDED here; Person 1 waits for it to be green before squash merge. No commit is created by this assistant.
- **Team agreement:** Person 1 reports a verbal Discord agreement: Person 2 does not review the PR; she receives the verified archive plus an explanatory handoff and continues independently. Person 2 PR review: NOT PERFORMED by team agreement (not a failure). Person 2's verification of the received extracted package: NOT RUN.
- **State synchronization:** T007 and P2-20 checked following the supplied acceptance; P2-24 remains unchecked. Earlier session scope and observations above are retained as historical evidence. D-007 remains Proposed; Person 1 decides separately.
- **Checks handoff:** Person 1 runs `uv run --locked pytest -q`, `uv run --locked ruff check . --no-cache`, `uv run --locked ruff format --check .`, `uv run --locked mypy src`, and `git diff --check`. These commands are NOT RUN by this assistant during this close-out.

### Golden v0 small change — Documentation, data, and optional question type

- **Owner:** Person 1; later human-written question contribution: Person 2.
- **Date:** 2026-11-18.
- **Scope and authorization:** Explicit small-change track requested in chat:
  documentation, the supplied dataset, and one optional schema property. No
  Spec Kit artifacts, Python changes, new feature tests, or subsequent feature.
- **Current state:** AUTO_VALIDATED; PR review and acceptance of this change
  remain pending. P2-22 and P2-23 remain unchecked; no checklist box changed.
- **Files changed:** `evals/golden_questions.schema.json`,
  `docs/EVALUATION_PLAN.md`, `evals/README.md`, `PROJECT_TODO.md`, and
  `EVIDENCE.md`. Dataset `evals/golden_questions.v0.json` was already supplied
  untracked by Person 1 and remains untracked and byte-identical; no staging,
  commit, or push. No changes to `src/`, `data/`, or `docs/DATA_CONTRACT.json`.
- **Research check:** Applied `solution-research` as a brief internal check of
  the existing schema, schema tests, CI workflow, evaluation documentation, and
  small-change workflow. Reused the installed `jsonschema` and Draft 2020-12
  CI approach; no new dependency or external compatibility claim. No external
  research was needed for the explicitly prescribed optional property.
  Applied `google-python-engineering` for read-only Python test inspection and
  validation commands. No Python files were added or edited.
- **Schema:** Added only optional `question_type` immediately after
  `question_id`, with the five requested enum values and a short description.
  Compared against HEAD after removing that property: structurally identical.
  `required`, `additionalProperties: false`, `$id`, and version fields are
  unchanged; no applicable repository convention requiring a version bump was
  found.
- **Dataset identity:** SHA-256 checked before edits and again after edits:
  `16a47954951c2c7ade6f9ef69dc232c8520d1debb042135cea5733b970180746`.
  File bytes were never written. LF-only bytes confirmed; Git attributes
  resolve to `text: auto`, `eol: lf`.
- **Recomputed corpus identity:** Read 17 entries from
  `data/pilot/manifest.jsonl`, sorted the UTF-8 `<doi>\t<xml_sha256>\n` lines,
  including the final LF, and computed SHA-256:
  `1fff1573b610c27e2e8016343d2f6429df294db974db4af898c4a0f82ffc26bd`.
  Derived `corpus_version`: `pilot17-xml-1fff1573b610`. This hashes the source
  XML identities recorded in the manifest; individual XML files were not
  rehashed. Parser, chunking, and embeddings do not enter this recipe.
- **Metadata checks:** `dataset_version: "v0"`; 21 questions (8 factual,
  4 comparisons, 3 conflicting-evidence, 3 research-gap, 3 insufficient-evidence);
  33 quotations; 12 distinct papers; every record has reviewer `"Person 1"`,
  status `"verified"`, date `"2026-11-18"`, and matching source corpus version.
  These are checks of recorded metadata, not independent scientific review.
- **Tests created or updated:** NONE; this is the prescribed small change.
  No RED claim is made. Existing schema tests were run unchanged.
- **Automated checks (assistant, local installed tools, not locked uv runs):**
  - PowerShell inline scripts piped to
    `.venv/Scripts/python.exe -X utf8 -`: PASS — loaded schema and dataset with
    `json`; `Draft202012Validator.check_schema(schema)`;
    `Draft202012Validator(schema, format_checker=FormatChecker()).validate(dataset)`;
    metadata counts, schema comparison against HEAD, hashes, and LF checks.
  - `.venv/Scripts/python.exe -m pytest tests/test_golden_schema.py -q -p no:cacheprovider`:
    PASS — 3 passed.
  - `.venv/Scripts/ruff.exe format --check docs/EVALUATION_PLAN.md evals/README.md PROJECT_TODO.md EVIDENCE.md`:
    PASS — 4 files already formatted. This is the repository's existing
    documentation formatting check; no formatter was applied to the dataset.
  - `git diff --check`: PASS.
  - `git check-attr text eol -- evals/golden_questions.v0.json`: PASS —
    `text: auto`, `eol: lf`. Byte checks also confirm LF in all five edited files.
- **Not run / verification limits:** `golden_check.py ... --final` could not be
  run because that external helper/path was not supplied and no repository copy
  was found. The full `uv run --locked pytest -q`,
  `uv run --locked ruff check . --no-cache`,
  `uv run --locked ruff format --check .`, and `uv run --locked mypy src`
  were NOT RUN, left for Person 1's stated local checks; no sandbox rejection
  of those commands is claimed. Branch CI, independent reading of all cited
  passages, and fresh `check-quote` verification of the 33 quotations were NOT
  RUN by the assistant. No live AI calls or evaluation runs were performed.
- **Known limitations:** All 21 questions are AI-drafted and human-verified;
  the planned approximately 30% human-written questions remain open for a later
  version (Person 2). Conflicts are author-versus-prior-literature within one
  paper. Insufficient-evidence cases rely on lexical search plus reading,
  support rather than prove absence, and omit tables, captions, formulas, and
  supplementary material from chunks. All evidence is from body paragraphs,
  none from abstracts. Coverage of 12 of 17 papers is an indicative regression
  signal, not a statistical estimate. No evaluation results were produced.
- **Human approval:** reported by Person 1 in chat on 2026-11-18.
  Person 1 reports reading and verifying EVERY record and machine-checking all
  33 quotations verbatim with `check-quote`. These are supplied curation facts;
  no additional human approval, assistant source verification, PR review, or
  completed-task decision is inferred.
- **Outstanding decisions:** None within the requested change. Human-written
  questions, broader evaluation, and PR review remain outside this scope.

### Person 3 Phase 0 — Baseline, environment, and integration readiness

- **Owner:** Person 3 (Backend & AI).
- **Current state:** AUTO_VALIDATED from user-supplied terminal evidence;
  documentation-only record awaiting human review. This is not approval for a
  Person 3 feature and does not complete P4-01 through P4-21.
- **Detailed record:** `docs/person3/PHASE_0_BASELINE.md` is the chronological
  source for the scope, provenance of reported results, environment setup,
  diagnostics, database checks, test matrix, limitations, and next checkpoint.
- **Repository baseline:** User-reported and documentation-session-checked
  `main` at `c70507e7c686214528b69aab4566786320c5f43c`, clean before this
  documentation update. Person 1 and Person 2 code and documentation are not
  changed by this record.
- **User-executed setup and static checks:** uv 0.13.9 installed CPython
  3.12.16; locked sync created a local 87-dependency environment. Ruff check,
  Ruff format check, and `mypy src` passed; the detailed report preserves the
  exact supplied commands and 286-file/78-source-file outputs.
- **User-executed tests:** Offline selections total **2,816 passed** across
  separate commands. PostgreSQL initial import, rollback, retrieval/lookup, and
  pipeline selections add 3, 8, 14, and 1 passes. **Aggregate: 2,842 passed**
  (`2816 + 3 + 8 + 14 + 1`), explicitly not a single full-suite pytest run.
  Synthetic evaluation coverage is not protected held-out evaluation.
- **Database evidence:** The dedicated `sciscope_test_005` PostgreSQL 17.11 /
  pgvector 0.8.7 database received only migration
  `f005_pgvector_foundation` and an explicit guarded pilot initialization.
  Reported active snapshot counts are 17 papers, 319 sections, 728 chunks, and
  728 vectors; the development database remained at zero application tables.
  The record does not expose connection data.
- **Retained failure history:** Initial temporary JATS/chunking and embedding
  failures were caused by incomplete temporary snapshots. Initial database
  fixture/Compose failures were traced to CRLF formatting and stale inherited
  local environment values, not a demonstrated importer/retrieval defect.
- **Limits and gates:** No live provider call, paid embedding, protected
  evaluation, FastAPI/backend implementation, production deployment, or
  answer-quality claim occurred. The public retrieval facade and Person 3 API
  integration remain subject to cross-owner review and P1-11/P1-14 gates.
- **Documentation-only verification:** No test, static check, database command,
  Docker command, or provider call was rerun by the documentation assistant.
  Exact source/test changes: NONE. `PROJECT_TODO.md` remains unchanged because
  no dedicated Person 3 baseline checklist item exists and broad foundation
  items cannot be checked without the required acceptance gate.

### Feature 011 — Fake-only Backend Question API

- **Owner:** Person 3 (Backend & AI).
- **Feature specification and plan:** [`specs/011-fake-backend-api/spec.md`](specs/011-fake-backend-api/spec.md) and [`plan.md`](specs/011-fake-backend-api/plan.md), approved for Feature 011's fake-only scope at revision `4309b22becef529940f86068329b01a6a5e862f9`.
- **Current state:** DONE within the approved fake-only, deterministic, offline scope. Feature-level human acceptance is recorded below. This does not mark broader Phase 4 integration work complete.
- **Implementation:** T001–T008 are implemented and committed through `1e18da5841f623be64c605fd808c7685eeb8bce4` on branch `011-fake-backend-api`. Individual task evidence and prior attempts are preserved in [`docs/person3/FEATURE_011_TEST_LOG.md`](docs/person3/FEATURE_011_TEST_LOG.md).
- **Automated verification:**
  - `uv run --locked pytest tests/backend/test_question_api.py -v` — PASS, exit `0`; 10 passed in 0.75s (post-commit run, 2026-11-21).
  - `uv run --locked pytest tests/backend/ -v` — PASS, exit `0`; 67 passed in 0.75s (post-commit run, 2026-11-21).
  - `uv run --locked mypy src/sciscope/api src/sciscope/question_service` — PASS, exit `0`; no issues in 10 source files.
  - `uv run --locked ruff check src/sciscope/api/app.py src/sciscope/api/routes.py tests/backend/test_question_api.py` — PASS, exit `0`.
  - `uv run --locked ruff format --check src/sciscope/api/app.py src/sciscope/api/routes.py tests/backend/test_question_api.py` — PASS, exit `0`; three files formatted.
  - `git diff --check` — PASS, exit `0`.
  - The first focused test invocation was blocked before pytest by uv's cache write restriction (exit `2`); it was rerun with approved cache-write permission and passed. This was not a test failure.
- **Manual evidence:** The user reported three successful T008 TestClient checks using explicitly injected fakes: controlled unavailable/timeout mappings, invalid response-contract rejection, and sanitized unexpected-error handling with developer observability. Details and observed values are retained in the test log; these were reported user-executed checks, not rerun in the post-commit verification.
- **Human evidence:**
  - **Verifier:** Mateja Miletic — Person 3 (Backend & AI).
  - **Verification date:** 2026-11-22.
  - **Review scope:** FR-001–FR-018, NFR-001–NFR-004, SC-001–SC-005; T001–T008 implementation; recorded automated verification; user-executed manual HTTP verification; and final readiness audit.
  - **Observed outcome:** Reviewer reports the requirements and evidence reviewed and accepts Feature 011 within its approved fake-only, deterministic, offline scope.
  - **Explicit decision:** ACCEPTED.
  - **Limitations:** Acceptance excludes live Gemini integration, production deployment, real corpus/retrieval integration, and scientific correctness of generated answers. Citation validation proves synthetic response-local identity membership, not scientific support.
- **Final status:** DONE for Feature 011's approved scope. Broader real-provider, retrieval, deployment, and scientific-quality work remains open and is not accepted by this record.

### Feature 007 — Public Retrieval Facade (T007)

- **Owner:** Person 3 (Backend & AI), with Person 2 retrieval review and
  Person 1 provenance/source-mapping review recorded in the chronological log.
- **Scope and artifacts:** [`spec.md`](specs/007-phase-b-retrieval-core/spec.md),
  [`plan.md`](specs/007-phase-b-retrieval-core/plan.md), and
  [`tasks.md`](specs/007-phase-b-retrieval-core/tasks.md). The complete
  chronological implementation, correction, verification, and decision record
  is [`docs/person3/FEATURE_007_T007_TEST_LOG.md`](docs/person3/FEATURE_007_T007_TEST_LOG.md).
- **Implementation history:** T007-B public DTOs/errors:
  `df104b966c1a5725f50f1f8845f79366fa5c6b9f`; T007-C public facade and
  composition: `d2262668dbb4afbf2ad5a34c9423a0db7244d55e`; T007-D offline
  conformance: `6c7748147fb0c3a47d26f8a0deb4dbdd58764a4f`; T007-E review
  package: `97ea843407e0424a388a7206f182b5c72a4f4f08`.
- **Automated verification:** T007-F-01, run by Codex on 2026-11-22:
  - `uv run --locked pytest tests/retrieval/test_public_service.py tests/retrieval/test_public_contracts.py tests/retrieval/test_errors.py` — PASS, exit 0; 66 passed.
  - `PYTHONPATH=. uv run --locked pytest tests/retrieval/test_validation.py tests/retrieval/test_core_offline.py tests/retrieval/test_v2_bm25.py` — PASS, exit 0; 43 passed.
  - `PYTHONPATH=. uv run --locked pytest tests/retrieval -q --ignore=tests/retrieval/test_postgres_core.py --ignore=tests/retrieval/test_postgres_lookup.py --ignore=tests/retrieval/test_phase_c_pipeline.py --ignore=tests/retrieval/test_public_postgres.py` — PASS, exit 0; 154 passed. PostgreSQL-backed tests were explicitly excluded from this offline regression.
  - Ruff lint, Ruff formatting, mypy (13 source files), and `git diff --check` — PASS, exit 0.
- **Database integration evidence:** The chronological log records separately
  authorized Ubuntu migration, pilot import, guarded public-facade integration,
  and independent owner verification. The project owner reports that the same
  native Windows guarded integration test passed. **Windows result: PASS —
  owner-reported; terminal evidence not retained.** No command transcript,
  environment measurement, test count, or other unretained Windows terminal
  detail is asserted.
- **Human verification and acceptance:** Person 2 review is **ACCEPTED
  (owner-reported)**. The project owner explicitly confirms **Feature 007
  ACCEPTED** on 2026-11-22 after T007-B through T007-E and the final offline
  verification. Person 1 provenance review is recorded in the chronological
  log as owner-reported acceptance.
- **Final status:** DONE for the approved T007 public-retrieval-facade scope.
  This does not complete broader P1 shared-contract work, the separate GIN
  migration, T008, P4-09 real retrieval integration, P4-10 Gemini integration,
  or any broader application/feature acceptance.

### Feature 012 — Frontend Research Question Explorer

- **Owner:** Person 4 (Frontend & Integration).
- **Date:** 2026-11-22.
- **Artifacts:** Approved specification, plan, and eight-task list, UI data model, question
  service contract summary, quickstart validation guide, and
  requirements-quality checklist in [`specs/012-frontend-explorer`](specs/012-frontend-explorer).
- **Current state:** IN_PROGRESS — the project owner explicitly approved the
  specification and supplied three corrections on 2026-11-22. Those
  corrections are applied in `spec.md`: mock notice dismissal is scoped to the
  current result, the header badge follows the latest response metadata, and
  requests time out after 30 seconds with an abort and retryable message. The
  plan and task list are approved; implementation is authorized through T008.
  T001 through T006 are automated-validated. T007's implementation, all four
  required checks, and the Explorer walkthrough are accepted. T008 is now
  implemented and automated-validated; feature-owner review remains pending. The owner also
  approved the ESLint and `@eslint/js` v9 alignment.
- **Research:** Read the constitution, development workflow, team ownership,
  product scope, architecture, data model, Phase 5 backlog, integration
  handoff, Feature 011 API source/models/fakes, Golden Questions v0, and current
  frontend starter. Verified the closed fake-only contract and separated its
  facts from the unsupported local launcher. Compared state-driven navigation
  with a router, Vitest/Testing Library with Jest, and checked the JSX
  accessibility plugin's maintained flat-config support. External findings
  and unavailable package-registry checks are recorded in `research.md`.
- **Plan decisions:** Use app state instead of a router; use Vitest with
  Testing Library, user-event, and jsdom for offline mocked behavior tests; use
  response-local mock-notice dismissal; abort pending requests after 30
  seconds; propose an independent frontend CI job without changing Python CI.
  Optional Playwright tests remain out of scope unless separately approved.
- **Task sequencing:** T001–T006 cover setup, User Story 1, and User Story 2;
  T007's four automated checks and owner-reported Explorer walkthrough passed;
  T008 implements User Story 3 previews. The task list records T007 accepted.
- **Proxy-response correction:** The owner clarified that a stopped backend
  can yield HTTP 5xx with an HTML/non-envelope proxy body. The specification,
  plan, data model, and service contract now classify any 5xx without a valid
  API error envelope as retryable API-unreachable; malformed HTTP 200/4xx
  bodies remain generic nonretryable errors. Client tests for both paths are
  required by the task list.
- **T001 evidence:** The IBM Plex Fontsource packages and approved development
  dependencies installed without peer overrides; npm reported zero
  vulnerabilities. npm also warned that resolved `eslint@9.39.5` is no longer
  supported; this is the resolved v9 major required by the approved
  `eslint-plugin-jsx-a11y` peer range. `npm.cmd run lint`, `npm.cmd run typecheck`, and
  `npm.cmd run build` all passed. The Vite `/api` proxy remains configured for
  `http://127.0.0.1:8000`. T001 is AUTO_VALIDATED; no manual acceptance is
  implied. Setup-only RED: N/A because T001 defines no application behavior;
  baseline inspection confirmed that the starter had no test script.
- **Dependency compatibility finding:** `eslint-plugin-jsx-a11y` 6.10.2
  declares ESLint peer support through major 9. T001 applied the approved
  alignment to `eslint` and `@eslint/js` 9 and enabled the recommended flat
  config without peer overrides. npm warned that resolved `eslint@9.39.5` is
  no longer supported; the installed version is recorded in the T001 evidence.
- **Template workflow:** The composed Spec Kit template was resolved with the
  repository script after the machine's default PowerShell execution policy
  blocked its initial invocation. The resolved template was used to create the
  draft spec. The requirements checklist was reviewed against the draft; it
  records specification quality only and is not implementation approval.
- **Automated verification:** T001–T008 implementation checks passed. T008
  RED/GREEN and final checks are recorded in its task entry below.
- **Manual verification:** T007 Explorer walkthrough was performed by Milena
  (Person 4) on 2026-11-22 and ACCEPTED; preview walkthrough is not part of the
  Explorer gate.
- **Backlog state:** P5 backlog items remain unchecked; the Phase 5 note in
  `PROJECT_TODO.md` reflects approved specification, plan, and task list plus
  the accepted T007 Explorer gate.
- **Runtime compatibility input:** The project owner reports Node.js
  `v24.20.0`. Official Vite guidance requires Node `20.19+` or `22.12+`;
  Vitest 5 requires Node `22.12+` and Vite `6.4+`. The reported Node and
  installed Vite `8.3.8` satisfy those minima. The local `node --version`
  command returned `v24.20.0`.
- **Open questions and limits:** The handoff does not establish an official
  backend launcher, evidence has no author/year/section fields, filters are not
  part of the request contract, and real retrieval (P4-09) and Gemini (P4-10)
  remain separate work. A separate frontend CI job appears only as a proposal
  in the plan. The local demo command is treated as owner-provided, not officially
  supported.
- **Next gate:** Owner review of the completed T008 previews; no further task is
  authorized in this implementation run.

### T002 — Frontend question-service types and fixtures

- **Owner:** Person 4
- **Feature specification and plan:** Approved Feature 012 `spec.md` and `plan.md`; approved `tasks.md`.
- **Current state:** AUTO_VALIDATED
- **Files changed:** `frontend/src/api/types.ts`, `frontend/src/api/fixtures.ts`, `frontend/src/api/types.test.ts`, `specs/012-frontend-explorer/research.md`, `specs/012-frontend-explorer/tasks.md`, `PROJECT_TODO.md`, `EVIDENCE.md`.
- **Tests created or updated:** `frontend/src/api/types.test.ts`.
- **RED result:** `npm.cmd run test -- src/api/types.test.ts` failed as expected before implementation: Vitest could not resolve the not-yet-created `./fixtures` module.
- **GREEN result:** The same command passed: 1 test file, 3 tests passed.
- **Other automated checks:** `npm.cmd run typecheck` — PASS.
- **Known issues and prior attempts:** Fixture text and DOI are explicitly synthetic and must not be presented as a real scientific source. TypeScript types alone do not validate network JSON; T003 covers runtime envelope validation.
- **Awaiting human confirmation:** Yes.

#### Human evidence

- **Verifier:** NOT PROVIDED
- **Verification date:** NOT PROVIDED
- **Exact manual commands or actions:** NOT RUN
- **Observed outcome:** NOT PROVIDED
- **Explicit decision:** NOT PROVIDED
- **Final status:** AUTO_VALIDATED; human verification pending.

### T003 — Question API client and request IDs

- **Owner:** Person 4
- **Feature specification and plan:** Approved Feature 012 `spec.md` and `plan.md`; approved `tasks.md`; accepted Person 3 HTTP handoff.
- **Current state:** AUTO_VALIDATED
- **Files changed:** `frontend/src/api/client.ts`, `frontend/src/api/client.test.ts`, `frontend/src/lib/requestId.ts`, `frontend/src/lib/requestId.test.ts`, `specs/012-frontend-explorer/tasks.md`, `PROJECT_TODO.md`, `EVIDENCE.md`.
- **Tests created or updated:** API-client tests for the three success states, six known error codes, fetch rejection, 5xx HTML/empty/malformed/success-shaped bodies, malformed 200/4xx bodies, request serialization and 30-second abort; request-ID validation tests.
- **RED result:** `npm.cmd run test -- src/api/client.test.ts src/lib/requestId.test.ts` failed before implementation because `client.ts` and `requestId.ts` did not exist.
- **GREEN result:** The same command passed: 2 files, 28 tests passed. HTTP 5xx without a valid API error envelope is retryable API-unreachable; malformed HTTP 200/4xx is generic nonretryable. Timeout aborts and retains the generated request reference.
- **Other automated checks:** `npm.cmd run typecheck` — PASS; `npm.cmd run lint` — PASS.
- **Known issues and prior attempts:** Initial assertions for valid server error envelopes expected the client-generated ID; corrected them to assert the returned server request ID, matching the contract. All client failures use sanitized messages; raw body/error text is not displayed. No backend contract changes.
- **Awaiting human confirmation:** Yes.

#### Human evidence

- **Verifier:** NOT PROVIDED
- **Verification date:** NOT PROVIDED
- **Exact manual commands or actions:** NOT RUN
- **Observed outcome:** NOT PROVIDED
- **Explicit decision:** NOT PROVIDED
- **Final status:** AUTO_VALIDATED; human verification pending.

### T004 — Research question form and initial/loading view

- **Owner:** Person 4
- **Feature specification and plan:** Approved Feature 012 `spec.md` and `plan.md`; approved `tasks.md`.
- **Current state:** AUTO_VALIDATED
- **Files changed:** `frontend/src/features/explorer/QuestionForm.tsx`, `frontend/src/features/explorer/QuestionForm.test.tsx`, `frontend/src/features/explorer/ExplorerPage.tsx`, `specs/012-frontend-explorer/tasks.md`, `PROJECT_TODO.md`, `EVIDENCE.md`.
- **Tests created or updated:** Form validation/count/examples/submission/pending tests and initial/loading Explorer results-area tests.
- **RED result:** `npm.cmd run test -- src/features/explorer/QuestionForm.test.tsx` failed before implementation because `QuestionForm.tsx` did not exist.
- **GREEN result:** The same command passed: 1 file, 8 tests passed. It verifies trimmed 1–2,000 character validation, example fill without submit, trimmed submit, duplicate-submit prevention, loading announcement, initial state, and busy results region.
- **Other automated checks:** `npm.cmd run typecheck` — PASS; `npm.cmd run lint` — PASS.
- **Known issues and prior attempts:** Initial long-input tests used simulated keystrokes and exceeded the test timeout; switched to direct input-change events for boundary values. ESLint first reported a redundant explicit `region` role on a section; removed the redundant role and reran lint successfully.
- **Awaiting human confirmation:** Yes.

#### Human evidence

- **Verifier:** NOT PROVIDED
- **Verification date:** NOT PROVIDED
- **Exact manual commands or actions:** NOT RUN
- **Observed outcome:** NOT PROVIDED
- **Explicit decision:** NOT PROVIDED
- **Final status:** AUTO_VALIDATED; human verification pending.

### T005 — Answer, citation, source, and provenance rendering

- **Owner:** Person 4
- **Feature specification and plan:** Approved Feature 012 `spec.md` and `plan.md`; approved `tasks.md`; accepted question-service contract.
- **Current state:** AUTO_VALIDATED
- **Files changed:** `frontend/src/lib/citations.ts`, `frontend/src/lib/citations.test.ts`, `frontend/src/features/explorer/AnswerView.tsx`, `frontend/src/features/explorer/AnswerView.test.tsx`, `frontend/src/features/explorer/ExplorerPage.tsx`, `frontend/src/features/explorer/ExplorerPage.test.tsx`, `frontend/src/components/SourceCard.tsx`, `frontend/src/components/CitationMarker.tsx`, `specs/012-frontend-explorer/plan.md`, `specs/012-frontend-explorer/spec.md`, `specs/012-frontend-explorer/tasks.md`, `PROJECT_TODO.md`, `EVIDENCE.md`.
- **Tests created or updated:** Citation resolution ordering/deduplication/unknown/uncited cases; answer rendering, citation navigation/highlighting, DOI link safety, source locator disclosure, provenance; answered flow integration.
- **RED result:** `npm.cmd run test -- src/features/explorer/AnswerView.test.tsx src/lib/citations.test.ts` failed before implementation because `citations.ts` and `AnswerView.tsx` did not exist. The integration test then demonstrated the page still showed only “Response received” rather than its answer.
- **GREEN result:** `npm.cmd run test -- src/features/explorer/AnswerView.test.tsx src/lib/citations.test.ts src/features/explorer/ExplorerPage.test.tsx` passed: 3 files, 7 tests.
- **Other automated checks:** `npm.cmd run typecheck` — PASS; `npm.cmd run lint` — PASS.
- **Known issues and prior attempts:** An integration assertion initially expected the unprefixed title; corrected it to assert the accessible “Source 1” heading. DOI uses the fixed HTTPS doi.org origin with slash-preserving path encoding and safe new-tab attributes. Fixture source details remain synthetic.
- **Awaiting human confirmation:** Yes.

#### Human evidence

- **Verifier:** NOT PROVIDED
- **Verification date:** NOT PROVIDED
- **Exact manual commands or actions:** NOT RUN
- **Observed outcome:** NOT PROVIDED
- **Explicit decision:** NOT PROVIDED
- **Final status:** AUTO_VALIDATED; human verification pending.

### T006 — Empty, error, synthetic-data, badge, and timeout states

- **Owner:** Person 4
- **Feature specification and plan:** Approved Feature 012 `spec.md` and `plan.md`; approved `tasks.md`; approved HTTP 5xx classification correction.
- **Current state:** AUTO_VALIDATED
- **Files changed:** `frontend/src/features/explorer/ResultStates.tsx`, `frontend/src/features/explorer/ResultStates.test.tsx`, `frontend/src/features/explorer/ExplorerPage.tsx`, `frontend/src/features/explorer/ExplorerPage.test.tsx`, `frontend/src/components/MockNotice.tsx`, `frontend/src/components/Header.tsx`, `frontend/src/components/Header.test.tsx`, `specs/012-frontend-explorer/tasks.md`, `PROJECT_TODO.md`, `EVIDENCE.md`.
- **Tests created or updated:** Result-state tests for empty, insufficient evidence, six known errors, retry/reference, reachability, malformed response, and timeout; header default/either-true/both-false metadata tests; Explorer tests for response-scoped notice dismissal, retained editable question/retry, and client timeout integration.
- **RED result:** `npm.cmd run test -- src/features/explorer/ResultStates.test.tsx src/components/Header.test.tsx` failed before implementation because the components did not exist. Explorer integration tests also failed before page wiring: the mock notice did not appear and API-unreachable errors displayed only a generic placeholder.
- **GREEN result:** `npm.cmd run test -- src/features/explorer/ResultStates.test.tsx src/components/Header.test.tsx src/features/explorer/ExplorerPage.test.tsx` passed: 3 files, 20 tests. The 30-second test confirms the request aborts, exact timeout text and retry appear, and the entered question remains editable.
- **Other automated checks:** `npm.cmd run typecheck` — PASS; `npm.cmd run lint` — PASS.
- **Known issues and prior attempts:** Result presentation is implemented in `ResultStates.tsx`; the task's optional `StatusPanel.tsx` path was not needed. Header is implemented and tested independently; T007 will place it in the app shell and wire latest response metadata.
- **Awaiting human confirmation:** Yes.

#### Human evidence

- **Verifier:** NOT PROVIDED
- **Verification date:** NOT PROVIDED
- **Exact manual commands or actions:** NOT RUN
- **Observed outcome:** NOT PROVIDED
- **Explicit decision:** NOT PROVIDED
- **Final status:** AUTO_VALIDATED; human verification pending.

### T007 — Explorer shell and demo-ready gate

- **Owner:** Person 4
- **Feature specification and plan:** Approved Feature 012 `spec.md` and `plan.md`; approved `tasks.md`.
- **Current state:** DONE
- **Files changed:** `frontend/src/App.tsx`, `frontend/src/App.test.tsx`, `frontend/src/components/Header.tsx`, `frontend/src/components/Navigation.tsx`, `frontend/src/features/explorer/ExplorerPage.tsx`, `frontend/src/features/explorer/QuestionForm.tsx`, `frontend/src/features/explorer/QuestionForm.test.tsx`, `frontend/src/features/explorer/AnswerView.tsx`, `frontend/src/styles/tokens.css`, `frontend/src/styles/global.css`, `frontend/src/index.css`, `frontend/index.html`, `frontend/README.md`, `specs/012-frontend-explorer/plan.md`, `EVIDENCE.md`, `PROJECT_TODO.md`, `specs/012-frontend-explorer/tasks.md`.
- **Tests created or updated:** `frontend/src/App.test.tsx` checks semantic app landmarks, default mock badge, active-page announcement, polite result announcements, and absence of preview content. `frontend/src/features/explorer/QuestionForm.test.tsx` additionally verifies that Golden Questions are visible as their full accessible button labels and grouped accessibly.
- **RED result:** `npm.cmd run test -- src/App.test.tsx` failed before implementation: the starter had no banner, navigation, main, footer, mock badge, or Research Question Explorer.
- **GREEN result:** `npm.cmd run test -- src/App.test.tsx` passed: 1 file, 2 tests.
- **Other automated checks:** `npm.cmd run lint` — PASS; `npm.cmd run typecheck` — PASS; `npm.cmd run test` — PASS (10 files, 67 tests); `npm.cmd run build` — PASS; `npm.cmd ls --depth=0` — PASS with no peer overrides. The build bundles IBM Plex Sans and IBM Plex Mono locally. Computed contrast ratios: primary button 5.02:1, secondary text 6.00:1, honey notice text 7.76:1, error title 6.95:1, blue link 10.36:1.
- **Known issues and prior attempts:** The original starter screen was replaced. Additional RED checks found that example prompts were hidden behind generic aria-labels and the results region lacked a polite live announcement; the accessible full prompts, group role, and `aria-live="polite"` region are now in place. The `/api` Vite proxy remains pointed at `http://127.0.0.1:8000`. Preview navigation labels are present but disabled until T008; no preview screen was implemented. Automated checks do not verify 390 px browser layout or the live fake-backend walkthrough.
- **Awaiting human confirmation:** No; Milena (Person 4) accepted the Explorer walkthrough.

#### Human evidence

- **Verifier:** Milena (Person 4)
- **Verification date:** 2026-11-22
- **Exact manual commands or actions:** Started `scratch/serve_fake.py` and `npm run dev`; exercised the default response, documented fake modes, backend-stopped proxy path, validation, keyboard navigation, focus, and 390 px viewport.
- **Observed outcome:** Answered flow, citation scroll/highlight, Details and About this result disclosures, DOI link, mock notice dismissal/reappearance, and header badge were OK. Retrieval-empty, insufficient-evidence, provider-unavailable, retrieval-timeout, and stopped-backend scenarios produced expected states/retry rules. Whitespace and >2,000-character validation passed. Keyboard navigation and visible focus were OK; no horizontal overflow at 390 px.
- **Explicit decision:** ACCEPTED.
- **Final status:** DONE. T007 is accepted and T008 is authorized after the requested pre-task fixes.

### T008 — Static workflow previews

- **Owner:** Person 4
- **Feature specification and plan:** Approved Feature 012 `spec.md` and `plan.md`; approved `tasks.md`; T007 Explorer gate accepted by Milena on 2026-11-22.
- **Current state:** AUTO_VALIDATED
- **Files changed:** `frontend/src/App.tsx`, `frontend/src/App.test.tsx`, `frontend/src/components/Navigation.tsx`, `frontend/src/features/explorer/ExplorerPage.tsx`, `frontend/src/features/explorer/ExplorerPage.test.tsx`, `frontend/src/features/explorer/QuestionForm.tsx`, `frontend/src/features/previews/PreviewBanner.tsx`, `frontend/src/features/previews/ComparisonPreview.tsx`, `frontend/src/features/previews/ConflictsPreview.tsx`, `frontend/src/features/previews/GapsPreview.tsx`, `frontend/src/features/previews/Previews.test.tsx`, `frontend/src/styles/global.css`, `specs/012-frontend-explorer/tasks.md`, `PROJECT_TODO.md`, `EVIDENCE.md`.
- **Tests created or updated:** Preview navigation and content tests cover all three placeholder views, exact preview notice and draft copy, disabled actions, comparison rows, and exactly one `<main>` landmark per view. Explorer regression test ensures retry submits the currently edited question.
- **RED result:** `npm.cmd run test -- src/features/previews/Previews.test.tsx` failed as expected before preview implementation: all three tests could not navigate because preview controls were disabled and preview screens did not exist. `npm.cmd run test -- src/features/explorer/ExplorerPage.test.tsx` also failed before the retry fix: retry submitted the original question after the field had been edited.
- **GREEN result:** `npm.cmd run test -- src/features/previews/Previews.test.tsx src/App.test.tsx` passed: 2 files, 5 tests. After finding the duplicate `research-question` DOM ID, added a regression assertion; `npm.cmd run test -- src/App.test.tsx src/features/explorer/QuestionForm.test.tsx` passed: 2 files, 10 tests after assigning the textarea a distinct ID. The retry regression passed with `npm.cmd run test -- src/features/explorer/ExplorerPage.test.tsx src/features/explorer/QuestionForm.test.tsx`: 2 files, 13 tests.
- **Other automated checks:** From `frontend/`, `npm.cmd run lint` — PASS; `npm.cmd run typecheck` — PASS; `npm.cmd run test` — PASS (11 files, 71 tests); `npm.cmd run build` — PASS (Vite 8.3.8 production build).
- **Known issues and prior attempts:** Explorer remains mounted but hidden while another view is active, preserving its question/result state. `App.tsx` owns the single `<main>` landmark shared by Explorer and each preview. No preview content is connected to the backend or makes scientific claims.
- **Awaiting human confirmation:** Yes.

#### Human evidence

- **Verifier:** NOT PROVIDED
- **Verification date:** NOT PROVIDED
- **Exact manual commands or actions:** NOT RUN
- **Observed outcome:** NOT PROVIDED
- **Explicit decision:** NOT PROVIDED
- **Final status:** AUTO_VALIDATED; T008 owner review pending.
