import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  answeredFixture,
  insufficientEvidenceFixture,
  noResultsFixture,
  questionErrorFixture,
} from './fixtures'
import { QuestionClientError, submitQuestion } from './client'

const requestId = 'ui-test-001'

function response(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status })
}

function errorEnvelope(code: string, retryable: boolean) {
  return {
    ...questionErrorFixture,
    error: { ...questionErrorFixture.error, code, retryable },
  }
}

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

describe('submitQuestion', () => {
  it.each([
    ['answered', answeredFixture],
    ['no_results', noResultsFixture],
    ['insufficient_evidence', insufficientEvidenceFixture],
  ])('returns a valid %s response', async (_status, body) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(body)))

    await expect(submitQuestion('  test question  ', requestId)).resolves.toEqual(body)

    expect(fetch).toHaveBeenCalledWith('/api/v1/questions', expect.objectContaining({
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        workflow: 'research_question',
        question: 'test question',
        request_id: requestId,
      }),
    }))
  })

  it.each([
    ['invalid_request', false],
    ['retrieval_unavailable', true],
    ['provider_unavailable', true],
    ['dependency_timeout', true],
    ['response_contract_failure', false],
    ['internal_error', false],
  ])('preserves a valid %s error envelope', async (code, retryable) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(errorEnvelope(code, retryable), 503)))

    await expect(submitQuestion('test question', requestId)).rejects.toMatchObject({
      code,
      retryable,
      requestId: questionErrorFixture.request_id,
    })
  })

  it('maps fetch rejection to a retryable API-unreachable error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('connection refused')))

    await expect(submitQuestion('test question', requestId)).rejects.toMatchObject({
      code: 'api_unreachable',
      retryable: true,
      requestId,
    })
  })

  it.each([
    ['HTML proxy body', new Response('<html>offline</html>', { status: 502 })],
    ['empty body', new Response('', { status: 503 })],
    ['malformed JSON', new Response('{', { status: 502 })],
    ['success-shaped JSON', response(answeredFixture, 502)],
  ])('maps HTTP 5xx with a %s to retryable API-unreachable', async (_name, body) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(body))

    await expect(submitQuestion('test question', requestId)).rejects.toMatchObject({
      code: 'api_unreachable',
      retryable: true,
      requestId,
    })
  })

  it.each([200, 400, 422])('maps malformed HTTP %i JSON to a generic nonretryable error', async (status) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{', { status })))

    await expect(submitQuestion('test question', requestId)).rejects.toMatchObject({
      code: 'invalid_response',
      retryable: false,
      requestId,
    })
  })

  it('aborts after 30 seconds and reports a retryable timeout with the request reference', async () => {
    vi.useFakeTimers()
    let requestSignal: AbortSignal | undefined
    vi.stubGlobal('fetch', vi.fn((_url: string, init: RequestInit) => {
      requestSignal = init.signal ?? undefined
      return new Promise<Response>((_resolve, reject) => {
        requestSignal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
      })
    }))

    const pending = submitQuestion('test question', requestId)
    const errorExpectation = expect(pending).rejects.toMatchObject({
      code: 'timeout',
      message: 'The request took too long. Please try again.',
      retryable: true,
      requestId,
    })

    await vi.advanceTimersByTimeAsync(30_000)
    await errorExpectation
    expect(requestSignal?.aborted).toBe(true)
  })

  it('exports the expected client error class for state handling', () => {
    expect(QuestionClientError).toBeTypeOf('function')
  })
})
