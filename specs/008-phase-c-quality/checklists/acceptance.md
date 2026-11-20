# Phase C Implementation Acceptance Checklist

**Purpose**: Execution acceptance criteria for P3-09 through P3-12. This is distinct from the requirements-quality review in [requirements.md](requirements.md).  
**Feature**: [spec.md](../spec.md)  
**Status**: CLOSED 2026-11-19 by Person 2 owner approval after independent verification. The historical Golden v0 isolation criterion is recorded as an approved exception and remains NOT PASSED.

## P3-09 — Ranking, duplicate policy, diversity

- [x] Phase B output is consumed as-is; Phase B retrieval, filters, dense/lexical scores, and RRF are not duplicated or changed.
- [x] RED tests precede implementation and an independent oracle verifies exact DOI/primary-locator/text duplicate identity and representative selection.
- [x] No Feature 007 file, accepted query behavior, score, order, shared DTO, schema, or contract is changed.
- [x] Repeated IDs, malformed spans, score ties, reranker ties, and deterministic final ordering have explicit tested outcomes.
- [x] The approved diversity cap is applied after optional reranking and every excluded item carries a reason.
- [x] Retained candidate text, IDs, score provenance, and source metadata remain exact.

## P3-10 — Offline reranking comparison

- [x] Default behavior uses no-op reranking; the base application imports/runs without optional model packages or weights.
- [x] Reranker rejects missing/extra/duplicate IDs and non-finite scores; a requested failure is surfaced without fallback.
- [~] Benchmark used only the five approved questions. **APPROVED HISTORICAL EXCEPTION — NOT PASSED:** the initial preparation run deserialized the full Golden v0 JSON before filtering; no held-out prompt was output, manually inspected, embedded, retrieved, scored, or used for tuning. Current preparation scans bounded byte chunks and deserializes only allowlisted records. Owner approval of this documented exception is recorded in `final-audit.md` and `EVIDENCE.md`; this does not convert the original criterion into a pass.
- [x] Both arms use identical RRF candidates, filters, evidence matching, K values, corpus and snapshot identity.
- [x] Compatible five-question query vectors and Phase B hybrid RRF candidate lists were generated using the separately authorized bounded embedding request; the measured comparison is complete.
- [x] Checkpoint revision/SHA-256, dependency lock, environment, candidate hashes, command, metrics, failures, warm/cold latency, and repetition details are recorded.
- [x] With network disabled and local pinned artifacts, the benchmark reproduces results and cannot invoke a paid/remote API.
- [x] FR-009 screening thresholds are computed from observed results; production remains disabled unless separately approved.
- [x] The measured quality/latency gates failed and are reported as observed; no substitute model or invented outcome is used. MiniLM remains disabled.

## P3-11 — Context and token budget

- [x] Tests prove the exact configured counter identity is required and mismatches fail.
- [x] Whole passages are greedily considered in rank order; exact fits are included, oversized passages are skipped with reason, later smaller passages can still fit, and total never exceeds budget.
- [x] Returned text and provenance are unchanged; exact counted total, budget, counter identity, and ordered omissions are present.
- [x] Prompt/system overhead is caller-reserved; the pilot byte-based estimate is not presented as an LLM tokenizer.

## P3-12 — Evidence lookup

- [x] DOI lookup returns the matching paper or explicit not-found; DOI normalization matches accepted behavior.
- [x] DOI plus locator returns all exact primary/span locator matches in stable order without interpreting locator syntax.
- [x] Exact chunk ID lookup returns only the active snapshot's record or explicit not-found.
- [x] Successful results include active import ID, delivery digest, source contract version, and corpus version from the same read-only REPEATABLE READ snapshot.
- [x] Native PostgreSQL integration uses a preflight-confirmed `sciscope_test_005`; no main DB, schema migration, or destructive operation occurs.

## Project closure and independent acceptance

- [x] Native Windows focused and applicable regression/static checks pass; outcomes and limitations are in `EVIDENCE.md`.
- [x] Read-only pilot verification reported 17 papers, 319 sections, 728 chunks, and 728 embeddings; schema and pilot were unchanged.
- [x] `PROJECT_TODO.md` mirrors final task state following user verification and approval.
- [x] User received copy-paste-ready read-only PowerShell verification and independently reported passing output.
- [x] User provided actual independent verification output and explicit human acceptance, including approval of the documented historical exception. The isolation criterion remains explicitly not passed.
- [x] Phase C stops at this handoff; Phase D has not started.

## Approval decisions before implementation

- [x] User approves the exact DOI/primary-locator/text duplicate key and configurable diversity cap default 2, with explicit `None` disable, 2026-11-19.
- [x] User approves P3-10 no-op/fake/offline harness and optional technically feasible local MiniLM; proposed metrics are diagnostic and latency is a bounded screening cost, 2026-11-19.
- [x] User approves exact-tokenizer injection and strict downstream tokenizer identity, without hardcoding Gemini, 2026-11-19.
- [x] User approves exact DOI/locator/chunk lookup and active-snapshot read-only REPEATABLE READ semantics, 2026-11-19.
- [x] User approves the Phase C specification and plan, 2026-11-19.
