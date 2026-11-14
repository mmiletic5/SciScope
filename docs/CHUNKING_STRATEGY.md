# Chunking Strategy (Draft)

Chunk within a single section and follow paragraph and sentence boundaries.
Target approximately 200–350 **content** tokens, subject to the candidate
embedding model's total 512-token input limit. Count the exact tokenizer input,
including `passage:` and any metadata, before embedding. A chunk may be shorter
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
This document records a proposal, not a measured result.
