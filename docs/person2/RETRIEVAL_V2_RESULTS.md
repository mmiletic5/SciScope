# Retrieval v2 Development Comparison

**Run date:** 2026-11-20  
**Status:** Person 2 implementation and development-only comparison complete; Person 3 application integration and owner acceptance are pending.  
**Machine-readable report:** `.cache/retrieval_v2/development-comparison.json` (Git-ignored)  
**Report SHA-256:** `5d626be1a0f72a1b38cc5d7416e4b307a00ca80486bc2ce1b9ab8cbf388ba395`

## Scope and frozen inputs

The comparison used the five previously approved Golden v0 development questions
only (`n=5`: four answerable and one insufficient-evidence question). Existing
compatible Phase C query vectors were available only for these five questions;
the three planned Golden v1 development query vectors were not present. No new
vectors were generated. No protected Golden v0/v1 question or result was read,
used, or included in the run.

The verified read-only database identity was `sciscope_test_005`, PostgreSQL 17,
role `sciscope`; corpus `pilot17-xml-1fff1573b610`, active delivery digest
`sha256:998241789fd9675853962bdfdf98b15b0991bc4cda103413b0abc470666af9d2`,
embedding set 115, OpenAI `text-embedding-3-small`, 1536 dimensions. The active
corpus counts were 17 papers, 319 sections, 728 chunks, and 728 embeddings.
Retrieval settings and v1 baselines remained frozen. No database writes,
migrations, paid API calls, or query-embedding generation occurred.

For every arm, the runner performed five measured repetitions per question,
after model initialization/warmup where applicable. Each retrieval request
returned up to 50 final candidates; hybrid branch pools were 50 each, allowing
an RRF union up to 100 before optional reranking and final top-k. Quality
metrics use only the four answerable questions with positive gold evidence;
the insufficient-evidence question is excluded from Recall/MRR/nDCG
denominators. Latency summarizes 25 request samples per arm. DOI/citation
identity was checked against exact active-snapshot chunk text, DOI, and locator.

## Aggregate results

| Arm | Recall@5 | Recall@10 | Recall@20 | MRR@10 | nDCG@10 | Median latency (ms) | p95 latency (ms) | DOI identity |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Dense v1 | 0.750 | 0.875 | 1.000 | 0.521 | 0.582 | 23.462 | 67.479 | 250/250 |
| PostgreSQL FTS v1 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 131.816 | 172.981 | 0 candidates |
| Dense + FTS + RRF v1 | 0.750 | 0.875 | 1.000 | 0.521 | 0.582 | 162.734 | 197.222 | 250/250 |
| BM25Okapi v2 | 0.500 | 0.750 | 0.750 | 0.417 | 0.513 | 69.488 | 84.646 | 250/250 |
| Dense + BM25 + RRF v2 | 0.625 | 0.875 | 1.000 | 0.421 | 0.536 | 88.646 | 111.591 | 250/250 |
| Dense + BM25 + RRF + MiniLM v2 | 0.625 | 0.750 | 0.875 | 0.375 | 0.472 | 4250.061 | 4498.784 | 250/250 |

DOI identity means every returned chunk's DOI, exact text, and source locator
resolved to that same active-corpus chunk. It measures attribution integrity,
not relevance. The MiniLM model was
`cross-encoder/ms-marco-MiniLM-L6-v2`, immutable revision
`233902d25c440f23af6f7d6e94d2946bac0bee0a`, checkpoint-directory SHA-256
`402c3a69514c2ccb83898cef29bdf468ec79da80fa091d9967b2de03e7e4adc0`; local
CPU-only inference was run offline.

For the v2 RRF arm, median measured BM25 branch time was 60.734 ms and RRF
fusion time was 0.279 ms. With MiniLM, median BM25 branch time was 65.085 ms,
RRF was 0.358 ms, and reranker inference was 4142.381 ms. These stage timings
are measurements from this local Windows run, not service-level guarantees.

## Per-question results

Each cell is `Recall@5 / Recall@10 / Recall@20; MRR@10; nDCG@10`. `—` means
undefined for the insufficient-evidence question, which is not in the positive
retrieval metric denominators.

| Development question ID | Dense v1 | BM25 v2 | Dense+BM25 RRF v2 | RRF+MiniLM v2 |
|---|---|---|---|---|
| `gq-cmp-001` | .50/.50/1.00; .500; .387 | 0/0/0; 0; 0 | 0/.50/1.00; .100; .177 | 0/0/.50; 0; 0 |
| `gq-conf-001` | .50/1.00/1.00; .250; .441 | 0/1.00/1.00; .167; .423 | .50/1.00/1.00; .250; .468 | .50/1.00/1.00; .250; .457 |
| `gq-gap-001` | 1/1/1; 1.000; 1.000 | 1/1/1; 1.000; 1.000 | 1/1/1; 1.000; 1.000 | 1/1/1; 1.000; 1.000 |
| `gq-ins-001` | — | — | — | — |
| `gq-sp-001` | 1/1/1; .333; .500 | 1/1/1; .500; .631 | 1/1/1; .333; .500 | 1/1/1; .250; .431 |

The existing v1 dense+FTS RRF arm matched dense on these aggregate retrieval
metrics. BM25 recovers one relevant unit for `gq-conf-001` by rank 10 where
dense finds only one of two; however, BM25 returns no relevant unit for the
multi-paper comparison question. RRF loses one comparison evidence unit at
rank 5 versus dense, then catches up by rank 20. MiniLM further lowers
comparison recall to zero at rank 10 and lowers the single-paper question's
MRR/nDCG. These are observed development-set differences, not statistical
claims.

The five-question set is too small and too narrow to support broad quality
claims or reliable per-functionality comparisons. It contains no adequate
systematic stress coverage for exact scientific terms, abbreviations,
numerical-value queries, methods, and named entities. A separately versioned,
source-grounded lexical diagnostic set is recommended before any future
lexical/hybrid improvement cycle; it is not created as part of this approved
implementation.

## Implementation recommendation and limits

- `retrieval.v1` remains unchanged and remains the default. `retrieval.v2` is
  explicitly selected and is not enabled in Person 3's application.
- BM25 and MiniLM are independently testable. The measured results do not
  support recommending BM25-only or MiniLM as an overall quality improvement.
- Keep MiniLM disabled in the recommended v2 service profile unless Person 3
  independently evaluates its latency/quality tradeoff for their application.
- RRF remains an opt-in diagnostic alternative; it ties dense at Recall@10/20
  but has lower Recall@5 and MRR@10 in the aggregate sample.
- Do not interpret BM25, RRF, or cross-encoder scores as calibrated
  probabilities or confidence.
- Multiple-source evidence is allowed to surface through retrieval scores; no
  DOI quota or forced-diversity rule was added. The retrieval layer does not
  invent conflicts or decide scientific equivalence.
- An empty retrieval response is represented by an empty `results` tuple and
  `EMPTY_RESULT` warning. This is not a scientific insufficient-evidence
  classification and must not be presented as one by downstream answer logic.
- The model runs locally on CPU; GPU was unavailable. The comparison does not
  establish production latency, held-out performance, statistical
  significance, or generalization beyond the frozen pilot/development sample.

## Verification evidence

- Offline evaluation/retrieval suite: 208 passed, exit 0.
- PostgreSQL retrieval and evidence-lookup integration tests: 14 passed,
  exit 0, using a guarded local URL targeting `sciscope_test_005`; tests enforce
  read-only transactions and no migration or write was run.
- Ruff check: all `src`, `tests`, `scripts` passed, exit 0.
- Ruff format check: 184 files already formatted, exit 0.
- Mypy: retrieval/evaluation source, 25 files, passed, exit 0.
- Model synthetic CPU inference with offline-only environment: passed.
- All 1,250 returned hit rows across five nonempty arms resolved to exact
  active-snapshot chunk text/DOI/locator; zero attribution failures.

Exact commands and full evidence are recorded in `EVIDENCE.md`. Independent
Person 3 integration approval and owner acceptance are not represented as
complete.
