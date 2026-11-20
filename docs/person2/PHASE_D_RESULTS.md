# Phase D Results and Current Status

**Status:** T004 accepted; T005 readiness PASS for both cohorts; explicitly
authorized T006 retrieval completed and independently reviewed. T007 reports
and handoffs are complete. T008 documentation and technical evidence are
complete, with final owner acceptance pending. Retrieval results remain in
Git-ignored protected output.

## Cohort and methodology status

The registered held-out populations remain Golden v0 held-out (n=16) and
Golden v1 held-out (n=6). The eight development questions remain excluded from
held-out estimates. Golden v1 keeps its approved 3/0/2/1/3 category distribution.
Q4 and Q5 are false-conflict negative controls; the corpus does not support a
genuine-conflict sensitivity claim.

The frozen retrieval configuration and metric definitions are unchanged. For
answerable questions with validated positive evidence, Recall@K is the number
of unique relevant gold evidence units retrieved through K divided by all
unique relevant units for that question; Evidence Hit@K is binary; MRR@K uses
the earliest relevant rank. Macro means use eligible positive questions, not
pooled evidence units. Positive Recall and MRR for insufficient-evidence
questions are null/not applicable. A missing query vector is a readiness
failure, never a retrieval miss or an exclusion from the denominator.

## T005 preflight outcome

The direct user authorization was recorded and integrity-checked. Cohort-bound
authorization records were created under Git-ignored protected storage. The
v1 frozen Q-slot assignment was cross-checked against the separate development
and held-out partition files. The v0 partition was recomputed from the
approved five-question development allowlist and the 21 IDs in the frozen v0
dataset; the repository has no prior standalone v0 partition-digest manifest.
The deterministic digests and derivation basis are recorded in the protected
T005 artifacts.

Read-only database checks passed for `sciscope_test_005`, role `sciscope`,
PostgreSQL 17, a read-only transaction, one active import, 17 papers, 319
sections, 728 chunks, 728 embeddings, and the frozen corpus and embedding-set
identity. All five delivery payload hashes and byte counts matched the local
draft delivery manifest. No database write or migration occurred.

The query-cache path was initially absent, so the owner explicitly authorized
generation of all missing held-out query vectors with OpenAI
`text-embedding-3-small`; the authorization has no monetary cap and is limited
to this operation. Before question text was loaded, both cohort file hashes
and fixed partition digests matched the previously recorded frozen identities.
Only the 16 v0-HO and 6 v1-HO allowlisted records were loaded and sent to the
embedding endpoint. Text was not emitted to console or reports and was not
used for retrieval or tuning. The cache writer applied the preregistered
strip-only normalization and empty query prefix.

Both cohorts passed manifest/vector validation: 22/22 vectors, exact question
association, provider and response model identity, 1536 dimensions,
float32-le cache encoding, finite values, normalized nonzero norms, exact
dataset/corpus/partition/embedding-set identities, and manifest/cache/vector
integrity. Generation used 3 API calls, 626 prompt tokens, and 626 total
tokens. Recorded cost is USD 0.00001252 at the configured USD 0.02 per million
input tokens (see [OpenAI model pricing](https://developers.openai.com/api/docs/models/text-embedding-3-small)).
Detailed cache manifests and vector digests remain in Git-ignored protected
storage; the protected text-free generation report records counts, aggregate
usage, cohort manifest digests, and authorization receipt identity.

**T005 readiness status: PASS.** Evidence is recorded in
evals/protected/phase_d_t005_readiness_report.json and
evals/protected/phase_d_t005_embedding_generation_report.json. T006 was
separately authorized; no retrieval approval was inferred from the embedding
generation authorization. No database write or migration occurred.

## T006 and metric results

The user separately authorized T006 for v0-HO and v1-HO on read-only
sciscope_test_005, using frozen dense, PostgreSQL English lexical, and hybrid
RRF modes. The strict distinct T005/T006 approval validator passed for each
cohort. The runner validated exact question/vector/cache identities before
database access; every request used the cached query vector or lexical text
path. Each question/arm ran twice and ranked evidence matched exactly.
Read-only database preflight and postflight passed with unchanged corpus and
row counts. No write, migration, tuning, additional paid API call, or reranker
run occurred.

The six per-arm cohort reports and the v1 functionality-stratified descriptive
summary are stored under Git-ignored evals/results/. The protected run
manifest is evals/protected/phase_d_t006_run_manifest.json. Reports keep v0
and v1 separate, use answerable-only positive Recall/Hit/MRR denominators,
report insufficient-evidence counts separately, and leave undefined metrics
null. No pooled result is claimed. Golden v1's six held-out questions support
scenario coverage only; functionality strata are descriptive and too small
for robust functionality-specific claims. Q4/Q5 are false-conflict negative
controls; no genuine-conflict sensitivity claim is measured.

## Verification and limitations

The native Windows offline evaluation/retrieval suite passed 195 tests,
including the new synthetic T006 execution-adapter tests. Ruff and formatting
passed; mypy passed across 29 source files. The actual authorized retrieval
run then completed for 22 held-out questions, 3 modes, and 2 exact-result
repetitions per question/arm. The 13 PostgreSQL integration tests were
previously accepted in T004; this run additionally exercised the read-only
database retrieval core. The delivery manifest remains marked draft;
original raw XML remains unavailable; the independent Golden review was model
review, not human verification.

Protected held-out results are for final reporting and independent review
only. Do not use them for retrieval tuning or configuration selection.

## Independent review and lexical diagnostic (2026-11-20)

The owner reports that independent ChatGPT review verified all 84 payload
hashes in the final package, confirmed all six cohort/arm reports were present,
and independently recomputed macro Recall, Evidence Hit, and MRR from the
per-question records. Those recomputations matched. The review observed that
dense and hybrid metrics are identical and lexical Recall@20 is zero in both
held-out cohorts. ChatGPT did not independently reproduce PostgreSQL access.

Read-only code/configuration inspection found the frozen lexical path uses
`websearch_to_tsquery('english', query_text)` and evaluates
`to_tsvector('english', Chunk.text) @@ query`, ranked by `ts_rank_cd`, with the
same corpus and request filters and a top-k of 20. It uses raw question text
and does not use query embeddings. The evidence matcher separately requires
normalized DOI plus an exact primary/span locator, with only the preregistered
same-section/exact-quotation fallback. Existing PostgreSQL integration tests
exercise stable English FTS on a controlled term and verify a stop-word-only
query can yield an empty result without embedding.

The saved reports contain aggregate/per-question metrics and a single
`retrieval_total` latency summary; they do not retain lexical candidate lists,
candidate counts, matched-locator diagnostics, or per-repetition cold/warm
labels. Therefore this read-only review cannot distinguish an empty FTS result
from returned chunks that fail strict gold-unit matching, nor identify a
question-specific lexical failure mechanism. No protected question or result
content was inspected for tuning, and no retrieval was rerun. No configuration
or retrieval-contract change is proposed. Lexical zero Recall is recorded as
an observed limitation, not a basis to alter the baseline.

Independent review limitations remain: small held-out cohorts (v0 n=16, v1
n=6); no human Golden v1 verification; original raw XML unavailable; no
genuine-conflict sensitivity measurement; and no independent PostgreSQL
reproduction by ChatGPT. Dense/hybrid metric equality is an observed result,
not evidence that either arm is generally superior.

The run records repeated total retrieval timings and cohort summaries, but do
not explicitly classify warm versus cold observations or separate database,
fusion, and other latency stages. AC-038 is therefore not fully evidenced and
must remain an explicit limitation; no missing characterization is inferred
from the existing run. T007/T008 evidence is otherwise prepared for final
owner acceptance.

## T008 read-only lexical and hybrid diagnostics

**Scope and safeguards.** Probes ran on native Windows against the active
`sciscope_test_005` corpus in a PostgreSQL repeatable-read, read-only
transaction. Preflight confirmed role `sciscope`, corpus
`pilot17-xml-1fff1573b610`, and unchanged identity. Queries were synthetic
strings derived from public frozen-corpus chunk text; no Golden record was
used. No filters were applied, matching the evaluation requests. The probes
joined each candidate through its DOI-bound paper and section and checked the
expected source chunk's DOI and locator. No query embedding was needed.

| Probe query | Source-grounded target | FTS candidates | Target rank / top-20 | Exact DOI+locator mapping |
| --- | --- | ---: | --- | --- |
| `Apis mellifera` | `10.1371/journal.pone.0000395`, Materials and Methods / Honeybees | 48 | 3 / retrieved | Pass |
| `RNA` | `10.1371/journal.pone.0244648`, Discussion | 44 | 19 / retrieved | Pass |
| `10` | `10.1371/journal.pone.0244648`, Discussion | 103 | 31 / not retrieved | Pass for the source row; it falls beyond top 20 |
| `10 genes` | `10.1371/journal.pone.0244648`, Discussion | 17 | 1 / retrieved | Pass |
| `feeding` | `10.1371/journal.pone.0034137`, Discussion | 36 | 11 / retrieved | Pass |
| `Varroa destructor` | `10.1371/journal.pone.0077354`, Introduction | 14 | 3 / retrieved | Pass |
| `How do Honeybees Apis mellifera bred open environment?` | `10.1371/journal.pone.0000395`, Materials and Methods / Honeybees | 1 | 1 / retrieved | Pass |
| `How do Honeybees Apis mellifera and sequencing used provide?` | Cross-source terms from the prior two source records | 0 | no candidate | N/A |

These are controlled probes of source-chunk retrieval, not relevance judgments
for Golden questions. The numeric-only probe confirms `ts_rank_cd` can rank a
source chunk beyond the frozen lexical top-20 limit; adding its source-context
term moved that source chunk to rank 1. PostgreSQL's `querytree`
for the long cross-source query showed its six positive lexemes joined with
AND; no single chunk contained all terms, so it returned no candidate. The
longer single-source query produced six lexemes and returned its target at
rank 1. This confirms a predictable over-constraint for multi-concept queries
under the current per-chunk FTS semantics.

**Confirmed mechanisms:** lexical uses English `websearch_to_tsquery` on
question text, `to_tsvector('english', Chunk.text)`, `ts_rank_cd`, active-import
and metadata joins/filters, and top-k. Query text is stripped but otherwise
unchanged. In T006 the lexical arm is limited to top 20. Hybrid's default
branch pool is 100 for top-k 20, then RRF returns the top 20. The code has no
unrequested query rewriting or lexical fallback. Exact locator mapping passed
for retrieved diagnostic targets; the numeric target was excluded by rank
cutoff, not broken chunk mapping. The diagnostic had no user filters, so
filtering did not explain its misses.

**Hybrid fusion:** no compatible development query cache was present at the
configured development-cache path, so no database hybrid probe was run. The
existing synthetic RRF tests were run instead: `test_ranking.py` verifies the
union of dense-only and lexical-only chunk IDs, overlap deduplication, exact
RRF scores, and deterministic ordering using an independent arithmetic
oracle. The frozen fusion implementation genuinely combines both branch
rankings in these controlled cases. This does not establish which lexical
candidates contributed to the protected T006 hybrid result. The independent
reviewer reported identical dense/hybrid held-out metrics; the protected
reports do not retain candidate lists, so that equality cannot be attributed
to an empty lexical branch, duplicate/redundant hits, evidence matching, or
fusion ranking.

**Development coverage:** the three separate Golden v1 development records
were scanned locally without printing their text: 3/3 contain a Latin
binomial pattern, 1/3 an uppercase acronym, 0/3 a numeric value, 2/3 a method
or assay term, and 0/3 one of the three checked bee taxa (Apis mellifera,
Varroa destructor, Nosema ceranae). The five Golden v0 development records
could not be fully scanned: the existing bounded allowlist utilities failed
closed on the v0 file. No held-out question was decoded or exposed, and no
development coverage claim is made for those five records. The established
development questions are smoke/diagnostic cases, not a systematic lexical
stress set.

**Conclusion and recommendation:** lexical FTS works for controlled exact
terms, an acronym, a method term, and a named taxon in this pilot. It can miss
source chunks through top-k rank cutoff and can return no candidate for a long
cross-source query because all query lexemes must match a single chunk. The
protected T006 report is insufficient to establish which mechanism caused
zero held-out lexical Recall. A separate versioned, source-grounded,
development-only lexical/hybrid diagnostic set is recommended before any
improvement cycle: include multiple cases for exact scientific terminology,
acronyms/abbreviations, numeric values with units, methods, named entities,
and long single- and cross-source questions, with expected DOI/section/chunk
locators and branch-level diagnostics. Keep it distinct from Golden held-out
results. This is a recommendation only; no new questions, configuration,
retrieval algorithm, or tuning were introduced.

**AC-038 limitation:** reports preserve two total-retrieval timings per
question/arm and cohort median/p95/max, but do not label warm/cold observations
or separately time embedding, database, and fusion stages. The completed run
cannot be retroactively relabeled. No further evaluation was run.
