# Evaluation data

This directory contains SciScope's human-verified honeybee evaluation dataset.
Golden v0 is present in [`golden_questions.v0.json`](golden_questions.v0.json):
21 AI-drafted, human-verified questions. See the
[evaluation plan](../docs/EVALUATION_PLAN.md#dataset-status) for provenance,
status, and limitations. No evaluation results were produced by this change.

## Format

Validate dataset files against [`golden_questions.schema.json`](golden_questions.schema.json).
The schema describes a versioned dataset with question records, source DOI and
section references, source quotations or locators, relevance labels, reviewer
and verification metadata, optional `question_type`, and optional
insufficient-evidence expectations. The evaluation plan documents the five
question types, relevance labels, and source corpus version recipe.
Prefer stable source locators over generated chunk IDs.

## Curation rules

- Draft candidate records with AI from inspected source text, never with the
  evaluated RAG system. Ground truth is never produced or revised by that
  system.
- AI-drafted candidates must have `verification_status: "unverified"` until a
  named human reviews them. EVERY record must be verified by a human who reads
  the cited source passage and checks the question, answer, locators, and
  relevance labels. Only `verified` records enter a released dataset.
- Paraphrase questions rather than copying them from the text. Derive reference
  answers from inspected papers. Quotations must be verbatim and
  machine-checked with `check-quote`. Do not invent papers, DOIs, findings,
  quotations, or answers.
- Keep question IDs stable and version the dataset and source corpus.
- Record the human reviewer and verification status. An unverified record must
  not be presented as verified ground truth.
- Record the reason, reviewer, and date when correcting expected answers or
  relevance labels; preserve the previous record or change history.
- Keep mock/test fixtures clearly labeled and separate from verified ground
  truth.

See [`../docs/EVALUATION_PLAN.md`](../docs/EVALUATION_PLAN.md) for ownership,
metrics, reporting expectations, and circularity controls.
