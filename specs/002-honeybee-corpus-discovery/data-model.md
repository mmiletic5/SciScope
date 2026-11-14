# Proposed screening data model

This describes a future lightweight selection manifest. It does not alter the processed `docs/DATA_CONTRACT.json` Paper → Section → Chunk model.

## Discovery run

Fields: `run_id`, `protocol_version`, `queried_at_utc`, publisher endpoint/source URL, exact `q`, `fl`, `wt`, `start`, `rows`, `sort`, filters if used, observed `numFound`, returned page IDs, and request outcome. Store one row per query/page. A failed request retains its attempted parameters and error; it is not counted as a successful search.

## Candidate decision

Fields: `candidate_id` (temporary if DOI unknown), every `doi_observed` with its source, provisional ASCII-folded `doi_normalized` comparison key or explicit unknown, title as observed, publisher article URL, discovery run IDs, study species/relevance class (`direct`, `conditional`, `excluded`, `pending`), decision reason and inspected source context, scientific theme or unknown, publication type (`primary_research`, `review`, other observed type, or unknown), paper-level provenance URL/status, full-text/JATS state (`verified`, `failed`, `unverified`), and license state (`verified`, `failed`, `unverified`) with article-level evidence URL/terms. Include inspection method and UTC time, reviewer and review state. Optional observed authors/journal/year/language/subjects remain unknown when absent. Retain every raw DOI and discovery path for duplicates. A conflicting DOI, uncertain eligibility, or unknown/conflicting license holds the record for review; none is processing-ready.

## Pilot selection

Fields: `corpus_version`, `protocol_version`, first-sample and complete-pilot candidate IDs, selection date, reviewer, coverage rationale, actual count, shortfall reason, and approval state. After approval, manually inspect approximately 3–5 papers first; accepted sample papers count toward the complete target of 20 eligible, unique papers. A proposed cap of 3 explicitly labeled reviews within the 20 awaits TEAM review. Only eligible DOI-verified PLOS papers with verified individual XML, provenance, and article-level license may become `processing_ready`. A pending or excluded candidate cannot. Neither the first sample nor the 20-paper target has been achieved here.

## Relation to existing contracts

The future processed `paper` record must use the approved DOI and source provenance, then attach sections and chunks from preserved XML. Candidate decisions do not fabricate `authors`, `source_xml_path`, checksum, section IDs, chunk IDs, or embedding versions required by the current draft processed schema. Once an individual XML file is verified and preserved, the proposed golden anchor is DOI + original nested section title/path + closest JATS element `@id` or a deterministic structural path with sibling positions when IDs are absent + source XML checksum/version. Add a short text fingerprint for fallback confirmation. Structural positions are valid only for the pinned XML version; changed checksum or unresolved path requires revalidation. Chunk IDs remain derived mappings. Person 2 reviews DOI key, locator encoding/version semantics, missing-value policy, and any shared-contract effect before ingestion.
