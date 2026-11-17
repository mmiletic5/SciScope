# SciScope Architecture (Draft)

The four proposed research workflows share one path from source papers to
validated citations. Module boundaries and API contracts require owner review
before implementation.

```text
PLOS/JATS XML -> parser -> Paper/Section/Chunk -> embeddings
                         |                       |
                         +---- provenance --------+
                                  |
                       PostgreSQL + pgvector + full-text search
                                  |
                         hybrid retrieval service
                                  |
                    FastAPI orchestration + AI provider interface
                                  |
                     React/TypeScript research workflows
```

In the F003 pilot, chunk and vector artifacts are file-based (`python -m sciscope.pipeline.cli {chunk,embed,validate}`); vectors come from hosted OpenAI only through an explicit `--live` run, while local `multilingual-e5-small` remains the D-004 proposal.

Person 1 owns acquisition, parsing, chunking, embeddings, and initial golden
evaluation data. Person 2 owns storage, filtering, retrieval, ranking, and
retrieval evaluation. Person 3 owns the backend, provider interface, and answer
validation. Person 4 owns the UI and end-to-end integration. See
[team ownership](TEAM_OWNERSHIP.md) for review boundaries.

The source XML must be retained and linked to derived records. A versioned
[data contract](DATA_CONTRACT.json) describes the proposed handoff from Person 1
to Person 2. The [data model](DATA_MODEL.md) and
[chunking proposal](CHUNKING_STRATEGY.md) explain the fields. Neither the schema
nor these documents are approved implementation contracts yet.

The first provider mode is planned to be deterministic and offline, with no
API key. Gemini must require explicit selection and configuration; a future
OpenAI integration is an interface goal only. Coding assistant model
`gpt-6-luna` is separate from these application provider choices. Routine
tests and CI must stay in fake mode and make no paid AI calls.

The proposed stack is Python 3.12, FastAPI/Pydantic, PostgreSQL with pgvector
and full-text search, local `sentence-transformers` inference, React/TypeScript,
and Docker Compose. Add each dependency only in its approved feature. Failure
behavior, API shapes, retrieval ranking, and deployment topology remain open.
