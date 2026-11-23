import { isValidRequestId } from '../lib/requestId'
import type {
  Evidence,
  MockMetadata,
  QuestionErrorCode,
  QuestionErrorResponse,
  QuestionSuccess,
} from './types'

export type QuestionClientErrorCode = QuestionErrorCode | 'api_unreachable' | 'invalid_response' | 'timeout'

const ERROR_MESSAGES: Record<QuestionErrorCode, string> = {
  invalid_request: 'Your question could not be accepted. Please check it and try again.',
  retrieval_unavailable: 'The SciScope API could not retrieve results. Please try again.',
  provider_unavailable: 'The SciScope API is temporarily unavailable. Please try again.',
  dependency_timeout: 'The request took too long. Please try again.',
  response_contract_failure: 'Something went wrong while processing the request.',
  internal_error: 'Something went wrong while processing the request.',
}

const API_UNREACHABLE_MESSAGE = 'Cannot reach the SciScope API. Is the backend running?'
const INVALID_RESPONSE_MESSAGE = 'We could not understand the SciScope API response.'
const TIMEOUT_MESSAGE = 'The request took too long. Please try again.'
const REQUEST_TIMEOUT_MS = 30_000
const REQUEST_ID_PATTERN = /^[A-Za-z0-9._:-]{1,128}$/

export class QuestionClientError extends Error {
  readonly code: QuestionClientErrorCode
  readonly retryable: boolean
  readonly requestId: string
  readonly response?: QuestionErrorResponse

  constructor(
    code: QuestionClientErrorCode,
    message: string,
    retryable: boolean,
    requestId: string,
    response?: QuestionErrorResponse,
  ) {
    super(message)
    this.name = 'QuestionClientError'
    this.code = code
    this.retryable = retryable
    this.requestId = requestId
    this.response = response
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function hasExactKeys(value: Record<string, unknown>, keys: string[]): boolean {
  return Object.keys(value).length === keys.length && keys.every((key) => key in value)
}

function isMetadata(value: unknown): value is MockMetadata {
  return isRecord(value)
    && hasExactKeys(value, ['is_mock', 'is_test_data'])
    && typeof value.is_mock === 'boolean'
    && typeof value.is_test_data === 'boolean'
}

function isNonEmptyString(value: unknown): value is string {
  return typeof value === 'string' && value.trim().length > 0
}

function isEvidence(value: unknown): value is Evidence {
  return isRecord(value)
    && hasExactKeys(value, ['chunk_id', 'doi', 'source_locator', 'passage', 'paper_title'])
    && isNonEmptyString(value.chunk_id)
    && isNonEmptyString(value.doi)
    && isNonEmptyString(value.source_locator)
    && isNonEmptyString(value.passage)
    && isNonEmptyString(value.paper_title)
}

function isSuccessEnvelope(value: unknown): value is QuestionSuccess {
  if (!isRecord(value)
    || !['api_version', 'request_id', 'workflow', 'status', 'answer', 'claims', 'evidence', 'corpus', 'metadata']
      .every((key) => key in value)
    || value.api_version !== 'v1'
    || typeof value.request_id !== 'string'
    || !REQUEST_ID_PATTERN.test(value.request_id)
    || value.workflow !== 'research_question'
    || !isMetadata(value.metadata)
    || !isRecord(value.corpus)
    || !hasExactKeys(value.corpus, ['corpus_version', 'source_contract_version', 'delivery_digest'])
    || !Object.values(value.corpus).every(isNonEmptyString)
    || !Array.isArray(value.claims)
    || !Array.isArray(value.evidence)
    || !value.evidence.every(isEvidence)) {
    return false
  }

  const claimsValid = value.claims.every((claim) => isRecord(claim)
    && hasExactKeys(claim, ['claim_id', 'text', 'citation_chunk_ids'])
    && isNonEmptyString(claim.claim_id)
    && isNonEmptyString(claim.text)
    && Array.isArray(claim.citation_chunk_ids)
    && claim.citation_chunk_ids.length > 0
    && claim.citation_chunk_ids.every(isNonEmptyString))

  if (!claimsValid) return false

  if (value.status === 'answered') {
    return isNonEmptyString(value.answer) && value.claims.length > 0 && value.evidence.length > 0
  }
  if (value.status === 'no_results') {
    return value.answer === null && value.claims.length === 0 && value.evidence.length === 0
  }
  if (value.status === 'insufficient_evidence') {
    return value.answer === null && value.claims.length === 0
  }
  return false
}

function isQuestionErrorCode(value: unknown): value is QuestionErrorCode {
  return value === 'invalid_request'
    || value === 'retrieval_unavailable'
    || value === 'provider_unavailable'
    || value === 'dependency_timeout'
    || value === 'response_contract_failure'
    || value === 'internal_error'
}

function isErrorEnvelope(value: unknown): value is QuestionErrorResponse {
  if (!isRecord(value)
    || !hasExactKeys(value, ['api_version', 'request_id', 'error', 'metadata'])
    || value.api_version !== 'v1'
    || typeof value.request_id !== 'string'
    || !REQUEST_ID_PATTERN.test(value.request_id)
    || !isMetadata(value.metadata)
    || !isRecord(value.error)
    || !hasExactKeys(value.error, ['code', 'message', 'retryable'])) {
    return false
  }

  return isQuestionErrorCode(value.error.code)
    && isNonEmptyString(value.error.message)
    && typeof value.error.retryable === 'boolean'
}

function makeError(
  code: QuestionClientErrorCode,
  message: string,
  retryable: boolean,
  requestId: string,
  response?: QuestionErrorResponse,
): QuestionClientError {
  return new QuestionClientError(code, message, retryable, requestId, response)
}

function parseJson(text: string): unknown {
  try {
    return JSON.parse(text) as unknown
  } catch {
    return undefined
  }
}

export async function submitQuestion(question: string, requestId: string): Promise<QuestionSuccess> {
  const trimmedQuestion = question.trim()
  if (trimmedQuestion.length < 1 || trimmedQuestion.length > 2000) {
    throw makeError('invalid_request', ERROR_MESSAGES.invalid_request, false, requestId)
  }
  if (!isValidRequestId(requestId)) {
    throw makeError('invalid_request', ERROR_MESSAGES.invalid_request, false, requestId)
  }

  const controller = new AbortController()
  let didTimeout = false
  let timeoutId: ReturnType<typeof setTimeout> | undefined
  const timeout = new Promise<never>((_resolve, reject) => {
    timeoutId = setTimeout(() => {
      didTimeout = true
      controller.abort()
      reject(makeError('timeout', TIMEOUT_MESSAGE, true, requestId))
    }, REQUEST_TIMEOUT_MS)
  })

  try {
    const response = await Promise.race([
      fetch('/api/v1/questions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workflow: 'research_question',
          question: trimmedQuestion,
          request_id: requestId,
        }),
        signal: controller.signal,
      }),
      timeout,
    ])
    const parsed = parseJson(await response.text())

    if (response.status >= 500 && response.status < 600) {
      if (isErrorEnvelope(parsed)) {
        const code = parsed.error.code
        throw makeError(code, ERROR_MESSAGES[code], parsed.error.retryable, parsed.request_id, parsed)
      }
      throw makeError('api_unreachable', API_UNREACHABLE_MESSAGE, true, requestId)
    }

    if (isErrorEnvelope(parsed)) {
      const code = parsed.error.code
      throw makeError(code, ERROR_MESSAGES[code], parsed.error.retryable, parsed.request_id, parsed)
    }

    if (response.status !== 200 || !isSuccessEnvelope(parsed)) {
      throw makeError('invalid_response', INVALID_RESPONSE_MESSAGE, false, requestId)
    }

    return parsed
  } catch (error) {
    if (error instanceof QuestionClientError) throw error
    if (didTimeout) throw makeError('timeout', TIMEOUT_MESSAGE, true, requestId)
    throw makeError('api_unreachable', API_UNREACHABLE_MESSAGE, true, requestId)
  } finally {
    if (timeoutId !== undefined) clearTimeout(timeoutId)
  }
}
