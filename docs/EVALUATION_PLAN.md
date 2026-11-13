# SciScope Evaluation Plan

## Purpose and scope

Establish a reproducible, manually grounded evaluation set and evaluation
approach for the shared SciScope RAG system. The bootstrap defines the record
format and process only. It does not contain scientific questions, answers,
papers, DOIs, quotations, or measured results. Create the real dataset only in
the approved Person 1 feature after inspecting source articles.

## Golden dataset creation

Start by selecting approximately 10–20 real PLOS honeybee papers. Prepare an
initial 5–10 manually verified questions and expand toward 20–30 when practical.
Do not invent scientific findings, articles, DOI values, or reference answers.
Derive each reference answer from inspected source text, not solely from model
knowledge.

Each record must capture a stable question ID, question text, query language,
expected key findings or reference answer, relevant paper DOI(s), section names
or paths, supporting quotations or durable source locators, evidence relevance
labels, reviewer, verification status, and source corpus version. An expected
negative or insufficient-evidence result is optional. Prefer DOI, section, and
source text locators as ground truth; generated chunk IDs can change when
chunking rules change.

Use `evals/golden_questions.schema.json` as the format contract. Store no
unverified or invented scientific records. Version both the dataset and source
corpus. Document changes to answers or relevance labels with the reason,
reviewer, and date when known; retain prior versions or a change history.

## Responsibilities

- **Person 1 — Data Processing & Embedding:** select representative papers;
  inspect source articles; prepare and verify questions, answers, locators, and
  relevance labels; maintain dataset and corpus versions.
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

## Bootstrap status

The dataset has not been populated. No scientific articles were inspected and no
evaluation results were produced as part of this planning document.
