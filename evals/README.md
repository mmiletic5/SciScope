# Evaluation data

This directory defines the format and future location for SciScope's manually
verified honeybee evaluation questions. The bootstrap does not include any
scientific question or answer. Create real records only in the approved Person
1 dataset feature after inspecting actual source articles.

## Format

Validate dataset files against [`golden_questions.schema.json`](golden_questions.schema.json).
The schema describes a versioned dataset with question records, source DOI and
section references, source quotations or locators, relevance labels, reviewer
and verification metadata, and optional insufficient-evidence expectations.
Prefer stable source locators over generated chunk IDs.

## Curation rules

- Begin with approximately 10–20 real PLOS honeybee papers and 5–10 manually
  verified questions; expand toward 20–30 questions when practical.
- Derive reference answers from inspected papers. Do not invent papers, DOIs,
  findings, quotations, or answers.
- Keep question IDs stable and version the dataset and source corpus.
- Record the human reviewer and verification status. An unverified record must
  not be presented as verified ground truth.
- Record the reason, reviewer, and date when correcting expected answers or
  relevance labels; preserve the previous record or change history.
- Keep mock/test fixtures clearly labeled and separate from verified ground
  truth.

See [`../docs/EVALUATION_PLAN.md`](../docs/EVALUATION_PLAN.md) for ownership,
metrics, reporting expectations, and circularity controls.
