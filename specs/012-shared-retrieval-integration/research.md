# Feature 012 Research — Shared Retrieval Integration

**Status:** Finalized supporting research for the Person 3-approved Feature 012 planning package (2026-11-22). Findings do not activate a retrieval mode, approve concrete v2 HTTP changes, database access, or final feature acceptance.

**Date:** 2026-11-22
**Branch baseline:** `feature/p4-09-backend-retrieval-integration` at `7a8233bd029ba666274d8ecd902a84bfe6cf8fe6`
**Owner:** Person 3 — Backend & AI

## Problem and scope

Feature 011's accepted question backend injects a narrow question-service retrieval protocol and currently validates all dependency output as synthetic. Feature 007's accepted public retrieval facade accepts a versioned `RetrievalRequest` and returns exact retrieval results or typed sanitized exceptions. P4-09 needs an explicit adapter and composition path between these boundaries. This research is read-only; no benchmark, database connection, embedding, provider call, or test run was performed for this planning task.

## Verified repository facts

- The Feature 011 protocol is `retrieve(question: str, request_id: str) -> RetrievalOutcome`, defined in `src/sciscope/question_service/contracts.py`. `QuestionService.answer()` calls it synchronously and preserves its evidence and corpus values in question outcomes.
- Feature 011's `MockMetadata` fields are `Literal[True]`, and the HTTP `MockMetadata` fields also require literal `true`. The output validator rejects either marker unless it is exactly true. The accepted `/api/v1/questions` response has no retrieval-version or retrieval-mode field.
- The public facade is exported from `sciscope.retrieval`. It consumes `RetrievalRequest` and returns `RetrievalResponse`. Requests require an explicit `contract_version`, request ID, query text, mode, and top-k. Optional filters and ranking are immutable public DTOs.
- `RetrievalResponse` exposes contract version, request ID, corpus identity, embedding configuration, effective retrieval metadata, exact results, and warnings. Each result includes a stable chunk ID, exact text, DOI, locator, section metadata, full paper metadata, and ranking signals.
- The public error enum contains `INVALID_REQUEST`, `UNSUPPORTED_CONTRACT_VERSION`, `CORPUS_NOT_LOADED`, `EMBEDDING_CONFIGURATION_MISMATCH`, `EMBEDDING_UNAVAILABLE`, `DATABASE_UNAVAILABLE`, and `RETRIEVAL_INTERNAL_ERROR`. `RetrievalException` carries a public message, request ID, and retryable flag. The current private core marks retryability by cause for embedding/database unavailable errors; callers must preserve that value rather than infer it from the code alone.
- The public service facade is driver-independent; its private-core composition helper is separate. The question app stores injected dependencies without invoking them, and the route constructs `QuestionService` per request. No current app-factory lifecycle owns or disposes a database engine.
- Feature 011's existing success response evidence fields are `chunk_id`, `doi`, `source_locator`, `passage`, and `paper_title`; corpus identity is `delivery_digest`, `source_contract_version`, and `corpus_version`. Claims cite response-local `chunk_id` values. Validation checks membership/uniqueness, not scientific support.
- Feature 007 acceptance is limited to the public facade scope. It did not adopt `retrieval.v1` as a team-wide contract, select a Person 3 application mode, enable v2, or define real-data HTTP metadata. `retrieval.v1` remains marked proposed; Person 2 approved the v2 version boundary and behavior, while Person 3 application enablement remains pending.
- `docs/EVALUATION_PLAN.md` prescribes comparisons on the same versioned questions and relevance labels, recording dataset/corpus/configuration/filters/cutoffs/environment, with Recall@K, Evidence Hit@K, and MRR where applicable. It requires citation validity to be reported separately from citation support.

## Existing comparative evidence

Person 2's [`RETRIEVAL_V2_RESULTS.md`](../../docs/person2/RETRIEVAL_V2_RESULTS.md) records a development-only comparison run on 2026-11-20. It used the approved five-question set (`gq-sp-001`, `gq-cmp-001`, `gq-conf-001`, `gq-gap-001`, `gq-ins-001`), with four answerable questions in positive-relevance metric denominators. The recorded aggregate values are:

| Version / mode arm | Recall@5 | Recall@10 | Recall@20 | MRR@10 | Median / p95 latency (ms) |
| --- | ---: | ---: | ---: | ---: | ---: |
| v1 dense | 0.750 | 0.875 | 1.000 | 0.521 | 23.462 / 67.479 |
| v1 lexical (PostgreSQL FTS) | 0.000 | 0.000 | 0.000 | 0.000 | 131.816 / 172.981 |
| v1 hybrid (dense + FTS + RRF) | 0.750 | 0.875 | 1.000 | 0.521 | 162.734 / 197.222 |
| v2 lexical (BM25Okapi) | 0.500 | 0.750 | 0.750 | 0.417 | 69.488 / 84.646 |
| v2 hybrid (dense + BM25 + RRF) | 0.625 | 0.875 | 1.000 | 0.421 | 88.646 / 111.591 |
| v2 hybrid + MiniLM reranker | 0.625 | 0.750 | 0.875 | 0.375 | 4250.061 / 4498.784 |

The report documents exact source identity for all 1,250 returned rows across its nonempty arms. Its authors explicitly describe the five-question sample as too small and narrow for broad quality claims or reliable per-functionality comparisons; the report is development evidence, not a production guarantee. The v2 contract says dense semantics are unchanged, so a separate v2-dense behavior arm is not a distinct algorithmic alternative. The report does not include Evidence Hit@K, and no benchmark was rerun here.

The report records `sciscope_test_005`, PostgreSQL 17, pgvector 0.8.7, role `sciscope`, corpus `pilot17-xml-1fff1573b610`, and active counts of 17 papers, 319 sections, 728 chunks, and 728 embeddings. Its six arms used five repetitions per question and up to 50 final results per request; hybrid branches used pools of 50. These are values recorded in that report, not remeasured by this planning task.

**Finding:** comparative measurements exist, but they are not sufficient to call a mode a reliable overall winner. **v1 dense is the leading measured candidate** because it tied v1 hybrid on the highest measured Recall@10 (0.875) and MRR@10 (0.521), with lower median latency (23.462 ms versus 162.734 ms). This is a candidate ranking from a small development sample, not a reliable general winner and not final application activation. Activation remains gated on approved comparative evidence, a compatible explicitly configured query embedder, and explicit Person 3 acceptance. No benchmark was run for this task.

## Controlled comparison proposal

After the feature plan is approved, Person 2 should review and authorize one fixed comparison protocol using only the five approved development smoke questions. Do not inspect or tune against the other 16 Golden v0 questions.

1. Freeze and record the exact question dataset version, corpus version, active snapshot identity, and accepted relevance labels.
2. Compare the distinct available behaviors: v1 dense, lexical, and hybrid; v2 lexical and hybrid. Record v2 dense as behaviorally equivalent to v1 dense per the v2 contract rather than counting it as an independent algorithm.
3. Use identical query text, filters, top-k cutoffs, candidate-pool settings where applicable, repeated-run count, environment, and evaluation code. Dense/hybrid arms require an explicitly named compatible query embedder/configuration; do not silently generate or assume vectors.
4. Report Recall@5/10/20 and Evidence Hit@5/10/20 per question and aggregate; report MRR@10 only for questions with positive relevant evidence. Keep the insufficient-evidence question out of positive relevance denominators and do not interpret empty retrieval as scientific insufficiency.
5. Record median and p95 retrieval latency, deterministic ordered IDs across repeated requests, and exact provenance resolution for every returned hit (chunk ID, DOI, locator, exact text, and corpus identity). Treat latency and ranking scores as observations, not confidence.
6. Preserve all arms and failures. Person 2 reviews the results and approves whether they support an application selection. If no arm is sufficiently justified, keep application selection pending and require an explicit configuration without an implicit default.

This proposal is not an approved benchmark run or selection rule. The fixed five-question set is a smoke/development sample and cannot support statistical or generalization claims.

## Approaches considered

| Approach | Facts and trade-offs | Assessment |
| --- | --- | --- |
| Inject a small adapter implementing the existing question retrieval protocol and depending only on the public facade | Preserves the accepted question-service boundary; keeps private core and database details out of API DTOs; gives one place to define request settings, mapping, and typed-error translation. Requires explicit version/mode/settings and metadata decisions. | **Recommended draft direction**, subject to Person 2 and Person 4 review. |
| Put retrieval request construction and result mapping directly in the FastAPI route | Avoids a module but mixes HTTP concerns, version/mode settings, retrieval DTOs, and evidence mapping in one route; harder to exercise as a pure offline adapter. | Less isolated; no current contract requires it. |
| Replace the question-service protocol with the public `RetrievalService` request/response types | Removes an adapter but couples the Feature 011 service and API contracts directly to retrieval-owned DTOs, makes the retrieval facade's richer surface leak inward, and complicates fake-only compatibility. | Not recommended absent owner approval for a contract rewrite. |

For lifecycle, FastAPI's official documentation describes lifespan handlers as a place to manage shared resources over an application lifetime. SQLAlchemy's official Engine documentation describes an Engine as a long-lived pool registry and says `Engine.dispose()` is appropriate when the application/test is finished with it; it cautions to return checked-out connections first. These facts support making ownership explicit, but do not decide which SciScope composition root owns the engine.

## Authoritative external references

- FastAPI, [Lifespan Events](https://fastapi.tiangolo.com/advanced/events/): startup/shutdown resource-lifetime mechanism. Accessed 2026-11-22.
- SQLAlchemy 2.0, [Working with Engines and Connections — Engine Disposal](https://docs.sqlalchemy.org/en/20/core/connections.html#engine-disposal): Engine lifetime and disposal behavior. Accessed 2026-11-22.
- Repository evaluation protocol: [`docs/EVALUATION_PLAN.md`](../../docs/EVALUATION_PLAN.md).
- Person 2 comparison and limitations: [`docs/person2/RETRIEVAL_V2_RESULTS.md`](../../docs/person2/RETRIEVAL_V2_RESULTS.md).
- Retrieval contracts: [`docs/contracts/retrieval-v1.md`](../../docs/contracts/retrieval-v1.md) and [`docs/contracts/retrieval-v2.md`](../../docs/contracts/retrieval-v2.md).

No new dependency is recommended. The research scope did not verify deployment behavior, the frontend's tolerance of additive response fields, database connection settings, or a production query embedder.

## Delegation and D012 decision record — design adopted, validation gates remain

**Owner-reported delegation (2026-11-22):** Person 2 (Retrieval) and Person 4 (Frontend) told the Person 3 owner that Person 3 may make technical choices within this feature, provided the solution is correct and any retrieval version/mode is selected using the best available measured results. This records delegated decision authority only. No specific implementation or test result was reviewed or approved by either person. Person 3 is responsible for validation and approval. Required affected-owner reviews of concrete contract changes and results remain separate gates.

- **D012-01 — Retrieval candidate:** Adopt `retrieval.v1` + `dense` as the leading measured candidate based on the existing Person 2 comparison. Do not claim a reliable general winner or activate it as the final application setting yet. Final activation requires approved comparative evidence, an explicitly configured compatible query embedder, and explicit Person 3 acceptance. `retrieval.v1` + `lexical` may be used only for a separately authorized PostgreSQL wiring smoke test; it is not the application default. No implicit mode fallback is allowed.
- **D012-02 — Metadata:** Adopt component-origin metadata for retrieval and answer provider, with test-data/environment status represented separately. Verify existing DTO validators and frontend compatibility before choosing wire fields. Preserve the exact accepted Feature 011 fake-only values and behavior. If additive fields are incompatible with strict clients, document and approve a separately versioned HTTP contract; do not silently break `/api/v1/questions`.
- **D012-03 — Errors:** Adopt the draft sanitized mapping where compatible with existing contracts. Preserve typed retryability. Caller-controlled invalid input may retain caller-validation behavior; server-owned invalid retrieval version/mode/configuration maps to an internal/server failure, not caller `422`. Never expose private exception details. Verify exact public status/code compatibility before implementation.
- **D012-04 — Lifecycle:** Use explicit composition-root ownership. The creator owns and disposes the Engine after its checked-out connections are returned. An adapter does not dispose a borrowed Engine. Import, app construction, and fake-only paths perform no implicit database/provider initialization.
- **D012-05 — Provenance:** Preserve exact stable source identifiers, DOI, locator, passage text, title, delivery digest, source-contract version, and corpus version; do not reinterpret or synthesize data. Request Person 1 review only if the source meaning or upstream source contract changes.

These are documented design decisions supporting the Person 3-approved specification and plan. They do not approve concrete implementation/test outcomes, v2 HTTP changes, database access, final mode activation, or final human feature acceptance.

## 2026-11-22 contract-compatibility correction

The final read-only compatibility audit found that Feature 011's HTTP Pydantic
models are strict and closed (`extra="forbid"`), `MockMetadata` requires both
flags to be literal `true`, and the route/test suite assert the exact v1 JSON
key set. No frontend source or tests are present in this repository to establish
tolerance for additive fields. The smallest safe direction is therefore to
preserve `POST /api/v1/questions` exactly for fake-only behavior and propose a
new `POST /api/v2/questions` contract for real-retrieval integration. This path
and its `api_version: "v2"` envelope follow the repository's existing path-plus-
envelope versioning convention; they are a DRAFT proposal requiring explicit
approval before implementation.

The audit also found that a truthful real-retrieval adapter cannot precede
internal metadata foundations: the current question-service `RetrievalOutcome`
accepts only literal-true fake metadata and its validator rejects false values.
The plan therefore orders internal metadata/validation before the public
retrieval adapter. The existing `_compose_private_executor` is a private
test/composition helper and is not an approved production API. A later explicit
composition-root dependency must construct and inject the exported public
`RetrievalService` without importing private retrieval-core types in the
question adapter.
