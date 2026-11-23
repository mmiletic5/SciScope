/**
 * SciScope MVP API contract v2 - TypeScript types.
 * Source of truth: docs/mvp/API_CONTRACT.md (this file mirrors it).
 * Copy to frontend/src/api/ (e.g. types.v2.ts); do not edit independently.
 */

export const WORKFLOWS_V2 = [
  'research_question',
  'evidence_comparison',
  'conflicting_evidence',
  'research_gap',
] as const
export type WorkflowV2 = (typeof WORKFLOWS_V2)[number]

/** POST /api/v2/questions body. request_id optional; pattern /^[A-Za-z0-9._:-]{1,128}$/. */
export type QuestionRequestV2 = {
  workflow: WorkflowV2
  /** Trimmed, 1-2000 characters. */
  question: string
  request_id?: string
}

// ---- shared building blocks (unchanged from v1 except metadata) ----

export type ComponentOrigin = 'synthetic' | 'fake' | 'real'

export type ComponentMetadata = {
  configured_origin: ComponentOrigin
  /** Whether the component was actually invoked for this request. */
  executed: boolean
  is_test_data: boolean
}

export type QuestionMetadataV2 = {
  retrieval: ComponentMetadata
  answer_provider: ComponentMetadata
}

export type Claim = {
  claim_id: string
  text: string
  /** >= 1, unique, every id exists in the same response's evidence[]. */
  citation_chunk_ids: string[]
}

export type Evidence = {
  /** 64-char lowercase SHA-256 in real mode; opaque string in fixtures. */
  chunk_id: string
  doi: string
  source_locator: string
  passage: string
  paper_title: string
}

export type CorpusProvenance = {
  corpus_version: string
  source_contract_version: string
  delivery_digest: string
}

// ---- workflow payloads ----

/** Every statement that carries citations (>= 1, all resolvable in evidence[]). */
export type CitedItem = {
  item_id: string
  text: string
  citation_chunk_ids: string[]
}

export type ComparisonSubject = {
  subject_id: string
  doi: string
  paper_title: string
  summary: string
  /** All cited chunks belong to this subject's doi. */
  citation_chunk_ids: string[]
}

/** evidence_comparison. subjects.length >= 2. similarities/differences cite chunks from >= 2 distinct DOIs; either list may be empty. */
export type ComparisonPayload = {
  subjects: ComparisonSubject[]
  similarities: CitedItem[]
  differences: CitedItem[]
}

export type ConflictPosition = {
  position_id: string
  text: string
  citation_chunk_ids: string[]
}

export type ConflictItem = {
  item_id: string
  topic: string
  summary: string
  /** >= 2 positions. Positions may come from the same paper (authors vs earlier literature). */
  positions: ConflictPosition[]
}

/** conflicting_evidence. items.length >= 1 when status is 'answered'. UI MUST show review_note. */
export type ConflictsPayload = {
  review_note: string
  items: ConflictItem[]
}

export type GapItem = {
  gap_id: string
  text: string
  citation_chunk_ids: string[]
}

export type Hypothesis = {
  hypothesis_id: string
  text: string
  rationale: string
  /** >= 1 ids from gaps[].gap_id of the same response. */
  based_on_gap_ids: string[]
  citation_chunk_ids: string[]
  /** Always true: hypotheses are model suggestions, not findings. UI MUST label them. */
  is_speculative: true
}

/** research_gap. gaps.length >= 1 when status is 'answered'; hypotheses may be empty. */
export type GapAnalysisPayload = {
  gaps: GapItem[]
  hypotheses: Hypothesis[]
}

// ---- responses ----

type SuccessBase = {
  api_version: 'v2'
  request_id: string
  corpus: CorpusProvenance
  metadata: QuestionMetadataV2
}

type NoResults<W extends WorkflowV2> = SuccessBase & {
  workflow: W
  status: 'no_results'
  answer: null
  claims: []
  evidence: []
}

type InsufficientEvidence<W extends WorkflowV2> = SuccessBase & {
  workflow: W
  status: 'insufficient_evidence'
  answer: null
  claims: []
  evidence: Evidence[]
}

type Answered<W extends WorkflowV2> = SuccessBase & {
  workflow: W
  status: 'answered'
  answer: string
  /**
   * research_question: provider claims.
   * other workflows: server-derived flat list of every cited statement in the payload
   * (claim_id === item/subject/position/gap/hypothesis id, same order). Render the payload, not this list.
   */
  claims: Claim[]
  evidence: Evidence[]
}

export type ResearchQuestionResponse =
  | (Answered<'research_question'>)
  | NoResults<'research_question'>
  | InsufficientEvidence<'research_question'>

export type EvidenceComparisonResponse =
  | (Answered<'evidence_comparison'> & { comparison: ComparisonPayload })
  | NoResults<'evidence_comparison'>
  | InsufficientEvidence<'evidence_comparison'>

export type ConflictingEvidenceResponse =
  | (Answered<'conflicting_evidence'> & { conflicts: ConflictsPayload })
  | NoResults<'conflicting_evidence'>
  | InsufficientEvidence<'conflicting_evidence'>

export type ResearchGapResponse =
  | (Answered<'research_gap'> & { gap_analysis: GapAnalysisPayload })
  | NoResults<'research_gap'>
  | InsufficientEvidence<'research_gap'>

export type QuestionSuccessV2 =
  | ResearchQuestionResponse
  | EvidenceComparisonResponse
  | ConflictingEvidenceResponse
  | ResearchGapResponse

// ---- errors ----

export type ErrorCodeV2 =
  | 'invalid_request'
  | 'retrieval_unavailable'
  | 'provider_unavailable'
  | 'dependency_timeout'
  | 'response_contract_failure'
  | 'internal_error'

export type ErrorResponseV2 = {
  api_version: 'v2'
  request_id: string
  error: { code: ErrorCodeV2; message: string; retryable: boolean }
  /** Absent on 422 and on failures before any component ran. */
  metadata?: QuestionMetadataV2
}

// ---- health ----

/** GET /api/health */
export type HealthResponse = {
  status: 'ok'
  api_versions: string[]
  workflows: WorkflowV2[]
  components: {
    retrieval: { configured_origin: ComponentOrigin }
    answer_provider: { configured_origin: ComponentOrigin }
  }
}

// ---- helpers (semantics fixed by the contract) ----

/** 'live' only if both components are real, executed and not test data; otherwise 'demo'. */
export function isLiveMode(m: QuestionMetadataV2): boolean {
  return [m.retrieval, m.answer_provider].every(
    (c) => c.configured_origin === 'real' && c.executed && !c.is_test_data,
  )
}
