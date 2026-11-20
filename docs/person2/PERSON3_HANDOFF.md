# Person 3 Handoff: Golden v1 Functionality Annotations

**Status:** Annotation-contract handoff plus retrieval-only evaluation evidence.
T006 completed for both held-out cohorts. No generated-answer or functionality
output-quality evaluation was run or is claimed.

## Contract and provenance

Golden v1 functionality labels are stored in a separately versioned sidecar
conforming to `evals/golden_functionality_annotations.schema.json`. The
unchanged shared question schema remains
`evals/golden_questions.schema.json`. The sidecar is a Person 2 artifact and
does not create or change a shared contract. Golden v1 question content and
the complete sidecar remain in Git-ignored protected storage.

The sidecar root uses `schema_version: golden-functionality-v1` and an
`annotations` array. Each annotation has one `question_id`, a nonempty unique
`functionalities` list, a `primary_functionality` that is also in that list,
and a structured `expected_output`. Validation requires exact one-to-one
question-ID referential integrity with Golden v1. Field meanings and current
validation rules are implemented in `src/sciscope/evaluation/golden.py`.

## Expected output structures

- **Research Question Explorer**: `claim_evidence_links` maps each `claim_id`
  to one or more `evidence_reference_ids`; `expected_disposition` is `answer`,
  `qualify`, or `abstain`. An `answer` requires claim/evidence links.
- **Evidence Comparison**: `paper_comparisons` contains at least two papers;
  each has DOI, objective, methods, conditions, outcomes, limitations, and
  evidence-reference IDs.
- **Conflicting Evidence Finder**: `contrasted_findings` identifies source
  papers and evidence links; `methodological_explanations` labels each
  explanation `source_supported`, `plausible_but_unverified`, or `unknown`.
  `conflict_assessment` records the relationship, decision, negative-control
  status, rationale, and supporting references. Q4 and Q5 are false-conflict
  negative controls. They must reject apparent/non-equivalent comparisons;
  they are not genuine-conflict examples and provide no sensitivity estimate.
- **Research Gap & Hypothesis Assistant**: `gap_statement`, `gap_scope`,
  `supporting_evidence_ids`, `candidate_research_question`,
  `candidate_hypothesis`, `assumptions`, `uncertainties`, and
  `evidence_needed_to_test` preserve the distinction between observed evidence
  and a proposed, unverified hypothesis.

## Citation and evidence linking

Every expected claim or comparison must link to stable Golden evidence
reference IDs. A reference resolves to a DOI, section/chunk locator, and
source-grounded passage in the protected source packet. Preserve the reference
ID and locator together; do not substitute transient database chunk IDs for
source locators. Model answers should cite the evidence units that support each
claim and distinguish supported findings from hypotheses or plausible but
unverified explanations.

Illustrative synthetic mapping only (not a Golden record):

```json
{
  "claim_evidence_links": [
    {"claim_id": "claim-example-1", "evidence_reference_ids": ["evidence-example-1"]}
  ],
  "expected_disposition": "answer"
}
```

## Suggested integration and validation

1. Load the sidecar only when its version and dataset identity match the
   corresponding Golden v1 metadata.
2. Validate unique question IDs and exact one-to-one referential integrity
   before joining annotations to model outputs.
3. Keep retrieval ground truth/Recall@K, Evidence Hit@K, and MRR@K separate from
   generated-answer correctness, citation faithfulness, comparison quality,
   conflict reasoning, and hypothesis quality.
4. Test citations against referenced evidence units, missing IDs, duplicate
   functionality tags, malformed expected-output objects, and unsupported
   claim/evidence links using synthetic fixtures.
5. Report output-quality judgments with their own preregistered rubric and
   reviewers. The current Person 2 retrieval results do not provide those
   judgments.

A Git-ignored v1 functionality-stratified retrieval summary is available at
evals/results/phase_d_v1_functionality_summaries.json. It reuses retrieval
metrics only, is descriptive at n=6, has overlapping functionality strata,
and must not be treated as a functionality-quality benchmark or statistical
comparison. Golden v1 Q4/Q5 are false-conflict negative controls; no genuine
conflict sensitivity result is available.

No shared schema or Person 3 code was changed. Any proposed shared adoption is
an integration proposal, not an accepted contract change. This handoff does
not require Person 3 approval for internal Person 2 completion.

## T008 lexical/hybrid diagnostic

Source-grounded read-only probes on `sciscope_test_005` confirmed expected
candidate retrieval for exact terms, an acronym, a methods term, and named
entities. A broad numeric-only probe placed its source chunk at rank 31, past
top 20; a composed cross-source natural-language query returned no lexical
candidates because English `websearch_to_tsquery` requires all positive
lexemes in one chunk. These are synthetic/public-corpus diagnostics, not
Golden or held-out results. RRF unit tests confirm dense-only, lexical-only,
and overlapping branch members are deterministically unioned/fused. The
protected reports do not expose enough detail to attribute held-out lexical
zero Recall to a specific mechanism.

The owner reports independent ChatGPT recomputation of the cohort macro
retrieval metrics matched per-question results. Small cohort sizes, no human
Golden v1 verification, unavailable original XML, no genuine-conflict
sensitivity measurement, and the partial cold/warm/stage latency criterion
(AC-038) remain limitations. See
`docs/person2/PHASE_D_T008_ACCEPTANCE_SUMMARY.md`.
