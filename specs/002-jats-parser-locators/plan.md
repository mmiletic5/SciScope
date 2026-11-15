# Implementation Plan: JATS parser, sections, and locators

**Branch**: `002-jats-parser-locators` | **Date**: 2026-11-15 | **Spec**: `specs/002-jats-parser-locators/spec.md` | **Owner**: Person 1

Post-design gate: Approved 2026-11-15 by Person 1 (spec, plan, taxonomy mapping table).

## Summary and technical context

Python 3.12, standard library `ElementTree`, `hashlib`, `json`, and `argparse`;
offline pytest, Ruff, and strict mypy. Source: F001 manifest and raw JATS;
title/DOI joined from F001 metadata. Outputs: two regenerable JSONL files and
one committed small report. No network, AI, new dependency, or shared-contract
finalization. Implementation may begin with Group A under this approved design.

## Constitution check and project structure

Research preceded the approved design. Each
code task starts with labeled synthetic behavior tests and a recorded RED run,
then GREEN, `ruff check . --no-cache`, and `mypy src`. T008 is human acceptance
and evidence; no checkbox is complete now. F004 contract reconciliation needs
Person 1 and Person 2 review before shared integration.

| Planned module | Boundary and public signature |
| --- | --- |
| `src/sciscope/jats/locator.py` | `SourceDocument.from_bytes(xml_bytes: bytes) -> SourceDocument` parses once after the safety gate. The instance exposes `root: ET.Element`, lowercase `sha256: str`, and a parent map built once; `locator_for(element: ET.Element) -> str` and `resolve(locator: str) -> ET.Element` use that tree. Reject an element from another parse. Preserve four distinct locator errors. |
| `src/sciscope/jats/parser.py` | `parse_paper(document: SourceDocument, doi: str, title: str) -> ParseResult`; `paragraph_text(element: ET.Element) -> tuple[str, Counter[str]]`. Owns hierarchy, abstract, text, omitted kinds, warnings, and stable record order; all locators come from the passed document. |
| `src/sciscope/jats/classify.py` | `classify_section(sec_type: str, heading: str, nearest_explicit_ancestor_type: str | None) -> ClassificationResult`, with `normalized_type: str` and `explicit: bool`. |
| `src/sciscope/jats/cli.py` | `main(argv: list[str] | None = None) -> int`; `parse`, `show`, `check-quote`, `verify-roundtrip`. File validation, output, and UTF-8 console handling. |
| `tests/jats/` | Labeled synthetic XML bytes and F001-style temporary CLI fixtures; no real paper prose or live calls. |

`parse_article` in `plos_pilot/metadata.py` returns a root but re-extracts and
requires front matter. Prefer a shared safe XML loader only if its behavior can
be reused without modifying F001 or weakening checks. F002 can use
`ET.fromstring` after a byte-level safety gate: reject UTF-16 BOMs and any
non-UTF-8 XML encoding declaration before an ASCII-compatible scan; accept
external DOCTYPE declarations (17 observed), reject `<!ENTITY`, internal DTD
subsets, and XInclude, cap input size, and surface parse failures per paper.
Choose a generous multiple of the largest measured pilot file during T006;
record both the measured maximum and chosen cap in T008 evidence.
Path resolution checks `Path.resolve().is_relative_to(repo_root.resolve())`
as F001 does. No DTD or XInclude resource is fetched.

## Locator and section algorithm

`SourceDocument.from_bytes` hashes the exact source bytes with SHA256 lowercase
hex, parses once after the safety gate, and builds a parent map once. Its
`locator_for` requires an element belonging to that tree, starting `/article[1]`;
every subsequent component uses the
local element name and 1-based position among siblings of that *same* local
name. Example: the third `<p>` child of the second `<sec>` child of `<body>` is
`jats:v1:<64-lowercase-hex>:/article[1]/body[1]/sec[2]/p[3]`.
Sibling indices do not depend on `id` or heading text. Repeated `locator_for`
calls for the same element yield identical locators. `resolve` parses locator
grammar strictly (version, lowercase 64-hex digest, root component, positive
indices); compares digest before traversal; and resolves by local name and
same-name index, then accept `<sec>`, `<p>`, or `<abstract>` as the root
abstract section container. A valid path to `<title>` or `<fig>` raises the
distinct target-type error. Future table/figure targets require a deliberate
extension of permitted target types, with v1 path grammar unchanged; any
grammar/meaning change is v2. An uppercase digest is malformed even when its
hex value matches; a changed lowercase digest is a mismatch.

Body `<sec>` IDs use `<normalized_doi>#sec-2.1` for second top-level section,
first nested section. Preserve preorder. Parent is the nearest `<sec>` ID.
Depth is 1 for top-level body `<sec>`. Direct body `<p>` runs before/between/after
sections form one implicit section per contiguous run, ID
`<doi>#body-p-<first-p-sibling-index>`, depth 1, empty original heading,
`(untitled)` path, and first paragraph locator as the grouping's source
anchor. A real untitled `<sec>` keeps its positional ID and own locator.
Abstract container ID is `<doi>#abstract`, depth 1, type `abstract`; its
nested `<sec>` IDs append `.1`, `.2`, etc., depth increments, and type stays
`abstract`. Plain abstract section locator addresses `<abstract>`; structured
abstract child sections address `<sec>`. The root abstract heading is `""`,
with `(untitled)` in path; child titles preserve displayed text. Paragraphs
under each section belong only to that section, not descendants. A `<sec>` with
neither direct paragraphs nor child sections is retained and warned as empty;
a structured abstract container with child sections and no direct `<p>` gets
no empty-section warning. Each paragraph retains its
1-based index within its owning section. `original_heading` is the verbatim
concatenation of `<title>` text nodes in document order (including inline
markup text), with no whitespace or Unicode normalization; `section_path`
uses those same strings or `(untitled)` where blank. Classification alone
normalizes a copy. Duplicate headings never affect IDs.

## Element-kind rule table

Apply rules to `<p>` child traversal, preserving `child.tail` after a skipped
element. Count each occurrence of an outer skipped subtree once under its
element kind; do not count its descendants separately. The same rule covers
abstract and body paragraphs.

| Element kinds observed in `<p>` survey | Rule |
| --- | --- |
| `p` itself | Own paragraph only when owned directly by a section or abstract; nested `<p>` inside a skipped block is skipped and counted via its outer block. |
| `italic`, `bold`, `xref`, `ext-link`, `named-content`, `email` | Included inline recursively; `xref` marker text retained. |
| `sub`, `sup` | Included inline recursively with no inserted spacing. |
| `inline-formula`, `disp-formula`, `list` | Omit the entire element from paragraph text; count every outer occurrence under its kind. Do not count descendants separately. Observed descendants such as `alternatives`, `graphic`, `label`, MathML nodes, `list-item`, and nested `p` are covered by the outer omission. Keep the omitted element's `.tail`. |
| `fig`, `table-wrap`, `supplementary-material`, `boxed-text` | Omit and count every outer occurrence if found inside `<p>`; no figure/table unit in F002. Keep its `.tail`. |
| Any unlisted child kind | Omit and count every outer occurrence by local name, with a warning for review; keep its `.tail`. |

For included nodes, concatenate `.text`, included descendants, and `.tail`
without synthetic spaces; then use `" ".join(text.split())`. This collapses
NBSP and other whitespace but does not normalize Unicode or case. Every
paragraph record has `omitted`: every element kind skipped inside that
paragraph (`inline-formula`, `disp-formula`, `list`, `fig`, `table-wrap`,
`supplementary-material`, `boxed-text`, and any unlisted kind), sorted and
distinct, or `[]` when none. The report separately counts each omitted outer
element occurrence by kind per paper. Empty text stays an empty paragraph
record. Skipped element counts also include block
children encountered directly under body/section/abstract that do not produce
paragraphs; nested `<sec>` and `<title>` are structural, not skipped. Report
counts per kind per paper so omitted content is visible.

## Taxonomy mapping

Person 1 approved this mapping table on 2026-11-15; review of the actual
`other` headings after parsing remains part of SC-005 and T008.

Normalize heading by lowercase, strip leading section number/punctuation,
strip remaining surrounding punctuation, collapse whitespace. Match exact
strings only. `sec-type` is trimmed/lowercased but otherwise matched exactly.

| Source | Exact value(s) | Type |
| --- | --- | --- |
| `sec-type` | `intro`, `introduction` | `introduction` |
| `sec-type` | `materials|methods`, `methods` | `methods` |
| `sec-type` | `results` | `results` |
| `sec-type` | `discussion` | `discussion` |
| `sec-type` | `conclusions` | `conclusions` |
| `sec-type` | `supplementary-material` | `other` |
| heading | `introduction` | `introduction` |
| heading | `material and methods`, `materials and methods`, `methods and materials`, `methods` | `methods` |
| heading | `results` | `results` |
| heading | `results and discussion` | `results_discussion` |
| heading | `discussion` | `discussion` |
| heading | `conclusions` | `conclusions` |
| heading | `supporting information` | `other` |

Abstract always classifies `abstract`. `classify_section` returns the type and
`explicit=True` only when a `sec-type` or heading table entry matched; inherited
or default `other` returns `explicit=False`. For an unmapped section, inherit
only the nearest explicitly classified ancestor's type; otherwise use `other`.
An explicit `other` (`supplementary-material`, supporting information) does not
inherit. If both tables match with different types, `sec-type` wins and the
section is recorded in `type_conflicts` with `section_id`, `sec_type`, and
`heading`. Record each unmatched original heading with DOI and count even if
it inherits; do not label explicit `other` as unmatched.
The actual `other` list is reviewed after T006 by Person 1.

## Output records and integration

`sections.jsonl` fields, in key order: `doi`, `title`, `xml_sha256`,
`section_id`, `parent_section_id`, `section_path`, `original_heading`,
`normalized_type`, `source_locator`, `depth`, `paragraph_count`.
`paragraphs.jsonl`: `doi`, `section_id`, `paragraph_index`, `text`, `omitted`,
`source_locator`. `parse_report.json`: `papers` array of `doi`, `xml_sha256`,
`section_count`, `paragraph_count`, `abstract_paragraph_count`,
`normalized_type_histogram`, `unclassified_headings`,
`type_conflicts`, `skipped_element_kinds`, `back_matter_containers`, `warnings`,
`errors`; plus
`summary` of succeeded/failed counts. Sort papers by DOI; section and paragraph
arrays follow XML preorder within DOI. JSON uses stable insertion key order,
`ensure_ascii=False`, UTF-8, and LF newline (including final newline).
`skipped_element_kinds` is a per-paper mapping from local element kind to the
number of outer omitted/skipped element occurrences; descendants of an omitted
element are not counted separately. The paragraph `omitted` list is distinct
per paragraph and does not replace these occurrence counts.
Write temporary output files and replace only after a complete run; failed
papers remain in report but do not emit partial records. Exit nonzero if any
paper fails. `data/processed/` is added to `.gitignore` in T006.
`abstract_paragraph_count` includes paragraphs directly under the abstract
container and paragraphs in all nested abstract sections.

F004 must reconcile the draft `docs/DATA_CONTRACT.json`: it nests sections
under paper and requires `chunks`, while F002 uses flat section/paragraph
JSONL; it has no paragraph entity or depth/count fields; its `section_path`
disallows empty items, hence `(untitled)` is synthetic; `parent_section_id`
permits null; its locator is only a nonempty string and must gain v1 validation;
its chunk text requires nonempty text whereas F002 can retain empty paragraphs;
its paper metadata/processing versions and chunk fields are outside F002.
`evals/golden_questions.schema.json` describes source locators but does not
enforce v1; Golden v0 remains human authored. Person 2 joins F004 review.

## Errors, helper, risks, and tests

Input errors (missing/escaping file, wrong digest, invalid XML, absent body,
missing metadata DOI) are per-paper report errors. A missing body produces a
failed paper. Missing/paragraph-free abstract is reported rather than
inventing text. Locator errors are malformed, digest mismatch, path absent,
and wrong target kind; quote absence is separate. CLI reports stable, concise
diagnostics without source prose in logs. `show` reads manifest/XML and may
parse in memory; no write. It prints `[omitted: <kinds>]` after any paragraph
with a nonempty `omitted` list (sorted kinds). `check-quote` identifies the
matching manifest digest, resolves against source bytes, and collapses quote
whitespace by the same rule as paragraph text. A match is case-sensitive and
must be wholly within one paragraph; it never spans paragraphs. A section
locator searches that section's own paragraphs and nested sections' paragraphs
in document order; an abstract locator likewise searches the full abstract
subtree. A paragraph locator checks only its paragraph. `--abstract` prints
all nested structured-abstract paragraphs. `verify-roundtrip` reads every
manifest paper, resolves each emitted section and paragraph locator, compares
stored headings and text with extraction from the resolved element, prints
checked counts, and exits nonzero on any mismatch. For an implicit grouping,
its paragraph anchor is checked against the first paragraph; its empty heading
is synthetic. Non-ASCII stdout: call `sys.stdout.reconfigure(
encoding="utf-8", errors="backslashreplace")` where available; write UTF-8
when piped in PowerShell and verify captured Unicode with subprocess tests.
`sys.stderr` gets the same configuration. Quote input remains Python Unicode.

Risks: all 17 have DOCTYPE; a blanket DOCTYPE rejection would fail. Entity
expansion remains a concern even with `ET`, hence reject internal entities and
bound bytes. Nested formula/math and lists may contain meaningful text; they
are counted and deferred, never silently inserted. Pilot has no direct body
paragraphs or untitled sections, so synthetic tests carry those cases. Parser
output is not the F004 contract. Real PLOS page display may differ from XML;
human checks must record discrepancies, not alter source text automatically.

Tests after approval: synthetic byte fixtures for locator grammar/round trips,
mixed inline and skipped blocks, abstract variants, deep/untitled/implicit
sections, inheritance and unmatched reporting, digest mismatch isolation,
deterministic files, and CLI quote/Unicode errors. Manual verification covers
all 17, including stored heading/text round trips and two-run SHA256.

## One PowerShell command set for manual verification (user terminal, after implementation)

```powershell
$env:PYTHONPATH = 'src'
uv run --locked python -m pytest tests/jats -q
uv run --locked python -m sciscope.jats.cli parse
$first = Get-FileHash data/processed/pilot/sections.jsonl,data/processed/pilot/paragraphs.jsonl,data/pilot/parse_report.json -Algorithm SHA256
uv run --locked python -m sciscope.jats.cli parse
$second = Get-FileHash data/processed/pilot/sections.jsonl,data/processed/pilot/paragraphs.jsonl,data/pilot/parse_report.json -Algorithm SHA256
Compare-Object $first.Hash $second.Hash
uv run --locked python -m sciscope.jats.cli show '10.1371/journal.pone.0037017'
# Person 1 chooses three papers, reviews their outlines/counts/skipped kinds
# against PLOS pages, then substitutes a real section ID and copied locator.
uv run --locked python -m sciscope.jats.cli show '10.1371/journal.pone.0037017' --section '<section_id>'
uv run --locked python -m sciscope.jats.cli show '10.1371/journal.pone.0037017' --abstract
uv run --locked python -m sciscope.jats.cli check-quote --locator '<locator>' --quote '<verbatim quote>'
uv run --locked python -m sciscope.jats.cli check-quote --locator '<locator>' --quote '<altered quote>'
uv run --locked python -m sciscope.jats.cli verify-roundtrip
uv run --locked ruff check . --no-cache
uv run --locked mypy src
git check-ignore data/processed/pilot/sections.jsonl
git status --short
```

Expected: empty `Compare-Object` output; the first quote succeeds, altered
quote fails; `verify-roundtrip` checks every emitted section/paragraph on all
17 files; Person 1 reports observed results and explicit acceptance/rejection.
Only after that, append `EVIDENCE.md` and synchronize task/backlog checkboxes.

## Objections

D3 says non-section/paragraph targets fail, while D5 requires an abstract
section locator. This plan treats the `<abstract>` container as the one
section-like target exception; all other non-`sec`/`p` targets fail. The v1
path grammar is unchanged. FR-008 includes the read-only `verify-roundtrip`
command used for SC-002; T007 implements it.
