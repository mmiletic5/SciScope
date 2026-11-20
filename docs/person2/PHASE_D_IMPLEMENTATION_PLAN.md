# Phase D Retrieval Evaluation - Planning Index

**Status:** T004 review and requested local verification completed on 2026-11-20; T005+ remain unauthorized.  
**Updated:** 2026-11-20  
**Scope:** Complete Person 2 Phase D, including Golden v1 curation, protected independent review, evaluation, reports, and handoffs.

Canonical Spec Kit package:

- [Feature specification](../../specs/009-phase-d-retrieval-evaluation/spec.md)
- [Research](../../specs/009-phase-d-retrieval-evaluation/research.md)
- [Implementation plan](../../specs/009-phase-d-retrieval-evaluation/plan.md)
- [Tasks, owners, files, gates, and estimates](../../specs/009-phase-d-retrieval-evaluation/tasks.md)
- [Acceptance checklist](../../specs/009-phase-d-retrieval-evaluation/checklists/acceptance.md)

## Decisions and governance boundary

**Approved Person 2 decisions (amended):** nine-question target (3 insufficient-evidence, 0 genuine conflicting-evidence, 2 research gaps, 1 single-paper factual, 3 multi-paper comparisons). Q4/Q5 are comparison questions and Conflicting Evidence Finder negative controls. The frozen corpus provides no defensible pair of genuinely contradictory comparable findings; Golden v1 does not measure genuine-conflict sensitivity. All four functions retain descriptive annotation coverage. AI-assisted drafting has transparent provenance and a separately versioned sidecar.

**Mandatory review gate:** after generating/annotating all nine candidates and mechanically validating them, prepare a protected packet with each question, original relevant passages, DOI/section/chunk locators, expected findings, answerability, labels/rationales, provenance, functionality annotations, validation results, and hashes. Stop. ChatGPT in a fresh review context must manually inspect every record and explicitly approve it. ChatGPT review is not human verification. Defects are corrected and resubmitted. After ChatGPT approves all nine, wait for the user's explicit continuation authorization before any subsequent implementation/evaluation.

The prior approximately 30% human-written/independently human-authored rule is preserved in decision history and replaced within the Person 2-owned master plan and retrieval protocol by the user's explicit decision. The repository-wide constitution and shared `docs/EVALUATION_PLAN.md` remain unchanged. Consequently this v1 is a Person 2 evaluation dataset with recorded ChatGPT review, not a shared human-verified release. This boundary is documented for handoff; it does not block internal Person 2 work. No Person 1, Person 3, mentor, or project-owner approval is required for Person 2 implementation, curation, validation, or sidecar.

## Execution gates and critical path

After approval of the complete plan and separate implementation authorization, T002 synthetic evaluator implementation/tests must finish before T003 question generation. At T003 completion, all work stops for T004 ChatGPT review. Once the review passes and the user authorizes continuation: freeze config/partitions and obtain preflight-only cohort authorization before protected text/hash access → T005 read-only DB/query-vector preflight → obtain second held-out retrieval authorization → T006 read-only evaluation → T007 reports and handoffs → T008 autonomous regression/evidence, ChatGPT review, and user final acceptance.

Preregister v1 partitions before generating content: Q1/Q4/Q6 development; Q2/Q3/Q5/Q7/Q8/Q9 held-out. The held-out content is protected from retrieval development, debugging, tuning, and ordinary logs/fixtures. Golden v0 remains unchanged (5 development smoke, 16 held out). Preserve accepted dense/lexical/hybrid RRF (`text-embedding-3-small`, 1536 dimensions, RRF k=60); MiniLM remains disabled.

The four reporting populations are v0 development n=5, v1 development n=3,
v0 held-out n=16, and v1 held-out n=6. Never include the eight development
questions in held-out results. Report the two held-out cohorts separately;
optionally add a descriptive pooled eligible n at most 22 only under identical
frozen corpus/configuration/metric conditions. No pooled or per-function
statistical-strength claim follows from the sample size. Positive metrics use
answerable questions with valid nonempty gold references; Recall uses unique
evidence units per question, while insufficient questions have null positive
Recall/MRR and separate negative reporting. Invalid gold blocks the cohort.

The inspected code contains a passage-input cache, not a query-cache subsystem;
no query cache was assumed, and no cache contents were inspected. Passage cache
entries alone do not bind question ID, dataset/partition/corpus, query role,
provider, or prefix. Missing/unverifiable vectors stop the affected dense and
hybrid cohort arms without dropping questions; lexical may run on the full
authorized cohort but is not compared to incomplete arms. Protected question
and vector preflight requires a first, cohort-specific authorization
before text or text hashes are read; final retrieval requires a second distinct held-out evaluation authorization after preflight readiness. Any paid generation request must enumerate
cache misses, deterministic input/token batches and request/retry counts, current
official price and estimated cost, and your hard cap; it requires separate
authorization.

Real evaluation requires separate explicit held-out authorization, verified vectors/provenance, read-only identity exactly `sciscope_test_005`, frozen pilot counts 17/319/728/728 and corpus `pilot17-xml-1fff1573b610`. Production `sciscope` stays protected. Missing/unverifiable vectors fail closed; protected vector preflight and held-out retrieval use separate authorizations; paid generation requires separate approval and a hard cap. No DB changes or shared contract changes are included.

The checklist inventory is **49 unique stable criteria (AC-001 through AC-049)**, recount verified from the checklist. Tasks T001 through T008 map to criteria, evidence artifacts, and required tests in the task traceability table. Routine implementation, debugging, testing, static checks, reproducibility checks, and read-only verification are Codex-run autonomously after authorization; the user reviews milestones and final evidence without repeating routine commands.

**T004 scientific review and verification:** Independent ChatGPT approved Q1–Q9. Q4/Q5 are Conflicting Evidence Finder negative controls, not genuine conflicts; the data does not measure genuine-conflict sensitivity. The review is model-based, not human verification. It used frozen-derived evidence passages; original raw XML was unavailable and the reviewer did not independently re-search all 17 papers. Local Windows verification passed 150 offline evaluation/retrieval tests, 13 PostgreSQL read-only retrieval integration tests, Ruff, formatting, mypy, package tests, protected-data checks, and frozen delivery hashes. Full details and package hashes are in `docs/person2/PHASE_D_T004_REVIEW_AND_VERIFICATION.md`. No Golden records or frozen settings were rewritten. T005+ remain stopped until explicit user continuation authorization.

## Effort and deadline

Routine local implementation and verification are executed autonomously after authorization; the user performs milestone review and final acceptance, not command reruns.

Estimated Person 2 effort: T001 2–4 h; T002 12–16 h; T003 12–20 h; T004 6–10 h plus any corrections/re-review; T005 3–5 h if a compatible cache exists; T006 5–8 h after its separate retrieval authorization; T007 5–8 h; T008 3–5 h. Total **48–76 focused hours**, excluding vector generation cost/wait, substantial defects, and environment debugging. This critical path does not support claiming scientifically complete Phase D by November 20, 2026 at 12:00 CET. No gate or review is shortened to fit the deadline.

The user approved implementation through T004 and replaced ACL isolation with procedural isolation. T001–T003 artifacts are complete; T004 scientific review and requested verification passed with limitations recorded in the T004 evidence report. Protected storage is Git-ignored and workflow-checked, not OS-enforced; same-identity processes can read it. Execution is now stopped pending explicit user continuation authorization. No query-vector preflight or held-out retrieval evaluation has begun.
