# Research: Honeybee Corpus Discovery & Pilot Selection

**Date**: 2026-11-14. **Status**: T001 was explicitly accepted by Person 1 after human-reported PLOS API, individual XML, publisher-page, DOI, article-type, and license checks. Exact pagination request URLs/times and the Creative Commons license version were not supplied. Formal JATS schema validation, complete corpus selection, and scientific eligibility review remain later work. Two earlier Codex-environment API attempts failed and remain documented below. No corpus was selected or downloaded into the repository.

## T001 human-provided Windows PowerShell observations (2026-11-14 report)

These are Person 1's reported observations from their own Windows environment,
not requests successfully executed by Codex. The exact execution times of the
requests were not supplied; the two pagination requests were about eight
seconds apart. Person 1 explicitly accepted T001 on 2026-11-14. Preserve the
previous Codex failures below as distinct evidence.

| Check | Request or parameters supplied | Reported response and limits |
| --- | --- | --- |
| Initial connectivity | `GET https://api.plos.org/search?q=title%3A%22Apis%20mellifera%22&fl=id%2Ctitle&wt=json&rows=1` | HTTP 200 OK; `Content-Type: application/json`; `numFound=232`; `start=0`; one document: ID `10.1371/journal.pone.0000395`, title “Magnetoreception System in Honeybees (Apis mellifera)”. No type, subject, or eligibility conclusion was supplied for this record. |
| Page 1 | `q=title:"Apis mellifera"`; `fl=id,title,article_type,publication_date,subject`; `wt=json`; `rows=1`; `sort=id asc`; `start=0` | HTTP 200 OK, JSON; `numFound=232`; `start=0`; one document: `10.1371/annotation/20dfdf0f-eab5-4ed6-ba0f-37b55b5ccf6a`; title “Correction: Comparative Sucrose Responsiveness in Apis mellifera and A. cerana Foragers”; `publication_date=2013-12-11T00:00:00Z`; `article_type=Correction`; `subject` absent. A correction is not automatically eligible primary research. |
| Page 2 | Same query/fields/format/rows/sort with `start=1` | HTTP 200 OK, JSON; `numFound=232`; `start=1`; one document: `10.1371/journal.pclm.0000485`; title “Climatic predictors of prominent honey bee (Apis mellifera) disease agents: Varroa destructor, Melissococcus plutonius, and Vairimorpha spp.”; `publication_date=2024-08-29T00:00:00Z`; `article_type=Research Article`; `subject` present with multiple scientific categories, whose exact values were not supplied. No scientific eligibility decision follows from the search result. |

The pagination observations support `rows=1`, distinct `start=0`/`start=1`
offsets, and the requested fields when present; `subject` can be absent. The
two IDs are in ascending order under the requested `sort=id asc`, but two
pages do not establish stable ordering under index changes. The literal URLs
and exact UTC execution times for these two requests were not supplied, so
the table records their reported parameters rather than inventing a URL.
There are three distinct returned IDs across all API probes (one minimal
connectivity sample and two detailed candidate metadata records). Person 1
explicitly directed that these probes be documented separately and accepted
T001 with that disclosure. No additional candidate was inspected or selected
here. `numFound=232`
is a search count, not an eligible-paper count.

**Individual XML, distinct from the two paginated records**: Person 1 reported
`GET https://journals.plos.org/plosone/article/file?id=10.1371%2Fjournal.pone.0000395&type=manuscript`
returned HTTP 200, `Content-Type: text/xml`, and 121676 bytes saved to a
Windows temporary file outside the repository. In PowerShell, `[xml]$doc =
Get-Content -Raw -Encoding UTF8 $xmlPath` succeeded, the document root's
`LocalName` was `article`, and an `article-id` element with
`pub-id-type="doi"` contained `10.1371/journal.pone.0000395`, matching the
requested DOI. Person 1 reported SHA-256
`EE0FC718E4C1C16B2D75347939F618091229BA8B26BE6257C13BF29F8816668F`.
This verifies reported XML retrieval, well-formed XML parsing, an article
root consistent with JATS, and DOI association for this one source. It pairs
the initial DOI/title-only API record with XML; neither detailed paginated
record has a reported XML check, and the initial article type was not supplied.
The exact local destination path was truncated in the supplied hash output.
Person 1 subsequently reported XML `article-type=research-article`, one license
node whose text identified Creative Commons Attribution and required attribution
to the authors and original source, and a matching official publisher article
page at
`https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0000395`.
The publisher page was reported to identify the same DOI and original-research
status and to provide the same licensing statement. The exact license-node text,
license URL, Creative Commons version, and separate page HTTP metadata were not
supplied; do not infer them. The XML-paired source is identified and provenance
is recorded for the T001 access check, but it is not a processing-ready pilot
selection. Formal JATS schema validation and scientific relevance assessment
remain outside the T001 connectivity objective. This XML is not for the
correction or the PLOS Climate result.

**T001 state**: DONE after the documented source checks and Person 1's explicit
human acceptance on 2026-11-14. The exact pagination request URLs and UTC times
were not retained in the supplied transcript; future discovery runs must record
them. The first 3–5-paper screening and scientific eligibility judgments have
not begun.

## Earlier Codex-environment T001 failures (2026-11-14)

**Gate at the time**: Person 1 approved the current `spec.md`, `plan.md`, and `tasks.md` baseline and authorized T001–T010 in dependency order, reporting the relevant TEAM/Person 2 planning decisions. Person 1 confirmed TEAM ratification of the exact constitution 0.1.0 text on 2026-11-14. Approval provenance and unresolved shared-schema decisions are in [DECISIONS.md](../../docs/DECISIONS.md). These Codex-environment attempts were BLOCKED; the later human observations and explicit acceptance above resolved T001 without changing these historical failures.

**Newly observed request**: One HTTPS GET was attempted with PowerShell `Invoke-WebRequest`, `-TimeoutSec 15`, one connection, and no retry:

```text
https://api.plos.org/search?q=title%3A%22Apis%20mellifera%22&fl=id%2Ctitle%2Carticle_type%2Cpublication_date%2Csubject&wt=json&rows=1&start=0&sort=id%20asc
```

Decoded parameters: `q=title:"Apis mellifera"`, `fl=id,title,article_type,publication_date,subject`, `wt=json`, `rows=1`, `start=0`, `sort=id asc`. No filter (`fq`) was sent. PowerShell exited 1 with `System.Net.WebException`: `The underlying connection was closed: An unexpected error occurred on a receive.` No HTTP response status, content type, or body was exposed. This is a transport failure, not evidence of a PLOS HTTP error or of absent records. No malformed response was observed because no response body was received.

**Failed or stopped Codex checks**: API connectivity was BLOCKED in the Codex environment. JSON format, fields, DOI/title/type/species/context, `numFound`, pagination, ordering, and article-type values were not verified by Codex. Codex inspected zero candidate records and issued no XML request. The later human-reported source checks above must not be attributed to Codex.

**Second local-client diagnostic (2026-11-14 00:32:08 UTC)**: The installed `curl.exe` was curl 8.22.0 with Schannel. One GET of the same exact URL above was attempted with `--max-time 15`, `--connect-timeout 5`, `--max-filesize 150000`, and no retry. curl exited 7: `Failed to connect to api.plos.org:443 over proxy 127.0.0.1 after 0 ms: Could not connect to server`. Its reported HTTP code was `000`, remote IP empty, SSL verify result `0`; there was no response header or body. A local read of configured proxy environment variables showed `HTTPS_PROXY`, `https_proxy`, `ALL_PROXY`, `all_proxy`, `HTTP_PROXY`, and `http_proxy` all pointing to `http://127.0.0.1:9`; no credentials were displayed. This identifies an unreachable configured proxy for the curl attempt. It does not establish whether PowerShell used that proxy, whether PLOS itself is reachable, whether TLS would succeed, or whether the query is valid. No direct-connection bypass, retry, or alternate network route was attempted.

**Follow-up**: Person 1 subsequently reported successful bounded API and individual XML checks and accepted T001. The [quickstart](quickstart.md) gives the later protocol-review checks. No alternate source was queried by Codex.

## Problem and recommendation

Find reproducible, scientifically relevant PLOS honeybee studies for a small pilot, with a later path to scale. **Recommendation**: use the PLOS Solr Search API for candidate DOI/metadata discovery, manually screen title/abstract/full text, and verify individual PLOS JATS files for only selected pilot papers. After approval, inspect approximately 3–5 papers first, then target 20 eligible, unique papers including that sample, subject to feasibility. Record exact queries and responses/provenance. Reconsider PLOS bulk XML or its maintained corpus updater only if scaling toward 500 papers is approved. This follows PLOS's own distinction between subset discovery, individual XML, and bulk TDM [PLOS API examples](https://api.plos.org/solr/examples/), [PLOS TDM](https://api.plos.org/text-and-data-mining.html), [PLOS bulk TDM](https://plos.org/text-and-data-mining/).

## Verified facts and limits

- PLOS documents `https://api.plos.org/search` semantics through its `/search` examples: `q`, field-limited queries, Boolean `AND`/`OR`/`NOT`, `fl`, `wt=json`, `start`, and `rows`; default result count is 10. Its examples contain inconsistent page-offset illustrations. Person 1's later one-row `start=0`/`start=1` responses support basic zero-based offset behavior for the reported query, without proving index stability. Source: [query examples](https://api.plos.org/solr/examples/).
- PLOS lists `id` (DOI), `title`, `abstract`, `body`, `everything`, `article_type`, `subject`, `publication_date`, and `timestamp` as search fields. `everything` includes metadata, and body searches can create incidental matches. Source: [search fields](https://api.plos.org/solr/search-fields/).
- PLOS asks users to stay within 10 requests/minute, 300/hour, 7200/day, at most five concurrent connections, and at most 100 rows/request; exceeding limits may lock out an IP. For this pilot use one connection, small pages, and conservative spacing. Source: [PLOS FAQ](https://api.plos.org/solr/faq).
- PLOS documents a known-DOI individual manuscript XML article-file route and discourages using that route for bulk XML. It points to bulk downloads or its corpus maintenance program for large-scale acquisition. Person 1 subsequently reported successful individual XML retrieval for `10.1371/journal.pone.0000395`; other article files remain unchecked. Source: [PLOS TDM](https://api.plos.org/text-and-data-mining.html).
- PLOS's bulk page describes a daily updated whole-corpus JATS ZIP including Articles and Front Matter, without figures or supplements. It is unsuitable for this bounded pilot and requires a separate later scale decision. Source: [PLOS bulk TDM](https://plos.org/text-and-data-mining/).
- JATS represents article metadata, identifiers, article type, sections, and permissions/license information; absence in an article must not be interpreted as a known value. Source: [JATS overview](https://jats.nlm.nih.gov/), [article metadata](https://jats.nlm.nih.gov/publishing/tag-library/1.0/n-ruc0.html), [permissions](https://jats.nlm.nih.gov/publishing/tag-library/1.4/element/permissions.html).
- DOI equivalence uses ASCII case folding, not general Unicode lowercasing. URI percent decoding is relevant to DOI URI comparison. Source: [DOI Handbook](https://www.doi.org/doi-handbook/html/), [DOI URI scheme](https://www.doi.org/resources/DOI_URI_Scheme.pdf). Canonical lower-case display is a project convention to approve, not a DOI requirement.
- JATS 1.4 lists base `id` attributes for both `sec` and `p`, while nested sections are represented by containment. This supports an ID-first locator strategy but does not prove any particular PLOS XML supplies those IDs. Sources: [JATS section](https://jats.nlm.nih.gov/publishing/tag-library/1.4/element/sec.html), [JATS paragraph](https://jats.nlm.nih.gov/publishing/tag-library/1.4/element/p.html).
- PLOS's current terms say article content is usually CC BY or a comparable open license unless otherwise indicated; individual article and object-level exceptions still need inspection and attribution. Source: [PLOS terms](https://plos.org/terms-of-use/), [PLOS content license](https://journals.plos.org/plosone/s/content-license.), [JATS permissions](https://jats.nlm.nih.gov/publishing/tag-library/1.4/element/permissions.html).
- Actual PLOS article pages show honeybee research in pesticide/nutrition and Varroa/health themes, e.g. [dietary phytochemicals and pesticides](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0243364) and [Varroa colony control](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0320037). These are theme feasibility evidence only, not selected pilot records or verified golden findings. Other suggested themes remain to be confirmed article by article.

## Three approaches compared

| Approach | Provenance, access, and reproducibility | Limits and cost | Decision |
| --- | --- | --- | --- |
| PLOS Solr discovery + individual PLOS JATS verification | Publisher primary source; DOI-indexed; documented fields, JSON, pagination; preserve URL/query/time and selected article page/XML evidence | Rate/row limits; human-reported API/XML/license check for one DOI, but Codex network blocked and each later selected paper still needs screening/license checks; article-file route unsuitable for bulk | Recommended for first 3–5, then 20-paper target |
| PLOS whole-corpus ZIP or PLOS corpus updater | Publisher primary source; documented daily JATS bulk access | Whole corpus is large and includes front matter; creates storage/update and filtering work; no need for pilot; licensing still article-specific | Deferred until approved scale-up |
| Europe PMC search/full text | Maintained secondary source with search and XML services, useful cross-check if PLOS fails | Some PLOS records may lack accessible full text there; provenance and license reconciliation add work; search population differs from PLOS | Fallback only, requiring approval and source reconciliation |

Europe PMC documentation: [REST service](https://dev.europepmc.org/RestfulWebService), [copyright/access](https://dev.europepmc.org/Copyright). No library or dependency is needed to establish the protocol; Python 3.12 standard HTTP/JSON tooling could suffice later, but any implementation choice requires an approved plan.

## Proposed full query protocol (partially live-verified)

1. Proposed exact query Q1: `title:"Apis mellifera" OR title:"honey bee" OR title:honeybee OR title:"Western honey bee"`. Proposed Q2: `abstract:"Apis mellifera" OR abstract:"honey bee" OR abstract:honeybee OR abstract:"Western honey bee"`. Keep the four variants as separate subqueries too if PLOS parsing or ranking makes the combined OR hard to audit. Proposed parameters: `fl=id,title,abstract,article_type,publication_date,subject`, `wt=json`, `rows=25`, `start=0,25,...`, and `sort=id asc` for stable paging. These are **proposals**, not validated endpoint behavior. Save literal expression and URL-encoded request, UTC time, `numFound`, and returned IDs. Use one connection, stop after a predeclared page cap, and confirm `start` and sorting with live requests before fixing operational rules.
2. Add narrow body/everything searches only to find missed candidates; these matches cannot independently establish eligibility. Confirm supported `article_type` values with a small live facet or inspected responses before any filter is used. Do not infer that `article_type` labels are uniform.
3. Screen title/abstract, then inspect full text for conditional cases, article type, study species, separable findings, DOI, and individual license. Log exclusion/pending reasons. Normalize DOI identity as specified in `spec.md`; preserve the observed DOI and all query paths.
4. In a later separately authorized acquisition task, manually inspect approximately 3–5 eligible, unique papers as the first smoke-test sample before extending to the complete target of 20 (the sample counts toward 20). Include primary research directly involving *A. mellifera* and conditional comparative research only where honeybee findings are identifiable and scientifically relevant. Exclude generic pollinator work without such evidence. Person 1 reports TEAM approval of at most 3 clearly labeled reviews in the 20-paper pilot; reviews are secondary synthesis, not original experimental evidence. Seek themes actually represented by eligible papers and JATS variation (nested sections, abstract forms, tables/captions, corrections relationships). Record why each chosen article adds coverage and report any shortfall from 20 without silently changing the target.
5. Before designating a record processing-ready, verify the publisher article page and individual JATS XML, compare DOI identity, inspect article license and any relevant object-level restrictions, and record URL/time/status. T001 has human-reported XML access for one DOI; each future selected paper still requires its own check.

## Bounded field-limited search protocol for T004 review

Use the eight separate expressions below as an auditable alternative to the
unverified combined OR expression above. This fixes the planned query syntax
without claiming that all eight expressions or 25-row offsets have been run.
The reported T001 check exercised only `title:"Apis mellifera"` at one-row
offsets 0 and 1.

| Query ID | Literal `q` value |
| --- | --- |
| Q1 | `title:"Apis mellifera"` |
| Q2 | `title:"honey bee"` |
| Q3 | `title:honeybee` |
| Q4 | `title:"Western honey bee"` |
| Q5 | `abstract:"Apis mellifera"` |
| Q6 | `abstract:"honey bee"` |
| Q7 | `abstract:honeybee` |
| Q8 | `abstract:"Western honey bee"` |

For each query use `https://api.plos.org/search`,
`fl=id,title,abstract,article_type,publication_date,subject`, `wt=json`,
`rows=25`, `sort=id asc`, no publication-type filter, and `start=0` then
`start=25` only if needed. The predeclared cap is two pages per query (at most
16 requests and 400 returned rows across all eight queries). Issue one request
at a time, at least eight seconds apart, below the documented
10-per-minute guidance. Stop on non-200, malformed JSON, missing `response`,
an empty page, or a page beyond `numFound`; record the failure without silently
switching sources. Save the exact URL-encoded request, UTC time, HTTP status,
content type, `numFound`, `response.start`, IDs in returned order, and any
field absence for each page. Preserve index-drift differences on a later run;
`sort=id asc` is a requested order, not a promise of immutable index contents.

Screen title and abstract first, then inspect the publisher page/full text for
conditional cases. Do not apply an API type filter until source values have
been checked; the T001 response included both `Correction` and `Research
Article`. Keep every hit and exclusion reason, but only a source-inspected,
DOI-verified paper may enter the later sample. If this cap does not yield
enough eligible papers, record the shortfall and request a reviewed extension
or a separately approved rescue query; do not silently change the cap.
The second-reviewer replay of exact page IDs and the eight-query live behavior
remain T004 verification work.

## Approved decisions, open decisions, and gaps

- Person 1 reported live API fields, basic offset pagination, two API article-type values, a search count, and individual XML/source/license observations for one DOI. Stable sorting beyond two pages, exact pagination request URLs/times, the Creative Commons license version, scientific eligibility, and formal JATS validation remain **unverified**. Documentation alone does not prove present behavior.
- No selected pilot DOI, source quotation, processing-ready license decision, eligible-paper count, or theme quota is claimed here. The one XML file was saved outside the repository by Person 1.
- Person 1 reports TEAM/Person 2 approval of the documented conditional inclusion rule, review cap, DOI comparison policy, source locator/XML versioning approach, screening, provenance, and unknown handling for Feature 002. Individual scientific eligibility and license terms still require source inspection. Exact shared-field encoding, source-language and article-license acceptance decisions beyond the documented rules, and field-level schema changes remain separate review topics; no shared contract was approved for editing.
- The current draft data contract requires complete processed-paper metadata and XML path/checksum; a screening manifest therefore must stay separate. The golden schema permits quotation without locator, and a negative question still requires one relevant paper; these require next-feature policy and possibly minimal shared schema approval.

## Minimal fallback proposal if PLOS access remains blocked

Europe PMC could be evaluated in a separately approved source check using its
[official REST documentation](https://dev.europepmc.org/RestfulWebService) and
[copyright/access guidance](https://dev.europepmc.org/Copyright), previously
reviewed for this feature. It was not queried in T001. Record exact Europe PMC
query, time, returned identifiers, full-text availability, and license/source
terms; reconcile each candidate DOI and publication identity against PLOS
before treating it as a PLOS pilot candidate. A Europe PMC result is secondary
discovery provenance and may have different indexing, XML availability, and
reuse terms. Preserve both source paths in a future screening manifest. Any
non-PLOS XML used for processing or any new shared source/locator field would
need explicit Person 2 and shared-owner field-level review. PLOS remains the
canonical publisher source under the current plan; this proposal grants no
fallback execution or schema-change approval.
