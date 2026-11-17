# Chunking Strategy (Draft)

Chunk within a single section and follow paragraph and sentence boundaries.
Target approximately 200–350 **content** tokens, subject to the candidate
embedding model's total 512-token input limit. For the proposed local model,
count the exact tokenizer input, including `passage:` and any metadata, before
embedding. A chunk may be shorter
when a section ends; never fill it with text from another section.

Keep original passage text separate from the actual embedding input. Build the
embedding input with the documented `passage:` prefix; use `query:` for query
embeddings. Any heading or metadata included in embedding text must fit within
the same token budget. Preserve the source locator, section path, and processing
versions for each chunk. Use overlap only when a documented boundary case
justifies it; record the amount and avoid duplicate evidence inflation.

Tables, figure captions, references, nested sections, unusually long sentences,
and multilingual passages need explicit rules in the chunking feature (F003). Validate token
counts and retrieval quality on inspected papers before fixing chunk sizes or
normalization rules. The candidate model and its input guidance are documented
in the [model card](https://huggingface.co/intfloat/multilingual-e5-small).

## F003 pilot implementation (chunking-v1)

The pilot uses in-section greedy packing toward 200-350 content tokens with no
overlap. Its `embedding-text-v1` input joins the section path with ` > `, adds
a blank line, then uses verbatim chunk text. The versioned conservative
byte-based estimator `utf8-bytes-div3-v1` uses ceil(UTF-8 bytes / 3), with a
384-token operational cap and 512-token absolute cap instead of an exact
tokenizer. Aggregate reported usage was 0.658 of the estimate on the pilot.

Under approved Option A, figure/table captions, tables, references,
acknowledgments, lists, formulas, supplementary material and boxed text are
counted, not chunked. Caption handling is a follow-up after Golden v0. The
pilot produced 728 chunks from 319 sections of 17 papers, including 2
hard-split chunks. Retrieval quality is NOT VERIFIED; Golden v0 is PENDING.

The unimplemented local-model guidance above remains a proposal, not a measured result.
