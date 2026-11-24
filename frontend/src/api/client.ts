import { isValidRequestId } from '../lib/requestId'
import { answeredFixtureByWorkflow, healthFixture } from './fixtures'
import {
  REQUEST_TIMEOUT_MS,
  type QuestionErrorCode,
  type QuestionErrorResponse,
  type QuestionSuccess,
} from './types'
import type { HealthResponse, WorkflowV2 } from './types.v2'
import { isErrorV2, isHealthV2, isSuccessV2 } from './validate'

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
const HEALTH_TIMEOUT_MS = 5_000
const FIXTURE_DELAY_MS = 400

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

function isFixtureMode(): boolean {
  return import.meta.env.VITE_API_MODE === 'fixtures'
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/** Offline development: return the answered contract fixture for the workflow. */
async function fixtureQuestion(workflow: WorkflowV2, requestId: string): Promise<QuestionSuccess> {
  await delay(FIXTURE_DELAY_MS)
  const fixture = { ...answeredFixtureByWorkflow[workflow], request_id: requestId }
  if (!isSuccessV2(fixture, workflow)) {
    throw makeError('invalid_response', INVALID_RESPONSE_MESSAGE, false, requestId)
  }
  return fixture
}

export async function submitQuestion(
  question: string,
  requestId: string,
  workflow: WorkflowV2 = 'research_question',
  signal?: AbortSignal,
): Promise<QuestionSuccess> {
  const trimmedQuestion = question.trim()
  if (trimmedQuestion.length < 1 || trimmedQuestion.length > 2000) {
    throw makeError('invalid_request', ERROR_MESSAGES.invalid_request, false, requestId)
  }
  if (!isValidRequestId(requestId)) {
    throw makeError('invalid_request', ERROR_MESSAGES.invalid_request, false, requestId)
  }
  if (isFixtureMode()) return fixtureQuestion(workflow, requestId)

  const controller = new AbortController()
  if (signal?.aborted) controller.abort()
  else signal?.addEventListener('abort', () => controller.abort(), { once: true })
  let didTimeout = false
  let timeoutId: ReturnType<typeof setTimeout> | undefined
  const timeout = new Promise<never>((_resolve, reject) => {
    timeoutId = setTimeout(() => {
      didTimeout = true
      controller.abort()
      reject(makeError('timeout', TIMEOUT_MESSAGE, true, requestId))
    }, REQUEST_TIMEOUT_MS[workflow])
  })

  try {
    const response = await Promise.race([
      fetch('/api/v2/questions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workflow,
          question: trimmedQuestion,
          request_id: requestId,
        }),
        signal: controller.signal,
      }),
      timeout,
    ])
    const parsed = parseJson(await response.text())

    if (response.status >= 500 && response.status < 600) {
      if (isErrorV2(parsed)) {
        const code = parsed.error.code
        throw makeError(code, ERROR_MESSAGES[code], parsed.error.retryable, parsed.request_id, parsed)
      }
      throw makeError('api_unreachable', API_UNREACHABLE_MESSAGE, true, requestId)
    }

    if (isErrorV2(parsed)) {
      const code = parsed.error.code
      throw makeError(code, ERROR_MESSAGES[code], parsed.error.retryable, parsed.request_id, parsed)
    }

    if (response.status !== 200 || !isSuccessV2(parsed, workflow)) {
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

/** GET /api/health. Rejects on any failure (network, non-200, invalid shape). */
export async function fetchHealth(): Promise<HealthResponse> {
  if (isFixtureMode()) return healthFixture
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), HEALTH_TIMEOUT_MS)
  try {
    const response = await fetch('/api/health', { signal: controller.signal })
    const parsed = parseJson(await response.text())
    if (response.status !== 200 || !isHealthV2(parsed)) throw new Error('Invalid health response')
    return parsed
  } finally {
    clearTimeout(timeoutId)
  }
}
