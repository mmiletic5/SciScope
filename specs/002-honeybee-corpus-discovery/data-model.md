# Proposed screening data model

This describes a future lightweight selection manifest. It does not alter the processed `docs/DATA_CONTRACT.json` Paper → Section → Chunk model.

## Discovery run

Fields: `run_id`, `protocol_version`, `queried_at_utc`, publisher endpoint/source URL, exact `q`, `fl`, `wt`, `start`, `rows`, `sort`, filters if used, observed `numFound`, returned page IDs, and request outcome. Store one row per query/page. A failed request retains its attempted parameters and error; it is not counted as a successful search.

## Candidate decision

Fields: `candidate_id` (temporary if DOI unknown), every `doi_observed` with its source, documented ASCII-folded `doi_normalized` comparison key or explicit unknown, title as observed, publisher article URL, discovery run IDs, study species/relevance class (`direct`, `conditional`, `excluded`, `pending`), decision reason and inspected source context, scientific theme or unknown, publication type (`primary_research`, `review`, other observed type, or unknown), paper-level provenance URL/status, full-text/JATS state (`verified`, `failed`, `unverified`), and license state (`verified`, `failed`, `unverified`) with article-level evidence URL/terms. Include inspection method and UTC time, reviewer and review state. Optional observed authors/journal/year/language/subjects remain unknown when absent. Retain every raw DOI and discovery path for duplicates. A conflicting DOI, uncertain eligibility, or unknown/conflicting license holds the record for review; none is processing-ready.

## Pilot selection

Fields: `corpus_version`, `protocol_version`, first-sample and complete-pilot candidate IDs, selection date, reviewer, coverage rationale, actual count, shortfall reason, and approval state. In a later separately authorized acquisition task, manually inspect approximately 3–5 papers first; accepted sample papers count toward the complete target of 20 eligible, unique papers. Person 1 reports TEAM approval of at most 3 explicitly labeled reviews within the 20. Only eligible DOI-verified PLOS papers with verified individual XML, provenance, and article-level license may become `processing_ready`. A pending or excluded candidate cannot. Neither the first sample nor the 20-paper target has been achieved here.

## Relation to existing contracts

The future processed `paper` record must use the source-verified DOI and source provenance, then attach sections and chunks from preserved XML. Candidate decisions do not fabricate `authors`, `source_xml_path`, checksum, section IDs, chunk IDs, or embedding versions required by the current draft processed schema. Once an individual XML file is verified and preserved, the reported approved Feature 002 golden-anchor approach is DOI + original nested section title/path + closest JATS element `@id` or a deterministic structural path with sibling positions when IDs are absent + source XML checksum/version. Add a short text fingerprint for fallback confirmation. Structural positions are valid only for the pinned XML version; changed checksum or unresolved path requires revalidation. Chunk IDs remain derived mappings. Person 1 reports Person 2 approval of the DOI key and locator/version approach; exact shared-field encoding, schema changes, and any ingestion handoff still require separate field-level review.

## DOI comparison and duplicate decision table (T005 draft)

The comparison key is an identity aid, never a replacement for the observed
identifier. Apply the approved Feature 002 rule only after the DOI is checked
against the publisher page or article XML. Keep every raw value and search path.

| Input situation | Comparison action | Record state |
| --- | --- | --- |
| Bare DOI with surrounding whitespace | Trim outer whitespace; validate `10.` + 4–9 digits + `/` + nonempty non-whitespace suffix. | Preserve raw and validated value. |
| ASCII case variant | Fold only ASCII `A`–`Z` to `a`–`z` for the comparison key. | Same identity only when the verified keys agree. |
| `doi:` prefix | Remove one recognized ASCII case-insensitive prefix, then validate. | Preserve prefix-bearing raw value. |
| `https://doi.org/` or `https://dx.doi.org/` (also HTTP) | Remove the recognized resolver wrapper and decode the URI DOI path once. | Preserve original URL and decoded DOI. |
| URI path containing `%2F` or other percent encoding | Decode once; reject malformed percent escapes and do not decode the result a second time. | Pending if malformed or ambiguous. |
| Non-ASCII suffix characters | Preserve code points; do not apply Unicode lowercasing or normalization. | Compare only ASCII letters case-insensitively. |
| Possible trailing suffix punctuation | Do not strip punctuation automatically. | Pending if publisher identifiers disagree. |
| Missing or malformed DOI | Do not infer from a title, URL slug, or search match. | Temporary screening ID; DOI unknown/pending. |
| Search/page/article/XML DOI conflict | Retain each value with source URL and time; do not choose one silently. | Pending manual identity review. |
| Same verified key on multiple queries/pages | Merge into one candidate identity while retaining every run ID, page offset, raw DOI, and return position. | Duplicate discovery paths, not duplicate papers. |

This table is a policy specification, not a DOI implementation or a claim that
real DOI variants were observed. T005's case review and Person 2 display
semantics check remain pending.

## Screening manifest states and version rules (T006 draft)

| Record | Required field groups | Unknown/failure behavior |
| --- | --- | --- |
| Discovery run | `run_id`, `protocol_version`, UTC request time, exact URL/`q`/`fl`/`wt`/`rows`/`start`/`sort`/filters, HTTP status or transport error, content type, `numFound` or unknown, returned ordered IDs | Failed requests retain attempted values and error; no invented count or page IDs. |
| Candidate identity | Temporary `candidate_id`, every raw DOI with source, verified comparison key or unknown, all discovery-run/page/position paths, observed title/type/date/subjects or unknown | Conflicting/invalid DOI is pending; no deduplication by title alone. |
| Scientific decision | Relevance class, decision (`pending`, `excluded`, `eligible`), inspected source URL/time and passage locator, reason, species/theme or unknown, reviewer/review state | Search hit begins pending; missing passage or contradictory species remains pending. |
| Access and rights | Publisher page URL/status, individual XML URL/status/content type, XML DOI/hash/version when preserved, article license source/terms/attribution or unknown, object-level exceptions or unknown | Keep `unverified`, `verified`, and `failed` distinct for XML, provenance, and license. Failed and unknown values cannot become processing-ready. |
| Pilot selection | `protocol_version`, `corpus_version`, first-sample flag, selection rationale, coverage axes, selection/review dates, reviewer, actual eligible count, shortfall reason, approval state | No selection is implied by a candidate hit; an unapproved or pending record is excluded from counts. |

`protocol_version` identifies the search/screening rules; `corpus_version`
identifies a later frozen set of accepted source XML. Changing the query or
rubric requires a new protocol version; replacing source XML or membership
requires a new corpus version and revalidation of locators. An observation
may be revised with reviewer, UTC time, source, old value, new value, and
reason rather than silently overwritten. The candidate is `processing_ready`
only after relevance, publication type, DOI, XML, publisher provenance, and
article-level license are all verified and the review state is accepted.
This manifest remains distinct from `docs/DATA_CONTRACT.json` and no populated
manifest is created by Feature 002.

## First-sample and complete-pilot selection matrix (T007 draft)

The later curation task first reviews 3–5 distinct, source-inspected eligible
papers; accepted papers from that sample count toward the complete target of
20. Select from logged candidates across the bounded title/abstract searches,
not simply the first API results. Record each included DOI and why it adds
scientific or JATS coverage; record every exclusion and pending reason.

| Coverage axis | Selection check, without a fixed quota |
| --- | --- |
| Scientific theme | Record the source-supported honeybee theme only after inspecting an eligible article; seek more than one represented theme if available. |
| Evidence type | Prefer direct primary research; include a comparative study only with separable honeybee findings; at most three labeled reviews in 20. |
| JATS variation | Where available, note abstract forms, nested sections, tables/captions, IDs or missing IDs, and correction relationships after inspecting actual XML. |
| Provenance and rights | Require verified DOI, publisher source, individual XML, and article-level license before processing-ready selection. |
| Count and shortfall | Record first-sample accepted count, later additions, unique final count, and any gap from 20 with reason; do not relabel a shortfall as completion. |

The matrix is a review protocol, not evidence that any theme, structure, or
paper has been selected. TEAM's approval of the 3–5-to-20 count and review
cap was reported; source-supported coverage and final pilot acceptance remain
future human checks.
