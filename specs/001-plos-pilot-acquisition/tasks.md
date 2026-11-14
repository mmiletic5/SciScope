# Tasks: PLOS pilot acquisition

**Input**: `spec.md`, `plan.md`, `research.md` in this directory. **Owner**: Person 1 throughout. **Gate**: No tests or implementation until explicit approval of `spec.md` and `plan.md`. No task is marked complete before automated checks and human acceptance are recorded.

## Phase 1: Setup

- [ ] T001 Person 1: Create `src/sciscope/__init__.py` and `src/sciscope/plos_pilot/__init__.py`; define six query arms, `doc_type:full` and `article_type:"research article"` filters, `fl=id,title,journal,publication_date,abstract`, row cap, 6.0-second spacing, 300-request run cap, and fixed hosts in `src/sciscope/plos_pilot/config.py`; first write configuration/arm behavior tests in `tests/plos_pilot/test_config.py`, demonstrate RED then GREEN; check exact arm coverage and limits. Depends on approved spec/plan. Covers FR-001, FR-004.

## Phase 2: Foundational

- [ ] T002 Person 1: Implement original-value-preserving DOI normalization and defensive URL `id` extraction in `src/sciscope/plos_pilot/doi.py`; first write at least 12 table-driven cases in `tests/plos_pilot/test_doi.py`, demonstrate RED then GREEN; check every FR-005 prefix, punctuation, bracket, decode, lowercase, and invalid-input rule. Depends on T001. Covers FR-005.

## Phase 3: User Story 1 — Human candidate review (P1)

**Independent check**: Mocked search writes all six arm counts and deduplicated candidates with complete arm provenance; a human can screen without an assigned relevance class.

- [ ] T003 [US1] Person 1: Implement paged Solr search, sequential request spacing, retry/resume behavior, candidate JSONL output targeting `data/pilot/candidates.jsonl`, and arm counts in `src/sciscope/plos_pilot/search.py`; first write mocked HTTP response/failure tests with labeled synthetic fixtures and injected HTTP fetch and sleep/clock callables in `tests/plos_pilot/test_search.py`, demonstrate RED then GREEN without network or real sleeping; check `q`, both `fq`, `numFound`, UTC date, Solr `id`, `title`, `journal`, `publication_date`, `abstract`, DOI deduplication, hit-count wording, `rows<=100`, 6.0-second spacing, 300-request cap, retry/backoff, and interruption. Depends on T001–T002. Covers FR-001–FR-002, FR-004.
- [ ] T004 [US1] Person 1: Define and validate `data/pilot/screening.tsv` and the exact `doi`, `class`, `reason`, `topic`, `methods_checked` columns of `data/pilot/selection.tsv` in `src/sciscope/plos_pilot/selection.py`; first write validation tests in `tests/plos_pilot/test_selection.py`, demonstrate RED then GREEN; check 15–20 unique reviewed candidate DOIs, the six FR-003 classes, `methods_checked=yes` for `honey_bee_unqualified` (empty allowed otherwise), reasons, at least three distinct topics, included-only selection, screening records only for reviewed candidates, and rejection of a selected normalized DOI missing from committed `data/pilot/candidates.jsonl`. The human populates both TSV files during T008, not this code task. Depends on T003. Covers FR-003.

## Phase 4: User Story 2 — Acquire selected sources (P2)

**Independent check**: With mocked XML, only selected DOIs are requested, accepted records match their raw XML and digest, and duplicates/conflicts/failures remain visible.

- [ ] T005 [US2] Person 1: Implement JATS retrieval for DOIs listed only in `data/pilot/selection.tsv`, resolving each selected normalized DOI's journal and all query-arm provenance from committed `data/pilot/candidates.jsonl`; reject missing candidate DOIs. Implement XML validation, atomic raw storage targeting `data/raw/plos/` + `urllib.parse.quote(normalized_doi, safe='')` + `.xml`, manifest JSONL output targeting `data/pilot/manifest.jsonl`, duplicate/conflict detection, sequential spacing, 300-request cap, retry/resume logic in `src/sciscope/plos_pilot/download.py`; first write mocked HTTP/JATS behavior tests with labeled synthetic XML and injected HTTP fetch and sleep/clock callables in `tests/plos_pilot/test_download.py`, demonstrate RED then GREEN without network or real sleeping; check fixed HTTPS PLOS hosts, DOI/JATS `article-type="research-article"`/language/license gates, every matching arm's provenance, UTC time, SHA256, unselected DOI exclusion, preserved conflict evidence, and `git check-ignore data/raw/plos/probe.xml`. Depends on T001–T004; verify selected journal routes and the JATS article-type value before live retrieval. Covers FR-004, FR-006, FR-008.
- [ ] T006 [US2] Person 1: Extract only JATS front matter into output targeting `data/pilot/metadata.jsonl` via `src/sciscope/plos_pilot/metadata.py`; first write synthetic JATS tests in `tests/plos_pilot/test_metadata.py`, demonstrate RED then GREEN; check title, ordered authors, journal, publication date, article type, subjects, abstract, license, language, missing-field errors, and absence of body/section fields. Depends on T005. Covers FR-007.

## Phase 5: Polish and verification

- [ ] T007 Person 1: Provide `search` and `download` commands plus accepted/duplicate/conflict/failed/pending summary in `src/sciscope/plos_pilot/cli.py`; first write mocked command-flow tests in `tests/plos_pilot/test_cli.py`, demonstrate RED then GREEN; check search never downloads, download obtains its DOI list only from `data/pilot/selection.tsv`, and selected DOI lookup in `data/pilot/candidates.jsonl` supplies journal and provenance. Depends on T003–T006. Covers FR-002, FR-004, SC-001–SC-003.
- [ ] T008 Person 1: Run offline checks and the live PowerShell verification in the user's terminal; produce `data/pilot/candidates.jsonl`, `data/pilot/screening.tsv`, `data/pilot/selection.tsv`, `data/pilot/manifest.jsonl`, `data/pilot/metadata.jsonl`, and `data/raw/plos/` XML there, then append observed automated and human results to `EVIDENCE.md` and synchronize `PROJECT_TODO.md` and this `tasks.md` only after explicit human acceptance; check 15–20 selected real PLOS research articles, XML-derived license/language, digest/file agreement, at least three human-assigned topics, resume, and visible errors. Depends on T001–T007 and approved spec/plan. Covers SC-001–SC-004. Leave task unchecked until evidence and acceptance exist.

## Dependencies and execution

T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008. US1 defines candidate and selection behavior before live selection; US2 downloads only selected DOIs and uses candidate records solely to resolve journal and provenance. Pilot data files are produced during T008 in the user's terminal, not by code tasks in the agent sandbox. No parallel task marker is used because each task depends on the previous deliverable. Each code task uses its listed test first (RED), the smallest implementation (GREEN), and a recorded acceptance check. Human decisions are not simulated by tests.

## One PowerShell command set for manual verification (user terminal, after implementation)

```powershell
$env:PYTHONPATH = 'src'
uv run --locked python -m pytest tests/plos_pilot -q
uv run --locked python -m sciscope.plos_pilot.cli search
# Person 1 reviews candidates until 15–20 qualify. Only reviewed candidates
# appear in data/pilot/screening.tsv; selection.tsv contains 15–20 included
# DOI rows with class, short reason, topic, and methods_checked (yes for
# honey_bee_unqualified; otherwise it may be empty). Journal and all matching
# query-arm provenance come from committed data/pilot/candidates.jsonl.
uv run --locked python -m sciscope.plos_pilot.cli download
uv run --locked python -m sciscope.plos_pilot.cli download
git check-ignore data/raw/plos/probe.xml
git status --short
```

Expected: offline tests pass without live HTTP or real sleeping; search reports six `numFound` hit counts and candidate provenance plus Solr screening fields; the human selects 15–20 unique eligible DOIs across at least three topics; the first download produces matching raw XML, manifest, and metadata for accepted selections or explicit failures; the second reports equal-digest duplicates without extra articles and changed-digest conflicts without overwrite. `git check-ignore` prints the probe path, while `data/pilot/` records are reviewable for commit. Before `download`, use the selected journal pages and PLOS XML URL pattern to verify each route and inspect the XML license, JATS `article-type="research-article"`, and language; report any route or field failure rather than guessing. Person 1 reports observed counts, failures, and explicit acceptance/rejection. Then record evidence and sync task states; no task is complete on command output alone.
