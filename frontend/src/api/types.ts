/** Thin aliases over the frozen v2 contract mirror (`types.v2.ts`). */
import type {
  ErrorResponseV2,
  QuestionSuccessV2,
  WorkflowV2,
} from './types.v2'

export type {
  Claim,
  ComponentMetadata,
  ComponentOrigin,
  CorpusProvenance,
  Evidence,
  HealthResponse,
  QuestionMetadataV2,
  WorkflowV2,
} from './types.v2'

export type QuestionSuccess = QuestionSuccessV2
export type QuestionErrorResponse = ErrorResponseV2
export type QuestionErrorCode = ErrorResponseV2['error']['code']
export type AnsweredResponse = Extract<QuestionSuccessV2, { status: 'answered' }>
export type NoResultsResponse = Extract<QuestionSuccessV2, { status: 'no_results' }>
export type InsufficientEvidenceResponse = Extract<QuestionSuccessV2, { status: 'insufficient_evidence' }>
export type ResearchQuestionAnswered = Extract<AnsweredResponse, { workflow: 'research_question' }>

/** Client timeout per workflow: 30 s for research_question, 60 s for the others. */
export const REQUEST_TIMEOUT_MS: Record<WorkflowV2, number> = {
  research_question: 30_000,
  evidence_comparison: 60_000,
  conflicting_evidence: 60_000,
  research_gap: 60_000,
}
