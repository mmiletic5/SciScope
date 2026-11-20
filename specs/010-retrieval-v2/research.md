# Retrieval v2 Research

**Status:** Research and implementation evidence recorded; see the approved
specification, plan, task tracker, and Retrieval v2 results. The original
pre-implementation facts below are retained as a dated research snapshot.

## Problem and existing project state

The accepted private retrieval core has dense pgvector, PostgreSQL English FTS lexical, and deterministic RRF hybrid modes. The strict `retrieval.v1` request contract accepts only `dense`, `lexical`, and `hybrid`. Phase C provides a `MiniLMCrossEncoderReranker` adapter and ranking pipeline, but the measured Phase C benchmark was negative and production reranking remains disabled. This feature proposes a separately selectable experimental profile; it must leave v1 behavior, frozen data, and existing results unchanged.

## Approaches

1. **PostgreSQL FTS only:** no dependency or new index; existing zero-Recall@20 result is a serious limitation for exact terms. Does not satisfy requested BM25.
2. **`rank-bm25` over the existing 728 chunk rows:** small, pure-Python package and no new database/index framework. Use BM25Okapi first; no BM25Plus comparison unless a preregistered development result justifies it. Package release 0.2.2 is Apache-2.0, universal wheel, but old (2022) and has no PyPI provenance attestation; pin exact artifact/hash and review dependency metadata. [PyPI package](https://pypi.org/project/rank-bm25/0.2.2/)
3. **Cross-encoder rerank after RRF:** reuse the existing adapter and candidate identity validation, rather than implementing a model. The canonical model ID is `cross-encoder/ms-marco-MiniLM-L6-v2` (the requested spelling `...L-6-v2` is not the model repository name). The official model card describes Sentence Transformers use, English MS MARCO passage ranking, and Apache-2.0. [Hugging Face model card](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2)

## Recommended design

Keep all v1 modes untouched. Add a v2-only hybrid profile: dense candidates and in-memory BM25Okapi candidates over the same active 728 chunks and filters, fused by the accepted RRF implementation, then passed through the existing local reranker adapter over the merged candidate pool before final top-k and existing token-budget selection. Reuse existing result DTOs and provenance fields. No schema, migration, database write, training, or replacement retrieval framework.

For nDCG@10, `ir-measures` provides established measure semantics; the published `pytrec-eval-terrier` 0.5.11 artifact includes a CPython 3.12 Windows x64 wheel. Keep existing project Recall/MRR definitions as the authority and independently cross-check compatible cutoffs with `ir-measures`. [ir-measures](https://pypi.org/project/ir-measures/), [Windows wheel](https://pypi.org/project/pytrec-eval-terrier/0.5.11/)

## Verified local facts and unknowns

The following facts were recorded before the owner-authorized implementation;
where later execution evidence differs, the later result below supersedes the
pre-implementation snapshot without deleting its history.

- Local environment metadata: Python 3.12; `sentence-transformers` and CPU `torch` are installed; `rank-bm25` and `ir-measures` are absent.
- Neither standard Sentence Transformers nor Hugging Face model cache location contains the MiniLM checkpoint. The existing adapter refuses network fetching and requires an immutable revision and directory SHA-256.
- Hugging Face lists the model's `model.safetensors` at 90.9 MB, before tokenizer/config files. This is a substantial download and requires explicit authorization under the user's stop conditions. [Model repository files](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2/tree/main)
- `uv` is discoverable on PATH, but a prior invocation failed with Windows “Access is denied”; a working approved uv invocation is not yet verified. Do not install packages until the feature plan is approved and this is resolved without bypassing host controls.
- Eight development question slots are identified by the prior frozen methodology (five previously exposed v0 development questions and v1 Q1/Q4/Q6). Content remains protected and was not opened in this research. Sample size and topic diversity are inadequate for strong generalization claims; reports must show per-question results and avoid statistical-significance claims. No held-out question may be accessed for selection/tuning.
- Exact v2 request/interface strategy remains a material shared-contract decision. `retrieval.v1` is strict and cannot accept a new mode. Any Person 3 selection requires a reviewed additive shared interface/version; private-only selection can be implemented without exposing v2 to Person 3 but would not satisfy end-to-end API selection.

## Recommendation and limitations

Use BM25Okapi from pinned `rank-bm25`, existing RRF, and the existing pinned MiniLM adapter. Keep v2 opt-in and v1 unchanged. The actual development comparison used the five previously approved Golden v0 development questions because only their compatible cached vectors were available; the three Golden v1 development vectors were not generated. Results are recorded in [`../../docs/person2/RETRIEVAL_V2_RESULTS.md`](../../docs/person2/RETRIEVAL_V2_RESULTS.md). On this small diagnostic sample, BM25 and dense+BM25 RRF did not improve overall macro metrics over dense, and MiniLM reduced retrieval metrics while adding about 4.1 seconds median CPU latency. Keep the reranker optional/off by default. These findings do not establish held-out performance or generalization. The Phase C negative MiniLM evidence remains intact.

## Gates at research time and current disposition

1. Owner approval of specification and plan: obtained 2026-11-20.
2. Additive `retrieval.v2` selection boundary: owner-approved; Person 3 application integration remains pending their review and is not enabled.
3. Model download and dependency setup: explicitly approved and completed; pinned local checkpoint hash and CPU offline inference are recorded in `EVIDENCE.md`.
4. The owner reports `uv run --locked` works in their Windows environment. Direct invocation from this agent execution context still returns Windows Access Denied; no security workaround was used. Dependencies and inference were verified in the existing `.venv`.
5. Protected cohorts were not accessed for the Retrieval v2 comparison. No T006 retrieval was rerun as part of this feature.
