# SciScope Master Project Backlog

This is the central checklist. Feature-specific Spec Kit `tasks.md` files remain
the execution source for approved feature work and must stay synchronized with
these entries. A checkbox may be marked `[x]` only after automated and human
verification succeeds and the evidence is recorded in `EVIDENCE.md`.

Each row records a stable task ID, owner, deliverable, phase, and dependency when
relevant. Dependencies refer to task IDs. All tasks begin incomplete; no
completion evidence or human verification is asserted by this initial backlog.

Part 3 has drafted the README, design documents, dependency configuration,
pull request template, and CI workflow. `uv.lock` now exists on `main`, and
routine dependency commands use `--locked`. Earlier local setup errors are
recorded in `EVIDENCE.md`; the lockfile alone does not verify local sync or CI.
Human review and verification remain pending; no checkbox is completed by this draft.

## Phase 0 — Foundation (TEAM)

- [ ] **P0-01** | Owner: TEAM | Deliverable: repository setup and agreed repository conventions | Phase: 0
- [ ] **P0-02** | Owner: TEAM | Deliverable: documented Git workflow and branch/review expectations | Phase: 0 | Depends on: P0-01
- [ ] **P0-03** | Owner: TEAM | Deliverable: Windows development environment setup | Phase: 0 | Depends on: P0-01
- [ ] **P0-04** | Owner: TEAM | Deliverable: Python 3.12 and isolated `.venv` setup | Phase: 0 | Depends on: P0-03
- [ ] **P0-05** | Owner: TEAM | Deliverable: Node.js prerequisites and setup | Phase: 0 | Depends on: P0-03
- [ ] **P0-06** | Owner: TEAM | Deliverable: Docker prerequisites and setup | Phase: 0 | Depends on: P0-03
- [ ] **P0-07** | Owner: TEAM | Deliverable: official Spec Kit installation and repository integration | Phase: 0 | Depends on: P0-01
- [ ] **P0-08** | Owner: TEAM | Deliverable: constitution reviewed and ratified by the team | Phase: 0 | Depends on: P0-07
- [ ] **P0-09** | Owner: TEAM | Deliverable: `AGENTS.md` instructions reviewed and accepted | Phase: 0 | Depends on: P0-01
- [ ] **P0-10** | Owner: TEAM | Deliverable: Google Python engineering skill installed and verified | Phase: 0 | Depends on: P0-07
- [ ] **P0-11** | Owner: TEAM | Deliverable: solution-research skill installed and verified | Phase: 0 | Depends on: P0-07
- [ ] **P0-12** | Owner: TEAM | Deliverable: Ruff configuration and applicable checks | Phase: 0 | Depends on: P0-04
- [ ] **P0-13** | Owner: TEAM | Deliverable: pytest configuration and applicable checks | Phase: 0 | Depends on: P0-04
- [ ] **P0-14** | Owner: TEAM | Deliverable: mypy configuration and applicable checks | Phase: 0 | Depends on: P0-04
- [ ] **P0-15** | Owner: TEAM | Deliverable: secret-free `.env.example` and ignored local `.env` policy | Phase: 0 | Depends on: P0-01
- [ ] **P0-16** | Owner: TEAM | Deliverable: fake-provider default and explicit live-provider policy | Phase: 0
- [ ] **P0-17** | Owner: TEAM | Deliverable: GitHub Actions CI workflow | Phase: 0 | Depends on: P0-12, P0-13, P0-14
- [ ] **P0-18** | Owner: TEAM | Deliverable: project README with setup and development entry points | Phase: 0 | Depends on: P0-03, P0-07, P0-15
- [ ] **P0-19** | Owner: TEAM | Deliverable: team ownership and responsibility map | Phase: 0
- [ ] **P0-20** | Owner: TEAM | Deliverable: `docs/DEVELOPMENT_WORKFLOW.md` | Phase: 0 | Depends on: P0-07, P0-09
- [ ] **P0-21** | Owner: TEAM | Deliverable: `EVIDENCE.md` verification and evidence workflow | Phase: 0 | Depends on: P0-20
- [ ] **P0-22** | Owner: TEAM | Deliverable: Definition of Done agreed and recorded | Phase: 0 | Depends on: P0-20, P0-21

## Phase 1 — Shared Design (TEAM)

- [ ] **P1-01** | Owner: TEAM | Deliverable: honeybee corpus scope and inclusion criteria | Phase: 1
- [ ] **P1-02** | Owner: Person 1 | Deliverable: PLOS API and JATS format analysis | Phase: 1 | Depends on: P1-01
- [ ] **P1-03** | Owner: TEAM | Deliverable: Paper → Section → Chunk entity model | Phase: 1 | Depends on: P1-02
- [ ] **P1-04** | Owner: Person 1 | Deliverable: required scientific metadata contract | Phase: 1 | Depends on: P1-02, P1-03
- [ ] **P1-05** | Owner: TEAM | Deliverable: licensing and provenance requirements | Phase: 1 | Depends on: P1-01, P1-02
- [ ] **P1-06** | Owner: Person 1 | Deliverable: section normalization rules | Phase: 1 | Depends on: P1-02, P1-03
- [ ] **P1-07** | Owner: Person 1 | Deliverable: paragraph-aware and section-aware chunking design | Phase: 1 | Depends on: P1-03, P1-06
- [ ] **P1-08** | Owner: Person 1 | Deliverable: embedding model, prefix, and version configuration | Phase: 1 | Depends on: P1-07
- [ ] **P1-09** | Owner: Person 2 | Deliverable: combined metadata filter contract | Phase: 1 | Depends on: P1-04
- [ ] **P1-10** | Owner: Person 1 | Deliverable: versioned JSON data contract | Phase: 1 | Depends on: P1-03, P1-04, P1-06, P1-07
- [ ] **P1-11** | Owner: TEAM | Deliverable: versioned API contracts agreed by module owners | Phase: 1
- [ ] **P1-12** | Owner: Person 1 | Deliverable: golden dataset record and curation design | Phase: 1 | Depends on: P1-02, P1-10
- [ ] **P1-13** | Owner: Person 2 | Deliverable: retrieval evaluation metrics and protocol | Phase: 1 | Depends on: P1-12
- [ ] **P1-14** | Owner: TEAM | Deliverable: human approval of shared architecture and contracts | Phase: 1 | Depends on: P1-01 through P1-13

## Phase 2 — Data Processing (Person 1)

- [ ] **P2-01** | Owner: Person 1 | Deliverable: PLOS batch downloader | Phase: 2 | Depends on: P1-01, P1-02, P1-05
- [x] **P2-02** | Owner: Person 1 | Deliverable: downloader pagination, retry, and resume behavior | Phase: 2 | Depends on: P2-01
- [x] **P2-03** | Owner: Person 1 | Deliverable: DOI-based paper deduplication | Phase: 2 | Depends on: P2-01, P1-04
- [x] **P2-04** | Owner: Person 1 | Deliverable: preserved source XML and provenance association | Phase: 2 | Depends on: P2-01, P1-05
- [x] **P2-05** | Owner: Person 1 | Deliverable: license and provenance extraction | Phase: 2 | Depends on: P2-04, P1-05
- [x] **P2-06** | Owner: Person 1 | Deliverable: F002 JATS parser, digest gate, and parse report | Phase: 2 | Depends on: P1-02, P1-10
- [x] **P2-07** | Owner: Person 1 | Deliverable: F002 nested section and paragraph extraction | Phase: 2 | Depends on: P2-06, P1-06
- [x] **P2-08** | Owner: Person 1 | Deliverable: F002 abstract extraction | Phase: 2 | Depends on: P2-06
- [x] **P2-09** | Owner: Person 1 | Deliverable: F002 section classification and taxonomy review | Phase: 2 | Depends on: P2-07, P1-06
- [x] **P2-10** | Owner: Person 1 | Deliverable: F002 stable source text locators and read-only passage helper | Phase: 2 | Depends on: P2-07, P1-10
- [x] **P2-11** | Owner: Person 1 | Deliverable: paragraph-aware and section-aware chunker | Phase: 2 | Depends on: P2-07, P2-10, P1-07
- [ ] **P2-12** | Owner: Person 1 | Deliverable: table and table-caption handling | Phase: 2 | Depends on: P2-06, P2-11 | Note: F003 Option A only counts and omits this content; chunking of it is a named follow-up after Golden v0
- [ ] **P2-13** | Owner: Person 1 | Deliverable: figure-caption handling | Phase: 2 | Depends on: P2-06, P2-11 | Note: F003 Option A only counts and omits this content; chunking of it is a named follow-up after Golden v0
- [ ] **P2-14** | Owner: Person 1 | Deliverable: reference-section handling | Phase: 2 | Depends on: P2-06, P2-11 | Note: F003 Option A only counts and omits this content; chunking of it is a named follow-up after Golden v0
- [x] **P2-15** | Owner: Person 1 | Deliverable: chunk identifiers and processing version metadata | Phase: 2 | Depends on: P2-11, P1-10
- [x] **P2-16** | Owner: Person 1 | Deliverable: tokenizer-based chunk length limits | Phase: 2 | Depends on: P2-11, P1-08
- [x] **P2-17** | Owner: Person 1 | Deliverable: embedding provider and model configuration (F003 re-scoped: OpenAI `text-embedding-3-small` pilot; local `multilingual-e5-small` loading not implemented, D-004 open) | Phase: 2 | Depends on: P1-08
- [x] **P2-18** | Owner: Person 1 | Deliverable: embedding generation pipeline | Phase: 2 | Depends on: P2-15, P2-17
- [x] **P2-19** | Owner: Person 1 | Deliverable: embedding shape, value, and version validation | Phase: 2 | Depends on: P2-18
- [x] **P2-20** | Owner: Person 1 | Deliverable: data contract validation | Phase: 2 | Depends on: P2-06 through P2-19, P1-10
- [ ] **P2-21** | Owner: Person 1 | Deliverable: XML processing quality tests | Phase: 2 | Depends on: P2-06 through P2-14
- [ ] **P2-22** | Owner: Person 1 | Deliverable: curated honeybee golden questions and reference answers | Phase: 2 | Priority: High — first development cycle | Depends on: P1-12, P2-04, P2-06, P2-10 | Note: Golden v0 (21 AI-drafted, human-verified questions) is delivered in this PR; human-written questions remain open for a later version (Person 2). Human approval: reported by Person 1 in chat on 2026-11-18; this task remains unchecked.
- [ ] **P2-23** | Owner: Person 1 | Deliverable: manually verified evidence references for golden questions | Phase: 2 | Priority: High — first development cycle | Depends on: P2-22 | Note: Golden v0 (21 AI-drafted, human-verified questions) is delivered in this PR; human-written questions remain open for a later version (Person 2). Human approval: reported by Person 1 in chat on 2026-11-18; this task remains unchecked.
- [ ] **P2-24** | Owner: Person 1 | Deliverable: initial 20-paper PLOS pilot | Phase: 2 | Depends on: P2-01 through P2-20
- [ ] **P2-25** | Owner: Person 1 | Deliverable: corpus expansion toward approximately 500 relevant papers | Phase: 2 | Depends on: P2-24

F004 status (2026-11-18): DONE. Groups A–F GREEN; branch CI passed per Person 1,
who explicitly accepted SC-001..SC-008. T001–T007 and P2-20 are checked.
Person 2 PR review: NOT PERFORMED by team agreement (not a failure);
received extracted-package verification: NOT RUN. Docs-only close-out CI result:
NOT RECORDED; Person 1 waits for green before squash merge.
P2-24 remains unchecked; no corpus expansion or Golden work was started in F004.

Golden v0 small-change evidence (2026-11-18): dataset
`evals/golden_questions.v0.json` is supplied by Person 1 and preserved unchanged.
Edited files: `evals/golden_questions.schema.json`, `docs/EVALUATION_PLAN.md`,
`evals/README.md`, `PROJECT_TODO.md`, and `EVIDENCE.md`.
Dataset SHA-256:
`16a47954951c2c7ade6f9ef69dc232c8520d1debb042135cea5733b970180746`.
Recomputed corpus version: `pilot17-xml-1fff1573b610`; full manifest-derived hash:
`1fff1573b610c27e2e8016343d2f6429df294db974db4af898c4a0f82ffc26bd`.
JSON loading, Draft 2020-12 schema/dataset validation, metadata/hash/LF checks,
three existing schema tests, touched-document Ruff formatting, and
`git diff --check` passed using local tools. The external `golden_check.py`,
full locked pytest/Ruff/mypy checks, source review, and `check-quote` reruns were
NOT RUN by the assistant. See the [evidence entry](EVIDENCE.md#golden-v0-small-change--documentation-data-and-optional-question-type)
for commands and verification limits. No checkbox changes or evaluation results.

## Phase 3 — Database & Retrieval (Person 2)

- [ ] **P3-01** | Owner: Person 2 | Deliverable: PostgreSQL and pgvector local setup | Phase: 3 | Depends on: P1-03, P1-10
- [ ] **P3-02** | Owner: Person 2 | Deliverable: relational paper, section, and chunk data model | Phase: 3 | Depends on: P3-01, P1-03, P1-10
- [ ] **P3-03** | Owner: Person 2 | Deliverable: validated data import pipeline | Phase: 3 | Depends on: P2-20, P3-02
- [ ] **P3-04** | Owner: Person 2 | Deliverable: idempotent indexing behavior | Phase: 3 | Depends on: P3-03
- [ ] **P3-05** | Owner: Person 2 | Deliverable: vector similarity search | Phase: 3 | Depends on: P3-01, P3-02, P2-18
- [ ] **P3-06** | Owner: Person 2 | Deliverable: PostgreSQL full-text search | Phase: 3 | Depends on: P3-01, P3-02
- [ ] **P3-07** | Owner: Person 2 | Deliverable: combined metadata filtering | Phase: 3 | Depends on: P3-02, P1-09
- [ ] **P3-08** | Owner: Person 2 | Deliverable: hybrid vector and lexical retrieval | Phase: 3 | Depends on: P3-05, P3-06
- [ ] **P3-09** | Owner: Person 2 | Deliverable: ranking and duplicate-result policy | Phase: 3 | Depends on: P3-08
- [ ] **P3-10** | Owner: Person 2 | Deliverable: optional reranking benchmark | Phase: 3 | Depends on: P3-09
- [ ] **P3-11** | Owner: Person 2 | Deliverable: retrieval context and token budgets | Phase: 3 | Depends on: P3-09
- [ ] **P3-12** | Owner: Person 2 | Deliverable: lookup by stable source identifiers and locators | Phase: 3 | Depends on: P3-02, P2-10
- [ ] **P3-13** | Owner: Person 2 | Deliverable: golden dataset loading and retrieval evaluation integration | Phase: 3 | Depends on: P2-23, P3-08
- [ ] **P3-14** | Owner: Person 2 | Deliverable: Recall@K, Evidence Hit@K, and applicable MRR reporting | Phase: 3 | Depends on: P3-13, P1-13
- [ ] **P3-15** | Owner: Person 2 | Deliverable: retrieval latency benchmark | Phase: 3 | Depends on: P3-08, P3-09

## Phase 4 — Backend & AI (Person 3)

- [ ] **P4-01** | Owner: Person 3 | Deliverable: FastAPI application skeleton | Phase: 4 | Depends on: P1-11
- [ ] **P4-02** | Owner: Person 3 | Deliverable: API request and response contracts | Phase: 4 | Depends on: P1-11, P4-01
- [ ] **P4-03** | Owner: Person 3 | Deliverable: approved Spec Kit specification, plan, tasks, and acceptance criteria for Fake AI Provider and Backend Integration | Phase: 4 | Priority: High — first development cycle
- [ ] **P4-04** | Owner: Person 3 | Deliverable: offline deterministic fake provider implementing the agreed interface | Phase: 4 | Priority: High — first development cycle | Depends on: P4-03, P4-02
- [ ] **P4-05** | Owner: Person 3 | Deliverable: fake provider success, error, timeout, and invalid-output scenarios | Phase: 4 | Priority: High — first development cycle | Depends on: P4-04
- [ ] **P4-06** | Owner: Person 3 | Deliverable: fake provider backend integration tests with no API key or live calls | Phase: 4 | Priority: High — first development cycle | Depends on: P4-05
- [ ] **P4-07** | Owner: Person 3 | Deliverable: deterministic fake responses marked as mock/test data and restricted to fixture source IDs | Phase: 4 | Priority: High — first development cycle | Depends on: P4-04, P4-05
- [ ] **P4-08** | Owner: Person 3 | Deliverable: backend integration tests | Phase: 4 | Depends on: P4-02, P4-06
- [ ] **P4-09** | Owner: Person 3 | Deliverable: shared retrieval service integration | Phase: 4 | Depends on: P3-08, P4-02
- [ ] **P4-10** | Owner: Person 3 | Deliverable: explicitly configured Gemini provider | Phase: 4 | Depends on: P4-04, P4-09
- [ ] **P4-11** | Owner: Person 3 | Deliverable: provider abstraction suitable for a future OpenAI integration | Phase: 4 | Depends on: P4-04
- [ ] **P4-12** | Owner: Person 3 | Deliverable: query understanding behavior | Phase: 4 | Depends on: P4-09, P4-10
- [ ] **P4-13** | Owner: Person 3 | Deliverable: structured AI response validation | Phase: 4 | Depends on: P4-02, P4-10
- [ ] **P4-14** | Owner: Person 3 | Deliverable: citation identifier and source validation | Phase: 4 | Depends on: P3-12, P4-13
- [ ] **P4-15** | Owner: Person 3 | Deliverable: insufficient-evidence response behavior | Phase: 4 | Depends on: P3-13, P4-13, P4-14
- [ ] **P4-16** | Owner: Person 3 | Deliverable: timeout and retry policies | Phase: 4 | Depends on: P4-10
- [ ] **P4-17** | Owner: Person 3 | Deliverable: request input validation | Phase: 4 | Depends on: P4-02
- [ ] **P4-18** | Owner: Person 3 | Deliverable: API rate limiting | Phase: 4 | Depends on: P4-01
- [ ] **P4-19** | Owner: Person 3 | Deliverable: token usage recording | Phase: 4 | Depends on: P4-10, P4-13
- [ ] **P4-20** | Owner: Person 3 | Deliverable: explicit provider and retrieval failure handling | Phase: 4 | Depends on: P4-09, P4-10, P4-16
- [ ] **P4-21** | Owner: Person 3 | Deliverable: approved feature acceptance criteria covered by RED/GREEN behavior tests and recorded verification | Phase: 4 | Priority: High — first development cycle | Depends on: P4-03 through P4-07

Feature 011 — Fake-only Backend Question API — T001–T008 was accepted at
feature level by Mateja Miletic (Person 3, Backend & AI) on 2026-11-22 within
the approved fake-only, deterministic, offline scope. See
[`EVIDENCE.md`](EVIDENCE.md#feature-011--fake-only-backend-question-api) and
[`specs/011-fake-backend-api/tasks.md`](specs/011-fake-backend-api/tasks.md).
The Phase 4 backlog items above remain unchecked because their deliverables
include broader work or dependencies outside Feature 011, including real
provider/retrieval integration, scientific validation, and production behavior.

Feature 007 — Public Retrieval Facade — T007-A through T007-F was accepted at
feature level by the project owner on 2026-11-22. It delivers the public,
driver-independent retrieval facade and guarded integration verification; it
does not complete P1-09, P1-11, P1-14, P4-09, P4-10, or any other backlog item.
Person 2 review and native Windows guarded-test PASS are owner-reported; Windows
terminal evidence was not retained. See
[`EVIDENCE.md`](EVIDENCE.md#feature-007--public-retrieval-facade-t007) and
[`specs/007-phase-b-retrieval-core/tasks.md`](specs/007-phase-b-retrieval-core/tasks.md).

Feature 012 / P4-09 planning package is APPROVED for T012-B offline work by
Person 3 on 2026-11-22, on branch
`feature/p4-09-backend-retrieval-integration` at baseline
`7a8233bd029ba666274d8ecd902a84bfe6cf8fe6`. The P4-09 checkbox above remains
unchecked. The accepted fake-only `/api/v1/questions` contract remains exact;
the proposed real-retrieval wire contract is separately versioned as draft
`/api/v2/questions` and needs explicit approval. D012-01 records v1 dense as
the leading candidate, not a final application selection; D012-02 through
D012-05 record adopted design directions with compatibility, implementation, or
conditional provenance gates. The Person 2/Person 4 technical delegation is
owner-reported, not implementation or test approval. Concrete v2 HTTP work,
affected-owner reviews, database authorization, mode activation, and feature
acceptance remain gated. No application code, tests, database operations, or
provider calls are part of this planning record. See
[`specs/012-shared-retrieval-integration/tasks.md`](specs/012-shared-retrieval-integration/tasks.md)
and [`docs/person3/P4_09_TEST_LOG.md`](docs/person3/P4_09_TEST_LOG.md).

## Phase 5 — Frontend (Person 4)

- [ ] **P5-01** | Owner: Person 4 | Deliverable: React and TypeScript application setup | Phase: 5 | Depends on: P0-05
- [ ] **P5-02** | Owner: Person 4 | Deliverable: shared research interface layout | Phase: 5 | Depends on: P5-01
- [ ] **P5-03** | Owner: Person 4 | Deliverable: research question input | Phase: 5 | Depends on: P5-02, P1-11
- [ ] **P5-04** | Owner: Person 4 | Deliverable: explicit metadata filter controls | Phase: 5 | Depends on: P5-03, P1-09
- [ ] **P5-05** | Owner: Person 4 | Deliverable: frontend integration against agreed fake API responses | Phase: 5 | Depends on: P4-02, P4-04, P4-07
- [ ] **P5-06** | Owner: Person 4 | Deliverable: loading, error, and empty states | Phase: 5 | Depends on: P5-05
- [ ] **P5-07** | Owner: Person 4 | Deliverable: research paper result presentation | Phase: 5 | Depends on: P5-05
- [ ] **P5-08** | Owner: Person 4 | Deliverable: citations and DOI links | Phase: 5 | Depends on: P5-07, P4-14
- [ ] **P5-09** | Owner: Person 4 | Deliverable: research evidence comparison interface | Phase: 5 | Depends on: P5-07
- [ ] **P5-10** | Owner: Person 4 | Deliverable: conflicting evidence interface | Phase: 5 | Depends on: P5-07
- [ ] **P5-11** | Owner: Person 4 | Deliverable: research gap interface | Phase: 5 | Depends on: P5-07
- [ ] **P5-12** | Owner: Person 4 | Deliverable: saved research behavior, subject to explicit approval | Phase: 5 | Depends on: P5-02
- [ ] **P5-13** | Owner: Person 4 | Deliverable: accessibility review and fixes | Phase: 5 | Depends on: P5-02 through P5-11
- [ ] **P5-14** | Owner: Person 4 | Deliverable: frontend end-to-end tests | Phase: 5 | Depends on: P4-02, P5-05 through P5-11

## Phase 6 — First Complete MVP (TEAM)

- [ ] **P6-01** | Owner: TEAM | Deliverable: integrated PLOS XML → parser → chunks → embeddings → PostgreSQL → retrieval → FastAPI → Gemini → React flow | Phase: 6 | Depends on: P2-24, P3-08, P4-10, P5-08
- [ ] **P6-02** | Owner: TEAM | Deliverable: end-to-end Research Question Explorer as the first functional workflow | Phase: 6 | Depends on: P6-01
- [ ] **P6-03** | Owner: TEAM | Deliverable: Research Question Explorer validation against real source documents | Phase: 6 | Depends on: P6-02, P2-24, P2-23

## Phase 7 — Advanced Features (TEAM)

- [ ] **P7-01** | Owner: TEAM | Deliverable: Evidence Comparison feature specification, plan, owner tasks, and shared-RAG integration design | Phase: 7 | Depends on: P6-02
- [ ] **P7-02** | Owner: TEAM | Deliverable: Evidence Comparison implementation across assigned owners | Phase: 7 | Depends on: P7-01
- [ ] **P7-03** | Owner: TEAM | Deliverable: Conflicting Evidence Finder feature specification, plan, owner tasks, and shared-RAG integration design | Phase: 7 | Depends on: P6-02
- [ ] **P7-04** | Owner: TEAM | Deliverable: Conflicting Evidence Finder implementation across assigned owners | Phase: 7 | Depends on: P7-03
- [ ] **P7-05** | Owner: TEAM | Deliverable: Research Gap & Hypothesis Assistant feature specification, plan, owner tasks, and shared-RAG integration design | Phase: 7 | Depends on: P6-02
- [ ] **P7-06** | Owner: TEAM | Deliverable: Research Gap & Hypothesis Assistant implementation across assigned owners | Phase: 7 | Depends on: P7-05
- [ ] **P7-07** | Owner: TEAM | Deliverable: verification that all four research workflows use one shared RAG infrastructure | Phase: 7 | Depends on: P6-02, P7-02, P7-04, P7-06

## Phase 8 — Evaluation and Reliability (TEAM)

- [ ] **P8-01** | Owner: Person 2 | Deliverable: repeatable retrieval benchmark using the verified golden dataset | Phase: 8 | Depends on: P2-23, P3-13
- [ ] **P8-02** | Owner: Person 2 | Deliverable: semantic versus lexical versus hybrid comparison | Phase: 8 | Depends on: P8-01
- [ ] **P8-03** | Owner: Person 2 | Deliverable: Evidence Hit@K evaluation | Phase: 8 | Depends on: P8-01
- [ ] **P8-04** | Owner: Person 2 | Deliverable: Recall@K evaluation | Phase: 8 | Depends on: P8-01
- [ ] **P8-05** | Owner: Person 3 | Deliverable: citation identifier and DOI validity evaluation | Phase: 8 | Depends on: P4-14, P8-01
- [ ] **P8-06** | Owner: Person 3 | Deliverable: citation support verification against source passages | Phase: 8 | Depends on: P2-23, P8-05
- [ ] **P8-07** | Owner: Person 3 | Deliverable: insufficient-evidence behavior tests | Phase: 8 | Depends on: P4-15, P8-01
- [ ] **P8-08** | Owner: TEAM | Deliverable: scientific evidence comparison quality evaluation | Phase: 8 | Depends on: P7-02, P8-01
- [ ] **P8-09** | Owner: Person 3 | Deliverable: token usage evaluation | Phase: 8 | Depends on: P4-19
- [ ] **P8-10** | Owner: TEAM | Deliverable: response latency evaluation | Phase: 8 | Depends on: P3-15, P6-02
- [ ] **P8-11** | Owner: TEAM | Deliverable: provider, database, and API error scenario evaluation | Phase: 8 | Depends on: P4-16, P4-20
- [ ] **P8-12** | Owner: TEAM | Deliverable: security checks | Phase: 8 | Depends on: P6-02
- [ ] **P8-13** | Owner: TEAM | Deliverable: regression suite for approved application behavior | Phase: 8 | Depends on: P6-02, P7-07

## Phase 9 — Delivery (TEAM)

- [ ] **P9-01** | Owner: TEAM | Deliverable: clean installation verification from documented prerequisites | Phase: 9 | Depends on: P0-03, P0-04, P0-05, P0-18
- [ ] **P9-02** | Owner: TEAM | Deliverable: complete README covering installation, use, and development | Phase: 9 | Depends on: P9-01, P6-02
- [ ] **P9-03** | Owner: TEAM | Deliverable: Docker startup verification | Phase: 9 | Depends on: P0-06, P6-02
- [ ] **P9-04** | Owner: TEAM | Deliverable: final evaluation report with dataset and corpus versions | Phase: 9 | Depends on: P8-01 through P8-13
- [ ] **P9-05** | Owner: TEAM | Deliverable: evidence ledger audit | Phase: 9 | Depends on: P9-04
- [ ] **P9-06** | Owner: TEAM | Deliverable: verified demo scenarios | Phase: 9 | Depends on: P6-02, P7-07, P9-04
- [ ] **P9-07** | Owner: TEAM | Deliverable: project presentation | Phase: 9 | Depends on: P9-06
- [ ] **P9-08** | Owner: TEAM | Deliverable: final human acceptance | Phase: 9 | Depends on: P9-01 through P9-07
