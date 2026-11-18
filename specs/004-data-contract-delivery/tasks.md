# Tasks: Data contract refresh and pilot delivery

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md).
**Status**: Approved for implementation by Person 1 on 2026-11-17 (R22, R28, R29, D5 amendment and abstract exclusion included)
**Owner**: Person 1; Person 2 reviews the shared contract PR.

Seven tasks split the former T004 into structure/file checks and cross-record
semantics as requested. Setup is the approval/research gate, not an eighth
task. Each code task T001–T006 begins only after explicit
spec/plan approval, renewed solution-research and google-python-engineering.
Write labeled synthetic offline behavior tests FIRST; observe meaningful RED
before implementing only that task, then GREEN. No real article text, network,
key or paid AI calls. All test modules named tests/delivery/test_deliver_*.py,
unique across tests; shared fixtures are neighboring delivery_fixtures.py,
never imports from tests. No checkbox completes without automated AND human
verification; interim RED/GREEN evidence is not completion.

## Phase 1: Setup gate

Person 1 APPROVED R22 (informational-only source hashes), R28 and R29 in this
session; D5 ID mapping is already approved and abstract exclusion is CLOSED.
These decisions authorize planning revisions only; implementation remains
stopped until explicit spec/plan implementation approval. No
dependency installation, runtime dependency or lockfile change is planned.

## Phase 2: Contract foundation

**Independent check**: One valid schema compiles and synthetic records exercise
the real flat shapes, including nullable and Unicode boundaries.

- [x] T001 Person 1 — Contract v0.3 and synthetic fixtures: first add labeled RED cases in `tests/delivery/test_deliver_contract.py` and `tests/delivery/delivery_fixtures.py`, then refresh `docs/DATA_CONTRACT.json` and implement shared stdlib record-structure checks in `src/sciscope/delivery/{__init__,contract}.py`. Root is delivery_manifest; local $defs/$ref covers paper, section, chunk, embedding_set and manifest children; additionalProperties false. Cover real field sets, nonempty author-object array/journal/surname, possibly empty given_names, ordered subjects, raw licenses/language with NO letter-case constraint, nonempty chunk text, legal zero-own-text sections, nullable parent/revision, exact locator v1 and DOI rules, dynamic dimensions and actual versions/provenance. Parser/taxonomy source_sha256 is informational only, shape 64 lowercase hex; embedding_set description contains only manifest-entry ID mapping. Establish shared good/mutated corpus for T004 parity; do not weaken constraints to fit fixtures. Depends on approval/research gate. Verify focused pytest, Draft202012Validator.check_schema, Ruff no-cache and mypy src. Covers FR-001/FR-002/FR-004/FR-005/FR-008, SC-004/SC-007.

## Phase 3: US1 — Reproduce a delivery (P1)

**Independent check**: Synthetic upstream artifacts yield a complete six-file
package, unchanged payload copies, stable manifest copies and repeat bytes.

- [x] T002 [US1] Person 1 — Paper builder: first RED in `tests/delivery/test_deliver_papers.py`, then implement `src/sciscope/delivery/papers.py` one-to-one normalized DOI join of F001 metadata/manifest. Keep D3 exact fields and raw values, verify license agreement, derive only integer publication_year from supported date precision, reject duplicates/missing counterparts/invalid year, exclude abstract/query_provenance/raw_xml_path/original_doi, sort by DOI. Do not modify source inputs. Depends on T001. Verify synthetic success and failure matrix, focused pytest, Ruff no-cache and mypy src. Covers FR-002, SC-001/SC-006.
- [x] T003 [US1] Person 1 — Package writer and deliver: first RED in `tests/delivery/test_deliver_package.py`, then implement `src/sciscope/delivery/package.py` and `src/sciscope/pipeline/cli.py` deliver wiring. Existing chunk/embedding validators must pass first on exact copied inputs. Build deterministic manifest with five payload descriptors, report hashes, informational parser/taxonomy source hashes, actual F003 version identifiers, embedding set and approved entry-ID mapping. Prefer a sibling temporary directory, validate there, then replace the whole six-file package directory; handle identical `data/pilot/delivery_manifest.json` in the same all-or-fail logic, retaining/restoring previous directory and copy on caught failure. Guard output/input/cache aliases and reject partial sets; add `data/delivery/` to `.gitignore`. Do not reorder/rewrite copied payloads or timestamp the new manifest. Test byte identity, two-run determinism, directory/copy replacement failures, unchanged upstream bytes and sanitized 0/1/2 exits. Symlink-based cases use pytest skipif when symlinks cannot be created. Staged validation initially uses existing validators/builder checks; T005 wires the full delivery validator after T004/T005 are built, avoiding a dependency cycle. Depends on T001–T002. Verify focused pytest, Ruff no-cache, mypy src and git diff --check. Covers FR-003–FR-006, SC-001/SC-002/SC-006.

## Phase 4: US2 — Verify a received package (P1)

**Independent check**: A synthetic valid package passes without source XML,
paragraphs/cache/key/network; independent corruptions are all reported safely.

- [x] T004 [US2] Person 1 — Structural validation, schema/runtime parity and file checks: first RED in `tests/delivery/test_deliver_structure.py` using shared good/mutated fixtures from T001; then extend `src/sciscope/delivery/contract.py` and add structural/file checks in `src/sciscope/delivery/validate.py`. Check exact record shapes, parser/taxonomy source_sha256 shape (64 lowercase hex), six-file inventory, payload/report hashes and byte sizes, physical record counts, manifest purity and rejection of partial-set markers. PARITY: same good/mutated manifest/paper/section/chunk/embedding_set structures accepted/rejected identically through local $ref jsonschema and stdlib checks, including language without case constraint, boolean/integral-number and Unicode regex boundaries. Reject malformed UTF-8/JSON, duplicate JSON keys, extra/missing files and trailing binary fragments where file metadata detects them; collect independent file/structure failures with safe IDs. Corrupt each of six file kinds. Symlink cases use pytest skipif when symlinks cannot be created. No cross-record semantics or CLI wiring in this task. Depends on T001/T003. Verify focused pytest, both full pytest entry points, check_schema, Ruff no-cache, format/mypy and diff checks. Covers FR-001/FR-004/FR-007/FR-008, SC-003/SC-004/SC-006.
- [x] T005 [US2] Person 1 — Cross-record semantics, F003 validation reuse and validate-delivery CLI: first RED in `tests/delivery/test_deliver_validate.py`, then extend `src/sciscope/delivery/validate.py`, wire `validate-delivery` in `src/sciscope/pipeline/cli.py` and full staged validation in `src/sciscope/delivery/package.py`. Check unique IDs, paper-section-chunk/parent foreign keys and cycles, DOI ownership, xml_sha256 and every locator digest via locator_digest plus full grammar, section paths/types/depth, contiguous ordinals, text/chunk hashes, span `end > start` for every span and agreement of requested/returned/set dimensions with the embedding manifest, report per-paper/aggregate count comparisons and real chunking_version/token_counter_id/template_version consistency. Parser/taxonomy source digests are informational: check internal consistency only, never compare local source files; regression case changes local parser/classifier bytes while a valid old package still passes. Reuse validate_embedding_structure/validate_embedding_set for input hashes, vector/count/dimension/finite/norm/report/calibration/complete-set semantics; do not reimplement. Combine T004 findings with all safely evaluable semantics, exact bounded diagnostics and 0/1/2 precedence, no prose/key/path leakage. Inject multiple independent semantic failures and verify staging refuses them. Depends on T004. Verify focused pytest, both full pytest entry points, Ruff no-cache, format/mypy and diff checks. Covers FR-004/FR-005/FR-006/FR-007/FR-008, SC-001/SC-003/SC-006.

## Phase 5: US3 — Read and trace the handoff (P2)

**Independent check**: Reader preserves raw Unicode separators and exact binary
shape; guide joins row ownership by manifest ID and describes local source trace.

- [x] T006 [US3] Person 1 — Reader and short guide: first RED in `tests/delivery/test_deliver_reader.py`, then implement stdlib `iter_jsonl`, `load_vectors` and `vectors_by_chunk_id(manifest_path, vectors_path, *, dimensions)` in `src/sciscope/delivery/reader.py`. The new helper returns chunk_id → vector tuple by embedding_manifest.entries order; reject duplicate IDs, row-count/dimension mismatches. Test LF-only JSONL (raw U+0085/U+2028/U+2029), malformed/blank input, little-endian matrix sizing/finiteness and nonmatching chunk/vector order. Write `docs/DELIVERY_GUIDE.md` (about two pages maximum), opening with the new helper example and stating vectors must NEVER be zipped with chunks.jsonl lines by position. Guide covers six files, compatible code/schema and matching reports (no local source-digest comparison), verify/archive hash and extracted-package check, reader APIs/ID join, same provider/model/dimensions/query_prefix, raw EN/en compared case-insensitively, DOI-to-local-XML rule, show/check-quote with Python-stdin code-point slicing, citation fields, no display of sentinel, omissions/report counts, abstract context/2 hard splits/O(n²) and inherited limits, PR process. Cite verified pgvector limits; no installed DB compatibility/import claim. Depends on T005. Verify focused pytest, both full pytest entry points, Ruff no-cache, format/mypy, doc links and diff checks. Covers FR-002/FR-005/FR-009, SC-005/SC-006/SC-007.

## Phase 6: Human verification and cross-cutting documentation

- [x] T007 Person 1 with Person 2 review — Manual verification, evidence and docs sync: execute `plan.md` PowerShell checks on the real pilot; require 17/319/728 and 0 failures, six-file two-run identity, identical committed manifest, unchanged copied-payload hashes, reader/mapping 728×1536, corruption/parity coverage and human abstract/body traces with negative control. Review new committed files for no article text/secrets/absolute paths; record symlink skips honestly. Person 1 verifies the planned `tar -a -c -f data/delivery/pilot-delivery.zip -C data/delivery pilot` command, records actual archive SHA256, extracts into a fresh temporary directory and runs `validate-delivery --package-dir <that directory>/pilot` BEFORE sending. Archive is not deterministic. Person 2 verifies the received extracted package and reviews PR. Rewrite `docs/DATA_MODEL.md` to real flat shapes, update `docs/DECISIONS.md` D-007 Proposed until Person 2 PR approval (D-004 stays Proposed), add `docs/CHUNKING_STRATEGY.md`/`docs/ARCHITECTURE.md` pointers, synchronize `PROJECT_TODO.md` (P2-20 only after human acceptance; P2-24 stays open) and task states. Append a correction line to the F001 `EVIDENCE.md` record: language in F001 metadata is 4 "EN" and 13 "en" (raw xml:lang), not "EN 17/17"; do not rewrite old text. Append exact RED/GREEN/check/human/review/CI observations; feature-PR CI result MUST be recorded on this branch BEFORE squash merge, never placeholders. Use NOT RUN/NOT VERIFIED/NOT RECORDED honestly. Depends on T001–T006 and explicit human outcome; rerun required quality checks after final edits. Covers FR-010 and SC-001–SC-008. Stop after F004; no F005/Golden work.

## Dependencies, coverage and implementation strategy

Approval → T001 → T002 → T003 → T004 → T005 → T006 → T007. No parallel markers:
shared CLI/schema/fixtures and staged validation dependencies favor serial small
scopes. Synthetic US2/US3 tests can use their own fixtures, independent of real
package availability; no parallel agent work is required. US1 producer MVP is
T001–T003, not a completed handoff; T004/T005 enable receiver validation,
T006 enables safe consumption. Full F004 includes all seven tasks and review.

| Requirement | Tasks |
| --- | --- |
| FR-001 | T001, T004, T007 |
| FR-002 | T001, T002, T006 |
| FR-003 | T003 |
| FR-004 | T001, T003, T004, T005 |
| FR-005 | T001, T003, T005, T006 |
| FR-006 | T003, T005 |
| FR-007 | T004, T005 |
| FR-008 | T001, T004, T005 |
| FR-009 | T006 |
| FR-010 | T007 |
| SC-001 | T003, T005, T007 |
| SC-002 | T003, T007 |
| SC-003 | T004, T005, T007 |
| SC-004 | T001, T004, T007 |
| SC-005 | T006, T007 |
| SC-006 | T001–T007 as applicable; T007 human review |
| SC-007 | T001, T006, T007 |
| SC-008 | T007 |
