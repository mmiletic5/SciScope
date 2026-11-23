# MVP demo script (5-8 minutes)

Lean-mode MVP track; nothing here is ACCEPTED. Corpus: 17 PLOS ONE honey bee papers.
Run the five questions below once before the demo; they are the only questions
exercised so far (live smoke, see `EVIDENCE.md`). Questions are copied verbatim from
`evals/golden_questions.v0.json`.

Before you start: header badge shows **Live** (both retrieval and answer provider are real).
A live answer takes roughly 2-8 s in the smoke run; the UI allows up to a minute and has a Cancel button.

## Plan

| # | Time | Screen (workflow) | Question id |
| --- | --- | --- | --- |
| 1 | ~1.5 min | Research question (`research_question`) | gq-sp-001 |
| 2 | ~1.5 min | Evidence comparison (`evidence_comparison`) | gq-cmp-001 |
| 3 | ~1.5 min | Potential differences (`conflicting_evidence`) | gq-conf-001 |
| 4 | ~1.5 min | Gaps & hypotheses (`research_gap`) | gq-gap-001 |
| 5 | ~1 min | Research question (`research_question`) | gq-ins-001 |

Paste each question into the form (example chips only prefill their own examples).

### 1. Single-paper factual question (gq-sp-001)
> In the experiment where forager bees were injected with a virus and then tracked with tags at the hive entrance, on which days after injection did the proportion of foragers coming back differ significantly from sham-injected controls, and how large was the gap on the first of those days?

- Point at: the answer, the numbered citation markers (click one: it scrolls to the source card and highlights it for about 2.5 s), the source cards with paper title and DOI link, the **Live** badge.
- Conclude: the answer is tied to specific retrieved passages that can be checked.

### 2. Evidence comparison (gq-cmp-001)
> How does sensitivity to sugar water change in foragers exposed to a toxic mineral versus foragers infected with a virus?

- Point at: one card per paper, the similarities and differences, each with citation markers, and the source cards.
- Conclude: the comparison is built from at least two papers, each statement traceable to a passage.

### 3. Potential differences (gq-conf-001)
> Is the literature consistent on whether Varroa parasitism suppresses or boosts immune gene expression in developing worker bees?

- Point at: the **Review note**, the heading "Potential differences for review", the cited items.
- Conclude: the tool surfaces candidates for a human to review; it does not rule on contradictions.

### 4. Gaps & hypotheses (gq-gap-001)
> What do the authors say their comparison of virus levels in colonies selected for low and high mite growth cannot settle, and what would they do next?

- Point at: the gaps (cited), then the hypotheses with the **"Suggested, not a finding"** label.
- Conclude: gaps come from the retrieved evidence; hypotheses are suggestions only.

### 5. Insufficient evidence (gq-ins-001)
> Does exposure to a glyphosate-based herbicide change the composition of the bee gut microbiota?

- Point at: the "insufficient evidence" state instead of an invented answer. (In the smoke run this question returned `insufficient_evidence` with no claims.)
- Conclude: when the corpus does not cover a topic, the system says so.

## What to say about limits

- The corpus is 17 PLOS ONE honey bee papers; the tool says nothing about the wider literature.
- Answers are generated from retrieved passages and may be wrong. Check the cited sources.
- Conflicts are "potential differences for review", not verified contradictions.
- Hypotheses are suggestions, not findings.
- Only these 5 development questions were exercised. There is no held-out evaluation and no statistical quality claim.

## Failure plan

**(a) OpenAI or network is down.** Start the backend in zero-config fake mode (no DB, no network):
```powershell
$env:PYTHONPATH = "src"
uv run --locked python -m sciscope.api.server
```
The badge shows **Demo (fake provider)** (or Demo (synthetic data)). Say so out loud: answers are
placeholder text from synthetic papers, shown only to demonstrate the screens.

**(b) Backup screenshots** in `docs/mvp/demo/` (added by the project owner):
`screenshot-1-question.png`, `screenshot-2-comparison.png`, `screenshot-3-conflicts.png`, `screenshot-4-gaps.png`.

**(c) Restart checklist**
1. Docker Desktop running; `docker compose ps` shows the `db` container **healthy** (else `docker compose up -d db`).
2. `.env` present in the repo root (gitignored; has `DATABASE_URL`, `OPENAI_API_KEY`, `OPENAI_ANSWER_MODEL`).
3. Backend (live), from the repo root; set `AI_PROVIDER` and `RETRIEVAL_BACKEND` in the shell
   (`.env` is loaded by `--env-file` only if it defines them):
   ```powershell
   $env:PYTHONPATH = "src"
   $env:RETRIEVAL_BACKEND = "postgres"; $env:AI_PROVIDER = "openai"
   uv run --locked --env-file .env python -m sciscope.api.server
   ```
4. Frontend: `cd frontend; npm run dev`, open http://localhost:5173.
5. `curl.exe http://127.0.0.1:8000/api/health` responds; badge shows **Live**.
(Health shows configured origins only; it does not probe the DB or OpenAI.)
