# Feature Specification: Phase C Retrieval Quality and Evidence Selection

**Feature Branch**: `008-phase-c-quality`  
**Created**: 2026-11-19  
**Status**: Approved for implementation (2026-11-19; refinements recorded below)  
**Input**: User request to plan Person 2 Phase C (P3-09 through P3-12).

## User Scenarios & Testing

### User Story 1 - Stable diverse evidence ranking (Priority: P1)

As a research workflow, I need one reproducible ordered evidence list so repeated retrieval does not reorder ties or overwhelm the answer context with repeated passages from one source.

**Why this priority**: Context selection and every downstream consumer depend on a stable, duplicate-aware ranking built on the accepted Phase B results.

**Independent Test**: Feed synthetic Phase B candidate records with known scores, duplicate DOI/primary-locator/text values, tied scores, and repeated DOIs to a pure ranking oracle; verify IDs, order, and duplicate/diversity reasons exactly.

**Acceptance Scenarios**:

1. **Given** identical candidates and snapshot identity, **When** ranking runs repeatedly, **Then** it emits byte-for-byte equivalent ordered IDs and scores.
2. **Given** two different chunk IDs with identical DOI, primary locator, and exact text, **When** deduplication runs, **Then** one representative remains, chosen by the documented base order and then chunk ID.
3. **Given** reranker ties or candidates from an overrepresented DOI, **When** final diversity is applied, **Then** the deterministic tie order and configured per-DOI cap are honored without altering retained text or provenance.

### User Story 2 - Reproducible reranker decision (Priority: P2)

As a retrieval owner, I need an offline comparison against accepted RRF so production reranking is enabled only when measured gains justify its added latency and runtime cost.

**Why this priority**: The benchmark can inform whether an optional dependency should ever enter the runtime path; a reranker is not a required production feature.

**Independent Test**: Run an immutable local checkpoint against exactly the five approved development smoke questions and the identical RRF candidate pool; reproduce each score, matching result, and latency summary from the manifest.

**Acceptance Scenarios**:

1. **Given** a pinned model checkpoint already present locally, **When** the benchmark runs with network access disabled, **Then** no paid or remote inference occurs and the run records code, corpus, question, model, environment, and configuration identities.
2. **Given** the five fixed smoke questions, **When** RRF and reranking are compared, **Then** both use the same candidates, evidence matching, K values, and denominator; the other 16 Golden v0 questions are not read or evaluated.
3. **Given** a reranker that does not meet the predeclared quality and latency gates, **When** the benchmark report is produced, **Then** the production configuration remains no-op/disabled and no superiority claim is made.

### User Story 3 - Deterministic budgeted evidence context (Priority: P1)

As an answer-generation caller, I need complete ranked passages selected under a precise token budget so the model receives reproducible evidence without silently truncated science text.

**Why this priority**: The selection step is required to safely consume ranked candidates within downstream context limits.

**Independent Test**: Use an injected deterministic token counter and fixed candidate sequence to verify exact selection, token totals, overflow behavior, and provenance preservation.

**Acceptance Scenarios**:

1. **Given** a valid nonnegative budget and ordered candidates, **When** selection runs, **Then** it greedily accepts each whole candidate that fits, skips a non-fitting candidate and continues, and never exceeds the budget.
2. **Given** a candidate larger than the remaining budget, **When** selection runs, **Then** the candidate is omitted with an explicit reason and its text is never truncated or rewritten.
3. **Given** a counter whose identity differs from the configured downstream model counter, **When** selection is requested, **Then** the request fails clearly instead of claiming an exact budget.

### User Story 4 - Resolve source evidence by stable identifiers (Priority: P1)

As a backend or evaluator, I need to resolve a paper, source passage, or chunk against the active corpus and receive the exact snapshot provenance so citations can be checked and reproduced.

**Why this priority**: Evidence matching and citation validation require exact, snapshot-scoped resolution rather than fuzzy source reconstruction.

**Independent Test**: Against the accepted test database corpus, resolve known DOI, digest-bound locator, and chunk ID in a read-only snapshot and compare the returned persisted identity and content with delivery records.

**Acceptance Scenarios**:

1. **Given** a normalized DOI, **When** lookup runs, **Then** it returns the matching paper identity/metadata and the captured corpus identity or an explicit not-found outcome.
2. **Given** a DOI plus exact opaque locator, **When** lookup runs, **Then** it returns all chunk records whose primary locator or any span locator exactly matches, ordered by chunk ID, with unchanged DOI, locator, text, and snapshot provenance.
3. **Given** a chunk ID, **When** lookup runs, **Then** it returns exactly that chunk from the active snapshot; an unknown or stale identifier produces explicit not-found rather than a result from an inactive snapshot.

## Edge Cases

- The same chunk ID is repeated in the candidate input; duplicate IDs are invalid input, distinct IDs with identical DOI/primary-locator/text are deduplicated.
- Equal RRF or reranker scores; non-finite scores; missing, invented, repeated, or reordered reranker identities; an empty reranker result; requested reranker failure.
- Multiple chunks share a locator because they cover different offsets; locator lookup must return all exact matching span owners.
- A single DOI dominates candidates; a configured cap excludes candidates; the corpus contains fewer distinct DOIs than the requested result count.
- Empty candidate list, zero budget, candidate cost equals budget, a candidate exceeds total budget, counter exception, and counter identity mismatch.
- Duplicate DOI normalization aliases, invalid DOI, blank locator, malformed chunk ID, valid but unknown ID, and an identifier existing only in a non-active snapshot.
- Active snapshot changes during lookup; all returned rows and provenance must come from one captured active snapshot.
- Model cache absent, hash mismatch, unsupported native Windows dependency, CPU-only machine, or offline benchmark invocation.

## Requirements

### Functional Requirements

- **FR-001**: Phase C MUST consume the accepted private Phase B retrieval output and its one-based dense/lexical ranks, RRF score, chunk ID, text, DOI, primary source locator, and corpus identity. It MUST NOT modify Feature 007 or copy/reimplement retrieval, filtering, or RRF.
- **FR-002**: Ranking MUST reject repeated candidate IDs and any missing required identity/provenance. Candidate identity is `chunk_id`; duplicate evidence identity is `(normalized DOI, exact primary source locator, exact text)` using only fields already returned by Phase B. The representative of a duplicate group is the candidate with the best Phase B base order; ties resolve by lowercase `chunk_id`. Do not fetch spans or reopen the accepted Phase B transaction for deduplication.
- **FR-003**: Base order MUST preserve Phase B order: its existing mode-specific score/rank order is authoritative. Phase C MUST NOT recompute dense, lexical, or RRF scores. The universal final tie key after any new score is `(base_rank ascending, chunk_id lowercase ascending)`.
- **FR-004**: Final diversity MUST use a configurable maximum selected evidence count per normalized DOI, default `2`, applied greedily in candidate order after reranking (or base order when disabled). An explicit `None` disables the cap; integer values 1 through 50 set the cap. No hidden relaxation is allowed. The ranking result reports exclusions and their reason.
- **FR-005**: Reranking MUST be optional, pluggable, disabled by default, and downstream of Phase B fusion and exact duplicate suppression, but upstream of final per-DOI diversity and context selection. The protocol receives the query and a stable ordered sequence of candidate IDs/text, and returns exactly one finite score per supplied ID. No missing, invented, duplicated, or extra IDs are accepted. Sort by reranker score descending, then base rank ascending, then chunk ID ascending. A requested reranker failure is surfaced; there is no silent fallback.
- **FR-006**: The P3-10 benchmark MUST compare RRF-only and a proposed local English cross-encoder `cross-encoder/ms-marco-MiniLM-L6-v2`, with a pinned immutable model revision and checkpoint SHA-256 recorded before any run. It MUST use the same RRF candidate list (default first 50 eligible candidates, capped to availability) for each method; the reranker changes only the ordering of those candidates. The benchmark and inference MUST work offline after checkpoint acquisition and MUST make no paid/remote model calls.
- **FR-006a**: Candidate lists MUST come from the accepted Phase B hybrid RRF path for the five smoke questions and a compatible query vector for each. Phase C MUST NOT make a paid/live embedding call or substitute another embedding model. If no compatible precomputed query vectors and candidate lists are available, the measured quality comparison is blocked; the benchmark harness, no-op/fake path, ranking, context, and lookup work can still proceed independently, and no reranker quality claim may be reported.
- **FR-007**: The only Golden v0 questions permitted in Phase C are `gq-sp-001`, `gq-cmp-001`, `gq-conf-001`, `gq-gap-001`, and `gq-ins-001`. The other 16 questions MUST remain unopened and excluded from tuning and comparison. No model fine-tuning, threshold selection, prompt tuning, or model selection on any Golden v0 question is allowed. This five-question run is diagnostic, not a release quality estimate.
- **FR-008**: Benchmark reports MUST include per-question and macro Recall@K, Evidence Hit@K, and applicable MRR at K=1,3,5,10,20 subject to candidate availability; per-question type; counts/denominators; evidence matching method; failures; and identical candidate pool hashes. Insufficient-evidence questions are reported separately without positive Recall/MRR, consistent with `RETRIEVAL_EVALUATION_PROTOCOL.md`.
- **FR-009**: For diagnostic recommendation only, the predeclared comparison must show at least +0.05 absolute macro MRR@10 OR +0.10 absolute macro Evidence Hit@5 versus RRF, no >0.05 absolute regression in either other applicable aggregate, and measured warm p95 reranking latency no more than 2.0x RRF-only ranking p95 and no more than 1,000 ms on the recorded reference Windows machine. Cold model load is reported separately. These are screening criteria, not a production enablement. They treat latency as a measured bounded screening cost, not a claim that reranking improves total RAG latency. Production remains disabled unless later explicitly approved. Given only five diagnostic questions, passing is not a general quality claim.
- **FR-010**: Context selection MUST consume the post-diversity sequence and an explicit nonnegative integer token budget plus an injected deterministic `TokenCounter` carrying a version/model identity. It MUST require exact identity match with the caller's configured context tokenizer; no guessed tokenizer or reuse of the pilot's `utf8-bytes-div3-v1` estimator as an LLM tokenizer is permitted.
- **FR-011**: Selection MUST perform one ranked-order greedy pass: include a whole candidate if its independently counted text tokens fit remaining budget; otherwise record `exceeds_remaining_budget` and continue to later candidates. It MUST return selected candidates in original order, exact total counted tokens, budget, counter identity, and ordered omissions. No text truncation, mutation, or provenance loss is permitted. Caller reserves prompt/system overhead before supplying the evidence budget.
- **FR-012**: Evidence lookup MUST provide three explicit lookup paths: normalized DOI; DOI plus exact opaque stable source locator; and exact lowercase 64-hex chunk ID. DOI-only lookup returns one paper record; DOI+locator returns all matching chunk evidence whose primary locator or a span locator exactly equals the locator; chunk ID returns zero or one chunk. No fuzzy locator parsing or text search is included.
- **FR-013**: All lookup operations MUST resolve rows from one read-only PostgreSQL REPEATABLE READ snapshot of the active import; the active import ID, delivery digest, source contract version, and corpus version must be returned with every found result. Never resolve against inactive imports or mix snapshot identity. Missing and malformed identifiers have separate typed errors/outcomes; not-found is not a database failure.
- **FR-014**: DOI normalization MUST reuse the accepted Phase B normalization semantics and shared helper; source locator is opaque and compared byte-for-byte after JSON string validation; chunk ID is lowercase 64-hex exact match. Do not alter or migrate the Person 1 delivery schema.
- **FR-015**: No Phase C field is added to `docs/contracts/retrieval-v1.md` or a public DTO unless Person 2/3 and affected owners explicitly review the additive contract. Keep these features behind private Person 2 interfaces until the P1-11/P1-14 gate is satisfied. Do not reopen or change Feature 007.
- **FR-016**: Preserve the accepted pilot exactly at 17 papers, 319 sections, 728 chunks, and 728 embeddings, as well as accepted Phase A/B evidence. Database checks and any necessary non-destructive fixtures MUST first verify the actual target is exactly `sciscope_test_005`; run natively with Windows PowerShell, Python 3.12/uv, PostgreSQL 17 and pgvector 0.8.7. No main database changes, schema migrations, destructive operation, Docker, WSL, paid call, commit, push, or merge request is in scope.
- **FR-017**: Behavior tests MUST be written before application implementation and demonstrate RED before GREEN. Use independent pure oracles for ranking, reranking validation, token totals, and identifier lookup. Real PostgreSQL integration tests are required for active snapshot lookup and exact DOI/locator/chunk resolution on `sciscope_test_005`; test writes must be rollback-scoped or otherwise demonstrably non-destructive.
- **FR-018**: Record actual commands/results/limitations in `EVIDENCE.md`, synchronize P3-09 through P3-12 in `PROJECT_TODO.md`, and do not check tasks complete until automated and human verification and explicit acceptance are recorded.

### Key Entities

- **RankedCandidate**: Phase B retrieval result plus immutable base rank and exact duplicate key.
- **RankedEvidence**: duplicate-free candidate with base score/rank, optional reranker score, snapshot identity, and deterministic exclusion metadata.
- **RerankerRun**: pinned local model/runtime identity, candidate/query hashes, per-candidate scores, quality metrics, and latency observations.
- **TokenBudgetSelection**: ordered selected evidence, ordered omissions/reasons, exact total, budget, and tokenizer identity.
- **EvidenceLookupResult**: found paper/chunk material and the active corpus provenance captured for the lookup.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Independent ranking oracle and repeated-run tests return the same IDs/order for all fixed fixtures; identical DOI/primary-locator/text groups retain exactly one deterministic representative while different text or locator values remain separate.
- **SC-002**: The approved per-DOI cap is applied consistently after reranking, with no DOI exceeding the cap and all exclusions reported.
- **SC-003**: Reranker validation rejects missing/extra/duplicate IDs, NaN/Infinity, and unstable score/order outputs; no-op preserves base order exactly.
- **SC-004**: The benchmark reproduces from an offline run manifest on the fixed five IDs, records all required quality and latency observations, and never reads the 16 held-out questions.
- **SC-005**: Production reranking remains disabled unless all FR-009 quality and latency gates pass and a separate explicit approval is recorded.
- **SC-006**: Every returned context has a tokenizer identity match, exact independently recomputed token total not exceeding budget, original text and provenance unchanged, and deterministic omissions.
- **SC-007**: Each lookup selector resolves the correct record or explicit not-found in a single active snapshot; a concurrent activation fixture cannot mix corpus identity or return inactive rows.
- **SC-008**: Native Windows automated checks and real database tests pass; the authorized database's accepted counts remain 17/319/728/728 with no schema change.
- **SC-009**: User receives concise independent read-only PowerShell checks, expected output and pass/fail rules, then separately verifies and explicitly accepts before Phase C is closed.

## Assumptions

- Feature 007 P3-05 through P3-08 remain accepted and frozen; its private core supplies stable ranked results, text, DOI, and primary locator. Phase C does not depend on adding span data to its result.
- The accepted Phase A delivery 0.3.0 schema is sufficient for lookup and requires no migration.
- English is the approved five-question smoke language. The proposed MiniLM checkpoint is a single fixed candidate for an initial comparison, not a search space for model tuning.
- A deterministic caller-provided tokenizer is necessary because downstream generation-model identity is not approved in the proposed retrieval contract.
- All added external package/model-artifact requirements need explicit feature approval and Windows compatibility verification before implementation.
- Person 2 approved the Phase C specification and plan on 2026-11-19 with the refinements in the latest user message: configurable diversity cap defaulting to 2 with explicit disable/adjust; P3-10 offline no-op/fake/benchmark and technically feasible optional MiniLM, no network downloads or held-out data, thresholds diagnostic only; strict tokenizer identity injection without guessing Gemini; exact lookup with active-snapshot provenance; proposed downstream handoff docs remain pending owner review.
