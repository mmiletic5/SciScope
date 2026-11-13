# Team Ownership and Review (Draft)

The role identifiers are Person 1 through Person 4; no individual names are
assigned here. The team has approximately 15 development days, so tasks should
remain small and independently reviewable.

| Role | Primary ownership | Required collaboration |
| --- | --- | --- |
| Person 1 | PLOS/JATS source processing, metadata, chunking, embeddings, initial golden dataset | Person 2 reviews data contract and evaluation requirements |
| Person 2 | PostgreSQL, pgvector, full-text search, filters, hybrid retrieval, ranking, retrieval evaluation | Person 1 reviews import and source locator use |
| Person 3 | FastAPI, fake and Gemini provider integration, validation, backend reliability | Person 2 reviews retrieval interface; Person 4 reviews API contract |
| Person 4 | React/TypeScript UI, filters, citations, comparisons, end-to-end integration | Person 3 reviews API integration |

Shared contracts, including [DATA_CONTRACT.json](DATA_CONTRACT.json), API
shapes, source locators, and evaluation labels, require affected owner review
before dependent work. The master [TODO](../PROJECT_TODO.md) tracks ownership;
[EVIDENCE.md](../EVIDENCE.md) tracks verification. A reviewer and CI are required
before a feature branch merges to stable `main`.

Proposed first feature: **Feature 001 — Honeybee Corpus Discovery, Data
Contract, and Golden Evaluation Dataset**. Person 1 owns its data and
evaluation artifacts; Person 2 reviews its contract and evaluation
requirements. Person 3 can independently plan the Fake AI Provider as a later,
parallel development feature. Neither is approved for implementation by this
bootstrap.
