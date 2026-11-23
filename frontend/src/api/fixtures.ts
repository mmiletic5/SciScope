/**
 * Typed access to the synthetic contract fixtures (copies of docs/mvp/fixtures).
 * All data is invented; none of it is a scientific finding.
 */
import conflictingEvidenceJson from './fixtures/v2/conflicting_evidence.answered.json'
import errorInvalidRequestJson from './fixtures/v2/error.invalid_request.json'
import errorProviderUnavailableJson from './fixtures/v2/error.provider_unavailable.json'
import evidenceComparisonJson from './fixtures/v2/evidence_comparison.answered.json'
import healthJson from './fixtures/v2/health.json'
import insufficientEvidenceJson from './fixtures/v2/insufficient_evidence.json'
import noResultsJson from './fixtures/v2/no_results.json'
import researchGapJson from './fixtures/v2/research_gap.answered.json'
import researchQuestionInsufficientJson from './fixtures/v2/research_question.insufficient_evidence.json'
import researchQuestionJson from './fixtures/v2/research_question.answered.json'
import type {
  AnsweredResponse,
  InsufficientEvidenceResponse,
  NoResultsResponse,
  QuestionErrorResponse,
} from './types'
import type { HealthResponse, QuestionSuccessV2, WorkflowV2 } from './types.v2'

export const answeredFixture = researchQuestionJson as unknown as Extract<AnsweredResponse, { workflow: 'research_question' }>
export const noResultsFixture = noResultsJson as unknown as NoResultsResponse
export const insufficientEvidenceFixture = researchQuestionInsufficientJson as unknown as InsufficientEvidenceResponse
export const questionErrorFixture = errorProviderUnavailableJson as unknown as QuestionErrorResponse
export const invalidRequestErrorFixture = errorInvalidRequestJson as unknown as QuestionErrorResponse
export const healthFixture = healthJson as unknown as HealthResponse

/** Answered fixture per workflow; used by VITE_API_MODE=fixtures and by tests. */
export const answeredFixtureByWorkflow: Record<WorkflowV2, QuestionSuccessV2> = {
  research_question: researchQuestionJson as unknown as QuestionSuccessV2,
  evidence_comparison: evidenceComparisonJson as unknown as QuestionSuccessV2,
  conflicting_evidence: conflictingEvidenceJson as unknown as QuestionSuccessV2,
  research_gap: researchGapJson as unknown as QuestionSuccessV2,
}

/** The shipped insufficient_evidence.json is an evidence_comparison example. */
export const insufficientEvidenceComparisonFixture = insufficientEvidenceJson as unknown as QuestionSuccessV2
