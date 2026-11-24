# Individual contributions (CAP-08)

Each section was written by the team member it describes. Commit links point to
https://github.com/mmiletic5/sciscope.

## Dušan Nikolić (GitHub: Dusan-Nikolic-98)

**What I did.** Data side (Person 1): PLOS ONE pilot acquisition of 17 papers, a JATS
parser with section locators, section-aware chunking, OpenAI embeddings
(`text-embedding-3-small`, 1536 dimensions), the data contract and delivery package,
and Golden v0 (21 verified questions). MVP track: froze API contract v2; wrote the
OpenAI query embedder and the grounded answer provider with a per-workflow prompt
registry for all four workflows; the env-configured server with health endpoint and
CORS; the guarded pilot import script; the live smoke script; the opt-in agentic
retrieval stage; demo readiness (Cancel and elapsed time, example questions, citation
highlight, removal of internal ids from text); the demo script; and the Capstone
evaluation EV-01..EV-16.

**Why this approach.** Citations may only name chunks that were actually retrieved
(an enum of allowed chunk ids plus server-side validation). The fake provider stays
the default and live OpenAI is an explicit opt-in. All four workflows share one RAG
path instead of four separate systems.

**How I checked it.** Live smoke of the five development questions through real
Postgres and the real model; 3399 offline tests; EV-01..EV-16 in
`docs/mvp/EVAL_RESULTS.md`, with EV-01 and EV-04 compared by hand against the source
papers; 170/170 retrieval tests on a disposable database loaded with the pilot; a
manual run of all four screens in Live mode.

**Where it fits.** Request → retrieval → grounded model call → validated response,
joining Isidora's retrieval, Mateja's API layer and Milena's screens.

**Limits.** Only five development questions were exercised; there is no held-out
evaluation; the corpus is the 17-paper pilot; agentic mode showed no measured quality
gain (one question, three runs); refusals for unclear questions and for missing
comparison halves both return `insufficient_evidence` without saying which reason
applies.

**Review of a colleague's work.** Milena and I did the final demo stage together:
she reviewed my changes, ran them locally and checked behaviour on the demo
questions; I reviewed her screens and checked each one manually in Live mode. While
integrating Mateja's retrieval adapter with the real database, every live request
failed with `response_contract_failure`; I traced it to filters being `None` in one
place and an empty `RetrievalFilters` in another, and fixed the adapter
([cff0593](https://github.com/mmiletic5/sciscope/commit/cff0593)). On Milena's
Evidence Comparison screen I noticed raw chunk ids in the answer text, which led to a
server-side sanitizer and a defensive UI strip
([cfec403](https://github.com/mmiletic5/sciscope/commit/cfec403),
[fee7960](https://github.com/mmiletic5/sciscope/commit/fee7960)), verified by five
repeated runs and the full smoke with `ids_in_text=false`.

**AI example.** The assistant suggested the answer model `gpt-5.4-mini`. It was a
guess: live calls failed with 503 `model_not_found`. I listed the models available to
the project, found only `gpt-6-luna`, set `OPENAI_ANSWER_MODEL` accordingly and
confirmed with the smoke run.

Evidence: [contract v2](https://github.com/mmiletic5/sciscope/commit/759a820),
[OpenAI provider](https://github.com/mmiletic5/sciscope/commit/d88b077),
[import script](https://github.com/mmiletic5/sciscope/commit/1315ead),
[four workflows](https://github.com/mmiletic5/sciscope/commit/4371e96),
[agentic retrieval](https://github.com/mmiletic5/sciscope/commit/fa7e5a0).

## Milena Paripović (GitHub: Milenica88)

**What I did.** The SciScope frontend (Person 4; Vite, React, TypeScript): the
Research Question Explorer, an API v2 client with strict response validation and a
fixture mode for working without the backend, the Live/Demo badge driven by response
metadata, and the real Evidence Comparison, Potential Differences and Gaps &
Hypotheses screens that replaced the preview versions. I also prepared and presented
the team's presentation at the consultations.

**Why this approach.** I chose strict response validation so that the user never sees
unvalidated content or a citation that does not exist among the evidence. The fixture
mode let me progress in parallel with the backend.

**How I checked it.** Tests written before the code (Vitest and Testing Library,
217 tests in 20 files), plus lint, typecheck and build, an end-to-end test in fixture
mode, and a manual pass through the screens (keyboard use, 390 px width). At the end
I ran the whole system locally with the real database and OpenAI and tried it on the
demo (development) questions.

**Where it fits.** The frontend is the only way a user reaches the system: it sends
the question to `/api/v2/questions` for the chosen workflow and shows the answer,
claims with citations, and sources with DOIs.

**Limits.** No filters (P5-04); evidence items have no authors, year or section
because the API does not return them; the frontend is not in CI; the end-to-end test
runs only in fixture mode; accessibility has not been formally reviewed.

**Review of a colleague's work.** I reviewed Mateja's API v2 against my frontend. I
noticed that the metadata no longer has `is_mock` but separate data for the retrieval
and the answer provider, and adjusted the validation and the header badge
accordingly. I also noticed that the CORS preflight returned 405, so I used the Vite
proxy until Dušan's server with CORS was ready. On Isidora's database I confirmed
that after the import the `delivery_digest` equals the SHA256 of the official
`delivery_manifest.json`, so my local database is identical to hers.

**AI example.** I developed the frontend with Codex following the Spec Kit process
and approved every step. In one suggestion the "Try again" button resent the old
question instead of the text currently in the field. I did not accept it and asked
for a fix and a regression test; I checked that the test failed first and passed
after the fix, and repeated the manual pass. I handled dismissing notices (valid for
one result only), the 30 s timeout and a single `<main>` element on the page the same
way.

**Shared work.** For the final stage before the demo I worked with Dušan: I
supervised and he implemented. Dušan did the server with CORS and the OpenAI
connection, agentic retrieval and the demo polish (Cancel and elapsed time, example
questions, citation highlight, removal of internal ids from text). I reviewed the
changes, ran them locally and checked behaviour on the demo questions.

Evidence: [explorer](https://github.com/mmiletic5/sciscope/commit/7b373a1),
[client v2](https://github.com/mmiletic5/sciscope/commit/d35f7f3),
[mode badge](https://github.com/mmiletic5/sciscope/commit/3ed386e),
[comparison screen](https://github.com/mmiletic5/sciscope/commit/60e1a2f),
[differences screen](https://github.com/mmiletic5/sciscope/commit/1f91588),
[gaps screen](https://github.com/mmiletic5/sciscope/commit/73cd3b0).

## Isidora Prica

**What I did.** Database and retrieval (Person 2), owner of the retrieval core:
PostgreSQL with pgvector (migration and compose setup), validated snapshot ingestion,
retrieval v1 (dense, full-text, fusion) and retrieval v2 (BM25 with reciprocal rank
fusion and an optional MiniLM reranker), the retrieval evaluation protocol and
tooling, Golden v1 preparation scripts, handoff documents for Persons 1 and 3, and CI
fixes ([foundation](https://github.com/mmiletic5/sciscope/commit/20a1f4a),
[CI](https://github.com/mmiletic5/sciscope/commit/dec032c)).

**Why this approach.** Hybrid retrieval, because exact scientific terms and
paraphrased questions both occur. The reranker was benchmarked rather than assumed.

**How it was checked.** Development comparison on the five approved questions
(`docs/person2/RETRIEVAL_V2_RESULTS.md`): hybrid v2 reached Recall@10 0.875 and
Recall@20 1.0, tying dense retrieval at those cut-offs but not beating it on Recall@5
or MRR@10. The reranker added about 4.2 s median latency without a quality
improvement, so it is disabled by default. 208 offline evaluation tests passed, 14
read-only PostgreSQL integration tests passed, and all 1250 returned hits resolved to
the exact chunk text, DOI and locator. Milena independently confirmed that the
delivery digest of a freshly imported database equals the official manifest checksum.

**Where it fits.** The MVP runs retrieval v2 hybrid with a candidate pool of 50 for
all four workflows. Mateja's facade and adapter preserve the DOI and chunk ids it
returns.

**Limits.** Five development questions only, no held-out result and no statistical
claim; the v1 full-text arm returned no candidates in this comparison.

## Mateja Miletić (GitHub: mmiletic5)

**What I did.** Backend & AI (Person 3): Feature 011 (fake AI provider and the
FastAPI question API), the public `RetrievalService` facade in Feature 007/T007, and
the retrieval integration through T005 of Feature 012. In T007 I implemented
versioned public retrieval DTO contracts, typed errors, the facade and conformance
tests, prepared the PostgreSQL integration verification and coordinated with Person
2, who owned the retrieval core. In Feature 012 I implemented the retrieval adapter
that preserves source identifiers and provenance metadata, controlled error handling,
citation validation, and application composition with explicit engine lifecycle
management
([API](https://github.com/mmiletic5/sciscope/commit/969700c),
[fail-closed validation](https://github.com/mmiletic5/sciscope/commit/65375fe),
[facade](https://github.com/mmiletic5/sciscope/commit/d226266),
[composition](https://github.com/mmiletic5/sciscope/commit/caf3c57)).

**Why this approach.** I chose dependency injection, public interfaces and separate
v1/v2 API contracts to allow deterministic offline testing and to keep clear
boundaries between backend logic, database infrastructure and private retrieval
implementation details.

**How I checked it.** RED/GREEN testing, pytest regression suites, Ruff and mypy
checks, independent test reruns, and documented evidence before accepting changes.

**Where it fits.** My work established the connection between the retrieval layer and
the Backend & AI API consumed by the frontend; the four v2 workflows were later built
on top of it.

**Limits.** Full Feature 012 integration, production-level PostgreSQL verification
and live AI provider integration were outside the scope of my final verification and
were handed over to teammates (the live provider was later integrated with OpenAI;
the planned Gemini provider was not built). The v1 endpoint returns 500 when
component metadata is present, so v2 is the supported path.

**Review of a colleague's work.** I examined the public retrieval contracts and
behaviour of the retrieval core developed by Person 2 and confirmed that the facade
and adapter preserved DOI values, chunk ids and other provenance information without
modifying the retrieval algorithms.

**AI example.** I used Codex to assist with tests and implementation but reviewed and
corrected its suggestions. For example, during T005 an incompatible shutdown-handler
registration was corrected, followed by successful lifecycle tests and regression
checks.