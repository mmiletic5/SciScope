# Corpus Requirements Checklist: Honeybee Corpus Discovery & Pilot Selection

**Purpose**: Reviewer-owned check of scientific selection, provenance, contract, and evaluation requirements
**Created**: 2026-11-14
**Feature**: [spec.md](../spec.md)
**Review Ownership**: `[x]` means a human reviewer judged requirements quality sufficient; it does not mean curation or implementation is complete. Automated document-consistency checks may be reported separately but do not mark these boxes or establish scientific validity.

## Scientific eligibility

- [ ] CHK001 Are direct, conditional comparative, generic mention, and other-species-only outcomes defined with evidence thresholds?
- [ ] CHK002 Are primary research, a small separately labeled review minority, corrections, editorials, front matter, and inaccessible full text treated explicitly without treating reviews as original experimental evidence?
- [ ] CHK003 Are ambiguity and contradictory species evidence handled without automatic inclusion?

## Reproducibility and provenance

- [ ] CHK004 Are exact query fields, Boolean strings, sort, pages, dates, and index-drift records required?
- [ ] CHK005 Are DOI wrapper, one-time URI decoding, ASCII-only case, original-identifier preservation, duplicate, missing, and conflict rules sufficient to identify unique papers?
- [ ] CHK006 Are individual JATS and article-level license checks required before processing-ready status?
- [ ] CHK007 Are unknown and failed source metadata states distinct from verified values?
- [ ] CHK008 Is the first approximately 3–5-paper inspected sample explicitly included in the complete target of 20 eligible, unique papers, with source-supported diversity, shortfall handling, and no automatic scale-up?

## Shared handoff and evaluation

- [ ] CHK009 Is the lightweight screening manifest clearly distinct from the processed Paper → Section → Chunk contract?
- [ ] CHK010 Are field-level contract gaps and Person 2 approval requirements explicit?
- [ ] CHK011 Are DOI, original section path, JATS `@id` or a pinned-XML structural fallback, and source checksum/version required for future golden evidence when chunk IDs change?
- [ ] CHK012 Are the 5–10-question follow-up and Person 2 evaluation dependency stated without fabricated findings?

## Verification readiness

- [ ] CHK013 Are positive, negative, missing-data, absent-XML-ID, index-drift, and bounded PLOS connectivity/JATS failure cases specified?
- [ ] CHK014 Are pre-execution feature-owner approval of spec/plan/tasks, dependent TEAM and Person 2 decisions, and separate post-execution human acceptance stated with the correct task order?

## Notes

All 14 items remain unchecked for human requirements-quality review. The built-in `requirements.md` records a separate agent writing-quality self-check. A passing mapping or markdown check only establishes internal document consistency; scientific eligibility, source verification, contract agreement, and implementation approval require actual human decisions. No implementation, corpus, or human acceptance is claimed.
