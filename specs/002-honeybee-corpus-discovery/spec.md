# Feature Specification: Honeybee Corpus Discovery & Pilot Selection

**Feature Branch**: `002-honeybee-corpus-discovery`
**Created**: 2026-11-14
**Status**: Draft — approval pending
**Input**: Person 1 planning request and repository governance.

## Problem and scope

SciScope needs a defensible method to identify real PLOS papers with meaningful *Apis mellifera* evidence before acquisition, processing, and retrieval evaluation. Search matches alone cannot establish eligibility. This feature defines a reproducible discovery and selection protocol: first inspect approximately 3–5 papers as a smoke-test sample, then aim for 20 eligible, unique papers in the complete initial pilot, subject to feasibility. The first sample counts toward the 20. This session creates planning artifacts only; neither stage has been acquired or approved for execution.

In scope: scientific and publication-type screening, query design, DOI identity, duplicate handling, diversity, source and license checks, a lightweight candidate manifest, and read-only contract/evaluation review. Out of scope: downloading a corpus, production downloader, JATS parser, chunker, embeddings, database, API, UI, populated golden questions, shared-contract edits, and expansion toward 500 papers.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Screen scientific relevance (Priority: P1)

Person 1 classifies each candidate from inspected title, abstract, and when needed full text. Primary research directly involving *A. mellifera* is eligible. Comparative or broader research is conditional only if identifiable, scientifically relevant honeybee methods or findings can be attributed to *A. mellifera*. Generic bee/pollinator mentions and other-species-only studies are excluded. A small, explicitly labeled minority of reviews may be selected for coverage, but their synthesis is not primary experimental evidence. Ambiguity is held for review.

**Independent Test**: A reviewer applies the rules to direct, comparative, generic, and other-species examples and records reasons.

**Acceptance Scenarios**:

1. **Given** direct *A. mellifera* research, **when** evidence is inspected, **then** the decision records supporting source context.
2. **Given** a comparative study without separable honeybee findings, **when** screened, **then** it is excluded or held with a reason.
3. **Given** a keyword-only bee mention, **when** screened, **then** it is excluded.

### User Story 2 - Reproduce bounded pilot selection (Priority: P1)

Person 1 records exact searches, dates, ordering, pages, screening, DOI identity, and selection rationale. After approval, a first 3–5-paper manually inspected sample tests the protocol; the complete pilot then targets 20 eligible, unique papers, including that sample, across supported scientific themes and varied JATS structures, not merely the first matches. Any shortfall is reported rather than relabeled as success.

**Independent Test**: A second reviewer can repeat searches and trace all decisions, including changes caused by a later index state.

**Acceptance Scenarios**:

1. **Given** the same DOI on multiple pages or in resolver and bare forms, **when** candidates are combined, **then** one identity remains with all discovery paths.
2. **Given** multiple pages, **when** selecting a pilot, **then** a recorded ordering, page range, and screening log explain the selection.
3. **Given** a proposed pilot, **when** the first sample is reviewed, **then** approximately 3–5 unique papers have manual eligibility, DOI, provenance, license, and individual XML checks before expansion toward 20.

### User Story 3 - Prepare contract and evaluation handoff (Priority: P2)

Person 1 records source, license, article type, and future section/locator prerequisites. Person 2 can review compatibility without treating a candidate manifest as a processed Paper → Section → Chunk record.

**Independent Test**: Person 2 can identify ingestion and golden-data decisions from a field-level compatibility note.

**Acceptance Scenarios**:

1. **Given** unverified XML or license, **when** a candidate is considered, **then** it remains pending or excluded from processing-ready selection.
2. **Given** a future golden evidence reference, **when** chunk IDs change, **then** DOI plus source section and durable locator still identify it.

### Edge Cases

- Search variants include `Apis mellifera`, `honey bee`, `honeybee`, `Western honey bee`, and justified subspecies, but every inclusion needs source inspection.
- Corrections linked to research are not independent studies. Reviews, editorials, and front matter need explicit publication-type decisions.
- Absent/conflicting DOI, inaccessible JATS, uncertain type, missing license, non-English text, and incomplete metadata remain unresolved rather than guessed.
- Partial Solr documents or corrected article versions must not silently double-count a paper.
- A theme is represented only after an inspected, eligible PLOS article supports it.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The proposed protocol MUST distinguish primary research directly involving *A. mellifera*, conditional comparative/broader research with identifiable and scientifically relevant *A. mellifera* findings, and excluded generic/other-species work; every decision records inspected source context and a reason. Uncertain relevance remains pending human review.
- **FR-002**: The proposed pilot MUST distinguish primary research, reviews, corrections, editorials, and front matter. Primary research with accessible full text is the default. Reviews MAY form a separately labeled minority (proposed cap: at most 3 of 20) when they add coverage, and MUST NOT be represented as original experimental findings. Corrections, editorials, front matter, and inaccessible full text are excluded from processing-ready selection; the proposed cap awaits TEAM review.
- **FR-003**: Discovery MUST record exact PLOS Boolean queries, fields, parameters, search time, result count, page offsets, ordering, source URL, and type treatment. Title/abstract matches seed discovery; body/everything matches require stronger screening.
- **FR-004**: Identity MUST use a source-verified DOI. Trim surrounding whitespace; remove only a recognized `doi:` prefix or `doi.org`/`dx.doi.org` resolver wrapper; percent-decode a URI DOI path exactly once; then compare by ASCII-only case folding without changing non-ASCII code points or stripping possible suffix punctuation. Preserve each original identifier and discovery path. Hold malformed encoding, conflicting source DOIs, or an uncertain DOI for manual review; deduplicate across pages/searches only when the verified comparison keys agree. This policy is provisional until Person 2 review.
- **FR-005**: After approval, the first approximately 3–5 distinct papers MUST be manually inspected as a smoke-test sample before expansion to a complete target of 20 distinct eligible PLOS papers, subject to feasibility. The sample counts toward 20. Document any shortfall, thematic and structural variation without fixed quotas, bounded screening and individual XML checks, and prohibit scale-up before pilot approval.
- **FR-006**: Each considered record MUST retain decision/reason, DOI or explicit unknown, PLOS link, observed title, publication type, theme/unknown, relevance class, JATS and license verification states, inspection method/time, and selection protocol/corpus version. Missing metadata stays explicit.
- **FR-007**: Processing-ready selections MUST have individually verified full-text/JATS access, paper-level source provenance, and inspected article-level license/reuse terms with attribution requirements. Unknown, conflicting, or failed eligibility, XML, provenance, or license checks MUST leave the candidate pending or excluded and retain reason, source, and time; no silent fallback is allowed.
- **FR-008**: The screening manifest MUST be separate from the draft processed Paper → Section → Chunk contract. Any `docs/DATA_CONTRACT.json` change needs a field-level gap statement and Person 2/shared-owner approval first.
- **FR-009**: Future golden evidence MUST anchor to normalized DOI, original source section title/path, a JATS element ID when available or a version-bound structural locator when absent, and the source XML version/checksum. If an XML revision invalidates a locator, revalidation is required. Chunk IDs are derived mappings only. Plan a separate follow-up 5–10-question manually verified set before Person 2 retrieval evaluation; Person 2 must review any shared-contract impact.
- **FR-010**: Future validation MUST cover direct/conditional/excluded relevance, primary-versus-review evidence, malformed and duplicate DOI, unknown metadata, missing XML/license, absent JATS IDs, and index/source drift. The first approved execution task MUST use bounded PLOS connectivity, candidate metadata, and individual JATS checks with safe failure recording and manual verification; no broad acquisition is allowed.

### Scientific and non-functional requirements

- **NFR-001**: Search and selection records must be reproducible, with source provenance and index changes acknowledged.
- **NFR-002**: Scientific findings, DOI values, licenses, quotations, and human approvals must derive from inspected sources; model output cannot establish ground truth.
- **NFR-003**: Pilot discovery must respect PLOS API access guidance and avoid broad crawling or bulk article-file requests.
- **NFR-004**: Any later Python behavior follows Python 3.12, Google style, typing, pytest RED → GREEN, offline checks, and uv conventions. No dependency is approved here.

### Key Entities

- **Discovery run**: Query, parameters, time, order, pages, result count, source, protocol version.
- **Candidate decision**: Observed identity/metadata, normalized DOI or unknown, eligibility/reason, inspection provenance, theme/type, XML/license states, review state. This is a screening artifact, not an ingestion contract.
- **Pilot selection**: First 3–5-paper smoke-test sample and complete 20-paper target, with rationale, variation coverage, shortfall status, and corpus version.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **AC-01 / SC-001**: Reviewers can classify direct, comparative, generic, and other-species cases; no keyword-only inclusion. Maps FR-001/002.
- **AC-02 / SC-002**: A reviewer can reconstruct every query, date, page range, and ordering rule. Maps FR-003, NFR-001.
- **AC-03 / SC-003**: After approval, approximately 3–5 unique papers are manually inspected first; the complete pilot targets 20 eligible, unique real PLOS papers including the first sample, with decisions, variation rationale, and an explicit shortfall report if 20 is infeasible. Maps FR-005/006.
- **AC-04 / SC-004**: Verified DOI variants collapse to one identity under the documented ASCII comparison policy; original values/paths remain, and unknown or conflicting metadata is explicit. Maps FR-004/006.
- **AC-05 / SC-005**: Every processing-ready selection has recorded individual JATS, paper-level provenance, and license checks; uncertain or failed checks block readiness. Maps FR-007.
- **AC-06 / SC-006**: Person 2 receives a field-level compatibility note; shared contract remains unchanged pending approval. Maps FR-008.
- **AC-07 / SC-007**: Follow-up golden plan uses DOI + original section + JATS ID or version-bound structural locator + source checksum, survives chunk-ID changes, targets 5–10 independently verified questions, and states Person 2 approval/dependency. Maps FR-009.
- **AC-08 / SC-008**: Pilot is bounded; 500-paper acquisition is deferred. Maps FR-005, NFR-003.
- **AC-09 / SC-009**: Validation matrix covers listed positive/negative cases, bounded connectivity/candidate/JATS checks, safe failure recording, and human review before expansion. Maps FR-010.

## Assumptions and pending decisions

- Primary research and the small labeled review minority are provisional selection recommendations. TEAM must approve the proposed review cap and whether reviews count within the 20-paper target; this draft proposes that they do.
- The 20-paper target matches `P2-24`; 3–5 manually inspected papers are an initial smoke-test subset, not an alternative completion target. If 20 eligible papers cannot be found, report the shortfall for human decision.
- The DOI comparison rule and source-locator fallback are proposed, not approved shared-contract semantics. Person 2 must review them alongside the conditional comparative threshold, license acceptance rubric, and source-language handling.
- Current live PLOS endpoint, facet values, and article-file responses were not verified in this session; validate them before operational use.

## Ownership and dependencies

Person 1 owns protocol and future curation. Person 2 reviews identity, provenance, unknown-value semantics, ingestion compatibility, and golden locators. TEAM retains shared scope, licensing policy, and approval. The next proposed feature, **Pilot XML & Golden Evaluation Dataset**, depends on accepted selection and source inspection and precedes Person 2 `P3-13` and `P8-01`.

**Pre-execution gate:** Before T001, the feature owner must explicitly approve this feature's `spec.md`, `plan.md`, and `tasks.md` and authorize T001. Approval of that bounded source check does not approve unresolved TEAM eligibility/licensing decisions, Person 2 contract/locator decisions, or dependent tasks. The applicable constitution and repository workflow still govern every task.

**Post-execution gate:** After T001–T010 and their applicable automated and manual verification, the feature owner must explicitly accept or reject the completed Feature 002 deliverables. No task or feature is complete merely because planning artifacts were reviewed or T001 was authorized. Neither gate has been satisfied by this draft.
