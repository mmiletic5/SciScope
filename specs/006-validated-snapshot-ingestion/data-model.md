# Data Model: Validated Snapshot Ingestion

Feature 006 uses the persisted schema defined by Feature 005. This artifact
defines operation models and state transitions rather than duplicating table
definitions.

## Import request

| Field | Rule |
|---|---|
| `package_dir` | Required path to a six-file delivery directory |
| `parse_report`, `chunk_report`, `embedding_report` | Required matching report paths |
| `mode` | Required `initialize` or `replace` |
| `expected_active_digest` | Null for initialize; required `sha256:<64 hex>` for a changed replacement |

Paths are operational inputs and are never persisted or included in sanitized
errors. The expected digest is a compare-and-swap guard, not delivery identity.

## Validated snapshot

Immutable in-memory description created only after all pre-write checks:

- Exact delivery digest over raw `delivery_manifest.json` bytes.
- Validated delivery and embedding manifests.
- Complete paper, section, chunk, and manifest-entry identity sets.
- Counts and processing/model metadata.
- Deterministically ordered record iterators.
- Streaming vector-row descriptor bound to manifest entries.
- Normalization method and numeric target remain distinct: validated source
  method `"l2"` is preserved in JSONB; the accepted Feature 005 numeric field
  stores target norm `1.0`, enforced by the existing embedding validator.
- The delivery repeats each chunk's `xml_sha256`, while Feature 005 stores the
  hash once on its parent paper. The delivery validator checks equality and the
  independent verifier compares every chunk hash through that paper relation;
  no redundant chunk column is added.

No function may mutate delivered records or write repaired files.

## Import result

| Field | Rule |
|---|---|
| `import_id` | Existing active ID for no-op; new activation ID otherwise |
| `delivery_digest` | Incoming validated snapshot identity |
| `outcome` | `imported`, `replaced`, or `unchanged` |
| `previous_delivery_digest` | Null for initialization; previous active identity for replacement/no-op context |
| record counts | Exact stored paper, section, chunk, and vector counts |

## State machine

| Active state | Request | Transition |
|---|---|---|
| None | Initialize | Validate, import, verify, activate |
| None | Replace | Reject; nothing to replace |
| Digest A | Either mode with incoming A | Return unchanged; no mutation |
| Digest A | Initialize with incoming B | Reject `REPLACEMENT_REQUIRED` |
| Digest A | Replace B without expected digest | Reject invalid request |
| Digest A | Replace B expecting C | Reject `ACTIVE_CORPUS_CONFLICT` |
| Digest A | Replace B expecting A | Transactionally replace and activate B |

Reactivation of a historically used digest creates a new successful activation
audit row because it is a new state transition; historical digest is not a
global unique key.

## Transaction state

1. Validated outside the mutation transaction.
2. Transaction begins and attempts the advisory lock.
3. Active state is re-read under the lock.
4. Operation preconditions are checked.
5. New audit is inserted inactive. For replacement, old corpus rows are pruned
   inside the transaction before inserting new rows because Feature 005 uses
   global entity keys that prevent overlapping snapshots from coexisting.
6. New data is loaded and verified while still inside the same transaction.
7. Old audit becomes inactive and new audit active.
8. Commit publishes the new snapshot atomically; rollback restores the previous
   committed corpus after any failure.

Any exception before commit returns to the previous committed state. No
durable in-progress row is needed; retry repeats validation and state checking.

## Error model

Stable public codes are `DELIVERY_INVALID`, `DELIVERY_INCOMPATIBLE`,
`EMBEDDING_CONFIGURATION_MISMATCH`, `REPLACEMENT_REQUIRED`,
`ACTIVE_CORPUS_CONFLICT`, `IMPORT_IN_PROGRESS`, `DATABASE_UNAVAILABLE`,
`IMPORT_TRANSACTION_FAILED`, and `IMPORT_VERIFICATION_FAILED`.

Messages are actionable but contain no source prose, vector values,
credentials, or absolute paths.
