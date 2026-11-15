# Tasks: JATS parser, sections, and locators

**Input**: `spec.md`, `plan.md`, `research.md` in this directory.  
**Owner**: Person 1. **State**: DONE 2026-11-15; automated and human verification recorded in EVIDENCE.md.
**Rule for T001-T007**: Invoke `$solution-research` before feature tests and
`$google-python-engineering` for Python work. Write labeled synthetic behavior
tests first, record RED for missing behavior, implement the smallest approved
scope, record GREEN, then run `uv run --locked ruff check . --no-cache` and
`uv run --locked mypy src`. Keep tests offline and free of real article prose.

## Phase 1: Foundational provenance and extraction

**Independent check**: In-memory synthetic XML yields stable positions and
paragraph text while malformed locators and skipped blocks remain visible.

- [x] T001 [US1] Person 1: Implement `SourceDocument.from_bytes`, `root`, lowercase `sha256`, a once-built parent map, `locator_for`, and `resolve` in `src/sciscope/jats/locator.py`; first add synthetic tests in `tests/jats/test_locator.py` for namespaced/local-name paths, same-name 1-based indices, digest binding, root path anchoring, abstract/section/paragraph round trips, root target rejection, identical locators from repeated builds, rejection of an element from another parse, malformed/uppercase digest, missing path, and wrong target; record RED/GREEN and quality checks. Depends on approved spec/plan. Covers FR-006, SC-002.
- [x] T002 [US1] Person 1: Implement paragraph text, per-paragraph sorted distinct `omitted` kinds, and per-paper occurrence counts by outer skipped kind in `src/sciscope/jats/parser.py`; first add synthetic tests in `tests/jats/test_parser.py` for mixed inline, xref markers, sub/sup, Unicode/whitespace, omission of `inline-formula`, `disp-formula`, `list`, `fig`, `table-wrap`, `supplementary-material`, `boxed-text`, and unlisted kinds, repeated outer occurrences counted individually without descendant counts, tails kept, complete `omitted` lists and `omitted=[]`, and empty text; record RED/GREEN and quality checks. Depends on T001. Covers FR-004.
- [x] T003 [US1] Person 1: Build body section recursion in `src/sciscope/jats/parser.py` using one `SourceDocument` for IDs, parents, depths, paths, locators, and direct-body implicit groups; first extend synthetic tests in `tests/jats/test_parser.py` for missing body, empty/untitled/deep sections, duplicate headings, and body paragraphs; record RED/GREEN and quality checks. Depends on T002. Covers FR-003, SC-001.
- [x] T004 [US1] Person 1: Add plain and structured abstract sections and paragraph ownership in `src/sciscope/jats/parser.py` using the same `SourceDocument`; first extend synthetic tests in `tests/jats/test_parser.py` for direct `<p>`, nested `<sec>`, absent `<p>`, abstract locators, aggregate `abstract_paragraph_count`, no empty warning for a structured abstract container with child sections, and an empty `<sec>` warning; record RED/GREEN and quality checks. Depends on T003. Covers FR-002, SC-001-SC-002.

## Phase 2: Classification and output

**Independent check**: Synthetic manifest files yield deterministic JSONL and
an error report while successful papers remain available.

- [x] T005 [US1] Person 1: Implement exact taxonomy tables and `ClassificationResult` with type and `explicit` flag in `src/sciscope/jats/classify.py`, plus unmatched headings, `type_conflicts`, skipped kinds, and back-container report data in `src/sciscope/jats/parser.py`; first add synthetic cases in `tests/jats/test_classify.py` and `tests/jats/test_parser.py` for heading precedence, heading numbering, nearest explicitly classified ancestor, inherited/default flag false, explicit `other` without inheritance, conflicting matches with heading winning, unknown headings, and back matter; record RED/GREEN and quality checks. Depends on T004. Covers FR-005, FR-009, SC-005.
- [x] T006 [US1] Person 1: Implement `parse` pipeline in `src/sciscope/jats/cli.py`, reading F001 manifest/metadata, validating confined raw paths and digests, applying the UTF-8-only XML safety gate, and atomically writing deterministic JSONL/report; add `data/processed/` to `.gitignore`. Choose a generous size cap from the largest of 17 measured XML files and carry both numbers to T008 evidence. First add labeled synthetic file-based tests in `tests/jats/test_jats_cli.py` following F001 conftest style for valid output, one-paper digest failure with continued processing/nonzero exit, missing files/body, accepted external DOCTYPE, rejected entity/internal subset/XInclude, rejected UTF-16 BOM/non-UTF-8 declaration, size cap, and byte-identical repeated runs; record RED/GREEN and quality checks. Depends on T005. Covers FR-001, FR-007, SC-001, SC-003-SC-004.

## Phase 3: Human passage helper and verification

**Independent check**: A synthetic passage can be displayed, located, and
checked case-sensitively with visible failures and correct Unicode output.

- [x] T007 [US2] Person 1: Implement read-only `show`, `check-quote`, and `verify-roundtrip` commands in `src/sciscope/jats/cli.py`; first extend `tests/jats/test_jats_cli.py` with synthetic file-based subprocess checks for outline, section/abstract text, `[omitted: <kinds>]` display for any nonempty skipped-kind list (including `fig` and an unlisted kind), section and abstract subtree search in document order, quote whitespace normalization/case sensitivity, no cross-paragraph match, digest/path/absence messages, all-manifest round-trip counts and nonzero mismatch exit, no file writes, and captured non-ASCII PowerShell-compatible UTF-8 output; record RED/GREEN and quality checks. Depends on T006. Covers FR-008, SC-002, SC-007.
- [x] T008 [US1] [US2] Person 1: Run the `plan.md` PowerShell command set on all 17 real files in the user's terminal; compare two-run SHA256 and full locator round trips; record the largest measured XML file and chosen size cap; review actual `other` headings under the approved mapping; self-select three papers for PLOS page outline/paragraph/skipped-kind spot checks; find and check a real quote plus altered quote; report observed results and explicit acceptance/rejection. Append automated and human evidence to `EVIDENCE.md` and sync F002 entries in `PROJECT_TODO.md` and these task states only after explicit acceptance. Depends on T001-T007 and approved spec/plan. Covers SC-001-SC-007. Leave unchecked until evidence exists.

## Dependencies and execution

T001 -> T002 -> T003 -> T004 -> T005 -> T006 -> T007 -> T008. No parallel
marker: every task depends on the prior deliverable. F002 ends after T008;
F003/F004 and golden question writing are separate future work.

**Implementation grouping**: Group A = T001-T004; Group B = T005-T006;
Group C = T007; T008 is human verification.
