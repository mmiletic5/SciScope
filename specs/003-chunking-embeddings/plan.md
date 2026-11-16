# Implementation Plan: Section-aware chunking and embeddings

**Branch**: `003-chunking-embeddings` | **Date**: 2026-11-15 | **Spec**: [spec.md](spec.md)
**Status**: Approved by Person 1, 2026-11-15, subject to A-E; implementation not started

## Summary and technical context

Build F002 paragraph-derived section chunks, then an explicitly selected embedding run for the 17-paper pilot (P2-11..P2-19). Python 3.12, standard library runtime, pytest/ruff/mypy development tools, local JSONL and binary files. Inputs are `data/processed/pilot/{sections,paragraphs}.jsonl` and F001 manifest; output is ignored `data/processed/pilot/chunks.jsonl` and `data/embeddings/pilot/` plus small committed `data/pilot/{chunk,embedding}_report.json`. No new dependency or `uv.lock` change under the recommended design. CI uses fake transport only. Person 1 owns data processing and embeddings; Person 2 reviews the F004 handoff contract. Scale: 17 papers, 319 sections, 585 paragraphs; larger-corpus performance is deferred.

## Constitution check and project structure

Research preceded specification; Person 1 approved this plan and spec subject to corrections A-E, now recorded here. All code tasks begin with labeled synthetic RED behavior tests and a renewed `$solution-research` check. No paid calls in tests/CI; live calls require explicit selection. Source provenance and deterministic processing are required. Person 2 contract review precedes F004 integration. Final human verification and evidence precede task completion.

Planned layout: `src/sciscope/chunking/{__init__,config,counter,split,core,report}.py`, `src/sciscope/embedding/{__init__,config,provider,openai_client,cache,store,pipeline}.py`, `src/sciscope/pipeline/cli.py`; unique `tests/chunking/test_chunk_*.py` and `tests/embedding/test_embed_*.py`. F002 `src/sciscope/jats/{locator,parser,source,cli}.py` remains unchanged under Option A. Feature directory contains only `spec.md`, `plan.md`, `tasks.md`, `research.md`. No data-model, quickstart, contracts or checklist files.

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

**T001/T002 (2026-11-16):** `config.py` fixes the 512 absolute ceiling, `embedding-text-v1`, `" > "` heading join, `"\n\n"` context separator and `"(untitled)"` sentinel without importing F002. Frozen, slotted `ChunkConfig` defaults to operational cap 384, content targets 200–350, soft minimum 50, prefix reserve 0 and minimum content budget 32; it rejects cap outside 1–512, reserve outside [0, cap), invalid targets, negative soft minimum or budget minimum below 1. `heading_context` drops blank/synthetic entries; `build_embedding_text` prepends the exact prefix and adds context plus separator only when context exists. `content_budget` subtracts reserve and the count of context plus separator, rejects a result below the minimum, and never truncates headings. `TokenCounter` exposes `counter_id` and `count`; `utf8-bytes-div3-v1` counts ceil(UTF-8 byte length/3), including zero for empty text. `ChunkingError`, `ConfigError` and `HeadingBudgetError` define the error hierarchy.

**T002 types and behavior (2026-11-16):** Frozen, slotted `SourceSection`, `SourceParagraph`, `ChunkSpan` and `Chunk` carry DOI, section identity, paragraph locator/index, [start,end) Unicode code-point offsets, heading path, ordinal, content count and hard-split flag. Chunking defines its own `SourceSection`/`SourceParagraph` because F002 records lack `doi`. Chunk IDs, versions and JSONL I/O belong to T004. `chunk_sections` groups by section ID and emits section order then ordinal; it rejects unknown sections, duplicate/non-increasing paragraph indices and DOI mismatches. Parent and child sections are independent. Include all section types with nonblank own text, including `other`; empty sections emit nothing. Compute `effective_max = min(content_target_max_tokens, content_budget)`. Greedily pack whole paragraphs while the joined count fits; do not split a fitting paragraph to fill a chunk. Split oversized paragraphs into sentence-aligned pieces, then hard-split an oversized sentence at the largest token-bounded prefix, preferring whitespace, with `hard_split=True` on affected chunks. Merge sub-`soft_min_tokens` orphans left to right into the previous chunk (next if first) only when the merged count fits the content budget; otherwise leave them. Apply clarification 2's whitespace and joining rules; `content_tokens = counter.count(text)`. Functions are deterministic and pure.

1. **Source contract:** Validate section/paragraph uniqueness and ownership, locator digest against `xml_sha256`, paragraph indices/order and allowed fields. Use F002's exact JSONL ordering for deterministic traversal. Survey found 50 zero-own-paragraph sections (not only 14); 0 empty paragraph records but synthetic tests cover them. Ignore child paragraphs when processing a parent.
2. **Text and spans:** Span offsets exclude whitespace at split boundaries, so chunk text has no leading or trailing whitespace. Spans of one paragraph are ordered and non-overlapping; the first starts at its first non-whitespace character, the last ends at its last, and every gap is whitespace only. Every non-whitespace character is covered exactly once in source order. Each span stores `source_locator` and [`start`,`end`) Unicode code-point offsets. Join span texts with `""` when the next span is adjacent in the same paragraph, otherwise with `"\n\n"`. `text` is never prefixed; `embedding_text` is separate and versioned.
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
