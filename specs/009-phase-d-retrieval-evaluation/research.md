# Phase D Research Notes

**Date:** 2026-11-19  
**Purpose:** Brief solution research for the evaluation feature specification. No implementation or evaluation was run.

## Problem and current facts

The repository already defines source-locator-based relevance, relevance labels 0–3 (2/3 relevant), Recall@K, Evidence Hit@K, applicable MRR, negative-question cautions, and reproducibility fields in `docs/person2/RETRIEVAL_EVALUATION_PROTOCOL.md` and `docs/EVALUATION_PLAN.md`. Existing code under `src/sciscope/evaluation/` implements only Phase C reranker benchmarking; no Phase D loader, evidence matcher, general retrieval metrics, or latency runner was located. Existing Phase C tests demonstrate an allowlist-scoped streaming-reader pattern, with a documented historic full-file deserialization exception that remains an exception.

Golden v0 metadata is documented as 21 AI-drafted, Person 1-verified questions over 12 of 17 papers, with five prior development/smoke IDs and 16 held-out IDs. Its question file was not opened. The Phase D population design treats those five as development-only and the remaining 16 as a distinct protected cohort. Golden v1 is a separate nine-question addendum: 3 development and 6 held-out. The eight development cases never enter a held-out estimate; the 22 protected cases are evaluated/reported by v0 and v1 cohort, with optional pooled descriptive reporting only under identical frozen conditions and eligible inputs. No 30-question independent-test claim is allowed. The earlier authorship rule and user's approved replacement are recorded in the Phase D plan; broader constitution/shared evaluation rules are unchanged, so the P2 v1 dataset must remain `in_review` and not be described as a shared human-verified release. The nine-category/functionality matrix and isolated T004 review gate are documented. The v1 question file was not generated or opened.

The local Golden schema was inspected. It requires question ID/text/language, expected findings, relevant papers, reviewer, verification status, and corpus version; `question_type` and insufficient flag are optional in schema but required by the Phase D curation contract. Evidence labels are strings; each relevant paper requires DOI/section/evidence; evidence requires either quote or locator. The schema supports `unverified`, `in_review`, and `verified`; its `reviewer` field description says human reviewer, and `evals/README.md` reserves released-dataset status for human-verified records. Thus the internal P2 v1 records will accurately identify ChatGPT as an AI reviewer and remain `in_review`, omit `verified_date`, and be used only by the P2 evaluation workflow after its sidecar review manifest and user continuation gate pass. This avoids fake human verification and preserves the shared schema/policy; shared-release integration remains a documented limitation.

Embedding source inspection found no query-cache subsystem. `EmbeddingConfig` defaults to provider `openai`, model `text-embedding-3-small`, dimensions 1536, empty prefixes, max 8 inputs and 2048 estimated tokens per request; query embedding prepends the query prefix once, and the OpenAI adapter validates the returned model ID and dimensions. Retrieval strips only query leading/trailing whitespace and accepts up to 2000 characters; active `EmbeddingSet` provides provider/model/dimensions/query prefix, while pilot compatibility requires float32-le and an empty passage prefix. `EmbeddingCache` is a passage-input cache keyed by model/dimensions/final input hash; entries hash vector bytes and validate size/finiteness, with batch/date metadata, but do not identify question, dataset/partition/corpus, provider, or query role. Its entries alone cannot establish query-vector provenance. Actual cache contents were not inspected and no cache availability is claimed. The approved design therefore requires a separate query manifest binding QID and exact retrieval-normalized query/config/corpus/partition identities to each entry. The returned API model ID is not a pinned immutable revision in the inspected contract; record the residual limitation rather than claim model-revision identity. The official model page lists $0.02 per million input tokens as of 2026-11-19; recheck at any future cost authorization.

## Approaches considered

1. **Use existing protocol and implement a repository-native harness plus explicit v1 curation/functionality provenance.** Reuse the existing Golden schema, retrieval core, exact DOI/locator/quotation policy, and specified metrics. Add narrowly scoped evaluation modules, a curation manifest recording AI and ChatGPT review provenance, a separately versioned internal functionality sidecar, protected review packet, and read-only vector/cache verifier. Do not change shared schema. Recommended.
2. **Adopt a general IR evaluation package.** Mature packages can provide standard metrics but do not define SciScope's source locator matching, evidence-unit identity, negative-question adjudication, partition isolation, or project manifests. Adding a dependency is not justified for the small, fixed metric set; package-specific tie/denominator behavior would still need explicit wrappers and independent oracles.
3. **Hand-score only or use answer-generation judgments.** Human assessment is essential for negative support and can check evidence quality, but alone it does not provide reproducible mode comparison. Using a system under evaluation to create ground truth would violate circularity controls. Human adjudication supplements, not replaces, labeled retrieval metrics.

## External authoritative references checked

## Owner-approved T004 category amendment (2026-11-20)

Source-level review of the frozen 17-paper corpus found no defensible pair of
genuinely contradictory findings under comparable study conditions. The owner
approved reclassifying Q4 and Q5 as multi-paper comparisons while retaining
their Conflicting Evidence Finder tags as negative controls for rejecting
apparent/non-equivalent conflicts. Golden v1's final target distribution is
3 insufficient-evidence, 0 genuine conflicting-evidence, 2 research-gap,
1 single-paper factual, and 3 multi-paper comparison. It does not measure
genuine-conflict detection sensitivity. This amendment preserves the frozen
corpus, retrieval baseline, metric definitions, and Q-slot partitions.

The prior T004 review found Q1/Q2/Q3/Q7/Q8 acceptable and defects in Q4/Q5/Q6/Q9.
Owner-authorized source-grounded corrections address only those four records;
all revised records remain pending independent ChatGPT review. Original raw
XML was unavailable, so source passages and locators derive from frozen local
chunks and source identity metadata; this provenance limitation is disclosed
in the protected review packet. No retrieval evaluation, database access,
query-vector preflight, paid API call, or Golden v0 access occurred.

## External authoritative references checked

- NIST TREC, [Common Evaluation Measures](https://trec.nist.gov/pubs/trec22/appendices/measures.pdf): describes common cutoff-based retrieval measures and aggregate conventions. It supports explicit cutoff/denominator reporting, not any SciScope-specific evidence matching rule.
- scikit-learn, [`ndcg_score` API](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.ndcg_score.html): documents graded-label ranking and tie behavior for NDCG. NDCG is not in the accepted Person 2 protocol's mandatory metric set, so this plan does not add it.

These references were checked on 2026-11-19. No library version/license review was needed because the recommendation adds no package. No recommendation is made to change the project metric contract.

## Recommendation and limits

Implement the existing protocol directly with pure functions, versioned manifests, synthetic fixtures, and read-only integration against the accepted private retrieval core. Use independent metric oracles. Keep labels 2/3 binary-relevant for the established metrics; do not introduce graded gain absent a reviewed requirement. Use macro-by-question aggregates and show denominators; do not pool all references across unequal questions. Treat the five development cases as smoke only. Keep the 16 v0 held-out records inaccessible until separate authorization and all partition/curation gates pass.

The dataset's size and coverage limit inferential claims. Golden v0 held-out and Golden v1 held-out remain separate cohorts; a 22-item optional pooled descriptive aggregate does not become more representative or independent merely by size. The eight development questions are never in held-out results. Nine v1 records provide scenario coverage but cannot substantiate strong per-functionality performance. ChatGPT review is a model review, not human verification. The v1 P2 artifact is internal evaluation-only under its `in_review` status, not a shared human-verified release. Exposure/contamination discovered in a protected cohort must be disclosed and excluded from independent held-out claims without score-based replacement.

## Unresolved decisions

- User approval of the complete Phase D plan and separate implementation authorization remain pre-implementation gates. After approval, routine implementation, debugging, tests, static checks, read-only verification, fixes/reruns, and evidence recording are executed autonomously; user review and final acceptance do not require command reruns.
- Fresh-context ChatGPT approval of every v1 record followed by separate explicit user continuation authorization is a hard post-generation gate.
- Separate held-out evaluation authorization, compatible query vector readiness, and exact read-only database/corpus preflight remain required before real evaluation.
- Source coverage/answerability must be measured against actual frozen corpus evidence; if nine questions cannot genuinely cover all four functions, report the exact gap and request user approval to expand.
- A positive and insufficient-evidence answerability rubric scoped to corpus version/content coverage; repository docs do not define an objective v1 rubric.
- No external team-member approval is required for internal P2 curation or sidecar work. ChatGPT review must be recorded accurately as AI review, not human verification.
- Actual local query-cache availability/provenance remains unknown because cache contents were not inspected. The existing source has only a passage-cache format; any reuse needs a manifest that binds query identity/config. If vectors are missing, the dense/hybrid arms stop until separate paid-generation approval, exact cost/call estimate, and hard cap.
- False-support rate needs separate blinded human adjudication. Without it, report NOT COMPUTED; this does not block other retrieval metrics.
- Two distinct authorizations after config/partitions freeze and T004/user continuation: first protected-cohort question/vector preflight only; second final held-out retrieval after preflight readiness. T004 v1 source review is the sole narrowly scoped pre-evaluation access exception; it supplies no retrieval-tuning input. v0 held-out remains sealed until the final evaluation authorization.
- User's explicit approval of this complete plan and implementation authorization; later continuation and held-out authorization remain distinct gates.

## Repository inspection boundaries

Planning inspected project governance, specs, Phase A/B/C evidence, source/test filenames and relevant evaluation/embedding/cache/retrieval code, evaluation protocol, Golden schema/README, and TODO/evidence metadata. It did not open `evals/golden_questions.v0.json` or any held-out question content, inspect cache contents or `.env` values, generate questions, execute tests/evaluations, connect to a database, or call a paid API.

## T005/T006 execution update (2026-11-20)

The user authorized and T005 generated the missing query vectors for both
protected cohorts; the exact cache is now verified and Git-ignored. T006 was
subsequently authorized for read-only retrieval on `sciscope_test_005` with
the frozen dense, lexical, and hybrid arms. Local code inspection found that
the repository's private `_RetrievalCore` already implements these exact arms
and enforces read-only repeatable-read transactions, but the Phase D CLI only
validates approvals and does not execute evaluation. Three approaches were
considered: reuse the private core behind an evaluation-only orchestration
module; add/change a shared retrieval facade; or write an independent SQL
retriever. Reusing the private core preserves accepted ranking behavior and
avoids shared-contract changes or duplicated SQL semantics, so it is selected.
No new dependency is needed. The residual limitation is that each retrieval
request creates a separate read-only snapshot; the runner must check the
active corpus identity before and after, and deterministic reruns must match.
No external library or service research was needed for this repository-local
adapter; only the existing interfaces, transaction guards, result model,
metric/matcher contracts, and approval validator were inspected.
