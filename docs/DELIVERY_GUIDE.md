# SciScope pilot delivery

Never zip vectors with `chunks.jsonl` lines by position: row `i` belongs to `embedding_manifest.entries[i].chunk_id`.

```python
import json
from pathlib import Path

from sciscope.delivery.reader import vectors_by_chunk_id

package = Path("data/delivery/pilot")
manifest = json.loads((package / "delivery_manifest.json").read_bytes())
by_id = vectors_by_chunk_id(
    package / "embedding_manifest.json",
    package / "vectors.f32",
    dimensions=manifest["embedding_set"]["dimensions"],
)
```

## Package and verification

The pilot has 17 papers, 319 sections and 728 vectors of 1536 dimensions.

| File | Contents |
| --- | --- |
| `papers.jsonl` | DOI-sorted metadata, provenance and derived `publication_year` |
| `sections.jsonl` | Flat hierarchy, headings, taxonomy and own paragraph counts |
| `chunks.jsonl` | Text, IDs, ordered source spans and omission metadata |
| `vectors.f32` | Little-endian float32 rows |
| `embedding_manifest.json` | Provider/model configuration, entry IDs and input hashes |
| `delivery_manifest.json` | Counts, payload/report SHA256, sizes, versions and `embedding_set` |

Use compatible code and `docs/DATA_CONTRACT.json`, `schema_version` 0.3.0 (draft until Person 2 reviews the contract pull request), with matching parse, chunk and embedding reports. Parser/taxonomy source digests are informational: there is no comparison with local parser/taxonomy source digests. The six-file package contains neither raw XML nor paragraphs.

Before handoff, Person 1 records the archive SHA256 under F004 in `EVIDENCE.md`; compare the received archive with that recorded value before extraction. Archive bytes are not deterministic. The planned producer command is `tar -a -c -f data/delivery/pilot-delivery.zip -C data/delivery pilot`. Run from the repository root. With uninstalled sources, set `PYTHONPATH=src` (`pyproject.toml` sets `package = false`). Verify an extracted temporary copy:

```powershell
$env:PYTHONPATH = "src"
Get-FileHash data/delivery/pilot-delivery.zip -Algorithm SHA256
$extract = Join-Path ([System.IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $extract -ErrorAction Stop | Out-Null
tar -x -f data/delivery/pilot-delivery.zip -C $extract
if ($LASTEXITCODE -ne 0) { throw "Extraction failed" }
uv run --locked python -m sciscope.pipeline.cli validate-delivery `
    --package-dir (Join-Path $extract "pilot") `
    --parse-report data/pilot/parse_report.json `
    --chunk-report data/pilot/chunk_report.json `
    --embedding-report data/pilot/embedding_report.json
if ($LASTEXITCODE -ne 0) { throw "Delivery validation failed" }
```

These three report paths are the `DeliveryInputs` defaults; supply matching reports at those paths or override them explicitly. Exit 0 means validation succeeded, 1 means semantic failure, and 2 means usage/structural failure.

## Reading and queries

`iter_jsonl(path)` splits only on LF, preserves raw Unicode separators and accepts one final LF; UTF-8/BOM/CR checks precede any record, while a later JSON error can follow earlier yielded rows. `load_vectors(path, dimensions=..., count=...)` checks positive integer arguments, I/O, exact size and finiteness. `vectors_by_chunk_id` uses manifest entry order, ignores manifest dimensions and hashes, and never reads chunks; join chunk records to its result by ID. Run `validate-delivery` first for full package validation.

`DeliveryReadError.code` and its message are identical safe tokens: `reader-io`, `reader-decoding`, `reader-json`, `reader-line`, `reader-argument`, `reader-size`, `reader-nonfinite`, `reader-manifest`, `reader-duplicate-id`. Manifest decoding/shape errors use `reader-manifest`; duplicate IDs precede vector I/O. Readers accept string and Path paths and need only the stdlib.

Query embeddings must use `delivery_manifest.json`'s `embedding_set.provider`, `model`, `dimensions` and `query_prefix` unchanged. The pilot uses openai/text-embedding-3-small, 1536 dimensions and an empty query prefix. Keep raw `language` values `EN`/`en`; comparisons are case-insensitive.

## Local source trace and citations

F001 download supplies `data/raw/plos/<quote(doi, safe='')>.xml`; its exact-byte SHA256 must equal `xml_sha256`. Source tracing requires that XML plus matching F001 metadata/acquisition manifest at the JATS CLI defaults. Run the next Python block through a PowerShell here-string: `@'` on its own line, the code, then `'@ | uv run --locked python -X utf8 -` on its own line. It uses Python code-point offsets, with `show` and `check-quote` for the first span:

```python
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

from sciscope.delivery.reader import iter_jsonl
from sciscope.jats.locator import SourceDocument
from sciscope.jats.parser import paragraph_text
from sciscope.jats.source import check_xml_safety

chunk = next(iter_jsonl(Path("data/delivery/pilot/chunks.jsonl")))
span = chunk["spans"][0]
raw = (
    Path("data/raw/plos") / (quote(chunk["doi"], safe="") + ".xml")
).read_bytes()
check_xml_safety(raw)
document = SourceDocument.from_bytes(raw)
assert document.sha256 == chunk["xml_sha256"]
text, _ = paragraph_text(document.resolve(span["source_locator"]))
start, end = span["start"], span["end"]
source_quote = text[start:end]
command = [sys.executable, "-m", "sciscope.jats.cli"]
subprocess.run(
    command + ["show", chunk["doi"], "--section", chunk["section_id"]],
    check=True,
)
subprocess.run(
    command
    + [
        "check-quote",
        "--locator",
        span["source_locator"],
        "--quote",
        source_quote,
    ],
    check=True,
)
```

To reconstruct chunk text, join consecutive spans of the same paragraph using the source characters between them; join spans from different paragraphs with "\n\n" (`chunking/core.py::_join_pieces`). Person 1 verified this for all 728 pilot chunks: 0 mismatches, including 5 same-paragraph joins.

Citations include `doi`, `title`, authors, `publication_year`, journal, license, `section_path`, `source_locator` and `chunk_id`; display the available heading. `(untitled)` in `section_path` is a sentinel for no heading and is never displayed.

## Limits and changes

Chunk `omitted` lists XML names. Reports count 223 skipped elements and 33 back-matter exclusions: figures, tables, supplementary material, formulas, lists and references are omitted under the recorded policy. Abstract chunks have no heading context; the pilot has exactly 2 `hard_split` chunks. Limits include O(n²) validator scans and no offline proof of vector origin. Retrieval quality is NOT VERIFIED; Golden v0 is pending. Propose contract changes by pull request with Person 2 as reviewer.

Verified 2026-11-17: pgvector [vector type](https://github.com/pgvector/pgvector#vector-type) supports up to 16,000 dimensions; [HNSW](https://github.com/pgvector/pgvector#hnsw) and [IVFFlat](https://github.com/pgvector/pgvector#ivfflat) vector indexes support up to 2,000. The pgvector version on the team database is UNVERIFIED.
