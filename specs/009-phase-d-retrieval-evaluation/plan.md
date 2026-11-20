# Implementation Plan: Phase D Scientific Retrieval Evaluation

**Branch**: `009-phase-d-retrieval-evaluation`  
**Date**: 2026-11-19  
**Spec**: [spec.md](spec.md)  
**Status**: T004 review and requested local verification completed on 2026-11-20; T005+ await explicit user continuation authorization

## Summary

Build and test a repository-native evaluation harness; create and validate mandatory Golden v1; stop for independent ChatGPT scientific review of a protected packet; after ChatGPT approval and the user's explicit continuation authorization, freeze and evaluate v1 in a reproducible read-only dense/lexical/hybrid comparison. Preserve v0 and all accepted Phase A/B/C behavior. No reranker experiments, schema/pilot changes, paid calls by default, or shared-contract changes.

## Technical Context

**Language/Version**: Python 3.12, Windows PowerShell  
**Primary Dependencies**: Existing dependencies and accepted Person 2 retrieval core; no new evaluation dependency proposed  
**Storage**: PostgreSQL 17 / pgvector 0.8.7; read-only evaluation only  
**Testing**: pytest synthetic unit tests, then read-only real-database integration checks  
**Target Platform**: Native Windows 10 x64; no Docker, WSL, Linux, or Bash requirement  
**Project Type**: Python library/CLI and evaluation artifacts  
**Performance Goals**: Report observed stage latency; no invented latency gate  
**Constraints**: implementation was authorized through T004; procedural Git-ignored storage is used without ACL changes; ChatGPT approved all nine v1 records; T004 verification is documented; all subsequent implementation/evaluation remains blocked until explicit user continuation; held-out evaluation has separate authorization; paid embedding calls require separate authorization and cap; pilot immutable  
**Scale/Scope**: Golden v0 remains 21 questions (5 development, 16 held-out); the separate Golden v1 addendum contains 9 new questions (3 development, 6 held-out). Thus 8 are development-only and 22 form two distinct held-out cohorts. The historical catalog totals 30 records, but is never one independent test set.

## Constitution Check

- Feature-plan approval and separate explicit user implementation authorization were granted through T004 review and verification. This does not authorize T005+, query-vector preflight, paid calls, or held-out evaluation.
- Research before specification: recorded in `research.md`.
- Test-first and independent oracles: required in T002 and subsequent tasks.
- Provenance, reproducibility, and limitations: addressed by curation manifest, hashes, reports, and non-claims.
- Shared contracts: no shared contract changes; use private accepted retrieval core.
- Security and privacy: native Windows, no secrets in artifacts, no paid API by default, only test DB and read-only evaluation.
- Golden v1 quality gate is independent ChatGPT source-based review, accurately recorded as model review and never as human verification; the user's explicit continuation authorization follows that review. User's final independent implementation verification/acceptance remains a separate closure gate.

## Repository-grounded v1 requirements and unresolved specifics

Repository history required approximately nine independently human-authored/verified questions and recorded an approximately 30% human-written target. The user, sole Person 2 decision maker, approved replacing the authorship method in Person 2-owned planning/governing documents with AI-generated/AI-assisted candidates and mandatory independent ChatGPT scientific review. `docs/person2/MASTER_PLAN.md` and `docs/person2/RETRIEVAL_EVALUATION_PROTOCOL.md` are updated for Person 2 scope. The repository constitution and shared `docs/EVALUATION_PLAN.md` remain unchanged because they govern broader project policy; therefore the P2 v1 artifact must be represented accurately as a P2 evaluation dataset with ChatGPT review, not as a shared human-verified release. Person 1/Person 3/mentor/project-owner approvals are not gates for P2 internal work; handoffs record integration implications. The user-approved matrix and exact 3-development/6-held-out slot assignment below are preregistered before generation.

### User-approved category matrix and functionality coverage

| Slot | Primary category | Functionality tags |
| --- | --- | --- |
| Q1 | Insufficient evidence | Research Question Explorer |
| Q2 | Insufficient evidence | Evidence Comparison |
| Q3 | Insufficient evidence | Research Gap & Hypothesis Assistant |
| Q4 | Cross-paper conflict | Evidence Comparison; Conflicting Evidence Finder; Research Question Explorer |
| Q5 | Cross-paper conflict | Evidence Comparison; Conflicting Evidence Finder |
| Q6 | Research gap | Research Gap & Hypothesis Assistant; Research Question Explorer |
| Q7 | Research gap | Research Gap & Hypothesis Assistant |
| Q8 | Single-paper factual | Research Question Explorer |
| Q9 | Multi-paper comparison | Evidence Comparison |

The owner-approved amended totals are 3 insufficient-evidence, 0 genuine conflicting-evidence, 2 research-gap, 1 single-paper factual, and 3 multi-paper comparison. Q4/Q5 are comparison cases that retain Conflicting Evidence Finder annotations strictly as false-conflict negative controls. The frozen 17-paper corpus contains no defensible pair of genuinely contradictory comparable findings; Golden v1 cannot support genuine-conflict detection sensitivity claims. IDs above are preregistered slots, not generated question IDs.

The owner approved the amendment after source review found no defensible genuine conflict examples. This does not weaken scientific validity: Q4/Q5 test rejection of apparent/non-equivalent conflicts only. The old approximately 30%/independently human-authored requirement remains in decision history; AI-assisted creation and explicit model-review provenance apply to Person 2 artifacts.

Other curation details remain gates: answerability rubric, exact source-paper coverage/selection, and deterministic 3-dev/6-held-out assignment must be finalized before generation; partition design and leakage rules are pre-registered first, and actual IDs/hashes freeze after review before any retrieval outputs/tuning. Every item must cite the actual pilot corpus. Preserve v0 byte-for-byte.

## Golden v1 curation and freeze workflow

1. **Pre-register** counts/category/coverage matrix, answerability rubric, partition sizes and assignment procedure, metric/matcher versions, baseline configuration, ID rules, and leakage controls before generating questions.
2. **Select sources** from the frozen 17-paper corpus to satisfy coverage and categories; record source DOI and why selected. Source reading is allowed for curation; evaluation output is not.
3. **Generate/refine nine candidates** with Codex/ChatGPT using actual pilot scientific literature. Record tool/model/version when known, date, source inputs, prompts/draft lineage and AI contribution; unknowns remain unknown. Do not label AI-generated questions human-authored. Never use evaluated-system outputs. No retrieval outputs or scores may be used in curation.
4. **Annotate** expected findings/answer, question type, answerability, relevant DOI(s), sections, durable source locator(s), verbatim quotation(s) where used, relevance labels 0–3 and rationale. For insufficient-evidence cases, document corpus scope and inspected/search evidence supporting the insufficiency judgment.
5. **Machine-validate** schema, fields, version, corpus membership, unique IDs, locator presence, type/function counts, DOI syntax, quotation exactness against source XML, and hashes. These checks do not establish scientific validity.
6. **Prepare protected review packet and STOP** immediately after all nine candidates and annotations are ready for review. Packet contains every candidate, functionality sidecar, exact original source passages with DOI/section/chunk/locator, expected findings, answerability, relevance labels/rationales, full AI provenance, validator outputs, version/hash manifest. Store in an access-restricted location excluded from version control, ordinary retrieval fixtures, logs, development data, and tuning paths; grant access only to the user and the review context. If such isolation cannot be established, do not generate/store question content. No subsequent implementation or evaluation work proceeds through this gate.
7. **Independent ChatGPT review** occurs in a fresh review context, which receives the packet and review rubric but no question-generation rationale or retrieval outputs. ChatGPT manually inspects each of the nine records against the original passages and checks scientific correctness, answerability, evidence links, expected finding, provenance, and functionality annotations. Record per-record decisions, findings, and limitations; call this model review, never human verification. Rejected records are corrected only as authorized after the review report, then affected records are resubmitted for fresh review. The gate passes only when ChatGPT explicitly approves all nine.
8. **User continuation gate**: after ChatGPT approval, stop and wait for the user's explicit authorization to continue. Neither plan approval nor ChatGPT approval alone authorizes continuation. Person 1/Person 3/mentor/project-owner approval is not required for P2 internal work.
9. **Freeze and protect partitions** after the gate: final IDs, text, dataset/corpus hashes, sidecar and partition ID/hash lists freeze before any retrieval output is observed. Any post-freeze ground-truth correction creates a new version and invalidates prior held-out results as confirmatory evidence; obtain a fresh holdout. Golden v0 stays byte-identical.

## Golden dataset roles

- **Development population (n=8)**: the five previously exposed v0 development/smoke questions plus three v1 development questions. Use only for development, smoke, debugging, and diagnostics. Never include these eight in held-out estimates or the optional pooled held-out summary.
- **v0 protected cohort (n=16)**: preserve as a distinct previously protected evaluation cohort. Do not expose content to retrieval development, debugging, tuning, threshold selection, prompt optimization, or model selection. Evaluate only after frozen configuration/partitions and explicit authorization. Validate provenance/readiness and contamination before making an independent-cohort claim; preserve the documented Phase C full-file deserialization exception without treating it as blanket access authorization.
- **v1 protected cohort (n=6)**: six new questions from the 9-question v1 addendum, assigned to held-out before drafting. The only pre-evaluation exposure is the user-mandated, access-restricted T004 scientific-review packet; reviewer sees no retrieval output or code/config tuning context. Review feedback is limited to source-grounded record corrections, not retrieval behavior. The T004 packet is not development input and does not authorize retrieval evaluation. After T004, no implementation resumes until ChatGPT approval and the user's continuation authorization.
- **v1 development population (n=3)**: Q1/Q4/Q6, development-only after creation and validation; never held-out estimates.
- **Primary reporting**: report v0-HO (n=16) and v1-HO (n=6) separately, with dataset/corpus/partition hashes, eligibility counts, provenance, and limitations. Optionally report a clearly labeled descriptive pooled held-out macro over eligible questions (maximum total n=22) only if both cohorts are fully validated and use the same frozen corpus, retrieval configuration, matcher, metrics, and cutoffs. It is not automatically more representative or statistically independent. Do not pool evidence units across questions; do not include the eight development questions; do not describe all 30 catalog records as one independent test set.
- **Contamination rule**: if an item in either protected cohort is found previously used for retrieval tuning, threshold selection, debugging, prompt optimization, or iterative model selection, record the exposure and exclude it from independent held-out claims without replacement or score-based reassignment. A contaminated item may be shown only as an explicitly exposed diagnostic. Report eligible n and exclusion reasons; if contamination makes the cohort unusable, say so and do not claim an independent cohort result.
- The nine v1 records are intended to broaden scenario coverage, not to establish statistically robust performance for each functionality. Report per-question outcomes and functionality-stratified descriptive summaries with n; avoid significance or strong comparative claims. Preserve v0 byte-for-byte. Under the unchanged shared schema/policy, v1 remains a P2 evaluation-only dataset with `verification_status: "in_review"` and a truthful AI reviewer label such as `ChatGPT (AI model review; not human verification)`; omit `verified_date`. A private P2 loader may accept it only when the versioned sidecar/manifest records ChatGPT approval and user continuation. Do not describe it as a shared human-verified release.

## Proposed functionality annotation sidecar

Keep the frozen `evals/protected/golden_v1_review/golden_questions.v1.json` under the protected, Git-ignored path and ground it in the existing question schema and truthful current status fields; ChatGPT approval must not be encoded as human verification. Add a separately versioned internal sidecar keyed by `question_id`; do not alter shared schema or imply shared adoption. Any shared-contract proposal is documented in Person 3 handoff only.

Common sidecar fields: sidecar schema/version; `question_id`; primary functionality and `functionality_coverage[]`; answerability/expected disposition; expected atomic findings; `claim_id` to evidence-reference links; evidence role (`supports`, `contrasts`, `context`, `distractor`); citation target and required source fields; reviewer status. Shared references point to dataset evidence annotations containing DOI, section, exact `source_locator`, optional derived `chunk_id`, optional exact quotation, relevance label 0–3 and rationale.

Function-specific annotations (Person 2 defines and validates this internal sidecar; Person 3 receives it as a handoff):

- **Research Question Explorer**: expected key claims/findings, relevant papers and exact evidence/citation mapping; expected qualification/refusal on insufficient cases.
- **Evidence Comparison**: per-paper objective, method, conditions/population, measured outcome/result and limitations, each tied to source evidence. Missing dimensions are marked unavailable, not invented.
- **Conflicting Evidence Finder**: the distinct claims/results and source references; why the claims are genuinely different under comparable conditions; methodological context. Explanations are labeled source-supported, plausible-but-unverified, or unknown and never presented as a fact without evidence.
- **Research Gap & Hypothesis Assistant**: evidence-bounded gap statement and scope, supporting/contrasting sources, candidate research question/hypothesis, rationale, assumptions, uncertainty, and what evidence would test it. Hypotheses are proposals, not factual gold answers.

### Objective per-question and functionality readiness

- **Positive/answerable**: question has a determinate answer from the frozen corpus; every atomic expected finding has at least one directly supporting evidence unit labeled 2 or 3, with normalized DOI, exact section context and durable locator. The question's source DOI set is a subset of the 17 corpus DOIs. Cross-paper comparison/conflict requires at least two distinct source DOIs. Every claim has at least one citation target; unsupported atomic claims fail.
- **Insufficient evidence**: question is explicitly bounded to the frozen corpus/version; corpus-wide search/review scope and sources inspected are recorded; no available passage sufficiently answers the whole question. Related or partial passages may be labeled 0/1 with rationale, but there must be no label-2/3 unit that answers the scoped question. State what is missing and avoid claiming universal absence beyond the corpus. Negative cases have no positive Recall/MRR denominator.
- **Functionality minimum**: each functionality has at least two distinct question tags and passes specific checks: Explorer has claim-to-source/citation links and abstention cases; Comparison has source-backed objectives/methods/conditions/outcomes/limitations or explicit `not_reported`; Conflict Finder's Q4/Q5 are negative controls that must reject conflict labels based on non-equivalence. No sensitivity claim is permitted because the corpus has zero defensible genuine-conflict pairs; Gap/Hypothesis has a scoped supported gap and labeled testable hypothesis. These counts support descriptive coverage only, not per-function performance claims.
- **Source-paper coverage**: every cited DOI must resolve to one of the frozen 17 papers and every question must have at least one such DOI. Report unique DOI count/list, question-to-DOI matrix, and per-category/per-function source coverage. No repository requirement establishes 17/17 coverage, so do not force irrelevant papers into annotations; if a new requirement for 17/17 emerges, ask the user before changing this plan.
- **Review disposition**: machine validation and source checks are prerequisites, not scientific approval. Each record remains transparently `in_review` in the shared schema fields unless their existing semantics accurately represent its state; sidecar/manifest records `chatgpt_review_status` (`pending`, `rejected`, `approved`), reviewer context, date, evidence inspected, findings and re-review history. Do not overload any human-verification field to mean ChatGPT approval.

P2 retrieval ground truth remains only the labeled evidence units and source matching. The sidecar separately records reference structures for answer support/citations, comparison, conflict explanation, insufficiency behavior, and hypotheses; Person 2 does not score generated outputs in Phase D. Person 3 may integrate these as proposed reference inputs under their own evaluation workflow; that integration is not a Person 2 completion dependency.

## Frozen retrieval and metric protocol

### Arms

Run accepted exact dense cosine, PostgreSQL English full-text lexical retrieval, and hybrid RRF (`k=60`), same snapshot, query set, filters, embeddings, candidate ceiling, and deterministic tie order. Freeze OpenAI `text-embedding-3-small` at 1536 dimensions and current pilot. No reranker; MiniLM remains disabled after the Phase C NO-GO. Do not add NDCG, rerankers, or unrelated experiments. Changed configs are separately labeled exploratory and cannot replace primary results.

### Evidence units and matching

Canonicalize DOI using the accepted DOI normalization; locator is an exact opaque source locator. Primary match requires equal normalized DOI and exact chunk primary/span locator. The only fallback is equal DOI, labeled section, and exact quotation containment. Section-only or approximate text matches are diagnostics, not positive hits.

A gold evidence unit is a canonical unique annotation identity: normalized DOI + exact canonical locator + SHA-256 identity of the exact quotation UTF-8 bytes when supplied, otherwise DOI + locator. Exact duplicate annotations are collapsed before denominators; conflicting relevance labels on the same canonical identity fail dataset validation. Distinct passages remain separate even within one paper.

- One retrieved chunk may credit multiple distinct gold units only when it independently matches each unit's DOI and locator (or independently satisfies the allowed fallback for each).
- Many retrieved chunks matching the same gold unit count that unit once; record the earliest matching rank for ranking metrics.
- Duplicate chunk IDs are rejected/deduplicated. Exact duplicate and overlapping chunks that map to already credited units cannot increase the numerator. Preserve ranking positions for MRR; do not compress ranks unless the accepted retrieval output itself already applies its frozen duplicate policy.
- Recall numerator and denominator are sets of unique relevant gold units. Therefore Recall is in [0,1]; assert this invariant. Evidence Hit is binary. One-to-many mappings cannot multiply-count a unit.

### Metrics and aggregation

For K=1,3,5,10,20 (limited by eligible returned candidates):

- `Recall@K = |unique relevant gold units matched by top K| / |all unique relevant gold units for question|`.
- `Evidence Hit@K = 1` iff the Recall numerator is nonzero; otherwise 0.
- `MRR@K = 1 / earliest rank matching any relevant unit`; 0 when none appears through K, only for positive questions where first-hit ranking is meaningful.
- If no positive reference set exists, positive Recall/MRR are null/not applicable, not zero. Negative/insufficient cases are a separate report.

Report per question, macro over eligible questions, and macro by question type; explicitly report total/eligible/excluded n, exclusion reason, reference-unit denominators, and null values. No micro-pooled score. False-support rate requires frozen blinded human adjudication (`supported`, `partial`, `unsupported`, `uncertain`) and explicit denominator/uncertain handling; otherwise mark NOT COMPUTED. Independent synthetic oracles cover one chunk→many references, many chunks→one reference, overlap/duplicates, repeated locator/quotes, exact/fallback boundaries, and assert no metric inflation and Recall≤1.

**Metric populations and missingness policy:** For each cohort and retrieval arm, positive Recall@K, Evidence Hit@K, and MRR@K are macro-averaged over answerable questions with validated ground truth containing at least one unique relevance-2/3 evidence unit. Per-question Recall denominator is that question's count of unique relevant gold units; it is never a pooled evidence-unit denominator. Evidence Hit contributes one binary value per eligible answerable question; MRR uses that same population. Insufficient-evidence cases have zero positive gold units by design, so their positive Recall/MRR are null/not applicable and excluded from positive means; report their n and retrieval observations separately. Do not score empty retrieval as correct abstention. An answerable question with missing/invalid gold evidence is a curation/readiness failure: stop the affected cohort, do not silently drop it. A missing query vector is an arm-level readiness failure, not a retrieval failure or denominator exclusion; stop that cohort's dense/hybrid arm. Lexical may be reported independently on all authorized eligible questions but cannot be compared to dense/hybrid on a different n. Report eligible and excluded counts by cohort, answerability, question type, functionality, and reason. The optional pooled held-out macro uses per-question positive metrics across eligible v0/v1 held-out questions only; it reports positive-eligible n separately from insufficient n and is omitted if configuration/definition mismatch, contamination, or incomplete arm eligibility prevents a valid common cohort.

## Deterministic query-vector compatibility procedure

**Code inspection findings:** `EmbeddingConfig` defaults to provider `openai`, model `text-embedding-3-small`, 1536 dimensions, empty query/passage prefixes, max 8 inputs/request, max 2048 estimated tokens/request, and up to 3 attempts. The retrieval request boundary strips leading/trailing whitespace, preserves all other text, and accepts at most 2000 characters; `OpenAIEmbedder.embed_queries()` prepends the configured query prefix once and verifies the response model identifier and vector dimension. The active `EmbeddingSet` supplies provider/model/dimensions/query prefix; the accepted pilot compatibility rule requires `float32-le` and empty passage prefix. Its model identifier is not an immutable model revision, so record this residual limitation and do not claim revision-level identity.

The local `EmbeddingCache` defaults to `data/embeddings/pilot/cache/` and keys entries by model, dimensions, and exact final input SHA-256. Entry metadata/checks validate cache format, model, dimensions, input digest, vector digest/length/finiteness, and batch usage/date/ID. This is a passage-input cache format: it has no question ID, dataset/partition/corpus identity, provider, query-vs-passage role, or prefix field. No query-cache artifact was found in the inspected code/configuration; no cache contents were inspected, and cache availability is unknown. A cache entry alone is therefore insufficient provenance. Reuse is allowed only when a separate versioned evaluation query-cache manifest binds every record to the entry and proves all configuration/source fields below. Do not assume the existing passage cache contains query vectors.

Before the user authorizes access to the named held-out cohort, freeze the retrieval configuration and partitions. A first separate explicit protected-preflight authorization must name each cohort before any protected question text or derived hash is read. It authorizes read-only preflight only. After readiness passes, a second explicit held-out retrieval authorization is required before any retrieval run. Then, and only then, the read-only verifier must:

1. Load only the specifically authorized question IDs. Apply the retrieval contract's exact normalization (`str.strip()` only; no case-folding, Unicode normalization, punctuation rewriting, or truncation), reject invalid/blank/over-2000-character strings, and hash the normalized exact UTF-8 text. Hash the dataset/version and partition manifests and map question ID→normalized-text hash.
2. Resolve the active corpus embedding identity from the read-only active `EmbeddingSet`; require provider `openai`, model identifier exactly `text-embedding-3-small`, 1536 dimensions, empty query prefix, empty passage prefix, and `float32-le`, matching the frozen retrieval configuration. Any mismatch stops dense/hybrid preflight.
3. For each query vector require exactly one record for the question ID and exact normalized-text hash, final provider-input hash (query prefix + normalized text), dataset version/full hash, cohort/partition hash, corpus version/hash, active embedding-set identity, provider/model/dimensions/prefix, cache-entry key, response model identity, generation timestamp, and provenance source. Require exact one-to-one ID association; duplicates, unknown IDs, duplicate/missing mappings, or cross-partition reuse without an exact same-input mapping fail closed.
4. Validate cache format/version, read-only file availability, cache metadata identity, expected `float32-le` byte length (1536×4), all finite components, nonzero norm, and L2 norm within the accepted 0.01 corpus tolerance. Recompute vector-byte SHA-256, entry-file SHA-256, manifest SHA-256, and mapping hashes; check before/after hashes to detect mutation. Log IDs/status/hashes only, never vector values, secrets, or held-out text.
5. Compare the cache/model/config identity to the active corpus and frozen config; persist an IDs-and-hashes-only pass/fail report, exact cache-miss list by opaque ID, and run configuration hash. Do not write or repair the cache or database during preflight.

Missing, stale, mismatched, duplicate, corrupt, non-finite, zero-norm, or unverifiable vectors fail closed. Do not substitute another model, fake/local incompatible vector, or placeholder. Do not silently remove a question or count it as a retrieval miss. A missing vector stops that cohort's dense and hybrid arms; a lexical-only result may be reported for all authorized eligible questions but is not a like-for-like comparison to incomplete dense/hybrid arms.

If vectors are missing/invalid, stop the affected real evaluation and prepare an approval request that specifies: exact cohort/IDs and number of distinct missing normalized queries; model/provider/identifier `openai` / `text-embedding-3-small`; dimensions 1536; empty query prefix; exact deterministic batching (sorted IDs, at most 8 distinct inputs and at most 2048 estimated tokens per request); token-counter ID and estimated total input tokens; logical request count and worst-case attempts using configured `max_attempts=3`; current cost rate/source and estimated charge; and a hard spending cap. Estimate calls by applying these batching limits to unique cache misses; do not fabricate a count before question text/cache inspection is authorized. The existing code reports a planning rate of $0.02 per 1M input tokens; re-check the official rate at authorization time. At current planning research, the [official model page](https://developers.openai.com/api/docs/models/text-embedding-3-small) lists $0.02/1M input tokens (checked 2026-11-19). No request is made without your separate explicit approval and cap. Never regenerate implicitly.

## Exact execution and authorization sequence

1. Following plan approval and separate explicit implementation authorization, implement/test the framework with synthetic fixtures and authorized development data. Person 1/3 readiness does not block this work.
2. Before any question generation, preregister the approved matrix/crosswalk, answerability/evidence rules, source-coverage reporting, deterministic slot partition (Q1/Q4/Q6 development; Q2/Q3/Q5/Q7/Q8/Q9 held-out), metrics/matcher, frozen baseline and leakage controls.
3. Generate/refine AI-assisted candidates from real frozen pilot scientific sources, record complete provenance, annotations and exact evidence locators. Do not use retrieval outputs. Mechanically validate all fields/claims that can be checked; mechanical checks are not scientific review.
4. Prepare the protected packet with all nine records, original relevant passages, locators, expected findings, answerability, labels, provenance, sidecar, validation results and hashes. Isolate it from retrieval development/debug/tuning inputs. Then STOP.
5. In a fresh ChatGPT review context, manually inspect every record against original source passages and independently assess scientific correctness, DOI/section/chunk/locator, expected findings, answerability, provenance and functionality coverage. Record per-question decision and defects. This is model review, not human verification. Correct and resubmit affected records until ChatGPT explicitly approves all nine.
6. After ChatGPT approval, STOP until the user explicitly authorizes continuation. If nine questions cannot genuinely meet the matrix, stop and request the user's approval for a justified expansion.
7. After continuation, freeze final question IDs/text, sidecar, dataset/corpus hashes and partitions; preserve v0 byte-for-byte. No evaluation outputs may inform any edits.
8. Pass synthetic partition-isolation tests; verify evaluator/config identities. After partitions/configuration freeze and T004 continuation, obtain the first explicit user authorization naming cohort/version/partition for protected record/vector preflight only; the review packet gate is not this authorization.
9. Use only `SCISCOPE_TEST_DATABASE_URL`; identity-preflight exactly `sciscope_test_005`, enforce read-only access, verify active corpus/counts 17/319/728/728 and `pilot17-xml-1fff1573b610`. Abort on mismatch or write requirement.
10. Under the preflight-only authorization, verify query-vector readiness: exact question/vector mapping and content hashes, dataset/corpus/partition hashes, model/provenance/cache integrity, frozen-config compatibility. Missing/unverifiable vectors fail closed. Paid embeddings need separate approval and hard cap.
11. After successful preflight, obtain a second explicit held-out retrieval authorization naming the same dataset/version/cohort/partition. Then run dense, lexical FTS and hybrid RRF on identical authorized questions/corpus/config/filters/cutoffs for each eligible cohort. Report v0-HO (n=16) and v1-HO (n=6) separately as primary cohort results. An optional descriptive pooled result may include only eligible held-out questions from both cohorts (maximum n=22) under identical frozen conditions; exclude all eight development questions and report positive-metric and insufficient-evidence denominators separately. Record deterministic aggregation, repeated stage latency, environment, manifests and hashes.
12. Verify post-run DB identity/read-only status, row/corpus counts and cache immutability; reproduce deterministic metrics. False-support is calculated only with blinded human adjudication; otherwise NOT COMPUTED.
13. Codex autonomously runs authorized regression, static, reproducibility, and read-only postcondition checks; fixes routine defects and reruns affected checks; records exact commands, environment/configuration identifiers, test counts, failures, skips, artifacts, and limitations. ChatGPT independently reviews code, reports, and evidence. The user reviews the concise evidence summary and explicitly accepts; no routine PowerShell rerun is required.

## Data safety

No database writes, migrations, schema changes, ingestion, or production `sciscope` access. Read-only pre/post checks of `sciscope_test_005` only. No credentials or question text in logs/manifests; held-out manifests contain IDs and hashes only. No paid API without separate authorization/cap.

## Planned file changes

### Execution status (T004 complete; T005 not authorized)

- `src/sciscope/evaluation/golden.py` — allowlisted streaming loader and version/hash/schema checks.
- `src/sciscope/evaluation/matching.py` — canonical evidence units and match diagnostics.
- `src/sciscope/evaluation/metrics.py` — exact pure metric definitions and aggregates.
- `src/sciscope/evaluation/embeddings.py` — read-only question/vector identity, provenance, and integrity validator; no generation path.
- `src/sciscope/evaluation/report.py` — per-question/type/macro report and manifests.
- `scripts/phase_d_retrieval_evaluation.py` — native Windows runner; fail closed on approvals, preflight, missing vectors, unauthorized partition or drift.
- `tests/evaluation/test_phase_d_golden.py`, `test_phase_d_matching.py`, `test_phase_d_metrics.py`, `test_phase_d_embeddings.py`, `test_phase_d_report.py`, `test_phase_d_runner.py`, `test_phase_d_curation_manifest.py` — synthetic first and independent oracles.
- `tests/retrieval/test_phase_d_readonly_integration.py` — read-only `sciscope_test_005` integration after gates.
- `evals/protected/golden_v1_review/golden_questions.v1.candidates.json` and protected curation manifest/sidecar copies — candidate-stage artifacts isolated from retrieval development/tuning.
- `evals/protected/golden_v1_review/` — access-restricted, version-control-excluded all-nine packet with original source passages, annotations, validation results, hashes, ChatGPT review report, and correction/re-review history.
- `docs/person2/PHASE_D_T004_REVIEW_AND_VERIFICATION.md` — all-nine independent ChatGPT decisions and scope limitations; native Windows test, database, package, and corpus verification evidence. The reported review is model review, not human verification.
- `evals/protected/golden_v1_review/golden_questions.v1.json` — frozen P2 evaluation dataset, kept access-restricted and Git-ignored; the runner accesses only explicitly authorized IDs through the allowlist; do not label as human-verified/shared release.
- `evals/golden_v1_curation_manifest.json` — author/reviewer/source/category/coverage/partition/hash/review evidence.
- `evals/golden_functionality_annotations.schema.json` and `evals/golden_functionality_annotations.v1.json` — versioned Person 2 sidecar schema/data; internal use only, not part of retrieval metrics; shared adoption is a proposal in Person 3 handoff.
- `docs/person2/PHASE_D_RUNBOOK.md`, `docs/person2/PHASE_D_RESULTS.md`, `evals/results/` — runbook and actual results only after execution; no placeholders/fabricated values.
- `specs/009-phase-d-retrieval-evaluation/quickstart.md` — approved native Windows commands and safety assertions.
- `EVIDENCE.md`, `PROJECT_TODO.md` — actual observations and status only after checks and user acceptance.

Any schema change or new cache format needs an explicit contract decision; prefer current contracts and existing vector artifact format.

## Verification strategy

- **Unit**: synthetic loader, partition isolation, curation readiness, locator/fallback boundaries, conflicting-label rejection, one-to-many/many-to-one matching, duplicate/overlap suppression, independent metric oracle cases, denominator/null/type aggregation, deterministic serialization, secret redaction, vector identity/hash/provenance/shape/dtype/finiteness/staleness.
- **Curation/review**: ChatGPT's fresh-context manual source-based review inspects every v1 record; preserve packet, per-record disposition, findings and re-review. Label this model review, not human verification. Mechanical checks do not substitute for it.
- **Integration**: read-only transactions on preflight-confirmed test DB; verify 17/319/728/728 and corpus before/after; three modes; no writes/schema changes.
- **Regression**: relevant retrieval suites and project checks; preserve A/B/C; content-opening tests do not disclose held-out questions.
- **Independent acceptance**: provide read-only PowerShell checks; user returns actual output and explicit acceptance. Do not close tasks before it.

## Risks and mitigations

| Risk | Mitigation / stop condition |
| --- | --- |
| Shared human-verification policy differs from P2 method | Keep constitution and `docs/EVALUATION_PLAN.md` unchanged; accurately identify v1 as a P2 evaluation dataset with ChatGPT review, not a shared human-verified release; document integration proposal in handoff. |
| ChatGPT identifies source or annotation defects | Stop at T004; correct affected records and submit them for another independent review. No downstream work until all nine are approved and user authorizes continuation. |
| Procedural isolation limitations | Protected storage is Git-ignored and workflow-checked, but the inherited Windows ACL remains broad. This is not OS-enforced isolation; same-identity processes can read the records. The exact limitation is disclosed in the review packet. |
| Mandatory review gate | ChatGPT approved all nine records and T004 verification is recorded. Do not proceed to T005+ until the owner explicitly authorizes continuation. |
| Sidecar differs from Person 3 needs | Keep it versioned and internal; document proposed integration/mapping in Person 3 handoff. No approval dependency for P2 completion. |
| V1 authoring/review cannot complete by deadline | V1 is mandatory: do not call Phase D complete until actual curation, review, freeze and evaluation finish. |
| Category/coverage/answerability criteria underspecified | Obtain approval of concrete matrix before generation; no silent category or coverage reduction. |
| Held-out data leakage | Frozen pre-registered partition, synthetic isolation tests, bounded allowlist loader, separate user authorization, no question text in manifests. |
| Missing/mismatched vectors | Read-only integrity verifier; fail closed; no implicit embedding calls. |
| Paid embedding needed | Stop pending separate authorization and hard cap. |
| Small dataset | Report the two held-out cohorts separately (v0 n=16, v1 n=6); any eligible pooled n≤22 is descriptive only. The 30-record catalog across 17 papers is not a single independent test set; no statistical generalization claim. |
| Negative labels do not prove absence | Human scope review and blinded retrieved-passage adjudication; otherwise false-support metric is not computed. |
| Pilot/corpus drift | Exact identity/count pre/post gates; abort on drift. |
| Phase C historical exception | Preserve the approved exception as a distinct Phase C history; it grants no Phase D access exception. |

## Handoff to Phase E

Provide frozen baseline, Golden v1 and partition identities, report and manifest hashes, observed results, curation/review evidence, reproducibility commands, limitations/non-claims, failures, and unresolved cross-owner dependencies. Phase E answer support, refusal, citation generation, and public facade remain out of scope.

## Complexity Tracking

No constitution violation or new dependency is proposed.
