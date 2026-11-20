# Phase C Solution Research

**Date:** 2026-11-19  
**Scope:** P3-09 ranking/duplicates/diversity; P3-10 reranker benchmark; P3-11 context budgeting; P3-12 evidence lookup.

## Problem and constraints

Phase B is accepted and closed. Phase C must consume its stable retrieval result and existing RRF ordering without duplicating dense/lexical retrieval, filters, or fusion. Pilot size remains 17 papers / 319 sections / 728 chunks / 728 vectors. Only the five approved development smoke IDs may be used; the other 16 Golden v0 questions are held out for Phase D. Work must run on native Windows 10 x64/PowerShell/Python 3.12 and use only `sciscope_test_005` for database integration. No schema migration or shared facade adoption is authorized by planning.

## Repository facts

- `src/sciscope/retrieval/_core.py` provides the accepted private retrieval path; `_ranking.py` owns deterministic Phase B RRF. Phase C should compose after this result rather than alter it.
- Persisted chunk records contain `chunk_id`, normalized `doi`, text, primary `source_locator`, ordered JSON `spans` with source locator and offsets, and `text_sha256`; the private Phase B result currently exposes ID, DOI, text, and primary locator (not spans). The active import contains digest and delivery version. Phase C deduplication uses only already-returned fields and does not modify Feature 007.
- DOI is already normalized by accepted delivery semantics. Locator is opaque and bound to the source XML digest; exact string matching is safe and avoids inventing locator grammar.
- Pilot `content_token_count` was produced by `utf8-bytes-div3-v1`, an explicitly conservative embedding-side estimator, not the eventual generation model tokenizer. Reusing it as exact LLM budgeting would overclaim.
- `docs/contracts/retrieval-v1.md` is still a proposed shared contract. Its Phase B response intentionally excludes reranker, selection, and lookup fields. Phase C internals can remain private until shared contract review.
- Existing evaluation protocol supplies matching and metrics but reports 21-question limitations. It explicitly reserves 16 Golden v0 questions for Phase D.
- The accepted pilot query embedding identity is OpenAI `text-embedding-3-small`; no approved compatible cached query vectors or five-question hybrid candidate dump was found in the inspected artifacts. Creating those vectors through the live provider would be a paid call and is explicitly out of scope. This blocks an actual reranker quality comparison until compatible inputs are supplied/authorized, but does not block the independent private components or benchmark harness.

## Options and recommendation

### Stable ranking, duplicate handling, diversity

1. **Deduplicate by DOI + primary locator**: simple, but incorrect where multiple chunks share a paragraph locator at different offsets.
2. **Deduplicate by chunk ID only**: already guaranteed by Phase B branch union and does not suppress duplicate evidence under separate IDs.
3. **Recommended: exact returned-evidence key** `(normalized DOI, primary source locator, exact text)`; retain the first candidate in accepted base order, chunk ID as final deterministic tie. This uses only accepted Phase B result fields and never reopens or extends Feature 007. Distinct text at a shared paragraph locator remains distinct. Apply a deterministic max two selected results per DOI after reranking, report exclusions. The cap is an explicit proposed policy requiring approval because it can trade within-paper recall for source diversity.

### Reranking

1. **No-op only**: zero dependency and preserves accepted RRF; offers no measured reranker comparison.
2. **Local cross encoder `cross-encoder/ms-marco-MiniLM-L6-v2`**: official model card documents Sentence Transformers use, English support and Apache-2.0 metadata. Sentence Transformers `CrossEncoder` accepts query/passage pairs and batch prediction; this is a suitable compact, local candidate for the English smoke set. Model checkpoint must be pinned by immutable revision and SHA-256; offline benchmark requires a pre-populated local checkpoint and network-disabled execution.
3. **Larger multilingual cross encoder**: e.g. BAAI `bge-reranker-v2-m3` is Apache-2.0 but materially larger; the five smoke questions are English, so multilingual capacity is not needed for this diagnostic and increases CPU latency risk.

**Recommendation:** implement an adapter protocol plus deterministic fake and no-op; benchmark only the pinned MiniLM candidate against the exact same top 50 RRF candidates. Keep the model/deep-learning package in an optional, separately pinned benchmark dependency group rather than the base application runtime, subject to plan approval and native Windows smoke verification. Do not fine-tune, sweep models, or alter thresholds on Golden v0. Report quality and warm/cold latency separately. Even if the screening thresholds pass, five questions do not establish general superiority; production remains a separate approval.

Sentence Transformers documents `CrossEncoder.predict` batching and pairwise ranking. PyTorch's official installation page currently says Windows supports Python 3.10–3.14; the project uses 3.12. This establishes current stated Python compatibility, not successful installation on this specific Win10 machine or its hardware/driver combination. Model-page metadata reports Apache-2.0. Runtime dependencies and checkpoint are not present in `pyproject.toml` today.

### Context token budgets

1. **Use persisted chunk token count**: fast, but it is `utf8-bytes-div3-v1`, an embedding/chunk estimator and not guaranteed equal to a downstream generation tokenizer.
2. **Count with an assumed tokenizer**: repeatable but can silently mismatch the generator model.
3. **Recommended: injected `TokenCounter` with immutable counter/model identifier**. Callers pass a budget already reduced for system/prompt overhead. Fail on unknown/mismatched counter identity. Greedy ranked-order whole-item selection accepts fitting passages, skips over-budget items and continues, returning exact total and omission reasons. No silent truncation or text rewrite.

### Evidence lookup

1. **Fuzzy locator parsing/quote search**: risks returning a near match and assumes locator grammar that Person 1 has not promised.
2. **Exact selectors against the captured active import**: normalized DOI for paper; `(DOI, exact opaque locator)` for all chunks with primary or span locator equality; exact lowercase 64-hex chunk ID for one chunk. Return active delivery/corpus provenance with every found result. This uses existing indexes/JSON span fields and requires no schema change. Recommended.

## Sources (checked 2026-11-19)

- Sentence Transformers CrossEncoder reference, prediction API and pair scoring: https://sbert.net/docs/package_reference/cross_encoder/model.html
- Sentence Transformers installation guidance (Python 3.10+; PyTorch 2.2+ recommendation): https://www.sbert.net/docs/installation.html
- PyTorch official Windows installation compatibility statement: https://pytorch.org/get-started/locally/
- Candidate model card and Apache-2.0 metadata: https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2
- Alternative multilingual model card and Apache-2.0 metadata: https://huggingface.co/BAAI/bge-reranker-v2-m3

## Facts, assumptions, and unresolved gates

- **Verified facts:** the above model/library documentation; accepted schema fields; accepted five/16 Golden partition; accepted Phase B/private boundary.
- **Initially proposed and approved by the owner:** exact DOI/primary-locator/text duplicate definition; configurable max-two-per-DOI policy; fixed candidate cutoff; optional MiniLM; diagnostic quality/latency gates; private interfaces.
- **Unverified:** locked Windows 10 installation of the optional model stack on this machine; a suitable local checkpoint is already cached; model performance/latency/quality on SciScope; exact downstream generation tokenizer identity; shared owner acceptance of additive API exposure.
- **Execution correction (2026-11-19):** the repository-local `.venv\Scripts\python.exe` is available (Python 3.12.16) with pytest 8.4.2, SQLAlchemy 2.0.58, pgvector 0.5.1, Ruff 0.17.5, and mypy 1.20.2. The initial environment diagnosis was wrong. Read-only identity/pilot preflight passed for `sciscope_test_005` when using only `SCISCOPE_TEST_DATABASE_URL`.
- **Optional reranker feasibility:** `sentence-transformers`, `transformers`, and `huggingface_hub` are absent from this interpreter; standard local Hugging Face and sentence-transformers cache paths are absent. No network/download was attempted. No saved five-question Phase B ranked candidate lists or compatible query vectors were identified. `data/pilot/candidates.jsonl` contains source-selection candidate records, not the required retrieval benchmark input. The measured reranker comparison is blocked pending compatible offline artifacts and a local checkpoint/runtime.
- **No benchmark outcome is claimed.** Any result must be observed, fully manifested, and restricted to the five approved development smoke questions.
