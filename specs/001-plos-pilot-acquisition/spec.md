# Feature Specification: PLOS pilot acquisition

**Feature Branch**: `001-plos-pilot-acquisition`  
**Created**: 2026-11-14  
**Status**: Approved 2026-11-14 by Person 1 (spec and plan)  
**Input**: Person 1 pilot of 15–20 real PLOS honeybee research articles.

## Problem and scope

Person 1 needs a small, inspectable source corpus for later processing. Search creates candidates; a human screens and commits a selection; download takes its DOI list only from that selection and resolves journal and provenance from the committed candidate records before producing raw XML and front-matter metadata. The search hit count is never an eligibility count.

## User Scenarios & Testing

### User Story 1 — Review candidates (Priority: P1)

A human reviews candidate articles and chooses a topic-spanning sample.

**Independent test**: A mocked search produces candidate records and per-arm hit counts without assigning relevance classes.

1. **Given** the six title/abstract query arms, **when** search runs, **then** it records each `q`, `fq`, `numFound`, search date, and candidate DOI, with duplicate candidates combined by normalized DOI. Each candidate also carries Solr `id`, `title`, `journal`, `publication_date`, and `abstract` for human screening only.
2. **Given** committed candidate records, **when** the human reviews them, **then** only 15–20 PLOS research articles judged `measured_mellifera` or `honey_bee_unqualified` are entered in `selection.tsv` with `doi`, `class`, `reason`, `topic`, and `methods_checked`; `methods_checked` is `yes` for `honey_bee_unqualified` and may be empty otherwise. Reviewed borderline/excluded judgments are recorded in `screening.tsv` and never selected. The human stops screening once the selection is complete and assigns at least three distinct topics. A selected DOI absent from `candidates.jsonl` fails validation.

### User Story 2 — Acquire selected sources (Priority: P2)

Person 1 downloads only the committed selection and obtains verifiable source records.

**Independent test**: Mocked downloads for selected DOIs yield XML, manifest, and metadata; an unselected candidate causes no download.

1. **Given** a valid selection, **when** download runs, **then** each accepted article has raw JATS XML and a manifest record with normalized and original DOI, source URL, UTC retrieval time, XML SHA256, XML-verified license, and query provenance (`q`, `fq`, `numFound`, date).
2. **Given** an existing normalized DOI, **when** its XML is retrieved again, **then** equal digests are reported as duplicates and unequal digests as conflicts, without silently replacing source data.
3. **Given** a selected article whose XML fails research-article, English, license, DOI, or parse checks, **when** download runs, **then** it is rejected with an actionable reason and not counted as acquired.

### Edge cases and failures

Malformed DOI or URL `id`; missing/invalid XML; absent license or language; inconsistent DOI; HTTP timeout, 429, or 5xx; interrupted run and restart; duplicate DOI under different spelling; conflict after changed XML; selection outside 15–20 or containing an excluded class. Failures remain visible and resumable. A human resolves eligibility and topic balance.

## Requirements

### Functional requirements

- **FR-001**: Search MUST cover `Apis mellifera`, `honey bee`, and `honeybee` in both title and abstract, using `doc_type:full` and `article_type:"research article"` filters; report each arm's `numFound` as hits, not eligible papers.
- **FR-002**: Candidate records MUST preserve search provenance and Solr `id`, `title`, `journal`, `publication_date`, and `abstract` for human screening, without an automatic relevance classifier. XML front matter remains the source of truth for acquired metadata.
- **FR-003**: Committed `selection.tsv` MUST have exactly `doi`, `class`, `reason`, `topic`, and `methods_checked` columns and contain 15–20 unique normalized DOIs from reviewed candidates, each with an included class code, short human reason, and human-assigned topic; at least three distinct topics MUST be represented. `methods_checked` MUST be `yes` for `honey_bee_unqualified` and MAY be empty otherwise; a named non-mellifera *Apis* species is not unqualified. Only reviewed candidates appear in `screening.tsv`; screening may stop once 15–20 are selected. Reviewed borderline/excluded assessments MUST be recorded there but MUST NOT enter the selection. The validator MUST reject a selected DOI absent from committed `candidates.jsonl`.
- **FR-004**: Search and download MUST use sequential requests (one connection), at least 6.0 seconds between request starts, a per-run request cap, at most 100 rows/search request, bounded retries with backoff, and resumability; download MUST take its DOI list only from the selection file. The PLOS limits of 10 requests/minute, 300/hour, 7,200/day, and five concurrent connections remain documented; repeat runs must respect the hourly/daily totals.
- **FR-005**: DOI normalization MUST trim, strip `doi:`, `https://doi.org/`, `http://doi.org/`, `https://dx.doi.org/`, and `info:doi/`; defensively percent-decode a URL `id` parameter; strip trailing `.`, `,`, `;`, and an unpaired `)` or `]`; lowercase; and accept only `^10\.[0-9]{4,9}/\S+$`. The original value MUST be retained.
- **FR-006**: For each acquired article, manifest MUST preserve normalized and original DOI, source URL, UTC `retrieved_at`, XML SHA256, XML-verified license, and each contributing query's `q`, `fq`, `numFound`, and date. Download MUST look up journal and all matching query arms by normalized DOI in committed `candidates.jsonl`; `selection.tsv` supplies only the selected DOI list and human fields. A selected DOI absent from candidates is a validation error. Same DOI plus same digest is a duplicate; same DOI plus different digest is a conflict.
- **FR-007**: Metadata MUST contain only front-matter title, authors, journal, publication date, article type, subjects, abstract, license, and language, traceable to the XML. No sections or chunks are parsed.
- **FR-008**: Raw XML MUST reside in gitignored `data/raw/plos/`; candidate, screening/selection, manifest, and metadata records MUST reside in committed `data/pilot/`. Automated HTTP tests MUST use mocks and clearly labeled synthetic fixtures, with no invented scientific content.

### FR-003 human screening codebook

| Group | Code | Human interpretation |
| --- | --- | --- |
| Included; selectable | `measured_mellifera` | *Apis mellifera* is the studied organism. |
| Included; selectable | `honey_bee_unqualified` | “Honey bee” or “honeybee” without a named species; check Methods. A named non-mellifera *Apis* species does not qualify. |
| Borderline; never selected | `comparative_mellifera` | *A. mellifera* is compared with other species. |
| Borderline; never selected | `species_ambiguous` | Species cannot be determined. |
| Excluded; never selected | `background_only` | Honey bee appears only as background or motivation. |
| Excluded; never selected | `other_species_only` | Studies only other species, including non-mellifera *Apis*. |

### Non-functional requirements and exclusions

Search/download failures must have actionable errors and preserve completed work. No paid AI, automatic scientific classification, section parsing (F002), embeddings, database import, or live download by the agent. The pilot does not approve the draft downstream Paper/Section/Chunk contract.

### Key entities

**Candidate**: DOI and one or more query-arm provenance records. **Screening decision**: DOI, human class and reason; only included classes enter **Selection**. **Manifest entry**: selected DOI, XML origin, digest, license, time, and query lineage. **Metadata entry**: XML front matter only.

## Success Criteria

- **SC-001**: A human can inspect all six arm counts and create one valid 15–20 DOI selection with at least three distinct human-assigned topics; no hit count is labeled eligible and no unreviewed candidate enters `screening.tsv`.
- **SC-002**: Every accepted DOI has one inspectable XML file, manifest entry, and front-matter metadata entry with matching DOI and digest; unsuccessful selections are explicitly reported.
- **SC-003**: Repeating a completed download adds no duplicate article; changed bytes for an existing DOI yield a visible conflict.
- **SC-004**: All offline behavior checks pass, including at least 12 DOI normalization cases; a human verifies the live run before completion is marked.

## Assumptions

Only PLOS-hosted articles are in scope. Selection is provisional until the XML confirms English, article type, DOI, and license. Actual selected DOIs and topics are human decisions. The live run in the user's terminal produces the pilot data files.
