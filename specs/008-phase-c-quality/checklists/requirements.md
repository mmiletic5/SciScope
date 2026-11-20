# Requirements Quality Checklist: Phase C Retrieval Quality and Evidence Selection

**Purpose**: Review completeness, precision, and testability of Phase C requirements.  
**Created**: 2026-11-19  
**Feature**: [spec.md](../spec.md)

**Review Ownership**: Reviewer-owned requirements-quality checklist. Mark `[x]` only when that quality criterion has been reviewed and satisfied; it does not signify implementation completion.

## Scope and preservation

- [ ] CHK001 Are accepted Phase A/B behavior, schema, pilot counts, and evidence explicitly preserved? [Completeness, Spec FR-001/FR-016]
- [ ] CHK002 Is reuse of Phase B retrieval and RRF explicit, with no duplicate ranking/fusion logic? [Consistency, Spec FR-001/FR-003]
- [ ] CHK003 Are public facade/shared contract, migrations, and held-out Golden questions clearly outside the approved scope? [Scope, Spec FR-007/FR-015/FR-016]

## Ranking and reranking

- [ ] CHK004 Is exact duplicate evidence identity precise, deterministic, and limited to fields already returned by Phase B? [Clarity, Spec FR-002]
- [ ] CHK005 Are representative choice, total tie order, diversity position, cap, configuration bounds, and exclusion reason deterministic? [Measurability, Spec FR-003/FR-004]
- [ ] CHK006 Are reranker input/output identity, score validation, ordering, failure, default-disabled behavior, and no-fallback behavior specified? [Completeness, Spec FR-005]
- [ ] CHK007 Are model source, immutable revision/hash, offline behavior, package isolation, same-candidate comparison, metrics and limitations defined? [Reproducibility, Spec FR-006/FR-008]
- [ ] CHK008 Are the quality and latency gates measurable, declared before the run, and separated from production approval? [Clarity, Spec FR-009]
- [ ] CHK009 Is the five-question development subset fixed and the 16-question holdout protected from access and tuning? [Scope, Spec FR-007]

## Context and evidence lookup

- [ ] CHK010 Is the downstream tokenizer identity explicit and distinct from the pilot byte-based estimate? [Correctness, Spec FR-010]
- [ ] CHK011 Are greedy ordering, whole-passage fit, skip/continue, exact totals, omission reporting, zero budget, and no truncation testable? [Edge cases, Spec FR-011]
- [ ] CHK012 Are DOI, exact opaque locator, span locator, and exact chunk lookup interfaces and cardinalities specified? [Completeness, Spec FR-012/FR-014]
- [ ] CHK013 Does every successful lookup carry one active snapshot's identity and define stale/not-found behavior? [Provenance, Spec FR-013]

## Environment, testing, approval

- [ ] CHK014 Are Windows PowerShell, Python 3.12/uv, `sciscope_test_005`, no-migration, no-paid-call, and non-destructive boundaries explicit? [Constraints, Spec FR-016]
- [ ] CHK015 Are RED-before-GREEN tests and independent oracles defined for every component? [Verification, Spec FR-017]
- [ ] CHK016 Are model availability and exact tokenizer/shared-contract owners identified as dependencies rather than assumed approved? [Dependencies, Spec Assumptions]
- [ ] CHK017 Are task completion, evidence recording, independent user verification, and explicit acceptance gates unambiguous? [Acceptance, Spec FR-018/SC-009]

## Notes

- Current items remain unchecked because this artifact is presented at the planning review checkpoint.
- Resolve any unsatisfied criterion before feature implementation approval.
