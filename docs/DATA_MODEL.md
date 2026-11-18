# Flat pilot data model (Draft)

[DATA_CONTRACT.json](DATA_CONTRACT.json) is the single source for record shapes:
one Draft 2020-12 schema with the delivery manifest at its root and records
under `$defs`. Its `schema_version` is 0.3.0, draft until Person 2's PR review.
The runtime structural checks are in
[contract.py](../src/sciscope/delivery/contract.py); byte integrity and
cross-record semantics require `validate-delivery`. See the
[delivery guide](DELIVERY_GUIDE.md) for verification, reading and source tracing.
This is a file handoff, not a database schema or migration.

## Flat records

`papers.jsonl` is sorted by normalized DOI. Each record contains `doi`, `title`,
`authors` (ordered objects with `surname` and `given_names`), `journal`,
`publication_date`, `article_type`, `subjects`, `license`, `language`,
`source_url`, `retrieved_at`, `xml_sha256` and `publication_year`.
The only derived metadata field is integer `publication_year`. Authors and
journal are required and nonempty; `given_names` may be empty. Preserve subject
order, raw license strings and raw language (`EN`/`en`, compared
case-insensitively). Paper-level abstract, query provenance and raw XML paths
are excluded. Abstract text remains in chunks linked to abstract sections.

`sections.jsonl` contains `doi`, `title`, `xml_sha256`, `section_id`,
`parent_section_id`, `section_path`, `original_heading`, `normalized_type`,
`source_locator`, `depth` and `paragraph_count`. Root parents are null;
top-level depth is 1 and nested sections add 1. Paragraph count includes only
own direct paragraphs, including empty ones; zero-own-text sections are legal.
`(untitled)` in a path means no heading and must never be displayed.

`chunks.jsonl` contains `chunk_id`, `doi`, `xml_sha256`, `section_id`, `ordinal`,
`chunk_kind`, `normalized_type`, `section_path`, `text`, `text_sha256`, `spans`,
`source_locator`, `content_tokens`, `hard_split`, `omitted`, `chunking_version`,
`token_counter_id` and `template_version`. Each nonempty-text chunk belongs to
one section; `chunk_kind` is `paragraph`, ordinals start at 1, and `omitted`
is an array of XML element names. Each span has `source_locator`, 1-based
`paragraph_index`, `start` and `end`: half-open Unicode code-point offsets
with `end > start`. The chunk locator is its first span locator. Neither
paragraph entities, embedding input text nor inline vectors are delivered.

Taxonomy v0 is `abstract`, `introduction`, `methods`, `results`,
`results_discussion`, `discussion`, `conclusions`, `other`. Abstracts always
use `abstract`; body precedence is exact normalized heading, then `sec-type`,
then nearest explicitly classified ancestor, then `other`.
DOIs follow F001 `normalize_doi`: supported prefixes/URL extraction, trimming
and trailing punctuation removal, then lowercase. `jats:v1` locators carry
the exact XML-byte SHA256 and indexed XML path; traversal needs local XML.

## Vectors and manifests

`vectors.f32` is a little-endian float32 matrix. `embedding_manifest.json`
preserves the F003 manifest: provider/model, requested/returned dimensions,
prefixes, versions, hashes, normalization, usage and ordered entries with
`chunk_id` and `input_sha256`. Row `i` belongs to
`embedding_manifest.entries[i].chunk_id`; join by ID, never by chunk line
position. The pilot has 728 vectors of 1536 dimensions from
openai/text-embedding-3-small, with empty passage/query prefixes. Dimensions
are set metadata, not a fixed contract constant. Queries must use the same
provider, model, dimensions and query prefix.

`delivery_manifest.json` contains `schema_version`, `contract_version`,
`status`, `counts`, `files`, `processing_versions`, `source_reports` and
`embedding_set`. Five payload descriptors carry SHA256, bytes and record
counts; the manifest has no self-hash or timestamp. Three external report
descriptors carry SHA256 and bytes. The embedding set adds row mapping,
norm tolerance and nullable model revision (null for this pilot).
Processing versions are parser version null with informational source hash,
taxonomy v0 with informational source hash, locator `jats:v1`,
`chunking-v1`, `utf8-bytes-div3-v1` and `embedding-text-v1`. Source hashes
are checked for shape/internal consistency, never against local code bytes.
Sections, chunks, vectors and the embedding manifest are unchanged copies;
the six-file package has 17 papers, 319 sections and 728 chunks/vectors.
