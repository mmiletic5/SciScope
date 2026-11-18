# Bootstrap Decisions and Open Questions

This log separates agreed bootstrap constraints from design proposals. The
constitution remains a draft awaiting PR review. No feature spec or
plan has yet been approved.

| ID | Status | Decision or question | Owner/review |
| --- | --- | --- | --- |
| D-001 | Agreed context | Four research workflows share one RAG infrastructure. | TEAM |
| D-002 | Agreed context | Initial entity hierarchy is Paper → Section → Chunk; preserve original JATS XML. | Person 1, Person 2 |
| D-003 | Bootstrap tooling | Use project-local `.venv`, uv lockfile, and a dev dependency group. No application packages until feature approval. | TEAM |
| D-004 | Proposed | `intfloat/multilingual-e5-small`, 384 dimensions, 512-token total input, `passage:`/`query:` prefixes. Validate with source papers. | Person 1, Person 2 |
| D-005 | Required policy | Fake mode is default; live Gemini requires explicit configuration. Routine CI never calls paid AI. | Person 3 |
| D-006 | Open | Corpus inclusion/exclusion, PLOS/JATS variation, and licensing policy. | Person 1, TEAM |
| D-007 | Proposed | Propose F001 DOI normalization, required metadata via papers.jsonl, taxonomy v0, the `jats:v1` locator and processing version semantics in draft contract 0.3.0. Proposed until Person 2 PR approval. | Person 1, Person 2 |
| D-008 | Open | Chunk boundaries, overlap, table/caption/reference handling, and actual token budgets. | Person 1, Person 2 |
| D-009 | Open | Filter, retrieval ranking, API and provider interface contracts; error behavior. | Affected owners |
| D-010 | Open | Golden relevance rubric, negative cases, and metric interpretation. | Person 1, Person 2 |
| D-011 | Closed 2026-11-14 | Contract and constitution changes go through PR review; no formal ratification. | TEAM |

F003 pilot (2026-11-17) used hosted OpenAI `text-embedding-3-small` (1536 dimensions) through an explicit `--live` run; `multilingual-e5-small` was not run in F003. The OpenAI configuration defaults are `passage_prefix=""` and `query_prefix=""`, differing from D-004's `passage:`/`query:` proposal. Status stays Proposed pending Person 2 and a Golden v0 comparison; see EVIDENCE.md.

The local dependency check is limited to existing repository artifacts and the
official [uv lock/sync guide](https://docs.astral.sh/uv/concepts/projects/sync/),
[uv GitHub Actions guide](https://docs.astral.sh/uv/guides/integration/github/),
[Spec Kit Codex integration](https://github.github.com/spec-kit/integrations/codex.html),
and [embedding model card](https://huggingface.co/intfloat/multilingual-e5-small).
The project has no application code, so adding FastAPI, model packages, or a
database driver now would precede the required feature decisions. The uv
lockfile now exists on `main`, and routine commands use `--locked`. Local sync
and CI remain unverified; see [EVIDENCE.md](../EVIDENCE.md).
