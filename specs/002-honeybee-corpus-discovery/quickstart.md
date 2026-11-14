# Future validation and human review guide

This is a planning guide. No corpus selection command or Python package exists yet. Before T001, the feature owner must explicitly approve `spec.md`, `plan.md`, and `tasks.md` and authorize T001. After T001–T010 and their verification, the feature owner separately accepts or rejects the completed deliverables. Neither gate has been satisfied here.

1. In PowerShell at the repository root, inspect [spec.md](spec.md), [research.md](research.md), [plan.md](plan.md), [tasks.md](tasks.md), and [data-model.md](data-model.md). Confirm protocol version and unresolved decisions with Person 1 and Person 2.
2. First run a small bounded PLOS search/API connectivity check. Record exact `q`, `fl`, `wt`, `start`, `rows`, sort, filter, UTC time, HTTP status, and observed response. Verify a small number of candidate metadata records, DOI fields, pagination, and article type values. If connection, parsing, or fields fail, mark the check BLOCKED or FAIL with the actual error; do not infer absence or continue dependent selection. A reviewer repeats the same URLs and compares observations.
3. Check individual JATS XML availability for those few candidates through the publisher's article page and documented article-file mechanism. Record the DOI match, response status, source URL, time, and any failure. Do not treat a successful search hit as proof of accessible XML.
4. After approval and successful access checks, manually inspect approximately 3–5 unique papers as the first smoke-test sample. Screen direct, comparative, generic pollinator, other-species, primary-research, and review cases using inspected sources. Verify original and normalized DOI mapping, paper-level provenance, article-level license, JATS availability, relevance reason, duplicate paths, and pending/excluded cases. A second reviewer checks all first-sample decisions. Uncertain eligibility or licensing stays pending.
5. Expand toward a complete target of 20 eligible, unique papers, counting accepted first-sample records. Review thematic and JATS variation and why each was chosen; explicitly report a shortfall if 20 is infeasible. Keep reviews separately labeled as secondary synthesis under the provisional minority cap. Compare manifest fields with `docs/DATA_CONTRACT.json`; obtain Person 2 approval for any shared change.
6. For the separate golden feature, inspect original XML/source passages and anchor 5–10 questions to DOI + original section path + JATS `@id` or a version-bound structural locator + XML checksum. If IDs are absent, record sibling positions and a text fingerprint; revalidate after XML changes. A human reviewer verifies findings and labels before Person 2 uses the dataset. Chunk IDs remain derived mappings.

Planning inspection commands:

```powershell
Get-Content -Encoding utf8 specs/002-honeybee-corpus-discovery/spec.md
Get-Content -Encoding utf8 specs/002-honeybee-corpus-discovery/plan.md
Get-Content -Encoding utf8 specs/002-honeybee-corpus-discovery/tasks.md
Get-Content -Encoding utf8 specs/002-honeybee-corpus-discovery/research.md
git diff -- PROJECT_TODO.md
Get-Content .specify/feature.json
git status --short
```

Expected now: only feature planning artifacts, active feature tracking, and the minimal planned backlog reference are changed; no selected paper, XML, test, or code exists. These steps are future manual verification instructions, not checks performed in this planning session.
