/** Strict runtime validation of API v2 payloads against docs/mvp/API_CONTRACT.md. */
import type {
  ErrorCodeV2,
  ErrorResponseV2,
  Evidence,
  HealthResponse,
  QuestionMetadataV2,
  QuestionSuccessV2,
  WorkflowV2,
} from './types.v2'
import { WORKFLOWS_V2 } from './types.v2'

export const REQUEST_ID_PATTERN = /^[A-Za-z0-9._:-]{1,128}$/

const ORIGINS = ['synthetic', 'fake', 'real']
const ERROR_CODES: string[] = [
  'invalid_request',
  'retrieval_unavailable',
  'provider_unavailable',
  'dependency_timeout',
  'response_contract_failure',
  'internal_error',
] satisfies ErrorCodeV2[]
const BASE_KEYS = ['api_version', 'request_id', 'workflow', 'status', 'answer', 'claims', 'evidence', 'corpus', 'metadata']
const PAYLOAD_KEY: Record<WorkflowV2, string | null> = {
  research_question: null,
  evidence_comparison: 'comparison',
  conflicting_evidence: 'conflicts',
  research_gap: 'gap_analysis',
}

type Rec = Record<string, unknown>
type EvidenceIndex = Map<string, Evidence>

function isRecord(value: unknown): value is Rec {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function hasExactKeys(value: Rec, keys: string[]): boolean {
  return Object.keys(value).length === keys.length && keys.every((key) => key in value)
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0
}

function allNonEmpty(value: Rec, keys: string[]): boolean {
  return keys.every((key) => isNonEmptyString(value[key]))
}

function isRequestId(value: unknown): value is string {
  return typeof value === 'string' && REQUEST_ID_PATTERN.test(value)
}

function isComponent(value: unknown): boolean {
  return isRecord(value)
    && hasExactKeys(value, ['configured_origin', 'executed', 'is_test_data'])
    && typeof value.configured_origin === 'string'
    && ORIGINS.includes(value.configured_origin)
    && typeof value.executed === 'boolean'
    && typeof value.is_test_data === 'boolean'
}

export function isMetadataV2(value: unknown): value is QuestionMetadataV2 {
  return isRecord(value)
    && hasExactKeys(value, ['retrieval', 'answer_provider'])
    && isComponent(value.retrieval)
    && isComponent(value.answer_provider)
}

function isEvidence(value: unknown): value is Evidence {
  return isRecord(value)
    && hasExactKeys(value, ['chunk_id', 'doi', 'source_locator', 'passage', 'paper_title'])
    && allNonEmpty(value, ['chunk_id', 'doi', 'source_locator', 'passage', 'paper_title'])
}

/** Non-empty, unique ids, each present in the same response's evidence[]. */
function validCitations(value: unknown, evidenceById: EvidenceIndex): value is string[] {
  return Array.isArray(value)
    && value.length > 0
    && value.every(isNonEmptyString)
    && new Set(value).size === value.length
    && value.every((id) => evidenceById.has(id))
}

function distinctDois(ids: string[], evidenceById: EvidenceIndex): number {
  return new Set(ids.map((id) => evidenceById.get(id)?.doi)).size
}

function validCitedItem(item: unknown, idKey: string, evidenceById: EvidenceIndex): item is Rec {
  return isRecord(item)
    && hasExactKeys(item, [idKey, 'text', 'citation_chunk_ids'])
    && allNonEmpty(item, [idKey, 'text'])
    && validCitations(item.citation_chunk_ids, evidenceById)
}

function validComparison(value: unknown, evidenceById: EvidenceIndex): boolean {
  if (!isRecord(value) || !hasExactKeys(value, ['subjects', 'similarities', 'differences'])) return false
  const { subjects, similarities, differences } = value
  if (!Array.isArray(subjects) || subjects.length < 2 || subjects.length > 6) return false
  const subjectsValid = subjects.every((subject) => isRecord(subject)
    && hasExactKeys(subject, ['subject_id', 'doi', 'paper_title', 'summary', 'citation_chunk_ids'])
    && allNonEmpty(subject, ['subject_id', 'doi', 'paper_title', 'summary'])
    && validCitations(subject.citation_chunk_ids, evidenceById)
    && subject.citation_chunk_ids.every((id) => evidenceById.get(id)?.doi === subject.doi))
  if (!subjectsValid) return false
  const listValid = (list: unknown) => Array.isArray(list)
    && list.every((item) => validCitedItem(item, 'item_id', evidenceById)
      && distinctDois(item.citation_chunk_ids as string[], evidenceById) >= 2)
  return listValid(similarities) && listValid(differences)
}

function validConflicts(value: unknown, evidenceById: EvidenceIndex): boolean {
  if (!isRecord(value) || !hasExactKeys(value, ['review_note', 'items'])) return false
  if (!isNonEmptyString(value.review_note)) return false
  const { items } = value
  return Array.isArray(items) && items.length >= 1 && items.length <= 5 && items.every((item) => isRecord(item)
    && hasExactKeys(item, ['item_id', 'topic', 'summary', 'positions'])
    && allNonEmpty(item, ['item_id', 'topic', 'summary'])
    && Array.isArray(item.positions)
    && item.positions.length >= 2
    && item.positions.every((position: unknown) => validCitedItem(position, 'position_id', evidenceById)))
}

function validGapAnalysis(value: unknown, evidenceById: EvidenceIndex): boolean {
  if (!isRecord(value) || !hasExactKeys(value, ['gaps', 'hypotheses'])) return false
  const { gaps, hypotheses } = value
  if (!Array.isArray(gaps) || gaps.length < 1) return false
  if (!gaps.every((gap) => validCitedItem(gap, 'gap_id', evidenceById))) return false
  if (!Array.isArray(hypotheses) || hypotheses.length > 4) return false
  const gapIds = new Set(gaps.map((gap) => (gap as Rec).gap_id))
  return hypotheses.every((hyp) => isRecord(hyp)
    && hasExactKeys(hyp, ['hypothesis_id', 'text', 'rationale', 'based_on_gap_ids', 'citation_chunk_ids', 'is_speculative'])
    && allNonEmpty(hyp, ['hypothesis_id', 'text', 'rationale'])
    && Array.isArray(hyp.based_on_gap_ids)
    && hyp.based_on_gap_ids.length >= 1
    && hyp.based_on_gap_ids.every((id) => gapIds.has(id))
    && validCitations(hyp.citation_chunk_ids, evidenceById)
    && hyp.is_speculative === true)
}

export function isSuccessV2(value: unknown, expectedWorkflow?: WorkflowV2): value is QuestionSuccessV2 {
  if (!isRecord(value)
    || value.api_version !== 'v2'
    || !isRequestId(value.request_id)
    || typeof value.workflow !== 'string'
    || !(WORKFLOWS_V2 as readonly string[]).includes(value.workflow)
    || (expectedWorkflow !== undefined && value.workflow !== expectedWorkflow)
    || !isMetadataV2(value.metadata)
    || !isRecord(value.corpus)
    || !hasExactKeys(value.corpus, ['corpus_version', 'source_contract_version', 'delivery_digest'])
    || !Object.values(value.corpus).every(isNonEmptyString)
    || !Array.isArray(value.claims)
    || !Array.isArray(value.evidence)
    || !value.evidence.every(isEvidence)) {
    return false
  }

  const workflow = value.workflow as WorkflowV2
  const payloadKey = PAYLOAD_KEY[workflow]
  const answered = value.status === 'answered'
  if (!hasExactKeys(value, answered && payloadKey ? [...BASE_KEYS, payloadKey] : BASE_KEYS)) return false

  const evidence = value.evidence as Evidence[]
  const evidenceById: EvidenceIndex = new Map(evidence.map((item) => [item.chunk_id, item]))
  if (evidenceById.size !== evidence.length) return false

  const claimsValid = value.claims.every((claim) => isRecord(claim)
    && hasExactKeys(claim, ['claim_id', 'text', 'citation_chunk_ids'])
    && allNonEmpty(claim, ['claim_id', 'text'])
    && validCitations(claim.citation_chunk_ids, evidenceById))
  if (!claimsValid) return false

  const { answer_provider: provider } = value.metadata
  if (answered) {
    if (!isNonEmptyString(value.answer) || value.claims.length === 0 || evidence.length === 0
      || !provider.executed) return false
    if (payloadKey === 'comparison') return validComparison(value.comparison, evidenceById)
    if (payloadKey === 'conflicts') return validConflicts(value.conflicts, evidenceById)
    if (payloadKey === 'gap_analysis') return validGapAnalysis(value.gap_analysis, evidenceById)
    return true
  }
  if (value.status === 'no_results') {
    return value.answer === null && value.claims.length === 0 && evidence.length === 0 && !provider.executed
  }
  if (value.status === 'insufficient_evidence') {
    return value.answer === null && value.claims.length === 0 && evidence.length > 0 && provider.executed
  }
  return false
}

export function isErrorV2(value: unknown): value is ErrorResponseV2 {
  if (!isRecord(value)
    || value.api_version !== 'v2'
    || !isRequestId(value.request_id)
    || !isRecord(value.error)
    || !hasExactKeys(value.error, ['code', 'message', 'retryable'])) {
    return false
  }
  const allowed = ['api_version', 'request_id', 'error', 'metadata']
  if (!Object.keys(value).every((key) => allowed.includes(key))) return false
  if ('metadata' in value && !isMetadataV2(value.metadata)) return false
  return ERROR_CODES.includes(value.error.code as string)
    && isNonEmptyString(value.error.message)
    && typeof value.error.retryable === 'boolean'
}

export function isHealthV2(value: unknown): value is HealthResponse {
  if (!isRecord(value)
    || !hasExactKeys(value, ['status', 'api_versions', 'workflows', 'components'])
    || value.status !== 'ok'
    || !Array.isArray(value.api_versions)
    || !value.api_versions.every(isNonEmptyString)
    || !Array.isArray(value.workflows)
    || !value.workflows.every((w) => (WORKFLOWS_V2 as readonly string[]).includes(w as string))
    || !isRecord(value.components)
    || !hasExactKeys(value.components, ['retrieval', 'answer_provider'])) {
    return false
  }
  const components = value.components
  return ['retrieval', 'answer_provider'].every((key) => {
    const component = components[key]
    return isRecord(component)
      && hasExactKeys(component, ['configured_origin'])
      && ORIGINS.includes(component.configured_origin as string)
  })
}
