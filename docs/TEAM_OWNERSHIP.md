# Team Ownership and Review (Draft)

The role identifiers are Person 1 through Person 4; no individual names are
assigned here. The team has approximately 15 development days, so tasks should
remain small and independently reviewable.

| Role | Primary ownership | Required collaboration |
| --- | --- | --- |
| Person 1 | PLOS/JATS source processing, metadata, chunking, embeddings, initial golden dataset | Person 2 reviews data contract and evaluation requirements |
| Person 2 | PostgreSQL, pgvector, full-text search, filters, hybrid retrieval, ranking, retrieval evaluation | Accepts Person 1 data-contract decisions; Person 1 reviews import and source locator use |
| Person 3 | FastAPI, fake and Gemini provider integration, validation, backend reliability | Person 2 reviews retrieval interface; Person 4 reviews API contract |
| Person 4 | React/TypeScript UI, filters, citations, comparisons, end-to-end integration | Person 3 reviews API integration |

Shared contracts, including [DATA_CONTRACT.json](DATA_CONTRACT.json), API
shapes, source locators, and evaluation labels, go through a PR with the
affected owner as reviewer before dependent work. The master
[TODO](../PROJECT_TODO.md) tracks ownership;
[EVIDENCE.md](../EVIDENCE.md) tracks verification. A reviewer and CI are required
before a feature branch merges to stable `main`.

**F001 — PLOS pilot acquisition (15–20 papers)** is Person 1's first feature.
Person 2 accepts Person 1's data-contract decisions and reviews the affected
contract PR. The Fake AI Provider remains Person 3's parallel feature.
