# Feature 012 UI Data Model

This document describes the frontend's typed view of the accepted Feature 011 question-service response. The backend handoff and Pydantic HTTP models remain authoritative. This model does not introduce new backend fields.

## Entities

### QuestionRequest

| Field | Type | Validation/meaning |
| --- | --- | --- |
| `workflow` | literal `research_question` | Only supported workflow. |
| `question` | string | Trim before send; length 1–2,000 after trimming. |
| `request_id` | string | Generated for each submit; 1–128 characters from `[A-Za-z0-9._:-]`. |

No filter, provider, model, or retrieval-mode values are sent.

### QuestionSuccess

Discriminated by `status`:

| Status | Answer | Claims | Evidence |
| --- | --- | --- | --- |
| `answered` | Nonempty string | One or more claims | One or more response-local evidence records matching claim references |
| `no_results` | `null` | Empty list | Empty list |
| `insufficient_evidence` | `null` | Empty list | Retained evidence may be present |

Every success also includes API version, request ID, workflow, corpus provenance, and metadata. The currently accepted fake service reports `is_mock: true` and `is_test_data: true`. The frontend visibility rule is generic boolean logic so that only an explicit pair of `false` values can hide the global badge; this does not claim that Feature 011 currently produces such a response.

### Claim

| Field | Type | Meaning |
| --- | --- | --- |
| `claim_id` | nonempty string | Response-local claim identity. |
| `text` | nonempty string | Claim wording shown to the user. |
| `citation_chunk_ids` | nonempty list of strings | Response-local evidence identities. |

### Evidence

| Field | Type | Meaning/presentation |
| --- | --- | --- |
| `chunk_id` | nonempty string | Response-local identity used only to resolve citations. |
| `doi` | nonempty string | DOI value converted to a `https://doi.org/` link. |
| `source_locator` | nonempty string | Shown only inside a “Details” disclosure. |
| `passage` | nonempty string | Displayed as a blockquote. |
| `paper_title` | nonempty string | Main source-card title. |

No authors, publication year, or section property exists in this contract.

### CorpusProvenance

| Field | Type | Presentation |
| --- | --- | --- |
| `corpus_version` | nonempty string | “About this result” disclosure. |
| `source_contract_version` | nonempty string | “About this result” disclosure. |
| `delivery_digest` | nonempty string | “About this result” disclosure. |

### ErrorResponse

| Field | Type | Meaning |
| --- | --- | --- |
| `api_version` | literal `v1` | Version marker. |
| `request_id` | valid string | Shown as a small support reference. |
| `error.code` | closed union | `invalid_request`, `retrieval_unavailable`, `provider_unavailable`, `dependency_timeout`, `response_contract_failure`, or `internal_error`. |
| `error.message` | nonempty string | Never shown raw. |
| `error.retryable` | boolean | Sole control for displaying retry on server error. |
| `metadata` | mock/test-data booleans | Drives synthetic warning and global badge state. |

## Derived UI State

| State | Derivation |
| --- | --- |
| `selectedView` | One of four navigation items; initial value is Research question. |
| `questionText` | Editable user text; survives all result transitions. |
| `requestStatus` | `idle`, `pending`, `success`, `server_error`, `unreachable_error`, `timeout_error`, or `invalid_response`. |
| `activeRequestId` | Generated at submit and retained for reference if there is no server response. |
| `latestResponse` | Latest valid success or error response; controls mock badge state. |
| `mockNoticeDismissedFor` | Identity of the currently displayed response only; reset on each new response. Never stored persistently. |
| `numberedEvidence` | Evidence ordered by first known citation across claims, with duplicate references de-duplicated. |
| `uncitedEvidence` | Evidence whose identity appears in no valid claim citation. |
| `highlightedEvidenceId` | Temporary target set by activating a citation marker. |

## State Transitions

```text
idle --valid submit--> pending
pending --answered/no_results/insufficient_evidence--> success
pending --retryable/nonretryable server envelope--> server_error
pending --fetch rejection--> unreachable_error
pending --HTTP 5xx without valid API error envelope--> unreachable_error
pending --malformed HTTP 200 or 4xx response--> invalid_response
pending --30 second abort--> timeout_error
any settled state --new valid submit--> pending
any state --switch view--> selectedView changes; question/result state remains available
success --dismiss notice--> same success with notice dismissed for this response only
success --new response--> notice dismissal resets and metadata refreshes badge state
```

One pending request is active at a time. A stale completion from an aborted or superseded request must not replace the latest result.

## Transport Classification

- A fetch rejection is an unreachable-service error with the retryable reachability message.
- For any HTTP 5xx response, a valid API error envelope is handled by its code and `retryable` field. A missing or invalid error envelope is an unreachable-service error, including an HTML proxy response.
- Malformed JSON or an invalid envelope under HTTP 200 or 4xx is a generic nonretryable client error. Raw proxy or response bodies are never displayed.
- The existing contract's valid 5xx error codes continue to use their sanitized error envelope and retryability mapping.
