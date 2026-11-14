# Implementation Plan: Honeybee Corpus Discovery & Pilot Selection

**Branch**: `002-honeybee-corpus-discovery` | **Date**: 2026-11-14 | **Spec**: [spec.md](spec.md)
**Input**: Planning refinement request and Person 1's 2026-11-14 report of TEAM/Person 2 approval of the current Feature 002 planning baseline and T001–T010 execution in dependency order. See [DECISIONS.md](../../docs/DECISIONS.md) for provenance; T001 was subsequently accepted, while later task checks remain open.

## Summary

Define a publisher-first, source-auditable method to screen PLOS honeybee research. After approval, manually inspect approximately 3–5 papers first; then target 20 eligible, unique papers in the complete initial pilot, counting the first sample. The target is subject to feasibility and a shortfall requires explicit review. This plan produces protocol and validation design, not an operational downloader or a corpus. PLOS Solr is the proposed discovery source; selected individual PLOS JATS files are a later verification step. See [research.md](research.md) for source-backed rationale and unverified live behavior.

## Technical Context

**Language/Version**: Repository targets Python 3.12 for later behavior; this phase is Markdown only.
**Primary Dependencies**: None added. Official Spec Kit 1.4.0, PowerShell scripts, uv setup, and existing draft JSON Schemas.
**Storage**: Planning files in `specs/002-honeybee-corpus-discovery/`; later candidate manifest location and format pending approval.
**Testing**: Requirements-quality review and read-only artifact consistency now; future offline pytest behavior tests RED → GREEN and manual source checks after approval.
**Target Platform**: Windows PowerShell developer workflow.
**Project Type**: Internal scientific corpus selection protocol.
**Performance Goals**: Bounded 3–5-paper first sample and 20-paper complete pilot target; no throughput target in this documentary phase.
**Constraints**: PLOS documented rate/row limits, no broad crawl, no AI calls, no shared-contract change, no unverified scientific record.
**Scale/Scope**: Pilot only; 500-paper expansion deferred.

## Constitution Check

**Before research and after design**: No code or tests were written. Scientific provenance is required for each future decision. Person 1 owns selection and Person 2 reviews shared identity and evidence handoff. Shared contract is read only. No credentials or live AI calls. Future Python behavior must follow Google style, type hints, offline tests, and RED → GREEN. **Status**: planning self-check only. Person 1 subsequently reported TEAM/Person 2 approval of the current Feature 002 baseline and decisions. Person 1 also confirmed TEAM ratification of the exact constitution 0.1.0 text on 2026-11-14; `P0-08` remains unchecked because its task verification is not recorded, and `D-011` still tracks unapproved draft contracts. T001 was accepted after human source checks; the remaining tasks and final feature acceptance remain open.

**Approval gates:** Person 1 approved `spec.md`, `plan.md`, and `tasks.md` and authorized T001–T010 in dependency order, reporting the relevant TEAM/Person 2 planning decisions. Person 1 then explicitly accepted T001, allowing dependent documentary tasks to proceed. Their source/automatic and human checks remain separate. Shared-contract changes require separate field-level approval. After T001–T010 and their verification, the feature owner separately accepts or rejects the completed deliverables. Record task evidence and human outcomes under `docs/DEVELOPMENT_WORKFLOW.md`; do not mark work complete from pre-execution approval alone.

## Existing architecture and feature boundary

The current repository has documentation, Spec Kit, `pyproject.toml`, `uv.lock`, and draft JSON Schemas, but no application Python package, tests, corpus, downloader, database, API, or UI. `docs/ARCHITECTURE.md` proposes PLOS/JATS → Paper → Section → Chunk → embeddings → Person 2 storage/retrieval. `docs/DATA_MODEL.md` and `docs/DATA_CONTRACT.json` are draft, unapproved interchange contracts. `docs/EVALUATION_PLAN.md` and `evals/golden_questions.schema.json` define unpopulated evaluation structure. No new module path is selected.

`docs/TEAM_OWNERSHIP.md` proposes **Feature 001** as a broad corpus, data-contract, and golden-dataset effort, and `docs/CHUNKING_STRATEGY.md` refers to Feature 001 for chunking decisions. No Feature 001 directory or approval was found. **Feature 002** is this narrower corpus discovery and pilot-selection protocol; it does not absorb Feature 001's contract, chunking, or golden-dataset scope. Both identifiers and the existing shared backlog IDs are preserved. `P1-15` is Feature 002's planned protocol item; `P2-24` remains the 20-paper pilot item, and `P2-22`/`P2-23` remain golden-dataset work.

`docs/EVALUATION_PLAN.md` and `evals/README.md` still describe an approximate 10–20-paper starting corpus. Feature 002 recommends 20 as the complete target, with a 3–5-paper first sample and documented feasibility shortfall. Those broader draft evaluation documents are outside this refinement's edit scope; TEAM should reconcile their wording when approving the pilot and planning the separate golden feature.

This feature ends at a selection protocol and planning artifacts. Actual DOI screening, JATS download, manifest population, parser work, source locators, chunking, embeddings, and golden data belong to later approved work. The next proposed feature is **Pilot XML & Golden Evaluation Dataset**; it must use selected source papers and precede Person 2 `P3-13`/`P8-01` retrieval evaluation.

## Phase 0 — Research and decisions

Use the publisher API for candidate discovery, source-page inspection for relevance, and individual JATS verification only for selected pilot articles. Record exact Boolean expressions, field, URL, `fl`, `wt`, `start`, `rows`, sort, type filter, UTC time, result count, and observed response. The first approved execution task must run a small bounded connectivity check, inspect a small number of candidate metadata records, and check individual JATS availability. Record HTTP/parse failures and unknown results without treating them as absence or success; stop dependent selection if the source cannot be verified. Direct requests were **BLOCKED** in the previous planning session; no retry or success is claimed here. Keep one connection, small pages, and spacing compatible with [PLOS FAQ](https://api.plos.org/solr/faq). More detail and alternatives are in [research.md](research.md).

Scientific screening uses the three eligibility classes in FR-001 and publication-type rules in FR-002. Each conditional inclusion needs a reviewer-recorded passage or section demonstrating identifiable honeybee findings. Person 1 reports TEAM approval of at most 3 clearly labeled reviews within the 20-paper target; reviews remain secondary synthesis and never substitute for primary experimental evidence. Duplicate detection uses the documented DOI comparison approach, retains raw identifiers and all discovery paths, and does not infer missing metadata. The first 3–5 manually inspected papers test protocol feasibility; their accepted records count toward the complete 20-paper target. Sampling seeks supported themes and structural diversity, with reasons per chosen article; no arbitrary theme quota. Record protocol version and corpus version separately.

## Phase 1 — Design artifacts and interfaces

- [data-model.md](data-model.md) defines proposed discovery run, candidate decision, and pilot selection records and their null/unknown semantics. This is a screening manifest design, not a competing final ingestion schema.
- `docs/DATA_CONTRACT.json` and `docs/DATA_MODEL.md` remain unchanged. `paper.doi`, `article_type`, `subject_categories`, `license`, `source`, optional `source_url`, XML path/hash, sections, section titles/types/locators, and chunk/version fields cover processed records. Gaps: the schema has no paper language field; required non-null authors/journal/year/license/XML path/hash and required nonempty embedding metadata cannot represent incomplete screening or pre-embedding processed records; DOI comparison and locator stability are undefined; `source_url` is optional. The existing `section.source_locator` and `chunk.source_locator` strings may hold the proposed locator, but their encoding and source-version semantics need Person 2 agreement. These are concrete approval topics, not edits; the manifest remains separate until an approved mapping exists.
- `evals/golden_questions.schema.json` has patterned IDs, question/language, findings, DOIs, sections, relevance labels, quotation or locator, reviewer/status/date, and versions. It does not enforce question-ID uniqueness across the array; labels are free text pending a rubric. It permits quotation without durable locator and requires at least one relevant paper even when `expected_insufficient_evidence=true`. The next golden feature should propose the minimal schema correction of requiring a durable locator for positive evidence and conditionally allowing no `relevant_papers` for genuinely insufficient-evidence cases, after a Person 1/Person 2 decision on their semantics. JSON Schema can enforce required fields, shapes, and `if`/`then` conditions; it cannot generically guarantee uniqueness of one property across arbitrary array objects. Dataset-level validation must check question-ID uniqueness, normalized DOI/corpus membership, locator resolution against pinned source XML, and label rubric; scientific support still requires human review. Any shared schema edit needs Person 1/Person 2 approval. Chunk IDs remain optional, derived mappings.
- [quickstart.md](quickstart.md) is a validation and human review guide. No public API is exposed, so no separate `/contracts/` artifact is needed; the approved shared schema files are referenced directly.

## Proposed manifest and reproducibility

One future manifest row per considered candidate, keyed by normalized DOI when verified, otherwise a temporary screening ID. Minimum fields: protocol/corpus version; run/query reference; original and normalized DOI/unknown; PLOS article URL and observed metadata; relevance class/decision/reason and inspected passage locator; theme; article type; paper-level provenance; JATS and license verification states with evidence URLs; inspection method/time; reviewer and review state. Repeated hits become source paths on that row. A separate run record retains exact query parameters and retrieval context. See `data-model.md` for field groups and state rules. The manifest is proposed only; no file or values are populated now.

## Approved Feature 002 DOI and source-locator approach

For DOI identity, retain each observed DOI and its source; trim surrounding whitespace; remove only a recognized `doi:` prefix or `doi.org`/`dx.doi.org` resolver wrapper; percent-decode the URI path once; validate the resulting DOI-shaped value; and form a comparison key by folding ASCII `A`–`Z` to `a`–`z` only. Do not apply Unicode normalization, discard suffix punctuation, or infer an absent DOI. Conflicts among search, article page, and JATS identifiers remain pending manual review. This follows the [DOI Handbook](https://www.doi.org/doi-handbook/html/) equivalence rule. Person 1 reports Person 2 approval of this Feature 002 approach, not a shared-schema edit.

For a fixed source XML version, use the approved Feature 002 approach of an evidence anchor consisting of normalized DOI, publisher URL, source XML checksum/version, original nested section title/path, and the closest available JATS element `@id` (`sec`, `p`, table, figure, or other evidence container). If the needed element has no `@id`, use a deterministic structural path with sibling positions within the pinned XML plus a short source-text fingerprint for manual confirmation. A structural path is stable only for that exact XML version; if its checksum changes or it no longer resolves, mark the evidence reference stale and reverify it against the new source. Generated chunk IDs may be mapped to the anchor but cannot replace it. JATS documents optional base `id` attributes for [sections](https://jats.nlm.nih.gov/publishing/tag-library/1.4/element/sec.html) and [paragraphs](https://jats.nlm.nih.gov/publishing/tag-library/1.4/element/p.html); this does not establish that a given PLOS XML file contains them. Person 1 reports Person 2 approval of this approach; any exact shared-field encoding or schema change still needs separately reviewed field-level approval before import or golden evaluation handoff.

## Field-level shared ingestion compatibility review (T008 draft)

This is a read-only comparison with `docs/DATA_CONTRACT.json` Draft 2020-12.
The proposed screening manifest is not a processed `Paper → Section → Chunk`
record. A later schema edit requires a separate field-level owner decision.

| Existing field(s) | Observed contract behavior | Minimal handoff proposal or gap |
| --- | --- | --- |
| Root `schema_version`, `processing_version`, `paper` | All required; no explicit `corpus_version`. | Keep protocol/corpus versions in screening records; propose an explicit corpus/source version only for a later approved processed-record revision. |
| `paper.doi` | Required DOI-shaped string; no normalization or raw-variant provenance rule. | Hand off verified DOI plus all observed DOI/source paths separately until Person 2 approves exact representation. |
| `paper.title`, `authors`, `journal`, `publication_year` | Required, with nonempty title/authors/journal and integer year. | An incomplete search hit cannot validate as processed paper; retain unknowns in the manifest. Do not fabricate missing values. |
| `paper.article_type`, `subject_categories` | Type is required nonempty text without enum; subjects are required array, possibly empty. | Preserve publisher type verbatim and normalized screening class separately. An empty subject array must not silently mean observed absence when API omitted the field. |
| Paper language | No field. | Propose a later optional language field only after Person 2 agrees on observed/unknown semantics. |
| `paper.license`, `source`, optional nullable `source_url` | License/source are required nonempty strings; source URL is optional and URI-formatted if present. | Keep article-specific license URL/terms/attribution and publisher URL/status in the manifest; propose explicit provenance fields only after field-level review. |
| `paper.source_xml_path`, `source_xml_sha256` | Both required; hash is 64 hexadecimal characters. | Unknown/inaccessible XML stays a candidate only. Preserve the actual XML path/hash in the later processed record after acquisition. |
| `paper.sections` | Required array that may be empty. | No section claim is made in discovery; a zero-section processed record would need review before import. |
| `section.section_id`, `parent_section_id`, `section_path` | IDs required; parent may be null; path is nonempty array. | Preserve original nested path and source ID when available; exact encoding needs Person 2 approval. |
| `section.original_heading`, `normalized_type`, `source_locator` | Heading may be empty; normalized type and locator are required text; locator format is unspecified. | Propose DOI + pinned XML hash/version + original section path + JATS `@id`, or sibling-index structural path and fingerprint when absent. Do not edit the string contract yet. |
| `section.chunks` and chunk IDs/locators/text | Array required; chunk objects have required IDs, text, and locator fields. | Chunk IDs are derived; never use them as the sole scientific evidence anchor. No chunks are produced in Feature 002. |
| Chunk embedding and version fields | `embedding` can be null or 384 numbers; model/revision/tokenizer/chunking strings remain required. | Screening cannot satisfy these processed fields; future pre-embedding staging semantics need separate review. |

The approved Feature 002 DOI/locator *approach* does not approve new shared
fields, nullability, or a locator encoding. Person 2 must accept or reject each
proposed change before an ingestion handoff or JSON Schema edit. T008's field
comparison is documented here; its manual owner review remains pending.

## Golden evaluation readiness and schema gaps (T009 draft)

The read-only source is `evals/golden_questions.schema.json`; no golden record
or schema edit is made in this feature. A later source-inspected set targets
5–10 human-verified questions before Person 2 retrieval evaluation.

| Existing field or rule | Observed gap | Follow-up prerequisite |
| --- | --- | --- |
| `dataset_version`, `corpus_version`, per-question `source_corpus_version` | Version strings exist, but no schema-level guarantee a question refers to the pinned source XML. | Record corpus membership and XML checksum/version; check them against preserved source files. |
| `question_id` | Pattern exists, but uniqueness of this property across array items is not enforced. | Dataset-level duplicate-ID check. |
| `relevant_papers` | Required with `minItems: 1`, including when `expected_insufficient_evidence=true`. | Person 1/Person 2 decide negative-case semantics; propose a conditional schema change only after field-level approval. |
| `relevantPaper.doi` and `sections` | DOI pattern and nonempty sections exist, but DOI normalization, corpus membership, and section existence are not checked. | Validate normalized DOI against approved corpus and resolve original section path in pinned XML. |
| `evidence.relevance_label` | Required nonempty text, without an approved value rubric. | Person 2 reviews label definitions and handling of partial, conflicting, or irrelevant evidence. |
| Evidence `quotation` or `source_locator` | `anyOf` permits quotation alone; durable locator is not required. | Propose requiring a DOI/section/JATS ID or version-bound structural locator plus XML checksum for positive evidence; verify manually against source. |
| Optional `chunk_id` | Present but may change with chunking. | Treat as derived mapping, never the only ground-truth anchor. |
| `verification_status=verified` / `verified_date` | Conditional date requirement exists, but a date does not prove scientific support. | Independent human source review of every finding, label, quotation, and locator. |

JSON Schema can check required fields, patterns, and conditional shapes after
approval. Dataset-level validation must check ID uniqueness, DOI/corpus
membership, source-locator resolution and checksum match; only a human can
judge scientific support. The exact negative-case rule, label rubric, and
schema diff require Person 2/shared-owner review in the next feature. T009's
manual review remains pending.

## Validation and test strategy

Planning checks: built-in and custom requirements-quality checklists, official read-only `speckit-analyze`, FR→AC and task→FR mapping, shared-contract diff, backlog duplicate review, and `git diff --check`. After approval, first run bounded PLOS connectivity, inspect a small number of metadata records, and verify individual JATS availability; record blocked/failed outcomes and stop dependent work safely. Then manually inspect approximately 3–5 papers before extending toward the complete 20-paper pilot, with a second reviewer checking inclusion, article type, DOI, source, XML, and license. Future behavior tasks, if separately approved, begin with offline pytest cases for DOI wrappers/case/encoding, duplicate paths, missing metadata, and state transitions; show RED before implementation, then GREEN. Pure curation tasks use source review plus reproducible query/manifest audit rather than artificial tests. No paid AI or broad network calls enter tests. Use existing uv/Ruff/mypy/pytest settings; do not add packages without a separate approved reason.

## Dependencies, risks, and mitigations

| Risk or dependency | Action before dependent work |
| --- | --- |
| Codex environment cannot reach PLOS; Person 1 completed and accepted bounded API/XML/source/license checks for one DOI | Preserve both failure and human evidence. Require article-level source/license checks for every later selected paper; if a future execution environment cannot access PLOS, pause operational selection and review the documented Europe PMC proposal. |
| Search index and order drift | Record UTC run time, exact query/parameters, result count, page IDs, and stable sort once verified; retain screening log. |
| Species ambiguity or weak comparative evidence | Human full-text inspection, conditional rubric, explicit exclusion/pending reason. |
| Article type and license variation | Check article page/JATS individually; preserve unknowns, corrections/retractions relationships, and provenance. |
| Feature 002 DOI/locator approach approved as reported, but shared DOI, nullability, locator encoding, and language fields not amended | Obtain separate field-level Person 2/shared-owner approval before changing a contract or handing off import. |
| Golden schema may make durable locators optional and negative cases awkward | Decide minimal compatible correction in next feature before populating questions; Person 2 reviews relevance rubric. |
| Twenty eligible papers may be infeasible in the time available | Use a 3–5-paper first sample to expose feasibility and JATS variation, then aim for 20; report the actual shortfall for a human decision rather than changing the target silently. |

## Project Structure

### Documentation (this feature)

```text
specs/002-honeybee-corpus-discovery/
  spec.md
  research.md
  plan.md
  data-model.md
  quickstart.md
  checklists/requirements.md
  checklists/corpus-quality.md
  tasks.md
```

### Source code (repository root)

No source or test directory currently exists. No source tree is proposed by this planning feature. `docs/` and `evals/` contain the existing shared draft contracts and evaluation framework.

**Structure Decision**: Use only the feature directory and a minimal planned backlog reference; leave shared contracts and all production paths untouched.

## Explicit deferred work

Production acquisition, XML parsing, metadata extraction, section-aware chunking, embeddings (`intfloat/multilingual-e5-small` is downstream context only), Postgres/pgvector, retrieval, FastAPI/LLM, React, actual golden-question curation, and 500-paper scale-up require separate approved scopes. No task in this feature authorizes their implementation.
