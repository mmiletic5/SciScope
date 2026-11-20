# Person 2 Retrieval v2 Handoff for Person 3

**Status:** Person 2 implementation and verification complete; application
integration is not enabled and requires Person 3's integration review.

## Selection and compatibility

The request and response field shape and the existing `dense`, `lexical`, and
`hybrid` mode names remain unchanged. Set `contract_version` explicitly to
`retrieval.v2` to select BM25 for `lexical` and dense+BM25+RRF for `hybrid`.
The default remains `retrieval.v1`; v1 dense, PostgreSQL FTS, and FTS+RRF
behavior are unchanged. Unknown contract versions fail closed. Reranking is
configured when constructing the Person 2 core/service; there is no
request-level model override.

Person 2 currently exposes this as the internal `_RetrievalCore`; the package
does not export a public `RetrievalService` facade. Person 3 can wrap the core
behind their existing API adapter after reviewing this handoff. This handoff
does not itself approve application enablement or modify Person 3-owned code.

```python
request = {
    "contract_version": "retrieval.v2",
    "request_id": "explorer-v2-0001",
    "query_text": query_text,
    "mode": "hybrid",
    "top_k": 5,
    "ranking": {"candidate_pool_size": 50},
}
response = retrieval_core.retrieve(request)
```

Set `candidate_pool_size` no lower than `top_k`. The current validated range is
1–250 and must be at least `top_k`. If omitted for hybrid, the core uses
`min(eligible_count, min(250, max(50, 5 * top_k)))`. Dense and BM25 each return
up to that pool. RRF merges their unique chunk-ID union (up to twice the pool);
an enabled reranker sees that entire union before final `top_k` truncation.
The tested production-compatible v2 profile is BM25+RRF without MiniLM;
MiniLM is independently configurable but should remain off by default given
the measured development results.

## Result evidence and citations

Each result carries:

- `rank`: one-based final retrieval order (after RRF and optional reranking).
- `chunk_id`: stable 64-character lowercase SHA-256 identity.
- `text`: complete persisted chunk text, not a generated paraphrase.
- `doi` and `paper.title` (plus paper bibliographic metadata).
- `source_locator`, `section_id`, `section_path`, and normalized section type.
- `scores.dense_rank`, `scores.lexical_rank`, and `scores.fusion_score` when
  applicable. BM25's component score is also present for lexical results.
- Response-level `corpus` provenance, active filters, `candidate_pool_size`,
  and `rrf_constant` when applicable.

Scores are ranking signals. BM25, RRF, cosine similarity, and cross-encoder
scores are not calibrated confidence probabilities. The final rank is the
ordering signal to use downstream.

When an answer cites retrieval evidence, resolve every cited `chunk_id` against
the actual response's `results`; cite its returned DOI, title, section/source
locator, and exact passage. Do not fabricate citations from a paper that was
not retrieved. Person 2's development benchmark independently checked each
returned ID against `EvidenceLookup.get_chunk` on the same frozen snapshot and
compared exact chunk text, DOI, and locator. Citation mapping is identity
validation, not a scientific relevance or answer-correctness judgment.

No forced DOI diversity is applied in the retrieval core. For comparison,
conflict, or research-gap outputs, downstream logic may use multiple relevant
papers when they were retrieved; it must not pad the result with irrelevant
papers or infer genuine contradiction from ranking scores.

## Empty and insufficient-evidence behavior

When a lexical query has no token matches, or no mode has eligible candidates,
the response is successful with `results == ()` and `warnings ==
("EMPTY_RESULT",)`. A nonempty result with no gold evidence is not a failure
signal either. Retrieval emptiness and scientific answerability are separate:
the caller must use the validated question/evidence policy and must not label
an empty retrieval response as proof that the literature has insufficient
evidence.

Validation and database failures continue to use the existing typed, sanitized
retrieval errors. A configured reranker failure returns a retrieval error; it
does not silently fall back to RRF order.

## Context token budget

The retrieval core returns ranked full chunks and does not itself spend the
generation prompt's token budget. Feed its final order into the existing
Person 2 context selector after downstream prompt overhead is reserved. Keep
the exact configured tokenizer identity and use whole passages:

```python
ranking = rank_evidence(response.results, max_per_doi=None)
context = select_context(
    ranking.candidates,
    budget_tokens=evidence_budget,
    token_counter=token_counter,
    expected_counter_id=token_counter.counter_id,
)
```

`max_per_doi=None` preserves all retrieved paper sources for workflows that
compare multiple studies. The selector processes candidates in the order it
receives, includes only complete passages that fit, and records omissions and
exact token accounting. The v2 ordering therefore precedes token selection.

## Verified behavior and limitations

On the five approved Golden v0 development questions, dense achieved Recall@5/
10/20 of .750/.875/1.000; dense+BM25 RRF achieved .625/.875/1.000; and
RRF+MiniLM achieved .625/.750/.875. Macro MRR@10 was .521/.421/.375 and nDCG@10
was .582/.536/.472, respectively. MiniLM median end-to-end latency was about
4.25 seconds on CPU. This small development sample does not establish a general
quality win; MiniLM remains optional and the historical Phase C negative result
is preserved. Full per-question values, other arms, configuration identity,
and limitations are in
[`RETRIEVAL_V2_RESULTS.md`](RETRIEVAL_V2_RESULTS.md).

The read-only PostgreSQL 17 integration suite and offline tests passed; see
`EVIDENCE.md` for exact native Windows commands and exit codes. The private
core/API boundary and Person 3 application wiring still require integration
review. Do not turn v2 on in a shared application before that review.

## Evidence quality, completeness, and safe generation boundary

The five-question development diagnostics are exploratory and not a scientific
reliability estimate. The frozen set includes only one query for each represented
question type, and its evidence annotations are not exhaustive relevance
judgments. The focused selector experiment compares dense v1, dense+BM25 RRF,
RRF+MiniLM, a temporary MMR selector, and a DOI-cap stress control. It found
that MMR improved macro MRR/nDCG but reduced all-required-evidence@20 from 1.0
to .75, and missed one of two required comparison passages. The DOI cap missed
the two required same-paper passages in the conflicting-evidence query. Neither
selector is a safe default. Dense v1 is the simplest defensible reference on
this sample; v2 remains opt-in and MiniLM remains disabled by default. Exact
per-question and aggregate results are in
[`RETRIEVAL_V2_EVIDENCE_SELECTION_EXPERIMENTS.md`](RETRIEVAL_V2_EVIDENCE_SELECTION_EXPERIMENTS.md).

Evidence-unit Recall@k and Evidence Coverage@k are the same statistic under the
current annotations. All-required evidence and required-source coverage add
separate completeness checks, but DOI coverage does not prove scientific
complementarity. There are no annotated conflict-side groups, so this sample
cannot measure opposing-findings completeness or genuine-conflict sensitivity.
The research-gap case's retrieval coverage does not validate a generated gap.

For downstream answer generation, resolve citations only to result IDs in the
same retrieval response and preserve exact passage text, chunk ID, DOI, paper
title, source/section locator, and corpus provenance. Retrieval scores and
citations do not establish claim support or evidence sufficiency. Generation
must check each claim against the returned passage, distinguish comparable
contradictory findings from non-equivalent contrasts, and state when the
available retrieved sources do not support a reliable answer. It must not
invent facts, citations, conflict explanations, or hypotheses. Keep answer
accuracy, citation entailment, comparison/complementarity, conflict quality,
and hypothesis quality as separate downstream evaluation targets.

The upstream frozen corpus contains paragraph chunks. Tables, figures,
formulas, lists, and boxed text are known representation limits; no source
evidence ties them to the development misses, and original XML is unavailable
for independent reparse. Any future extraction/chunking/metadata/embedding
change requires a separately versioned proposal and corpus, validated against
raw source material. The frozen pilot must not be modified in place. A larger
evaluation set should include independently reviewed multi-question strata,
required evidence/source groups, negative judgments, true and apparent
conflicts, corpus-bounded insufficient-evidence cases, document-structure
coverage, and a sealed test cohort sized by a pre-registered precision or power
goal. Question-type routing is not justified by the current sample.

An empty or incomplete retrieval result may reflect omitted source structure in
the corpus, rather than absence of scientific evidence. In particular, the
current paragraph-only index does not represent table cells, figure captions or
image-derived information, formulas, list items, or supplementary material.
This is a plausible coverage limitation, not a confirmed explanation for the
observed development misses. See
[`RETRIEVAL_V2_PERSON1_CORPUS_HANDOFF.md`](RETRIEVAL_V2_PERSON1_CORPUS_HANDOFF.md)
for verified omission rules/counts and a versioned future-ingestion and
evaluation proposal. Do not claim evidence is absent from the literature based
only on an empty retrieval response.
