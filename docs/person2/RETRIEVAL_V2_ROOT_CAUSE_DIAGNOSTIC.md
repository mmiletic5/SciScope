# Retrieval v2 root-cause diagnostic

**Status:** diagnostic only; V2-14 remains open. No production configuration, frozen data, annotations, or shared interfaces were changed.

## Scope and reproducibility

This report uses only the five previously approved development questions (`gq-sp-001`, `gq-cmp-001`, `gq-conf-001`, `gq-gap-001`, `gq-ins-001`), existing compatible query vectors, frozen corpus `pilot17-xml-1fff1573b610`, 728 chunks, and read-only `sciscope_test_005`. Protected cohorts were not accessed. Experiment-set SHA-256: `90f5568fd7c3f2afc56d8f1129ea98a421b66ee5d933ee89d08bddabeb331dfc`. The saved baseline was independently recomputed by the experiment harness and matched. Full numeric machine records are under Git-ignored `.cache/retrieval_v2/root-cause-diagnostic.json` and `.cache/retrieval_v2/controlled-experiments.json`; these contain development IDs, locators, hashes, and metrics, not held-out content.

## Where the six annotated evidence units rank

Ranks are one-based. Each stage's rank and score refer to its earliest matching chunk for the gold unit; matching chunk IDs can differ when chunk spans overlap the same source locator. “Regex” is the diagnostic Unicode component tokenizer; the separate requested ASCII-regex and stopword aggregate results are below. BM25, RRF, and MiniLM raw scores are ranking signals, not calibrated confidence.

| Development question | Evidence DOI and source locator | Dense rank (score) | BM25 rank (score) | Regex BM25 rank | RRF rank (score) | MiniLM rank (score) |
|---|---|---:|---:|---:|---:|---:|
| `gq-cmp-001` | `10.1371/journal.pone.0034137`, `/article[1]/body[1]/sec[3]/p[3]` | 2 (.567053) | 36 (13.127354) | 6 | 10 (.025568) | 18 (-5.110314) |
| `gq-cmp-001` | `10.1371/journal.pone.0077354`, `/article[1]/body[1]/sec[3]/sec[1]/p[1]` | 13 (.517151) | 33 (13.253813) | 24 | 13 (.024451) | 37 (-7.945205) |
| `gq-conf-001` | `10.1371/journal.pone.0187079`, `/article[1]/body[1]/sec[4]/p[2]` | 10 (.657277) | 7 (18.966748) | 10 | 7 (.029211) | 8 (-.817912) |
| `gq-conf-001` | `10.1371/journal.pone.0187079`, `/article[1]/body[1]/sec[4]/p[6]` | 4 (.686134) | 6 (19.887119) | 5 | 4 (.030777) | 4 (1.747687) |
| `gq-gap-001` | `10.1371/journal.pone.0118885`, `/article[1]/body[1]/sec[4]/sec[2]/p[6]` | 1 (.681253) | 1 (46.078002) | 2 | 1 (.032787) | 1 (4.186132) |
| `gq-sp-001` | `10.1371/journal.pone.0077354`, `/article[1]/body[1]/sec[3]/sec[4]/p[1]` | 3 (.692594) | 2 (43.641376) | 7 | 3 (.032002) | 4 (3.094363) |

All six gold units are represented in the frozen corpus, their quoted evidence fits within one source chunk, and the DOI/locator matcher recognizes each. `gq-cmp-001` evidence overlap with the current BM25 whitespace tokens is 6/17 and 5/17 query terms; diagnostic Unicode component overlap is 7/17 and 5/17. Its first gold passage matches two chunks carrying the same source locator: the earliest dense/MiniLM match is chunk prefix `5692cd82` (dense rank 2, MiniLM rank 18), while the earliest BM25/RRF match is prefix `866145e0` (BM25 rank 36, RRF rank 10; that chunk's dense branch rank is 6 and RRF score .025568). This is locator-span multiplicity, not duplicate suppression. The matcher canonicalizes evidence by DOI/locator/quote identity and counts unique gold units; repeated retrievals cannot inflate recall. No gold unit was excluded by reranker duplicate suppression. The final top-50 trace retains each unit; misses at smaller metric cutoffs are ranking/cutoff effects, not candidate absence. `gq-conf-001` has two annotated passages from one paper, not two-source coverage.

## Controlled, one-variable experiments

Positive-answerable macro denominator is four questions; the insufficient-evidence question is excluded from relevance metrics. BM25 timing is one measured in-memory index-build-and-score pass per question. These are small-sample development diagnostics, not estimates of general performance.

| BM25 tokenization variant | Recall@5 / @10 / @20 | MRR@10 | nDCG@10 | Median build+score ms |
|---|---|---:|---:|---:|
| Current whitespace `casefold().split()` | .500 / .750 / .750 | .417 | .513 | 94.9 |
| Requested ASCII regex `[a-zA-Z0-9]+` | .625 / .750 / .875 | .363 | .468 | 140.1 |
| Unicode regex components | .375 / .875 / .875 | .252 | .399 | 278.5 |
| Conservative English stopwords (negations retained) | .500 / .750 / .875 | .542 | .606 | 90.8 |

The ASCII regex improved recall at 5 and 20 but worsened MRR/nDCG; Unicode component splitting did not help overall; conservative stopword removal improved recall@20, MRR, and nDCG on this set without changing recall@5. These are mixed, development-only results and do not justify changing defaults. A synthetic punctuation/hyphen/acronym example showed whitespace token overlap 0 versus component overlap 6. It does not show abbreviation-expansion synonym handling or establish the explanation for every observed rank.

| Dense/BM25 branch candidate depth; final top 20 | Union candidate recall | RRF Recall@5 / @10 / @20 | RRF MRR@10 / nDCG@10 | MiniLM Recall@20 | Median BM25 / MiniLM ms |
|---:|---:|---|---|---:|---:|
| 20 | 1.000 | .625 / .875 / .875 | .438 / .547 | 1.000 | 95.6 / 2,140.7 |
| 50 | 1.000 | .625 / .875 / 1.000 | .421 / .536 | .875 | 92.4 / 5,755.5 |
| 100 | 1.000 | .625 / .875 / 1.000 | .421 / .536 | .875 | 93.4 / 11,038.9 |

Candidate-union recall is already 1.0 at depth 20 for these annotations; depth 50 improves RRF recall@20 over depth 20, while 100 has no measured quality gain. Timing used one repetition per question and is noisy, especially for CPU MiniLM; the pronounced MiniLM cost is nonetheless consistent with earlier runs. Do not infer service latency from these measurements.

Per-question sensitivity is most visible for the comparison case. At branch depth 20, `gq-cmp-001` RRF Recall@20 is .5 and MiniLM Recall@20 is 1.0; at depth 50 or 100, RRF Recall@20 is 1.0 but MiniLM Recall@20 falls to .5 (MiniLM MRR@10 is 0 in all three cases). All six judged units are in the dense/lexical union at each depth. This non-monotonic change confirms that pool depth changes which unjudged competitors MiniLM sees; it does not prove the additional candidates irrelevant. For `gq-conf-001`, both RRF and MiniLM Recall@20 stay 1.0 and MRR@10 stays .25 at each depth. Gap and factual questions retain Recall@20 1.0; MiniLM lowers factual MRR@10 from .333 to .25.

## Root-cause assessment

**Confirmed for this development set:**

- Dense retrieval finds all annotated units by branch depth 20. Candidate generation is not the limiting stage for these gold annotations.
- BM25 tokenization/ranking is a contributor for comparison evidence: both `gq-cmp-001` passages rank 33–36 under baseline BM25 despite being in the corpus. Tokenizer variants produce mixed metric tradeoffs.
- RRF changes the ordering relative to dense alone. For the first `gq-cmp-001` source evidence unit, its earliest matching chunk is dense rank 2, while the earliest RRF-matching (different overlapping) chunk is RRF rank 10; the second unit's matched chunk is dense rank 13 and RRF rank 13. The RRF rank-10 chunk has dense branch rank 6 and BM25 branch rank 36. This follows the defined equal-weight reciprocal-rank sum; top unannotated candidates are unjudged, not established false positives.
- MiniLM worsens comparison evidence ordering: those passages move to ranks 18 and 37, with negative scores, and comparison-question Recall@20 is incomplete at pool 50/100. It is ranking demotion, not duplicate suppression. Its development-set CPU latency is not justified by the observed aggregate quality.
- More candidates beyond 20 do not fix candidate recall; moving from pool 20 to 50 can improve the final RRF cutoff placement, while 100 provides no further observed benefit.

**Not established:**

- Whether the gold annotations omit valid alternative evidence or whether unjudged candidates are false positives. The annotations are not exhaustive relevance judgments.
- Whether AND-style query semantics, filtering, metadata joins, or section/chunk mapping caused the protected lexical zero-recall observations. No protected candidates were inspected in this diagnostic; the separately recorded public FTS probes show that long PostgreSQL FTS queries can return zero under AND semantics but cannot prove that was the T006 cause.
- Whether source extraction omitted any scientifically relevant content for these records. Original raw XML is unavailable. Gold paragraphs in the delivered corpus are present and locator-consistent, but that does not prove completeness of unannotated evidence.

## End-to-end upstream pipeline review

Read-only code inspection covered `sciscope.jats.parser`, locator/source safety, `sciscope.chunking.core`, chunk serialization/loading/validation, embedding input/configuration/pipeline, delivery contract, and retrieval BM25/RRF/reranking modules.

- JATS parsing preserves paragraph text and traverses approved inline elements (`italic`, `bold`, `xref`, `named-content`, subscripts/superscripts, etc.) while recording omitted child kinds. It does not turn table, figure, formula, list, or boxed-text contents into paragraph evidence; chunk records are explicitly paragraph chunks. This is a declared source-coverage boundary, not a defect proven to affect the six annotated units.
- Chunking is source-span based, paragraph/sentence aligned where possible, bounded by the configured token budget, and records half-open source offsets and locators. All six reviewed gold quotations fit a single existing chunk; no chunk-boundary mismatch explains their ranking misses.
- Embedding inputs use the approved `embedding-text-v1` heading-plus-chunk template, empty configured prefixes, and `text-embedding-3-small` at 1536 dimensions. The retrieval corpus is frozen at embedding set 115. No mismatch or missing vectors were observed in the existing approved development path.
- Delivery and chunk validators enforce hashes, IDs, locator/span shape, row mapping, dimensions, and exact file provenance. No upstream metadata/join fault is confirmed by the current evidence.

Because raw XML is unavailable, this review cannot reparse the source articles or establish whether table/figure/formula extraction would change retrieval. Any such pipeline change or corpus/embedding regeneration would require coordination with Person 1 and a separately versioned corpus; no shared code or frozen data was changed here.

## Evidence-selection follow-up

A fixed-pool, read-only MMR experiment and a two-per-DOI stress control were run after this rank trace. MMR improved macro MRR@10/nDCG@10 (.625/.647) versus dense v1 (.521/.582) but reduced Recall@20 from 1.0 to .875 and All-Required-Evidence@20 from 1.0 to .75; it lost one of two required comparison passages. A simple DOI cap reduced Recall@20 to .25 and dropped same-paper and factual evidence. Thus no selector improvement is defensible from the current five questions; complete metrics, per-question regressions, methodology, and downstream handoff are recorded in [`RETRIEVAL_V2_EVIDENCE_SELECTION_EXPERIMENTS.md`](RETRIEVAL_V2_EVIDENCE_SELECTION_EXPERIMENTS.md). The current recommended reference is dense v1; RRF remains opt-in, and MiniLM stays disabled. This is not a general superiority claim.

## Smallest justified next steps

1. Keep `retrieval.v1` and current v2 defaults unchanged; do not enable MiniLM by default. Existing negative MiniLM evidence and current comparison regressions argue against doing so.
2. Before a lexical/hybrid improvement cycle, build a separate versioned, source-grounded diagnostic set covering exact terms, punctuation, acronym variants, numeric values, methods, named entities, and longer questions, with independently reviewed evidence and exhaustive-enough judgments for the diagnostic purpose. Keep it separate from Golden held-out cohorts.
3. In that approved cycle, vary one factor at a time: test conservative stopword handling and tokenizer alternatives first; inspect RRF branch ranks without calling unjudged items irrelevant; compare final cutoffs at candidate depth 20 and 50; treat MiniLM as an optional experiment unless it demonstrates repeatable gains that justify CPU cost.
4. If evidence is found to depend on omitted JATS structures or source extraction, coordinate a targeted Person 1 change, validate it against raw source files, then propose a separately versioned corpus/embedding set. Do not repair or regenerate the frozen pilot in place.

`V2-14` remains open for independent verification and owner acceptance. No protected evaluation, database write, corpus change, retrieval-default change, or shared-interface change occurred.
