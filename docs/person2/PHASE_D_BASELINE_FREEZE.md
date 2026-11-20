# Phase D Retrieval Baseline Freeze

Frozen before Golden v1 question generation on 2026-11-20 (UTC timestamp and exact hashes are in the protected JSON manifest). This is the accepted retrieval baseline; no algorithm or configuration changes are authorized by this freeze.

- Git source revision: `a872cb7770ff0033795bacf3675d5dd514c72f07`.
- Working-tree identity: status digest `5e29bbbfc25e6c948d3c87cd1b40dc77f3e93d4c2fb9b3b339aea91d52ce2c13`; tracked diff digest from HEAD `89d078579c9f4c68bebb1bb1a6cb643e5c12b91cd7015cc2825475ee18a1322d`. Pre-existing files and changes were preserved.
- Frozen corpus identity: `pilot17-xml-1fff1573b610`; full source-manifest SHA-256 `1fff1573b610c27e2e8016343d2f6429df294db974db4af898c4a0f82ffc26bd`. Local paper/section/chunk/vector/embedding-manifest payload hashes match the delivery manifest; 17 papers, 319 sections, 728 chunks, 728 embeddings. No database state was read. The delivery manifest says `draft`; preserve this provenance caveat.
- Embeddings: OpenAI `text-embedding-3-small`, 1536 dimensions, empty query/passage prefixes, `float32-le`. The accepted configuration does not expose an immutable provider model revision.
- Retrieval arms: exact dense cosine, PostgreSQL English full-text lexical, and hybrid reciprocal-rank fusion. RRF constant 60. `top_k` bounds 1?50; hybrid candidate pool defaults to `min(250, max(50, 5 * top_k))`, with explicit pool bounds 1?250 and at least `top_k`. Existing filters and deterministic tie ordering stay fixed.
- Reranker: disabled. MiniLM remains the prior NO-GO and is not an evaluation arm.
- Evaluator snapshot: `phase-d-evaluator-v0.2.0`; the pre-question-generation manifest hashes 14 retrieval/embedding/configuration files and 13 evaluator/schema/preparation files. Its current SHA-256, including a transparent post-generation leak-audit amendment, is `5c9828961e69e40a9de3d08bba30c98c8c6ff944bfc48421cd09d6c255d323e6`.
- Fixed v1 partitions: development Q1/Q4/Q6; held-out Q2/Q3/Q5/Q7/Q8/Q9. Assignment is content- and score-independent and may not be changed.

The exact per-file code/configuration hashes, status/diff digest, payload hashes and recorded limitations are in the protected baseline manifest. Golden v0 was not opened or hashed. This is a source/configuration snapshot, not a live database check.

After candidate creation, the first automated leak audit conservatively matched
shared schema/identifier strings already present in evaluator code and tests.
The audit was narrowed to candidate question/answer prose, free-text expected
outputs, evidence quotations/rationales, and cited passages. The protected
manifest preserves the original pre-generation hashes and separately records
the two amended guard-file hashes. This procedural audit correction changed no
retrieval code/configuration, metric implementation, corpus data, or partition.

The frozen local source delivery contains derived chunk passages, JATS locators,
recorded source XML digests, and source URLs, but not the original raw XML. Thus
the record can be checked exactly against the frozen derived corpus and source
identity metadata; local byte-level revalidation against original XML is not
possible. The delivery manifest remains marked `draft`.
