# SciScope Constitution

## Core Principles

### I. Specification and Approval

Every meaningful feature MUST begin with the official Spec Kit workflow: research existing
solutions, write and clarify a specification, then produce a reviewable plan and small,
traceable tasks. Implementation MUST wait for explicit human approval of the specification
and plan. Research alone does not authorize implementation. Do not invent requirements,
sources, results, or approvals; ask targeted questions when essential decisions are open.

### II. Test-First, Verifiable Delivery

For feature work, write behavior tests before implementation and demonstrate a failing
test before making it pass. Each task MUST have a defined acceptance check and automated
verification where practical. Each feature MUST receive manual human verification
before completion is marked. Record evidence for every implementation task in
`EVIDENCE.md`; report failed, skipped, and unexecuted checks honestly. A passing
automated test alone is insufficient to claim human verification.

### III. Scientific Provenance and Reproducibility

Every research artifact MUST preserve its source, retrieval or processing context, and
transform lineage sufficient to reproduce results. Scientific claims MUST be traceable to
actual source material. Evaluation data and metrics MUST distinguish observed results
from assumptions; do not fabricate papers, citations, findings, or measurements.

### IV. Shared Contracts and Reliable Engineering

Research Question Explorer, Evidence Comparison, Conflicting Evidence Finder, and
Research Gap & Hypothesis Assistant MUST use one shared RAG infrastructure. Module owners MUST
agree on versioned interfaces, data schemas, and error behavior before dependent work.
Changes to shared contracts require owner review and relevant integration checks. Handle
expected failures explicitly, expose actionable errors, and avoid silent fallback to a
different AI provider or data source. Prefer maintained, compatible solutions when research
supports them; avoid needless dependencies and duplicated business logic.

### V. Secure, Reviewable Code

Code, identifiers, comments, and docstrings MUST be in English. Python MUST follow the
Google Python Style Guide, with type annotations and Google-style docstrings where needed.
Secrets MUST remain outside version control, logs, screenshots, and evidence. Changes MUST
be small enough to review independently, pass applicable CI checks, and receive code review
before merge. No live AI call is permitted in default development or test mode.

## Engineering Constraints

Use Python 3.12 subject to dependency compatibility, FastAPI/Pydantic, React/TypeScript,
PostgreSQL with pgvector and full-text search, and a provider interface as the proposed
architecture; confirm detailed choices in later specifications and plans. The fake AI
provider is the default and requires no key. Gemini requires explicit configuration and
a valid key; a future OpenAI provider is an interface goal, not an initial dependency.
Tests MUST be isolated from paid external AI calls. `AI_PROVIDER=fake` MUST never silently
switch to a live provider. Repository-local Python and solution-research skills supplement,
and do not replace, official Spec Kit skills.

## Delivery Gates

Each feature follows research -> specification -> clarification when needed -> approved
plan -> small tasks -> failing behavior tests -> implementation -> automated checks ->
one human verification per feature -> evidence and task-state update -> code review and CI.
Record task ownership and cross-module contract decisions before parallel integration.
Use `PROJECT_TODO.md`, `EVIDENCE.md`, and `docs/DEVELOPMENT_WORKFLOW.md` for the
corresponding tracking and gates.

## Governance

This constitution governs repository work. Amendments require a written rationale, a
review of affected specifications and contracts, and PR review by another team member
before taking effect.
Use semantic versioning: major for incompatible governance changes, minor for added or
materially expanded rules, patch for editorial clarifications. Review every proposed
change and PR for constitutional compliance, test evidence, security, and contract impact.
This 0.2.0 document remains a draft pending review.

**Version**: 0.2.0 | **Ratified**: TODO(RATIFICATION_DATE): team approval pending | **Last Amended**: 2026-11-14
