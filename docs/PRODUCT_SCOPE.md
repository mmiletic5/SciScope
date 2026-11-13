# SciScope Product Scope (Draft)

SciScope is a proposed research aid for honeybee and related scientific literature.
It should help a researcher inspect evidence and source locations, while making
uncertainty and missing evidence visible. This is a product outline, not a claim
that the application or scientific corpus exists.

## Proposed workflows

1. **Research Question Explorer:** ask a question, retrieve relevant source
   passages, and inspect an answer with traceable citations.
2. **Evidence Comparison:** compare findings across papers with their source
   passages and metadata.
3. **Conflicting Evidence Finder:** surface potentially conflicting statements
   for review; a model's classification is not a scientific conclusion.
4. **Research Gap & Hypothesis Assistant:** identify possible gaps and draft
   hypotheses with explicit evidence limits and source references.

All four workflows must share one retrieval and provenance infrastructure.
Corpus eligibility, exact user journeys, acceptance criteria, and performance
targets belong in approved feature specifications. Saved research is optional
and requires separate approval.

## Bootstrap boundary

This repository currently contains planning artifacts and tooling only. It has
no downloader, corpus, embeddings, database, API, AI provider, frontend, or
verified scientific answers. See [the architecture draft](ARCHITECTURE.md),
[the evaluation plan](EVALUATION_PLAN.md), and [the master backlog](../PROJECT_TODO.md).
