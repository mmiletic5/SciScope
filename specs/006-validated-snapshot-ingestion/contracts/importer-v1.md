# Person 2 Importer Contract `importer.v1`

**Status**: Approved Person 2 Phase A implementation contract. It consumes the
existing delivery contract 0.3.0 without changing delivered data. It is not a
claim of unrecorded cross-team agreement.

**Execution platform**: Person 2 invokes and verifies this contract from native
Windows 10 x64/PowerShell against the approved PostgreSQL 17/pgvector 0.8.7
installation. The contract's behavior is platform-neutral; no Docker, WSL,
Linux container, or Linux-only dependency is required or permitted for Person 2.

## Python-facing interface

```python
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Literal, Protocol


class ImportMode(str, Enum):
    INITIALIZE = "initialize"
    REPLACE = "replace"


@dataclass(frozen=True)
class ImportRequest:
    package_dir: Path
    parse_report: Path
    chunk_report: Path
    embedding_report: Path
    mode: ImportMode
    expected_active_digest: str | None = None


@dataclass(frozen=True)
class ImportResult:
    import_id: int
    delivery_digest: str
    outcome: Literal["imported", "replaced", "unchanged"]
    previous_delivery_digest: str | None
    papers: int
    sections: int
    chunks: int
    vectors: int


class SnapshotImporter(Protocol):
    def import_snapshot(self, request: ImportRequest) -> ImportResult: ...
```

These declarations specify behavior and typing; this documentation task does
not create Python code.

## Input compatibility

- Delivery schema and contract version must both be `0.3.0`.
- All six package files and three matching reports are required.
- Embedding set must be complete and use
  `openai/text-embedding-3-small`, 1536 dimensions, `float32-le`, and empty
  prefixes.
- Delivery digest is `sha256:` plus SHA256 of exact delivery-manifest bytes.
- The package is accepted as a complete snapshot only after all hashes, counts,
  references, ID sets, and model facts validate.

## Operation behavior

- Initialize is valid only when there is no active corpus.
- Same active and incoming digest returns `unchanged` in either mode and makes
  no database mutation.
- Different digest in initialize mode returns `REPLACEMENT_REQUIRED`.
- Different digest in replace mode requires `expected_active_digest` matching
  the active digest after the advisory lock is acquired.
- The importer uses transaction lock
  `pg_try_advisory_xact_lock(1396918611, 1229803604)` (`SCIS`/`IMPT`). Lock
  contention returns `IMPORT_IN_PROGRESS`; caller may retry.
- Successful initialization/replacement returns exact stored counts.

## Atomicity and errors

Validation failures occur before mutation. Database load, verification,
pruning, audit transition, and activation use one transaction. No failure may
make a partial snapshot visible or alter the prior active snapshot.

Errors expose one stable code from the set defined in `data-model.md`. They do
not include scientific text, vector values, secrets, or absolute paths.

## Compatibility

Additive optional result metadata may remain within `importer.v1`. Changing
operation preconditions, digest semantics, scientific preservation, vector
ownership, atomicity, or error codes requires a new contract version and an
owner-approved architecture change.
