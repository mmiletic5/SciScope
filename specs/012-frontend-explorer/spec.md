# Feature Specification: Frontend Research Question Explorer

**Feature Branch**: `012-frontend-explorer`

**Created**: 2026-11-22

**Status**: Approved; implementation authorized through T007, with T008 gated on the Explorer demo walkthrough

**Input**: User description: Build the first SciScope frontend feature: a Research Question Explorer that works end-to-end with the accepted Feature 011 fake API, alongside static previews of the other research workflows.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ask a research question and inspect its sources (Priority: P1)

A researcher enters a question or chooses an example, submits it, and reviews the returned answer alongside the claim-linked source passages. They can follow a citation marker to its source card and open the paper DOI.

**Why this priority**: This is the first working SciScope workflow and the only feature connected to the backend in this release.

**Independent Test**: Submit a valid question against a controlled successful service response and verify the answer, claim citations, source cards, DOI link, provenance, and mock-data notice.

**Acceptance Scenarios**:

1. **Given** the initial page, **When** the user chooses an example question, **Then** it fills the editable question field without submitting it.
2. **Given** a question containing 1–2,000 non-whitespace characters after trimming, **When** the user searches, **Then** the page shows a loading state and sends the supported research-question request with a valid request reference.
3. **Given** an answered response, **When** it is displayed, **Then** the answer and claims appear separately, citations follow first-citation order, and each citation resolves only to a matching response evidence item.
4. **Given** a numbered citation, **When** the user activates its source button, **Then** the matching source card is brought into view and highlighted.
5. **Given** response evidence not cited by any claim, **When** the result is displayed, **Then** it appears under “Other retrieved passages” without a citation number.
6. **Given** a source with a DOI, **When** the user opens its DOI link, **Then** the link targets `https://doi.org/<doi>` in a new tab with safe opener/referrer behavior.

### User Story 2 - Understand empty, uncertain, synthetic, and failed results (Priority: P2)

A researcher can tell the difference between no retrieved passages, insufficient evidence, a retryable service problem, and synthetic test data. They can correct or retry a question without losing it.

**Why this priority**: Clear result and failure states prevent synthetic output or backend failures from being mistaken for scientific findings.

**Independent Test**: Provide each supported successful status and representative error envelope, then verify the corresponding state, safe message, retry affordance, and retained input.

**Acceptance Scenarios**:

1. **Given** the service reports that no relevant passages were found, **When** the result is displayed, **Then** the page says “No relevant passages were found in the corpus.” and suggests rephrasing.
2. **Given** the service reports insufficient evidence, **When** the result is displayed, **Then** the page says “Not enough evidence to answer”, explains that the system declined rather than guess, and shows retained evidence as unnumbered “Closest passages found”.
3. **Given** a service error, **When** it is displayed, **Then** a friendly message is shown without raw backend details, the response reference is available for support, and “Try again” appears only when the error is marked retryable.
4. **Given** the API cannot be reached, **When** the request fails, **Then** the page says “Cannot reach the SciScope API. Is the backend running?”, offers retry, and keeps the question editable.
5. **Given** a response is marked as mock or test data, **When** it is displayed, **Then** the synthetic-data notice appears, can be dismissed for that result only, and returns with the next mock/test-data response.
6. **Given** a request is pending, **When** the user views the results area, **Then** it announces that results are busy, shows the loading message and skeleton content, and prevents duplicate submissions.
7. **Given** a response, **When** the user opens “About this result”, **Then** the corpus version, source contract version, and delivery digest are available.
8. **Given** a request remains pending for 30 seconds, **When** the timeout is reached, **Then** the request is aborted, a retryable timeout error says “The request took too long. Please try again.”, and the question remains editable.
9. **Given** the backend is stopped and the Vite proxy returns HTTP 5xx without a valid API error envelope, **When** the user submits a question, **Then** the page shows the retryable API-unreachable message and keeps the question editable.

### User Story 3 - Preview the other research workflows (Priority: P3)

A researcher can explore the intended shape of evidence comparison, conflicting evidence, and research gaps while understanding that those workflows are not connected yet.

**Why this priority**: The preview screens support the team demo while keeping unimplemented research behavior clearly separated from the working workflow.

**Independent Test**: Select each preview navigation item and verify its preview banner, named placeholder layout, and lack of invented findings.

**Acceptance Scenarios**:

1. **Given** the app shell, **When** the user selects one of the three preview sections, **Then** the selected section is visibly and accessibly identified and shows “Preview — this feature is not connected to the backend yet.”
2. **Given** the Evidence comparison preview, **When** it is shown, **Then** it includes Stressor, Control group, Measure, Sample, Result, and Claim source rows and two paper columns containing “[paper selected from results]”.
3. **Given** the Conflicting evidence preview, **When** it is shown, **Then** it includes Position A, Position B, and Possible reasons cards for Experimental conditions, Sample, and Methods, with placeholder text only.
4. **Given** the Gaps & hypotheses preview, **When** it is shown, **Then** it includes “What is missing”, “What was found”, and a dashed “Draft hypothesis · model suggestion · not a verified finding” box whose Save, Edit, and Dismiss controls are disabled.

### Edge Cases

- Whitespace-only input is rejected; trimmed input under 1 character or over 2,000 characters cannot be submitted, and an inline error explains the limit.
- Unknown citation chunk IDs do not create markers; repeated IDs do not create duplicate source numbers; evidence never cited by a claim remains unnumbered.
- If no claims cite evidence, every evidence item is unnumbered and presented as other retrieved passages.
- A malformed JSON body or invalid envelope on HTTP 200 or 4xx produces a safe generic nonretryable error; the question remains editable. Any HTTP 5xx without a valid API error envelope is treated as retryable API-unreachable, including an HTML proxy response.
- A request still pending after 30 seconds is aborted and treated as a retryable timeout; the timeout message is “The request took too long. Please try again.”
- Retry resubmits the current question and does not clear it. Only a server error marked retryable or an unreachable API exposes the retry action.
- A long DOI, passage, or navigation label must not cause horizontal page overflow at a 390 px viewport width.
- Every interactive control is keyboard-operable and retains a visible focus indicator; state updates are announced to assistive technology.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The application MUST present a SciScope header with a simple inline hexagon mark, navigation for Research question, Evidence comparison, Conflicting evidence, and Gaps & hypotheses, plus the footer note “SciScope is a research aid and does not replace reading the original papers.” The “MOCK · test data” badge MUST be visible by default and whenever the latest response marks either `is_mock` or `is_test_data` true. It may be hidden only after a response explicitly reports both values as false.
- **FR-002**: The application MUST identify the selected navigation item accessibly. Research question is connected; the other three items open static previews with a clear preview banner.
- **FR-003**: The research-question view MUST provide a field labelled “Research question”, a primary “Search” action, a live character count, client validation of trimmed length from 1 through 2,000, and an inline validation message. It MUST retain the editable question after responses and errors.
- **FR-004**: The initial research-question view MUST explain the workflow and provide two or three English example questions sourced from Golden Questions v0 as fill-in actions. It MUST NOT display expected answers from that dataset.
- **FR-005**: For each valid submission, the application MUST create a valid request reference and send only the approved research-question request to the existing question service. It MUST NOT send unsupported filter or provider choices.
- **FR-006**: While a request is pending, the application MUST disable repeat submission, show the Search button's loading indicator and label, and show an accessible busy result area with skeleton content and “Retrieving passages and checking citations…”.
- **FR-007**: For an answered result, the application MUST present the answer and each claim separately. It MUST number sources by first occurrence in claim citation order, resolve citations only by matching claim references to source identifiers in the same result, ignore unknown IDs, and leave uncited evidence unnumbered.
- **FR-008**: Each numbered citation MUST be a keyboard-operable source button with an accessible name such as “Source 1” that scrolls to and highlights its matching source card. A source card MUST show its number, paper title, DOI link when present, and passage. The source location MUST be available only in a “Details” disclosure. The DOI link MUST open in a new tab with safe opener/referrer behavior. The interface MUST NOT display author, publication-year, or section information absent from the approved contract.
- **FR-009**: Uncited evidence in an answered response MUST appear under “Other retrieved passages” without numbers. Evidence retained when the service declines to answer for insufficient evidence MUST appear as “Closest passages found”, also without citation numbers.
- **FR-010**: The application MUST show the specified neutral message and rephrasing hint when no relevant passages are found, and the specified decline-to-guess explanation when evidence is insufficient.
- **FR-011**: For service errors, the application MUST map known error types to friendly messages, avoid rendering raw backend details, preserve the user’s question, retain the response reference as a small “Reference: …” value, and show “Try again” only when the service marks an error retryable. A fetch rejection or HTTP 5xx without a valid API error envelope MUST be treated as retryable API-unreachable and use “Cannot reach the SciScope API. Is the backend running?”. Malformed JSON or an invalid envelope under HTTP 200 or 4xx MUST show a generic safe nonretryable error.
- **FR-012**: The application MUST provide an above-results notice reading “Responses are synthetic test data from the fake backend, not real literature.” whenever the current result is marked as mock or test data. The user may dismiss the notice for the currently displayed result only. The notice MUST reappear with every new mock/test-data response. The header badge remains visible according to FR-001.
- **FR-013**: The “About this result” disclosure MUST display the reported corpus version, source contract version, and delivery digest.
- **FR-014**: The Evidence comparison preview MUST show the six specified comparison rows and two paper placeholder columns. The Conflicting evidence preview MUST show two position cards and the three specified possible-reason cards. The Gaps & hypotheses preview MUST show the two gap cards and the specified draft-hypothesis placeholder with disabled Save, Edit, and Dismiss actions. Preview content MUST not assert scientific findings.
- **FR-015**: The interface MUST use semantic, accessible controls; announce result-state changes politely; provide accessible names for icon-only controls; preserve visible focus indicators; and support keyboard operation.
- **FR-016**: The responsive interface MUST remain usable at 390 px viewport width without horizontal page overflow. Text MUST have at least 4.5:1 contrast. The layout MUST be centered and no wider than 1,200 px, with a readable results column of about 760 px. Navigation MUST wrap or scroll on narrow screens.
- **FR-017**: The visible design MUST follow the supplied visual direction: IBM Plex Sans for interface text and IBM Plex Mono for DOI, citation, and reference text; text `#1B1F24`, secondary text `#5B6470`, page `#F6F7F9`, surface `#FFFFFF`, border `#DDE1E6`, input border `#C9CED5`; honey actions `#B45309` (hover `#92400E`, tint `#FEF3E2`, tint text `#7C3A06`); blue links, citation, and focus `#1D4ED8` (tint `#E8EFFE`, dark `#1E3A8A`); error panel `#FFF8F4` with border `#F3C4AE` and title `#9A3412`. Use 4/8 px spacing, 14 px card corners, 1 px card borders without heavy shadows, and 10 px button corners. Buttons MUST be at least 44 px tall and show hover, active, disabled, and loading states. Citation markers MUST be 26 px mono pills with a blue tint and a solid blue/white active state. Every interactive element MUST retain the visible focus ring `2px solid #1D4ED8` with 3 px offset. Page titles MUST be 28 px/600, section titles 18–20 px/600, body and answer text 16 px with 1.7 line height, and metadata/mono text 13 px. Avoid gradients, emoji, and decorative animation; respect reduced-motion preferences.
- **FR-018**: The frontend README MUST explain setup, frontend development/check commands, how to run the local fake backend using the owner-provided demo command, and how to select its documented fake modes. It MUST identify that command as a local demo setup because the integration handoff does not define an officially supported launcher.
- **FR-019**: The application MUST abort a pending request after 30 seconds and show a retryable timeout error with the message “The request took too long. Please try again.” The question MUST remain editable.

### Key Entities *(include if feature involves data)*

- **Question request**: The user's trimmed question, the fixed research-question workflow, and a valid request reference.
- **Question response**: A result status, answer when available, claims, evidence, corpus provenance, and synthetic-data marking.
- **Claim**: A response claim with text and citation references resolved against evidence identifiers. The accepted service contract requires at least one citation reference for each returned claim.
- **Evidence passage**: A response-local source identifier, DOI, source location, passage text, and paper title. The accepted contract does not provide authors, publication year, or section information.
- **Corpus provenance**: Corpus version, source contract version, and delivery digest reported with a response.
- **Service error**: A sanitized error category, friendly-safe message, retryability indication, and request reference.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can submit any valid question and observe a loading state followed by exactly the corresponding answered, no-results, insufficient-evidence, or error outcome.
- **SC-002**: Every rendered citation marker resolves to the evidence item with the same chunk ID, and no uncited or unknown evidence receives a number.
- **SC-003**: All three non-connected workflows are reachable from navigation and visibly identified as previews with placeholder-only content.
- **SC-004**: All required interactions can be completed with a keyboard, and the interface remains usable at 390 px width without horizontal page overflow.
- **SC-005**: The demo visibly identifies all Feature 011 responses as synthetic test data and exposes the three contract-defined corpus provenance values.

## Assumptions

- The accepted Feature 011 integration handoff is authoritative for the question-service boundary. Its fake responses are synthetic and do not represent real literature or scientific conclusions.
- The owner-provided `scratch/serve_fake.py` command is a local demo procedure, not an officially supported backend launcher. The handoff may be updated after backend integration work.
- The three non-question workflows are previews only. Filters, saved research, real retrieval, live providers, and scientific validation are outside this feature.
- Manual verification by the feature owner is still required before backlog tasks can be marked complete.

## Out of Scope

- Metadata filters or any additional request-body fields.
- Saved searches or saved hypotheses.
- Real retrieval, Gemini or other live-provider calls, and claims of scientific correctness.
- Authors, publication years, or section metadata absent from the current evidence contract.
- A new backend launcher, backend contract changes, or a backend workflow change.
- Browser-driven end-to-end tests unless separately approved.
