# Feature Specification: JATS parser, sections, and locators

**Feature Branch**: `002-jats-parser-locators`  
**Created**: 2026-11-15  
**Status**: Approved 2026-11-15 by Person 1 (spec and plan)  
**Input**: F002 planning request, decisions D1-D10, and 17-file read-only survey.

## Problem and scope

Person 1 needs source-faithful sections and paragraphs from the preserved PLOS
ONE XML so a human can inspect evidence for Golden v0 and later F003 chunking.
F001 already supplies raw bytes, manifest digests, and front-matter metadata.
F002 produces section/paragraph records, a compact parse report, and a
read-only passage helper. Owner: Person 1; backlog P2-06 through P2-10.

## User Scenarios & Testing

### User Story 1 - Extract traceable passages (Priority: P1)

Person 1 parses the 17-paper pilot and can trace each extracted section and
paragraph to the exact XML bytes.

**Independent test**: Synthetic JATS verifies hierarchy, text, classification,
digest checks, and locator round trips without real article text in the repo.

1. **Given** a manifest entry with matching bytes, **when** parsing runs,
   **then** abstract and nested body sections and their paragraphs are emitted
   in document order, with stable IDs and locators.
2. **Given** a malformed or mismatched paper, **when** parsing runs, **then**
   its error is visible, other papers continue, and the command exits nonzero.

### User Story 2 - Inspect a real source passage (Priority: P2)

Person 1 prints a paper outline or a section's paragraphs, then checks that a
short quote occurs at a copied locator.

**Independent test**: Synthetic files exercise the helper commands, including
non-ASCII PowerShell output, successful matches, and distinct failures.

1. **Given** a DOI, **when** `show` runs, **then** it prints section IDs,
   headings, normalized types, and paragraph counts; a selected section or
   `--abstract` prints indexed paragraph text and full locators, with an
   `[omitted: <kinds>]` marker for paragraphs with omitted elements.
2. **Given** a paragraph or section locator, **when** `check-quote` runs,
   **then** a case-sensitive, whitespace-collapsed exact substring within one
   paragraph succeeds and reports its locator; an absent quote fails visibly.

### Edge Cases and failures

No `<body>`; empty or untitled `<sec>`; depth greater than the observed three;
paragraphs directly under body; `<p>` with only block children; abstract with
no `<p>`; duplicate headings; XML DOCTYPE/entity input; non-text locator;
path case differences; valid digest prefix with altered digest case; missing
source file; inconsistent metadata DOI; and non-ASCII console text. Errors
remain per paper where possible. The report records omissions and warnings.

## Requirements

### Functional requirements

- **FR-001**: Parse only manifest-listed PLOS ONE source bytes whose SHA256
  equals `xml_sha256`; join metadata by normalized DOI for DOI and title only.
  A failed paper MUST NOT stop processing other entries and MUST cause a
  nonzero command exit.
- **FR-002**: Extract the primary abstract as one section, with nested abstract
  sections when present, and its paragraph locators. Count abstract paragraphs
  across the container and all nested abstract sections. A container with
  nested sections and no direct paragraph is not warned as empty; warn for a
  `<sec>` with neither paragraphs nor child sections. Report a missing or
  paragraph-free abstract per paper.
- **FR-003**: Recurse all body `<sec>` nodes. Each section MUST have deterministic
  `section_id`, `parent_section_id`, heading path, original heading (empty if
  missing), normalized type, source locator, and depth. Direct body paragraphs
  MUST belong to an implicit untitled section; untitled paths use `(untitled)`.
- **FR-004**: Paragraph text MUST follow document order, collapse whitespace
  runs to one space and trim ends, without Unicode or case normalization.
  Inline text including citation markers is retained; `sub` and `sup` do not
  gain spaces. `inline-formula`, `disp-formula`, `list`, `fig`, `table-wrap`,
  `supplementary-material`, `boxed-text`, and any unlisted child kind are
  omitted in full; text following each omitted element is kept. The per-paper
  `skipped_element_kinds` report MUST count the number of occurrences of each
  outer omitted/skipped element kind; descendants inside an omitted element
  MUST NOT be counted separately. Each paragraph record MUST include `omitted`,
  every kind skipped inside that paragraph as a sorted distinct list, or `[]`
  when none. Empty resulting paragraphs remain locatable and generate a warning.
- **FR-005**: Classify by exact `sec-type` mapping first, then normalized
  heading mapping, then nearest explicitly classified ancestor, else `other`.
  Classification returns a type and an `explicit` flag, true only for a table
  match; explicit `other` does not inherit. When both tables match different
  types, `sec-type` wins and the report records `type_conflicts` with section
  ID, `sec-type`, and heading. The eight
  v0 types are `abstract`, `introduction`, `methods`, `results`,
  `results_discussion`, `discussion`, `conclusions`, `other`. Report unmatched
  headings with DOI and count; Person 1 reviews the mapping and `other` list.
- **FR-006**: Build and resolve `jats:v1:<xml_sha256>:<path>` locators using
  absolute local-name paths and 1-based same-name sibling indices. Resolution
  MUST distinguish malformed locator, digest mismatch, path not found, and
  non-section/paragraph target. The format is immutable within v1.
- **FR-007**: `parse` MUST write sections and paragraphs as UTF-8 JSONL under
  `data/processed/pilot/`, and a small committed per-paper report at
  `data/pilot/parse_report.json`. Records sort by DOI then document order;
  keys, newline style, and repeated output bytes are stable. Generated
  processed data is gitignored.
- **FR-008**: The read-only helper MUST support `show <doi>`, optional
  `--section <section_id>` or `--abstract`, and `check-quote --locator <L>
  --quote <text>` with digest, path, and quote-absence messages. `show` MUST
  print `[omitted: <kinds>]` after paragraphs with nonempty `omitted` lists.
  `check-quote` MUST collapse quote whitespace by the paragraph rule, match
  case-sensitively within one paragraph, and search a section's own and nested
  paragraphs in document order (likewise for an abstract locator). The helper
  MUST also support `verify-roundtrip`: for every manifest paper, resolve every
  emitted section and paragraph locator, compare stored heading/text to the
  resolved element (using the documented anchor for synthetic groups), print
  counts, and exit nonzero on any mismatch. It MUST make no network or AI
  calls and write no files.
- **FR-009**: Back containers `ack`, `ref-list`, `app`, `notes`, `fn-group`,
  `glossary` MUST be listed when present and not emitted as text units.

### Non-functional requirements and exclusions

Use Python 3.12 standard library XML parsing and no new runtime dependency.
Keep tests offline with labeled synthetic JATS only. Do not re-extract front
matter. Out of scope: chunking, tokenization, embeddings, table/figure-caption
units, reference-list parsing (P2-12 through P2-14 and F003), data-contract
finalization (F004), golden questions or answers (human authored only; helper
never generates either), corpus expansion, and journals other than PLOS ONE.

### Key entities

**Section**: a body `<sec>`, abstract container/child `<sec>`, or synthetic
body paragraph grouping, with hierarchy and source position. **Paragraph**:
one `<p>` element and exact normalized text. **Locator**: version, source
digest, and absolute position. **Parse report**: per-paper counts, taxonomy
gaps, skipped kinds, back containers, errors, and warnings.

## Success Criteria

- **SC-001**: All 17 manifest papers parse; each yields at least one abstract
  paragraph and one body section with paragraphs, or the exception is reported
  for that paper.
- **SC-002**: For every section and paragraph of all 17 papers,
  `verify-roundtrip` resolves its locator and reproduces stored heading/text
  exactly; for synthetic grouping, it verifies the documented first-paragraph
  anchor and synthetic empty heading. The command reports counts and exits
  nonzero on any mismatch.
- **SC-003**: Two consecutive `parse` runs yield identical SHA256 digests for
  `sections.jsonl`, `paragraphs.jsonl`, and `parse_report.json`.
- **SC-004**: Given one synthetic file with a wrong manifest digest, parsing
  visibly fails that paper only and returns nonzero.
- **SC-005**: Person 1 has approved the plan's taxonomy mapping table; after
  parsing, Person 1 reviews actual `other` headings and explicitly accepts or
  rejects that result.
- **SC-006**: Person 1 compares outline, paragraph counts, and skipped-kind
  counts for three self-chosen papers against the PLOS article page.
- **SC-007**: Person 1 finds a real paragraph with `show`, copies its locator,
  and observes `check-quote` pass for a verbatim quote and fail for an altered
  quote.

## Assumptions

The 17 manifest entries and F001 metadata are the pilot input; the raw XML is
untracked. The draft shared contract is an F004 input, not an approved F002
output schema. No scientific conclusions are inferred from parser output.
