# Paper, Section, and Chunk Model (Draft)

The agreed initial hierarchy is **Paper → Section → Chunk**. The proposed
interchange shape is in [DATA_CONTRACT.json](DATA_CONTRACT.json); this document
explains intent. It is not a database migration or approved final contract.

| Entity | Proposed information | Purpose |
| --- | --- | --- |
| Paper | DOI, title, authors, journal, publication year, article type, subject categories, license, source, XML location and checksum | Identification, filters, license review, source preservation |
| Section | Stable section ID, parent ID, hierarchy path, original heading, normalized type, source locator | Preserve JATS structure and citation context |
| Chunk | Stable chunk ID, section ID, original text, source locator, embedding input, optional vector, versions | Retrieval and traceable evidence |

The original JATS XML is retained as a local source artifact. The contract
references that artifact and a digest; it does not embed a downloaded corpus in
Git. Every chunk belongs to exactly one section. The original text and the
embedding input are separate fields. A source locator should be stable enough
to find the passage in the preserved XML after chunk IDs change.

The proposed embedding candidate is `intfloat/multilingual-e5-small` with 384
dimensions. The vector, when present, has 384 numeric components. Record model
identifier and version/revision, tokenizer and chunking versions, and processing
version so derived data can be rebuilt. The schema allows a null vector before
embedding generation; an approved ingestion contract may tighten this.

Person 1 and Person 2 must agree on DOI normalization, field nullability,
section taxonomy, locator stability, version semantics, and import error
behavior before accepting this contract. Person 3 and Person 4 should review
fields needed for citation display and filters. No real paper records have
been created in this bootstrap.
