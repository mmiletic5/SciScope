# SciScope Evaluation Plan

## Purpose and scope

Establish a reproducible, human-verified evaluation set and evaluation approach
for the shared SciScope RAG system. Golden v0 is present; its provenance and
limitations are recorded under Dataset status. No evaluation results were
produced by this change.

## Golden dataset creation

Candidate records are drafted by AI from inspected source text, never by the
evaluated RAG system. AI-drafted candidates must have
`verification_status: "unverified"` until a named human reviews them. EVERY
record must be verified by a human who reads the cited source passage and
checks the question, reference answer, locators, and relevance labels. Only
`verified` records enter a released dataset.

Questions must be paraphrased, not copied from the text. Quotations must be
verbatim and machine-checked with `check-quote`. Do not invent scientific
findings, articles, DOI values, quotations, or reference answers. Derive each
reference answer from inspected source text, not solely from model knowledge.
Ground truth is never produced or revised by the evaluated system.

Each record must capture a stable question ID, question text, query language,
expected key findings or reference answer, relevant paper DOI(s), section names
or paths, supporting quotations or durable source locators, evidence relevance
labels, reviewer, verification status, and source corpus version. An expected
negative or insufficient-evidence result is optional. Prefer DOI, section, and
source text locators as ground truth; generated chunk IDs can change when
chunking rules change.

Use `evals/golden_questions.schema.json` as the format contract. Keep unverified
candidates separate from released datasets. Version both the dataset and source
corpus. Document changes to answers or relevance labels with the reason,
reviewer, and date when known; retain prior versions or a change history.

The optional `question_type` field classifies a record as:

- `single_paper_factual`: a factual question answered by one paper.
- `multi_paper_comparison`: a comparison supported by several papers.
- `conflicting_evidence`: a question about conflicting findings or claims.
- `research_gap`: a question about a source-supported gap or open issue.
- `insufficient_evidence`: a question the corpus cannot adequately answer.

Evidence relevance labels are stored as strings using this rubric:

| Label | Meaning |
| --- | --- |
| `3` | The paragraph directly gives the answer. |
| `2` | The paragraph provides an important part of the answer. |
| `1` | Related background. |
| `0` | Deliberate distractor. |

Labels >= 2 count as relevant.

### Source corpus version

Compute `corpus_version` as `"pilot17-xml-"` plus the first 12 hexadecimal
characters of SHA-256 over the UTF-8 lines `<doi>\t<xml_sha256>\n` for the 17
source XMLs from `data/pilot/manifest.jsonl`, sorted by line. Here `\t` is a
literal tab and `\n` is LF, including the final LF. This identifier depends only
on source XML, not on the parser, chunking, or embeddings.

Recomputed on 2026-11-18: `pilot17-xml-1fff1573b610`.
Full SHA-256:
`1fff1573b610c27e2e8016343d2f6429df294db974db4af898c4a0f82ffc26bd`.

## Responsibilities

- **Person 1 — Data Processing & Embedding:** select representative papers;
  inspect source articles; oversee AI drafting and human verification of every
  record, including questions, answers, locators, and relevance labels; maintain
  dataset and corpus versions.
- **Person 2 — Database & Retrieval:** evaluate retrieval against the approved
  dataset; compare semantic, lexical, and hybrid search; assess filtering and
  ranking; report retrieval metrics.
- **Person 3 — Backend & AI:** use the same verified evidence to evaluate answer
  generation, citation handling, and insufficient-evidence behavior.
- **Person 4 — Frontend & Integration:** prepare UI and end-to-end scenarios
  using approved, versioned test fixtures.

## Retrieval evaluation

Use the same versioned questions and relevance labels when comparing system
variants. Record the dataset version, corpus version, retrieval configuration,
filter settings, cutoff K, and command/environment for every run. At minimum,
plan to report:

- **Recall@K:** fraction of known relevant evidence items retrieved in the top K.
- **Evidence Hit@K:** whether at least one labeled relevant evidence item
  appears in the top K; report the aggregate and per-question results.
- **MRR:** mean reciprocal rank of the first relevant result when one ranked
  result per question is appropriate.

Compare semantic, lexical, and hybrid retrieval on the same cases. Evaluate
metadata filtering and ranking separately where possible. Define treatment of
multiple relevant papers, ties, and questions with no expected evidence in the
approved evaluation specification before interpreting scores. Do not claim a
metric or result until it has been computed and recorded.

## Answer, citation, and reliability evaluation

Use the source passages and relevance labels in the golden dataset to inspect
whether answers are supported, citations resolve to the supplied sources, and
the system declines or qualifies answers when evidence is insufficient. Record
citation validity separately from citation support. Cover scientific
comparison quality, token use, response latency, error scenarios, security
checks, and regression behavior as the implementation and fixtures become
available. Do not use the system under evaluation to generate or revise its own
ground truth.

## Circularity controls and reporting

- Do not generate expected answers using the evaluated system.
- Do not change ground truth solely to improve system metrics.
- Inspect cited source material and document every correction with its reason.
- Keep test fixtures distinct from verified scientific ground truth and label
  simulated outputs as mock/test data.
- Report failures, missing labels, unavailable checks, and limitations alongside
  results. Preserve raw run configuration and dataset versions so comparisons
  can be reproduced.

## Dataset status

Golden v0 exists at `evals/golden_questions.v0.json`, with `dataset_version`
`"v0"` and `corpus_version` `"pilot17-xml-1fff1573b610"`. It contains 21 questions
over 12 of the 17 pilot PLOS ONE papers:

| Question type | Count |
| --- | ---: |
| `single_paper_factual` | 8 |
| `multi_paper_comparison` | 4 |
| `conflicting_evidence` | 3 |
| `research_gap` | 3 |
| `insufficient_evidence` | 3 |

All 21 records were AI-drafted from the pilot papers, never from the evaluated
RAG system, then read and verified by Person 1. The records name reviewer
`"Person 1"`, `verification_status: "verified"`, and
`verified_date: "2026-11-18"`. All 33 evidence quotations were machine-checked
verbatim with `check-quote`. Human verification and these quotation checks are
reported by Person 1 in chat on 2026-11-18; they were not repeated by the
assistant during this documentation change.

Known limitations:

- All 21 questions are AI-drafted and human-verified. The previously planned
  approximately 30% human-written questions are deferred to a later version
  (Person 2).
- `conflicting_evidence` records concern author-versus-prior-literature
  conflicts inside one paper, not conflicts across several corpus papers.
- `insufficient_evidence` records rest on lexical search plus reading. They are
  supporting evidence only, not proof of absence. Chunks omit tables, captions,
  formulas, and supplementary material.
- All evidence comes from body paragraphs; none comes from abstracts.
- 21 questions over 12 of the 17 pilot papers provide an indicative regression
  signal, not a statistical estimate.

No evaluation results were produced. Dataset availability and curation checks
do not establish retrieval or answer-generation performance.
