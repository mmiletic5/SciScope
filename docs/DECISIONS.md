# Bootstrap Decisions and Open Questions

This log separates agreed bootstrap constraints from design proposals and
reported approvals. Person 1 confirmed that TEAM ratified the exact current
constitution 0.1.0 text on 2026-11-14 and reported the Feature 002 approvals
below. No individual signatures, meeting record, or other external evidence
was supplied. Approval does not establish task completion or approve shared
JSON Schema edits.

| ID | Status | Decision or question | Owner/review |
| --- | --- | --- | --- |
| D-001 | Agreed context | Four research workflows share one RAG infrastructure. | TEAM |
| D-002 | Agreed context | Initial entity hierarchy is Paper → Section → Chunk; preserve original JATS XML. | Person 1, Person 2 |
| D-003 | Bootstrap tooling | Use project-local `.venv`, uv lockfile, and a dev dependency group. No application packages until feature approval. | TEAM |
| D-004 | Proposed | `intfloat/multilingual-e5-small`, 384 dimensions, 512-token total input, `passage:`/`query:` prefixes. Validate with source papers. | Person 1, Person 2 |
| D-005 | Required policy | Fake mode is default; live Gemini requires explicit configuration. Routine CI never calls paid AI. | Person 3 |
| D-006 | Partially resolved for Feature 002 | Person 1 reports TEAM approval of documented scientific eligibility, conditional comparative inclusion, review cap, 3–5-to-20 count rule, screening, provenance, and unknown handling. Actual article/JATS and paper-specific license evidence remains unverified. | Person 1, TEAM |
| D-007 | Partially resolved for Feature 002 | Person 1 reports Person 2 approval of the documented DOI comparison and proposed source locator/XML versioning approach. Required processed metadata, section taxonomy, and any field-level shared-contract edit remain open. | Person 1, Person 2 |
| D-008 | Open | Chunk boundaries, overlap, table/caption/reference handling, and actual token budgets. | Person 1, Person 2 |
| D-009 | Open | Filter, retrieval ranking, API and provider interface contracts; error behavior. | Affected owners |
| D-010 | Partially resolved for Feature 002 | Person 1 reports approval of the documented golden follow-up requirements and identified schema gaps. Golden relevance rubric, negative-case semantics, metric interpretation, and any schema edit remain open. | Person 1, Person 2 |
| D-011 | Partially resolved | Person 1 confirmed TEAM ratification of the exact current constitution 0.1.0 text, original date 2026-11-14. Approval of draft shared contracts remains open; no field-level schema change was approved. | TEAM |

## Feature 002 approval provenance (reported 2026-11-14)

Person 1, the feature owner, reports that relevant TEAM and Person 2 approvals
were obtained outside the repository. Person 1 specifically confirmed TEAM
ratification of the exact current constitution text and its original date;
the repository cannot independently inspect the external approval record.
No individual reviewer identity, signature, or meeting date is inferred.

The reported approvals cover the current Feature 002 `spec.md`, `plan.md`, and
`tasks.md` planning baseline and authorization for T001–T010 in their documented
dependency order. They also cover the documented scientific eligibility and
conditional comparative rules; at most three clearly labeled reviews within
the 20-paper target; the first 3–5 inspected papers counting toward 20; DOI
normalization/comparison; source locator and XML versioning approach; screening,
provenance, unknown-metadata handling; separation of the screening manifest
from the processed-data contract; and the golden follow-up requirements and
identified schema gaps.

This is approval of decisions and task execution, not evidence that any task,
source check, paper selection, checklist review, or schema change is complete.
Shared ingestion and golden JSON Schemas and other team-owned interfaces still
require separately reviewed, documented field-level change approval. Person 1
later reported successful API and individual XML observations from Windows
PowerShell. Person 1 subsequently supplied article-type, license, and
publisher-page observations and explicitly accepted T001 on 2026-11-14.
The owner then authorized grouped T002–T010 documentary execution. Each task
retains its source, dependency, and human-review gate; no schema edit or
post-execution Feature 002 acceptance follows from this authorization.

The local dependency check is limited to existing repository artifacts and the
official [uv lock/sync guide](https://docs.astral.sh/uv/concepts/projects/sync/),
[uv GitHub Actions guide](https://docs.astral.sh/uv/guides/integration/github/),
[Spec Kit Codex integration](https://github.github.com/spec-kit/integrations/codex.html),
and [embedding model card](https://huggingface.co/intfloat/multilingual-e5-small).
The project has no application code, so adding FastAPI, model packages, or a
database driver now would precede the required feature decisions. The uv
lockfile and local sync remain unverified until the environment blocker is
resolved; see [EVIDENCE.md](../EVIDENCE.md).
