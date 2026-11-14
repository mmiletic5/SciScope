# Future validation and human review guide

This is the Feature 002 protocol validation and human review guide. No corpus selection command or Python package exists. Person 1 approved the planning baseline and T001–T010 execution in dependency order, then explicitly accepted T001 on 2026-11-14 after human PLOS API/XML/source/license checks. Earlier Codex-environment failures remain in [research.md](research.md). T002–T010 are documentary and review tasks; their own acceptance remains pending. See [DECISIONS.md](../../docs/DECISIONS.md) for approval provenance.

## Earlier Codex-environment checks

From a Windows PowerShell session, run the same bounded GET. Record the UTC time, exact URL, HTTP status and content type if returned, and any error. The first 2026-11-14 agent attempt ended with `System.Net.WebException` and `The underlying connection was closed: An unexpected error occurred on a receive.` It yielded no status or body. Do not infer result fields, candidate records, or XML availability from that attempt.

```powershell
$query = 'title:"Apis mellifera"'
$uri = 'https://api.plos.org/search?q=' + [uri]::EscapeDataString($query) + '&fl=id%2Ctitle%2Carticle_type%2Cpublication_date%2Csubject&wt=json&rows=1&start=0&sort=id%20asc'
[DateTime]::UtcNow.ToString('o')
Write-Output "REQUEST GET $uri"
try {
  $response = Invoke-WebRequest -Uri $uri -Method Get -TimeoutSec 15 -ErrorAction Stop
  Write-Output "HTTP $([int]$response.StatusCode)"
  Write-Output "CONTENT_TYPE $($response.Headers['Content-Type'])"
  Write-Output "BODY $($response.Content)"
} catch {
  Write-Output "ERROR_TYPE $($_.Exception.GetType().FullName)"
  Write-Output "ERROR_MESSAGE $($_.Exception.Message)"
  if ($_.Exception.Response) { Write-Output "HTTP $([int]$_.Exception.Response.StatusCode)" }
}
```

If `curl.exe` is available, one alternative local-client diagnostic uses the
same URL and request size. On 2026-11-14 it returned exit code 7 while trying
the configured `http://127.0.0.1:9` proxy; HTTP code was `000`. This does not
test PLOS's endpoint or TLS. Do not disable or bypass a configured proxy to
interpret this check as publisher access.

```powershell
$uri = 'https://api.plos.org/search?q=title%3A%22Apis%20mellifera%22&fl=id%2Ctitle%2Carticle_type%2Cpublication_date%2Csubject&wt=json&rows=1&start=0&sort=id%20asc'
[DateTime]::UtcNow.ToString('o')
Write-Output "REQUEST GET $uri"
curl.exe --silent --show-error --dump-header - --max-time 15 --connect-timeout 5 --max-filesize 150000 --write-out "`nCURL_HTTP_CODE=%{http_code} CURL_REMOTE_IP=%{remote_ip} CURL_SSL_VERIFY=%{ssl_verify_result}`n" $uri
Write-Output "CURL_EXIT_CODE=$LASTEXITCODE"
```

Person 1 has since reported successful API and individual XML checks from a different Windows environment. The earlier failures above remain useful for diagnosing the Codex environment; they do not need another automatic retry. No pilot selection is authorized here.

## T001 accepted source-check reproduction

The reported XML parsed successfully with root `article`, matching DOI, and a
SHA-256 hash. Person 1 reported `article-type=research-article`, one license
node identifying Creative Commons Attribution with author/source attribution,
and a matching publisher page, then explicitly accepted T001. The command
below remains a reproduction procedure for the already downloaded temporary
file; it was not run by Codex:

```powershell
$xmlPath = Join-Path $env:TEMP 'sciscope-t001.xml'
[xml]$doc = Get-Content -Raw -Encoding UTF8 $xmlPath
"ARTICLE_TYPE: $($doc.DocumentElement.GetAttribute('article-type'))"
$licenseNodes = $doc.SelectNodes('//*[local-name()="permissions"]//*[local-name()="license"]')
"LICENSE_NODE_COUNT: $($licenseNodes.Count)"
foreach ($node in $licenseNodes) { "LICENSE_XML: $($node.OuterXml)" }
```

The initial DOI/title connectivity sample is the only record paired with an
XML check. The two detailed paginated candidate metadata records have no
reported XML check. Three distinct IDs appeared across all probes and are
recorded separately in `research.md`. The exact pagination request URLs and
UTC times were not supplied; later discovery runs must capture them. No
scientific eligibility or pilot selection follows from T001 acceptance.

1. In PowerShell at the repository root, inspect [spec.md](spec.md), [research.md](research.md), [plan.md](plan.md), [tasks.md](tasks.md), and [data-model.md](data-model.md). Confirm protocol version and unresolved decisions with Person 1 and Person 2.
2. First run a small bounded PLOS search/API connectivity check. Record exact `q`, `fl`, `wt`, `start`, `rows`, sort, filter, UTC time, HTTP status, and observed response. Verify a small number of candidate metadata records, DOI fields, pagination, and article type values. If connection, parsing, or fields fail, mark the check BLOCKED or FAIL with the actual error; do not infer absence or continue dependent selection. A reviewer repeats the same URLs and compares observations.
3. Check individual JATS XML availability for those few candidates through the publisher's article page and documented article-file mechanism. Record the DOI match, response status, source URL, time, and any failure. Do not treat a successful search hit as proof of accessible XML.
4. After approval and successful access checks, manually inspect approximately 3–5 unique papers as the first smoke-test sample. Screen direct, comparative, generic pollinator, other-species, primary-research, and review cases using inspected sources. Verify original and normalized DOI mapping, paper-level provenance, article-level license, JATS availability, relevance reason, duplicate paths, and pending/excluded cases. A second reviewer checks all first-sample decisions. Uncertain eligibility or licensing stays pending.
5. In a separately authorized acquisition task, expand toward a complete target of 20 eligible, unique papers, counting accepted first-sample records. Review thematic and JATS variation and why each was chosen; explicitly report a shortfall if 20 is infeasible. Keep reviews separately labeled as secondary synthesis under the approved at-most-three cap. Compare manifest fields with `docs/DATA_CONTRACT.json`; obtain separate field-level Person 2/shared-owner approval for any shared change.
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

Current T001 state: DONE by explicit owner acceptance, recorded in `research.md` and `EVIDENCE.md` with prior Codex failures retained. The human XML file is outside the repository; no pilot paper, in-repository XML, test, or code was created. The numbered steps remain future protocol instructions, not checks performed by Codex in T001.

## Source-review handoff for T002–T004

The owner should inspect four **actual** publisher articles or article pages
and record one case for each rubric class: direct *A. mellifera* research,
separable comparative research, generic bee/pollinator mention, and
other-species-only work. For each, capture DOI, publisher URL, article type,
title/abstract/full-text section inspected, passage locator, observed species,
decision, reason, license URL/terms, and UTC inspection time. A title, API hit,
or the T001 correction record alone is not a source-inspected scientific case.
If a class cannot be found within the bounded search, record `NOT FOUND`
and the searched pages; do not fabricate an example.

For a bounded replay of the already observed first two one-row pages, run the
following in Windows PowerShell. It makes two requests, eight seconds apart;
record actual IDs and note index drift from the 2026-11-14 human report. For
the full T004 query protocol, use the eight expressions and 25-row two-page
cap in `research.md` only after manual review of this replay and rate limits.

```powershell
$q = [uri]::EscapeDataString('title:"Apis mellifera"')
foreach ($start in 0, 1) {
  $uri = "https://api.plos.org/search?q=$q&fl=id%2Ctitle%2Carticle_type%2Cpublication_date%2Csubject&wt=json&rows=1&sort=id%20asc&start=$start"
  "UTC: $([DateTime]::UtcNow.ToString('o')) URL: $uri"
  $response = Invoke-WebRequest -Uri $uri -Method Get -TimeoutSec 15 -ErrorAction Stop
  $json = $response.Content | ConvertFrom-Json
  "HTTP: $([int]$response.StatusCode) TYPE: $($response.Headers['Content-Type']) NUM_FOUND: $($json.response.numFound) START: $($json.response.start)"
  $json.response.docs | Select-Object id,title,article_type,publication_date,subject
  if ($start -eq 0) { Start-Sleep -Seconds 8 }
}
```

Person 2 should review the T008 field-level table in `plan.md` and explicitly
accept or reject each proposed mapping or gap before any shared contract
change. Person 2 should likewise review the T009 golden negative-case,
locator, and label-rubric proposals. These are reviews, not schema edits.

## T010 validation matrix and acceptance handoff

| Requirement → acceptance → task | Documentary check | Source or human gate still needed |
| --- | --- | --- |
| FR-001 → AC-01 → T002 | Direct/conditional/generic/other-species rubric in `spec.md`. | Four publisher-inspected cases and TEAM borderline review. |
| FR-002 → AC-01/05 → T003 | Type/license decision table and approved review cap. | TEAM checks source application and article-specific terms. |
| FR-003 → AC-02 → T001/T004 | Exact planned queries, fields, offsets, cap, ordering and drift rules. | T004 replay and reviewer transcription check. |
| FR-004 → AC-04 → T005 | DOI wrapper/case/decoding/conflict/duplicate table. | Person 2 display/identity case review. |
| FR-005 → AC-03/08 → T004/T007 | First 3–5 count toward 20; two-page query cap; shortfall rule. | TEAM selection-matrix review; actual pilot acquisition is later work. |
| FR-006 → AC-03/04/05 → T006 | Manifest fields, unknown/failed states, versions. | Person 2 handoff-boundary review. |
| FR-007 → AC-05 → T001/T003 | One T001 source/XML/license check; processing-ready rule. | Later selected papers each need individual source checks. |
| FR-008 → AC-06 → T008 | Read-only field-level contract compatibility table. | Person 2 accepts/rejects gaps before any schema edit. |
| FR-009 → AC-07 → T008/T009 | Golden locator/version and schema-gap table. | Person 2 reviews rubric, negative cases, exact mapping; later 5–10 real questions. |
| FR-010 → AC-09 → T001/T010 | T001 failure/success history, this matrix, consistency review. | T002–T009 checks, checklist review, and final feature-owner acceptance. |

No row claims a selected pilot paper or a validated golden question. Keep the
reviewer-owned corpus checklist unchecked until a human reviews its questions.
T010 cannot be accepted while its upstream task checks remain open.
