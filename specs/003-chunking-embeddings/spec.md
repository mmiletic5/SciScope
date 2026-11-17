# Feature Specification: Section-aware chunking and embeddings

**Feature Branch**: `003-chunking-embeddings`
**Created**: 2026-11-15
**Status**: Implemented and verified; accepted by Person 1, 2026-11-17 (see EVIDENCE.md)
**Input**: P2-11 through P2-19 for the 17-paper F002 pilot.

## User Scenarios & Testing

### User Story 1 — Traceable section chunks (Priority: P1)

Person 1 produces chunks from F002 records for indexing while preserving source substrings and provenance with exact non-whitespace character coverage. **Independent test:** synthetic sections and paragraphs can be chunked and validated without an embedding provider.

1. **Given** a section with nonempty paragraphs, **when** chunks are built, **then** spans cover every non-whitespace character of each paragraph exactly once, in order, with whitespace-only gaps at split boundaries and no paragraph from another section.
2. **Given** nested sections, a structured or plain abstract, an implicit body group, or an untitled section, **when** chunks are built, **then** each record remains in its owning section and synthetic `(untitled)` is not treated as a heading.
3. **Given** empty paragraphs or a section with no own text, **when** chunks are built, **then** no empty embedding input or empty chunk is produced.
4. **Given** an oversize paragraph or sentence, **when** chunks are built, **then** source-preserving offsets cover it once and a hard-split fallback is flagged when needed.

### User Story 2 — Controlled, resumable embeddings (Priority: P2)

Person 1 can estimate a run offline, explicitly select a live provider, resume after interruption, and hand Person 2 a versioned embedding set. **Independent test:** fake transport verifies batching, retries, cache, output shape and deterministic reruns without network.

1. **Given** no live selection, **when** the CLI runs or dry-run is selected, **then** it makes zero network calls and does not require a key.
2. **Given** an explicit live selection and valid process-environment key, **when** uncached chunks are embedded, **then** complete indexed vectors, usage and sanitized metadata are recorded.
3. **Given** a partially complete run or warm cache, **when** embedding is rerun with the same configuration, **then** only missing inputs are sent; a warm rerun makes zero API calls and yields byte-identical `vectors.f32`, `manifest.json` and `embedding_report.json`.
4. **Given** a transient rate limit, server error, timeout, or connection failure, **when** the request is retried, **then** bounded exponential backoff with jitter respects a valid `Retry-After`; permanent errors fail safely.

### User Story 3 — Verifiable handoff (Priority: P3)

Person 1 validates chunk and vector artifacts before Person 2 uses them. **Independent test:** synthetic corruptions each cause an actionable nonzero validation result.

1. **Given** a complete chunk and embedding set, **when** `validate` runs, **then** source coverage, token cap, chunk-set equality, hashes, dimensions, finite values, norm tolerance and versions pass.
2. **Given** an overflow, changed input text, missing or extra vector, malformed response, cache corruption, or wrong dimensions, **when** generation or validation runs, **then** it fails without silent truncation or secret disclosure.

### Edge Cases and failures

- Untitled paths, direct-body implicit groups, parent sections with only child text, empty paragraph records, `other` sections, and structured abstracts.
- Abbreviations (`et al.`, `Fig.`), species names, decimals and units near sentence boundaries; a single sentence exceeding the budget; long heading context.
- 429 with `Retry-After`, transient 5xx, timeout, connection failure, exhausted retries, non-retryable 400/401/403/404, and quota 429 requiring action.
- Out-of-order response `index` values, short or malformed responses, duplicate indices, wrong vector count/length, non-finite vector entries, missing key, and corrupt cache.

## Requirements

### Functional Requirements

- **FR-001**: Read and verify F002 `sections.jsonl` and `paragraphs.jsonl` for the pilot, preserving DOI, `section_id`, paragraph locators, `xml_sha256`, section path and type; fail on missing or inconsistent source records.
- **FR-002**: Emit only nonempty paragraph-derived chunks under Option A, approved by Person 1 on 2026-11-15. Excluded content kinds remain counted in the chunk report. Figure/table caption chunks are a named follow-up after Golden v0. No text crosses section ownership or overlaps.
- **FR-003**: Preserve chunk `text` as verbatim source substrings joined by the specified span separators. Store paragraph locator plus start/end character offsets for every span; validation checks every non-whitespace character of each nonempty paragraph exactly once, in order, with whitespace-only gaps at split boundaries.
- **FR-004**: Use a configurable, versioned token counter and template. The provisional operational cap is 384 estimated tokens per final embedding input, configurable up to an absolute ceiling of 512, including heading context, separator and provider prefix. The chunker reserves prefix overhead; the embedding step rebuilds, recounts and fails on overflow.
- **FR-005**: Produce deterministic chunk IDs, `chunking_version`, token-counter ID, template version, source `xml_sha256`, ignored-content counts and a deterministic chunk report. Repeated identical input/configuration must produce byte-identical files.
- **FR-006**: Configure provider, model, requested dimensions, passage/query prefixes, batch input/token limits and retry limits. Default configuration is OpenAI `text-embedding-3-small`, 1,536 dimensions, empty prefixes. The model is not hard-coded into the chunker.
- **FR-007**: Expose `embed_passages` and `embed_queries` through one provider interface. Build passage inputs from a versioned template; query inputs use the same provider, model, dimensions and the configured `query_prefix`.
- **FR-008**: Live requests require explicit selection and read `OPENAI_API_KEY` and optional `OPENAI_BASE_URL` only from process environment. Dry-run and all automated tests make zero network calls. No output, exception, log or report may contain a key, key length/prefix, base URL, or local absolute path.
- **FR-009**: Cache by model, dimensions and SHA256 of the exact input text. Batch within configured input-count and estimated-token limits. Retry eligible temporary failures with bounded exponential backoff/jitter and `Retry-After`; do not retry specified permanent errors.
- **FR-010**: Persist resumable vectors and an embedding-set manifest with provider, model, requested/returned dimensions, normalization observation, prefixes, template version, counter ID, creation date, usage totals, and a boolean indicating a custom base URL. `embedding_report.json` contains set-level counts, estimated tokens, aggregate usage from the run that produced the vectors, dimensions, versions and approximate cost. `vectors.f32`, `manifest.json` and `embedding_report.json` must be byte-identical after cold and warm runs; none may contain cache hits/misses, API-call counts or retry counts. Run-level statistics appear on the console only or in an optional gitignored last-run file.
- **FR-011**: `validate` checks exact paragraph coverage, section isolation, the configured operational token cap and absolute 512-token ceiling, chunk-set equality, text hashes, versions, vector count/dimensions/finite values and empirical norm tolerance. `--dry-run` reports chunk count, estimated tokens and labeled approximate cost without network.
- **FR-012**: Commands return 0 for success, 1 for validation or processing failure, and 2 for invalid usage, consistent with F002.

### Key Entities

- **Source paragraph span**: locator and [start, end) character offsets into F002 paragraph text.
- **Chunk**: source text, one owning section, ordered spans, deterministic ID, provenance and processing versions.
- **Embedding input**: versioned heading context and passage prefix around chunk text; independently hashed.
- **Embedding set**: vectors keyed to chunk IDs, manifest and usage; provider configuration also supports queries.
- **Cache entry**: exact-input hash plus model/dimensions, vector and integrity data.

### Assumptions and dependencies

F002 JSONL and manifest-listed raw XML are authoritative for this pilot. `data/processed/pilot` files are regenerable but need not be regenerated during planning. Source omissions are an explicit policy, not missing coverage of F002 paragraphs. The 200–350 content-token target is provisional until estimator calibration. Person 1 approved this spec and plan subject to corrections A-E, including Option A; the gate results and remaining unverified items are recorded in `research.md`.

## Success Criteria

- **SC-001**: All 17 pilot papers process; every non-whitespace character of every nonempty F002 paragraph is covered exactly once, in order, with whitespace-only gaps at split boundaries, and zero chunks mix sections.
- **SC-002**: All final embedding inputs are nonempty and at or below the configured operational cap (provisionally 384 estimated tokens) and the absolute 512-token ceiling; overflows fail before a network call.
- **SC-003**: Two unchanged chunk runs produce byte-identical chunk artifacts. A cold embedding run and a warm-cache rerun produce byte-identical `vectors.f32`, `manifest.json` and committed `embedding_report.json`; console output shows zero provider calls on the warm run.
- **SC-004**: Synthetic offline tests cover transient/permanent failures, malformed/short/out-of-order responses, cache resume/corruption, shape and norm checks, and absence of secret leakage.
- **SC-005**: The committed reports include counts and provenance summaries without article prose, credentials or absolute paths. A sampled chunk traces to F002 `show` and `check-quote`.
- **SC-006**: Person 1 runs the manual command set and explicitly accepts the observed result before any P2 task is marked done.

## Out of scope

Golden v0, model comparison, local E5/sentence-transformers provider, retrieval evaluation, database, F004 `DATA_CONTRACT.json` finalization, F005 corpus expansion and live API calls in CI. Figure/table caption chunks and a title-bearing `embedding-text-v2` template are deferred candidates for evaluation after Golden v0.
