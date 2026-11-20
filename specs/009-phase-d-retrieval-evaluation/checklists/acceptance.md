# Acceptance Checklist: Phase D Scientific Retrieval Evaluation

**Purpose**: Mandatory feature and final acceptance gates  
**Created**: 2026-11-19  
**Feature**: [spec.md](../spec.md)  
**Status**: T004 is accepted. T005 readiness and separately authorized T006 retrieval are complete for both cohorts; T007 reports/handoffs and T008 package verification, independent review findings, and read-only lexical diagnostics are recorded. All 49 stable criteria AC-001–AC-049 remain individually tracked. T008 acceptance awaits the owner's decision on a separate versioned lexical/hybrid diagnostic cycle and final owner acceptance. AC-038 is only partially evidenced because reports do not label cold/warm observations or separate retrieval stages.

## Approval, requirements, and pre-registration

- [x] AC-001 User explicitly approves the complete specification, plan, tasks, and checklist, then user separately explicitly authorizes implementation before tests/code changes.
- [ ] AC-002 Person 2-owned methodology transparently records the prior approx. 30%/independently human-authored requirement and its scoped replacement with AI-assisted creation plus ChatGPT source-based review; constitution and shared `docs/EVALUATION_PLAN.md` remain unchanged and handoffs disclose that this is not a shared human-verified release.
- [ ] AC-003 No Person 1, Person 3, mentor, or project-owner approval is imposed on internal P2 artifacts; cross-team schema/output integration is documented as a proposal in handoffs only.
- [x] AC-004 Owner-approved amended matrix is validated: 3 insufficient-evidence, 0 genuine conflicting-evidence, 2 research-gap, 1 single-paper factual, 3 multi-paper comparison. Q4/Q5 retain Conflict Finder tags only as false-conflict negative controls; no genuine-conflict sensitivity claim is made because the frozen corpus has no defensible comparable contradiction pair. Evidence: protected validation report and T004 review/verification record.
- [ ] AC-005 Before generation, the plan fixes positive/insufficient answerability rules, per-question evidence sufficiency, cross-paper minimums, source DOI coverage reporting, functionality criteria, and deterministic v1 slot split Q1/Q4/Q6 development versus Q2/Q3/Q5/Q7/Q8/Q9 held-out; v0 stays unchanged.

## Golden v1 creation, validation, protected packet, and ChatGPT review gate

- [ ] AC-006 Each candidate records mode (`ai_generated`/`ai_assisted`), tool/model/version when known, date, frozen-pilot source inputs, prompt/draft lineage, AI contribution, and correction history; unknowns are explicitly unknown.
- [ ] AC-007 Every candidate accurately identifies `ai_generated`/`ai_assisted`; no AI-generated question is called human-authored or ChatGPT-reviewed content called human-verified. AI prompts/draft lineage and tool/model metadata are retained where known.
- [ ] AC-008 Every positive question has a source-derived expected answer and at least one relevant evidence unit labeled 2 or 3; labels 0/1 follow the approved rubric.
- [x] AC-009 All nine records validate against the unchanged `evals/golden_questions.schema.json`; Phase D additionally requires explicit `question_type`, `expected_insufficient_evidence`, `source_corpus_version`, DOI/section/evidence locator, and answerability/findings. `reviewer` truthfully identifies ChatGPT as an AI model reviewer, `verification_status` remains `in_review`, and no human `verified_date` is fabricated. Evidence: protected validation report; no human verification is claimed.
- [ ] AC-010 Every insufficient-evidence record documents frozen corpus scope/content coverage, searched/reviewed sources, why available evidence is insufficient, and the limits of any absence claim.
- [x] AC-011 The protected packet includes all nine records, supplied source passages from frozen derived chunks, DOI/section/chunk/durable locators, expected findings, answerability, relevance annotations/rationales, provenance, functionality annotations, validation outputs, and hashes. Raw XML was unavailable; no raw-XML verification is claimed.
- [x] AC-012 ChatGPT in a fresh review context inspected all nine records against the supplied source passages and approved scientific correctness, answerability, evidence links, expected findings, provenance, and functionality annotations. Per-question outcomes are recorded in `docs/person2/PHASE_D_T004_REVIEW_AND_VERIFICATION.md`. This is model review, not human verification; review limitations are disclosed.
- [x] AC-013 Q4/Q5/Q6/Q9 defects were corrected with provenance/history and resubmitted; the independent ChatGPT review approved all four. No unresolved scientific review finding remains.
- [x] AC-014 After ChatGPT approved all nine, work stopped pending the user's explicit continuation authorization. No subsequent implementation or evaluation has proceeded.
- [ ] AC-015 No retrieval/tuning outputs were viewed before v1 freeze; questions/labels/partitions were not moved or changed in response to scores. Post-freeze corrections create a new version and require a fresh untouched confirmatory holdout.

## Partition isolation and embedding readiness

- [ ] AC-016 Synthetic isolation tests pass before the retrieval/evaluation loader can decode any real held-out object; the source-curation/review packet path is separately access-restricted and is never an evaluation-runner input. The evaluation loader only buffers/decodes allowlisted objects; malformed non-allowlisted fixtures do not reach the decoder.
- [ ] AC-017 v0 five development IDs remain smoke-only; its other 16 questions remain held out until separate authorization. The Phase C historical full-deserialization exception remains disclosed and does not authorize Phase D access.
- [ ] AC-018 Golden v1 development and held-out partitions match the approved frozen assignment; no partition change is based on observed performance.
- [ ] AC-019 Before protected query/vector access, explicit authorization covers the named cohort. The read-only check proves exactly one vector per authorized question ID and exact normalized-query hash, dataset version/full hash, corpus/partition hashes, model/config identity, cache manifest, and vector mapping.
- [ ] AC-020 Vector provenance proves provider `openai`, response model identifier `text-embedding-3-small`, 1536 dimensions, empty query/passage prefixes, compatibility with the active embedding-set provider/model/dimensions/prefix/dtype, and source artifact; shape alone is not model identity. Record that provider model revision is not pinned if unavailable.
- [ ] AC-021 Every vector is `float32-le`, exactly 1536 finite values, nonzero norm (and within the corpus normalization tolerance where required); canonical vector-byte and cache-file SHA-256 and manifest integrity pass; no vector values or secrets are logged.
- [ ] AC-022 Missing, stale, mismatched, duplicate, corrupt, non-finite, or unverifiable vectors fail closed for the affected dense/hybrid cohort; no implicit regeneration or silent denominator removal. Paid generation requires explicit authorization for the operation; record actual calls, token usage, and cost. A monetary cap applies only when the authorization specifies one.

## Matching, metrics, and frozen evaluation

- [ ] AC-023 Gold-unit identity and duplicate policy are explicit and applied before denominators: normalized DOI + exact canonical locator + exact quotation byte identity where supplied; exact duplicate annotations collapse and conflicting labels for one canonical unit fail validation.
- [ ] AC-024 A retrieved chunk credits multiple gold units only when each independently matches; multiple chunks matching one gold unit count it once at earliest matching rank; duplicate/overlap retrievals do not improve counts.
- [ ] AC-025 DOI and exact locator are the primary match; only fallback is matching DOI, labeled section, and exact quotation containment. Section-only or approximate matches are diagnostic only.
- [ ] AC-026 Independent synthetic oracles cover one retrieved chunk→multiple gold units, one gold unit→multiple chunks, overlapping and duplicate results, repeated locator/quotes, DOI normalization, fallback boundaries, no-result, no-positive-reference, ties, and K cutoffs.
- [ ] AC-027 Tests assert Recall@K is always in [0,1], duplicate/overlap rows cannot increase Recall/Hit/MRR, and matching/metric values meet hand-calculated independent expectations.
- [ ] AC-028 Recall@K = unique relevant gold units in top K / all unique labeled relevant gold units; labels 2/3 relevant; Evidence Hit@K is binary for any hit; MRR@K is reciprocal earliest positive rank, with each undefined case null and explained.
- [ ] AC-029 Reporting contains per-question and per-cohort results (v0 held-out n=16; v1 held-out n=6), answerable-only denominators for positive Recall/Hit/MRR, insufficient-evidence counts and separate negative outcomes, type/function descriptive summaries, eligible n, exclusions/reasons, evidence-unit denominators, and nulls; no micro-pooled score replaces required macro means.
- [ ] AC-030 Insufficient-evidence questions have no positive evidence-unit denominator, so positive Recall@K and MRR@K are `null`/not applicable (not zero); Evidence Hit is reported only for its defined eligible population. Empty retrieval is not proof of correct abstention. False-support rate is computed only with frozen blinded human adjudication and explicit denominator; otherwise NOT COMPUTED.
- [ ] AC-031 Primary v1 comparison includes exact dense, PostgreSQL lexical FTS and hybrid RRF on identical frozen questions, corpus, filters, vectors, candidate ceiling, metrics and K; no reranker or NDCG arm.
- [ ] AC-032 Frozen baseline remains `text-embedding-3-small`/1536, exact cosine, PostgreSQL FTS, hybrid RRF `k=60`, no reranker. Changed settings are exploratory and do not replace preregistered results.
- [ ] AC-033 v0 held-out n=16 and v1 held-out n=6 are reported separately with provenance. Optional pooled n=22 is descriptive only when both cohorts pass readiness and use the same frozen config/definitions; it excludes all eight development cases and is not called independent/representative or a 30-question test set. No small-sample significance or per-function strength claims.

## Execution safety, reproducibility, and closure

- [ ] AC-034 Two distinct explicit user authorizations name dataset version/cohort/partition: first, protected record/vector preflight after config/partitions freeze and before protected text/hash access; second, final held-out retrieval after preflight readiness. T004 source review is isolated from retrieval development and is neither authorization.

**AC-034 implementation note (2026-11-20):** The standalone T005 authorization
validator and preflight-only CLI mode are implemented; 33 synthetic
authorization/CLI tests pass as part of the 181-test offline suite.
The T006 validator still requires a separate, distinct, matching retrieval
approval. No real approval record was created or checked, and no protected
query/cache was accessed; therefore AC-034 remains open until the required
cohort-specific approvals and operational checks occur.

**T005 execution update (2026-11-20):** The owner later explicitly authorized
read-only preflight for both held-out cohorts. Direct-message approval
provenance was recorded and verified, and separate protected authorization
records bind each cohort to its dataset and partition identity. The database
and corpus preflight passed. The registered query-cache directory and manifest
are absent, so no vector could be verified; AC-019–022 and AC-034 remain
unchecked. No vector generation, paid call, or retrieval run occurred. See
`docs/person2/PHASE_D_RESULTS.md` and the protected T005 readiness report.

**T005 completion update (2026-11-20; supersedes the blocked-cache outcome
above):** The owner explicitly authorized all missing query vectors for both
held-out cohorts using `text-embedding-3-small`/1536 with no monetary cap.
Question and partition identities were checked before text access; only the
16 v0-HO and 6 v1-HO allowlisted records were embedded. Both manifests and all
22 vectors passed identity, mapping, model/config, cache integrity, dimension,
finiteness, and norm validation. Actual usage was 3 calls, 626 prompt/total
tokens, USD 0.00001252. T005 readiness is PASS; no retrieval was run. AC-019,
AC-020, and AC-021 have supporting execution evidence, while checklist boxes
remain open pending final independent review/acceptance. AC-034 remains open
because T006 retrieval authorization has not been granted. See the protected
readiness and text-free generation reports.
- [ ] AC-035 Only `SCISCOPE_TEST_DATABASE_URL` is used; actual database identity is exactly `sciscope_test_005`, and the connection/read operations are confirmed read-only.
- [ ] AC-036 Frozen pilot/corpus identity is verified before and after: 17 papers, 319 sections, 728 chunks, 728 embeddings, corpus `pilot17-xml-1fff1573b610`; no schema/pilot writes, migrations, or production `sciscope` access.
- [ ] AC-037 Run manifests contain input/config/version/hash, code/env/command, DB/migration, embedding usage/cost, repetitions, failures, stage latency and output identity; no secrets or held-out question text.
- [ ] AC-038 Latency uses repeated warm/cold measurements and reports median/p95/max/failures for separable stages; unavailable stages are marked unavailable.
- [ ] AC-039 Post-run database, corpus and vector/cache invariants pass; deterministic metric outputs reproduce from frozen inputs; all failures, skips, limitations and non-claims are recorded.
- [ ] AC-040 Results and Phase E/Person 1/Person 3 handoffs distinguish v0/v1, summarize actual AI provenance and ChatGPT review evidence, disclose 30-question/17-paper limits and shared human-verification governance boundary, and do not claim statistical generalizability or answer-generation quality.
- [ ] AC-041 `EVIDENCE.md` and `PROJECT_TODO.md` reflect only actual outcomes and remain open until automated checks and explicit user acceptance.
- [ ] AC-042 Codex autonomously executes and records all authorized implementation, debugging, tests, static checks, reproducibility checks, and read-only verification; it fixes routine failures and reruns affected checks. Exact commands, environment/config IDs, counts, failures, skips, artifacts, and limitations are recorded. ChatGPT independently reviews implementation, reports, and evidence. User reviews the concise evidence summary and explicitly accepts; user need not rerun routine commands.
- [ ] AC-043 No Phase A/B/C accepted implementation/evidence, protected production database, shared contract, or disabled reranker decision was changed.

## Stop conditions

- [ ] AC-044 Any missing curation review, partition/hash mismatch, unauthorized held-out access, vector mismatch, wrong DB/corpus identity, write attempt, unapproved paid call, secret leak, or unresolved evidence ambiguity halts real evaluation and is recorded without a result claim.
- [ ] AC-045 After plan approval and explicit implementation authorization, framework work may proceed with synthetic/already-authorized development data. The T004 packet review gate blocks all subsequent implementation/evaluation until ChatGPT approval and user continuation authorization.

## Cross-cutting contract, inventory, and contamination controls

- [ ] AC-046 Metric/matcher versions, frozen retrieval config, corpus identity, leakage controls, IDs and curation provenance are preregistered before generation or evaluation.
- [ ] AC-047 Functionality sidecar validates against a separate P2-owned schema/version, has unique question IDs with exact one-to-one referential integrity to v1 IDs, source-grounded references/expected structures, and remains distinct from retrieval labels/metrics; Person 3 integration is handoff only.
- [ ] AC-048 Final v1 addendum validates against the unchanged Golden schema, preserves v0 byte-for-byte, remains `verification_status: in_review` with truthful AI reviewer labeling and no fabricated verified date, and has its own version, dataset/corpus hashes, AI/ChatGPT review manifest, category/functionality coverage, actual source-paper coverage, and frozen dev/held-out ID lists/hashes.
- [ ] AC-049 Protected held-out content is accessed only in the specified isolated T004 v1 review and explicitly authorized final evaluation; it never enters retrieval development/debug/tuning fixtures, ordinary outputs, logs, or manifests. Prior exposure is audited; contaminated items are disclosed and excluded from independent claims without replacement. Any post-freeze correction creates a new version and fresh confirmatory holdout.

**T006 execution update (2026-11-20; supersedes the prior awaiting-T006 note):** The user separately authorized v0-HO and v1-HO retrieval under frozen dense, lexical, and hybrid modes using read-only sciscope_test_005. Separate T005/T006 approval pairs validated for both cohorts. The run completed for n=16 and n=6 with two exact-result repetitions per question/arm. Six protected cohort/arm reports, run metadata, latency, and metric denominators are available in Git-ignored output; read-only pre/post corpus checks passed. Metric bounds, answerable/insufficient denominators, and text-leak audit passed. No tuning, database mutation, additional paid API call, pooled estimate, or genuine-conflict sensitivity claim. AC-029–039 have supporting artifacts where applicable; AC-034 authorization evidence is present. Checklist boxes remain open until independent technical review and final user acceptance.

**T008 diagnostic update (2026-11-20):** Owner-reported independent ChatGPT
review verified package hashes and independently recomputed macro metrics.
Read-only source-derived probes confirmed English FTS returns expected chunks
for scientific terminology, RNA, feeding, a bee taxon, and a contextualized
numeric query. A numeric-only target ranked 31, beyond top 20; a composed
cross-source long query returned no candidates with positive lexemes joined by
AND. Synthetic RRF unit tests passed for dense-only, lexical-only, overlapping,
and duplicate chunk cases. Existing development questions do not form a
purpose-built lexical test set; a separate versioned diagnostic set is
recommended before any improvement cycle. No held-out text/results were
inspected, no tuning or retrieval rerun occurred. The exact probe table and
coverage limitations are in `docs/person2/PHASE_D_RESULTS.md`. AC-038 remains
partial. Final T008 acceptance requires the owner to decide whether a separate
lexical/hybrid diagnostic cycle is necessary and then explicitly accept Phase D.

**Final independent review and T008 diagnostic update (2026-11-20):** The
owner reports ChatGPT verified all 84 package payload hashes, confirmed all six
cohort/arm reports, and independently recomputed macro Recall, Evidence Hit,
and MRR from per-question results with matching values. Dense and hybrid
metrics were identical; lexical Recall@20 was zero for both cohorts. This
review did not independently reproduce PostgreSQL. A read-only code/test review
found English `websearch_to_tsquery` over `to_tsvector` of chunk text with
`ts_rank_cd`; controlled integration tests cover deterministic matching and
the empty stop-word-only case. Stored reports lack lexical candidate and
locator-match diagnostics, so the exact cause of zero lexical Recall is
undetermined. No tuning or retrieval rerun occurred. AC-038 is partial:
reports contain repeated total retrieval timing summaries but no cold/warm
labels or stage-separated timings. Small cohorts, lack of human Golden
verification, unavailable raw XML, and no genuine-conflict sensitivity
measurement remain explicit limitations. All checklist boxes remain open for
the owner's final acceptance; see
`docs/person2/PHASE_D_T008_ACCEPTANCE_SUMMARY.md` for criterion-by-criterion
evidence status.
