# Feature Specification: Data contract refresh and pilot delivery

**Feature Branch**: `004-data-contract-delivery` | **Created**: 2026-11-17
**Status**: Draft; specification and plan approval NOT RECORDED; planning only.
**Input**: Person 1's F004 instructions, D1–D10, and this session's approved
clarification that vector rows map through embedding-manifest entry IDs.

## Context and scope

Person 2 needs a validated, reproducible handoff of the real F001–F003 pilot
for later PostgreSQL/pgvector import (P2-20). The bootstrap nested contract
does not describe the flat records already written. F004 describes and
packages those records without changing upstream files or their contents.
Person 1 owns delivery; Person 2 reviews the contract PR. There are no formal
sign-offs. This planning run creates only the four feature Markdown files;
source, tests, existing documentation, data, evidence and backlog stay untouched.

## User Scenarios & Testing

### User Story 1 — Reproduce a delivery (Priority: P1)

Person 1 builds a complete package from validated pilot artifacts.
**Why this priority**: Import must start from a complete, traceable set.
**Independent Test**: A labeled synthetic offline set produces six files,
unchanged copies of existing outputs and identical bytes on a repeated build.

**Acceptance Scenarios**:
1. **Given** matching complete acquisition, parser, chunk and embedding outputs,
   **When** delivery runs twice, **Then** every delivered file is identical,
   paper metadata is joined by normalized DOI, and the committed delivery
   manifest is identical to its package copy.
2. **Given** failed upstream validation, duplicate/missing join keys, conflicting
   checksums or unsafe output aliases, **When** delivery runs, **Then** it
   refuses publication and preserves the previous complete package.

### User Story 2 — Verify the received package (Priority: P1)

Person 2 verifies an out-of-band archive's extracted package before import.
**Why this priority**: Corruption and broken joins must be detected offline.
**Independent Test**: Synthetic corruptions yield bounded, collected findings
without XML, paragraphs, cache access, a key or network.

**Acceptance Scenarios**:
1. **Given** the package and matching repository reports, **When** verification
   runs, **Then** it checks structures, hashes, counts, relationships, versions
   and vectors and reports zero failures for a valid complete set.
2. **Given** independently corrupted or missing files, **When** verification
   runs, **Then** all safely evaluable findings are collected, partial sets
   are rejected, and diagnostics contain no source prose or sensitive values.
3. **Given** identical good and mutated record fixtures, **When** schema and
   runtime structural validation run, **Then** their acceptance agrees.
4. **Given** a valid old package and later edits to local parser/classifier
   source files, **When** verification runs, **Then** informational source
   digests do not cause rejection; payload/report integrity and real version
   identifiers are still checked.

### User Story 3 — Read and trace the handoff (Priority: P2)

Person 2 reads metadata, chunks and vector rows and can trace citations to
locators using a short guide. **Why this priority**: Correct imports require
correct joins and source interpretation, beyond checksum agreement.
**Independent Test**: Synthetic Unicode JSONL and binary matrix fixtures load
through the documented helpers; a human checks a real citation trace locally.

**Acceptance Scenarios**:
1. **Given** raw U+0085, U+2028 or U+2029 inside a JSON string, **When** JSONL
   is read, **Then** records split only on LF and retain those characters.
2. **Given** vector row `i`, **When** its owner is needed, **Then** use
   `embedding_manifest.entries[i].chunk_id` to join to the matching chunk,
   irrespective of chunk-file line order (session-approved D5 clarification).
   The guide opens with `vectors_by_chunk_id` and forbids zipping vectors
   with `chunks.jsonl` lines by position.
3. **Given** a citation and locally retained raw XML, **When** the guide's JATS
   helpers are used, **Then** locators resolve against the original digest;
   `(untitled)` is never displayed as a heading.

### Edge cases and failure scenarios

Legal zero-own-paragraph sections, structured abstracts, untitled and implicit
sections, nullable parents and model revision, ordered subjects, free-text
licenses, raw language casing and empty author given names must survive.
Reject malformed JSON/UTF-8, duplicate JSON keys, extra/missing fields, booleans
as numeric fields, invalid locators, duplicate IDs, orphan/cyclic parents,
cross-paper joins, stale reports, partial vectors, trailing binary fragments,
nonfinite values, wrong norms and output paths aliasing inputs. Do not infer
missing metadata, a model revision, or content omitted upstream.

## Requirements

### Functional Requirements

- **FR-001**: Refresh one Draft 2020-12 `docs/DATA_CONTRACT.json`, schema_version
  `0.3.0`, draft until Person 2 PR approval. Its root describes delivery_manifest;
  `$defs` describes paper, section, chunk and embedding_set, usable via `$ref`.
  Describe exact flat fields, DOI normalization, taxonomy v0, locator v1 and
  version semantics. Every upstream handoff item must have a reconciliation row.
- **FR-002**: Produce DOI-sorted `papers.jsonl` by a one-to-one metadata/manifest
  join using D3's exact retained fields and only derived `publication_year`.
  Preserve raw values, including observed `EN`/`en`; exclude abstract,
  query_provenance and raw_xml_path. The schema MUST NOT constrain language
  letter case; the guide compares language case-insensitively. Check duplicate
  license values agree. Abstract exclusion is closed by Person 1 in this session.
- **FR-003**: Publish exactly the D2 six-file package under ignored
  `data/delivery/pilot/`, preserving existing sections, chunks, vector bytes
  and embedding manifest. New paper/manifest output is atomic and deterministic.
  Commit only the identical small `data/pilot/delivery_manifest.json` copy.
  Prefer staging in a sibling temporary directory and replacing the whole
  package directory; handle the committed copy in the same all-or-fail logic.
- **FR-004**: Delivery manifest records contract version, counts, per-payload
  sha256/bytes/record count, real processing identities and embedding-set facts.
  It has no timestamps, prose, filesystem paths or secrets. It must not hash
  itself. Existing retrieval/creation provenance in copied files is preserved.
  `processing_versions.parser.source_sha256` and `taxonomy.source_sha256`
  are informational provenance only: 64 lowercase hex with internal consistency,
  never compared to source files in the local checkout.
- **FR-005**: Describe provider/model/dimensions, float32 little-endian layout,
  manifest-entry row mapping, prefixes, norms/tolerance, chunks/vectors digests
  and nullable model revision. Queries use the same provider, model, dimensions
  and query_prefix. D-004 stays Proposed; dimensions are not fixed at 384.
- **FR-006**: Add offline `deliver` and `validate-delivery` pipeline subcommands
  with F003 0/1/2 statuses. `deliver` first runs existing chunk and embedding
  validation and refuses failure; use sanitized F003-style error codes.
- **FR-007**: `validate-delivery` checks file digests/size/counts, exact record
  structure and unique IDs, paper/section/chunk foreign keys, parent ownership,
  xml_sha256 including every locator digest via `locator_digest()`, section-path
  equality and version consistency; reuse F003 vector validation for row count,
  dimensions, finiteness, norms and complete-set status. Compare parse/chunk/
  embedding report counts, enforce manifest purity and reject partial sets.
  Check parser/taxonomy source-digest shape and internal consistency only;
  do not compare them with local source bytes. Continue comparing the real
  chunking_version, token_counter_id and template_version identifiers.
  Print `error: <code> count: <k> first: <ids>` and `failures: <n>`.
- **FR-008**: Runtime validation and readers use stdlib only. Offline dev
  jsonschema parity tests cover the same good/mutated manifest and record
  structures. Cross-record/byte semantics have separate tests, not schema claims.
- **FR-009**: Supply tested `delivery/reader.py` helpers `iter_jsonl`,
  `load_vectors` and `vectors_by_chunk_id(manifest_path, vectors_path, *,
  dimensions)` returning chunk_id → vector tuple by manifest entry order,
  plus `docs/DELIVERY_GUIDE.md` of about two pages or less, opening with that
  mapping helper and forbidding positional zipping with chunk-file lines:
  contents, verification, LF-only JSONL, vector mapping, query rule, local XML
  resolution, citation fields, omissions, F003 limits and PR review process.
- **FR-010**: After implementation, record automated and human verification,
  archive SHA256, Person 2's PR review and feature-PR CI result on the same branch
  before squash merge. Synchronize D-007, data model, architecture/chunking
  pointers and backlog. P2-20 is checked only after human acceptance; P2-24
  remains open. Never add placeholders to EVIDENCE.md.
  Before sending, Person 1 extracts the archive to a fresh temporary directory
  and validates its `pilot` directory. Append a correction to the F001 evidence
  record: raw xml:lang in metadata is 4 `EN` and 13 `en`, not `EN 17/17`;
  preserve the original evidence text.

### Non-functional requirements

No network/key/cache access in delivery verification; no paid AI test calls.
Preserve upstream bytes and Unicode code-point span offsets. Two builds on
unchanged inputs must match byte-for-byte. Errors never echo article prose,
credentials or absolute paths. No larger-corpus performance claim is made.

### Key Entities

- Paper: normalized DOI and original metadata/provenance plus derived year.
- Section: flat own-paragraph count, hierarchy, taxonomy and digest-bound locator.
- Chunk: one section, nonempty text, ordered paragraph spans, identity and versions.
- Embedding set: provider metadata and ordered entry IDs for external vector rows.
- Delivery manifest: payload integrity, counts, processing identities and set metadata.

## Success Criteria

### Measurable Outcomes

- **SC-001**: The 17-paper pilot package validates with 0 failures (319 sections,
  728 chunks); this is a target, not a result of this planning run.
- **SC-002**: Two `deliver` runs produce identical bytes for all six files and
  the committed delivery-manifest copy.
- **SC-003**: Synthetic corruption of each of the six file kinds is detected,
  including missing files and partial sets; independent failures are collected.
- **SC-004**: Schema/runtime structural parity holds for every shared good and
  mutated fixture, and the single schema passes CI's `check_schema`.
- **SC-005**: The reader helper loads 728 vectors of 1536 dimensions from the
  real package, with `vectors_by_chunk_id` verifying ownership through manifest
  entry IDs, independently of chunk-file order.
- **SC-006**: Newly committed files contain no article text, secrets or absolute
  paths; synthetic examples only. Existing article-bearing files are untouched.
- **SC-007**: Every F002/F003 handoff item has a reconciliation row in plan.md.
- **SC-008**: Person 2's PR review and Person 1's explicit human acceptance are
  recorded, together with feature-PR CI before squash merge.

## Assumptions, dependencies and exclusions

F001–F003 are DONE per EVIDENCE.md and this session. Local ignored artifacts
were inspected read-only; delivery itself is NOT RUN. Person 2 uses compatible
code/schema and matching committed reports; raw XML is
needed only for source tracing. Parser identity has no existing version constant;
source hashes are informational provenance only, not checkout compatibility
requirements. Person 1 approved R22 (with this restriction), R28 and R29 in
this session. Symlink-based tests use pytest skipif when symlinks cannot be
created. Archive commands await Person 1 verification; archive is not deterministic.

Out of scope: DB schemas/migrations/import implementation, retrieval, Golden v0
(PENDING, humans only), model changes/comparison, captions/tables/references as
chunks, corpus expansion/journal routing (F005), nested export, Parquet,
paragraph delivery, local e5 loading, SPDX normalization and closing P2-24.
