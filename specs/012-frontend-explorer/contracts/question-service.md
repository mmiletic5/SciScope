# Feature 012 Question-Service Contract

This is a frontend integration summary of the accepted [Person 3 handoff](../../../docs/person3/BACKEND_FRONTEND_INTEGRATION_HANDOFF.md) and [HTTP models](../../../src/sciscope/api/http_models.py). It does not amend the backend contract. If this file and the handoff disagree, the handoff and backend models control.

## Request

- Method and path: `POST /api/v1/questions`.
- Request body is a closed JSON object containing:

```json
{
  "workflow": "research_question",
  "question": "A trimmed question between 1 and 2,000 characters.",
  "request_id": "ui-<timestamp>-<random>"
}
```

- `request_id` must match `^[A-Za-z0-9._:-]{1,128}$`.
- Do not send filter, provider, model, retrieval-mode, or any unknown fields.
- The existing Vite proxy forwards `/api` to the local service for development. No backend CORS change is planned.

## Success

HTTP 200 returns `api_version`, `request_id`, `workflow`, `status`, `answer`, `claims`, `evidence`, `corpus`, and `metadata`.

| `status` | `answer` | Claims | Evidence |
| --- | --- | --- | --- |
| `answered` | Nonempty string | Claims with nonempty citation identity lists | Evidence records resolved through those identities |
| `no_results` | `null` | Empty | Empty |
| `insufficient_evidence` | `null` | Empty | May contain retained passages |

Each evidence record has exactly the supported display data: `chunk_id`, `doi`, `source_locator`, `passage`, and `paper_title`. Authors, publication year, and section are not in the contract. Corpus provenance fields are `corpus_version`, `source_contract_version`, and `delivery_digest`.

The currently accepted fake service marks both `metadata.is_mock` and `metadata.is_test_data` true. The frontend shows its global badge by default and while either value is true; it hides the badge only if a response explicitly reports both false. The spec's generic false/false behavior is future-compatible UI logic; the current accepted fake API does not emit it.

## Errors

Error envelopes contain `api_version`, `request_id`, `error {code, message, retryable}`, and `metadata`. The client maps these codes to friendly messages, never renders raw error text, and shows the retry affordance only when `retryable` is true.

| HTTP | Code | Retryable |
| --- | --- | --- |
| 422 | `invalid_request` | No |
| 503 | `retrieval_unavailable` | Yes |
| 503 | `provider_unavailable` | Yes |
| 504 | `dependency_timeout` | Yes |
| 500 | `response_contract_failure` | No |
| 500 | `internal_error` | No |

## HTTP Response Classification

- First determine whether the body is a valid response envelope; do not classify solely from `fetch` resolving or rejecting. The Vite proxy can return HTTP 5xx with an HTML or other non-envelope body when the backend is stopped.
- Any HTTP 5xx response without a valid API error envelope is treated as API unreachable, including an empty body, HTML proxy page, malformed JSON, or success-shaped JSON. Show “Cannot reach the SciScope API. Is the backend running?” and offer retry.
- A valid API error envelope on HTTP 5xx is handled using its known error code and `retryable` value; preserve its response request ID.
- A malformed JSON body or invalid envelope on HTTP 200 or 4xx is a generic safe, nonretryable error. Do not expose raw body content.
- A fetch rejection uses the same retryable API-unreachable message.

## Frontend-Only Transport Behavior

- A 30-second frontend timer aborts an unresolved request and shows “The request took too long. Please try again.” as retryable. The client-generated request ID remains the support reference when no server response arrives.
- HTTP 5xx without a valid API error envelope, or a fetch rejection, shows “Cannot reach the SciScope API. Is the backend running?” as retryable.
- Invalid JSON or a malformed response with HTTP 200 or 4xx produces a generic safe nonretryable client error. It does not invent an API code or display raw payload text.
- All failures preserve the editable question.

## Citation Resolution

For an answered result, process claims in response order. For each claim's citation IDs, find matching evidence by `chunk_id`. Assign each first-seen matching evidence item the next number. Ignore unknown IDs, do not assign multiple numbers to duplicate IDs, and do not number evidence with no matching claim reference. These source numbers exist only within the current response.
