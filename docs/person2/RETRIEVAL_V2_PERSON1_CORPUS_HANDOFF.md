# Person 1 handoff: versioned scientific-structure corpus expansion

**Status:** future-improvement proposal only. Person 2 did not modify Person 1 code, source data, the frozen corpus, embeddings, database, or shared delivery contracts. Implementation requires a separately scoped Person 1 ingestion change and independent source-level validation.

## Executive handoff

The frozen pilot currently retrieves paragraph chunks. The current parser and chunking reports confirm that tables, figures, formulas, lists, and supplementary-material elements are omitted from paragraph evidence. This did not explain any of the six annotated positive evidence misses examined in the five-question diagnostic: all six passages were present, locator-matched, and fit in a single chunk. It remains a credible coverage risk for other scientific queries, particularly queries whose answer is encoded only in a table, formula, caption, or supplement. The original raw XML is unavailable in the current workspace, so this review could not reparse or independently check individual omitted elements.

## Verified implementation behavior

Read-only inspection covered `src/sciscope/jats/parser.py`, `src/sciscope/jats/locator.py`, `src/sciscope/chunking/core.py`, `src/sciscope/chunking/output.py`, `src/sciscope/chunking/report.py`, and `src/sciscope/chunking/validate.py`.

- `jats.parser.INLINE_KINDS` recurses through italic, bold, xref, external-link, named-content, email, subscript, and superscript elements. Their text remains in the containing paragraph. Other child elements encountered inside a paragraph are omitted as whole subtrees and their element kind is recorded; the parser retains the child's tail text.
- At section/body level, the parser emits direct paragraphs and recurses into sections. Other child structures are counted as skipped and are not traversed into paragraph records. A skipped parent such as a figure or table therefore also hides nested caption, cell, label, and footnote text from paragraph chunking.
- The supported chunk kind is explicitly `paragraph`. Chunking is based on source paragraph spans and records source locators, offsets, section paths, hashes, and omission-kind summaries. It does not emit structured non-paragraph chunks.
- Formula elements are not inline kinds: `inline-formula` and `disp-formula` content is omitted. Lists, figures, table-wrap elements, supplementary material, and boxed text are also explicit exclusions. Unknown non-paragraph child kinds are skipped and can produce parser warnings.
- Only the primary abstract without an `abstract-type` attribute is selected for abstract parsing. Alternate typed abstracts are not represented as abstract paragraphs by this path.
- Back-matter reference, acknowledgement, appendix, note, footnote-group, and glossary containers are recorded by kind, but their contents are not emitted as evidence paragraphs.

## Omission counts from existing artifacts

Reliable local counts are available in the existing pilot `parse_report.json` and `chunk_report.json`; the delivery manifest contains the exact hashes of these reports. They describe 17 papers and match the pilot delivery's 17-paper, 319-section, 728-chunk identity. Counts below are skipped JATS element occurrences under the parser's outer-skip accounting, not counts of unique scientific claims or distinct missing facts.

| Omitted structure | Count in existing report | Interpretation |
|---|---:|---|
| Figure (`fig`) | 82 | Figure elements omitted; nested caption/graphic material is not emitted as paragraph evidence. |
| Table (`table-wrap`) | 39 | Table-wrap elements omitted, including table caption/body structures. |
| Formula (`disp-formula` + `inline-formula`) | 10 | Nine display-formula and one inline-formula elements omitted. |
| List (`list`) | 1 | List subtree omitted. |
| Supplementary material | 91 | Supplementary-material elements omitted; these may include non-text assets and do not imply 91 missing answer passages. |
| Boxed text | 0 observed | Explicitly excluded by policy; no such element was counted in these local reports. |
| Other/unlisted child kinds | 0 reported | The chunk report's unlisted-kind aggregate is empty for this pilot. |

The reported total is 223 omitted elements in the five counted categories. Nine paragraph records contained omitted child elements. The parser and chunk report do not measure omitted text volume, table-cell count, figure-caption word count, supplement scientific relevance, or how many omissions affect any query; those counts are unavailable. Back-matter counts in the chunk report represent container presence categories, not counts of all nested elements.

Report provenance:

- `data/pilot/parse_report.json` SHA-256: `3bd0a61310edf49fe00ecf9c31489110197c80e786ad9c5333d7ecdf0a63b426`
- `data/pilot/chunk_report.json` SHA-256: `475aba74cf677e8cdd7cba44707dccf3124adcca36ff57e0de5fac0dd272fd6b`
- `data/pilot/delivery_manifest.json` SHA-256: `998241789fd9675853962bdfdf98b15b0991bc4cda103413b0abc470666af9d2`

## Scientific risks (plausible, not observed causes)

- **Numerical-result questions:** exact values, denominators, units, uncertainty intervals, and subgroup results may occur only in table cells, footnotes, or figures. Missing them can make a correct answer unretrievable or leave a value without its unit/condition.
- **Study comparisons:** outcome and condition matrices may be tabular; omitting header paths, footnotes, or captions can obscure which value belongs to which method, treatment, time point, or population.
- **Conflicting findings:** the apparent direction or magnitude of a result can depend on table strata, figure panels, assay definitions, or confidence intervals. Missing these structures can hide a real difference or create an apparent one from incomplete context.
- **Mathematical questions:** formula statements, symbols, subscripts, operators, and definitions may be absent. Flattening MathML to plain text could also change meaning.
- **Research-gap analysis:** limitations, negative/null results, subgroup boundaries, and caveats may occur in tables, figures, appendices, or supplements. Missing them can make an asserted gap too broad.
- **Provenance:** current paragraph locators cannot cite a table cell, list item, formula, or figure panel that was never represented. A citation to a surrounding paragraph must not be used to imply that an absent structure was inspected.

These are coverage risks implied by the implementation and literature document formats. The current evidence does not show that they caused the diagnosed retrieval failures.

## Proposed versioned ingestion extension

### Version boundary and storage model

Create a separate ingestion/corpus version, provisionally named `jats-structured-v1`, and a new immutable pilot corpus identity, provisionally `pilot17-jats-structured-v1`. Names are proposals; the ingestion builder should derive and record the final corpus digest. Never overwrite `pilot17-xml-1fff1573b610`, embedding set 115, existing chunk IDs, existing delivery files, Golden records, or reports. Assign new stable element IDs from a versioned canonical tuple containing source XML SHA-256, exact JATS locator, element kind, and extraction-schema version.

For initial prototyping, prefer a separately versioned structured-evidence sidecar over changing the existing shared paragraph/chunk record shape. The proposal does not alter the current shared delivery contract. Any eventual public-contract change requires explicit cross-owner review before adoption.

Each sidecar record should include at least:

- Immutable paper identity (normalized DOI), source XML SHA-256, source URL/retrieval manifest identity, parser version/source revision, extraction schema version, and record SHA-256.
- Stable element ID, exact `jats:v1` source locator, parent locator, section ID/path, element type, sibling/order indices, and source offsets where the source mapping supports them.
- Exact source text or a faithful structured representation plus the original serialized XML fragment hash. Do not replace source text with a generated summary.
- Any derived searchable/normalized representation separately stored and labeled with the deterministic transformation/version; preserve the original source form unchanged.

### Structure-specific extraction rules

1. **Tables:** retain table-wrap locator, label, exact caption, table group, row and cell order, row/column header paths, spans (`rowspan`/`colspan`), cell text, units, footnote markers, and links to footnote source locators. Store a faithful structured matrix and the original XML-fragment hash. Optional parsed numeric value/unit fields must be additive, deterministic, reversible to raw cell text, and rejected when parsing is ambiguous. Never infer missing headers, units, or statistical meaning.
2. **Lists:** retain list type, parent locator, nesting level, item order/labels, exact item text, section path, and each item's locator. Keep list-item records separate while preserving parent/list relationships.
3. **Inline and display formulas:** retain the containing paragraph relationship and exact MathML/TeX/XML source representation with formula locator and inline/display type. Index any canonical token string as a separate derived field. Do not silently convert symbols, operators, subscripts, or equations to natural-language claims.
4. **Figure captions and references:** retain exact caption, label, figure locator, graphic asset URI/hash when legally available, and all source cross-reference IDs/locators. A caption is source text; it must not be conflated with interpretation of the plotted image.
5. **Figure-derived information:** keep optional OCR or plot/table extraction in a separately versioned derived artifact keyed by source asset hash and figure locator, recording tool/model/version, parameters, raw output, and validation status. Do not run an image model or add dependencies as part of this proposal. Accept a derived value only when the axis/legend/panel mapping is reproducible and independently checked; otherwise mark it unavailable. Never turn an inferred curve value into an exact source-reported number.
6. **Supplementary material:** record the exact available manifest, file name/type, checksum, and source relation. Parse only formats with a declared deterministic extractor and validated locator mapping; retain a status for files not parsed. Do not assume each listed supplement contains scientific evidence.

Structured retrieval text should be generated by a separately versioned template that includes element type, section heading, table headers/units or list hierarchy, and exact source text. Keep each structured unit's original locator and unit context intact. Use a new embedding manifest/set for any new passage inputs; existing vectors are incompatible with changed text and must never be relabeled or reused for new units.

## Reproducible comparison and acceptance plan

1. **Freeze inputs:** acquire the exact raw XML set, verify each byte hash against an immutable manifest, record source licenses/URLs and repository revision, and record the current paragraph-only manifest hashes as the control. Fail closed on a missing or mismatched source file.
2. **Extraction fidelity:** create fixture tests for tables with multi-level headers, merged cells, units, footnotes, nested lists, inline/display MathML, captions with xrefs, supplementary relations, Unicode, and malformed/unsupported constructs. Verify exact source round-trip or documented faithful structure, stable locators/IDs, deterministic repeated output, no dropped cell/item/formula text, and explicit unsupported status. Independently inspect a stratified sample against raw XML, including numeric values and units.
3. **Corpus integrity:** validate the new sidecar schema, unique IDs, DOI/source-hash consistency, parent-child locators, ordering, stable text hashes, parser provenance, element-kind counts, and exact manifest/file hashes. Preserve the paragraph corpus as a byte-identical baseline and prove the new import is a separate immutable version.
4. **Evaluation preregistration:** before retrieval runs, freeze question wording, answerability scope, development/test partitions, retrieval arms, candidate pool, metrics, latency procedure, and decision rules. Add source-grounded questions whose necessary evidence is known to occur in paragraphs, tables, lists, formulas, captions, figures, and supplements, plus controls where the requested evidence is genuinely outside the corpus. Obtain independently reviewed, complete-enough evidence annotations with required evidence groups, locators, exact cell/item/formula references, relevant alternatives, and known distractors.
5. **Matched corpus comparison:** run the same preregistered development questions and unchanged retriever configuration against the existing paragraph-only corpus and the new structured corpus. Use the same embedding model/configuration for comparable passage types. New document vectors must be generated under explicit approval and a recorded cost cap if a paid provider is used; do not call APIs under this proposal. Do not tune on the sealed test partition.
6. **Retrieval metrics:** report per-question and stratified Recall@5/10/20, Evidence Coverage@5/10/20, All-Required-Evidence@5/10/20, Required-Source Coverage, MRR@10, nDCG@10, corpus coverage (whether required units exist in that corpus version), source coverage, and latency. Report undefined denominators explicitly. Keep comparison-side coverage and conflict-side coverage separate; only calculate them where the gold annotation explicitly defines all necessary sides. Insufficient-evidence retrieval behavior is descriptive and cannot prove literature-wide absence.
7. **Citation and numeric fidelity:** for every returned structured item, resolve stable ID to exact DOI/title, XML hash, element kind, locator, and source fragment. Verify exact cell/unit/formula/caption traceability. On numerically grounded cases, compare retrieved raw value, sign, precision, unit, denominator, and condition with the source cell/figure annotation; reject any transformation that changes them. Include negative controls for plausible but unsupported numeric statements. Retrieval does not guarantee generated answers are factual; Person 3 must separately test claim entailment and abstention.
8. **Immutability and release gate:** compare pre/post hashes and row counts for the frozen delivery and `sciscope_test_005`; no migration or write is permitted during corpus extraction validation. Accept a new corpus only after independent extraction review, reproducible retrieval evidence, leakage checks, and cross-owner interface review. Keep old/new corpus results separate and preserve all prior phase evidence.

### Proposed acceptance criteria

- Every extracted item resolves to an exact source paper and valid XML locator; every source fragment hash is reproducible.
- Tables preserve cell/header/units/footnotes relationships; lists preserve order/nesting; formulas preserve exact source notation; captions remain distinct from figure-derived interpretations.
- No numerical value is emitted as source-derived unless it maps to exact source text/cell/figure coordinates and retains units/conditions; ambiguous extraction fails closed.
- New corpus/embedding manifests are complete and distinct; current pilot files and set 115 remain byte- and identity-stable.
- Expanded-corpus gains are reported against the paragraph-only control with pre-frozen questions and metrics, including regressions and cases where source evidence remains unavailable.
- Person 3 can cite every retrieved structured result using stable IDs and source locators, while answer-level evaluation separately tests factual support and abstention.

## Ownership, approval, and next action

- **Confirmed current behavior:** existing parser/chunker policy and local pilot omission counts documented above.
- **Plausible risk:** important evidence may be present only in omitted structures; no observed miss has been attributed to this yet.
- **Proposed change:** a new versioned structured-evidence sidecar and corpus/embedding set, with source-exact provenance and a matched evaluation.
- **Person 1 work:** implement and independently validate extraction, schema/versioning, deterministic serialization, source locators, and new corpus/embedding build in a separate authorized scope.
- **Person 2 work:** define retrieval integration and evaluation only after the source records and interface are concrete; preserve a baseline comparison and verify source resolution.
- **Person 3 work:** review how structured results will be cited and separately validate answer-claim support/abstention. No generation code or Person 3 interface is changed here.
- **Approval gates:** corpus/schema/shared-contract changes, any database import/migration, regenerated paid embeddings, new model/dependency, and any protected held-out evaluation require their own authorization under project policy. This handoff itself is not an implementation approval.

Immediate Person 1 action: assess availability/licensing of the exact 17 raw XML files and table/figure/supplement asset hashes. If the source package cannot be recovered with matching hashes, stop before extraction and report the missing provenance rather than substituting newer article versions.
