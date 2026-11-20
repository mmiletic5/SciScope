# Person 2 Database and Retrieval Master Plan

**Status:** Approved working architectural baseline on 2026-11-18; Person 2 native Windows constraint approved 2026-11-19.
**Approval boundary:** The relevant feature specification and plan remain the
implementation approval gates. Once approved, Person 2 has standing authority
to execute routine local implementation, testing, documentation, and approved
non-destructive operations on `sciscope_test_005` without repeated routine
permission requests. This is operational authority, not approval of an
unapproved feature, changed architecture, infrastructure, or acceptance of
results. The main `sciscope` database remains protected and requires separate
authorization for modification.

## Standing Person 2 execution policy

This policy applies to all Person 2 phases A–E. Work runs natively on Windows
under the environment constraint below. For approved scope, execute routine
PowerShell, Python/uv, implementation, debugging, tests, static checks, and
documentation autonomously. Non-destructive DB operations (including migrations,
test writes, queries, and verification) are authorized on `sciscope_test_005`
only; verify the connected database is exactly that target before mutation.
Never expose credentials and retain least privilege. The user reviews milestone
reports and independently verifies important results; do not ask them to repeat
routine commands. At each completed feature, provide concise, copy-paste-ready
read-only PowerShell checks, expected output, and pass/fail criteria; wait for
the user's actual output and explicit acceptance before marking that feature
accepted. Stop for destructive/high-risk operations, main database or
infrastructure changes, elevated privileges, paid API calls, commits/pushes/MRs,
required approval gates, material architecture/security decisions, or genuine
blockers. Never bypass sandbox/security controls. Preserve feature approval and
human acceptance gates and do not extend scope by inference.

## Authority and decision states

## Permanent Person 2 environment constraint

All Person 2 development, implementation, testing, database operations,
retrieval, ranking, evaluation, and integration across Phases A–E and future
work must run natively on Windows 10 Pro x64 with Windows PowerShell and the
approved Python/uv toolchain. No Person 2 workflow may require Docker/Desktop,
WSL, Linux distributions or containers, Bash-only scripts, or Linux-only
dependencies. This owner-specific decision does not constrain other owners or
deployment platforms. It does not change PostgreSQL 17, pgvector 0.8.7, the
six-table model, `vector(1536)`, embedding model, contracts, algorithms, or
acceptance criteria. Exact Windows compatibility and repeatability must be
verified before being claimed.

This plan follows `AGENTS.md`, `.specify/memory/constitution.md`,
`docs/DEVELOPMENT_WORKFLOW.md`, the master backlog, approved Person 1 delivery
artifacts, and the validated delivery contract. Decisions use these states:

- **Required:** established by the backlog, repository governance, implemented
  delivery contract, or the organizer's fixed embedding requirement.
- **Approved baseline:** approved for architectural planning, but not for
  implementation.
- **Proposed:** technically recommended and still requires the applicable
  feature approval.
- **Cross-team review:** cannot become a shared contract until the named module
  owners agree.

The master plan and every phase specification/plan are separate approval gates.
Approval of this document does not approve Phase A or any later phase.

## Phase A detailed baseline

On 2026-11-18, Person 2 approved the detailed Phase A technical baseline and
authorized documentation persistence only. The implementation authority is
split into two separately traceable Spec Kit features:

- [`005-postgres-pgvector-foundation`](../../specs/005-postgres-pgvector-foundation/spec.md)
  covers P3-01 and P3-02: PostgreSQL/pgvector environment, migrations, schema,
  constraints, and real-database integration tests.
- [`006-validated-snapshot-ingestion`](../../specs/006-validated-snapshot-ingestion/spec.md)
  covers P3-03 and P3-04: delivery validation, exact manifest-owned vector
  mapping, transactional import, idempotency, explicit replacement,
  concurrency control, recovery, and independent reconciliation.

These documents become the detailed Phase A implementation authority after
their feature-level implementation approval. The standing execution policy
authorizes routine work within that approved scope and non-destructive
operations on `sciscope_test_005`; it does not authorize infrastructure changes,
the protected main database, or unapproved scope. Person 2 independently owns the
complete subsystem: unavailable cross-team agreement is recorded as an
assumption or versioned boundary, not an implementation blocker.

**Phase A closure (2026-11-19):** Features 005 and 006, covering P3-01 through
P3-04, are human-accepted and complete. Feature 006's owner independently
reported the full suite as 2,672 passed, 2 skipped, zero failures/errors in
106.73 seconds and the read-only pilot verifier as 10/10 PASS. Counts were 17
papers, 319 sections, 728 chunks, and 728 embeddings; all six reconciliation
mismatch counters were zero. Full records are in `EVIDENCE.md` and Feature 006
`tasks.md`.

## Verified baseline

At the planning audit, `main` was at commit
`a872cb7770ff0033795bacf3675d5dd514c72f07`. The locked delivery validator
reported 17 papers, 319 sections, 728 chunks, 728 vectors, six files, and zero
failures. The locked regression suite reported 2590 passed and two skipped.
These observations verify the existing delivery and tests, not a database or
retrieval system. No Person 2 persistence, retrieval, ranking,
context-selection, or evaluation implementation exists.

The pilot embedding contract is fixed: OpenAI `text-embedding-3-small`, 1536
dimensions, little-endian float32 delivery vectors, empty passage/query
prefixes, and ownership by `embedding_manifest.entries[].chunk_id`. Delivered
pilot embeddings must not be regenerated. Legacy E5 and local
sentence-transformers proposals are superseded for this subsystem.

## Requirements and traceability

| Task | Required deliverable | Phase | Acceptance focus |
| --- | --- | --- | --- |
| P1-09 | Combined metadata filter contract | B | Shared, deterministic semantics across all retrieval modes |
| P1-13 | Retrieval evaluation metrics and protocol | D, designed early | Evidence matching, metrics, negatives, reproducibility |
| P3-01 | PostgreSQL and pgvector local setup | A | Repeatable real database environment |
| P3-02 | Relational paper, section, and chunk model | A | Constraints, relationships, provenance, vectors |
| P3-03 | Validated data import pipeline | A | Validation before writes, rollback, real pilot |
| P3-04 | Idempotent indexing behavior | A | Same-delivery no-op and atomic replacement |
| P3-05 | Vector similarity search | B | Exact cosine baseline and deterministic ties |
| P3-06 | PostgreSQL full-text search | B | Native PostgreSQL FTS, explicitly not BM25 |
| P3-07 | Combined metadata filtering | B | Identical filtering in dense, lexical, and hybrid modes |
| P3-08 | Hybrid vector and lexical retrieval | B | Deterministic reciprocal-rank fusion |
| P3-09 | Ranking and duplicate-result policy | C | Stable ordering, duplicate suppression, diversity |
| P3-10 | Optional reranking benchmark | C | Without/with-reranker comparison; production remains optional |
| P3-11 | Retrieval context and token budgets | C | Deterministic budgeted evidence selection |
| P3-12 | Stable source identifier and locator lookup | C | DOI/locator/chunk resolution and citation provenance |
| P3-13 | Golden loading and retrieval evaluation integration | D | Versioned loader and DOI/locator matching |
| P3-14 | Recall@K, Evidence Hit@K, applicable MRR | D | Tested formulas, ties, multiple references, type reports |
| P3-15 | Retrieval latency benchmark | D | Repeated component and end-to-end measurements |
| P8-01 | Repeatable verified-Golden benchmark | D | Reproducible run manifests |
| P8-02 | Semantic versus lexical versus hybrid comparison | D | Identical corpus, questions, filters, and cutoffs |
| P8-03 | Evidence Hit@K evaluation | D | Per-question, aggregate, and type reports |
| P8-04 | Recall@K evaluation | D | Explicit denominators and macro reporting |

Shared dependencies include P4-02, P4-09, P4-14, P4-15, P4-20, P5-04,
P5-08, P6-01 through P6-03, and P8-05 through P8-13. Shared contracts require
review by the affected owners.

## Complete A-E roadmap

### Phase A: Database and ingestion

Scope P3-01 through P3-04: a real PostgreSQL/pgvector environment, relational
schema and migrations, validated full-snapshot import, exact chunk-to-vector
mapping, transactional rollback, idempotency, and clean-database pilot
verification. The required Person 2 environment is native Windows PostgreSQL
17 with pgvector 0.8.7, using SQLAlchemy, Alembic, psycopg 3, and
pgvector-python. PostgreSQL's official Windows download page points to the EDB
installer. pgvector upstream documents compiling v0.8.7 on Windows with Visual
Studio C++ tools and `nmake`; no official precompiled Windows extension package
was verified. Win10-specific installation, service, extension build, and test
compatibility remain to be rehearsed. Docker, WSL, and containers are excluded
from Person 2 workflows.

The smallest corpus-update approach is a complete validated snapshot
replacement. Validate before writes, load through transaction-local staging,
upsert authoritative IDs, prune records absent from the new snapshot, verify
all relationships/counts, and atomically activate the import. Reimporting the
same delivery digest is a no-op. Retain a compact import audit record. An
incremental producer contract, tombstones, or partial paper updates are out of
scope and require a future approved contract change.

Acceptance requires the real pilot counts 17/319/728/728, no orphan records,
sampled and aggregate vector ownership checks, repeat-import stability, forced
rollback proof, clean-database reproduction, automated checks, human
verification, evidence, and Person 1 provenance review.

### Phase B: Retrieval core and early integration

**Status:** The private Person 2 retrieval core for P3-05 through P3-08 was
independently verified by the owner and HUMAN-ACCEPTED/CLOSED on 2026-11-19.
The accepted implementation and evidence are frozen in Feature 007. This
closure does not approve the shared `retrieval.v1` contract or public facade;
P1-09/P1-11/P1-14, affected-owner integration, and the proposed GIN migration
remain pending. Feature 007 T007/T008 and the five-question integration smoke
remain gated follow-ups.

Database, vector, and retrieval checks execute in the native Windows PostgreSQL
environment with PowerShell-compatible commands. Retrieval semantics do not
change to accommodate the platform.

Accepted internal scope P3-05 through P3-08: exact dense cosine retrieval,
PostgreSQL full-text retrieval, the Person 2 internal metadata filter
implementation, and deterministic reciprocal-rank fusion. Exact search is the
baseline at 728 chunks; HNSW is deferred until measured scale/latency justifies
approximate search. BM25 is not native PostgreSQL FTS and is not part of the
baseline. The shared `retrieval.v1` DTO/facade, P1-09 adoption, and early
five-question smoke were not included in this closure and remain gated.

Filters use AND across categories and OR within a populated category. Bounds
are inclusive and languages compare case-insensitively. An omitted filter is
unrestricted. An explicitly supplied empty array or `null` is invalid; clients
must omit unrestricted categories. The same rule applies to
`normalized_types`, `journals`, `languages`, and `dois`.

The frozen development smoke IDs are `gq-sp-001`, `gq-cmp-001`,
`gq-conf-001`, `gq-gap-001`, and `gq-ins-001`. This smoke has not yet run and
remains a gated follow-up; any smoke output is diagnostic and must not be
presented as a release benchmark. The other 16 Golden v0 questions remain held
out from Phase B/C tuning for Phase D reporting and were not accessed during
Phase B implementation or acceptance.

### Phase C: Ranking, reranking, context, and citations

Ranking, reranker evaluation, and context-selection tooling must run in the same
native Windows Python environment. Any optional reranker needs a verified
Windows-compatible dependency or an explicit blocker and approval.

Scope P3-09 through P3-12: stable base ranking, duplicate suppression,
diversity, optional pluggable reranking, token-budgeted evidence selection, and
stable DOI/locator/chunk lookup. Reranking occurs after fusion/base deduplication
and before final diversity and context selection.

Required architecture includes a no-op reranker and a deterministic test fake.
An optional benchmark adapter may be local/open-source or explicitly
configured, but no paid reranker is required. Tests reject invented or duplicate
candidate IDs, nonfinite scores, and unstable ties. Phase C compares the same
candidate pool without and with each approved reranker using retrieval metrics,
latency, resources, and cost. Production enablement requires a separate measured
decision; disabled reranking remains a valid final configuration.

**Phase C feature approval (2026-11-19):** `specs/008-phase-c-quality/` is
approved for implementation with the user's refinements. Deduplication uses
exact `(DOI, primary source locator, text)` fields already returned by the
accepted Phase B core; configurable per-DOI cap defaults to 2 and `None`
disables it. Reranking remains disabled by default; quality/latency thresholds
are diagnostic screening only. Context budgeting requires an injected,
identity-matched tokenizer; lookup is exact and snapshot-scoped. Current
execution uses the repository-local `.venv\Scripts\python.exe` (Python 3.12.16)
and read-only database checks use only `SCISCOPE_TEST_DATABASE_URL`. The first
environment report was corrected. The actual five-question MiniLM benchmark
used real Phase B hybrid candidates and a pinned local checkpoint; it failed
the predeclared quality and latency diagnostic gates, so production reranking
remains disabled. The owner has independently reproduced this no-go result.
Phase C technical work and current verification results are in `EVIDENCE.md`;
the owner independently verified and explicitly closed Phase C on 2026-11-19.
The literal held-out isolation criterion remains NOT PASSED under the approved
historical exception: the initial preparation script deserialized the full
Golden JSON before selecting the five allowed IDs, although no held-out prompt
was output, embedded, retrieved, evaluated, or used for tuning. The checklist
records that exception separately from passed technical criteria. No Phase D
work has started. Downstream handoff drafts are proposed only and do not alter
retrieval.v1.

**Proposed downstream provider update (2026-11-19):** OpenAI is proposed to
replace Gemini for generation, pending Person 3/team review. This is recorded
for handoff only; it does not authorize live calls or change another owner's
backend.

### Phase D: Scientific retrieval evaluation

Evaluation and latency measurement must be reproducible on native Windows.
Record Windows and hardware context while preserving frozen partitions,
metrics, and matching methodology.

Scope P1-13, P3-13 through P3-15, and P8-01 through P8-04: versioned Golden
loading, evidence matching, held-out dense/lexical/hybrid comparisons,
Recall@K, Evidence Hit@K, applicable MRR, negative-question methodology,
latency, reproducibility, and mandatory Golden v1 creation/review/evaluation.
No reranker arm is required; preserve the Phase C MiniLM NO-GO. Runs record dataset/corpus
hashes, Git revision, database/pgvector/migration versions, delivery digest,
embedding configuration, retrieval configuration, command, environment, and
query-embedding usage/cost.

Golden v1 adds nine questions (3 insufficient-evidence, 0 genuine conflicts,
2 research-gap, 1 single-paper factual, 3 multi-paper comparisons), grounded in
the frozen pilot and tagged across all four product functionalities. Person 2's
approved Phase D methodology permits AI-generated/AI-assisted drafting with
transparent provenance, followed by a mandatory independent ChatGPT scientific
review of every record and a separate user continuation decision. This replaces
the earlier approximately nine independently human-authored requirement for
this Person 2 plan only. Rationale: the evaluation owner prefers AI-assisted,
source-grounded drafting over manually authoring all nine questions, with
review effort concentrated on direct inspection of source passages, evidence,
answerability, provenance, and functionality annotations. ChatGPT review is
not human verification. The previous rule and rationale for this scoped
replacement are retained in the Phase D decision history. The repository-wide constitution and shared
`docs/EVALUATION_PLAN.md` remain unchanged; until their governance is amended,
this v1 artifact is a Person 2 evaluation dataset and must not be represented as
a shared human-verified Golden release. Freeze partitions before retrieval
outputs/tuning and preserve v0 byte-for-byte.

Phase D reporting separates v0 development n=5, v1 development n=3, v0 held-out
n=16, and v1 held-out n=6. The eight development questions never contribute to
held-out estimates. Report the held-out cohorts separately; a pooled result over
at most 22 is optional descriptive reporting only when both cohorts are fully
eligible under identical frozen evaluation conditions. No 30-question
independent-test or strong per-functionality claim is permitted. T004 ChatGPT
review is the sole pre-evaluation exposure of v1 held-out text and must remain
isolated from retrieval development/results; v0 held-out content remains sealed
until explicit final-evaluation authorization. T005 vector preflight also
requires cohort-specific authorization before reading protected text/hashes.

For this Phase D feature, after explicit plan/implementation authorization,
Person 2/Codex autonomously performs routine implementation, debugging, tests,
static checks, read-only verification, fixes/reruns, and evidence reporting.
ChatGPT independently inspects code/results/evidence; the user retains final
acceptance without rerunning routine PowerShell commands. Record actual command
lines, environment/configuration identities, test counts, failures/skips, and
limitations. This feature-specific direction does not authorize a paid call,
database mutation, shared-contract change, held-out access, or commit/push.

### Phase E: Integration and final verification

Person 2 integration and final verification commands run on native Windows.
Other owners may use their own environments; shared interfaces and behavior
remain platform-neutral.

Integrate the approved `retrieval.v1` service with Person 3, preserve the fake
provider default, validate citations and insufficient-evidence behavior, cover
database/embedding/reranker failures, run end-to-end regressions, record
evidence, and produce the final team handoff. Person 3's proposed ownership of
the live OpenAI query-embedding adapter requires their explicit agreement. No
silent dense-to-lexical fallback or unrequested provider change is allowed.

## Definition of done and continuity

Each phase requires its own research, specification, plan, no-more-than-eight
tasks, consistency analysis, explicit feature approval, RED/GREEN implementation,
automatic checks, human verification, evidence, review, and synchronized task
state. Each phase ends with a repository handoff containing completed tasks,
changed files, observed checks, decisions, limitations, open issues, and next
dependencies. Work stops at the approved phase boundary.

