# Implementation Plan: Section-aware chunking and embeddings

**Branch**: `003-chunking-embeddings` | **Date**: 2026-11-15 | **Spec**: [spec.md](spec.md)
**Status**: Approved by Person 1, 2026-11-15, subject to A-E; implementation not started

## Summary and technical context

Build F002 paragraph-derived section chunks, then an explicitly selected embedding run for the 17-paper pilot (P2-11..P2-19). Python 3.12, standard library runtime, pytest/ruff/mypy development tools, local JSONL and binary files. Inputs are `data/processed/pilot/{sections,paragraphs}.jsonl` and F001 manifest; output is ignored `data/processed/pilot/chunks.jsonl` and `data/embeddings/pilot/` plus small committed `data/pilot/{chunk,embedding}_report.json`. No new dependency or `uv.lock` change under the recommended design. CI uses fake transport only. Person 1 owns data processing and embeddings; Person 2 reviews the F004 handoff contract. Scale: 17 papers, 319 sections, 585 paragraphs; larger-corpus performance is deferred.

## Constitution check and project structure

Research preceded specification; Person 1 approved this plan and spec subject to corrections A-E, now recorded here. All code tasks begin with labeled synthetic RED behavior tests and a renewed `$solution-research` check. No paid calls in tests/CI; live calls require explicit selection. Source provenance and deterministic processing are required. Person 2 contract review precedes F004 integration. Final human verification and evidence precede task completion.

Planned layout: `src/sciscope/chunking/{__init__,config,counter,split,core,report}.py`, `src/sciscope/embedding/{__init__,config,inputs,provider,openai_client,cache,store,pipeline}.py`, `src/sciscope/pipeline/cli.py`; unique `tests/chunking/test_chunk_*.py` and `tests/embedding/test_embed_*.py`. F002 `src/sciscope/jats/{locator,parser,source,cli}.py` remains unchanged under Option A. Feature directory contains only `spec.md`, `plan.md`, `tasks.md`, `research.md`. No data-model, quickstart, contracts or checklist files.

## Decisions for Person 1 (R1–R9)

| ID | Recommendation | One-line reason | Alternatives | Cost / approval impact |
| --- | --- | --- | --- | --- |
| R1 HTTP | Standard-library `urllib` behind an injectable transport. | One endpoint and explicit offline/retry behavior. | Official `openai` SDK. | No lock/CI delta; SDK would need optional group, `uv.lock` refresh and CI install/test changes, justified separately. |
| R2 counter | `TokenCounter` interface, versioned B3 = ceil(UTF-8 bytes/3), configurable provisional operational cap 384 estimated input tokens (25% below the absolute ceiling of 512); compare live aggregate usage to estimates. | B3 is 33.7% above C4 on this pilot and needs no vocabulary fetch. | C4; `tiktoken` with explicit approval. | B3 has no true-model bound. `tiktoken` would change lock/CI and require preseeded offline vocabulary; see [loader](https://github.com/openai/tiktoken/blob/main/tiktoken/load.py). |
| R3 content | Option A: paragraph chunks only; explicit policy/counts, caption handling as named follow-up after Golden v0. **Option A approved by Person 1, 2026-11-15.** | Every chunk can be reconstructed from F002 paragraphs, as required. | Option B: A plus separate `figure_caption`/`table_caption` chunks owned by enclosing section, locators to `fig`/`table-wrap` via minimal F002 `_TARGET_KINDS` extension; table cells excluded. | A: 0 F002 files, one policy task, no hash risk. B: at least `jats/locator.py` and tests, caption extractor and contract changes within T003, source cannot be reconstructed from `paragraphs.jsonl`, higher review risk; existing F002 outputs/hashes must remain identical. Requires changing FR-003 explicitly. |
| R4 template | `embedding-text-v1`: non-synthetic section path joined with ` > `, then `\n\n`, then verbatim chunk text; no paper title. Prefix prepended exactly as configured. | Heading context without repeating the long title; exact input hash invalidates cache on any template change. | Title-bearing `embedding-text-v2` candidate after Golden v0; no heading. | Small implementation; title would increase overhead and cost. Empty path gives just chunk text. |
| R5 packing | Greedy in-section packing toward 200–350 B3 content tokens, no overlap; split oversize paragraphs at tested sentence boundaries; hard split oversize sentence at character offset and flag it. | Survey shows 194 paragraphs >350 B3 and 65 >512 B3. | Fixed characters; third-party splitter. | One splitter/core task; must retain whitespace and exact [start,end) spans. Soft minimum 50; merge orphan only within same section and cap, else leave short. |
| R6 IDs | `chunk_id` = SHA256 of `chunking_version`, section ID, ordinal and ordered span locators/offsets (canonical UTF-8 fields); embed version in record. | Stable reruns and IDs change on boundary/version changes. | Section ID + ordinal alone; text hash. | One output task; text hash separately detects content changes. |
| R7 storage | Atomic cache entry per input hash (JSON metadata plus little-endian float32 vector), atomic final `vectors.f32` and JSON manifest/index. Ask API for `encoding_format=float`. | Cheap stdlib, deterministic ordered output and crash resume; validate before cache use. | Append-only cache; JSONL vectors; `base64` response. | File-per-entry overhead is acceptable for pilot; float32 quantization requires empirical norm tolerance. Base64 could reduce transfer but needs explicit decode/integrity checks. |
| R8 CLI | `python -m sciscope.pipeline.cli {chunk,embed,validate}`, `embed --dry-run`, `--limit N` and explicit `--live --provider openai`; return 0/1/2. | Separates offline preview from paid call and matches F002 statuses. | Split module CLIs. | One shared CLI plus offline tests. Defaults never create a transport or require key. |
| R9 tasks | T001–T008 in `tasks.md`; serial small scopes, last is human verification/evidence/doc sync. | Covers P2-11..P2-19 at eight tasks. | Split F003a chunking / F003b embeddings if T003 caption option or implementation review makes scope too large. | Option A fits proposed budget; Option B risks overrun and needs a new approved spec/plan or split. |

## Non-paragraph content policy

| Kind | Option A recommended | Option B alternative |
| --- | --- | --- |
| References and acknowledgments | Exclude by policy, count from F002/back report | Same |
| Figure/table captions | Exclude by policy, count 82/39, named follow-up | Separate caption chunks, enclosing section owner, `chunk_kind` and extended v1 target set |
| Table bodies/cells | Exclude, count 39 table wraps | Same |
| Lists, formulas, supplementary material, boxed text | Exclude, count by kind, including zero | Same |

Nested-section paragraphs remain included only in their own section. F002 skip counts (fig 82, table-wrap 39, supplementary-material 91, disp-formula 9, list 1, inline-formula 1) are the public baseline; raw XML survey counts differ where elements are nested or outside emitted scope. No silent conversion of omitted content into paragraph text. Caption extraction, if approved later, must use F002's XML safety gate and retain original F002 output hashes.

## Implementation clarifications

**Group C Phase 2 (2026-11-17):** Implement T005 before T006 using the
approved D1–D12 contracts and no new dependency or external verification.
The Windows ignore-test repair passes bytes to `git check-ignore --stdin`
and decodes stdout explicitly, avoiding CRLF translation. The live guard
precedes path/environment access; paths resolve before key lookup, and key
validation precedes cache writes while transport creation remains lazy.
A single final input exceeding the per-request token budget also fails as
`input-over-cap` before cache writes, since it cannot form a valid batch.
Base URL normalization lowercases the hostname, removes the default HTTPS
port and trailing slashes. Cache batch consistency is checked across
referenced entries within a model/dimension namespace; failed writes restore
the in-memory accounting registry, preserving individually committed files
for resume. Escaped lone surrogates are invalid chunk record values because
final inputs must be strict UTF-8. The UTC provider stamps each successful
batch; set dates and totals are recomputed from referenced cache metadata.
No T007 validation/norm-tolerance/dry-run work or task ticks are included.

**Group C Phase 1 (2026-11-17):** Person 1 supplied final D1–D12 decisions
for T005 then T006: typed contracts and labeled synthetic offline RED tests
only; behavior remains `NotImplementedError`, with real constants,
dataclasses, Protocols and sanitized exception classes. No task completion,
live run, evidence/backlog sync, dependency/config/ignore change, T007 work,
or chunking/JATS/acquisition behavior change is authorized in this phase.
The starting branch is `003-chunking-embeddings`, HEAD `e44e094`.

Renewed `$solution-research` and `$google-python-engineering` were applied
before feature tests. **Local-only research:** inspected the existing B3
counter, public `build_embedding_text`, `CHUNK_RECORD_FIELDS`, LF-only loader
semantics, public atomic `write_outputs`, CLI and offline test guard. Compared
reuse through these public contracts, an independent serializer/publisher,
and SDK integration. Reuse plus an injected stdlib transport preserves the
zero-runtime-dependency contract and rollback behavior; duplicate publication
logic adds integrity risk, and an SDK needs an unapproved dependency change.
The Official OpenAI facts and links in `research.md` are prior planning
evidence only: **no external fact, version, license, compatibility, current
price, API limit, or account observation was reverified**; no network is
authorized. This Phase 1 does not claim the live verification gates passed.

- **D1 — layout:** Add `inputs.py` to the embedding package for the public
  reusable reader. T005 uses `test_embed_provider.py` and the additional
  `test_embed_transport.py`; T006 adds `test_embed_store.py` and
  `test_embed_pipeline.py`. Shared synthetic helpers are `embed_fixtures.py`;
  `conftest.py` blocks both `urllib.request.urlopen` and
  `socket.socket.connect`. Test filenames are unique across `tests/`.
- **D2 — CLI:** `embed --live --provider openai`; only `openai` is a CLI
  provider. The library fake can never be selected to publish CLI outputs.
  Validate arguments/config, then reject missing `--live` with exit 2,
  `live-not-selected`, before any file/environment access or transport
  construction. Resolve paths before reading; an output aliasing another
  output, the chunk input, or the cache directory is `output-path-conflict`
  (2). Defaults: pilot chunks, cache/vectors/manifest under
  `data/embeddings/pilot/`, report `data/pilot/embedding_report.json`, small
  model, dimensions 1536, empty prefixes, cap 384, request count/token limits
  8/2048, attempts 3; optional positive `--limit N`. Config/input/chunk config
  errors exit 2; provider/cache/write errors exit 1; success exits 0.
  Stderr is only `error: <code>` and, for corrupt cache,
  `entry: <64-hex key>`; OSError maps to `output-write-failed`.
- **D3 — provider:** Runtime-checkable `Embedder` exposes provider/model/
  dimensions and both embedding methods. Results contain input-ordered tuple
  vectors, prompt/total usage, sanitized headers and total attempt count.
  `build_passage_input` delegates to public `build_embedding_text` with the
  exact passage prefix; providers receive final passages unchanged. Queries
  prepend only `query_prefix`. Both methods reject empty lists, blank items,
  and excess count before any request (`empty-input-list`, `blank-input`,
  `too-many-inputs`). The fake is deterministic, order preserving and L2
  normalized, depending only on final text/dimensions with injected usage.
- **D4 — transport:** `post_json(TransportRequest)` receives only an
  object-valued payload mapping and timeout, never a URL/key. Response is
  status, parsed JSON or None, and lowercase allowlisted `retry-after`/
  `x-ratelimit-*` headers whose values are printable ASCII, length <=64.
  Transport owns the connection; timeout/connection errors have no message,
  cause or context. Suppressing display with `from None` alone is insufficient
  for the no-`__context__` contract: sanitized failures must leave the active
  exception handler before being raised.
- **D5 — OpenAI:** Payload keys are exactly `model,input,dimensions,
  encoding_format`, with `float` encoding and default ASCII JSON. Validate
  shape/model, response count, indices, dimensions, finite numeric values
  (excluding bool/string), and nonnegative integer usage (excluding bool).
  Error codes: `response-shape`, `response-model-mismatch`, `response-count`,
  `response-index`, `response-dimensions`, `response-nonfinite`,
  `response-usage`, `response-not-json`; no response validation retry.
  Reorder by integer index. Retry transient 429, 5xx, timeout/connection;
  quota code OR type `insufficient_quota` is `quota-exceeded` without retry.
  Permanent mappings: 400 `request-rejected`, 401 `authentication-failed`,
  403 `permission-denied`, 404 `endpoint-or-model-not-found`, other 4xx
  `http-<status>`, 3xx `unexpected-redirect`. Retry-After accepts only plain
  nonnegative finite decimal seconds <=3600. Attempt k uses
  `base=min(max_backoff,initial_backoff*2**(k-1))` and
  `delay=max(retry_after or 0,base+uniform(0,base*0.25))`. Attempts include the
  first request; exhaustion is `retry-exhausted`, and elapsed time plus the
  next delay over budget is `retry-budget-exceeded` without sleeping.
- **D6 — connection:** Only an injected process-environment mapping supplies
  keys/base URLs. Missing/blank key is `missing-api-key`; any key character
  outside ASCII 0x21–0x7E is `invalid-api-key`, checked before HTTP header
  construction. Base defaults to `https://api.openai.com`; custom bases need
  HTTPS/host and no userinfo/query/fragment (`invalid-base-url`). Normalize
  trailing slashes; append `/embeddings` after a `/v1` path, otherwise
  `/v1/embeddings`. `OpenAIConnection` hides key and URL from repr. The default
  opener refuses redirects. Send Authorization, JSON Content-Type/Accept,
  and `User-Agent: sciscope-embed/0`. Read at most 16 MiB (injectable cap,
  with at most one extra byte to detect overflow); oversized, non-JSON or
  NaN/Infinity bodies become None. HTTPError bodies expose only error code/
  type. Sanitize every other opener exception, including key-bearing
  ValueError, with no chaining. No logging imports or non-CLI output.
- **D7 — inputs:** Read bytes, hash the exact raw file, strict UTF-8, split
  only on LF and drop exactly one final empty element; internal blanks are
  invalid, CRLF/missing final LF accepted. Reject NaN/Infinity, wrong exact
  chunk field sets, blank text, bad text digest, invalid section paths,
  non-lowercase/non-64-hex or duplicate chunk IDs, empty input, mixed chunk
  versions, counter/template mismatches. Codes respectively include
  `chunks-unreadable`, `chunks-invalid-utf8`, `chunks-invalid-json`,
  `chunks-bad-record`, `chunks-duplicate-id`, `chunks-empty`,
  `chunks-mixed-versions`, `counter-mismatch`, `template-mismatch`.
  Preserve raw untitled headings. Hash/recount exact final prefixed inputs;
  exceeding operational cap or 512 is `input-over-cap` before cache writes
  or network.
- **D8 — cache:** Canonical SHA256 fields are model, decimal dimensions,
  exact-input digest; use private 8-byte big-endian field-count/byte-length
  framing, never import a private chunk helper. Each `<64-hex>.entry` is one
  compact sorted ASCII JSON metadata line, LF, and dimensions*4 float32-LE
  bytes. Metadata records format/model/dimensions/input/vector digests,
  estimate/counter/date plus batch ID/count/estimate/prompt/total usage.
  Batch ID hashes sorted input digests joined with LF. Validate identity,
  format, byte length, checksum, finite values and shared batch metadata;
  any defect is `cache-entry-corrupt`, with no deletion or silent re-embed.
  Temp file and replace are in the cache directory; ignore stale `*.tmp`.
  Persist each successful validated batch before requesting the next. Final
  vectors always come from stored float32 bytes.
- **D9 — durable accounting:** Recompute from the final referenced cache
  entries, summing each UNIQUE batch ID once: batch estimated tokens, prompt/
  total usage and input counts. Estimates and usage always cover the same
  batches across probes/resume/warm reruns. `creation_date` is the EARLIEST
  referenced batch's `embedded_on` UTC YYYY-MM-DD, replacing item 5's former
  first-run configured timestamp; no separate state file.
- **D10 — outputs:** Sort by chunk ID, row i matches manifest entry i;
  publish vectors, manifest and report in ONE public `write_outputs` call.
  JSON uses fixed insertion order, `ensure_ascii=False`, indent 2 and final
  LF. Manifest includes `embedding-set-v1`, complete/partial status,
  provider/model/requested/returned dimensions, declared L2 and fsum observed
  norm range rounded to 9 places, prefixes/template/counter/chunk versions,
  exact `chunks_sha256`, file chunk/vector counts, earliest date, durable
  usage/estimate/provider-input totals, custom-URL boolean, fixed
  `vectors.f32` name, `float32-le`, vector digest, and chunk/input digest
  pairs. Report uses the same set totals/provenance plus selected paper count
  and approximate USD cost rounded to 6 places at the prior model-page
  planning price 0.02/1M. Basis is `reported usage x USD 0.02 per 1M tokens;
  official model page; team billing not verified`. No output includes cache
  hits/misses, call/retry counts, headers, key, URL, absolute path or prose.
- **D11 — pipeline:** Read/validate -> select file-order prefix -> build,
  hash, count and overflow-check -> deduplicate by input digest -> cache
  lookup -> greedily batch misses in selection order within count and token
  limits -> lazily create ONE embedder only for misses -> call/float32/cache
  each batch -> assemble/publish. Concurrency is always 1, not configurable.
  A warm run constructs neither embedder nor transport. Pre-publication
  failures preserve all previous outputs. `limit>=chunk_count` is complete;
  a smaller positive limit is partial, using the same output paths; a later
  full run restores the complete set, reusing all available cached inputs.
- **D12 — console:** Exactly line 1 `chunks: <chunk_count> selected: <n>
  unique-inputs: <u> cache-hits: <h> cache-misses: <m> api-calls: <c>
  retries: <r> status: <complete|partial>` and line 2
  `usage-total-tokens: <u> estimated-input-tokens: <e>`, then zero or more
  allowlisted `x-ratelimit-<name>: <value>` lines from this run's LAST
  response only; none on a warm run. Calls count successful requests;
  retries count failed attempts actually retried.

**Signature refinements for Phase 2:** `ChunkInput` stores validated raw
chunk identity/text/path/version fields; `LoadedChunks` contains file-order
chunks, raw-file digest and common versions. Config-dependent final inputs
are built in the pipeline because `load_chunk_inputs(path,counter)` must
remain reusable without embedding config for T007. `EmbeddingCache(directory)`
has `get(model,dimensions,input_sha256)` and `put_batch(entries)`;
`decode_entry` takes expected identity as keyword arguments for explicit
cache-key validation. `CacheEntry` stores metadata plus immutable
`vector_bytes`. Manifest builder receives entries keyed by chunk ID, retaining
duplicate-input mappings; report builder consumes manifest totals plus
`paper_count` to avoid a second accounting path. `write_embedding_files`
receives prepared vector bytes, both mappings, and three paths. `EmbedOptions`
contains paths/limit; `EmbedStats` holds ephemeral console fields and durable
totals separately. `run_embedding` injects a zero-argument embedder factory
and UTC YYYY-MM-DD string provider. `main` injects keyword-only environment,
connection-to-transport factory, sleep, monotonic clock, uniform and UTC date.
`environ=None` is a lazy process-environment sentinel: Phase 2 resolves it
only AFTER the live guard, never at import/default evaluation. Sleep/clock/
uniform/factory defaults name the real stdlib/class callables; the UTC helper
is a stub until Phase 2, then uses the real UTC date. `OpenUrl` accepts a
urllib Request and keyword timeout, returning the small `HttpResponse`
Protocol. Provider metadata uses read-only Protocol properties to support
immutable implementations. Unspecified retry defaults are now explicit:
timeout 30s, initial backoff 1s, maximum backoff 30s, total retry budget 120s.
Malformed response tests isolate defects: count is checked before index
range/coverage when the number of otherwise shaped items differs; missing
or non-integer (including bool) index is a shape error.

**Group B Phase 2c (2026-11-17):** Person 1 approved verbatim source gaps
between spans from the same paragraph after reviewing the 17-paper run.
Single-paragraph chunk text is now a source substring so downstream quote
checks can use it directly; different paragraphs still join with `"\n\n"`.
`chunk_id` is unchanged when its ordered spans are unchanged. Keep
`chunking-v1` because no consumer has used v1 yet; hashes from the earlier
real run are superseded.

**Group B Phase 2 (2026-11-17):** Loader input precedence is per file in
sections, paragraphs, parse-report order: unreadable/missing file, invalid
UTF-8, invalid JSON, then missing field, extra field, and wrong type
(`report-extra-field` for report extras). Only after all three parse, apply
consistency checks in this order: `doi-order`, `failed-paper-records`,
`doi-set`, `duplicate-section`, `unknown-section` or
`cross-doi-section`, `paragraph-order`, `section-paragraph-count`,
`section-locator-digest`, `paragraph-locator-digest`, `xml-report-digest`.
The first failure wins. Output files are fully staged beside targets before
replacement; if publication fails, restore all previous target bytes (or
absence) and remove staging files. The hard-split boundary scan includes
whitespace at `fitting_end`; `heading_context` and `chunk_section` share one
meaningful-headings helper.

**Group B Phase 2b (2026-11-17):** JSONL records split on `"\n"` only:
U+2028, U+2029 and U+0085 may be raw characters inside JSON strings when
`ensure_ascii=False` and must not become record boundaries. Drop exactly one
empty element after a final LF; keep internal blank lines invalid. Resolve
all five CLI paths after configuration validation and before source loading;
an output equal to another output or any input raises
`output-path-conflict` (exit 2) without reading or writing files. Any
`OSError` while publishing outputs reports `output-write-failed` (exit 1),
with previous output bytes restored.

**Known limits (not implemented in F003):**

- Group C: a crash between the entry writes of one batch can later double
  count that batch's usage and estimate; rare and explicitly accepted.
- Group C: a partial set cut from a larger earlier batch reports that entire
  batch's totals, made visible through `provider_input_count`.
- Group C: response `model` must equal the requested string; revisit in
  Phase 2b if the live run returns a different string.
- Group C: aggregate calibration still cannot prove per-input fit.
- `chunk_record` rebuilds the section map per chunk, O(chunks x sections);
  revisit around 500 papers in F005.
- `final_input_estimated_tokens` uses an empty prefix and ignores
  `prefix_reserve_tokens`.
- F002 papers with nonempty errors and no records are accepted and included
  in `paper_count`; the parse-report summary is not cross-checked with papers.
- `chunks.jsonl` may contain raw U+2028/U+2029/U+0085 inside JSON strings;
  consumers must split on `"\n"` only. Carry this into the F004 handoff.
- Hard splits cut at the last whitespace in the fitting prefix and can split
  a named entity. The real run observed this in 2 of 728 chunks, including
  a 1,250-character semicolon list in 10.1371/journal.pone.0037017.
  Preferring `;` boundaries is deferred and unnecessary before Golden v0.

**T003/T004 (2026-11-16, Phase 1 contract; behavior pending):** A renewed local
solution check compared reuse of F002 JSONL plus `locator_digest`, a generic
splitter/serializer, and a new dependency. F002 already supplies ordered,
digest-bound records; standard-library JSON, SHA256 and file staging fit this
small integration. No external version, license or compatibility fact was
reverified because this phase forbids network access. Use no new dependency.

- **Option A policy:** `CHUNKING_VERSION="chunking-v1"` and
  `CHUNK_KIND_PARAGRAPH="paragraph"`. F002 `skipped_element_kinds` counts
  outer occurrences: `fig` -> `figure`, `table-wrap` -> `table` (caption and
  body), `supplementary-material` -> `supplementary_material`,
  `disp-formula`/`inline-formula` -> `formula`, `list` -> `list`, and
  `boxed-text` -> `boxed_text`. Any other kind -> `other_omitted`, retaining
  name and count in per-paper `unlisted_kinds`. Every category is numeric and
  present with zero when absent. All are `excluded` with a short reason; only
  figure and table have `follow_up="caption chunks after Golden v0"`.
  F002 `back_matter_containers` is a presence list: `ref-list` ->
  `references`, `ack` -> `acknowledgments`, and `app`/`notes`/`fn-group`/
  `glossary` -> `back_matter_other`, counted once per present container.
  `paragraphs_with_omitted` counts paragraph records with a nonempty
  `omitted` list, independent of outer skipped-element counts.
- **Loader:** Strict UTF-8 JSONL and report JSON validate exact F002 field
  sets and types as listed in F002's Output records. Preserve file order and
  require ascending DOI groups. Distinct sanitized consistency codes cover
  duplicate `(doi, section_id)`, unknown/cross-DOI paragraph section,
  non-increasing paragraph index, section paragraph-count mismatch,
  section/paragraph locator digest mismatch (via public `locator_digest`),
  section `xml_sha256` mismatch with its report, successful-report DOI-set
  mismatch, and leftover records for a failed report paper. Return ordered
  sections/paragraphs, per-DOI XML SHA256, omitted kinds by paragraph locator,
  SHA256 of each of three input files, and parse-report papers. Errors never
  expose paragraph text or absolute paths.
- **Chunk ID and record:** Canonical input begins with one 8-byte big-endian
  unsigned field count (`4 + 3 * span_count`), followed by each field as an
  8-byte big-endian unsigned byte length and that many UTF-8 bytes. Ordered
  fields are `chunking_version`, `doi`, `section_id`, decimal `ordinal`, then
  each span's `source_locator`, decimal `start`, decimal `end`. SHA256 lowercase
  hex of those bytes is `chunk_id`; text is excluded. Record key order is
  `chunk_id, doi, xml_sha256, section_id, ordinal, chunk_kind,
  normalized_type, section_path, text, text_sha256, spans, source_locator,
  content_tokens, hard_split, omitted, chunking_version, token_counter_id,
  template_version`. Original F002 `section_path` retains `(untitled)`;
  `spans` are ordered `{source_locator, paragraph_index, start, end}`;
  top-level locator is the first span; `omitted` is the sorted distinct union
  from all contributing paragraphs. `text_sha256` hashes UTF-8 chunk text.
- **Chunk report:** Stable keys include versions, all `ChunkConfig` values,
  three input SHA256 values, static policy, DOI-sorted papers, and summary.
  Each paper has `xml_sha256, section_count, sections_with_chunks,
  chunk_count, paragraph_count, blank_paragraph_count,
  paragraphs_with_omitted, hard_split_chunks, excluded_elements,
  unlisted_kinds, back_matter_excluded`. Summary has totals, counts per
  `normalized_type`, and min/median/p95/max nearest-rank integer statistics
  for content tokens and estimated final input tokens from
  `build_embedding_text` with empty prefix and the same counter, plus below
  soft-minimum and hard-split counts. No prose, headings, or absolute paths.
  JSON uses stable key order, `ensure_ascii=False`, UTF-8, LF and final LF;
  JSONL uses F002 section order then ordinal.
- **Files and CLI:** Stage both files beside targets; publish with
  `os.replace` only after both are fully written. Any failure leaves prior
  output bytes intact and no temporary files. `chunk` defaults to F002 pilot
  inputs, processed `chunks.jsonl`, `data/pilot/chunk_report.json`, cap 384 and
  prefix reserve 0. Console uses UTF-8 and numeric counts only. Exit 0 for
  success; 2 for usage/configuration, unreadable/missing input, malformed
  JSON or wrong field set/type; 1 for parsed but inconsistent inputs or
  chunking failure. Failures print `error: <code>` on stderr and write nothing.

**Group A carry-over (2026-11-16):** A RED assertion requires a hard split to
use whitespace at the fitting prefix end and mark both resulting pieces;
Phase 2 also extracts the shared meaningful-headings filter for
`heading_context` and `chunk_section` without changing heading behavior.

**T001/T002 (2026-11-16):** `config.py` fixes the 512 absolute ceiling, `embedding-text-v1`, `" > "` heading join, `"\n\n"` context separator and `"(untitled)"` sentinel without importing F002. Frozen, slotted `ChunkConfig` defaults to operational cap 384, content targets 200–350, soft minimum 50, prefix reserve 0 and minimum content budget 32; it rejects cap outside 1–512, reserve outside [0, cap), invalid targets, negative soft minimum or budget minimum below 1. `heading_context` drops blank/synthetic entries; `build_embedding_text` prepends the exact prefix and adds context plus separator only when context exists. `content_budget` subtracts reserve and the count of context plus separator, rejects a result below the minimum, and never truncates headings. `TokenCounter` exposes `counter_id` and `count`; `utf8-bytes-div3-v1` counts ceil(UTF-8 byte length/3), including zero for empty text. `ChunkingError`, `ConfigError` and `HeadingBudgetError` define the error hierarchy.

**T002 types and behavior (2026-11-16):** Frozen, slotted `SourceSection`, `SourceParagraph`, `ChunkSpan` and `Chunk` carry DOI, section identity, paragraph locator/index, [start,end) Unicode code-point offsets, heading path, ordinal, content count and hard-split flag. Chunking defines its own `SourceSection`/`SourceParagraph` because F002 records lack `doi`. Chunk IDs, versions and JSONL I/O belong to T004. `chunk_sections` groups by section ID and emits section order then ordinal; it rejects unknown sections, duplicate/non-increasing paragraph indices and DOI mismatches. Parent and child sections are independent. Include all section types with nonblank own text, including `other`; empty sections emit nothing. Compute `effective_max = min(content_target_max_tokens, content_budget)`. Greedily pack whole paragraphs while the joined count fits; do not split a fitting paragraph to fill a chunk. Split oversized paragraphs into sentence-aligned pieces, then hard-split an oversized sentence at the largest token-bounded prefix, preferring whitespace, with `hard_split=True` on affected chunks. Merge sub-`soft_min_tokens` orphans left to right into the previous chunk (next if first) only when the merged count fits the content budget; otherwise leave them. Apply clarification 2's whitespace and joining rules; `content_tokens = counter.count(text)`. Functions are deterministic and pure.

**T001/T002 Phase 2 implementation details (2026-11-16):** A paragraph at or below `effective_max` is one unit. An oversize paragraph becomes sentence-piece units: consecutive sentences within that paragraph form the largest source span whose count fits `effective_max`; an oversize sentence becomes hard-split pieces. All units pass through one greedy loop in source order, and a unit may join an open chunk when the count of the joined text fits `effective_max`. After packing, repeat left-to-right orphan passes until no merge succeeds. A sub-`soft_min_tokens` chunk merges with its previous neighbor, or its next neighbor when first, only when the joined count fits the content budget; merged `hard_split` is the OR of both flags, and final ordinals are 1..n. Sentence spans are trimmed, ordered and non-overlapping, covering every non-whitespace character once. Abbreviations compare the whitespace-delimited period-ending token case-insensitively after leading opening quotes/brackets are stripped; single-uppercase-letter initials remain case-sensitive. Sentence punctuation and starter rules are those in clarification 4. `largest_end_within_limit` finds the maximal fitting offset and raises `ChunkingError` if one code point cannot fit. The hard-split caller takes a fitting remainder whole; otherwise it prefers the last whitespace strictly inside the fitting prefix when that leaves a nonempty piece, then starts after boundary whitespace, or cuts at the maximal offset. `chunk_sections` validates all records before chunking and uses code-like errors without paragraph text for unknown section IDs, duplicate/non-increasing indices and DOI mismatches. T001/T002 functions use no clock, randomness or I/O.

1. **Source contract:** Validate section/paragraph uniqueness and ownership, locator digest against `xml_sha256`, paragraph indices/order and allowed fields. Use F002's exact JSONL ordering for deterministic traversal. Survey found 50 zero-own-paragraph sections (not only 14); 0 empty paragraph records but synthetic tests cover them. Ignore child paragraphs when processing a parent.
2. **Text and spans:** Span offsets exclude whitespace at split boundaries, so chunk text has no leading or trailing whitespace. Spans of one paragraph are ordered and non-overlapping; the first starts at its first non-whitespace character, the last ends at its last, and every gap is whitespace only. Every non-whitespace character is covered exactly once in source order. Each span stores `source_locator` and [`start`,`end`) Unicode code-point offsets. Consecutive spans from the same paragraph join with the exact source substring between their offsets (empty when adjacent); spans from different paragraphs join with `"\n\n"`. A chunk whose spans all belong to one paragraph is a verbatim source substring. `text` is never prefixed; `embedding_text` is separate and versioned.
3. **Budget and calibration acceptance:** B3 counter version `utf8-bytes-div3-v1`. The absolute 512 model-agnostic ceiling includes section context, separator and passage prefix. The operational cap defaults to 384 estimated tokens on complete input (headroom 128/25%) and is configurable up to 512; keep 200–350 content-token soft target when feasible. Chunker reserves configurable prefix overhead; embedder rebuilds with the same counter and fails before a call if over the configured cap or 512. A heading alone that exhausts budget is an actionable error, never truncated. Record the aggregate estimate for exactly the inputs sent to the live provider and the corresponding aggregate `usage.total_tokens`. **Acceptance:** reported tokens must be ≤ estimated tokens. If reported tokens exceed the estimate, reject this estimator and revisit the cap/estimator before F004. Aggregate success cannot prove each input individually fits; state this limit in evidence. No overlap without new evidence.
4. **Sentence boundaries:** A stdlib rule set protects approved abbreviations, initials/species abbreviations and decimals. Sentence punctuation (`.`, `?`, `!`) may be followed by closing quotes/brackets; a boundary requires whitespace and then an uppercase letter, digit, opening quote or bracket. Units and terminal `p < 0.05.` can split. The protected abbreviation list is `et al.`, `Fig.`, `Figs.`, `Tab.`, `Eq.`, `Ref.`, `e.g.`, `i.e.`, `vs.`, `cf.`, `ca.`, `approx.`, `no.`, `sp.`, `spp.`, `var.`, `subsp.`, `Dr.`; a single uppercase letter before a period is protected. This conservative rule may miss a real boundary after an abbreviation or initial. Hard split finds the largest prefix within the token limit, preferring the last whitespace within it; flags `hard_split`.
5. **Identity/versioning:** Canonical SHA256 uses length-delimited UTF-8 fields to avoid ambiguous concatenation. `chunking_version` changes whenever boundary, coverage or policy semantics change; `template_version` changes with heading/separator/prefix construction; `token_counter_id` changes with estimator rules. Text hash and cache key use the exact final input bytes. Generated manifest/report timestamps are excluded from deterministic outputs; `creation_date` is a deterministic embedding-set creation date retained across resume, passed/configured at first run rather than reset on rerun.
6. **Embedder and transport:** `embed_passages` and `embed_queries` accept nonempty text inputs through one config. OpenAI transport receives a request object and returns status, selected headers and parsed JSON; never logs request headers/body or raw error bodies. Sort response `data` by `index` and reject missing/duplicate/out-of-range indices, mismatched model, count, dimensions, nonfinite values and malformed usage before writing cache. Explicit live selection is required even when a key exists. No `.env` loading. Document `OPENAI_BASE_URL=` in `.env.example` only during T008 doc sync; store only `custom_base_url_used` boolean.
7. **Retry/cache/output:** Conservative provisional defaults: 8 inputs per request, 2,048 estimated tokens per request, concurrency 1, 3 attempts, bounded total retry time; all configurable and below verified endpoint maxima. Person 1's observed key-specific limits (10,000 requests and 5,000,000 tokens in the reported windows) do not make these defaults unsafe; retain them as provisional. For temporary 429 only retry rate-limit subtype, not quota/billing; retry 5xx/timeouts/connection failures, honoring valid `Retry-After` as a minimum. Inject sleep/clock/randomness for tests. Cache entries live under `data/embeddings/pilot/cache/`, covered by the existing `data/embeddings/` rule in `.gitignore`. Atomic cache files use temp write + replace; validate checksum/dimension before hit and fail on corruption. Persist each successful batch before the next; final outputs are sorted by chunk ID, atomically published after completeness and validated set equality. The set-level `embedding_report.json` contains counts, `estimated_input_tokens` for the exact provider inputs originally sent, `usage.total_tokens` summed from their successful responses, dimensions, versions and labeled approximate cost. Preserve creation date, usage and report values on warm rerun so `vectors.f32`, `manifest.json` and `embedding_report.json` remain byte-identical to the cold run. None of those three files contains cache hits/misses, API-call counts or retry counts; print run-level statistics and observed `x-ratelimit-*` values to the console only, or an optional gitignored last-run file. No report contains prose, key, URL or local absolute path. `--limit N` creates a partial embedding set with explicit `partial` status and only selected chunk IDs; `validate` rejects it as complete unless `--allow-partial` is specified.
8. **Vector validation:** Store little-endian float32, recorded requested and returned dimension, count, finite values, SHA256 of vector bytes and corresponding exact-input hashes. OpenAI normalization is documented, but `validate` computes L2 norms and checks tolerance 0.01 (provisional, review after real run). Other providers declare expected normalization; validator checks that declaration rather than assuming it. Stable ordering prevents response-order changes from changing bytes.
9. **Failure boundaries:** Missing key, bad config, unsupported provider, input overflow and unsafe source are exit 2 for invalid invocation/config; source, transport, response or validation failures are exit 1. Sanitized error codes only, no raw URLs or exception chaining that might reveal credentials.

## Tests and verification strategy

Every T001–T007 code task first adds labeled synthetic RED tests, runs them to confirm missing behavior, then implements its own scope. No real article prose or paid calls in fixtures. Planned unique files: `test_chunk_counter.py`, `test_chunk_core.py`, `test_chunk_policy.py`, `test_chunk_output.py`, `test_embed_provider.py`, `test_embed_pipeline.py`, `test_embed_validate.py`. Tests cover untitled/implicit/nested/abstract/`other`, empty paragraph, exact whitespace coverage, oversize paragraph/sentence, IDs and deterministic two-run bytes, no overlap. Provider tests cover out-of-order `index`, 429 with `Retry-After` then success, 5xx then success, timeout/connection retries, retry exhaustion, no retry on 400/401/403/404 or quota 429, malformed/short/duplicate response, vector count/length and nonfinite values, no empty string sent, input-count/estimated-token batch splits, cache hit/miss/partial resume/corruption, and missing key. Capture exceptions, logs, reports and CLI output to assert the test key never appears, including its prefix/length; default CLI and dry-run assert zero network calls. Meaningful local checks after each task: focused pytest, `ruff check . --no-cache`, `mypy src`.

## Pre-implementation verification gate

The 2026-11-15 gate results are appended to `research.md`. Record any newly checked official source and team-account observation before an implementation prompt or behavior test. Person 1's safe local probe is reported evidence, not an independently repeated call.

| Item | Current status | Person 1 check required before implementation |
| --- | --- | --- |
| (a) Per-request limits | **VERIFIED in official [API reference](https://developers.openai.com/api/reference/resources/embeddings/methods/create)**: 8,192 per input, 2,048 inputs, 300,000 summed. | Confirm current endpoint documentation immediately before implementation and record date. |
| (b) Rate limits and headers | **VERIFIED** [guide](https://developers.openai.com/api/docs/guides/rate-limits) header names: `x-ratelimit-limit-requests`, `-limit-tokens`, `-remaining-requests`, `-remaining-tokens`, `-reset-requests`, `-reset-tokens` and project-token variants; `Retry-After`. **OBSERVED by Person 1, 2026-11-15:** request limit 10,000, token limit 5,000,000, remaining requests 9,999, remaining tokens 4,999,995, resets 6ms and 0s. | Record these as this key's observed header values, not defaults or independently verified account limits. Account/project limits-page values remain NOT VERIFIED. |
| (c) Price | **VERIFIED for planning** on the official [model page](https://developers.openai.com/api/docs/models/text-embedding-3-small): $0.02/1M input tokens. The general [pricing page](https://developers.openai.com/api/docs/pricing) did not expose an embedding entry in fetched text; that gap is non-blocking per Person 1. | Label dry-run cost “approximate”; current team billing rate is NOT VERIFIED. |
| (d) Dimensions and normalization | **VERIFIED** [reference](https://developers.openai.com/api/reference/resources/embeddings/methods/create), [guide](https://developers.openai.com/api/docs/guides/embeddings), [FAQ](https://help.openai.com/en/articles/6824809): `dimensions` supported for v3+, default 1,536 for small, outputs L2 normalized including shortening. | Observe returned dimensions and norms on live run; tune tolerance only with evidence. |
| (e) 429/5xx and retry | **VERIFIED** [rate guide](https://developers.openai.com/api/docs/guides/rate-limits), [error guide](https://developers.openai.com/api/docs/guides/error-codes): transient 429/503, 500, `Retry-After` minimum; quota/billing 429 must not retry. | Record any actual status/code/header; confirm gateway behavior if used. |
| (f) Key route | **OBSERVED by Person 1, 2026-11-15:** direct `https://api.openai.com/v1/embeddings`, key from `OPENAI_API_KEY`, `OPENAI_BASE_URL` unset; default model returned 1,536 dimensions and 6 usage tokens. **NOT VERIFIED independently** in this sandbox. | Use the reported direct route for the pilot; do not save or print the key. |

Rate/concurrency defaults remain provisional at 8 inputs, 2,048 estimated tokens/request, concurrency 1; the observed limits do not make them unsafe. Do not send a live request from CI or this sandbox. The embedding-model comparison (OpenAI vs E5/other), caption chunks and title-bearing `embedding-text-v2` are **DEFERRED** until Golden v0 (PENDING), with no comparison work in F003.

## Handoff notes for F004

Chunk JSONL consumers must split records on `"\n"` only. Because output uses
`ensure_ascii=False`, U+2028, U+2029 and U+0085 can occur raw inside strings.
Single-paragraph chunk text is a verbatim source substring; `"\n\n"` is
inserted only between different paragraphs.

Person 2 must embed queries with the **same provider, model and dimensions** as the embedding-set manifest, using its `query_prefix` and compatible input construction. `embed_queries` and `embed_passages` share the provider interface/config; never compare vectors from differing sets. Record requested and returned dimensions, observed normalization, `template_version`, `token_counter_id` and `chunking_version`. F004 reconciles flat F002/F003 JSONL with draft `DATA_CONTRACT.json`, including its 384-vector restriction and `embedding_model_revision` field; it should define authoritative version semantics with Person 1/2. Retrieval evaluation and database insertion remain outside F003.

## One PowerShell command set for final manual verification (Person 1 terminal)

Run after implementation. The `OPENAI_API_KEY` must already be in the process environment; commands never print it. Store observations, hashes and explicit acceptance/rejection in EVIDENCE.md only after Person 1 reports them. The first `validate` checks chunks; the second checks the complete embedding set. The UTF-8 Python stdin script slices Unicode code points so PowerShell/.NET UTF-16 `Substring` cannot misinterpret stored offsets. It also avoids Windows PowerShell 5.1 stripping embedded double quotes from native-command arguments.

```powershell
uv run --locked pytest tests -q
uv run --locked python -m sciscope.pipeline.cli chunk
$chunkHash1 = (Get-FileHash data/processed/pilot/chunks.jsonl -Algorithm SHA256).Hash
$reportHash1 = (Get-FileHash data/pilot/chunk_report.json -Algorithm SHA256).Hash
uv run --locked python -m sciscope.pipeline.cli chunk
$chunkHash2 = (Get-FileHash data/processed/pilot/chunks.jsonl -Algorithm SHA256).Hash
$reportHash2 = (Get-FileHash data/pilot/chunk_report.json -Algorithm SHA256).Hash
Compare-Object @($chunkHash1, $reportHash1) @($chunkHash2, $reportHash2)
uv run --locked python -m sciscope.pipeline.cli validate --chunks-only
uv run --locked python -m sciscope.pipeline.cli embed --dry-run
# Explicit live selection; key is read only from the existing process environment:
uv run --locked python -m sciscope.pipeline.cli embed --provider openai --live
$vectorHash1 = (Get-FileHash data/embeddings/pilot/vectors.f32 -Algorithm SHA256).Hash
$manifestHash1 = (Get-FileHash data/embeddings/pilot/manifest.json -Algorithm SHA256).Hash
$embeddingReportHash1 = (Get-FileHash data/pilot/embedding_report.json -Algorithm SHA256).Hash
$embeddingReport = Get-Content data/pilot/embedding_report.json -Encoding UTF8 | ConvertFrom-Json
$tokenRatio = $embeddingReport.usage.total_tokens / $embeddingReport.estimated_input_tokens
if ($embeddingReport.usage.total_tokens -gt $embeddingReport.estimated_input_tokens) { throw 'Embedding token estimator calibration failed' }
$tokenRatio
uv run --locked python -m sciscope.pipeline.cli embed --provider openai --live
$vectorHash2 = (Get-FileHash data/embeddings/pilot/vectors.f32 -Algorithm SHA256).Hash
$manifestHash2 = (Get-FileHash data/embeddings/pilot/manifest.json -Algorithm SHA256).Hash
$embeddingReportHash2 = (Get-FileHash data/pilot/embedding_report.json -Algorithm SHA256).Hash
Compare-Object @($vectorHash1, $manifestHash1, $embeddingReportHash1) @($vectorHash2, $manifestHash2, $embeddingReportHash2)
uv run --locked python -m sciscope.pipeline.cli validate
$sampleChunk = Get-Content data/processed/pilot/chunks.jsonl -Encoding UTF8 -TotalCount 1 | ConvertFrom-Json
uv run --locked python -m sciscope.jats.cli show $sampleChunk.doi --section $sampleChunk.section_id
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$span = $sampleChunk.spans[0]
$quote = @'
import json, sys
from pathlib import Path
locator, start, end = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
for line in Path("data/processed/pilot/paragraphs.jsonl").read_text(encoding="utf-8").splitlines():
    row = json.loads(line)
    if row["source_locator"] == locator:
        print(row["text"][start:min(end, start + 80)])
        break
'@ | uv run --locked python -X utf8 -I - $span.source_locator $span.start $span.end
uv run --locked python -m sciscope.jats.cli check-quote --locator $span.source_locator --quote $quote
uv run --locked ruff check . --no-cache
uv run --locked ruff format --check .
uv run --locked mypy src
git diff --check
git status --short
```

Expected: pytest/quality checks pass; both `Compare-Object` calls are empty, including the committed embedding report; chunk validation covers all nonempty F002 paragraphs; dry-run makes no network request; first live run returns complete vectors, second console output reports zero API calls; trace and quote succeed. Person 1 records the aggregate estimated/reported token ratio and observed `x-ratelimit-*` header values, inspects one chunk and its F002 passage, confirms observed norms and explicitly accepts or rejects. A ratio above 1 rejects the estimator and requires cap/estimator revision before F004. A failed command remains failed in evidence until resolved; do not mark tasks done on assistant observation alone.

## Risks and deferred document work

The stdlib estimator has no known per-input true-token bound; 25% headroom and aggregate calibration reduce but cannot eliminate overflow risk. Caption omission limits retrieval of figure/table descriptions, with counts and follow-up visible. Atomic cache files may occupy many small files, acceptable for pilot. Account limits-page values and any future gateway behavior remain unverified. T008 makes doc-only edits to D-004, CHUNKING_STRATEGY, ARCHITECTURE, `.env.example` and P2-17, then updates EVIDENCE and backlog only after human acceptance. `DATA_MODEL.md` and `DATA_CONTRACT.json` remain F004 work; no schema finalization here.
