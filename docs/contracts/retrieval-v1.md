# Proposed Retrieval Contract `retrieval.v1`

**Status:** Person 2 reference design; proposed shared contract, not team
approved. Technical choices in Person 2's authority are selected; this does not
approve P1-09/P1-11/P1-14, shared contract adoption, or schema migration.
This file is the canonical detailed contract; spec/plan link here rather than
redefining its wire fields.

## Ownership boundary

- Person 1 owns delivery metadata, normalization, source locators, and source
  provenance. Phase B consumes accepted delivery 0.3.0 as-is.
- Person 2 owns the Python DTOs/protocol, validation, filters, retrieval SQL,
  ranking, typed exceptions, database isolation, and result provenance.
- Person 3 consumes the driver-independent service, owns RAG orchestration,
  HTTP routing/status mapping, answer generation, and citation validation.
  Proposed live query-embedder adapter/config ownership is Person 3; the
  protocol and fake remain Person 2-owned.
- Person 4 maps UI choices to filter request values and maps public error
  categories to UI states. UI has no dependency on SQL/ORM/schema.

Phase B excludes HTTP endpoints, answer generation, citation validation,
reranking, duplicate suppression/diversity, context budgeting, timing,
evidence lookup, and evaluation benchmark/report tooling. The smoke subset is
only a wiring regression. Future additions require a reviewed additive v1
field or a new contract version according to compatibility rules below.

## Python API and errors

```python
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, Protocol, Sequence


RetrievalMode = Literal["dense", "lexical", "hybrid"]
NormalizedType = Literal[
    "abstract",
    "introduction",
    "methods",
    "results",
    "results_discussion",
    "discussion",
    "conclusions",
    "other",
]


@dataclass(frozen=True, slots=True)
class RetrievalFilters:
    publication_year_from: int | None = None
    publication_year_to: int | None = None
    normalized_types: tuple[NormalizedType, ...] | None = None
    journals: tuple[str, ...] | None = None
    languages: tuple[str, ...] | None = None
    dois: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class RankingOptions:
    candidate_pool_size: int | None = None


@dataclass(frozen=True, slots=True)
class RetrievalRequest:
    contract_version: str
    request_id: str
    query_text: str
    mode: RetrievalMode
    top_k: int
    filters: RetrievalFilters | None = None
    ranking: RankingOptions | None = None


@dataclass(frozen=True, slots=True)
class EmbeddingConfig:
    provider: str
    model: str
    dimensions: int
    query_prefix: str


class RetrievalErrorCode(StrEnum):
    INVALID_REQUEST = "INVALID_REQUEST"
    UNSUPPORTED_CONTRACT_VERSION = "UNSUPPORTED_CONTRACT_VERSION"
    CORPUS_NOT_LOADED = "CORPUS_NOT_LOADED"
    EMBEDDING_CONFIGURATION_MISMATCH = "EMBEDDING_CONFIGURATION_MISMATCH"
    EMBEDDING_UNAVAILABLE = "EMBEDDING_UNAVAILABLE"
    DATABASE_UNAVAILABLE = "DATABASE_UNAVAILABLE"
    RETRIEVAL_INTERNAL_ERROR = "RETRIEVAL_INTERNAL_ERROR"


@dataclass(frozen=True, slots=True)
class RetrievalException(Exception):
    code: RetrievalErrorCode
    request_id: str | None
    retryable: bool
    public_message: str


@dataclass(frozen=True, slots=True)
class Author:
    surname: str
    given_names: str


@dataclass(frozen=True, slots=True)
class PaperMetadata:
    title: str
    authors: tuple[Author, ...]
    journal: str
    publication_year: int
    language: str
    license: str
    source_url: str


@dataclass(frozen=True, slots=True)
class RetrievalScore:
    dense_similarity: float | None
    dense_rank: int | None
    lexical_score: float | None
    lexical_rank: int | None
    fusion_score: float | None


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    rank: int
    chunk_id: str
    text: str
    doi: str
    source_locator: str
    section_id: str
    section_path: tuple[str, ...]
    normalized_type: NormalizedType
    paper: PaperMetadata
    scores: RetrievalScore


@dataclass(frozen=True, slots=True)
class CorpusIdentity:
    delivery_digest: str
    source_contract_version: str
    corpus_version: str


@dataclass(frozen=True, slots=True)
class RetrievalMetadata:
    mode: RetrievalMode
    top_k: int
    candidate_pool_size: int | None
    applied_filters: RetrievalFilters | None
    rrf_constant: int | None


@dataclass(frozen=True, slots=True)
class RetrievalResponse:
    contract_version: str
    request_id: str
    corpus: CorpusIdentity
    embedding: EmbeddingConfig | None
    retrieval: RetrievalMetadata
    results: tuple[RetrievalResult, ...]
    warnings: tuple[Literal["EMPTY_RESULT"], ...]


class QueryEmbedder(Protocol):
    def embed_query(
        self, text: str, *, config: EmbeddingConfig
    ) -> Sequence[float]: ...


class RetrievalService(Protocol):
    def retrieve(self, request: RetrievalRequest) -> "RetrievalResponse": ...
```

`RetrievalFilters` uses `None` for omitted categories; explicit JSON null is
rejected during parsing rather than represented as an unrestricted value.

`retrieve()` returns `RetrievalResponse` on success and raises
`RetrievalException` on failure; no union return. Exception fields are
`code: RetrievalErrorCode`, `request_id: str | None`, `retryable: bool`, and
`public_message: str`. Internal cause may be retained only for protected
debugging and must not be serialized/logged. Person 3 catches this exception
and maps it to HTTP plus the JSON error envelope below. The service and DTOs
expose no SQLAlchemy, psycopg, pgvector, connection, or ORM types.

The embedder is injected at service construction. It receives an immutable
configuration and returns a vector only; it cannot access database state.
Lexical mode does not call it. Dense/hybrid query vectors are validated before
database use. Offline tests use `FakeQueryEmbedder`, configured with a fixed
vector and expected config; it records calls and makes no network calls. A
fixed `FakeRetrievalService` response stub lets Persons 3/4 develop without
Person 2 code or a database.

## Request DTO and validation

All objects reject unknown fields. Validation occurs before provider/database
access. Integers reject booleans; strings must be UTF-8 and within limits.

```json
{
  "contract_version": "retrieval.v1",
  "request_id": "explorer-0184",
  "query_text": "How does viral infection affect honey bee homing?",
  "mode": "hybrid",
  "top_k": 5,
  "filters": {
    "publication_year_from": 2010,
    "publication_year_to": 2025,
    "normalized_types": ["results", "discussion"],
    "journals": ["PLOS ONE"],
    "languages": ["en"],
    "dois": ["10.1371/journal.pone.0077354"]
  },
  "ranking": {"candidate_pool_size": 50}
}
```

| Field | Type | Required | Validation/default |
|---|---|---:|---|
| `contract_version` | literal string | yes | Exactly `retrieval.v1`; unsupported value raises `UNSUPPORTED_CONTRACT_VERSION`. |
| `request_id` | string | yes | 1–128 ASCII chars matching `[A-Za-z0-9._:-]`; echo unchanged. |
| `query_text` | string | yes | Trim surrounding whitespace and use the trimmed text for embedding/search; 1–2,000 characters. |
| `mode` | enum | yes | `dense`, `lexical`, `hybrid`. |
| `top_k` | integer | yes | 1–50. |
| `filters` | object | no | Omission means no filters. Explicit null invalid. |
| Year bounds | integer | no | 1–9999, inclusive; from <= to. |
| `normalized_types` | string array | no | Nonempty, at most 100, unique exact members of fixed taxonomy. |
| `journals` | string array | no | Nonempty, at most 100, unique after surrounding-whitespace trim; exact case-sensitive stored-value match. |
| `languages` | string array | no | Nonempty, at most 100, unique after ASCII lowercase; exact case-insensitive stored-value match. |
| `dois` | string array | no | Nonempty, at most 100, unique after accepted Phase A DOI normalization; valid DOI shape and exact match to persisted normalized DOI. |
| `ranking` | object | no | Only valid for hybrid; unknown fields invalid. |
| `candidate_pool_size` | integer | no | Hybrid only; 1–250 and >= `top_k`; default `min(eligible_count, max(50, 5 * top_k))`, capped at 250 then eligible count. |

Arrays supplied as null, empty, blank-valued, or duplicated after category
normalization are `INVALID_REQUEST`. Omission means unrestricted. AND across
categories; OR within a populated category. Request canonicalization affects
comparison only; persisted source values never change. Allowed normalized
types: `abstract`, `introduction`, `methods`, `results`,
`results_discussion`, `discussion`, `conclusions`, `other`.

DOI filter inputs follow the accepted F001 normalization semantics: trim;
remove one supported prefix (`doi:`, `https://doi.org/`,
`http://doi.org/`, `https://dx.doi.org/`, `info:doi/`) or extract exactly one
nonempty `id` query parameter from another DOI URL; remove trailing `.,;` and
unmatched closing `)`/`]` with preceding punctuation; lowercase; validate
`^10\.[0-9]{4,9}/\S+$`. This mirrors the accepted data contract semantics
without requiring consumers to import Person 2's Python helper. Ambiguous or
invalid resolver URLs are `INVALID_REQUEST`.

`candidate_pool_size` may not be smaller than `top_k`. If explicitly supplied
for dense/lexical mode, reject it as irrelevant/invalid. In hybrid, each branch
returns up to the effective pool over the same eligible set. If eligible rows
are fewer than `top_k`, return all available rows; if fewer than pool, each
branch evaluates all eligible rows. The hybrid union may contain up to twice
the branch pool before final truncation. Response reports the effective pool.

## Metadata and provenance boundary (Person 1)

Accepted Phase A schema/validation guarantees these nonempty persisted fields:

- Paper: normalized lowercase DOI, title, ordered author objects (`surname`,
  `given_names`), source journal string, source publication date, integer
  `publication_year`, source article type, subjects, raw license, raw language,
  source URL, retrieved timestamp, XML SHA-256.
- Section: section ID, DOI, title, ordered section path, original heading,
  normalized type, digest-bound source locator, depth, paragraph count, parent.
- Chunk: stable chunk ID, DOI, section ID, exact text, text hash, spans with
  source locators/offsets, digest-bound source locator, normalized type/path,
  token count, processing versions.
- Snapshot/embedding: active import ID/digest, source contract version,
  corpus version (derived per delivery convention), provider/model/dimensions,
  dtype and prefixes, and chunk-owned vectors keyed by manifest `chunk_id`.

DOI is normalized upstream by the accepted delivery builder and revalidated by
the consumer. Publication year is derived upstream from publication date and
persisted; retrieval does not rederive it. Journal and language are preserved
source strings (`EN` and `en` both occur); normalized section type comes from
the fixed taxonomy. Locator is opaque and bound to the XML digest; clients
preserve it exactly. Retrieval returns source metadata verbatim. Request-time
trim/case normalization is not persisted. Missing/inconsistent required data
should already reject ingestion; if detected in DB, fail safely with
`RETRIEVAL_INTERNAL_ERROR`, never synthesize or silently omit citation fields.

External assumptions requiring later Person 1 confirmation: journal value
aliases are not provided by current schema; source locator grammar stability
is not a promise beyond its digest-bound opaque value; language taxonomy is
not richer than persisted raw strings. No ingestion change is proposed.

## Query embedding contract

```json
{
  "provider": "openai",
  "model": "text-embedding-3-small",
  "dimensions": 1536,
  "query_prefix": ""
}
```

This is the fixed pilot identity. Embedder returns a 1-D numeric sequence of
exactly 1536 values, all finite and representable as float32, with finite
nonzero L2 norm. Wrong type/shape/dimension/nonfinite/out-of-range/zero norm
or mismatch with active embedding metadata raises
`EMBEDDING_CONFIGURATION_MISMATCH`. Provider outage/timeout raises
`EMBEDDING_UNAVAILABLE`. No retry or provider switch is performed by retrieval;
adapter may classify transient failure, and caller may retry the same request.
No document embeddings are generated.

For dense/hybrid, first perform a short read-only preflight to confirm an active
corpus and read its embedding metadata; close that transaction before provider
work. Embed using the fixed immutable runtime configuration, then open the
retrieval transaction and re-read/validate the active metadata. The preflight
does not pin a snapshot: if activation occurs during embedding, the final
transaction may use the newly active snapshot only if its embedding identity
matches. Otherwise raise `EMBEDDING_CONFIGURATION_MISMATCH`; do not silently
re-embed or retry with another provider. The result rows and all response
provenance still come from exactly one final retrieval snapshot. This avoids
provider calls when no corpus exists and avoids holding a database connection
or MVCC snapshot during provider latency. Lexical mode uses only one retrieval
transaction and does not call an embedder.

## Retrieval methodology

### Dense

Exact pgvector cosine distance `<=>`; return similarity `1 - distance`. Apply
active import, compatible embedding-set, and shared metadata predicates before
top-k. Order by cosine distance ascending and `chunk_id` ascending. No ANN
index or approximate candidate stage in Phase B.

### Lexical

Search chunk text only using explicit English configuration:
`websearch_to_tsquery('english', query_text)` and `ts_rank_cd` descending.
Bind raw query as a parameter. Blank query is invalid in all modes. If query
parsing yields no lexemes (e.g. only English stop words), lexical mode succeeds
with zero candidates and `EMPTY_RESULT`. In hybrid, an empty lexical query
means lexical branch has zero candidates while dense proceeds normally. This
is not fallback; parser completion is successful. Actual FTS/database failure
fails the requested mode. FTS scores are ordering signals, not confidence.

### Hybrid and determinism

Use same repeatable-read snapshot, filter predicate, and eligible corpus for
both branches. Default branch pool is `min(eligible_count, min(250,
max(50, 5 * top_k)))`; explicit pool is 1–250 and at least top-k. Union by
`chunk_id`; each chunk appears once, while distinct chunks from one paper stay
distinct (deduplication/diversity is Phase C). RRF uses one-based branch ranks,
k=60, score `sum(1 / (60 + rank))` for branches containing the candidate.
Order: fusion score descending, best component rank ascending, chunk ID
ascending. Dense ties: distance then chunk ID. Lexical ties: score descending
then chunk ID. This is total deterministic ordering for a fixed snapshot and
database version. Hybrid fails if either branch fails; no partial/silent
fallback. Return at most `top_k`; fewer eligible hits yield fewer results.

## Snapshot, transaction, and provenance

For dense/hybrid, do a short read-only active-corpus preflight before provider
embedding and close that transaction, so no-corpus errors do not spend provider
calls. Embed outside a database transaction. Then open one connection and one
read-only `REPEATABLE READ` transaction. Resolve active import and embedding
set once; validate embedding compatibility; bind captured active import ID and
embedding set ID in every query. Perform both branches and result metadata
reads inside the transaction, then commit read-only. An activation committed
before the first read of this final transaction is wholly visible; activation
committed after snapshot establishment is invisible until retrieval ends. A
snapshot activated during embedding may be used if its embedding identity
matches; all results still come from one final snapshot. No retrieval read uses
`READ COMMITTED` or a separately opened connection. Do not add locks that
block ingestion; PostgreSQL MVCC supplies old/new committed visibility. Errors
abort and close transaction. Lexical-only requests skip embedding and preflight
separately; they resolve corpus inside their one repeatable-read transaction.

Each result includes exact text and persisted DOI + digest-bound source locator,
section/chunk identity, section path/type, and citation metadata. Top-level
corpus fields identify captured delivery digest, source contract version, and
corpus version. This makes response provenance reproducible even during
concurrent activation.

## Response DTO and example

```json
{
  "contract_version": "retrieval.v1",
  "request_id": "explorer-0184",
  "corpus": {
    "delivery_digest": "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "source_contract_version": "0.3.0",
    "corpus_version": "pilot17-xml-1fff1573b610"
  },
  "embedding": {"provider":"openai","model":"text-embedding-3-small","dimensions":1536,"query_prefix":""},
  "retrieval": {"mode":"hybrid","top_k":5,"candidate_pool_size":50,"applied_filters":{"languages":["en"]},"rrf_constant":60},
  "results": [{
    "rank":1,"chunk_id":"<64-hex-chunk-id>","text":"Exact preserved chunk text.",
    "doi":"10.1371/journal.pone.0077354",
    "source_locator":"jats:v1:<xml-sha256>:/article[1]/body[1]/sec[3]/p[1]",
    "section_id":"10.1371/journal.pone.0077354#sec-3",
    "section_path":["Results","Example subsection"],"normalized_type":"results",
    "paper":{"title":"Example title","authors":[{"surname":"Example","given_names":"A."}],"journal":"PLOS ONE","publication_year":2013,"language":"EN","license":"CC BY 4.0","source_url":"https://doi.org/10.1371/journal.pone.0077354"},
    "scores":{"dense_similarity":0.8123,"dense_rank":2,"lexical_score":0.184,"lexical_rank":1,"fusion_score":0.03252}
  }],
  "warnings":[]
}
```

For lexical mode omit the top-level `embedding`; `candidate_pool_size` and
`rrf_constant` are null outside hybrid. All score/rank properties are present;
properties for unrun branches and `fusion_score` outside hybrid are null. In
hybrid, an absent branch rank/score is null. Zero results return `results: []`
and warning `EMPTY_RESULT`. There are no per-result license decisions or citation claims;
Person 3/4 own downstream presentation/policy.

Phase B deliberately excludes `token_budget`, `selection`, timing, reranker
identity/score, lookup methods, answer, citations assembled by an LLM, and HTTP
status. The Phase B contract should not retain fields with no Phase B
semantics. If downstream implementation already depends on them, treat that
as a compatibility blocker to resolve before v1 adoption, not as permission to
implement later-phase features in Phase B.

## Error behavior and security

Success returns `RetrievalResponse`; failures raise `RetrievalException`.
Codes and default retryability:

- `INVALID_REQUEST` false; `UNSUPPORTED_CONTRACT_VERSION` false;
  `CORPUS_NOT_LOADED` false; `EMBEDDING_CONFIGURATION_MISMATCH` false.
- `EMBEDDING_UNAVAILABLE` true only for classified transient timeout/service
  outage; malformed output/configuration is mismatch and nonretryable.
- `DATABASE_UNAVAILABLE` true only for connection/serialization transient
  classes; query/schema/data invariant failures map internal and are not
  blindly retried.
- `RETRIEVAL_INTERNAL_ERROR` false.

HTTP adapter serializes `{contract_version, request_id, error:{code,message,
retryable}}`; `request_id` is null only when missing/invalid in the request. No
v1 error details. Messages are stable, actionable, sanitized.
No silent provider, mode, or branch fallback. SQL values are bound parameters;
identifiers/configuration are fixed code constants. Logs may contain request
ID, mode, duration, error code, and snapshot digest; never query text, article
text, vectors, secret, full connection string, stack, or absolute path. Limits:
request ID 128 chars, query 2,000 chars, filter arrays 100 values each,
candidate pool 250, top-k 50. A batch/request timeout is infrastructure-owned;
no arbitrary hard latency target is claimed.

UI-independent public categories: `INVALID_REQUEST` means correct the submitted
query/filter; `EMPTY_RESULT` is a successful response with no matching
evidence; `CORPUS_NOT_LOADED` means retrieval is not ready; transient
`EMBEDDING_UNAVAILABLE`/`DATABASE_UNAVAILABLE` may offer retry; configuration
mismatch and unsupported contract version are integration/configuration errors
to surface as service errors rather than user-authored input errors;
`RETRIEVAL_INTERNAL_ERROR` is a generic service failure. Exact wording and
presentation remain UI-owned.

## Conformance and compatibility

Pure contract tests validate valid/invalid request fixtures, response/error
fixtures, field bounds, unknown-field rejection, empty lexical query, fake
embedder calls/configuration, malformed vectors, mode call graph, and stable
RRF arithmetic. They import no database internals. Person 3 uses a fake service
stub with JSON success/error fixtures; Person 4 uses filter fixtures and
public error codes.

Real PostgreSQL tests verify cosine scores/order including ties, English FTS
query parsing/rank/empty lexemes, all filters and combinations in each mode,
parameterization, no-hit behavior, and transaction snapshot under concurrent
snapshot activation. Tests use known deterministic fixture data and rollback
or fixture cleanup only on verified test target `sciscope_test_005`; planning
does not access databases. No live embedding provider is called.

Changing required fields, error codes, filter meaning, scoring/ranking,
provenance, or isolation requires retrieval.v2 and affected-owner review.
Additive optional fields require Person 2/3 compatibility review. HTTP status
mapping is not part of this Python contract.
