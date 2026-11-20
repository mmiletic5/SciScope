# Person 2 Retrieval Evaluation Protocol

**Status:** Approved working planning baseline. Metrics, partitions, and
cross-team review become implementation requirements only through separately
approved phase specifications and plans. No retrieval results currently exist.

**Person 2 execution constraint:** Implement and run evaluation, data loading,
retrieval, and latency workflows natively on Windows 10 x64/PowerShell. Record
Windows build, CPU, memory, PostgreSQL/pgvector versions, and relevant runtime
configuration with benchmark manifests. This records execution context only;
it does not change partitions, questions, matching rules, metrics, cutoffs, or
reporting methodology. Do not require Docker, WSL, Linux, or Bash.

## Golden v0 provenance

`evals/golden_questions.v0.json` has dataset version `v0`, corpus version
`pilot17-xml-1fff1573b610`, and 21 questions over 12 of the 17 pilot papers:
eight single-paper factual, four multi-paper comparison, three
conflicting-evidence, three research-gap, and three insufficient-evidence.

All questions were drafted by an AI assistant from pilot source papers and are
recorded as verified by Person 1 on 2026-11-18. Person 1 reported reading every
record and machine-checking all 33 quotations against source XML. These are
supplied curation facts, not an independent Person 2 scientific review. The
evaluated retrieval system did not generate its own ground truth.

Each positive reference uses DOI, section information, a short exact quotation,
and a digest-bound source locator. Ground truth is not `chunk_id`, because
chunking changes can change chunk identifiers.

## Development and held-out separation

The Phase B development smoke subset is frozen to one question per type:

- `gq-sp-001`
- `gq-cmp-001`
- `gq-conf-001`
- `gq-gap-001`
- `gq-ins-001`

It verifies loader, evidence matching, retrieval-mode wiring, and obvious
regressions. It is not a release benchmark and must not support quality claims.
The other 16 Golden v0 questions are held out from Phase B/C tuning and reserved
for Phase D reporting. This partition is planning metadata; it does not alter
or create a Golden dataset version.

Golden v1 adds nine source-grounded questions in the amended category/function
matrix: 3 insufficient-evidence, 0 genuine conflicts, 2 research-gap,
1 single-paper factual, and 3 multi-paper comparison. Q4/Q5 retain Conflict
Finder annotations as negative controls for rejecting apparent or
non-equivalent findings. The frozen 17-paper corpus contains no defensible
pair of genuinely contradictory comparable findings, so Golden v1 makes no
genuine-conflict sensitivity claim. Person 2's Phase D method allows
AI-generated/AI-assisted drafting
because the evaluation owner does not intend to manually author all nine
questions from scratch; review effort is directed to source-grounded scientific
validation. It requires full provenance and mandatory independent ChatGPT
source-based review of every question and annotation. ChatGPT approval is recorded as model review,
never human verification; after that gate, the user must explicitly authorize
continuation. The earlier independently human-authored requirement is preserved
in Phase D decision history but replaced within this Person 2 protocol. The
shared evaluation plan and constitution remain unchanged. Until governance for
those documents is updated, this is a Person 2 evaluation dataset, not a shared
human-verified Golden release. Freeze the v1 development/held-out partition
before retrieval outputs/tuning; questions do not move based on results. Preserve
Golden v0 unchanged.

The populations are fixed as follows: v0 development/smoke n=5 (previously
exposed, diagnostics only), v1 development n=3, v0 protected held-out n=16, and
v1 protected held-out n=6. The eight development cases never enter held-out
metrics. Report the two held-out cohorts separately with provenance and eligible
n. An optional pooled descriptive result over at most 22 held-out questions is
permitted only when both cohorts are fully eligible and use identical frozen
corpus/configuration/metric definitions; it is not automatically independent,
representative, or a 30-question independent test. The mandatory T004 review is
the sole pre-evaluation exposure of v1 held-out question content; it is isolated
from retrieval code/results and may only correct source-grounded records, never
retrieval behavior. v0 held-out content remains sealed until explicit final
evaluation authorization. Any discovered prior exposure is documented and the
affected item is excluded from independent held-out claims without replacement.

Schema note: `evals/golden_questions.schema.json` requires a reviewer string and
verification status and supports `in_review`; it describes reviewer identity as
human and `evals/README.md` reserves released status for human-verified data.
The internal P2 v1 record therefore truthfully records ChatGPT as an AI model
reviewer, remains `in_review`, and omits `verified_date`. A P2-only loader may use
it after the ChatGPT review sidecar says approved and the user authorizes
continuation. It is not a shared human-verified release; no schema change or
fabricated verification is permitted.

## Evidence matching

A retrieved chunk matches a labeled evidence reference when its normalized DOI
matches and at least one chunk span locator equals the evidence locator. A
controlled fallback may accept a matching labeled section plus exact quotation
containment. Section-path-only matches are weaker diagnostics and do not replace
locator/quotation matching. Relevance labels 2 and 3 count as relevant.

Multiple valid papers and evidence references remain distinct evidence units.
Tie handling follows the deterministic retrieval contract.

## Metrics

- Recall@K is retrieved relevant evidence units divided by all labeled relevant
  evidence units for the question.
- Evidence Hit@K is one when any relevant evidence unit occurs in the top K and
  zero otherwise.
- MRR is the reciprocal rank of the first relevant result only for positive
  questions where first-hit ranking is methodologically meaningful.

For each cohort/arm, macro-average per-question metrics over answerable positive
questions with valid nonempty ground truth. The Recall denominator is the number
of unique relevant evidence units for that question, not a pooled unit count;
Evidence Hit and MRR use the same eligible answerable population. Report
insufficient-evidence count/outcomes separately: positive Recall/MRR are
null/not applicable, not zero, and empty retrieval is not correct abstention.
Missing/invalid ground truth blocks that cohort rather than silently removing a
question. Report per-question, cohort, type, and functionality summaries with n,
eligible/excluded n and reasons, denominators, and nulls. Do not micro-pool
evidence units. Proposed cutoffs are 1, 3, 5, 10, and 20 when valid for the
eligible corpus. For Phase D compare exact dense, PostgreSQL lexical FTS, and
hybrid RRF using identical questions, corpus, filters, K, embeddings, and
matching rules. No reranker arm is part of Phase D; MiniLM remains disabled
after its accepted negative benchmark.

## Insufficient-evidence questions

Do not compute positive Recall or MRR when no positive reference set exists.
An absence of retrieved evidence is not automatically correct. Report these
questions separately using the number/rank of apparently answer-asserting
passages and blinded human labels `supported`, `partial`, `unsupported`, or
`uncertain`. Report a false-support rate at K only after that adjudication.
Downstream decline/qualification behavior is outside Person 2 retrieval metrics
and is described in the Person 3 handoff. Re-review negative questions whenever
corpus coverage changes.

## Latency and reproducibility

For the Phase D baseline, measure query embedding, database retrieval,
fusion/ranking, context selection, and total retrieval separately. Record warm/cold
status, repetitions, median, p95, maximum, failures, hardware/environment, and
query-embedding token/cost accounting.

Every benchmark records dataset/corpus hashes, Git revision,
PostgreSQL/pgvector versions, migration revision, delivery digest, embedding
configuration, retrieval/filter/reranker configuration, K, command,
environment, and timestamp. Repeated runs must use the same frozen inputs.

## Limitations

- Twenty-one questions over 12 papers are an indicative regression signal, not
  a statistical estimate of general retrieval quality.
- All v0 questions are AI-drafted, although recorded as human-verified.
- Current conflicting-evidence records concern author-versus-prior-literature
  conflicts inside one paper, not cross-paper conflicts.
- Insufficient-evidence records rely on lexical search plus reading and support,
  but do not prove, absence.
- Current chunks omit tables, captions, formulas, references, and supplementary
  material. All Golden evidence is from body paragraphs, not abstracts.
- Corpus expansion may make an insufficient-evidence question answerable and
  requires renewed review.
- No retrieval approach may be declared superior before the benchmark is run
  and recorded.



### Golden v1 procedural isolation amendment (approved 2026-11-20)

The owner approved procedural, reproducible isolation instead of Windows ACL changes. No ACLs, accounts, WSL, or separate environment are introduced. This is **not operating-system-enforced isolation**: the repository's inherited Windows ACL grants the Codex sandbox group Modify access, and processes sharing a Windows security identity can access the same local files. Do not describe Golden v1 as independently human-authored, OS-protected, or inaccessible to every development process.

Before question generation, freeze the retrieval/configuration/evaluator snapshot, source/corpus identities and the fixed Q-slot partition map in `docs/person2/PHASE_D_BASELINE_FREEZE.md` and the ignored protected baseline manifest. Candidate questions, answer keys, evidence annotations, source passages and review packet are stored only under `evals/protected/golden_v1_review/`, which is Git-ignored. Separate development and held-out candidate files; never copy held-out payload into tests, fixtures, debug output, tuning inputs, ordinary logs, tracked files, or retrieval code. The curation/validation workflow emits only counts, statuses and hashes to ordinary output. It must fail closed if protected paths are linked/tracked/not ignored, partition assignment differs, candidate text is found in ordinary development locations, or source/annotation validation fails. A protected review packet is for independent source review only and is not an input to retrieval development or tuning.

These are workflow controls and audit checks; they cannot prevent a process running under the same Windows account from reading accessible files. Their purpose is to keep the protected cohort out of the development/evaluation pipeline and ordinary artifacts, with contamination limitations disclosed. The v1 candidates remain `in_review`; ChatGPT review is model review, not human verification.
