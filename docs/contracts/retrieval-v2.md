# Person 2 Retrieval Contract `retrieval.v2`

**Status:** Owner-approved version boundary for Person 2 implementation on
2026-11-20. Person 3 application integration remains pending their review.
The existing `retrieval.v1` contract and behavior are unchanged.

## Compatibility and selection

The request and response fields, validation limits, result fields, provenance,
error categories, and mode names remain the `retrieval.v1` shape. Set
`contract_version` to exactly `retrieval.v2` to select the v2 behavior. The
service echoes `retrieval.v2` in its response. Unknown versions still fail
closed.

| Mode | `retrieval.v1` | `retrieval.v2` |
|---|---|---|
| `dense` | Existing pgvector cosine retrieval | Same dense retrieval |
| `lexical` | Existing PostgreSQL English FTS | In-memory `rank-bm25` BM25Okapi over the active eligible chunks |
| `hybrid` | Existing dense + PostgreSQL FTS + RRF | Existing dense + BM25Okapi + the same RRF constant and tie ordering |

No default or interpretation changes for `retrieval.v1`. No Person 3-owned
source or application setting is changed in this implementation. Person 3 must
review and approve application enablement separately.

## v2 BM25 behavior

- Read only the active snapshot's eligible chunk ID and exact text rows in the
  same repeatable-read, read-only retrieval transaction. In hybrid mode, join
  the active `EmbeddingSet` rows so dense and lexical branches use the same
  candidate-eligible population.
- Build `BM25Okapi` with the pinned `rank-bm25` dependency in memory. The small
  adapter uses case-folded whitespace-delimited terms; BM25 scoring comes
  exclusively from the established library. Do not persist an index or cache
  query text.
- Return only chunks containing at least one query token; sort score descending
  and chunk ID ascending for stable ties. Blank and no-match queries return an
  empty result.
- Apply the existing metadata filters and `top_k`/candidate-pool validation.
  No corpus, schema, or database changes are required.

## v2 hybrid and reranker

- Dense and BM25 branches each return up to the validated candidate pool (same
  pool and active eligibility filters). Existing deterministic RRF combines
  branch ranks and constructs the complete unique union, up to twice the pool.
- If no reranker is configured on the Person 2 service, return RRF order
  truncated to final `top_k` (the v2 BM25+RRF arm).
- If a reranker is configured, pass the full RRF union to the existing
  `rank_with_reranker`/`MiniLMCrossEncoderReranker` path before final `top_k`.
  Existing exact duplicate-evidence suppression is applied by that adapter;
  the v2 core does not impose the Phase C per-DOI cap. Invalid scores or model
  errors fail the request without silently falling back.
- Model loading remains local-only, CPU, pinned revision and directory SHA-256.
  This contract does not add a request-level model selector. The v2 benchmark
  can compare service instances with no reranker and with the pinned MiniLM.
- The Person 3 answer/context pipeline receives the final ranked result list;
  any token-budget selector consumes that list downstream. No context budget
  logic or result DTO is changed here.

## Example request

```json
{
  "contract_version": "retrieval.v2",
  "request_id": "explorer-v2-0001",
  "query_text": "How does viral infection affect honey bee homing?",
  "mode": "hybrid",
  "top_k": 5,
  "ranking": {"candidate_pool_size": 50}
}
```

## Error and data behavior

Use existing `INVALID_REQUEST`, `UNSUPPORTED_CONTRACT_VERSION`, database,
embedding, and retrieval internal errors. The v2 retrieval transaction is
read-only. Dense/hybrid uses the existing compatible query embedder; BM25-only
does not call the embedder. No query embedding is generated or cached by this
contract. Active corpus identity, DOI/source metadata, and result provenance
remain sourced from the same database snapshot as v1.

## Person 3 handoff and measured development results

The exact Person 3 integration mapping, citation rules, empty-result behavior,
and downstream token-budget usage are documented in
[`../person2/RETRIEVAL_V2_PERSON3_HANDOFF.md`](../person2/RETRIEVAL_V2_PERSON3_HANDOFF.md).
The five-question development-only comparison and limitations are in
[`../person2/RETRIEVAL_V2_RESULTS.md`](../person2/RETRIEVAL_V2_RESULTS.md).
These documents do not enable v2 in Person 3's application; that integration
remains subject to their review.
