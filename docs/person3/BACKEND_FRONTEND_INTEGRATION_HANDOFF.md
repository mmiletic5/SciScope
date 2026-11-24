# Backend–Frontend Integration Handoff

> **Feature 011 v1 baseline plus accepted offline Feature 012 v2 boundary.**
>
> **Status:** v1 remains ready for the accepted fake-only contract. The
> separately versioned v2 boundary is accepted for explicitly injected offline
> dependencies; T006 cross-story integration, T007 database verification, and
> T008 feature closeout remain pending.

## 1. Purpose and Audience

This handoff gives Person 4 (Frontend & Integration) the current, evidence-based
contract for the Feature 011 question API. It is suitable for UI contract work,
response rendering, and deterministic in-process compatibility testing.

It does not describe a deployed backend or a live scientific-answer service.
Feature 011 is the accepted deterministic fake-only v1 baseline in
[specs/011-fake-backend-api](../../specs/011-fake-backend-api). In addition,
Feature 012 T004 accepts a separately versioned injected offline v2 HTTP
boundary, and T005 accepts explicit composition and request-dispatch lifecycle
behavior. T006–T008 remain pending.

## 2. Current Backend Status

Feature 011 is accepted within its approved fake-only, offline scope. It
provides one synchronous, non-streaming endpoint:

```text
POST /api/v1/questions
```

The application factory in [src/sciscope/api/app.py](../../src/sciscope/api/app.py)
requires injected retrieval and answer-provider dependencies. The approved
fixtures are [FakeRetrieval and FakeAnswerProvider](../../src/sciscope/question_service/fakes.py);
they do not create a database connection, embedding client, Gemini client, or
network listener.

The accepted evidence and human-verification record are in
[docs/person3/FEATURE_011_TEST_LOG.md](FEATURE_011_TEST_LOG.md) and
[EVIDENCE.md](../../EVIDENCE.md).

## 3. API Endpoint and Contracts

### Request

`POST /api/v1/questions` accepts one closed JSON object.

```json
{
  "workflow": "research_question",
  "question": "What does the synthetic fixture demonstrate?",
  "request_id": "ui-question-001"
}
```

| Field | Required | Contract |
| --- | --- | --- |
| `workflow` | Yes | Exact string `research_question`. |
| `question` | Yes | String with trimmed length from 1 through 2,000 characters. |
| `request_id` | No | When supplied, matches `^[A-Za-z0-9._:-]{1,128}$`. A valid supplied value is returned unchanged. |

The request has no request-body API-version field; `/v1/` in the path selects
the version. It has no public filter, provider, model, or retrieval-mode field.
Unknown fields and type coercion are rejected.

### Success envelope

Every successful response is HTTP `200` and has these fields:

| Field | Meaning |
| --- | --- |
| `api_version` | Always `v1`. |
| `request_id` | Valid caller value or a generated opaque ID. |
| `workflow` | Always `research_question`. |
| `status` | One of `answered`, `no_results`, or `insufficient_evidence`. |
| `answer` | Nonempty string only for `answered`; otherwise `null`. |
| `claims` | Answer claims; each citation ID refers to an item in this response's `evidence`. |
| `evidence` | Response-local source records. |
| `corpus` | Corpus provenance, independent of individual evidence IDs. |
| `metadata` | Fake-only marker: `{"is_mock": true, "is_test_data": true}`. |

An evidence entry has `chunk_id`, `doi`, `source_locator`, `passage`, and
`paper_title`. A claim has `claim_id`, `text`, and a nonempty
`citation_chunk_ids` list. Corpus provenance has `delivery_digest`,
`source_contract_version`, and `corpus_version`.

These are HTTP JSON fields defined by
[src/sciscope/api/http_models.py](../../src/sciscope/api/http_models.py). The
plain Python dataclasses in
[src/sciscope/question_service/contracts.py](../../src/sciscope/question_service/contracts.py)
are internal dependency contracts; frontend code should use the HTTP shapes.

## 4. Verified Request and Response Examples

The following answered example uses the exact deterministic fake values from
[src/sciscope/question_service/fakes.py](../../src/sciscope/question_service/fakes.py).
It is synthetic test data, not article text or a scientific result.

```json
{
  "api_version": "v1",
  "request_id": "ui-question-001",
  "workflow": "research_question",
  "status": "answered",
  "answer": "Synthetic fixture answer for deterministic backend testing.",
  "claims": [
    {
      "claim_id": "synthetic-claim-001",
      "text": "Synthetic fixture claim linked to supplied evidence.",
      "citation_chunk_ids": ["synthetic-chunk-001"]
    }
  ],
  "evidence": [
    {
      "chunk_id": "synthetic-chunk-001",
      "doi": "10.0000/synthetic.001",
      "source_locator": "synthetic:section-1:paragraph-1",
      "passage": "Synthetic fixture passage for deterministic backend testing.",
      "paper_title": "Synthetic Fixture Paper"
    }
  ],
  "corpus": {
    "delivery_digest": "synthetic-delivery-digest-v1",
    "source_contract_version": "synthetic-source-contract-v1",
    "corpus_version": "synthetic-corpus-v1"
  },
  "metadata": {
    "is_mock": true,
    "is_test_data": true
  }
}
```

### Other successful states

| Status | `answer` | `claims` | `evidence` | Frontend interpretation |
| --- | --- | --- | --- | --- |
| `no_results` | `null` | `[]` | `[]` | Retrieval returned no eligible fake evidence. This is a successful response. |
| `insufficient_evidence` | `null` | `[]` | Nonempty retained fake evidence | The configured fake provider declined to make an answer. It is a synthetic policy outcome, not a scientific conclusion. |

For every `answered` result, render citations by joining each claim's
`citation_chunk_ids` to response-local `evidence[].chunk_id`. Do not fabricate
citations, infer a citation from display text, or assume an evidence item is
cited unless a claim contains its ID.

## 5. Error and Validation Behavior

Errors use a closed, sanitized envelope:

```json
{
  "api_version": "v1",
  "request_id": "ui-question-001",
  "error": {
    "code": "invalid_request",
    "message": "The request does not meet this API version's validation rules.",
    "retryable": false
  },
  "metadata": {
    "is_mock": true,
    "is_test_data": true
  }
}
```

| HTTP status | Error code | Retryable | Trigger |
| --- | --- | --- | --- |
| 422 | `invalid_request` | `false` | Invalid JSON, closed-schema violation, invalid workflow/question/request ID, or unsupported field. |
| 503 | `retrieval_unavailable` | `true` | Configured fake retrieval unavailable. |
| 503 | `provider_unavailable` | `true` | Configured fake provider unavailable. |
| 504 | `dependency_timeout` | `true` | Configured fake retrieval or provider timeout. |
| 500 | `response_contract_failure` | `false` | Fake output fails response/citation validation. |
| 500 | `internal_error` | `false` | Unexpected backend exception. |

Validation and error handling deliberately omit raw request values, framework
validation details, stack traces, provider configuration, and private exception
text. If a malformed request includes a valid request ID, that ID is retained
in its error envelope. If the ID is missing or invalid, the backend generates a
new valid opaque ID and never echoes the invalid value.

## 6. Local Setup and Test Commands

The repository-supported dependency setup is:

```bash
uv sync --locked
uv run --locked python --version
```

Feature 011 establishes **in-process** FastAPI `TestClient` testing only. It
does not define a supported `uvicorn` command, HTTP listener, localhost port,
deployment topology, or frontend API base URL. Do not configure a production or
local frontend base URL from this handoff.

Use the established test commands to verify contract compatibility:

```bash
uv run --locked pytest tests/backend/test_question_api.py -v
uv run --locked pytest tests/backend/test_request_ids_and_validation.py -v
uv run --locked pytest tests/backend/test_response_validation.py -v
uv run --locked pytest tests/backend/ -v
```

The implementation uses `create_app(...)` with explicitly injected
`FakeRetrieval` and `FakeAnswerProvider` in tests. Person 4 can use the same
contract fixtures in frontend component tests, but should not introduce an
unapproved backend launcher or direct imports of private retrieval modules.

## 7. Person 4 Integration Checklist

- [ ] Submit only `workflow`, `question`, and optionally `request_id`.
- [ ] Treat a `200` with `no_results` or `insufficient_evidence` as a handled
  result state rather than a transport failure.
- [ ] Show a loading state while the request is pending.
- [ ] Render an `answered` response's answer, claims, and evidence separately.
- [ ] Resolve citations through `citation_chunk_ids` and response-local
  `evidence[].chunk_id`.
- [ ] Keep corpus provenance available to the user or diagnostic surface as
  appropriate for the approved UI contract.
- [ ] Display a conspicuous test/development indication whenever
  `metadata.is_mock` and `metadata.is_test_data` are true.
- [ ] Use `error.retryable` to decide whether a retry affordance is appropriate;
  preserve the returned `request_id` for support/debug correlation.
- [ ] For `422`, keep the user's editable input client-side, but do not render
  backend raw validation details because the contract intentionally omits them.
- [ ] Reject unsupported client-side request shapes before sending when
  practical; backend validation remains authoritative.

Loading, visual hierarchy, retry UI, and provenance-display design are frontend
implementation choices unless a separately approved frontend specification
makes them requirements.

### Feature 012 v2 and post-T005 integration status

`POST /api/v2/questions` is a separately versioned accepted API, registered
only when `create_app` receives valid explicit `v2_metadata`. Its closed request
contains `workflow`, `question`, and optional `request_id`; retrieval settings,
mode, version, ranking, filters, and provider selection remain server-owned.
The provider is explicitly injected.

V2 success responses contain `api_version`, `request_id`, `workflow`, `status`,
`answer`, `claims`, `evidence`, `corpus`, and component `metadata`. Retrieval
and answer-provider metadata each have `configured_origin`, `executed`, and
`is_test_data`; the frontend must never infer execution from origin. V2 errors
are sanitized, preserve typed retryability where applicable, and use the
route-scoped request ID rather than a downstream exception ID. Error metadata
may be omitted when execution state is unavailable or unknown. The implemented
422/500/503/504 mappings remain authoritative in the v2 models and handlers.

Citations must resolve only from a claim's `citation_chunk_ids` to evidence in
the same response. No cross-response evidence reuse is valid, and citation
membership does not establish scientific correctness. V1 has no implicit
migration to v2: its closed fake-only request/response shapes, synthetic
evidence, and literal `is_mock=true` / `is_test_data=true` metadata remain
unchanged.

T005 provides explicit offline composition and a handler-dispatch lifecycle
boundary. It does not establish production retrieval readiness, real PostgreSQL
connectivity, real provider execution, a final mode, streaming-response or
background-task protection, ASGI-server draining, or complete deployment
shutdown safety. T006 still needs end-to-end in-process integration evidence.
Person 4's next concrete gate is review of T006 v2 response/error/metadata
behavior and frontend handling assumptions; no T006 approval is claimed here.

## 8. Fake vs Real Data Boundaries

Every accepted Feature 011 response carries:

```json
{"is_mock": true, "is_test_data": true}
```

The deterministic fake evidence, corpus identifiers, claims, and answers are
synthetic. They must not be presented as retrieved literature, real citations,
or scientific advice. `insufficient_evidence` in this baseline is a configured
fake behavior; it does not establish absence of evidence in a real corpus.

Feature 011 does not access PostgreSQL, the T007 retrieval service, a real
corpus, query embeddings, Gemini, or another live provider.

## 9. Dependencies and Known Limitations

- Feature 007 is accepted within its public-facade scope; Person 2 review and
  native Windows verification are owner-reported, and Windows terminal evidence
  was not retained. See [BACKEND_AI_HANDOFF.md](BACKEND_AI_HANDOFF.md).
- P4-09 is in progress through accepted T005. T006–T008 remain pending; no
  production or live-retrieval integration is established.
- P4-10, **explicitly configured Gemini provider**, is not implemented.
- The repository contains no established frontend runtime, frontend API base
  URL, or approved server-launch command for this API baseline.
- Feature 011 has no feature-specific `quickstart.md`; its specification,
  approved contracts, tests, and recorded verification are the current
  integration references.
- Feature 005/006 database and corpus work are dependencies, not a guarantee
  that the Feature 011 HTTP endpoint already consumes real retrieval data.

## 10. Future Updates After P4-09 and P4-10

After T006 is specified, implemented, tested, reviewed, and accepted, revise
this document with the verified cross-component integration behavior and
frontend verification results. T007 and T008 remain separately gated.

After P4-10 is separately specified, implemented, tested, reviewed, and
accepted, revise it again with the explicit provider configuration path,
provider-specific failure behavior, real-answer/citation constraints, and safe
local execution instructions. Do not add Gemini credentials, keys, or live
provider calls to frontend setup or automated tests.

## 11. Key Source References

- [Feature 011 specification](../../specs/011-fake-backend-api/spec.md)
- [Feature 011 plan](../../specs/011-fake-backend-api/plan.md)
- [Feature 011 tasks](../../specs/011-fake-backend-api/tasks.md)
- [Feature 011 test log](FEATURE_011_TEST_LOG.md)
- [HTTP models](../../src/sciscope/api/http_models.py)
- [Application factory and error handlers](../../src/sciscope/api/app.py)
- [Question route](../../src/sciscope/api/routes.py)
- [Question-service contracts](../../src/sciscope/question_service/contracts.py)
- [Question-service orchestration](../../src/sciscope/question_service/service.py)
- [Deterministic fakes](../../src/sciscope/question_service/fakes.py)
- [Response validation](../../src/sciscope/question_service/validation.py)
- [Backend HTTP tests](../../tests/backend/test_question_api.py)
- [Backend & AI handoff](BACKEND_AI_HANDOFF.md)
- [Backend/AI roadmap](../../PROJECT_TODO.md)

## 12. Handoff Status

**Feature 011 v1 baseline plus accepted offline Feature 012 v2 boundary.**

This document is immediately usable for deterministic v1 and injected-offline
v2 contract work. It is not a live-backend deployment guide. T006–T008 and
P4-10 require their own approved scope, implementation, verification, review,
and acceptance evidence.
