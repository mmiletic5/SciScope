# Implementation Plan: Data contract refresh and pilot delivery

**Branch**: `004-data-contract-delivery` | **Date**: 2026-11-17 | **Spec**: [spec.md](spec.md)
**Owner**: Person 1; shared-contract reviewer: Person 2.
**Status**: Draft; implementation approval NOT RECORDED.

## Summary and technical context

Deliver the real flat F001–F003 pilot using Python 3.12 and stdlib runtime;
existing dev pytest/jsonschema/Ruff/mypy. No dependency or lockfile change.
Windows PowerShell 5.1 and CI Linux; 17 papers, 319 sections, 585 source
paragraphs, 728 chunks/vectors; 1536 dimensions in this pilot, not a contract
constant. Vector bytes: 4,472,832. Read-only inspection confirmed finiteness
and norms 0.999368748–1.000662474; this is not F004 package validation.
See [research.md](research.md) for sources and evidence distinctions.

## Constitution check and workflow

Research → specification → plan → tasks → read-only analysis → explicit
approval → synthetic offline RED/GREEN → automated checks → human acceptance
→ evidence/review/CI. Person 1 owns new modules; Person 2 reviews contracts.
No paid calls, real article prose in fixtures, or implied acceptance.
Before future tests renew `solution-research`; Python work applies
`google-python-engineering`. Pre/post-design constitution gate: PASS for
planning. Implementation gate CLOSED until spec/plan approval.

Follow the four-file structure of F001–F003: consolidate design, interfaces
and verification here. User's run restrictions override skill defaults for
checklists, auxiliary design files and existing-doc updates. No source/tests
or existing docs/data/evidence/backlog changes in this run. Spec Kit template
resolution and setup use process-local `SPECIFY_FEATURE_DIRECTORY` and
`SPECIFY_FEATURE_NO_PERSIST=1`; `.specify/feature.json` stays unchanged.
No `.specify/extensions.yml` exists; no hooks are registered.

## Implementation clarifications

D1–D10 below preserve the supplied decisions, with the requested inline
supersession marker on D5; subsequent session amendments follow them.

- **D1 Principle.** The contract describes the real flat F001–F003 shapes. No nested Paper→Section→Chunk JSON, no field renames, no re-serialization of existing files. The only new record file is `papers.jsonl` (join of F001 `metadata.jsonl` and `manifest.jsonl` by DOI). Every other proposed deviation needs a row in a reconciliation table (source field → delivered field, reason) and defaults to NOT done.
- **D2 Package.** Directory `data/delivery/pilot/` (add `data/delivery/` to `.gitignore`) containing:
  - `papers.jsonl` (new)
  - `sections.jsonl` (byte-identical copy of F002 output)
  - `chunks.jsonl` (byte-identical F003 output)
  - `vectors.f32` (byte-identical)
  - `embedding_manifest.json` (byte-identical copy of F003 `manifest.json`)
  - `delivery_manifest.json`

  A byte-identical copy of `delivery_manifest.json` is committed as `data/pilot/delivery_manifest.json` (no prose, no absolute paths, no timestamps). Delivery to Person 2 is an out-of-band archive: Person 1 zips it with PowerShell and records the archive SHA256 in EVIDENCE. The archive itself is not claimed to be deterministic. Person 2 verifies it with `validate-delivery`. No article text and no large file is committed.
- **D3 `papers.jsonl` fields.**
  - Keep from F001: doi, title, authors (`{surname, given_names}`), journal, publication_date, article_type, subjects (order preserved, including the leading "Research Article"), license (raw text, no SPDX normalization, no license-version inference), language (raw "EN"), source_url, retrieved_at, xml_sha256.
  - Derived: `publication_year` (int, from publication_date). It is the only derived field.
  - Excluded: abstract text (abstract chunks and sections carry it; list it as an open question with a recommendation), `query_provenance`, `raw_xml_path`. Document the rule for resolving the local XML from the DOI instead.
- **D4 Reality over the draft.**
  - Taxonomy v0 enum (abstract, introduction, methods, results, results_discussion, discussion, conclusions, other), the locator v1 grammar and its digest rule, and the DOI normalization rule from F001 go into the contract exactly as implemented. Read them from the code.
  - The `(untitled)` sentinel stays unchanged in `section_path`. It is documented as "no heading, never display it".
  - Sections without their own paragraphs are legal; chunk `text` is nonempty.
  - Paragraphs are NOT delivered. Chunk `spans` carry locator and offsets.
  - Document `depth` and `paragraph_count` exactly as F002 emits them. Recompute only to detect inconsistency, and report it if found.
- **D5 Embedding set.** Provider-agnostic block: provider, model, dimensions (not fixed 384), dtype float32 little-endian, row i ↔ line i of `chunks.jsonl` [SUPERSEDED: row/line clause, see session amendment], passage_prefix, query_prefix, observed norm min/max and tolerance, `chunks_sha256`, `vectors_sha256`. `embedding_model_revision` is nullable ("not applicable" for the OpenAI API; never invent a revision). D-004 stays Proposed. State plainly that queries must use the same provider, model, dimensions and query_prefix.
- **D6 Versioning.**
  - Contract `schema_version` is "0.3.0", status draft until the Person 2 PR approval.
  - `delivery_manifest.json` carries: contract_version; counts (papers, sections, chunks); per-file sha256, bytes and record count; processing versions (find the real identifiers in code: parser/taxonomy/locator, `chunking_version`, `token_counter_id`, `template_version`); and the embedding_set block.
  - No timestamps. Two runs must be byte-identical.
- **D7 Schema.** `docs/DATA_CONTRACT.json` stays ONE valid Draft 2020-12 file, because CI runs `check_schema` on it. The root describes `delivery_manifest`. Record types live under `$defs` (paper, section, chunk, embedding_set) and are validated through `$ref`. No new runtime dependency: the runtime validator is stdlib only. Tests use the dev `jsonschema` and include PARITY tests (the same good and mutated records must be accepted or rejected identically by the schema and by the validator). Evaluate `jsonschema` as a runtime dependency in research.md; the recommended default is no.
- **D8 Commands.** Both are subcommands of `src/sciscope/pipeline/cli.py`; exit codes are 0 / 1 / 2 as in F003; they run offline with no key and no network.
  - `deliver`:
    - runs the existing chunk and embedding validators first and refuses on failure;
    - writes atomically and deterministically;
    - uses F003-style error codes (`output-path-conflict` and similar).
  - `validate-delivery` collects all findings and prints `error: <code> count: <k> first: <ids>` plus `failures: <n>`. It checks:
    - file digests against the manifest;
    - record structure and unique IDs;
    - paper↔section↔chunk foreign keys;
    - `xml_sha256` consistency across paper, sections, chunks and locator digest (use `locator_digest()`);
    - `chunk.section_path == section.section_path`;
    - version consistency;
    - vector row count, dimensions, finiteness and norms (reuse F003 `validate` logic, do not reimplement);
    - counts against parse_report, chunk_report and embedding_report;
    - manifest purity (no prose, no paths, no secrets);
    - rejection of partial sets.
- **D9 Guide.** `docs/DELIVERY_GUIDE.md`, at most about two pages, covering:
  - package contents;
  - how to verify;
  - how to read the files: split JSONL ONLY on `"\n"`, never `splitlines()`; vectors are a float32 little-endian matrix; a tested stdlib helper `src/sciscope/delivery/reader.py` (`iter_jsonl`, `load_vectors`);
  - the query-embedding rule from D5;
  - how to resolve locators (`jats` `show` and `check-quote` need the raw XML locally);
  - fields for citation display (doi, title, authors, year, journal, section heading and path, locator, license);
  - known limits from F003 and the Handoff notes (omitted captions/tables/references are counted in the report; abstract chunks have no heading context; 2 hard splits; O(n²) validators);
  - the change process (PR with Person 2 as reviewer).

  A "Notes for Person 2" section may mention pgvector limits (vector dimension limit and index dimension limit) ONLY after you verify them in the official pgvector documentation. Cite the URL, and mark it UNVERIFIED if you cannot verify it.
- **D10 Out of scope.** DB schema or migrations, retrieval, Golden v0 (PENDING, humans only), a new embedding model, caption/table chunks, corpus expansion and journal routing (F005), nested JSON export, Parquet, delivering paragraphs, local e5 loading, SPDX license normalization. Do not close P2-24 (Person 1 decides after F004).

### Session amendment and interpretation

**D5 amendment — APPROVED in this session:** Person 1 answered "Use manifest
ID mapping (Recommended)" after 727/728 positional mismatches were reported.
Vector row `i` maps through `embedding_manifest.entries[i].chunk_id` to a
chunk by ID. Never zip vectors with chunk-file lines. Both files remain
byte-identical. This supersedes only D5's row/line clause.

D3's raw language rule preserves actual `EN` (4 papers) and `en` (13); its
example does not authorize uppercasing. Schema imposes no language letter-case
constraint; guide comparisons are case-insensitive. T007 appends the F001
evidence correction without rewriting its original text. D6 forbids timestamps
in the new delivery manifest; copied F003 `creation_date` and D3 `retrieved_at` stay.

**Planning revision — APPROVED by Person 1 in this session:** R22 (parser and
taxonomy source hashes are informational only, checked for shape/internal
consistency, never against local source files), R28 (repository report inputs
and hashes), R29 (five payload descriptors, no self hash). Abstract question
CLOSED: keep paper-level abstract excluded. These approvals do not authorize
implementation; this run remains planning only.

## Reconciliation table

All mandatory rows and F002/F003 handoffs follow. "Draft" refers to committed
bootstrap docs; the optional v0.2 proposal is absent. Transformations beyond
these decisions default to NOT done.

| ID | Current state / source field → delivered field | Decision | Reason / evidence |
| --- | --- | --- | --- |
| R01 | Flat JSONL vs nested paper.sections[].chunks[] | Flat papers/sections/chunks; no nesting | D1; real writers, F002 handoff |
| R02 | `(untitled)` → unchanged section_path | No heading, never display it | D4; blank/root-abstract headings; filtered from embedding context |
| R03 | Locator nonempty string → strict v1 | Full path grammar plus locator_digest | locator_digest checks prefix/digest only; resolve checks path/traversal |
| R04 | Empty paragraphs vs nonempty chunk text | Legal zero-own-text section; no empty chunk | F002/F003; 0 blank pilot paragraphs, synthetic coverage needed |
| R05 | depth / paragraph_count → unchanged fields | Top level 1, nested sec +1; count own direct p including empty, not descendants | parser.py; 50 zero-own-paragraph sections; 0 recomputed count/depth-path mismatches |
| R06 | No paragraph entity → none delivered | Keep span locators and offsets | D4; paragraphs are producer-validation inputs only |
| R07 | 384 draft dimensions → set dimensions | Pilot 1536 requested/returned; no fixed 384 | Actual F003 manifest; D-004 stays Proposed |
| R08 | Required embedding_model_revision → nullable set field | null for OpenAI; not applicable | F003 supplies no revision; never invent |
| R09 | passage:/query: draft → empty prefixes | Preserve actual prefixes and query config | F003 manifest; D-004 proposed only |
| R10 | License URL assumption → raw string | No normalization or version inference | 11 URLs, 6 free text; require metadata/manifest agreement |
| R11 | Language example EN → raw language | Preserve 4 EN and 13 en; no schema case constraint; compare case-insensitively in guide | T007 appends a correction to F001 evidence; original text remains; no evidence edit in planning |
| R12 | subjects[0] Research Article → subjects | Preserve ordering and leading value | All 17 metadata records; no subject_categories rename |
| R13 | Draft source/source_url/source_xml_path → source_url | Retain source_url/retrieved_at/xml_sha256; exclude raw_xml_path, query_provenance, original_doi; no invented source | D3 allowlist; local XML resolved by DOI |
| R14 | Inline embedding → vectors.f32 | No embedding or embedding_text added to chunks | Exact F003 fields; rebuild input via versioned template |
| R15 | authors minItems 1 / nonempty journal → real constraints | Keep nonempty author-object array and journal; surname nonempty, given_names may empty | F001 rejects absent authors/journal; pilot has 0 empty; candidates differ |
| R16 | publication_date → publication_year | Retain date; derive leading four-digit integer year | Only derived paper field; all pilot dates full; F001 also permits year/month precision |
| R17 | DOI inputs → normalized DOI | Exact F001 algorithm; stored records already normalized | Reuse normalize_doi; no rewriting copied outputs |
| R18 | 11 candidates with empty journal → no delivery rows | F005 journal routing, outside pilot | 870 candidates; none of 17 acquired papers has empty journal |
| R19 | Raw Unicode separators → unchanged JSONL | Split LF only, never splitlines | F003 ensure_ascii=False handoff |
| R20 | Vector ID order vs chunk section order → manifest ID join | Session-approved D5 amendment, no reordering | 727/728 positional mismatches; store/pipeline sort chunk IDs |
| R21 | embedding_text/tokenizer_version draft → actual version fields | No rename/addition; record template/counter/chunking versions | embedding-text-v1, utf8-bytes-div3-v1, chunking-v1; exact input hashes |
| R22 | No parser/taxonomy version constants → informational provenance | APPROVED by Person 1 this session: parser version null + source_sha256; taxonomy v0 + source_sha256; check 64 lowercase hex and internal consistency only, never local source files; locator jats:v1 | Preserve old packages after F005 source edits; keep checking real chunking_version/token_counter_id/template_version identifiers |
| R23 | xml_sha256 / locator / hierarchy → unchanged | Check cross-record digest/ownership/path/type, raw XML for traversal | F002/F003 provenance; no XML shipped |
| R24 | Omitted captions/tables/references → unchanged chunks | Guide/report counts, no extra records | F003 Option A: 223 skipped elements, 33 back-matter exclusions |
| R25 | Abstract context / hard splits → unchanged | Document absent abstract heading context and 2 hard splits | Sentinel removed from input; no paper title; hard_split flag not independently proved |
| R26 | Validator/calibration/performance limits → guide limits | No retrieval/sentence-quality/vector-origin guarantee or optimization | Aggregate calibration only; O(chunks×sections)/O(chunks×paragraphs); F005 revisit |
| R27 | Upstream timestamps → retained payloads | New manifest has no timestamps | D2/D3 preservation and D6 determinism compatible |
| R28 | Reports outside package → repository report inputs + manifest hashes | APPROVED by Person 1 this session: no extra delivered files; matching reports required, not matching parser source bytes | Six payloads cannot prove report agreement alone; consumer needs no paragraphs/XML |
| R29 | Per-file digests → five payload descriptors | APPROVED by Person 1 this session: no self hash; compare committed manifest externally | Self-reference impossible; fixed basename identifiers, no filesystem paths |

## Record and identity contract

Paper field order: doi, title, authors, journal, publication_date, article_type,
subjects, license, language, source_url, retrieved_at, xml_sha256,
publication_year. Descriptive fields from metadata; source_url/retrieved_at/
xml_sha256 from manifest; licenses must agree. Require equal unique normalized
DOI sets; preserve strings/arrays without defaults. Year derives from leading
four digits of valid F001 year/year-month/full date; invalid date/year fails.
Do not import the draft's minimum year 1600 without authority.

Section fields exactly `jats/cli.py`: doi, title, xml_sha256, section_id,
parent_section_id, section_path, original_heading, normalized_type,
source_locator, depth, paragraph_count. Preserve preorder within DOI and null
root parents. Producer recomputes own paragraph counts using local paragraphs
only to detect inconsistency; consumer checks depth/parent/path and report
counts. It cannot reconstruct empty paragraph counts from chunk spans alone.

Chunk fields exactly `CHUNK_RECORD_FIELDS` in `chunking/output.py`: chunk_id,
doi, xml_sha256, section_id, ordinal, chunk_kind, normalized_type, section_path,
text, text_sha256, spans, source_locator, content_tokens, hard_split, omitted,
chunking_version, token_counter_id, template_version. chunk_kind is paragraph.
Spans: source_locator, paragraph_index, start, end; 1-based paragraph_index,
half-open Unicode code-point offsets, start >= 0, end > start. Chunk locator
equals first span locator. Same-paragraph gaps use original source substring;
different paragraphs join with `\n\n`. text_sha256 hashes exact UTF-8 text.
Reuse chunk_id's length-delimited fields: version, DOI, section ID, ordinal,
ordered span locator/start/end; paragraph_index is not in that hash.

Taxonomy enum exactly D4. Abstract always abstract. Body precedence: exact
normalized heading, sec-type, nearest explicitly classified ancestor, other.
Explicit other does not inherit. Carry `classify.py` exact mappings and F002
approved table into contract descriptions/DATA_MODEL. Normalize heading with
lower/strip, remove leading numbering matching
`^[0-9]{1,2}(?:\.[0-9]{1,2})*(?:\.(?![0-9])|[):]|\s+)`, strip surrounding
ASCII punctuation/whitespace, collapse whitespace. sec-type strip/lower only.
Mappings: intro/introduction → introduction; materials|methods/methods →
methods; results/discussion/conclusions → same; supplementary-material →
other. Heading mappings: introduction; material and methods / materials and
methods / methods and materials / methods → methods; results; results and
discussion → results_discussion; discussion; conclusions; supporting
information → other. Matches are exact, heading wins conflicts.

Locator syntax is `jats:v1:<64 lowercase hex>:/<component>/...`; component
full-matches Python `([^\W\d][\w.-]*)\[([1-9][0-9]*)\]` with Unicode
semantics. Delivered JATS root article[1]; subsequent indices count siblings
of the same local name, positive without leading zeros. Exact XML-byte SHA256,
no case folding. `locator_digest()` checks prefix/digest, not path; full
grammar must be checked separately. `SourceDocument.resolve` distinguishes
malformed, digest mismatch, path absent, invalid target; allowed targets sec,
p, abstract. Consumer proves grammar/digest, not XML traversal without XML.
Parity cases include Unicode names and trailing-LF edge cases.

DOI algorithm exactly `plos_pilot/doi.py`: strip whitespace; remove one
case-insensitive prefix from doi:, https://doi.org/, http://doi.org/,
https://dx.doi.org/, info:doi/. Otherwise http(s) URLs require exactly one
nonempty lowercase `id=` query item, percent-decoded once. Strip again,
remove trailing `.,;`, then surplus closing `)`/`]` using opener/closer counts,
removing trailing punctuation after each removed closer; lowercase; full-match
`^10\.[0-9]{4,9}/\S+$`. Preserve balanced closers, never double-decode.
Local XML rule: `data/raw/plos/` + `urllib.parse.quote(normalized_doi, safe='')`
+ `.xml`. Confine resolution to repo and check digest before JATS helpers.

## Manifest, modules and interfaces

Planned new modules: `src/sciscope/delivery/{__init__,contract,papers,package,
validate,reader}.py`; extend command wiring in `src/sciscope/pipeline/cli.py`.
Reuse public F003 validators, no upstream writer changes. Tests are unique
`tests/delivery/test_deliver_{contract,papers,package,structure,validate,reader}.py` and
neighboring `delivery_fixtures.py`; never `from tests...`.

Proposed manifest exact fields: schema_version and contract_version both
0.3.0, status initially draft, counts {papers, sections, chunks}, files,
processing_versions, source_reports, embedding_set. One schema root describes
this; `$defs` describes records/children with additionalProperties false.
Person 2 PR approval is recorded in evidence/D-007; do not infer it from a
string or inject review timestamps into reproducible data.

files has exactly five fixed payload basenames as keys, each sha256, bytes,
record_count: JSONL record count, vector row count, 1 for embedding manifest.
No self descriptor. source_reports has fixed parse/chunk/embedding report
basenames and sha256/bytes, no paths. These metadata-only additions (R28/R29)
support D8 without extra record files. Read committed reports directly.

processing_versions: parser {version: null, source_sha256: exact parser.py
digest}; taxonomy {version: v0, source_sha256: exact classify.py digest};
locator: jats:v1; chunking_version: chunking-v1; token_counter_id:
utf8-bytes-div3-v1; template_version: embedding-text-v1. The last four are
real identifiers; taxonomy v0 is D4's label, not a code constant. Parser null
honestly records absent version metadata. R22 is APPROVED by Person 1 in this
session with the informational-only restriction. Both source_sha256 values must be 64 lowercase
hex and internally consistent wherever repeated within manifest metadata.
They are NOT compared with local checkout source files: F005 edits must not
invalidate old packages. No source authenticity guarantee follows from a
well-formed digest. Keep comparing the real chunking_version, token_counter_id
and template_version identifiers across records, manifest and reports.

embedding_set: provider, model, dimensions (positive, requested = returned),
dtype float32-le, row_mapping embedding_manifest.entries, passage_prefix,
query_prefix, normalization {declared, observed_norm_min, observed_norm_max,
tolerance}, chunks_sha256, vectors_sha256, embedding_model_revision (null
for pilot). Copy observed norms from validated F003 manifest; tolerance 0.01.
No provider enum or 384 restriction. Current reused validator supports L2
declaration only; do not claim other normalizations work. Queries use the
same provider/model/dimensions/query_prefix and compatible input construction.

Proposed CLI (NOT available yet):

- deliver: --metadata, --acquisition-manifest, --sections, --paragraphs,
  --parse-report, --chunks, --chunk-report, --vectors, --embedding-manifest,
  --embedding-report, --output-dir, --committed-manifest. Defaults are the
  current pilot inputs; output-dir data/delivery/pilot, committed-manifest
  data/pilot/delivery_manifest.json.
- validate-delivery: --package-dir (data/delivery/pilot), --parse-report,
  --chunk-report, --embedding-report (data/pilot defaults). No partial override.
  Compatible checkout supplies schema/code and matching committed reports;
  parser/taxonomy source bytes need not match. No raw XML, paragraphs,
  cache, network or environment key required. Fixed six-file inventory;
  reject extra files, symlink escapes and paths supplied inside JSON.

Producer rejects resolved output aliases/overlap with input/cache directories.
Run existing load_sources/validate_chunks and validate_embedding_set on exact
bytes before writing; detect duplicate/missing DOI joins, license/digest/count
inconsistencies. Prefer building the complete package in a sibling temporary
directory, validate it, then replace the whole package directory rather than
rolling back individual payload files. Stage the committed manifest copy too;
retain the prior directory/copy until both replacements succeed and restore
both on caught failure (same all-or-fail logic). Test directory/copy replacement
failure injection. No claim of multi-file OS transaction on power loss: crash-mixed
sets must fail validation and be recoverable by rerunning. Existing valid
package survives caught failures. New JSON: UTF-8/no BOM, LF/final LF, stable
key order, paper DOI order, ensure_ascii=False, allow_nan=False. No clock.
Existing four payloads are copied as bytes, never reserialized or reordered.

Consumer independently checks all six files, rejects malformed UTF-8/JSON,
duplicate JSON keys and NaN/Infinity; collects structural findings and all
safe independent semantic findings. No raw values echoed. Check hashes/bytes/
record counts; report hashes and aggregate/per-paper counts against all three
reports; IDs/foreign keys/parent cycles and DOI ownership; xml_sha256 for paper,
section, chunk and every locator; paths/types, contiguous ordinals, text hash
and existing chunk_id function; real version identifiers, informational source
digest shape/internal consistency (never local source comparisons), and new
manifest purity.
Counts from parse_report.papers section_count and summary succeeded/failed;
chunk_report summary/per-paper paper/section/chunk counts; embedding_report
paper_count/chunk_count/vector_count. Consumer cannot prove paragraph coverage.

Reuse validate_embedding_structure and validate_embedding_set with delivered
chunks, exact chunks digest, copied manifest, repository embedding_report,
vector bytes and B3 counter. This reuses input hash/cap, size/finite/norm/set,
report/calibration checks and correct entry order. Do not manufacture paragraph
records to run producer chunk validation on the receiver. Cross-check all
embedding_set fields against reused validation. New manifest purity is an
allowlist of typed metadata and fixed filename identifiers: no prose, paths,
secrets or arbitrary extra keys. Existing manifest keeps F003 purity checks.

Exit 0 success, 1 semantic/I/O/publication failure, 2 usage/config/structural
failure as F003. Structural exit 2 takes precedence while all safe findings
are printed. Sorted codes, summed counts, at most 3 distinct safe IDs per
code: `error: <code> count: <k> first: <ids>` then `failures: <n>`; success
includes `failures: 0` and numeric summary. Reuse existing output-path-conflict,
output-write-failed, partial-set and vector/report/version codes. Synthetic
RED tests define new delivery-specific join/file/structure/digest/purity codes.

Reader contracts: iter_jsonl(path: Path) → Iterator[dict[str, object]], UTF-8
and LF-only segmentation, final empty segment allowed, interior blank/malformed
records rejected; preserve Unicode strings. load_vectors(path: Path, *,
dimensions: int, count: int) → tuple[tuple[float, ...], ...], positive dimensions,
exact count×dimensions×4 byte size, finite values, unpack `<f` using struct.
Set/norm validation stays in F003. Row ownership uses manifest entry IDs.
Add vectors_by_chunk_id(manifest_path: Path, vectors_path: Path, *,
dimensions: int) → dict[str, tuple[float, ...]]: load vectors using manifest
entry count, require dimension agreement with manifest, unique entry chunk IDs
and one-to-one row count, then map each entry's chunk_id to its vector tuple
in entries order. No chunks-file order assumption. Pilot fits memory;
no larger-corpus performance promise.

T006's guide opens with this example (planned, NOT RUN):

```python
from pathlib import Path
from sciscope.delivery.reader import vectors_by_chunk_id

package = Path("data/delivery/pilot")
vectors = vectors_by_chunk_id(
    package / "embedding_manifest.json", package / "vectors.f32", dimensions=1536
)
```

Never zip vector rows with chunks.jsonl lines by position. Join chunks by ID.
The embedding_set contract description contains only manifest-entry ID mapping;
the superseded row/line wording is historical context above, never schema guidance.

## Tests and verification strategy

T001–T006 start with labeled synthetic offline RED tests and observed failure
due to missing behavior, then GREEN for only that task. Fixture text is invented
and labeled; no article prose, network, key or paid call. Assert delivery
paths never read keys/cache or construct transports. Cover exact source copies,
one-to-one joins, raw license/language/subjects, year precision, untitled,
implicit/structured abstracts, zero-own-text sections, spans and Unicode LF.
Mutation matrix covers every six-file kind, missing/extra/wrong fields/types,
nulls, booleans, integral floats under JSON Schema integer semantics, nested
authors/spans, enums/hashes/locator Unicode/boundaries. Schema/runtime parity
compares structural acceptance through local `$ref` into the single schema;
no network refs, no silent reliance on nonasserting format. Cross-record/byte
semantics have separate tests. Include duplicates/orphans/cycles, digest/path/
version/report mismatches, partial/nonfinite/truncated/wrong-norm vectors,
independent error collection and status precedence, manifest/diagnostic purity,
output aliases, deterministic two-run bytes and injected directory/copy
publication failure recovery. Symlink-based tests MUST use pytest skipif when
symlinks cannot be created; report skipped cases honestly. Test informational
source digests against changed local source files in an isolated synthetic
checkout fixture: no mismatch finding solely because parser/classifier bytes differ.

Task split: T004 owns structure/schema parity and file-level checks (hashes,
bytes, record counts, purity, six-file inventory, partial-set marker). T005
owns cross-record semantics, report count comparisons, reuse of F003 embedding
validators, validate-delivery CLI and full staged-validator wiring. T006 owns
all three reader helpers/guide; T007 owns manual verification/evidence/docs sync.

Windows PowerShell 5.1 verification commands below are planned, NOT RUN here.
Run at repository root after implementation; check native exit codes. No
embedding/network command is needed.

```powershell
$env:PYTHONPATH = 'src'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
uv run --locked pytest -q
uv run --locked python -m pytest tests -q
uv run --locked ruff check . --no-cache
uv run --locked ruff format --check .
uv run --locked mypy src
git --no-pager diff --check
uv run --locked python -m sciscope.pipeline.cli validate --chunks-only
uv run --locked python -m sciscope.pipeline.cli validate
uv run --locked python -m sciscope.pipeline.cli deliver
if ($LASTEXITCODE -ne 0) { throw 'First delivery failed' }
$deliveryFirst = @{}
Get-ChildItem data/delivery/pilot -File | ForEach-Object {
    $deliveryFirst[$_.Name] = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
}
$committedFirst = (Get-FileHash data/pilot/delivery_manifest.json -Algorithm SHA256).Hash
uv run --locked python -m sciscope.pipeline.cli deliver
if ($LASTEXITCODE -ne 0) { throw 'Second delivery failed' }
Get-ChildItem data/delivery/pilot -File | ForEach-Object {
    if ($deliveryFirst[$_.Name] -ne (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash) {
        throw 'Delivery bytes changed'
    }
}
$committedSecond = (Get-FileHash data/pilot/delivery_manifest.json -Algorithm SHA256).Hash
if ($committedFirst -ne $committedSecond) { throw 'Committed manifest changed' }
if ($committedSecond -ne $deliveryFirst['delivery_manifest.json']) { throw 'Manifest copies differ' }
uv run --locked python -m sciscope.pipeline.cli validate-delivery
if ($LASTEXITCODE -ne 0) { throw 'Package validation failed' }
@'
import json
from pathlib import Path
from jsonschema import Draft202012Validator
from sciscope.delivery.reader import iter_jsonl, load_vectors, vectors_by_chunk_id
schema = json.loads(Path('docs/DATA_CONTRACT.json').read_text(encoding='utf-8'))
Draft202012Validator.check_schema(schema)
root = Path('data/delivery/pilot')
chunks = {row['chunk_id']: row for row in iter_jsonl(root / 'chunks.jsonl')}
manifest = json.loads((root / 'embedding_manifest.json').read_text(encoding='utf-8'))
vectors = load_vectors(root / 'vectors.f32', dimensions=1536, count=728)
assert len(vectors) == len(manifest['entries']) == len(chunks) == 728
assert all(len(row) == 1536 for row in vectors)
assert {entry['chunk_id'] for entry in manifest['entries']} == chunks.keys()
by_id = vectors_by_chunk_id(root / 'embedding_manifest.json', root / 'vectors.f32', dimensions=1536)
assert len(by_id) == 728 and by_id.keys() == chunks.keys()
assert all(by_id[entry['chunk_id']] == vectors[i] for i, entry in enumerate(manifest['entries']))
print('reader rows: 728 dimensions: 1536; ownership: manifest ID join')
'@ | uv run --locked python -X utf8 -
git check-ignore data/delivery/pilot/papers.jsonl
git --no-pager diff --stat
git --no-pager status --short
# Human reviews staged files for source prose, secrets and absolute paths.
# Trace one abstract and one body citation with show/check-quote and local XML.
# Archive commands: TO BE VERIFIED by Person 1 on Windows PowerShell 5.1.
tar -a -c -f data/delivery/pilot-delivery.zip -C data/delivery pilot
if ($LASTEXITCODE -ne 0) { throw 'Archive creation failed' }
Get-FileHash data/delivery/pilot-delivery.zip -Algorithm SHA256
$deliveryExtractDir = Join-Path ([System.IO.Path]::GetTempPath()) ('sciscope-f004-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $deliveryExtractDir -ErrorAction Stop | Out-Null
tar -x -f data/delivery/pilot-delivery.zip -C $deliveryExtractDir
if ($LASTEXITCODE -ne 0) { throw 'Archive extraction failed' }
uv run --locked python -m sciscope.pipeline.cli validate-delivery --package-dir (Join-Path $deliveryExtractDir 'pilot')
if ($LASTEXITCODE -ne 0) { throw 'Extracted package validation failed' }
# Send only after extracted-package validation and human acceptance.
```

Person 1 checks exact source-copy hashes and all six basenames; traces an
abstract and body section with `python -m sciscope.jats.cli show` and
`check-quote` plus a negative control. Guide includes a here-string/stdin
Python trace with Unicode code-point span slicing, never .NET Substring.
Actual quote text remains local, not evidence. Person 2 verifies archive
SHA256 out of band, extracts into an isolated directory, runs
validate-delivery --package-dir there with matching repository reports, and
reviews mappings, query rule and citation fields in the PR. No DB import gate.
Before sending, Person 1 creates and extracts the archive to a fresh temporary
directory and validates that directory's pilot package as shown above. Archive
commands are UNVERIFIED until Person 1 runs them. Archive is not deterministic;
choose a fresh archive destination on repeats.

T007 rewrites DATA_MODEL to real shapes, adds D-007 Proposed until Person 2
PR approval (D-004 stays Proposed), updates CHUNKING_STRATEGY/ARCHITECTURE
pointers and PROJECT_TODO. Append exact RED/GREEN, automated/human results,
archive SHA256, review and feature-PR CI result to EVIDENCE.md on this same
branch BEFORE squash merge. No placeholders: use NOT RUN / NOT VERIFIED /
NOT RECORDED where applicable. P2-20 checked only after human acceptance and
automated checks; P2-24 stays open. No commit or push in planning.
T007 also appends a correction line to the F001 evidence record, preserving
its old text: language in F001 metadata is 4 "EN" and 13 "en" (raw xml:lang),
not "EN 17/17". Do not edit EVIDENCE.md during this planning revision.

## Known limits and open questions

F003 proves structure/hashes, not vector semantic origin, sentence-boundary
quality or retrieval quality; hard_split is type-checked, not independently
proved. Calibration aggregate-only, tolerance empirical 0.01. O(n²) scans
are not benchmarked for expansion. Inherited limits: cache batch-write crash
may double-count usage; partial-batch totals can exceed selected inputs;
empty OPENAI_BASE_URL invalid; upstream cache-subdirectory output alias not
checked. New delivery path guards/complete-set rejection bound F004 without
rewriting F003. Omissions counted; abstract has no heading context; 2 hard
splits. Golden v0 PENDING; no model/retrieval comparison.

**Abstract question CLOSED by Person 1 in this session:** keep paper-level
abstract text excluded; abstract chunks/sections carry it. No essential
unresolved decision remains. R22 (informational-only source hashes), R28 and
R29 are APPROVED by Person 1 in this session. Spec/plan implementation
approval remains NOT RECORDED; these decisions authorize planning revisions only.

Person 2 installed DB/extension versions and actual import: UNVERIFIED.
Official pgvector documentation verified 2026-11-17: vector storage supports
up to 16,000 dimensions; HNSW and IVFFlat vector indexes up to 2,000. The
pilot's 1536 fits those documented limits, without an import claim. Guide
cites [vector type](https://github.com/pgvector/pgvector#vector-type),
[HNSW](https://github.com/pgvector/pgvector#hnsw) and
[IVFFlat](https://github.com/pgvector/pgvector#ivfflat).
