# Person 2 Database and Retrieval Architecture

**Status:** Approved working architectural baseline; implementation is not
authorized. Material changes require a written proposal and approval.

## Responsibilities and data flow

## Person 2 development platform

Person 2 development and verification across all phases is permanently native
Windows 10 x64 with Windows PowerShell and Python 3.12/uv. Person 2 workflows
must not require Docker, WSL, Linux containers, Bash-only commands, or
Linux-only packages. This does not restrict other owners or deployment. Keep
the PostgreSQL 17/pgvector 0.8.7 and real-database requirements unchanged.
Upstream pgvector documents a native Windows source build using Visual Studio
C++ tools and `nmake`; exact Windows 10 reproducibility is not yet verified.

```text
Person 1 validated delivery snapshot
  -> delivery validation
  -> transactional PostgreSQL/pgvector import
  -> dense and lexical candidates
  -> metadata filters and hybrid fusion
  -> base ranking and duplicate policy
  -> optional pluggable reranker
  -> token-budgeted evidence selection
  -> retrieval.v1
  -> Person 3 backend and answer generation
  -> Person 4 citation presentation
```

Person 1 owns source processing, chunks, document embeddings, and delivery.
Person 2 owns persistence, retrieval, filters, ranking, context selection,
source lookup, and retrieval evaluation. Person 3 owns backend orchestration,
answer generation, and citation validation. Person 4 owns the user interface.

## Persistence design

The proposed Phase A model contains `delivery_imports`, `papers`, `sections`,
`chunks`, `embedding_sets`, and `chunk_embeddings`. It preserves all delivered
paper metadata, DOI identity, XML digests, hierarchy, exact chunk text, hashes,
spans, source locators, processing versions, embedding input hashes, and model
metadata. The pilot vector column is `vector(1536)` because the organizer-fixed
model is OpenAI `text-embedding-3-small`.

Vector rows are associated only through
`embedding_manifest.entries[].chunk_id`, never by `chunks.jsonl` position.
Validation occurs before writes. Any invalid delivery, missing reference,
duplicate ID, corrupt/nonfinite/wrong-dimension vector, or database invariant
failure rolls back the complete import.

Delivery contract 0.3.0 is authoritative for the current pilot. Person 2 treats
a package as a complete snapshot only after full contract, completeness,
compatibility, hash, count, reference, and ID-set validation. Initial import is
explicit. A changed snapshot cannot replace the active corpus unless the caller
uses replace mode and supplies the active digest observed after acquiring the
transaction advisory lock. The importer performs load, verification, pruning,
audit transition, and activation in one transaction. Incremental updates are
deferred because contract 0.3.0 has no change manifest or tombstones.

Concurrent imports use a fail-fast transaction-scoped PostgreSQL advisory lock.
One active-import database constraint provides defense in depth. PostgreSQL
MVCC exposes either the previous or new committed snapshot, never a mixed
intermediate corpus. Identical active digest is a true no-op; failures retain
the prior corpus. These are approved Person 2 decisions, not claims of
unrecorded cross-team agreement. Detailed authority lives in Features 005 and
006; no implementation is yet authorized.

## Retrieval pipeline

Dense retrieval begins with exact cosine distance. Approximate HNSW is deferred
until a measured expanded-corpus latency target requires it. Lexical retrieval
uses PostgreSQL full-text search with an explicit English configuration and
`ts_rank_cd`; this is not BM25 and its score is not calibrated confidence.

Hybrid retrieval obtains fixed candidate pools from dense and lexical branches
and combines ranks using reciprocal-rank fusion. The proposed default is RRF
constant 60 and candidate size `max(50, 5 * top_k)`, capped by eligible corpus
size. Stable ties use fused score, best component rank, then `chunk_id`.

Filter categories are publication-year bounds, normalized section types,
journals, languages, and DOI values. Categories combine with AND, values inside
one populated category combine with OR, year bounds are inclusive, and
languages compare case-insensitively. Omitted means unrestricted. Supplying
`[]` or `null` is `INVALID_REQUEST`; the server never silently treats an empty
array as omission or as match-none.

## Reranking and context selection

A `Reranker` accepts query text, a stable sequence of retrieval candidates, and
a limit, and returns only those candidate identities with reranker scores. The
baseline `NoOpReranker` preserves base order. Tests use a
`DeterministicFakeReranker`. Optional adapters require their own approved
dependency/configuration decision; no paid reranker is assumed.

Reranking follows fusion and base deduplication and precedes final diversity
and token-budget selection. Invented/duplicate IDs, missing candidates,
nonfinite scores, or unstable output are errors. Equal reranker scores fall
back to base rank and then `chunk_id`. A requested reranker failure is explicit;
it cannot silently fall back to base order.

Context selection consumes the final ranked evidence without changing text or
provenance. It selects whole evidence units under the approved token budget and
reports selected tokens and truncation. It never cuts or rewrites scientific
text silently.

Phase C approved details (Feature 008): duplicate evidence is exact
`(normalized DOI, primary source locator, exact text)` among fields already
returned by the private Phase B result. No change to the accepted Phase B core
or its RRF behavior is permitted. Per-DOI diversity is configurable with a
default cap of 2; `None` disables it and integer values 1–50 set it. The
optional MiniLM benchmark uses only five approved smoke questions and reports
quality plus warm/cold latency; production reranking remains disabled absent
later approval. Context budgeting requires a caller-provided counter whose
identity exactly matches the configured downstream generator; configured provider
tokenizer identity is supplied by the caller and never guessed. Lookup uses exact DOI/locator/chunk identity in one
read-only active-snapshot REPEATABLE READ transaction. See Feature 008 for
current execution status.

## Citation and error boundaries

The stable scientific citation anchor is normalized DOI plus the digest-bound
source locator. Section ID/path and `chunk_id` provide processing and display
context, but `chunk_id` alone is not scientific ground truth. Every result
includes the active delivery digest and contract/corpus versions.

Invalid requests, unavailable corpus/database/embedder, incompatible embedding
configuration, reranker failure, and missing evidence use typed errors. A valid
zero-match request returns an empty list plus an `EMPTY_RESULT` warning. There
is no silent retrieval-mode or provider fallback.

