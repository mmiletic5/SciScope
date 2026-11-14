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
const Ajv2020 = require('C:/Users/Nikola/AppData/Roaming/npm/node_modules/@angular/cli/node_modules/ajv/dist/2020').default;
const addFormats = require('C:/Users/Nikola/AppData/Roaming/npm/node_modules/@angular/cli/node_modules/ajv-formats').default;
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
| `uv venv .venv --python 3.12 --no-managed-python --no-python-downloads` | BLOCKED | `error: Could not acquire lock` / `failed to open file C:\Users\Nikola\AppData\Local\uv\cache\.lock: Access is denied. (os error 5)`. No workaround attempted. |
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
const Ajv2020 = require('C:/Users/Nikola/AppData/Roaming/npm/node_modules/@angular/cli/node_modules/ajv/dist/2020').default;
const addFormats = require('C:/Users/Nikola/AppData/Roaming/npm/node_modules/@angular/cli/node_modules/ajv-formats').default;
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

## Feature 002 T001 — bounded PLOS API and JATS verification

- **Owner:** Person 1. The owner approved the current Feature 002 specification, plan, and tasks baseline and authorized T001 only in the 2026-11-14 execution request. TEAM constitution ratification and scientific-policy decisions, Person 2 shared-contract decisions, and T002–T010 execution were not approved.
- **Current state:** BLOCKED; the first live API request failed before an HTTP response was exposed. T001 remains unchecked in `tasks.md` and human verification is pending.
- **Files changed:** `specs/002-honeybee-corpus-discovery/research.md`, `specs/002-honeybee-corpus-discovery/quickstart.md`, `PROJECT_TODO.md`, and this ledger.
- **Tests / RED / GREEN:** N/A; T001 is a source research task and introduces no behavior or code. Its acceptance check requires live publisher observations and human review.
- **Live check (2026-11-14 00:24 UTC):** BLOCKED. One PowerShell `Invoke-WebRequest -Uri $uri -Method Get -TimeoutSec 15 -ErrorAction Stop` was executed after setting `$query = 'title:"Apis mellifera"'` and `$uri = 'https://api.plos.org/search?q=' + [uri]::EscapeDataString($query) + '&fl=id%2Ctitle%2Carticle_type%2Cpublication_date%2Csubject&wt=json&rows=1&start=0&sort=id%20asc'`. The exact resolved GET URL and all parameters are recorded in `research.md`. Exit code 1; `System.Net.WebException`: `The underlying connection was closed: An unexpected error occurred on a receive.` No HTTP status, content type, or body was returned to the caller. No retry was attempted.
- **Dependent checks:** NOT RUN. Pagination, candidate metadata, individual JATS XML, DOI association, and article-specific license/provenance checks require a successful API response and observed candidate DOI. No candidate or XML was downloaded.
- **Other automated checks:** `git diff --check` — PASS (exit 0, no whitespace errors). `git diff --exit-code -- specs/002-honeybee-corpus-discovery/tasks.md specs/002-honeybee-corpus-discovery/spec.md specs/002-honeybee-corpus-discovery/plan.md docs/DATA_CONTRACT.json evals/golden_questions.schema.json` — PASS (exit 0; these task IDs, approved baseline artifacts, and shared schemas were unchanged). The PowerShell relative-link check below — PASS (`PASS: relative Markdown links resolve in four changed files.`). The PowerShell reproduction-block parse check below — PASS (`PASS: T001 PowerShell reproduction block parses.`). Neither documentation check validates live PLOS access.
- **Known issues:** Prior live PLOS requests in the planning research were blocked; this new attempt did not resolve access. The documented PLOS fields and route remain unverified in this environment. No alternate source or workaround was attempted.
- **Awaiting human confirmation:** Yes. Manual PowerShell reproduction is in `specs/002-honeybee-corpus-discovery/quickstart.md`. Human outcome and explicit decision: NOT PROVIDED. Final status: BLOCKED, not DONE.

The exact PowerShell documentation checks were:

````powershell
$files = @('specs/002-honeybee-corpus-discovery/research.md','specs/002-honeybee-corpus-discovery/quickstart.md','PROJECT_TODO.md','EVIDENCE.md'); $broken = @(); foreach ($file in $files) { $directory = Split-Path $file -Parent; if (-not $directory) { $directory = '.' }; $content = Get-Content -LiteralPath $file -Raw -Encoding UTF8; foreach ($match in [regex]::Matches($content, '\[[^\]]+\]\(([^)]+)\)')) { $target = $match.Groups[1].Value.Split('#')[0]; if ($target -and $target -notmatch '^(https?://|mailto:)') { $resolved = Join-Path $directory $target; if (-not (Test-Path -LiteralPath $resolved)) { $broken += "$file -> $target" } } } }; if ($broken.Count) { $broken; exit 1 }; Write-Output 'PASS: relative Markdown links resolve in four changed files.'
$text = Get-Content -LiteralPath 'specs/002-honeybee-corpus-discovery/quickstart.md' -Raw -Encoding UTF8; $block = [regex]::Match($text, '(?s)## Reproduce the blocked T001 API check.*?```powershell\s*(.*?)\s*```').Groups[1].Value; if (-not $block) { throw 'T001 reproduction block missing' }; $tokens = $null; $errors = $null; [System.Management.Automation.Language.Parser]::ParseInput($block, [ref]$tokens, [ref]$errors) | Out-Null; if ($errors.Count) { $errors | ForEach-Object { Write-Output $_.Message }; exit 1 }; Write-Output 'PASS: T001 PowerShell reproduction block parses.'
````

## Feature 002 approval report and second T001 connectivity diagnostic

- **Approval provenance (2026-11-14):** Person 1 reported that relevant TEAM and Person 2 approvals were obtained outside the repository, then specifically confirmed that TEAM approved the exact current constitution 0.1.0 text with original ratification date 2026-11-14. No external approval record, individual signatures, reviewer identities, or meeting date was supplied. The current Feature 002 spec/plan/tasks baseline, documented scientific and DOI/locator decisions, and T001–T010 execution in dependency order are approved as reported; shared JSON Schema edits are not approved. See `docs/DECISIONS.md` for the decision scope.
- **P0-08:** Ratification is recorded in the constitution, but the backlog item remains unchecked because independent task completion evidence has not been recorded. `D-011` retains the open draft-contract component.
- **T001 state:** BLOCKED. The earlier PowerShell failure remains above. T002–T010 are authorized in dependency order but not started; they depend on T001's source checks and manual acceptance. Human outcome and explicit T001 decision: NOT PROVIDED.
- **Local client check:** `Get-Command curl.exe -ErrorAction SilentlyContinue | Select-Object Name,Source; $PSVersionTable.PSVersion.ToString()` — PASS: `curl.exe` at `C:\WINDOWS\system32\curl.exe`, Windows PowerShell 5.1.26100.9818. `curl.exe --version` — PASS: curl 8.22.0 using Schannel.
- **Second live check (2026-11-14 00:32:08 UTC):** BLOCKED. One bounded curl GET of the same T001 URL was attempted with the exact command below. curl exit 7: `Failed to connect to api.plos.org:443 over proxy 127.0.0.1 after 0 ms: Could not connect to server`. `CURL_HTTP_CODE=000`, empty remote IP, SSL verify result `0`; no HTTP response headers or body. The query, endpoint, TLS exchange, returned fields, pagination, candidate records, and JATS remain unverified. No retry or proxy bypass was attempted.
- **Proxy configuration read:** PASS as a local diagnostic only. `HTTPS_PROXY`, `https_proxy`, `ALL_PROXY`, `all_proxy`, `HTTP_PROXY`, and `http_proxy` resolved to scheme `http`, host `127.0.0.1`, port `9`; only scheme/host/port were printed. This explains curl's attempted route but does not establish PowerShell's route or PLOS availability.
- **Dependent checks:** NOT RUN — candidate metadata, pagination, individual JATS XML, DOI association, and article-specific license/provenance. No corpus, source XML, Python module, or test was created.
- **Human verification:** NOT PROVIDED. T001 and all T002–T010 checkboxes remain unchecked. The [Feature 002 quickstart](specs/002-honeybee-corpus-discovery/quickstart.md) gives minimal Windows PowerShell reproduction.
- **Documentation, consistency, governance, and Git checks:** `git diff --check` — PASS (exit 0, no whitespace errors); `git diff --exit-code -- docs/DATA_CONTRACT.json evals/golden_questions.schema.json` — PASS (exit 0, both shared JSON Schemas unchanged); constitution metadata/placeholder check below — PASS; T001–T010 checkbox check below — PASS (one unchecked entry for each ID); changed-Markdown relative-link check below — PASS (12 files). `.specify/extensions.yml` was absent, so no constitution extension hooks applied. `speckit-analyze` — NOT RUN: its full post-task analysis belongs to deferred T010; this session did not execute T010.

Exact second request (PowerShell):

```powershell
$uri = 'https://api.plos.org/search?q=title%3A%22Apis%20mellifera%22&fl=id%2Ctitle%2Carticle_type%2Cpublication_date%2Csubject&wt=json&rows=1&start=0&sort=id%20asc'; [DateTime]::UtcNow.ToString('o'); Write-Output "REQUEST GET $uri"; curl.exe --silent --show-error --dump-header - --max-time 15 --connect-timeout 5 --max-filesize 150000 --write-out "`nCURL_HTTP_CODE=%{http_code} CURL_REMOTE_IP=%{remote_ip} CURL_SSL_VERIFY=%{ssl_verify_result}`n" $uri; Write-Output "CURL_EXIT_CODE=$LASTEXITCODE"
```

Exact local proxy-setting inspection (only scheme, host, and port were printed):

```powershell
$names = @('HTTPS_PROXY','https_proxy','ALL_PROXY','all_proxy','HTTP_PROXY','http_proxy'); foreach ($name in $names) { $value = [Environment]::GetEnvironmentVariable($name); if ($value) { try { $parsed = [uri]$value; Write-Output "$name scheme=$($parsed.Scheme) host=$($parsed.Host) port=$($parsed.Port)" } catch { Write-Output "$name configured; URI parse failed" } } }
```

Exact local validation commands:

````powershell
git diff --check
git diff --exit-code -- docs/DATA_CONTRACT.json evals/golden_questions.schema.json
$text = Get-Content -LiteralPath '.specify/memory/constitution.md' -Raw -Encoding UTF8; if ($text -notmatch '\*\*Version\*\*: 0\.1\.0 \| \*\*Ratified\*\*: 2026-11-14 \| \*\*Last Amended\*\*: 2026-11-14') { throw 'Constitution metadata mismatch' }; if ($text -match '\[[A-Z][A-Z0-9_]+\]' -or $text -match 'TODO\(') { throw 'Unresolved constitution placeholder' }; if ($text -notmatch 'Version change: 0\.1\.0 → 0\.1\.0') { throw 'Sync Impact version mismatch' }; Write-Output 'PASS: ratification date, unchanged version, sync impact, and placeholders.'
$text = Get-Content -LiteralPath 'specs/002-honeybee-corpus-discovery/tasks.md' -Raw -Encoding UTF8; for ($i=1; $i -le 10; $i++) { $id = 'T{0:d3}' -f $i; $matches = [regex]::Matches($text, '(?m)^- \[ \] ' + $id + ' '); if ($matches.Count -ne 1) { throw "$id checkbox count $($matches.Count)" } }; Write-Output 'PASS: T001-T010 retain one unchecked task each.'
$files = @(git diff --name-only -- '*.md'); $broken = @(); foreach ($file in $files) { $directory = Split-Path $file -Parent; if (-not $directory) { $directory = '.' }; $content = Get-Content -LiteralPath $file -Raw -Encoding UTF8; foreach ($match in [regex]::Matches($content, '\[[^\]]+\]\(([^)]+)\)')) { $target = $match.Groups[1].Value.Split('#')[0]; if ($target -and $target -notmatch '^(https?://|mailto:)') { if (-not (Test-Path -LiteralPath (Join-Path $directory $target))) { $broken += "$file -> $target" } } } }; if ($broken.Count) { $broken; exit 1 }; Write-Output "PASS: relative links resolve in $($files.Count) changed Markdown files."
````

## Feature 002 T001 — explicit Person 1 acceptance

- **Verifier and decision:** Person 1, the feature owner, explicitly **ACCEPTED** T001 on 2026-11-14 based on their Windows PowerShell checks and previously recorded evidence. This supersedes the earlier IN_PROGRESS state, without erasing the blocked Codex requests or the intermediate human evidence above.
- **Additional source observations (human report):** The individual `10.1371/journal.pone.0000395` XML had `article-type=research-article`, one license node whose text identified Creative Commons Attribution and required attribution to authors and original source. The official publisher page `https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0000395` reportedly identified the same DOI, original-research status, and licensing statement. The XML HTTP 200, `text/xml`, 121676 bytes, root `article`, matching DOI, and SHA-256 `EE0FC718E4C1C16B2D75347939F618091229BA8B26BE6257C13BF29F8816668F` remain as recorded above. A Creative Commons license **version** was not supplied or inferred.
- **Scope and limitations:** The initial connectivity result and two detailed pagination records are three distinct IDs from separate bounded probes; only the latter two were used as candidate metadata records. The owner explicitly requested this distinction and accepted T001 with it recorded. Literal pagination URLs and exact request times were not supplied; exact query parameters, page offsets, ordering request, and report date are retained. `numFound=232` is not an eligible-paper count. Formal JATS schema validation, full scientific eligibility, and pilot acquisition were not T001 completion claims.
- **Automatic/source verification:** PASS for documented human-performed API connectivity, two-page metadata/pagination, and one XML retrieval/DOI/source/license observation. Prior Codex network attempts remain BLOCKED in their own environment. Documentation/Git checks for the final task state are recorded below after execution.
- **Final status:** DONE after owner acceptance and recorded source evidence. The T001 checkbox in `tasks.md` is checked; broader backlog items remain unchecked where their deliverables extend beyond T001.

## Feature 002 T002–T010 — grouped documentary execution

**Owner and scope:** Person 1 authorized T002–T010 as one coordinated cycle on
2026-11-14 after accepting T001. The authorized deliverable is the discovery
and pilot-selection protocol, not a corpus or production pipeline. No new
publisher request was made by Codex; the Codex environment remains unable to
reach PLOS. No Python code, behavior test, populated manifest, golden question,
or shared JSON Schema was created.

| Task | Current state | Documentary/source result | Remaining required check |
| --- | --- | --- | --- |
| T002 | IN_PROGRESS | Direct, conditional comparative, generic, other-species, and ambiguous rubric drafted in `spec.md`. | Four actual publisher-inspected example decisions and TEAM borderline review; BLOCKED for Codex source inspection, not fabricated. |
| T003 | AWAITING_MANUAL_VERIFICATION | Type/license readiness table in `spec.md`; T001 human evidence supports one `research-article`/Creative Commons Attribution example without license version. | TEAM verifies table application and paper-specific license handling; T002 dependency remains open. |
| T004 | IN_PROGRESS | Eight exact field-limited query expressions, 25-row/two-page cap, rate spacing, sort, drift, and stop rules in `research.md`. | Reviewer replays exact URLs/pages and checks 25-row offset behavior; Codex source replay BLOCKED and T002 dependency open. |
| T005 | AWAITING_MANUAL_VERIFICATION | DOI wrapper, ASCII case, one-time URI decode, non-ASCII, conflict, and duplicate decision table in `data-model.md`. No DOI code was written. | Person 2 verifies comparison/display cases; T004 dependency remains open. |
| T006 | AWAITING_MANUAL_VERIFICATION | Separate run/candidate/pilot fields, unknown/failure states, and protocol/corpus version rules in `data-model.md`. | Person 2 checks ingestion handoff boundary; T005 dependency remains open. |
| T007 | IN_PROGRESS | First 3–5-to-20 count and theme/JATS variation matrix in `data-model.md`, without fabricated papers. | TEAM reviews matrix after T002/T003/T004/T006; actual acquisition is later scope. |
| T008 | AWAITING_MANUAL_VERIFICATION | Read-only field-by-field `docs/DATA_CONTRACT.json` compatibility table in `plan.md`. | Person 2 accepts/rejects field gaps and locator encoding; T006 dependency remains open. |
| T009 | AWAITING_MANUAL_VERIFICATION | Golden schema gaps and 5–10-question prerequisites in `plan.md`; no records or schema edits. | Person 2 reviews negative-case semantics and label rubric; T007/T008 dependencies remain open. |
| T010 | IN_PROGRESS | FR→AC→task matrix in `quickstart.md`; Spec Kit read-only analysis and Git checks below. | T002–T009 source/human checks, reviewer-owned checklist, and separate final feature-owner acceptance. |

**Official Spec Kit analysis:** `.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireSpec -RequireTasks -IncludeTasks` — PASS; it resolved the active Feature 002 directory and `research.md`, `data-model.md`, `quickstart.md`, and `tasks.md`. The read-only `$speckit-analyze` semantic pass found 10 functional requirements, 9 acceptance criteria, and 10 unique tasks; all 10 FRs map to at least one task, with no unmapped task or constitution conflict. Critical issues: 0; duplication: 0. Open validation findings: four T002 source examples are missing (source gate), T004's planned 25-row offset and all eight query variants have not been live replayed (source gate), and the broader `docs/EVALUATION_PLAN.md` still says approximately 10–20 papers while Feature 002 specifies a 20-paper target (known cross-document wording to reconcile in a later approved scope). These findings do not assert that incomplete tasks passed.

**Checklist gate:** `checklists/requirements.md` has 16/16 checked writing-quality items; reviewer-owned `checklists/corpus-quality.md` has 0/14 checked items. The user's explicit grouped-execution authorization allowed documentary work to proceed, but no checklist human judgments were inferred or marked.

**Automatic/documentation checks:** `git diff --check` — PASS (exit 0); `git diff --exit-code -- docs/DATA_CONTRACT.json evals/golden_questions.schema.json` — PASS (shared schemas unchanged); unchecked-task check — PASS (T001 checked, T002–T010 unchecked); FR coverage check — PASS (10/10); bounded PowerShell replay parse — PASS; relative local links in 12 changed Markdown files — PASS. Scientific source-example verification — BLOCKED in Codex environment. Python Ruff/pytest/mypy — NOT RUN, with no Python change. Post-execution human acceptance for T002–T010 — NOT PROVIDED.

The exact validation commands used were:

````powershell
.specify/scripts/powershell/check-prerequisites.ps1 -Json -RequireSpec -RequireTasks -IncludeTasks
git diff --check
git diff --exit-code -- docs/DATA_CONTRACT.json evals/golden_questions.schema.json
$text = Get-Content -LiteralPath 'specs/002-honeybee-corpus-discovery/tasks.md' -Raw -Encoding UTF8; $done = @([regex]::Matches($text, '(?m)^- \[x\] T\d{3} ')).Count; $open = @([regex]::Matches($text, '(?m)^- \[ \] T\d{3} ')).Count; if ($done -ne 1 -or $open -ne 9) { throw "Unexpected task states: done=$done open=$open" }; Write-Output "PASS: T001 checked; T002-T010 unchecked ($done/$open)."
$spec = Get-Content -LiteralPath 'specs/002-honeybee-corpus-discovery/spec.md' -Raw -Encoding UTF8; $tasks = Get-Content -LiteralPath 'specs/002-honeybee-corpus-discovery/tasks.md' -Raw -Encoding UTF8; $frs = @([regex]::Matches($spec, '(?m)^- \*\*(FR-\d{3})\*\*:') | ForEach-Object { $_.Groups[1].Value }); $missing = @($frs | Where-Object { $tasks -notmatch [regex]::Escape($_) }); if ($missing.Count) { throw "Unmapped: $($missing -join ',')" }; Write-Output "PASS: $($frs.Count) FR IDs mapped to tasks."
$text = Get-Content -LiteralPath 'specs/002-honeybee-corpus-discovery/quickstart.md' -Raw -Encoding UTF8; $block = [regex]::Match($text, '(?s)For a bounded replay.*?```powershell\s*(.*?)\s*```').Groups[1].Value; if (-not $block) { throw 'Replay block missing' }; $tokens = $null; $errors = $null; [System.Management.Automation.Language.Parser]::ParseInput($block, [ref]$tokens, [ref]$errors) | Out-Null; if ($errors.Count) { throw ($errors.Message -join '; ') }; Write-Output 'PASS: bounded PowerShell replay parses.'
$files = @(git diff --name-only -- '*.md'); $broken = @(); foreach ($file in $files) { $dir = Split-Path $file -Parent; if (-not $dir) { $dir = '.' }; $content = Get-Content -LiteralPath $file -Raw -Encoding UTF8; foreach ($match in [regex]::Matches($content, '\[[^\]]+\]\(([^)]+)\)')) { $target = $match.Groups[1].Value.Split('#')[0]; if ($target -and $target -notmatch '^(https?://|mailto:)') { if (-not (Test-Path -LiteralPath (Join-Path $dir $target))) { $broken += "$file -> $target" } } } }; if ($broken.Count) { $broken; exit 1 }; Write-Output "PASS: links resolve in $($files.Count) changed Markdown files."
````

## Feature 002 T001 — subsequent human source evidence

- **Verifier/provenance:** Person 1 supplied their own Windows PowerShell results on 2026-11-14. These requests were not executed successfully by Codex. Exact execution timestamps were not supplied; the two pagination requests were approximately eight seconds apart. The earlier Codex failures above remain valid records of that environment.
- **Current state:** IN_PROGRESS. Local publisher access and one individual XML retrieval were demonstrated by the human report; source/license and provenance details required for T001 acceptance remain incomplete. T001 and T002–T010 remain unchecked. Explicit human task acceptance: NOT PROVIDED.
- **Initial API check — PASS (human report):** `GET https://api.plos.org/search?q=title%3A%22Apis%20mellifera%22&fl=id%2Ctitle&wt=json&rows=1` returned HTTP 200 OK, `application/json`, `numFound=232`, `start=0`, one document: DOI `10.1371/journal.pone.0000395`, title “Magnetoreception System in Honeybees (Apis mellifera)”. No publication type or subject was reported for this record.
- **Pagination/metadata — PASS for basic behavior (human report):** Query `title:"Apis mellifera"`, `fl=id,title,article_type,publication_date,subject`, `wt=json`, `rows=1`, `sort=id asc`, `start=0` then `start=1` each returned HTTP 200 OK and JSON, `numFound=232`, matching `start`, and one document. Page 0: `10.1371/annotation/20dfdf0f-eab5-4ed6-ba0f-37b55b5ccf6a`, `Correction`, 2013-12-11T00:00:00Z, title “Correction: Comparative Sucrose Responsiveness in Apis mellifera and A. cerana Foragers”, `subject` absent. Page 1: `10.1371/journal.pclm.0000485`, `Research Article`, 2024-08-29T00:00:00Z, title “Climatic predictors of prominent honey bee (Apis mellifera) disease agents: Varroa destructor, Melissococcus plutonius, and Vairimorpha spp.”, `subject` present with multiple categories, exact values not supplied. The literal page URLs and exact UTC request times were not supplied. Requested ID order is observed across these two pages only; index stability is NOT VERIFIED. The correction is not automatically eligible primary research; neither record was scientifically screened.
- **Individual XML — PASS for retrieval, XML parsing, and DOI association (human report):** `https://journals.plos.org/plosone/article/file?id=10.1371%2Fjournal.pone.0000395&type=manuscript` returned HTTP 200, `text/xml`, 121676 bytes, saved to a Windows temporary file outside the repository. `[xml]` parsing succeeded; document root `LocalName` was `article`; an `article-id` with `pub-id-type="doi"` contained `10.1371/journal.pone.0000395`, matching the requested DOI. Reported SHA-256: `EE0FC718E4C1C16B2D75347939F618091229BA8B26BE6257C13BF29F8816668F`. The file path in the hash output was truncated. This XML pairs with the initial DOI/title-only connectivity record, whose article type was not supplied; neither detailed paginated record has a reported XML check. Formal JATS validation is NOT RUN.
- **Source/license/scientific eligibility:** NOT RUN or NOT VERIFIED. No article page or XML `permissions`/`license` content, reuse terms, abstract/full-text relevance assessment, or reviewer eligibility decision was supplied. A search count of 232 is not an eligible-paper count.
- **Boundedness/provenance issue:** Three distinct API IDs were returned in total: one minimal connectivity sample and two detailed pagination metadata records. T001's at-most-two candidate-record limit needs reviewer interpretation of the connectivity sample; no further candidate was inspected by Codex. Exact page URLs and UTC request times should be supplied if retained from the human session. No new PLOS request was made while recording this evidence.
- **Tests/RED/GREEN:** N/A; this is source research with no Python behavior, module, or feature test. Documentation and Git checks are recorded below. Human acceptance is still separate.
- **Current documentation/Git checks:** `git diff --check` — PASS (exit 0, no whitespace errors after newline normalization); `git diff --exit-code -- docs/DATA_CONTRACT.json evals/golden_questions.schema.json` — PASS (exit 0, shared schemas untouched); T001–T010 unchecked-ID check — PASS; remaining license-inspection PowerShell parse check — PASS; relative Markdown links in 12 changed files — PASS. These checks validate documentation and syntax, not publisher availability or license terms. Formal JATS validation and scientific screening — NOT RUN.

The human-provided XML inspection transcript used these commands; results are
reported above and were not re-executed by Codex:

```powershell
$xmlPath = Join-Path $env:TEMP 'sciscope-t001.xml'
[xml]$doc = Get-Content -Raw -Encoding UTF8 $xmlPath
"ROOT: $($doc.DocumentElement.LocalName)"
$doiNodes = $doc.SelectNodes('//*[local-name()="article-id" and @pub-id-type="doi"]')
foreach ($node in $doiNodes) { "DOI: $($node.InnerText)" }
Get-FileHash $xmlPath -Algorithm SHA256
```

The exact current documentation checks were:

````powershell
git diff --check
git diff --exit-code -- docs/DATA_CONTRACT.json evals/golden_questions.schema.json
$text = Get-Content -LiteralPath 'specs/002-honeybee-corpus-discovery/tasks.md' -Raw -Encoding UTF8; for ($i=1; $i -le 10; $i++) { $id = 'T{0:d3}' -f $i; if ([regex]::Matches($text, '(?m)^- \[ \] ' + $id + ' ').Count -ne 1) { throw "$id checkbox missing or duplicated" } }; Write-Output 'PASS: T001-T010 each remain unchecked.'
$text = Get-Content -LiteralPath 'specs/002-honeybee-corpus-discovery/quickstart.md' -Raw -Encoding UTF8; $block = [regex]::Match($text, '(?s)## Minimal remaining T001 human review.*?```powershell\s*(.*?)\s*```').Groups[1].Value; if (-not $block) { throw 'License inspection block missing' }; $tokens = $null; $errors = $null; [System.Management.Automation.Language.Parser]::ParseInput($block, [ref]$tokens, [ref]$errors) | Out-Null; if ($errors.Count) { $errors | ForEach-Object { Write-Output $_.Message }; exit 1 }; Write-Output 'PASS: license inspection PowerShell parses.'
$files = @(git diff --name-only -- '*.md'); $broken = @(); foreach ($file in $files) { $directory = Split-Path $file -Parent; if (-not $directory) { $directory = '.' }; $content = Get-Content -LiteralPath $file -Raw -Encoding UTF8; foreach ($match in [regex]::Matches($content, '\[[^\]]+\]\(([^)]+)\)')) { $target = $match.Groups[1].Value.Split('#')[0]; if ($target -and $target -notmatch '^(https?://|mailto:)') { if (-not (Test-Path -LiteralPath (Join-Path $directory $target))) { $broken += "$file -> $target" } } } }; if ($broken.Count) { $broken; exit 1 }; Write-Output "PASS: relative links resolve in $($files.Count) changed Markdown files."
````
