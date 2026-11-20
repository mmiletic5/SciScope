# Feature Specification: Retrieval v2 BM25 and Reranking

**Feature Branch**: `010-retrieval-v2`  
**Created**: 2026-11-20  
**Status**: Approved for implementation by owner on 2026-11-20  
**Input**: Owner request to add selectable v2 lexical/hybrid retrieval.

## User Scenarios & Testing

### User Story 1 — Select v2 without changing v1 (Priority: P1)

As Person 3, I can request v2 retrieval while existing v1 callers and results remain compatible.

**Independent Test**: contract tests accept the approved v2 selector and prove all v1 request/response behavior remains unchanged; v2 results preserve current provenance DTOs.

### User Story 2 — Retrieve with dense plus BM25 and RRF (Priority: P1)

As a scientific user, a hybrid search can retrieve semantic and exact lexical evidence from the same frozen corpus and filters.

**Independent Test**: deterministic offline corpus fixtures verify BM25 candidate ranking, candidate union, RRF contribution, stable tie ordering, filtering, and metadata identity.

### User Story 3 — Rerank merged candidates and compare fairly (Priority: P1)

As Person 2, I can compare frozen v1 against opt-in v2 on approved development questions and report reproducible retrieval quality and cost.

**Independent Test**: on the exact same query text, corpus, filters, gold labels, and candidate availability, produce per-question Recall@5/10/20, MRR@10, nDCG@10, latency, and DOI attribution results for both profiles.

## Acceptance Scenarios

1. v1 requests continue to use the unchanged PostgreSQL FTS, dense, or RRF path and cannot activate v2 implicitly.
2. v2 lexical candidates come from BM25Okapi over exactly the active corpus chunks and apply the same eligibility filters and chunk-to-paper metadata constraints.
3. v2 hybrid fuses dense and BM25 ranked lists with the existing deterministic RRF implementation; each branch is bounded by an explicit, validated candidate pool.
4. The reranker receives the RRF merged pool before final top-k and token-budget selection; it may only reorder candidate IDs, and errors fail visibly without silent fallback.
5. Result DTOs retain DOI, source locator, chunk identity, filters, and corpus provenance; no database schema or migration is introduced.
6. Evaluation uses only the eight preapproved development questions, reports per-question and aggregate results, and makes no held-out or statistical-generalization claim.
7. Results contain the complete chunk passage, stable chunk ID, paper title, DOI, precise source locator, one-based final rank, and applicable branch/fusion scores. Downstream citations must resolve to returned chunk IDs and their exact source metadata; ranker scores are not confidence probabilities.
8. Empty retrieval returns an empty result list with the established empty-result warning and is not itself interpreted as scientific insufficient evidence. Multi-paper workflows may use multiple relevant retrieved sources without forced irrelevant diversity.

## Requirements

- **FR-001**: Preserve PostgreSQL 17, pgvector, frozen corpus identity, embedding model/configuration, dense retrieval, RRF behavior, filters, DOI metadata, token budget, and every v1 baseline.
- **FR-002**: Add lexical BM25 using pinned `rank-bm25` `BM25Okapi` over the existing active 728 chunks; no new database/index framework. Reuse active corpus and metadata joins; do not persist a BM25 index.
- **FR-003**: Add a separately selectable v2 profile using `contract_version: "retrieval.v2"` without changing the meaning or default of any v1 mode. Keep the request/response shape and mode names; under v2, `lexical` selects BM25Okapi and `hybrid` selects dense + BM25Okapi + existing RRF. The local reranker is independently configurable at Person 2 service construction so unreranked and reranked v2 arms can be compared; no request-time model-selection field is added.
- **FR-004**: Fuse dense and BM25 candidate ranks with the existing RRF function and existing frozen RRF constant. Deterministic order uses existing policy or an explicitly tested v2 tie rule.
- **FR-005**: When a local reranker is configured, rerank the full bounded RRF union using existing `MiniLMCrossEncoderReranker`, `sentence-transformers`, and the canonical pinned model `cross-encoder/ms-marco-MiniLM-L6-v2`; preserve fail-closed output validation. When no reranker is configured, retain RRF order. No model training or homegrown ranker.
- **FR-006**: Apply existing final selection, filters, DOI diversity behavior if present in the caller, and token-budget logic after reranking; do not truncate the pool before reranking beyond the declared candidate limit.
- **FR-007**: Keep model/dependency setup local, free, pinned, and Windows/Python 3.12 compatible. The adapter must remain offline at runtime and must not auto-download weights.
- **FR-008**: Compare v1 and v2 only on approved development question IDs. Never load v0-HO or v1-HO records or use protected outcomes for selection, tuning, debugging, or model selection.
- **FR-009**: Report per-question and macro Recall@5/10/20, MRR@10, nDCG@10, latency, and DOI attribution correctness with explicit metric denominators, missing-ground-truth handling, repetitions, and configuration identity. Reuse existing Recall/MRR definitions and `ir-measures` where compatible; independently verify nDCG semantics with synthetic oracles.
- **FR-010**: Preserve Phase C's negative MiniLM benchmark in evidence; the v2 result is a new development-only comparison and cannot erase or rewrite prior evidence.
- **FR-011**: Keep v1 and v2 independently callable in private Person 2 code and preserve Person 3 response shape. The owner approved `retrieval.v2`; Person 3 application enablement still requires their integration approval.
- **FR-012**: No database writes/migrations, frozen data changes, paid APIs, Docker/WSL, commits, pushes, or MRs.

## Metric and dataset policy

- Development population: only the five pre-exposed Golden v0 development/smoke questions and the three approved Golden v1 development questions (n≤8), restricted to positive-answerable questions for Recall/MRR/nDCG when positive relevant units exist. Insufficient-evidence questions are reported separately and do not enter positive retrieval metric denominators.
- No held-out record, text, hash, label, or result may enter tuning or this comparison. Preserve frozen partitions byte-for-byte.
- Recall@K uses the existing canonical evidence-unit matcher: unique matched relevant gold evidence units retrieved by rank K divided by total unique answerable relevant gold evidence units. It is bounded [0,1]. MRR@10 is reciprocal rank of first matched relevant unit, zero if none; only eligible positive questions. Report macro means over eligible questions, with denominator n for each metric.
- nDCG@10 uses binary relevance per unique retrieved evidence unit, gain 1 for a relevant evidence unit and 0 otherwise, logarithmic discount `1/log2(rank+1)`, ideal ranking built from the same question's unique gold units, zero if no relevant unit in the eligible question. Confirm the chosen `ir-measures` measure matches this oracle before reporting.
- DOI attribution correctness is the proportion of unique returned chunks whose normalized DOI equals the frozen chunk-to-paper DOI mapping from the same active corpus snapshot; report numerator/denominator across returned items and per question. It measures attribution integrity, not scientific relevance.
- Latency reports separate BM25 build time, query scoring, dense query+DB time, RRF, reranker inference, final selection, end-to-end time; report cold model load separately and warm repeated runs (5 measured passes after one warmup), median/p95/max and hardware/runtime identity. No unmeasured performance claim.
- Before/after comparisons are descriptive on n≤8; show every per-question result and do not claim significance or external validity.

## Non-goals

No held-out evaluation, tuning on held-out questions, query-embedding generation, new retriever/model/tokenizer/metric framework, model training, BM25Plus sweep absent preregistered justification, schema/database changes, shared contract change without approval, answer generation, production enablement, or rewriting Phase A–D historical evidence.

## Dependencies and approval gates

The owner approved this specification/plan, the additive `retrieval.v2` request/response version, and download of the pinned official model checkpoint. The current `retrieval.v1` contract remains unchanged. Person 3 application integration still requires that owner's integration approval. No held-out authorization is requested or implied.
