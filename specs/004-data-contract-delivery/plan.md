# Implementation Plan: Data contract refresh and pilot delivery

**Branch**: `004-data-contract-delivery` | **Date**: 2026-11-17 | **Spec**: [spec.md](spec.md)
**Owner**: Person 1; shared-contract reviewer: Person 2.
**Status**: Approved for implementation by Person 1 on 2026-11-17 (R22, R28, R29, D5 amendment and abstract exclusion included)

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
    package / "embedding_manifest.json",
    package / "vectors.f32",
    dimensions=1536,
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

## Implementation clarifications — Group A (T001–T002)

Person 1 approved spec/plan implementation on 2026-11-17, including R22,
R28, R29, the D5 amendment and abstract exclusion. The Status lines record
that approval; earlier planning-only statements above are historical. This
run authorizes **Phase 1 stubs and synthetic RED tests only** for T001–T002;
the phase label here is the session's RED-only stage, not a renumbering of
the tasks artifact. No GREEN, schema replacement, package, CLI, dependency,
data, existing documentation, evidence/backlog, checkbox, commit or push.
Person 1 runs RED locally. Automated execution and human acceptance remain
separate gates; no task is marked complete.

The following C1–C7 decisions are recorded verbatim from this session:

- **C1 Contract file.** In Phase 2 `docs/DATA_CONTRACT.json` becomes one Draft 2020-12 file: root = `delivery_manifest`; `$defs` for paper, section, chunk, span, embedding_set, embedding_manifest (derive its shape from the real F003 writer; `additionalProperties: false` only where the writer's field set is fixed), file descriptor, source-report descriptor, processing_versions. Local `#/$defs/...` references only. Tests build per-entity validators from that single file by wrapping a `$ref` plus the `$defs` (no network refs).
- **C2 Runtime checkers.** `src/sciscope/delivery/contract.py` exposes pure functions `check_paper`, `check_section`, `check_chunk`, `check_embedding_set`, `check_embedding_manifest`, `check_delivery_manifest`, each taking one parsed JSON object and returning a sorted tuple of unique structure codes (empty tuple = structurally valid). They never raise on bad input and never echo values. Code vocabulary (finalize names in plan.md): `<entity>-missing-field`, `<entity>-extra-field`, `<entity>-bad-type`, `<entity>-bad-value`, `<entity>-bad-pattern`. Aggregation into `Finding` with safe IDs happens in T004/T005, not here. Reuse the existing `is_json_*` helpers.
- **C3 Integer strictness.** Runtime keeps the existing strictness (`type(value) is int`: booleans and integral floats like `1.0` are rejected). JSON Schema `integer` accepts `1.0` and cannot be made stricter, so integral-float mutations are tagged in the fixtures as a DOCUMENTED divergence (schema accepts, runtime rejects) and excluded from parity; all other mutations must agree. The contract descriptions state that integers are written as integer literals.
- **C4 Pattern semantics.** Patterns (SHA-256 hex, DOI, locator v1, dates) must reject a trailing `"\n"` identically under Python `re.search` (what jsonschema uses) and in the runtime checkers; for example use a negative lookahead before `$`. Add trailing-LF mutations for each pattern field. Locator v1: `jats:v1:<64 lowercase hex>:/<component>/...`, each component fully matching `([^\W\d][\w\.-]*)\[([1-9][0-9]*)\]` with Unicode semantics (exactly as in the plan). DOI pattern and taxonomy enum exactly as implemented in code.
- **C5 Shared corpus.** `delivery_fixtures.py` provides factory functions returning FRESH dicts of valid synthetic records for every entity (labeled "SYNTHETIC"; include a zero-own-text section, an untitled/implicit section, a structured abstract section, a Unicode heading, `EN` and `en` languages, a free-text license and a URL license, `parent_section_id` null and non-null, `embedding_model_revision` null) and a tuple `MUTATIONS` of frozen dataclass items `(name, entity, apply, schema_accepts, runtime_accepts)`. Cover: missing/extra field, wrong type, boolean-as-integer, integral float (C3), null where forbidden, empty strings where nonempty is required, empty `authors`, empty `journal`, empty chunk `text`, empty-but-allowed `given_names`, bad enum, bad hash case/length/trailing LF, bad DOI, bad locator (uppercase digest, zero index, leading zero, bad component, trailing LF), unknown `chunk_kind`, span with `end <= start` or `start < 0`, non-positive dimensions, `dimensions` mismatch types, `status` not `draft`. T004 will extend this corpus with file-level cases and a formal parity test; do not weaken a constraint to fit a fixture.
- **C6 Real constraints only.** Derive every field set and constraint from the code (list the source file for each in plan.md). Where code does not constrain a value (e.g. `language`), use the minimal schema (nonempty string, NO letter-case constraint) and say so. `publication_year` has no 1600 minimum (not authorised). `schema_version` and `contract_version` are const `"0.3.0"`; `status` const `"draft"`.
- **C7 Paper builder (T002).** `src/sciscope/delivery/papers.py`: pure functions `derive_publication_year(date_text: str) -> int` (leading four digits of F001-valid year / year-month / full date; invalid → error) and `build_papers(metadata_records, manifest_records) -> tuple[dict[str, object], ...]` (one-to-one join by normalized DOI, equal unique DOI sets, licenses must agree, DOI order, field order exactly as in the plan's "Record and identity contract", raw string/array values preserved, excluded fields never copied). No file I/O (loading is T003). On any join/validation problem raise `PaperBuildError` carrying sorted, sanitized codes (collect ALL problems first: duplicate DOI, missing counterpart, license mismatch, invalid date/year, invalid DOI, malformed record). Finalize code names in plan.md. Inputs are never mutated.

### Renewed solution-research check (2026-11-17)

Problem: assert the flat v0.3 shapes through one local schema while retaining
the existing strict stdlib JSON helpers and no runtime dependency. The two
relevant approaches remain (A) local `$defs` with dev jsonschema plus stdlib
runtime checks, and (B) adding jsonschema at runtime. Recommend A under D7:
no new dependency or license, with shared mutation coverage to expose drift.
Dependency declaration remains `jsonschema>=4.23,<5` (dev only), Python
`>=3.12,<3.13`; the earlier research artifact records 4.26.0/MIT metadata.
No new package/version/license recommendation or security audit is claimed.

Renewed authoritative checks:

- [JSON Schema structuring](https://json-schema.org/understanding-json-schema/structuring)
  documents local JSON Pointer references and `$defs`; wrappers contain the
  original `$defs` plus `#/$defs/<entity>`. The delivery-manifest root is
  validated directly; it needs no duplicate definition. Tests reject remote
  references before constructing validators. No resolver/network hook needed.
- [JSON Schema integers](https://json-schema.org/understanding-json-schema/reference/numeric)
  confirms `1.0` is an integer in schema semantics. C3 preserves the runtime
  helper's stricter representation rule; only those tagged cases diverge.
- [jsonschema 4.26.0 pattern implementation](https://raw.githubusercontent.com/python-jsonschema/jsonschema/v4.26.0/jsonschema/_keywords.py)
  uses Python `re.search`. [Python re documentation](https://docs.python.org/3/library/re.html)
  documents `$` before a final newline and negative lookahead. Use an end
  guard such as `(?![\s\S])$` after the existing field grammar. This preserves
  Unicode locator semantics and rejects LF; do not replace it with ASCII names.

**Additional decision approved by Person 1 in this session:** general
`span.end > span.start` is semantic validation in T005 because Draft 2020-12
cannot compare arbitrary sibling numbers. T001 schema/runtime structure
checks enforce `start >= 0`, `end >= 1`; its `end <= start` cases use the
zero boundary (`0/0`, `0/-1`) and are rejected by both. No arbitrary positive
span-order comparison is claimed by structural parity. Likewise numeric
requested/returned dimension agreement remains set semantics in T005;
T001 tests wrong dimension types and non-positive dimensions. No other
unresolved design decision is introduced by this addendum.

### Sources, shapes and constraint boundaries

| Entity or constraint | Source file / approved authority | Phase 2 rule pinned by Group A |
| --- | --- | --- |
| Paper input fields, authors and descriptive values | `src/sciscope/plos_pilot/metadata.py` (`parse_article`, `_date`), committed `metadata.jsonl` structure only | Required title/authors/journal/date/article_type/license/language; authors are objects with nonempty surname and possibly empty given_names; subjects order unchanged. Metadata has abstract, which is excluded from papers. |
| Paper provenance and license agreement | `src/sciscope/plos_pilot/download.py`, committed `manifest.jsonl` structure only; D3/C7 | source_url/retrieved_at/xml_sha256 from manifest; compare raw license strings; exclude original_doi/raw_xml_path/query_provenance. Never infer SPDX/version. |
| DOI | `src/sciscope/plos_pilot/doi.py` | Reuse normalize_doi for join keys. Stored DOI grammar `^10\.[0-9]{4,9}/\S+` with true end guard, not just `$`. Normalization lowercases/trims/handles approved prefixes and punctuation; only normalized DOI is derived alongside publication_year. Other raw values are unchanged. |
| Date/year | `metadata.py::_date`; C4/C7 and record contract | Year/year-month/full date precision; leading four ASCII digits, valid positive calendar year/date, no 1600 minimum. F001 formats source components but does not independently validate every calendar combination; the approved builder rejects invalid dates. Retrieved-at keeps download writer's UTC ISO string, not a new delivery timestamp. |
| Section fixed fields/order | `src/sciscope/jats/cli.py::_section_rows` | Exact eleven fields in the record contract. Root parent null; nested parent non-null; original_heading can be empty; section_path carries `(untitled)`. |
| Section identities/depth/count | `src/sciscope/jats/parser.py` | DOI-bound IDs, implicit body-p groups and structured abstract descendants; depth positive, own paragraph_count nonnegative. Zero-own-text is legal; do not require chunks for every section. Cross-record relationships remain T005. |
| Taxonomy | `src/sciscope/jats/classify.py`, parser abstract handling; D4 | Exactly abstract, introduction, methods, results, results_discussion, discussion, conclusions, other. Preserve the mappings/precedence already recorded above. |
| Locator and XML digest | `src/sciscope/jats/locator.py` | Lowercase 64-hex digest; full Unicode component grammar, positive indices without leading zero; reject trailing LF. locator_digest alone does not validate the path; traversal/ownership is outside structural checks. |
| Chunk fixed fields/order and span shape | `src/sciscope/chunking/output.py::CHUNK_RECORD_FIELDS`, `chunk_record`; `core.py`/`report.py` | Exact eighteen fields, four span fields; paragraph chunk_kind, nonempty text, positive ordinal/index, nonnegative start; end bound as approved above. Preserve booleans, omitted array, versions and Unicode. Hash/identity consistency is T005, not a fixture claim. |
| JSON primitive predicates and findings | `src/sciscope/chunking/validate.py` | Reuse is_json_string/integer/number; int excludes bool and float, numbers finite. New checkers return code tuples, not Finding. Findings/IDs are T004/T005. |
| Embedding manifest and fixed nested objects | `src/sciscope/embedding/store.py::build_manifest`, `pipeline.py`, `validate.py::validate_embedding_structure` | Exact F003 root field set; normalization {declared, observed_norm_min, observed_norm_max}, usage {prompt_tokens,total_tokens}, entries {chunk_id,input_sha256}; no added revision/tolerance here. AdditionalProperties false only for these fixed sets. |
| Embedding set | Same F003 writers/validator plus approved D5 amendment and C1–C6 | New set metadata uses positive dynamic dimensions, float32-le, L2 norms/tolerance, nullable revision, row_mapping embedding_manifest.entries. No provider enum or fixed 384. Prefixes may be empty. |
| New delivery manifest/descriptors/versions | D6/R22/R28/R29 and Manifest, modules and interfaces above | Root fields and fixed five payload/three source-report names; no self descriptor; exact descriptor keys. parser null/version hash and taxonomy v0/hash informational only. Version/status constants and actual chunking/counter/template/locator identifiers. |
| Language and license | `metadata.py`, D3/C6/R10/R11 | Nonempty raw strings, no language case/English enum and no license URL-only constraint. Fixtures include EN/en plus mixed case, free text and URL licenses. |

Definition names are `paper`, `section`, `chunk`, `span`, `embedding_set`,
`embedding_manifest`, `file_descriptor`, `source_report_descriptor`, and
`processing_versions`. Factory dictionaries are structural examples only;
their invented cross-record hashes/counts are not a validated six-file package.
Nested fixed shapes inherit their enclosing entity's structure-code prefix.

### Interfaces and final code vocabularies

Every body below is a stub raising `NotImplementedError` in this phase.
`__init__.py` contains only a package docstring. No schema/runtime logic is
implemented and no existing helper is modified.

```python
def check_paper(value: object) -> tuple[str, ...]: ...
def check_section(value: object) -> tuple[str, ...]: ...
def check_chunk(value: object) -> tuple[str, ...]: ...
def check_embedding_set(value: object) -> tuple[str, ...]: ...
def check_embedding_manifest(value: object) -> tuple[str, ...]: ...
def check_delivery_manifest(value: object) -> tuple[str, ...]: ...
```

The finalized structure-code Cartesian vocabulary is:

- Entity prefix: `paper`, `section`, `chunk`, `embedding_set`,
  `embedding_manifest`, `delivery_manifest` (underscore spellings match `$defs`).
- Suffix: `missing-field`, `extra-field`, `bad-type`, `bad-value`, `bad-pattern`.
- Join with one hyphen, for example `embedding_manifest-bad-type`.
  Codes are sorted/unique; malformed roots produce only `<entity>-bad-type`.
  For present wrong types, report bad-type before attempting value/pattern
  checks; missing/extra/type errors are collected independently. Unknown
  values/keys never enter messages. Correctly typed empty strings/ranges/enums
  use bad-value; grammar violations use bad-pattern.

```python
class PaperBuildError(ValueError):
    codes: tuple[str, ...]

    def __init__(self, codes: Sequence[str]) -> None: ...


def derive_publication_year(date_text: str) -> int: ...


def build_papers(
    metadata_records: Sequence[object],
    manifest_records: Sequence[object],
) -> tuple[dict[str, object], ...]: ...
```

Here `Sequence` is `collections.abc.Sequence`. Broad element types permit
malformed parsed records to reach the collector without unsafe casts or
file loading. Functions never mutate inputs and do no I/O. Required input
fields are the retained allowlists plus DOI/license; excluded or unrelated
upstream fields are ignored and never copied. Missing excluded fields do
not fail the builder. A correctly typed record may have multiple defects.
Index every valid normalized DOI even when other retained fields are invalid,
so independent join/license problems remain detectable. An unkeyable row
still contributes invalid-doi/malformed-record, while unmatched valid DOI
keys contribute counterpart errors. Duplicate groups do not short-circuit
validation of other fields or license comparisons.

Final paper error codes (deduplicated and lexicographically sorted):

- `paper-duplicate-metadata-doi`
- `paper-duplicate-manifest-doi`
- `paper-missing-metadata`
- `paper-missing-manifest`
- `paper-license-mismatch`
- `paper-invalid-publication-date` (includes invalid year)
- `paper-invalid-doi` (a string fails normalize_doi)
- `paper-malformed-record` (non-object, missing retained field, wrong type,
  or invalid non-date retained structure/value)

`PaperBuildError.codes` contains only those codes; `str(error)` joins them
with `", "`. No DOI, raw date, text, license or path appears. Invalid
publication_date strings use invalid-publication-date; non-string dates
use malformed-record. No exception text from normalize_doi is propagated.

### Synthetic tests and expected RED inventory

Tests import the neighboring module as `from delivery_fixtures import ...`.
There is no `tests/delivery/__init__.py`. Fixtures label invented text as
SYNTHETIC; they perform no file/network/key access and return fresh nested
objects. MUTATIONS is a tuple of frozen dataclasses; each application copies
replacement containers. No xfail/skip hides missing behavior. T004 extends
the same corpus, filtering only DOCUMENTED-C3 cases from formal parity.

`test_deliver_contract.py` covers:

- Draft202012Validator.check_schema and dialect, root/required/definitions/
  local references, the two version constants and draft status.
- Good records for every schema entity (including child descriptors/span),
  and all six runtime checkers; raw language variants, pre-1600 year,
  zero-own-text, implicit/untitled, structured abstract, Unicode locator.
- Every mutation's separately tagged schema/runtime verdict, non-object
  roots, sorted unique collected codes, safe vocabulary and unchanged inputs.
- Fixture field order against CHUNK_RECORD_FIELDS, AST extraction of the
  actual section writer and embedding-manifest writer; fresh nested factories,
  unique mutation names, explicit C3 divergence tags.

`test_deliver_papers.py` covers:

- Success with shuffled metadata/manifest order, DOI spelling normalization,
  exact field order, provenance ownership, raw strings/arrays/subjects/license/
  EN/en, empty given_names and excluded fields; unchanged inputs.
- Standalone year derivation at all three precisions, pre-1600 and year 0001;
  retained publication_date precision through the builder.
- Invalid precision/calendar/year/LF/whitespace/Unicode-digit dates; exact
  errors for duplicates on both sides, missing counterparts, invalid DOI,
  malformed/missing fields/records and license mismatch; unchanged failures.
- Collection of all eight independent error codes, equal-count unequal DOI
  sets, sorted unique PaperBuildError codes, and blocked filesystem/network
  access around successful and failing pure builder calls.

Counts and RED/pass predictions are recorded after static review below.
RED is **expected, not observed**: all runtime tests reach NotImplementedError;
schema behavior/layout/constants tests fail against the unchanged old nested
schema. Schema verdict tests assert the root layout first, producing clear
old-schema failures instead of unresolved local-reference exceptions.
Already-pass predictions are the existing document's check_schema, actual
writer field checks, fixture freshness and mutation-tag integrity. No existing
928-test result, locked-tool result, or human acceptance is claimed here.

| File | Test functions | Expanded cases (static count) | Expected RED | Expected pass |
| --- | ---: | ---: | ---: | ---: |
| `tests/delivery/test_deliver_contract.py` | 14 | 623 | 608 | 15 |
| `tests/delivery/test_deliver_papers.py` | 9 | 86 | 86 | 0 |
| `tests/delivery/delivery_fixtures.py` | 0 | 0 | 0 | 0 |

The corpus has ten entity factories, 34 good schema examples (30 for the
six runtime checkers), and 252 mutations, six of which are DOCUMENTED-C3
integral-float divergences. Contract case arithmetic: 1 metaschema + 1 layout
+ 3 constants + 34 good schema + 30 good runtime + 252 schema mutations
+ 252 runtime mutations + 30 non-object roots + 6 collected-code cases
+ 3 writer checks + 10 freshness checks + 1 divergence-integrity check = 623.
Expected passes: metaschema (1), writer checks (3), freshness (10), divergence
integrity (1). Paper arithmetic: 1 success + 5 year precision/boundary
+ 3 builder precision + 17 bad dates + 1 error class + 56 failure cases
+ 1 collect-all + 1 unequal sets + 1 no-I/O = 86. These are statically
derived counts; pytest collection/execution is NOT RUN.

Phase 1b extends only the existing SYNTHETIC corpus and the T005 semantic
sentence. The generic tests already exercise every added fixture/mutation;
`test_deliver_contract.py` and `test_deliver_papers.py` need no changes.
Whole-suite prediction, **assuming all 928 existing tests still pass**:
**694 failed, 943 passed** (608 contract RED + 86 builder RED; 15 contract
passes + 928 existing passes). This is not an observed test outcome.

| Phase 1b addition | New mutations | Reject both | Accept both | New good records |
| --- | ---: | ---: | ---: | ---: |
| Section boundaries and field types | 9 | 9 | 0 | 0 |
| Chunk boundaries, types, omitted/spans and version strings | 11 | 11 | 0 | 1 |
| Delivery manifest children/descriptors/versions | 32 | 30 | 2 | 0 |
| Embedding set shape and allowed strings/prefixes | 13 | 10 | 3 | 0 |
| Embedding manifest status/entries/usage/boolean | 12 | 10 | 2 | 0 |
| Paper date/provenance/year/subjects | 12 | 9 | 3 | 1 |
| Total added (163 -> 252 mutations; 32 -> 34 good records) | 89 | 79 | 10 | 2 |

Phase 1b renewed solution-research/static code check: extend the existing
tagged shared corpus rather than introduce a second validator or dependency.
The [official schema string reference](https://json-schema.org/understanding-json-schema/reference/string)
confirms patterns and minLength are explicit constraints: a pattern-shaped
date does not assert calendar validity. The existing dev dependency and
stdlib-runtime recommendation remain unchanged. No new package/license or
runtime implementation. Source verification and minimal-schema decisions:

| Requested constraint group | Verified code / authority | Verdict or deviation |
| --- | --- | --- |
| Section depth/count/path/heading/parent/ID/title | `jats/parser.py::visit_section`, implicit body paragraph construction; `jats/cli.py::_section_rows`; `plos_pilot/metadata.py::parse_article` | Top level depth 1, nested +1; own paragraph count >= 0; nonempty path of heading-or-sentinel strings; heading may be empty but not null; parent null or string, generated IDs nonempty; title required by metadata. All nine requested rejects added. |
| Chunk ordinal/count/span/boolean/version fields | `chunking/core.py::chunk_section`, `_source_piece`, `_paragraph_units`; `chunking/output.py::chunk_record`; `chunking/counter.py::Utf8BytesDiv3Counter.count`; `chunking/validate.py::validate_chunks` | Ordinals start at 1; nonblank pieces have spans; hard_split is boolean. Nonempty text under the actual utf8-bytes-div3-v1 counter has content_tokens >= 1, so both 0 and -1 reject. Equality to recomputed text counts and configurable caps remain semantic; no fixed schema maximum is invented. Empty version strings cannot represent the emitted identifiers. |
| Omitted element shape | `chunking/core.py::Chunk`; `chunking/output.py::chunk_record`; `chunking/report.py::EXCLUDED_CATEGORIES`; `jats/parser.py::paragraph_text`, `emit_paragraph` | List of raw XML element-name strings, not category/count objects. Good hard_split chunk uses [fig, table-wrap]. Reject object containers and object/integer elements. No closed enum is invented for omitted kinds; report policy handles unlisted names. |
| Five files, three reports, counts and descriptors | Approved D6/R22/R28/R29 and the existing manifest interface (there is no F004 writer yet) | Missing/extra basenames reject, including a sixth delivery_manifest.json self descriptor. Each of five payload descriptors has nonnegative bytes/record_count; each source-report descriptor has nonnegative bytes and **no record_count field**. Test every existing descriptor count/size field; do not invent source-report record counts. All three entity counts reject negative values. |
| Processing versions | Existing manifest interface, R22; `jats/locator.py` literal jats:v1 | Locator must be jats:v1, parser object rejects extra keys, taxonomy version cannot be empty. No parser version constant exists in code. Under Phase 1b, allow null or a nonempty informational parser version string, without inventing a fixed version. This refines the pilot's null example; hash remains informational. |
| Embedding set fields | `embedding/store.py::build_manifest`; `embedding/validate.py::_check_vectors`, validate_embedding_set norm_tolerance contract; `pipeline/cli.py::_norm_tolerance`; D5 amendment and approved set interface | float32-le, L2, positive tolerance (existing CLI also bounds it by 1), numeric observed extrema. Nonempty provider/model; model revision nullable or nonempty string; prefixes may be empty. Row mapping and model-revision field are approved new F004 metadata, not fields emitted by F003. No provider enum or dimension-agreement check is added here. |
| F003 manifest status and fixed child shapes | `embedding/store.py::build_manifest`; `embedding/pipeline.py::EmbedStats`, run_embedding; `embedding/validate.py::validate_embedding_structure`, validate_embedding_set | Writer emits complete or partial: both structurally accepted; draft/unknown/empty rejected. Delivery-level partial rejection remains T004/T005. Entries have exactly chunk_id/input_sha256; usage exactly prompt_tokens/total_tokens; custom_base_url_used boolean. |
| Publication date/year and provenance | `plos_pilot/metadata.py::_date`, parse_article; `plos_pilot/download.py::download_selected`; approved C7 | Format-only year/year-month/full-date pattern rejects yesterday, 2024-1 and 24, but **accepts 2024-13 structurally**. Calendar validity is the paper builder's job. Derived positive year permits 1 but not 0/negative; no 1600 minimum. Retrieved-at must have timestamp shape; real writer uses timezone-aware astimezone(UTC).isoformat(), including optional microseconds. Invented good timestamp: 2026-11-15T09:26:53.481027+00:00. Source URL nonempty, no new host whitelist. |
| Subjects | `plos_pilot/metadata.py::parse_article` initializes [], appends only nonempty _text results, excludes subjects from required-nonempty checks | Empty array ACCEPTED; empty/non-string elements rejected. Order preserved. This follows the code rather than inferring minItems from the selected pilot. |

No requested rejection is silently strengthened into a new semantic check.
The intentional distinctions above are structural 2024-13 acceptance,
complete/partial acceptance, empty subjects/prefix acceptance, real omitted
string shape and report descriptors without record_count. No article prose,
network calls, keys, implementation or schema edits are introduced. T005 now
explicitly owns span end > start for every span and agreement of requested/
returned/set dimensions with the embedding manifest.

| Phase 1b verification (direct local .venv executables) | Observed result |
| --- | --- |
| `ruff check . --no-cache` | PASS |
| `ruff format --check tests/delivery` | PASS (3 files) |
| `ruff format --check .` | PASS (119 files in the current checkout); supersedes the earlier Phase 1 formatting failure below |
| `mypy src` | PASS (38 files; source unchanged in Phase 1b) |
| `git --no-pager diff --check` | PASS |
| Focused/full pytest, locked-tool run, existing 928 regression tests, human verification | NOT RUN / UNVERIFIED; RED counts above are predictions |

Static/tool review in this run (direct local `.venv/Scripts` executables,
not `uv run --locked`; no dependency synchronization):

- `ruff check . --no-cache`: PASS.
- `ruff format --check tests/delivery src/sciscope/delivery`: PASS (six files).
- `mypy src`: PASS (38 source files, including the three new stub files).
- `git --no-pager diff --check`: PASS for tracked changes. New files were
  reviewed for trailing whitespace as part of the final static check.
- Whole-repository `ruff format --check .`: FAIL with local Ruff 0.17.5,
  solely on the pre-existing plan example at line 338. Its existing
  vectors_by_chunk_id call needs its three arguments on separate lines.
  That snippet is outside this addendum and remains untouched under the
  explicit restriction on existing planning-file edits. All new code and
  addendum snippets pass the format check. Locked-tool outcome is UNVERIFIED.
- Focused/full pytest, prior 928 regression tests, meaningful observed RED,
  CI and human verification: NOT RUN / UNVERIFIED. No claim of GREEN.

Person 1 runs these exact commands from the repository root:

```powershell
$env:PYTHONPATH = 'src'
uv run --locked python -m pytest tests/delivery -q
uv run --locked pytest -q
uv run --locked ruff check . --no-cache
uv run --locked ruff format --check .
uv run --locked mypy src
git --no-pager diff --check
```

Expected pytest failures are confined to tests/delivery and missing behavior
(NotImplementedError or the old schema shape); existing 928 tests are
expected to remain passing but must be verified locally. Do not mark task
boxes complete from these predictions. Stop after this Group A Phase 1 scope.

## Implementation clarifications — Group A, Phase 2

Person 1 authorizes T001/T002 implementation only, after the preceding RED
test-writing phases. No observed RED result was supplied or run here; the
user explicitly assigns pytest execution to Person 1. No task checkbox is
changed, and automated/human verification remains pending until T007.
Only DATA_CONTRACT.json, delivery/contract.py, delivery/papers.py, this
addendum and the single permitted test function change in Phase 2.

- **P1 One pattern source.** `contract.py` defines the compiled module-level
  HASH_PATTERN, DOI_PATTERN, LOCATOR_PATTERN, PUBLICATION_DATE_PATTERN,
  RETRIEVED_AT_PATTERN and CREATION_DATE_PATTERN. The schema uses their exact
  `.pattern` strings. The schema was rendered once from the same declarative
  field tables; runtime never reads the schema or imports jsonschema. The
  only test addition, `test_schema_patterns_match_runtime_constants`, checks
  every schema pattern and coverage of all six constants. It was added in
  Phase 2 **without an observed RED**; existing tests/fixtures are unchanged.
- **P2 End guard.** All six anchored patterns end in `(?![\s\S])$` so Python
  re.search rejects a final LF. The same strings are in the schema; no
  separate fullmatch-only runtime interpretation hides a schema mismatch.
- **P3 Pattern content.** Hash is 64 lowercase hexadecimal characters; DOI
  is the exact F001 `^10\.[0-9]{4,9}/\S+` grammar plus the end guard. DOI
  lowercase/normalization consistency is semantic (T005), not a pattern
  restriction. Locator uses jats:v1, a lowercase digest and one or more
  Unicode `[^\W\d][\w\.-]*\[[1-9][0-9]*\]` components. Publication date
  is ASCII YYYY / YYYY-MM / YYYY-MM-DD shape only, including structurally
  legal 2024-13. Retrieved-at is UTC ISO seconds with optional 1–6 fractional
  digits and literal +00:00; creation_date is YYYY-MM-DD. Builder calendar
  validation is separate and exact.
- **P4 Descriptions carry the contract.** Schema descriptions record the
  normalize_doi reference and DOI-to-local-XML quote rule; taxonomy v0 enum
  and heading > sec-type > nearest explicit ancestor > other precedence
  (abstract always abstract); locator grammar and locator_digest limitations;
  no-display `(untitled)` sentinel; raw EN/en language and case-insensitive
  comparison; raw license; integer literals rather than 1.0; manifest-entry
  ID vector ownership only; informational parser/taxonomy source hashes,
  never compared with local files; and null model revision when inapplicable.
  The existing `$id` remains https://sciscope.example/schemas/data_contract.json.
  Title/description now state flat F001–F003 shapes and draft status until
  Person 2 approves the contract PR.
- **P5 Paper builder internals.** Both input sides are indexed by
  normalize_doi, including valid keys on records with invalid other fields.
  DOI exception text is caught and discarded. Every retained field is checked
  independently, using the same paper field specifications as check_paper;
  this also catches nested missing author fields. Missing counterpart,
  duplicate, raw-license and field/date errors collect before raising.
  Excluded upstream fields are never copied or traversed. Output uses the
  exact PAPER_FIELDS order and normalized DOI order, preserving raw values
  in fresh dictionaries/arrays. Calendar checking uses datetime.date and
  the ASCII shape pattern, with no whitespace/LF/fullwidth-digit acceptance
  or 1600 floor. PaperBuildError retains only approved codes (unknown codes
  become paper-malformed-record), deduplicates/sorts them and joins with
  comma-space for str(error). No file/network/key/cache access.

Renewed solution-research for the small drift guard compared the existing
local-$defs/declarative stdlib approach with adding a runtime schema library;
retain the approved stdlib approach with no dependency/license change.
[Official Python re documentation](https://docs.python.org/3/library/re.html)
reconfirms compiled patterns and the final-newline `$` behavior;
[official schema structuring documentation](https://json-schema.org/understanding-json-schema/structuring)
reconfirms local `$defs` JSON Pointer references. No new library version or
security claim is made. Both checks preceded the drift-guard addition.

| Writer verification / decision | Code evidence | Result |
| --- | --- | --- |
| Locator root | `jats/locator.py::SourceDocument.resolve` compares root name with local_name(self.root), and root index with 1 | It does **not** hardcode article[1]. Preserve the supplied Unicode component grammar; document-specific root/traversal checks remain semantic. No extra article-root constraint. |
| DOI grammar | `plos_pilot/doi.py::_DOI_PATTERN`, normalize_doi | Same F001 grammar with true end guard, no structural lowercase test. |
| Publication-date shape | `plos_pilot/metadata.py::_date` formats year/month/day components | Three supported precisions, shape only structurally; approved builder rejects invalid calendar combinations. |
| Retrieved-at | `plos_pilot/download.py::download_selected` calls retrieved_at.astimezone(UTC).isoformat() | Literal UTC +00:00, optional microseconds; the requested 1–6 fractional digits accepts the writer's six-digit fractional form without imposing a calendar check. |
| Creation date | `pipeline/cli.py::_utc_date` returns datetime.now(UTC).date().isoformat(); `embedding/pipeline.py::run_embedding` passes it to cache entries; `embedding/store.py::build_manifest` emits creation_date | YYYY-MM-DD shape, independently of timestamp pattern. |
| Checkers | `chunking/validate.py::is_json_string/integer/number` reused by one field-spec walker | Sorted unique safe codes, wrong types stop value/pattern checks for that field, missing/extra/type defects collected independently. Malformed roots yield only entity-bad-type. No mutation, recursive schema, or input-dependent exception formatting. |
| Schema layout | Root delivery_manifest, exactly nine approved `$defs`, all references local | Every declared object has a fixed required set and additionalProperties false; nullable parent/revision/parser-version and permitted empty values preserved. C3 integer representation divergence remains documented. |

No deviation from the requested Phase 2 behavior was found in static
review. The locator root interpretation follows the prompt's conditional
rule and the real resolver rather than assuming every SourceDocument is
rooted at article. TEST ISSUES: **none identified by static review**; no
existing test or fixture was changed. Test execution is still required.

| Phase 2 verification | Observed result or explicit prediction |
| --- | --- |
| Local `.venv/Scripts/ruff.exe check . --no-cache` | PASS |
| Local `.venv/Scripts/ruff.exe format --check .` | PASS, including Markdown Python blocks |
| Local `.venv/Scripts/mypy.exe src` | PASS (38 source files) |
| `git --no-pager diff --check` | PASS |
| Focused pytest | NOT RUN; predicted 710 passed, 0 failed (624 contract, 86 paper cases) |
| Whole-suite pytest, either entry point | NOT RUN; predicted **1638 passed, 0 failed** = prior 1637 + 1 unparameterized drift guard; existing 928 assumed passing |
| Draft202012Validator.check_schema | NOT RUN; predicted PASS for the new Draft 2020-12 schema |
| Locked-tool verification, CI and human verification | NOT RUN / UNVERIFIED; no observed GREEN or completion claim |

Person 1 runs these exact commands from the repository root:

```powershell
$env:PYTHONPATH = 'src'
uv run --locked python -m pytest tests/delivery -q
uv run --locked pytest -q
uv run --locked python -m pytest tests -q
uv run --locked ruff check . --no-cache
uv run --locked ruff format --check .
uv run --locked mypy src
git --no-pager diff --check
```

T001/T002 remain unchecked until T007 human verification; no commit/push.
Stop after this Group A Phase 2 scope.

## Implementation clarifications — Group B (T003)

Person 1 authorizes **Phase 1 only** on 2026-11-17: package interfaces,
SYNTHETIC offline behavior tests, and this addendum. No package implementation,
CLI wiring, ignore-rule change, GREEN claim, checkbox change, commit or push.
Group A's 1638 passing tests are **user-reported local evidence**, not rerun
here. EVIDENCE.md and PROJECT_TODO.md remain untouched by explicit run scope.
The following B1–B10 decisions are recorded verbatim from Person 1's request.

- **B1 Validate what you ship.** `deliver` first COPIES the four F002/F003 payloads (`sections.jsonl`, `chunks.jsonl`, `vectors.f32`, embedding `manifest.json` → `embedding_manifest.json`) as bytes into a staging directory, then runs the existing validators (`load_sources`, `validate_chunks`, `validate_embedding_set`, `validate_embedding_structure`, same orchestration as `_validate` with `allow_partial=False`, default tolerance 0.01) against the STAGED copies, using the original `paragraphs.jsonl` and `parse_report.json` (not delivered). Put that orchestration in a new function in `package.py`; do NOT modify `_validate` or any F003 module. A partial embedding set is refused through the existing code.
- **B2 Public API in `src/sciscope/delivery/package.py`** (finalize exact names in plan.md): a frozen `DeliveryInputs` dataclass with all paths (defaults = the current pilot paths, same constants the CLI uses); `DeliveryError(code)` with sanitized codes; pure `build_delivery_manifest(...) -> dict[str, object]` (no I/O; takes hashes/sizes/counts/identifiers and the F003 manifest facts); `render_manifest(...) -> bytes` and papers rendering `render_papers(...) -> bytes` (deterministic: UTF-8, no BOM, LF, final LF, `ensure_ascii=False`, `allow_nan=False`, key order as built — papers in `PAPER_FIELDS` order, DOI order; reuse the JSON/JSONL conventions of `chunking/output.py` and `embedding/store.py::render_json`, and record them); `run_delivery(inputs) -> DeliverySummary` doing everything incl. publication.
- **B3 Manifest contents** exactly the contract's `delivery_manifest`: `schema_version`/`contract_version` "0.3.0", `status` "draft", counts, `files` (five payload descriptors: sha256, bytes, record_count — JSONL line count, vector row count, 1 for the embedding manifest), `source_reports` (sha256, bytes of the three committed reports `data/pilot/{parse,chunk,embedding}_report.json`; no record_count), `processing_versions` (parser `{version: null, source_sha256: sha256 of the bytes of src/sciscope/jats/parser.py}`, taxonomy `{version: "v0", source_sha256: sha256 of classify.py bytes}` — informational only, locator "jats:v1", chunking_version/token_counter_id/template_version taken from the validated data and asserted equal to the code constants), `embedding_set` (from the staged F003 manifest: provider, model, dimensions = returned = requested, `float32-le`, `embedding_manifest.entries`, prefixes, normalization {declared, observed min/max, tolerance 0.01 as the default constant}, chunks_sha256, vectors_sha256, `embedding_model_revision` null). No timestamps, paths, prose or secrets. Run `contract.check_*` over the manifest and every produced paper/section/chunk record and refuse on any structural code.
- **B4 Reading inputs.** Read `metadata.jsonl` and the acquisition `manifest.jsonl` with a small private LF-only JSONL reader in `package.py` (split on `"\n"` only, never `splitlines()`; reject malformed UTF-8/JSON, duplicate keys, NaN/Infinity, interior blank lines); `reader.py` belongs to T006, do not create it. Section/chunk record counts are LF-delimited line counts of the staged bytes.
- **B5 Publication is all-or-fail.** Build the complete six-file package in a sibling temporary directory inside the output directory's parent; validate it (re-read the staged files, recompute hashes against the manifest, structure checks); stage the committed manifest copy as a temp file next to `data/pilot/delivery_manifest.json`; then replace the whole package directory and the committed copy, retaining the previous directory/copy until BOTH replacements succeed and restoring both on a caught failure (Windows: a directory rename can fail with PermissionError; treat it as `output-write-failed`). After a caught failure the previous package and copy are intact, no staging/backup directory remains (best effort) and nothing is mixed. Leftover staging/backup from an earlier crash must not be mistaken for a valid package and must be cleaned or ignored deterministically (define and test). No claim of power-loss atomicity.
- **B6 Alias guards.** Reject (code `output-path-conflict`, exit 2) when the resolved output dir or committed-manifest path equals or overlaps any input path, the embedding cache directory, the staging/backup locations, or each other; also reject an output dir that is a file or a symlink to elsewhere (symlink tests `pytest.mark.skipif` when symlinks cannot be created).
- **B7 Exit codes and output.** Same as F003: 0 success; 2 usage/config/unreadable or structurally invalid input/`output-path-conflict`; 1 upstream semantic findings, join/paper-build failures, structure findings in the produced records, or `output-write-failed`. Output is sanitized: `error: <code> count: <k> first: <ids>` then `failures: <n>` (reuse the existing `Finding`/printing style; `PaperBuildError` codes print as findings with id `report`); success prints one line with numeric counts only (papers, sections, chunks, vectors, files). Never print paths, values, prose, keys, or exception text.
- **B8 No environment/network.** `deliver` never reads environment variables for keys, never creates a transport, never touches the embedding cache. Test it the way F003 did (recording environment + static guard + blocked sockets).
- **B9 Determinism.** Two runs on unchanged inputs produce byte-identical files for all six package files and for the committed copy; the four copied payloads are byte-identical to their sources; sources are never modified.
- **B10 CLI.** `deliver` is a subcommand of `src/sciscope/pipeline/cli.py` with options `--metadata --acquisition-manifest --sections --paragraphs --parse-report --chunks --chunk-report --vectors --embedding-manifest --embedding-report --output-dir --committed-manifest` (defaults = current pilot paths; output dir `data/delivery/pilot`, committed copy `data/pilot/delivery_manifest.json`). Phase 1 only specifies it in plan.md and tests it through `main([...])`; Phase 2 wires it and adds `data/delivery/` to `.gitignore`.

### Renewed solution-research before the new tests

Problem: replace a nonempty package directory and a second manifest file on
Windows and POSIX, preserving both previous artifacts after a caught move
failure. There is no portable two-path filesystem transaction in the current
stdlib design. No new dependency is proposed; Python target remains 3.12.

| Approach | Verified facts, integration and tradeoff |
| --- | --- |
| Direct directory replacement | [Python 3.12 os.replace](https://docs.python.org/3.12/library/os.html#os.replace) documents atomic successful rename, same-filesystem constraints, and failure for nonempty destination directories. [Microsoft MoveFileExW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-movefileexw) documents same-drive directory moves and an error when replacement targets an existing directory. This does not provide the required portable replacement of a populated directory. |
| Sibling staging plus retained backups | Recommended: move old destinations aside, install staged directory and staged copy, restore on caught failure. Uses maintained stdlib os/tempfile/shutil/Path, project Python 3.12, no third-party version/license or dependency addition. More rollback logic; test each forward move on Windows/POSIX. No cross-path or power-loss atomicity claim. |
| Existing write_outputs per-file rollback | Reuses F003's maintained local stdlib writer and byte rendering conventions; its existing rollback restores individual file bytes. Does not replace a complete directory or exclude mixed package inventories as B5 requires. Reuse its conventions, not its publication algorithm. |

Documentation confirms API limitations; actual Windows lock/permission
behavior and rollback success remain **NOT RUN** here. No security audit or
new library compatibility claim. Recommendation follows B5, with the precise
reserved-name and move protocol below; no unresolved design choice is needed
for these Phase 1 tests. This brief research is kept here because this run
permits only plan.md changes among existing artifacts; research.md is untouched.

### Final interfaces and serialization

`src/sciscope/delivery/package.py` contains interface-only stubs. The frozen,
slotted `DeliveryInputs` fields and defaults are:

| Field | Default |
| --- | --- |
| metadata | data/pilot/metadata.jsonl |
| acquisition_manifest | data/pilot/manifest.jsonl |
| sections | data/processed/pilot/sections.jsonl |
| paragraphs | data/processed/pilot/paragraphs.jsonl |
| parse_report | data/pilot/parse_report.json |
| chunks | data/processed/pilot/chunks.jsonl |
| chunk_report | data/pilot/chunk_report.json |
| vectors | data/embeddings/pilot/vectors.f32 |
| embedding_manifest | data/embeddings/pilot/manifest.json |
| embedding_report | data/pilot/embedding_report.json |
| output_dir | data/delivery/pilot |
| committed_manifest | data/pilot/delivery_manifest.json |
| cache_dir | data/embeddings/pilot/cache |
| parser_source | src/sciscope/jats/parser.py |
| taxonomy_source | src/sciscope/jats/classify.py |

Every field is a Path. Existing CLIs use literal Path defaults rather than a
shared constants module: these values match the real F001/F002/F003 defaults.
Do not change upstream modules to centralize them. cache_dir is only a guard
input; never stat/read/list/create its contents. parser_source/taxonomy_source
are informational hash inputs for producer provenance, configurable through
the Python API for isolated checkout tests, with no new CLI options.

The frozen, slotted `DeliverySummary` contains five integers: papers,
sections, chunks, vectors, files. `DeliveryError(code: str)` exposes only
sanitized `code: str` and `exit_code: int`; unknown input becomes
`delivery-failed`, exit 1. No exception text is retained or printed.
`DEFAULT_NORM_TOLERANCE = 0.01`. Final function signatures are:

```python
def build_delivery_manifest(
    *,
    counts: Mapping[str, int],
    files: Mapping[str, Mapping[str, object]],
    source_reports: Mapping[str, Mapping[str, object]],
    parser_sha256: str,
    taxonomy_sha256: str,
    chunking_version: str,
    token_counter_id: str,
    template_version: str,
    embedding_manifest: Mapping[str, Any],
) -> dict[str, object]: ...


def render_manifest(manifest: Mapping[str, object]) -> bytes: ...


def render_papers(papers: Sequence[Mapping[str, object]]) -> bytes: ...


def validate_staged_inputs(
    inputs: DeliveryInputs, staged_dir: Path
) -> tuple[Finding, ...]: ...


def run_delivery(inputs: DeliveryInputs) -> DeliverySummary: ...
```

The builder receives descriptors and identifiers, never paths, clocks or
source code to compare. Fresh output mappings preserve the exact manifest
field order in the existing interface table. The three real identifiers
come from validated data and must equal CHUNKING_VERSION (chunking-v1),
Utf8BytesDiv3Counter.counter_id (utf8-bytes-div3-v1), TEMPLATE_VERSION
(embedding-text-v1). Producer hashes the actual parser/classifier bytes;
neither builder nor staged upstream validation compares those informational
hashes with another checkout. T005 still owns the old-package consumer test.

render_manifest follows embedding/store.py::render_json: json.dumps with
ensure_ascii=False, indent=2, allow_nan=False, no sort_keys, then final LF
and UTF-8 encoding. render_papers sorts normalized DOI records and constructs
each dict in PAPER_FIELDS order; json.dumps uses default separators (comma
space, colon space), ensure_ascii=False, allow_nan=False and no sort_keys,
one final LF per record. This matches chunking/output.py's JSONL convention
while explicitly refusing nonfinite numbers. No BOM or newline translation.
The four copied files are never rendered. Sections/chunks count physical
LF-delimited records, allowing a single final empty segment only.

validate_staged_inputs uses staged sections/chunks/vectors/embedding manifest
and original paragraphs/parse report/chunk report/embedding report. It loads
chunk records and exact digest, calls load_sources and validate_chunks with
the existing cap 384 and Utf8BytesDiv3Counter, then validate_embedding_set
with explicit allow_partial=False and norm_tolerance=DEFAULT_NORM_TOLERANCE,
and validate_embedding_structure with exact fields. Retain _validate's
handling of semantic findings versus SourceInputError, including structural
exit 2 precedence. Return a tuple of Finding; SourceInputError and
SourceConsistencyError retain their established classification for callers.
Import validator modules and contract as modules so tests can wrap their
public functions without patching F003 or depending on private bindings.

run_delivery guards aliases before reading inputs or creating output parents;
copies the four payloads; calls that seam; privately reads strict F001 JSONL;
builds papers; invokes each Group A checker over all produced records and
the manifest; re-reads staged artifacts for structure/digest/size/count
agreement; stages the identical committed copy; publishes. T003 performs
these checks itself using Group A/F003 APIs. It never imports a future
delivery/validate.py or reader.py; T005 later wires full consumer validation.

Success stdout is exactly `delivered papers: <n> sections: <n> chunks: <n>
vectors: <n> files: 6` on **one line**, followed by LF; stderr empty. B7
supersedes the earlier generic success `failures: 0` wording for deliver.
All failures use the established Finding aggregation/printing format on
stderr, stdout empty, including deliver usage errors. Phase 2 must handle
deliver parsing errors without changing other commands' behavior.

### Publication and alias protocol to implement in Phase 2

Reserve basenames beginning `.sciscope-delivery-stage-` and
`.sciscope-delivery-backup-` under each destination parent. Current-run stage
and backup names use unique suffixes, on the same filesystem as their own
destination. The package stage is a directory; the committed-copy stage is
a file. Reject either destination or any aliased input that equals or
overlaps a reserved location; check ancestry in both directions after
resolution. Refuse file/symlink output directories before resolving away the
symlink identity. Guard the default cache path as well as the Python API's
explicit cache_dir, without opening the cache. Reject output/copy ancestry
and equality, including an output inside an input file path.

**Crash leftovers: ignore deterministically.** Never enumerate/read/adopt
old reserved siblings as input or as a valid package, never overwrite them
using a reused name, and never remove another run's old artifacts. Only the
requested output path is a package. Tests plant invalid stage/backup siblings
beside both destinations, run twice, and require them unchanged with no new
leftovers. Cleanup removes only this invocation's known stage/backup paths
(best effort), never follows a leftover symlink. Ignoring old artifacts does
not certify the output after a crash: a later deliver rebuilds it; future
validate-delivery detects corruption. No concurrent-writer or power-loss
transaction guarantee is claimed.

With both destinations present, the four forward publication moves are
fixed to os.replace (Path.replace may delegate to it):

1. Move the previous output directory to this run's package backup.
2. Move the complete staged directory to output_dir.
3. Move the previous committed manifest to this run's copy backup.
4. Move the staged committed copy to committed_manifest.

Keep both backups until move 4 succeeds; only then clean them. On a caught
failure restore every moved previous artifact, remove any newly installed
artifact that had no predecessor, and clean current-run temporary artifacts.
An OSError/PermissionError on any forward move becomes output-write-failed.
Tests inject a single failure so rollback operations can succeed; persistent
filesystem denial can prevent restoration or cleanup and is not claimed to
be solvable by Python. For initially absent outputs skip backup moves and
still roll back a package installed before the copy fails. Parent directories
may remain empty after a first-publication failure, but no staging/backup
artifact or partial package may remain.

### Code vocabulary and fixture strategy

Reuse SourceInputError: missing-file, invalid-utf8, invalid-json, wrong-type,
wrong-field-set and established loader field errors. Reuse
SourceConsistencyError codes unchanged. Reuse F003 Finding codes, including
chunk-hash-mismatch, chunk-version-mismatch, chunk-report-mismatch,
chunks-sha-mismatch, partial-set, vectors-size, vectors-sha-mismatch,
report-manifest-mismatch, set-version-mismatch, set-dimensions and all other
existing validator findings; do not translate them to generic delivery codes.
Reuse invalid-usage, output-path-conflict and output-write-failed with B7
statuses. All eight PaperBuildError codes stay unchanged, id report, exit 1.
All contract.check_* codes stay unchanged as produced-record findings,
exit 1. Safe IDs are report, manifest, vectors or lowercase 64-hex IDs only.

New delivery-specific codes:

| Code | Meaning | Exit |
| --- | --- | ---: |
| duplicate-json-key | Duplicate object key in private F001 JSONL parsing | 2 |
| delivery-integrity-mismatch | Final staged re-read disagrees with payload hash/bytes/count descriptors | 1 |
| delivery-failed | Sanitized fallback for an unknown DeliveryError code | 1 |

The DeliveryError allowlist covers delivery's publication/alias/integrity
codes plus its private reader's stable input codes; upstream errors/findings
remain their existing exception/Finding types. Never pass raw exception
text to a diagnostic. Distinguish incoming malformed record (exit 2) from a
Group A structural finding in a produced record (exit 1).

`tests/delivery/package_fixtures.py`, imported as `from package_fixtures
import ...`, creates everything under tmp_path. It borrows the F003 fixture
strategy and reuses the existing pure delivery_fixtures factories, without
imports from tests or new __init__.py files. Two invented DOI-sorted papers
produce three sections (one with zero own paragraphs), two paragraphs, two
real chunks and two two-dimensional fake vectors. Write exact F002-shaped
sources/parse report, load_sources, chunk_sections, write_chunk_files, then
run_embedding with FakeEmbedder, explicit dimensions=2 and a fixed date.
No key/live provider/network. F003's config/provider metadata conventions
are retained; a fake transport does not invent a new manifest provider value.

Metadata order is deliberately reversed; raw EN/en, subjects, empty given
names and Unicode Δ/U+0085/U+2028/U+2029 survive. The cache is populated only
by fixture setup. Delivery tests block sockets from setup onward, instrument
environment reads and forbid cache construction/I/O during deliver. Expected
paper records come from independent SYNTHETIC factories. Full upstream/tree
snapshots detect source changes and leftovers. Move-injection tests first
publish a valid prior package, change metadata, then fail each move; other
refusal tests use six-file sentinel predecessors to detect any replacement.
The symlink privilege probe uses a disposable workspace-local directory and
pytest.mark.skipif, never a platform-name assumption.

### Test inventory and static RED prediction

Counts below are static parameter expansion, **not pytest collection or
execution**. All new test functions live in test_deliver_package.py; the
shared fixture module has no test cases. Each new case must remain RED in
Phase 1 due to a NotImplementedError, missing deliver command/diagnostic
behavior, missing validator orchestration, or the absent ignore rule. Tests
never xfail or catch NotImplementedError as success. The symlink case may be
SKIPPED where privilege is unavailable; state that separately from passes.

| Test group in test_deliver_package.py | Functions | Expanded cases | Expected RED | Expected pass |
| --- | ---: | ---: | ---: | ---: |
| Success/exact manifest; byte copies/papers; two-run identity | 3 | 3 | 3 | 0 |
| Upstream corrupt/hash/partial/truncated/report/version/unreadable/structure | 1 | 8 | 8 | 0 |
| Missing/duplicate DOI on both sides; license mismatch | 1 | 5 | 5 | 0 |
| Strict private JSONL reader, two input sides × six defects | 1 | 12 | 12 | 0 |
| Produced paper/section/chunk/manifest structural findings | 1 | 4 | 4 | 0 |
| Alias/overlap/file/reserved-name matrix | 1 | 13 | 13 | 0 |
| Symlink output, privilege-dependent skipif | 1 | 1 | 1 | 0 |
| Four publication moves × OSError/PermissionError | 1 | 8 | 8 | 0 |
| First-publication rollback; crash leftovers | 2 | 2 | 2 | 0 |
| Staged-source race; staged corruption; staged-path validation | 3 | 3 | 3 | 0 |
| Pure builder/renderers; two nonfinite-renderer cases | 2 | 3 | 3 | 0 |
| Informational real parser digest / alternate checkout | 1 | 1 | 1 | 0 |
| Runtime no-env/transport/cache; static offline/validator guard | 2 | 2 | 2 | 0 |
| Default CLI paths; four-validator orchestration parameters | 2 | 2 | 2 | 0 |
| Usage diagnostics; publication diagnostics; error sanitization | 3 | 6 | 6 | 0 |
| Exact data/delivery/ ignore rule | 1 | 1 | 1 | 0 |
| Total | 26 | 74 | 74 | 0 |
| package_fixtures.py | 0 | 0 | 0 | 0 |

Arithmetic: 3 + 8 + 5 + 12 + 4 + 13 + 1 + 8 + 2 + 3 + 3 + 1 + 2 + 2 + 6 + 1
= **74**. Static AST inspection counts literal parameter arrays without
importing test modules or invoking pytest. The dataclass declarations can be
imported; all five public behavior functions and DeliveryError initialization
raise NotImplementedError. Missing deliver dispatch causes CLI success/status
assertions to fail; even usage cases require the new finding format and fail
against the existing short usage message. The static guard fails on missing
validator calls; .gitignore lacks the exact required rule. These are missing
behavior failures, not collection/import failures by design.

Assuming all user-reported **1638 existing tests remain passing**, predicted
whole suite: **74 failed, 1638 passed** (1712 cases). If symlink privilege is
unavailable: **73 failed, 1638 passed, 1 skipped**. Predicted focused delivery
suite: **74 failed, 710 passed**, or **73 failed, 710 passed, 1 skipped**,
using Group A's 624 contract + 86 paper cases. No new case is expected to pass
in Phase 1; no observed RED is claimed.

### Group B verification

| Check | Observed vs NOT RUN |
| --- | --- |
| Read-only branch/status inspection | Observed branch 004-data-contract-delivery; initially clean working tree |
| Official Python/Microsoft filesystem API research | Observed documentation reads before the new tests; runtime OS behavior NOT RUN |
| Static AST parameter arithmetic and Python syntax parsing | Observed 26 test functions, 74 expanded cases; no test imports or collection |
| Direct .venv/Scripts/ruff.exe check . --no-cache | PASS |
| Direct .venv/Scripts/ruff.exe format --check . | PASS (122 files, including plan.md Python blocks) |
| Direct .venv/Scripts/mypy.exe src | PASS (39 source files, including the new stubs) |
| git --no-pager diff --check | PASS; new Python files also checked for trailing whitespace by static review |
| Final scope diff/status | Only plan.md and the three new T003 files; no existing source/test/doc/data changes, no checkbox changes |
| uv / locked-tool verification | NOT RUN by explicit session constraint; direct tools do not establish locked-tool parity |
| Focused/full pytest, actual fixture execution, observed RED | NOT RUN; Person 1 runs locally |
| Existing 1638 regression cases | User-reported GREEN locally before this change; NOT RUN here |
| Windows/POSIX rollback execution and symlink privilege | NOT RUN; skip outcome unknown |
| Human verification, CI, GREEN or completion | NOT RUN / not claimed |

Person 1 runs these exact PowerShell commands from the repository root:

```powershell
$env:PYTHONPATH = 'src'
uv run --locked python -m pytest tests/delivery -q
uv run --locked pytest -q
uv run --locked ruff check . --no-cache
uv run --locked ruff format --check .
uv run --locked mypy src
git --no-pager diff --check
```

Expected failures are confined to tests/delivery/test_deliver_package.py and
missing T003 behavior, including the future ignore rule. Existing tests are
expected to pass unchanged; Person 1 must verify fixture validity and actual
RED locally. No observed RED/GREEN, CI, human verification or completed task
is claimed. STOP after Group B Phase 1; no Phase 2 work is authorized here.

## Implementation clarifications — Group B, Phase 2

Person 1 authorizes T003 implementation in this session: package.py, an
optional publication-only publish.py, deliver CLI wiring, one ignore rule,
this addendum and the single permitted symlink-probe support change. No
pytest/uv run is authorized in this sandbox. The Phase 1 RED counts remain
predictions; no observed RED result has been supplied in this session.
Apply google-python-engineering; stdlib runtime only, no dependency/lockfile
change. T003 stays unchecked until automated and human verification at T007.

- **P1 Seams.** Call validator functions and `contract.check_*` through module attributes (`chunk_validate.validate_chunks`, `embedding_validate.validate_embedding_set`, ...) and the four publication moves through `os.replace` (module attribute), exactly so the Phase 1 tests' wrappers and failure injection work. Never import a name that bypasses a seam the tests patch.
- **P2 Order of operations** exactly as the addendum: guard aliases (before reading inputs or creating parents) → copy four payloads to the stage → `validate_staged_inputs` on staged copies → strict private JSONL read of F001 files → `build_papers` → render → manifest from validated facts (parser/taxonomy hashes from `parser_source`/`taxonomy_source` bytes) → `contract.check_*` over every produced record and the manifest → re-read staged files and compare hashes/bytes/record counts (`delivery-integrity-mismatch`) → stage committed copy → four moves with rollback.
- **P3 Windows.** Close every file handle before a move; read/write with `Path.read_bytes`/explicit `with` blocks; never `shutil.rmtree` a path this invocation does not own; cleanup is best effort and never raises, never follows a leftover symlink; any OSError/PermissionError becomes the sanitized code `output-write-failed` (exit 1).
- **P4 Sanitization.** No path, record value, prose, key or exception text in stdout/stderr, in `DeliveryError`, or in any code path; unknown exception types map to `delivery-failed` (exit 1).
- **P5 No behaviour added beyond the plan.** No new CLI option, no timestamps, no environment reads, no transport, no cache access, no progress output.

### Implemented structure and static review

package.py keeps the approved public signatures, frozen path/count dataclasses,
pure builder and renderers. It orchestrates byte copying, existing upstream
validation, F001 reading/paper assembly, metadata, Group A checkers and final
integrity checks. The publication protocol is isolated in the allowed
publication-only delivery/publish.py, with private helpers for sibling stages,
closed-handle committed-copy staging, unique backup names, four os.replace
moves, rollback and best-effort cleanup. package.py remains approximately
500 lines; no unrelated logic was moved out or new runtime module introduced.

All validator/checker calls use module attributes; both forward and rollback
moves call os.replace through the os module. The staged-validation seam is
called once; later checks never reread original sections/chunks/vectors to
replace the staged facts. This preserves the Phase 1 source-change wrapper's
meaning: shipped copies are validated even if an original changes afterward.
Final integrity re-reads the six-file inventory, hashes/sizes/physical record
counts, dimensions-based vector rows, source-report descriptors and serialized
manifest, then rechecks produced structures. Payload chunks/vector descriptors
also agree with embedding_set's validated digests. No dependency on future
delivery/validate.py or reader.py; T005 still owns full consumer semantics.

Private F001 JSONL reading splits only LF, rejects duplicate nested keys,
nonstandard constants, floating-point overflow to infinity, malformed JSON
and malformed UTF-8, and discards decoder exception text. Rendering delegates
manifest JSON to the existing render_json convention; papers are DOI-sorted
and rebuilt in PAPER_FIELDS order. The pure builder only copies supplied
validated metadata, with fresh nested mappings; source hashes remain
informational and are never compared to a different checkout.

DeliveryError(code) keeps an allowlisted sanitized code/status and defaults
to one report Finding. Internally aggregated upstream/checker failures carry
their unchanged safe Finding groups in its `findings` tuple, with exit 2 for
structural input errors and exit 1 for semantic/produced-structure failures.
The generic carrier's code stays delivery-failed; CLI prints its specific
trusted Finding groups through the unchanged _print_findings function.
Source reads retain B7's existing missing-file/exit-2 classification; output
staging/move OSError or PermissionError becomes output-write-failed/exit 1.
Unexpected Exception subclasses map to delivery-failed without retaining
their text in diagnostics. Cleanup never masks the original failure.

Static stdlib review found that argparse.ArgumentParser construction invokes
gettext for group/help labels, while add_argument invokes HelpFormatter,
whose default width calls shutil.get_terminal_size. These can inspect locale
and COLUMNS/LINES environment variables even on a successful parse. To meet
B8 and test_no_environment_transport_or_cache, main routes only an exact
leading deliver token through a private parser for the twelve B10 long
options. It accepts separated or equals-form values and retains last-value
semantics for repeated options; unknown/missing arguments produce only the
invalid-usage Finding. Help is static text from the same twelve-option table,
without terminal/locale probes. The existing argparse parser also registers
deliver for root command help. Other command dispatch, argument parsing,
diagnostics and _validate are unchanged. No new option is introduced.

Crash leftovers retain the approved deterministic ignore rule: never scan,
adopt or remove old reserved siblings. Track and clean only this invocation's
paths. Keep both predecessors until the committed-copy installation succeeds;
on a single injected failure restore both independently. If persistent OS
denial prevents restoring a backup, preserve that surviving backup rather
than delete the last predecessor. This is the already documented best-effort
limit, not a power-loss or concurrent-writer transaction claim.

The sole test-support edit is
tests/delivery/package_fixtures.py::symlinks_supported: remove dir=REPO from
TemporaryDirectory so collection uses the default system temp directory and
creates no probe directory in the repository. No test assertions, fixtures
outside that function, case inventory or parameter counts were changed.
The sole .gitignore edit adds data/delivery/ beside the other data/ rules.

### Deviations and TEST ISSUES

No deviation from the approved T003 behavior is identified by static review.
The dedicated deliver parser is an implementation choice required by the
no-environment rule; the code evidence is the Python 3.12 stdlib functions
listed above. The permitted publication module contains only that protocol.
TEST ISSUES: **none identified by static review**. Tests and fixtures were
not executed, so their runtime validity and GREEN outcome remain unverified.
No tests were weakened or changed to accommodate implementation.

### Phase 2 verification and predicted outcomes

| Phase 2 check | Observed result or explicit limit |
| --- | --- |
| Direct .venv/Scripts/ruff.exe check . --no-cache | PASS |
| Direct .venv/Scripts/ruff.exe format --check . | PASS (123 files, including Markdown Python blocks) |
| Direct .venv/Scripts/mypy.exe src, configured strict | PASS (40 source files) |
| git --no-pager diff --check | PASS |
| Static AST syntax/whitespace, validator calls and offline package guard | PASS; no NotImplementedError remains in package/publication code; no test imports or delivery execution |
| Scope diff | Only package.py, new publish.py, CLI deliver wiring, one .gitignore rule, this addendum and the permitted symlink-probe line |
| Focused pytest / both whole-suite entry points / fixture execution | NOT RUN; Person 1 runs locally |
| uv / locked-tool parity, Windows/POSIX moves, symlink privilege | NOT RUN; direct tools do not establish locked-tool or runtime parity |
| Human verification, CI, T003 completion | NOT RUN / not claimed; checkbox unchanged |

Expected, **not observed**: all **74** Group B cases turn GREEN and all
**1638** prior cases remain passing. Focused tests/delivery: **784 passed**,
or **783 passed, 1 skipped** if symlink privilege is unavailable. Either
whole-suite entry point: **1712 passed, 0 failed**, or **1711 passed,
1 skipped, 0 failed** on Windows without symlink privilege. These counts
assume the user-reported prior GREEN baseline and successful fixture execution;
no pytest collection, observed RED/GREEN, CI or human acceptance is claimed.

Person 1 runs these exact PowerShell commands from the repository root:

```powershell
$env:PYTHONPATH = 'src'
uv run --locked python -m pytest tests/delivery -q
uv run --locked pytest -q
uv run --locked python -m pytest tests -q
uv run --locked ruff check . --no-cache
uv run --locked ruff format --check .
uv run --locked mypy src
git --no-pager diff --check
```

Stop after this Group B Phase 2 scope. No commit/push, completion checkbox,
EVIDENCE.md or PROJECT_TODO.md changes; T004–T006 are not implemented.

## Implementation clarifications — Group C (T004)

Person 1 authorizes **Phase 1 only** on 2026-11-17: new validate.py interface
stubs, tests/delivery/test_deliver_structure.py, and this appended addendum.
Spec/plan approval and Group A/B GREEN (1711 passed, 1 skipped on Windows)
are user-reported; they were not rerun here. The later session authorization
supersedes historical planning-only statements above. No implementation,
GREEN, existing source/test/fixture/schema/doc/data changes, checkbox change,
evidence/backlog update, commit or push. The explicit run restriction leaves
EVIDENCE.md and PROJECT_TODO.md untouched. Person 1 runs RED locally.

The following S1–S9 decisions are recorded verbatim from this session:

- **S1 Scope split.** T004 = everything checkable per file or per descriptor without joining records across files: inventory, decoding, per-record structure, descriptor facts, report descriptors, purity, partial-set marker, vector-file size shape. T005 (not now) = cross-record semantics (foreign keys, parents, digests inside locators, hashes of text, chunk ids, version equality across records/reports, count comparison against report contents, reuse of F003 vector/set validators) and the `validate-delivery` CLI. Do not implement or test T005 checks; do not call F003 validators here except what is listed below.
- **S2 API in `src/sciscope/delivery/validate.py`** (finalize names in plan.md): a frozen `LoadedPackage` (raw bytes of the six files, parsed records per file, parsed manifests; only for files that parsed), a `PackageReports` input (paths of the three repository reports: `parse_report.json`, `chunk_report.json`, `embedding_report.json`; read as bytes for descriptor comparison only), `load_package(package_dir) -> tuple[LoadedPackage, list[Finding]]`-style loader and `check_package_structure(...) -> StructureOutcome` where `StructureOutcome` carries `findings: tuple[Finding, ...]`, `structural: bool` (True when any structural finding exists → T005/CLI will use exit 2) and the `LoadedPackage` for reuse by T005 so nothing is parsed twice. All checks are independent and collected; one failing file never hides findings about the others; nothing raises for corrupt input. Never modify the package.
- **S3 Safe IDs.** A delivery finding collector (new class in `validate.py`, not a change to F003) whose allowed IDs are only: the six fixed package basenames, the three fixed report basenames, `manifest`, `vectors`, `report`, and lowercase 64-hex. Anything else is shown as `report`. Counting unit = (file, record index). Output format later is the existing `error: <code> count: <k> first: <ids>` / `failures: <n>`; here you only produce `Finding` objects. No value, prose, path or exception text may ever reach a `Finding`.
- **S4 Inventory (structural).** Exactly the six regular files `papers.jsonl`, `sections.jsonl`, `chunks.jsonl`, `vectors.f32`, `embedding_manifest.json`, `delivery_manifest.json`; anything else is a finding: `delivery-missing-file`, `delivery-extra-file` (including nested directories, hidden files and leftover `.sciscope-delivery-*` entries), `delivery-not-regular-file` (directory/symlink/other at a fixed name; never follow symlinks). The three repository reports must exist and be regular files (`delivery-missing-file`, id = its basename). Missing/extra/non-regular = structural. Symlink tests use `pytest.mark.skipif` when symlinks cannot be created.
- **S5 Decoding (structural).** Strict UTF-8 without BOM (`invalid-utf8`), strict JSON (`invalid-json`: malformed, NaN/Infinity/-Infinity, finite-looking overflow such as `1e999`, nesting-depth/recursion errors), duplicate object keys at any depth (`duplicate-json-key`), JSONL split ONLY on LF (never `splitlines()`; raw U+0085/U+2028/U+2029 inside strings must survive), a single final empty segment allowed, interior blank lines rejected (`invalid-json`), an empty JSONL file is allowed to parse (emptiness is a T005 count matter) but `delivery_manifest.json` and `embedding_manifest.json` must be single JSON objects. Reuse the private strict reader ideas from `package.py` (do not import private names; extract or re-implement behind a public helper in `validate.py` and record the choice; if you move code out of `package.py`, say so in plan.md and keep its tests green).
- **S6 Per-record structure (structural).** Run `contract.check_paper/check_section/check_chunk` on every JSONL record, `check_embedding_manifest` on `embedding_manifest.json` and `check_delivery_manifest` on `delivery_manifest.json`; each non-empty code tuple becomes a finding whose code is the contract code unchanged (e.g. `paper-bad-pattern`), unit = (file, index), id = file basename. A non-object JSONL line produces `<entity>-bad-type`.
- **S7 Descriptor facts (semantic, exit-1 class).** Using the parsed `delivery_manifest.json`: for each of the five payload descriptors compare sha256, bytes and record_count with the actual file (record_count = LF-delimited records for JSONL, vector rows for `vectors.f32` = bytes / (4 × `embedding_set.dimensions`), 1 for the embedding manifest) → code `delivery-integrity-mismatch`, id = the file basename; compare `counts` with the three JSONL record counts → `delivery-count-mismatch`; compare each `source_reports` descriptor (sha256, bytes) with the repository report file → `source-report-mismatch`, id = report basename; compare `embedding_set.chunks_sha256` and `vectors_sha256` with the actual SHA-256 of `chunks.jsonl`/`vectors.f32` → `delivery-integrity-mismatch`; vector file shape: `vectors.f32` size must equal `record_count × dimensions × 4` and be a multiple of 4 → `vectors-size` (existing F003 code name, id `vectors`). These run only when the manifest structure is valid.
- **S8 Partial-set marker and purity.** `embedding_manifest.status == "partial"` → `partial-set` (existing code, id `manifest`). Delivery-manifest purity as a runtime-only rule (NOT in the schema, so schema/runtime parity is unaffected; document it): every string value in `delivery_manifest.json` other than hex digests must be a short token (≤ 128 chars), without control characters, without whitespace and not path-like (no backslash, no leading `/`, no drive prefix, no `..`), except `passage_prefix` and `query_prefix`, which may contain spaces but no control characters and are ≤ 64 chars. Violations → `delivery-manifest-impure`, id `manifest`. State plainly in plan.md that this detects prose/paths structurally and is not a secret scanner.
- **S9 Parity at file level.** For every shared `MUTATIONS` case of entity paper/section/chunk/embedding_manifest/delivery_manifest EXCEPT the DOCUMENTED-C3 cases: build a valid package (use the real `run_delivery` on `package_fixtures.make_tree`, which is GREEN), apply the mutation callback to the first real record of the corresponding file (or to the whole manifest), rewrite the file, and assert that structure findings with that entity's code prefix exist iff `not mutation.runtime_accepts`; also assert the same verdict through the local-`$ref` jsonschema validator on that mutated real record (so schema, runtime and file-level validator agree). Hash/count findings caused by rewriting are ignored for this comparison. Mutations only touch fields whose paths exist in the real record; if a path does not exist in the real record, say so in plan.md and handle it explicitly (do not silently skip).

### Brief renewed solution-research before tests

Problem: independently load potentially corrupt package files, retain exact
bytes/parses for T005, and collect safe file-level findings using the approved
contract. Decisions S1–S9 resolve the task boundary; no new requirement or
dependency is proposed. Relevant existing code inspected: contract/papers/
package/publish, chunking Finding/collector/strict readers/is_json_* helpers,
embedding validation, the shared corpus and the Group A/B tests/fixtures.

| Approach | Verified facts, tradeoff, recommendation |
| --- | --- |
| Public stdlib decoder in validate.py; reuse public contract.check_* | Recommended. Python 3.12 JSON exposes object_pairs_hook, parse_constant and parse_float; its defaults accept repeated keys and nonfinite constants. Explicit hooks plus finite-float rejection are necessary. Reimplement the small private package.py reader ideas behind public decode_json; retain package.py unchanged under this run's scope. Small duplication avoids importing private producer functions and preserves all existing tests. No added package/license obligation. |
| Reuse F003 strict readers unchanged | Existing readers sanitize failures and split JSONL on LF, but reject at the first file and lack nested duplicate-key and overflow rejection. Reuse Finding and public contract predicates/checkers; do not call F003 vector/set validators in T004. |
| Add runtime jsonschema | Existing dev jsonschema supports Draft202012Validator/check_schema and local references. It does not replace decoding, byte integrity or inventory checks; conflicts with approved stdlib runtime. Keep dev-only, no install/version change. |

Official sources read before these new tests: [Python 3.12 JSON](https://docs.python.org/3.12/library/json.html),
[Python 3.12 pathlib](https://docs.python.org/3.12/library/pathlib.html), and
[jsonschema validation](https://python-jsonschema.readthedocs.io/en/stable/validate/).
The first two sources are specifically the project Python 3.12 documentation;
the unversioned Python URLs redirected to 3.15 and were not used to infer
3.12-only API support. pathlib documents lstat/is_symlink and file-type queries;
never infer regular-file safety from is_file alone because it follows links.
jsonschema documentation identifies release 4.26.0; existing research.md records
its MIT license/Python floor. No renewed release/license/security audit or
installed-version verification was performed. Repository compatibility is
Python >=3.12,<3.13 and the existing dev dependency jsonschema >=4.23,<5;
no new runtime dependency. Actual decoder/filesystem behavior is NOT RUN.
This brief check is kept in the authorized plan addendum; research.md stays
unchanged. No essential unresolved decision blocks the Phase 1 stubs/tests.

### Final interfaces and collection policy

All behavior bodies in the new validate.py raise NotImplementedError.
Only frozen, slotted dataclasses and interface declarations exist; no file
validation is implemented. Types use collections.abc.Mapping and pathlib.Path:

```python
@dataclass(frozen=True, slots=True)
class LoadedPackage:
    raw_files: Mapping[str, bytes]
    records: Mapping[str, tuple[object, ...]]
    manifests: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class PackageReports:
    parse_report: Path
    chunk_report: Path
    embedding_report: Path


@dataclass(frozen=True, slots=True)
class StructureOutcome:
    findings: tuple[Finding, ...]
    structural: bool
    loaded: LoadedPackage


class DeliveryFindingCollector:
    def __init__(self) -> None: ...

    def add(
        self, code: str, identifier: str, unit: tuple[str, int]
    ) -> None: ...

    def findings(self) -> list[Finding]: ...


def decode_json(data: bytes) -> tuple[object, tuple[str, ...]]: ...


def load_package(package_dir: Path) -> tuple[LoadedPackage, list[Finding]]: ...


def check_package_structure(
    package_dir: Path,
    reports: PackageReports,
    *,
    loaded: LoadedPackage | None = None,
    load_findings: tuple[Finding, ...] = (),
) -> StructureOutcome: ...
```

raw_files retains successfully read fixed-file bytes, even if decoding fails.
records maps each fully decoded JSONL file to its ordered records; a corrupt
file is absent, whereas a successfully parsed empty file has an empty tuple.
manifests retains successfully decoded manifest values, including non-object
roots so the public contract checker can report its unchanged bad-type code.
No fabricated parse result replaces a failed file. Frozen dataclasses freeze
their fields; they do not promise transitive immutability of decoded objects.
The validator must not mutate them or the package.

load_package collects six-file inventory/decoding findings only. The combined
checker calls it exactly once when loaded is None; supplied loaded and
load_findings are reused unchanged, with outcome.loaded preserving identity.
Reports are read only by the combined checker as bytes, never decoded or
parsed in T004. Package/report symlinks are refused before opening; dangling
links at fixed package names are nonregular rather than missing. Nonregular
reports use delivery-missing-file per S4. Unknown extra basenames map to report;
extra directories count as one inventory entry and are not traversed.

decode_json returns (value, ()) on success, including (None, ()) for JSON null;
failure returns (None, (safe_code,)). It must reject a UTF-8 BOM as invalid-utf8,
use nested duplicate-key detection and reject both constants and parse_float
overflow. No exception/value text is retained. Recursion failures are invalid-json.
LF-only splitting removes at most one final empty segment; CR is retained and
accepted only where JSON permits it as whitespace. Empty JSONL decodes without
a structural finding; S7 may still report its descriptor/count disagreement.
The loader independently attempts every other file when one file fails.

S6 collects every returned contract code separately, unchanged, once per
(file, zero-based record index) for that code. File-level checks/manifests use
index 0; descriptor and embedding_set digest mismatches for the same payload
deduplicate under that payload's unit. Multiple bad fields in a record never
inflate the unit count. DeliveryFindingCollector sorts codes, counts distinct
units, and retains at most three distinct safe IDs in encounter order.
Its code allowlist is the complete vocabulary below; unknown caller codes
become invalid-json and unknown IDs become report. Unit strings never become
display identifiers. Each allowed basename/token/digest is tested independently
so truncating to three IDs cannot hide accidental masking.

S7 runs only after contract.check_delivery_manifest returns no codes; byte
facts for available files remain checkable even when their content is corrupt.
Never divide by invalid dimensions or infer vector rows from chunk order.
vectors-size is semantic under S7 despite detecting binary shape; partial-set
is semantic too. No vector finiteness, norms, embedding-entry joins or F003
validator calls occur in T004. Purity is structural: it detects prose/paths
structurally and **is not a secret scanner**. It is runtime-only, absent from
DATA_CONTRACT.json and excluded from entity-prefix parity verdicts. Control
characters include C0/DEL/C1 (Unicode Cc); ordinary token whitespace is checked
with Unicode whitespace semantics. Prefixes use their <=64/no-controls rule.
Digest strings remain exempt; existing real 64-hex fields are exercised by
the valid-package test. Valid 128-character ordinary tokens are accepted.

### Complete code vocabulary and precedence

No printing or CLI is added. structural is True iff at least one structural
finding exists, including when semantic findings coexist; semantic-only
findings leave it False. T005 later maps that precedence to exit 2 vs exit 1.

| Codes | Origin | Class / safe ID |
| --- | --- | --- |
| delivery-missing-file | New delivery inventory/report code | Structural; fixed package/report basename |
| delivery-extra-file | New delivery inventory code | Structural; report for arbitrary extra entry names |
| delivery-not-regular-file | New delivery inventory code | Structural; fixed package basename |
| invalid-utf8, invalid-json | Reused strict-reader code names | Structural; fixed package basename; collector unknown-code fallback uses invalid-json |
| duplicate-json-key | Reused Group B decoder code name | Structural; fixed package basename |
| paper-{missing-field,extra-field,bad-type,bad-value,bad-pattern} | Reused Group A codes unchanged | Structural; papers.jsonl |
| section-{missing-field,extra-field,bad-type,bad-value,bad-pattern} | Reused Group A codes unchanged | Structural; sections.jsonl |
| chunk-{missing-field,extra-field,bad-type,bad-value,bad-pattern} | Reused Group A codes unchanged | Structural; chunks.jsonl |
| embedding_manifest-{missing-field,extra-field,bad-type,bad-value,bad-pattern} | Reused Group A codes unchanged | Structural; embedding_manifest.json |
| delivery_manifest-{missing-field,extra-field,bad-type,bad-value,bad-pattern} | Reused Group A codes unchanged, including nested embedding_set errors | Structural; delivery_manifest.json |
| embedding_set-{missing-field,extra-field,bad-type,bad-value,bad-pattern} | Existing standalone Group A checker vocabulary accepted by collector | Structural; reserved for standalone callers, not emitted by S6 file checks |
| delivery-manifest-impure | New runtime-only purity code | Structural; manifest |
| delivery-integrity-mismatch | Reused Group B code | Semantic; affected payload basename |
| delivery-count-mismatch | New delivery count code | Semantic; affected JSONL basename |
| source-report-mismatch | New descriptor code | Semantic; report basename |
| vectors-size | Reused F003 code name, no F003 call | Semantic; vectors |
| partial-set | Reused F003 code name, no F003 call | Semantic; manifest |

The brace notation expands to five literal suffixes per entity, not a new
code containing braces. No T005 foreign-key/hash/version/report-content or
vector-value codes belong to this phase. All six fixed package basenames,
all three report basenames, manifest/vectors/report and lowercase 64-hex
are the only allowed display IDs. No source path, record value or exception
message may reach a Finding.

### Synthetic test inventory and static predictions

All 38 test functions are in the new test_deliver_structure.py. Tests use
neighboring imports only, reusing both delivery_fixtures and package_fixtures;
no fixture module is added or changed. Setup calls make_tree then the real
GREEN run_delivery. Sockets are blocked before setup. Text is invented and
labeled SYNTHETIC; no real article prose, credentials or paid calls.

| Test group | Functions | Expanded cases | Expected RED | Expected pass |
| --- | ---: | ---: | ---: | ---: |
| Valid package, exact retained bytes/parses, unchanged tree | 1 | 1 | 1 | 0 |
| Missing package/report files; extras; directory at each fixed name | 3 | 23 | 23 | 0 |
| Symlink matrix in one privilege-dependent skipif case | 1 | 1 | 1 or skipped | 0 |
| Per-text-file decoding matrix (5 x 10) | 1 | 50 | 50 | 0 |
| Public decoder failures and valid/null/Unicode values | 2 | 14 | 14 | 0 |
| Interior blanks; final endings; CRLF rows; extra LF/CR-only; raw controls | 5 | 35 | 35 | 0 |
| Unicode separators in every text kind; empty JSONL; manifest object roots | 3 | 16 | 16 | 0 |
| Non-object records; every record counted; checker code passthrough | 3 | 35 | 35 | 0 |
| Each payload descriptor field (5 x 3) | 1 | 15 | 15 | 0 |
| Each report descriptor field (3 x 2); opaque report bytes | 2 | 9 | 9 | 0 |
| Manifest counts; two embedding_set digests; three vector shape defects | 3 | 8 | 8 | 0 |
| Partial-set marker | 1 | 1 | 1 | 0 |
| Purity (2 nested locations x 13); prefixes (2 x 5); token/digests | 3 | 37 | 37 | 0 |
| Independent failures/retained parses; invalid-manifest S7 gating | 2 | 2 | 2 | 0 |
| Collector safety/unit deduplication; every allowed ID; file/index units | 3 | 15 | 15 | 0 |
| Successful and failed loader-result reuse | 2 | 2 | 2 | 0 |
| No environment/cache/XML/paragraph/source access, F003 calls or writes | 1 | 1 | 1 | 0 |
| File/schema/runtime parity on emitted records | 1 | 219 | 219 | 0 |
| Total | 38 | 484 | 484, or 483 plus 1 skipped | 0 |

Arithmetic: 1 + 23 + 1 + 50 + 14 + 35 + 16 + 35 + 15 + 9 + 8 + 1 + 37
+ 2 + 15 + 2 + 1 + 219 = **484**. These are static parameter expansions,
not pytest collection or observed RED. A read-only AST/constant expansion
evaluated the existing pure fixture corpus and test parameter expressions;
it did not import the new test module, run delivery/fixtures with filesystem
I/O, invoke pytest, or execute a test. No test catches NotImplementedError,
xfails, or treats missing behavior as success. Every nonskipped new case
calls a new stub before behavioral assertions, so its expected failure is
NotImplementedError rather than missing imports or assertion-based GREEN.
Symlink support is checked with the existing disposable-temp probe; one new
case loops over six package links, three report links, and extra/dangling
links. No platform-name assumption or existing fixture change is made.

S9 selects **219** cases: paper 35, section 26, chunk 47,
embedding_manifest 35, delivery_manifest 76. Standalone embedding_set cases
remain covered by Group A; nested set mutations in delivery_manifest are
included here. DOCUMENTED-C3 integral-float cases are explicitly excluded.
The parity test compares only the entity's unchanged structural-code prefix
to the tagged runtime verdict; other descriptor/count/purity/partial findings
do not affect that comparison. It also calls the real runtime checker and a
Draft202012Validator with local references on that same mutated real record.

Mutation path review: all pre-existing target paths are present in the first
emitted records (nonempty authors/spans/entries and all manifest children).
There are **12 intentionally absent final keys**, representing extra-field
mutations, not missing fixture data: extra-field for each of the five entities;
chunk span-extra; delivery files-extra-SYNTHETIC-extra.json and
files-extra-delivery_manifest.json; delivery source-reports-extra and
processing-parser-extra-key; embedding entry-extra-field and usage-extra-field.
Their enclosing paths exist; apply inserts the new key and the test asserts
rejection. Nothing is skipped or redirected to a factory. All other callbacks
replace/remove existing fields. The static closure-path check confirmed all
parent paths on the shared factory shapes; actual emitted-record execution
is explicitly NOT RUN. The real fixture writers were reviewed for matching
field shapes. KeyError or another setup error during Person 1's run would
be a test issue requiring correction, never accepted as meaningful RED.

Expected whole suite with symlink privileges available: **484 failed,
1712 passed** (2196 cases). On the user-reported Windows baseline without
symlink privilege: **483 failed, 1711 passed, 2 skipped**. The two skips are
the unchanged existing Group B case and this new Group C case. Thus all
existing 1712 cases retain their expected outcome (1711 pass + 1 skip).
If the new probe succeeds while retaining that recorded baseline, prediction
is **484 failed, 1711 passed, 1 skipped**. Focused tests/delivery prediction:
**484 failed, 784 passed**, or **483 failed, 783 passed, 2 skipped** without
symlink privilege. These are conditional predictions only; failures must be
confined to test_deliver_structure.py and due only to NotImplementedError.

### Verification and exact local handoff commands

| Check | Observed vs NOT RUN |
| --- | --- |
| Initial branch/status | Observed 004-data-contract-delivery, initially clean |
| Repository/artifact/code inspection and renewed official-source check | Observed before new tests; no new dependency or schema change |
| AST syntax/constant case arithmetic and pure mutation-path review | Observed 38 functions, 484 cases, 219 parity cases; no test execution/collection |
| Direct .venv/Scripts/ruff.exe check . --no-cache | PASS; initial new-file lint issues corrected before final check |
| Direct .venv/Scripts/ruff.exe format --check . | PASS (125 files, including Markdown Python blocks) |
| Direct .venv/Scripts/mypy.exe src | PASS (41 source files, including the new interface stubs) |
| git --no-pager diff --check and final scope | PASS; only appended plan.md plus new validate.py and test_deliver_structure.py; no existing source/test/schema/doc/data or checkbox changes |
| uv / locked-tool parity | NOT RUN by explicit sandbox/run constraint |
| Focused/full pytest, actual make_tree/run_delivery execution, observed RED | NOT RUN; Person 1 runs locally |
| Existing 1712 cases | User-reported 1711 passed, 1 skipped on Windows before change; NOT RUN here |
| Symlink probe/test execution, CI and human verification | NOT RUN; no actual platform skip count claimed |
| GREEN, T004 completion, implementation | Not claimed / intentionally absent; all checkboxes unchanged |

Person 1 runs these exact PowerShell commands from the repository root:

```powershell
$env:PYTHONPATH = 'src'
uv run --locked python -m pytest tests/delivery -q
uv run --locked pytest -q
uv run --locked ruff check . --no-cache
uv run --locked ruff format --check .
uv run --locked mypy src
git --no-pager diff --check
```

STOP after Group C Phase 1. No Phase 2 behavior or T005 work is authorized.
