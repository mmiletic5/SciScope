# F004 research: real contract and reproducible delivery

**Date**: 2026-11-17 | **Method**: solution-research before specification;
read-only repository/code/artifact inspection and official documentation.
Problem: hand Person 2 the real flat pilot with verifiable integrity and a
short reading guide. D1–D10 constrain design; research does not approve code.

## Repository facts and gaps

- Branch is 004-data-contract-delivery; initial tree clean. HEAD da22b2b.
  EVIDENCE.md records F001–F003 DONE and accepted. F003 full checks reported
  928 tests; those historical results were not rerun here.
- Read AGENTS, constitution, local skill files, prior plans, EVIDENCE/TODO,
  DATA_MODEL/CONTRACT/CHUNKING_STRATEGY/ARCHITECTURE/DECISIONS, setup/workflow,
  CI/dependency configuration and specified real writers. Existing runtime
  dependencies are empty. jsonschema is dev-only; locally installed 4.26.0.
- Committed pilot: metadata/manifest/selection each 17, screening 24,
  candidates 870 with 11 empty journals outside selected pilot. Acquired
  authors and journal are nonempty (also enforced by metadata.py). Licenses:
  11 URLs, 6 free text; subjects begin Research Article in 17/17. Dates all
  YYYY-MM-DD; language actually 4 EN, 13 en, contrary to the older evidence
  summary. Preserve raw values, impose no schema case restriction, and compare
  case-insensitively in the guide. T007 will append a correction to F001
  evidence without rewriting old text; no evidence change during planning.
- Ignored artifacts exist: 319 sections, 585 paragraphs, 728 chunks. Field
  lists match real writers, recorded in plan. 50 sections have no own
  paragraphs; recomputed paragraph_count and depth/path checks found 0
  inconsistencies. No article text or credentials were copied into artifacts.
- Reports: parse succeeded 17/failed 0; chunk counts 319 sections/269 with
  chunks/728 chunks, 2 hard splits, 0 blank paragraphs, 223 skipped elements
  and 33 back-matter exclusions. F003 report records 123740 actual aggregate
  tokens vs 188108 estimated; it does not prove per-input token fit.
- Local embedding manifest: complete, openai/text-embedding-3-small, 1536
  requested/returned, empty prefixes, embedding-set-v1. Vector size 4,472,832
  bytes; read-only unpack confirmed 728 finite rows and norm extrema rounded
  to 9 decimals 0.999368748/1.000662474, matching manifest; vector digest
  matched. This inspection is not a validate-delivery result.
- Critical ordering fact: chunk writer preserves section/ordinal order;
  embedding store/pipeline sort chunk IDs. 727/728 row/line positions differ.
  Person 1 explicitly approved manifest-entry ID mapping in this session;
  original D5 and amendment both remain in plan. Never reorder payloads.
- No parser/taxonomy version constants exist; locator has literal jats:v1;
  actual F003 identifiers are chunking-v1, utf8-bytes-div3-v1,
  embedding-text-v1. Plan proposes honest null parser version plus exact
  source hashes; taxonomy v0 is D4's supplied label. Person 1 now approves R22
  as informational provenance: check 64 lowercase hex/internal consistency,
  never compare local source files. No invented code version.
- locator_digest validates prefix/digest only; full component grammar is in
  SourceDocument.resolve. Byte/digest checking cannot prove XML traversal or
  vector semantic origin. Upstream validators use local paragraphs; consumer
  checks package relationships and reuses embedding validation, not fabricated
  paragraph reconstruction.
- Optional `data-contract-v0.2-proposal.md` is ABSENT. Reconcile against real
  artifacts and committed bootstrap draft; no claims about absent content.

## Approaches compared

| Approach | Advantages | Limits, integration and recommendation |
| --- | --- | --- |
| A. Preserve JSONL/f32, stdlib package/runtime validator, dev schema parity | Reuses current bytes, validators, atomic primitives and zero runtime dependencies | Custom structure checks can drift; shared mutation parity and separate semantic tests required. Recommended under D1/D7. Stdlib version is project Python 3.12; no third-party package/license addition. |
| B. Promote jsonschema to runtime | Established Draft 2020-12 validation, iter_errors and check_schema; less hand-maintained structural logic | Compatible Python baseline and MIT license verified below; adds runtime dependency and transitive integration. Does not replace hash/foreign-key/vector checks. Retain dev-only per D7; no runtime dependency recommended. |
| C. Adopt an interchange framework (Frictionless or Arrow/Parquet) | Standard resource descriptors or columnar reading APIs | New descriptor/conversion/runtime integration; conflicts with byte preservation or six-file scope. Do not adopt. Package versions/licenses/Python compatibility and operational security of unselected libraries UNVERIFIED; no installation or performance claims. |

## Official-source check

- [Frictionless Data Package standard](https://datapackage.org/standard/data-package/)
  describes a descriptor/resources container and recommends profile 2.0.
  Borrow integrity/resource separation, not its descriptor format; F004 does
  not claim Frictionless compliance. The [older v1 standard](https://specs.frictionlessdata.io/data-package/)
  was also inspected; it is not the current profile recommendation.
- [jsonschema validation documentation](https://python-jsonschema.readthedocs.io/en/stable/validate/)
  documents Draft202012Validator/check_schema/iter_errors. Formats are not
  automatically asserted: parity must explicitly match the chosen structural
  rules. [Project release metadata](https://pypi.org/project/jsonschema/)
  lists 4.26.0, MIT, Python >=3.10 (compatible declared floor for project 3.12);
  [maintainer license](https://raw.githubusercontent.com/python-jsonschema/jsonschema/main/COPYING)
  confirms MIT text. No full security audit performed.
- [Draft 2020-12](https://json-schema.org/draft/2020-12) is the selected schema
  dialect; use internal references only. CI already runs check_schema on one
  DATA_CONTRACT.json. Semantic foreign keys and binary checks remain runtime.
- [Arrow Parquet reader](https://arrow.apache.org/docs/python/generated/pyarrow.parquet.read_table.html)
  confirms Parquet → Table API. The older Python parquet.html URL returned
  404; the generated API page was verified instead. No migration or dependency
  proposed; package compatibility/license not checked because out of scope.
- [numpy.fromfile](https://numpy.org/doc/stable/reference/generated/numpy.fromfile.html)
  reads binary data with an explicit dtype that determines byte order/size.
  Person 2 could use dtype '<f4' and reshape after validating dimensions/count.
  F004 implements stdlib struct '<f' instead; NumPy is not required or tested.
- [PostgreSQL 18 COPY](https://www.postgresql.org/docs/18/sql-copy.html)
  documents table/file transfers, STDIN over the client connection, and
  text/CSV/binary formats. Raw vectors.f32 is not a PostgreSQL COPY binary
  stream; Person 2's future importer must adapt it. No SQL/migration here.
- [Official pgvector README](https://github.com/pgvector/pgvector#vector-type)
  verifies vector type maximum 16,000 dimensions; [HNSW](https://github.com/pgvector/pgvector#hnsw)
  and [IVFFlat](https://github.com/pgvector/pgvector#ivfflat) vector indexes
  maximum 2,000. Pilot 1536 is below both documented limits. Installed
  extension/server versions and actual import are UNVERIFIED.

## Recommendation and remaining uncertainty

Use A: preserve four payloads, build papers only, deterministic typed manifest,
offline stdlib validation and reader, dev jsonschema parity, existing F003
vector logic, repository reports supplied to consumer. Person 1 APPROVED
R22 (source hashes informational only), R28 (matching report inputs/hashes)
and R29 (no self hash) in this session. D5 mapping remains approved; abstract
question CLOSED: keep excluded. No essential unresolved question remains.
The planning revision adds the manifest-ID reader helper and prefers sibling
directory staging/publication with the committed copy in the same all-or-fail
logic. These follow session decisions and existing stdlib/file contracts;
no new dependency or externally verified performance claim. Source-hash shape
does not establish historical source authenticity. Windows tar ZIP creation,
fresh-directory extraction and validation are TO BE VERIFIED by Person 1;
no archive was built or tested in this planning run. Prior official-source
checks above were not repeated for this internal planning revision.
F004 tests, package build/validation/determinism, archive, PR review, CI and
human verification are NOT RUN / NOT RECORDED, not fabricated results.
Golden v0 is PENDING and retrieval quality UNVERIFIED.
