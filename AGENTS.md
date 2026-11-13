# SciScope agent instructions

- Read `.specify/memory/constitution.md` and relevant specifications. Follow official
  Spec Kit workflow and apply repository-local skills when their scope matches.
- Invoke `$solution-research` before creating or finalizing a feature specification
  and before feature tests. Research existing solutions; distinguish facts from gaps.
- Never implement without an explicitly approved specification and plan. Write behavior
  tests first, then implement only the approved, small task scope.
- Invoke `$google-python-engineering` for Python creation, change, test, or review.
  Follow the Google Python Style Guide. Use English in all code, identifiers, comments,
  and docstrings, regardless of prompt language.
- Respect module owners and existing shared contracts. Ask targeted questions when a
  necessary decision is unresolved; never invent requirements, sources, results,
  approvals, or verification.
- Ownership: Person 1 handles data processing and embeddings; Person 2 database and
  retrieval; Person 3 backend and AI; Person 4 frontend and integration.
- Never expose credentials. Use the fake AI provider by default; live providers require
  explicit configuration. Keep tests free of paid AI calls.
- Update `PROJECT_TODO.md` and `EVIDENCE.md` when they exist (planned for later
  bootstrap parts). Never mark a task complete without automated and human verification.
- Stop at the approved scope; do not automatically start another feature.

For local setup, including the preferred Codex model, see `DEVELOPMENT_SETUP.md`.
Detailed guidance in `docs/DEVELOPMENT_WORKFLOW.md` is planned for Part 2.
