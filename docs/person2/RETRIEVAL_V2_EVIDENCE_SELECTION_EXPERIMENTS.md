# Retrieval v2 evidence-selection experiments

**Status:** exploratory diagnostics only; no production selector/default was changed. V2-14 remains open.

## Reproduction identity

- Platform: native Windows, repository `.venv`, Python 3.12, PostgreSQL 17.
- Evaluation population: the same five approved development questions only; positive metric denominator is four. Insufficient-evidence positive relevance metrics are undefined.
- Corpus: frozen `pilot17-xml-1fff1573b610`, embedding set 115, 728 chunks; existing query vectors only.
- Question/vector set SHA-256: `90f5568fd7c3f2afc56d8f1129ea98a421b66ee5d933ee89d08bddabeb331dfc`.
- Candidate pool: dense 50 plus BM25 50, RRF union up to 100; final selection top 20. All queries used read-only database snapshots.
- Selector D: fixed MMR with lambda .7, query-to-document and document-to-document cosine over the existing compatible vectors. No gold ID, answer, question type, expected DOI, or gold evidence is consulted by the selector.
- Selector E: RRF order with a two-chunks-per-DOI cap, tested only as a negative stress control. DOI diversity is not treated as relevance or evidence complementarity.
- The baselines are the previously frozen development-comparison report. Per-question quality metrics use the approved evidence matcher after selection.
- Reproduction helper/report are Git-ignored: `.cache/retrieval_v2/evidence_selector_experiment.py` and `.cache/retrieval_v2/evidence-selector-experiment.json`. Report SHA-256: `89a8480585e5acf169496b35e2699b6dd95b9c8677ca17973c4cceda658ec2f7`.

## Aggregate results

| Arm | Recall@5 / @10 / @20 | MRR@10 | nDCG@10 | Required-source coverage@20 | All required evidence@20 | Latency |
|---|---|---:|---:|---:|---:|---:|
| Dense v1 baseline | .750 / .875 / 1.000 | .521 | .582 | 1.000 | 1.000 | median retrieval 23.46 ms |
| Dense + BM25 + RRF | .625 / .875 / 1.000 | .421 | .536 | 1.000 | 1.000 | median retrieval 88.65 ms |
| RRF + MiniLM | .625 / .750 / .875 | .375 | .472 | .875 | .750 | median end-to-end 4,250 ms; reranking stage median 4,142 ms |
| RRF + MMR lambda .7 | .750 / .875 / .875 | .625 | .647 | .875 | .750 | selector-only median 3.44 ms |
| RRF + DOI cap 2 (stress control) | .250 / .250 / .250 | .250 | .250 | .250 | .250 | selector-only median .016 ms |

The dense/RRF/MiniLM timing values are from the existing repeated baseline run; selector timings are one timing sample per question and cover only selection, not database retrieval. Do not add these timing populations as if they were measured in one synchronized run. MMR improves early-rank MRR/nDCG on this sample but loses completeness at rank 20 compared with dense/RRF. A quality objective that values complete necessary evidence cannot select MMR as the winner from these data.

Evidence Coverage@k is numerically the same as the approved evidence-unit Recall@k here because both count the same annotated positive evidence units. Reporting both can improve interpretability but is not an independent metric. All-Required-Evidence is the stricter Boolean check. Required-Source Coverage measures the fraction of distinct annotated source DOIs represented; it does not show that every paper contributes a useful or scientifically complementary finding.

## Per-question evidence at cutoffs

The table shows Recall@20 and whether every annotated required evidence unit is present by rank 20. The source-coverage field is descriptive. Question types are read for post-hoc reporting only; every selector uses the same inference-time policy.

| Question / annotation type | Dense | RRF | RRF + MiniLM | RRF + MMR | DOI cap control |
|---|---|---|---|---|---|
| `gq-cmp-001` / multi-paper comparison | 1.00; complete; source coverage 1.00 | 1.00; complete; 1.00 | .50; incomplete; .50 | .50; incomplete; .50 | 0; incomplete; 0 |
| `gq-conf-001` / conflicting-evidence query | 1.00; complete; 1.00 | 1.00; complete; 1.00 | 1.00; complete; 1.00 | 1.00; complete; 1.00 | 0; incomplete; 0 |
| `gq-gap-001` / research gap | 1.00; complete; 1.00 | 1.00; complete; 1.00 | 1.00; complete; 1.00 | 1.00; complete; 1.00 | 1.00; complete; 1.00 |
| `gq-sp-001` / single-paper factual | 1.00; complete; 1.00 | 1.00; complete; 1.00 | 1.00; complete; 1.00 | 1.00; complete; 1.00 | 0; incomplete; 0 |
| `gq-ins-001` / insufficient evidence | Positive evidence metrics undefined; each baseline returned 50 candidates, MMR selected 20, DOI cap selected 19. None of these counts establishes absence of evidence in the literature. |

For `gq-cmp-001`, the annotated required source coverage at 20 is 1.0 for dense/RRF and .5 for MiniLM/MMR; RRF and dense retrieve both gold passages, while MMR retrieves only one. The evidence is a comparison case. `gq-conf-001` has two annotated passages from one paper; there are no opposing-finding side labels, so these results do not measure conflict-side completeness or genuine-conflict sensitivity. The research-gap case has only one annotated required passage; its retrieval coverage does not judge whether a generated gap is scientifically valid.

## Findings and recommendation

1. **Do not recommend MMR as a default.** It raises macro MRR@10 and nDCG@10 versus dense on this small sample, but lowers Recall@20, required-source coverage@20, and all-required-evidence@20 from 1.0 to .875/.875/.75. On the comparison query it loses one of two required sources/passages by rank 20. Cosine similarity is only a redundancy proxy; semantically similar passages may contain distinct necessary findings.
2. **Reject DOI capping as an evidence-completeness policy.** The two-per-paper stress control leaves the annotated same-paper pair in `gq-conf-001` unretrieved, despite that query having two necessary passages from one source. At top 20 it also loses the factual evidence in `gq-sp-001` and both comparison sources. This demonstrates why paper count is not scientific complementarity.
3. **Keep MiniLM disabled by default.** It does not improve macro relevance measures over dense/RRF and fails comparison completeness at 20 while adding seconds of CPU latency.
4. **Retain dense v1 as the simplest defensible reference/default.** On the same five questions, dense has complete annotated evidence by rank 20, higher Recall@5 and MRR/nDCG than RRF, and lower measured latency. RRF remains an opt-in, independently selectable v2 mode; it preserves Recall@20 here but harms the comparison question's early rank. No approach is proven generally superior by five questions.
5. **Do not add question-type-specific routing.** There is only one question per represented type in this development sample; the conflict item lacks opposing-finding groups and Golden v1's conflict examples are negative controls. This is inadequate evidence for adaptive policies.

No experimental selector is implemented in the retrieval path. No gold annotation, frozen dataset, corpus, vector, partition, or retrieval default was modified. The temporary helper and numeric report are ignored by Git and contain no question or passage text.

## Supported coverage metrics and their limits

- **Evidence Coverage@k:** unique required evidence units retrieved divided by annotated required units; defined only for positive-answerable questions with nonempty ground truth. In this protocol it equals Recall@k.
- **All-Required-Evidence@k:** true only when every annotated positive unit is retrieved by `k`; undefined for insufficient-evidence cases.
- **Required-Source Coverage@k:** distinct gold DOI sources retrieved divided by distinct annotated required DOI sources. This checks source representation, not scientific usefulness.
- **Comparison coverage:** report required-source coverage and all-required-evidence for comparison annotations. If the annotation does not define evidence sides/groups, side-level completeness is unavailable.
- **Conflicting-findings coverage:** unavailable without explicit labels for each comparable finding side and source. A negative-control query that rejects an apparent conflict cannot measure genuine-conflict detection sensitivity.
- **Research-gap coverage:** retrieval coverage of annotated supporting findings/limitations only. It cannot assess generated gap validity or hypothesis quality.
- **Insufficient evidence:** report candidate count/rank distribution and validated sources separately. A nonempty or empty retrieval set cannot prove literature-wide presence or absence.

## Downstream Person 3 requirements

- Cite only actual returned result IDs. Resolve each citation against the same response and preserve exact passage text, DOI, title, stable chunk ID, source locator, section path, and corpus provenance.
- Treat every ranking score as a relative signal, never as a calibrated probability or proof of claim support.
- Assess each generated claim against the retrieved passage itself. Valid DOI mapping does not prove that the passage entails the claim.
- For comparisons, surface evidence from all explicitly required annotated source sides when retrieved; do not pad with unrelated papers to satisfy a diversity heuristic.
- For conflicts, distinguish comparable findings that disagree from different populations, interventions, outcomes, or measurement conditions. Never infer conflict from different DOIs or scores.
- For research gaps/hypotheses, present the cited findings and limitations that motivate the proposed gap; label hypotheses as proposals rather than established results.
- If retrieved source evidence is insufficient, state that the available retrieved sources do not support a reliable answer and identify what is missing. Retrieval scores cannot guarantee sufficiency.
- Preserve retrieved evidence records and ranking/provenance metadata in any downstream evaluation trace; keep answer correctness, citation entailment, comparison completeness, conflict explanation, and hypothesis quality as separate generation-level judgments.

## Requirements for a larger independent evaluation set

Before making broad scientific-reliability claims, create a separately versioned, source-grounded set with multiple independently curated questions per task type and topic/domain, with a sealed test partition and no use in tuning. Determine its size through a pre-specified precision/power objective instead of choosing an arbitrary count. Each record should have:

- Frozen wording, answerability scope, query provenance, and development/test assignment before system runs.
- Exhaustively reviewed positive and graded partially relevant evidence units, valid alternatives, explicit negative judgments for known distractors, DOI, exact locator/chunk spans, and source-integrity hashes.
- Required evidence groups and required source mapping for each multi-part answer, with side labels for comparisons. Genuine conflict questions require comparable methods/populations/outcomes/conditions and independently verified opposing findings. Include non-equivalent/apparent-conflict negative controls separately.
- Research-gap questions with the corpus-bounded supporting findings and limitations that justify the gap; do not score generated hypothesis quality as retrieval relevance.
- Insufficient-evidence questions with a bounded corpus/search scope, expert-reviewed answerability label, evidence that the corpus does not support the requested assertion within that scope, and known near-miss evidence. Do not label an empty result as proof of absence.
- Independent blinded annotators, adjudication records, inter-annotator agreement where applicable, and complete AI/human provenance.
- Coverage of exact terminology, punctuation/hyphenation, acronyms and expansions, numerical values, assay/method terms, named entities, long natural questions, and table/figure/formula-dependent evidence when those source types are in scope.
- Separate retrieval-unit relevance/completeness labels from answer factuality, citation entailment, conflict explanation, and hypothesis-quality judgments.

Current frozen corpus limitations remain: original XML is unavailable in this workspace, and retrieval input consists of paragraph chunks; tables, figures, formulas, lists, and boxed text are not independently represented as evidence units. No source evidence currently links those omissions to the observed development failures. Any extraction/chunking change or corpus/vector regeneration requires an explicitly versioned upstream proposal and impact verification; the frozen pilot must remain unchanged.
