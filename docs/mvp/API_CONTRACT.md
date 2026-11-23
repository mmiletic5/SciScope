# SciScope MVP API Contract (v2, frozen for the MVP sprint)

**Status:** FROZEN on 2026-11-23 for the MVP track. Changes need agreement of both
backend (`mvp-be`) and frontend (`mvp-fe`) owners and a note at the bottom of this file.
**Scope:** MVP track, no formal Spec Kit acceptance. Nothing here claims ACCEPTED status.
**Files:** `docs/mvp/api-types.v2.ts` (TypeScript types, mirror of this file),
`docs/mvp/fixtures/*.json` (synthetic examples; all invariants below hold in them).

## 1. Principles

1. `/api/v1/questions` stays untouched (fake-only, `research_question` only). The MVP
   frontend uses **v2 only**.
2. `/api/v2/questions` keeps its current envelope. Changes are additive:
   - `workflow` has four values (below); it selects prompt, output schema and retrieval profile.
   - Three workflows add one payload field each (`comparison`, `conflicts`, `gap_analysis`).
   - `research_question` responses are byte-compatible with today's v2 shape.
3. Every cited statement cites **only `chunk_id`s present in the same response's `evidence[]`**.
   No external IDs, no DOIs invented by the model. The server validates this and fails
   closed with `response_contract_failure` (HTTP 500).
4. Server owns retrieval configuration; the request never carries retrieval settings.
5. Corpus is 17 PLOS ONE honey bee papers. The UI must not imply broader coverage.

## 2. Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/v2/questions` | Run one workflow (below) |
| GET | `/api/health` | Liveness + configured component origins (no secrets, no network calls) |

Dev: Vite proxies `/api` to `http://127.0.0.1:8000`. Backend also allows CORS for
`http://localhost:5173` and `http://127.0.0.1:5173`.

### Request

```json
{
  "workflow": "evidence_comparison",
  "question": "How do papers A and B differ in the effect of treatment X?",
  "request_id": "optional-client-id-001"
}
```

`workflow` is one of `research_question | evidence_comparison | conflicting_evidence | research_gap`.
`question`: trimmed, 1-2000 chars. `request_id`: optional, `^[A-Za-z0-9._:-]{1,128}$`; the
server generates one if absent and always echoes it. Unknown fields are rejected (HTTP 422).

## 3. Response envelope (HTTP 200)

Common fields: `api_version: "v2"`, `request_id`, `workflow` (echo), `status`, `answer`,
`claims[]`, `evidence[]`, `corpus`, `metadata`.

| `status` | `answer` | `claims` | `evidence` | payload field | `metadata.answer_provider.executed` |
| --- | --- | --- | --- | --- | --- |
| `answered` | non-empty string | non-empty | non-empty | **present** (3 new workflows) | `true` |
| `insufficient_evidence` | `null` | `[]` | retrieved evidence (non-empty) | absent | `true` |
| `no_results` | `null` | `[]` | `[]` | absent | `false` |

- `no_results` = retrieval returned nothing. It does **not** mean the literature lacks an answer.
- `insufficient_evidence` = the provider declined to answer from the retrieved passages. The UI
  should still show the retrieved evidence, and say the corpus is small.
- For `evidence_comparison`, fewer than 2 distinct papers in the cited evidence -> `insufficient_evidence`.
- For `conflicting_evidence`, no potential difference identified -> `insufficient_evidence`
  (UI text: "No potential differences were identified in the retrieved passages. This does not
  show that none exist.").

### Metadata (truthful, per component)

```json
{
  "retrieval":       { "configured_origin": "real", "executed": true, "is_test_data": false },
  "answer_provider": { "configured_origin": "real", "executed": true, "is_test_data": false }
}
```

`configured_origin`: `real | fake | synthetic`. Frontend mode badge rule (also `isLiveMode()` in
the TS file): **Live** only if both components are `real`, `executed` and not `is_test_data`;
anything else is shown as **Demo (fake provider)** or **Demo (synthetic data)**. Never show
"Live" otherwise.

### 3.1 `research_question` (unchanged)

`answer` + `claims[]` (provider claims, each with `citation_chunk_ids`) + `evidence[]`.
Example: `fixtures/research_question.answered.json`.

### 3.2 `evidence_comparison` -> `comparison`

```json
"comparison": {
  "subjects": [
    { "subject_id": "subj-1", "doi": "10.x/...", "paper_title": "...",
      "summary": "...", "citation_chunk_ids": ["<chunk_id>"] }
  ],
  "similarities": [ { "item_id": "sim-1",  "text": "...", "citation_chunk_ids": ["...", "..."] } ],
  "differences":  [ { "item_id": "diff-1", "text": "...", "citation_chunk_ids": ["...", "..."] } ]
}
```

Rules: `subjects` 2-6 entries, one per paper; a subject's citations all belong to that subject's `doi`.
Every similarity/difference cites chunks from at least 2 distinct DOIs. Either list may be empty.
Example: `fixtures/evidence_comparison.answered.json`.

### 3.3 `conflicting_evidence` -> `conflicts` ("potential differences for review")

```json
"conflicts": {
  "review_note": "These are potential differences ... They are not verified contradictions.",
  "items": [
    { "item_id": "conf-1", "topic": "...", "summary": "...",
      "positions": [
        { "position_id": "conf-1-p1", "text": "...", "citation_chunk_ids": ["..."] },
        { "position_id": "conf-1-p2", "text": "...", "citation_chunk_ids": ["..."] } ] }
  ]
}
```

Rules: 1-5 items, each with >= 2 positions. Positions may come from one paper (authors vs earlier
literature) - the 17-paper corpus does not support genuine cross-paper contradictions. **The UI
must display `review_note` and must not use the words "contradiction"/"proven conflict" as a verdict.**
Example: `fixtures/conflicting_evidence.answered.json`.

### 3.4 `research_gap` -> `gap_analysis`

```json
"gap_analysis": {
  "gaps": [ { "gap_id": "gap-1", "text": "...", "citation_chunk_ids": ["..."] } ],
  "hypotheses": [
    { "hypothesis_id": "hyp-1", "text": "...", "rationale": "...",
      "based_on_gap_ids": ["gap-1"], "citation_chunk_ids": ["..."], "is_speculative": true }
  ]
}
```

Rules: >= 1 gap when answered; 0-4 hypotheses; each hypothesis references existing `gap_id`s and
cites >= 1 chunk. `is_speculative` is always `true`: **the UI must label hypotheses as
"suggested, not a finding".** Example: `fixtures/research_gap.answered.json`.

### 3.5 `claims[]` for the three new workflows

Server-derived, flattened: one `Claim` per cited statement in the payload, in payload order
(`claim_id` = subject/item/position/gap/hypothesis id). It exists so generic citation
validation and `CitationMarker` keep working. **Render the payload, not `claims`.**

## 4. Errors

Envelope (not `status`-based): `{ api_version: "v2", request_id, error: { code, message, retryable }, metadata? }`.
`metadata` is absent on 422 and when no component ran.

| HTTP | `error.code` | `retryable` |
| --- | --- | --- |
| 422 | `invalid_request` | false |
| 503 | `retrieval_unavailable` / `provider_unavailable` | true |
| 504 | `dependency_timeout` | true |
| 500 | `response_contract_failure` | false |
| 500 | `internal_error` | false |

Messages are sanitized (no provider text, no keys, no SQL). Examples: `fixtures/error.*.json`.

## 5. Health

`GET /api/health` -> `fixtures/health.json`. `components.*.configured_origin` drives the
header badge before any question is asked. No secrets are ever returned.

## 6. Server behavior the frontend can rely on

- Retrieval profile per workflow (server-side): `retrieval.v2`, `hybrid`, candidate pool 50;
  `top_k` 5 for `research_question`, 10 for the other three. Not exposed in the request.
- Answer provider is selected by server env (`AI_PROVIDER=fake|openai`). The frontend only
  reads `metadata` / `/api/health`.
- Timeouts: provider and retrieval have bounded budgets; the frontend keeps its 30 s client
  timeout but should allow up to 60 s for the three new workflows (more evidence, longer output).

## 7. Changelog

- 2026-11-23: initial freeze (v2 + three workflows + health).
