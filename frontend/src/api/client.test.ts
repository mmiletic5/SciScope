import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  answeredFixture,
  answeredFixtureByWorkflow,
  insufficientEvidenceFixture,
  noResultsFixture,
  questionErrorFixture,
} from './fixtures'
import { QuestionClientError, fetchHealth, submitQuestion } from './client'
import { WORKFLOWS_V2, type WorkflowV2 } from './types.v2'

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

function hangingFetch() {
  return vi.fn((_url: string, init: RequestInit) => new Promise<Response>((_resolve, reject) => {
    init.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
  }))
}

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
  vi.unstubAllEnvs()
})

describe('submitQuestion', () => {
  it.each([
    ['answered', answeredFixture],
    ['no_results', noResultsFixture],
    ['insufficient_evidence', insufficientEvidenceFixture],
  ])('returns a valid %s response and posts to /api/v2/questions', async (_status, body) => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(body)))

    await expect(submitQuestion('  test question  ', requestId)).resolves.toEqual(body)

    expect(fetch).toHaveBeenCalledWith('/api/v2/questions', expect.objectContaining({
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        workflow: 'research_question',
        question: 'test question',
        request_id: requestId,
      }),
    }))
  })

  it.each(WORKFLOWS_V2.map((workflow) => [workflow]))('accepts the %s fixture and sends the workflow field', async (workflow) => {
    const body = answeredFixtureByWorkflow[workflow]
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(body)))

    await expect(submitQuestion('question', requestId, workflow)).resolves.toEqual(body)

    const init = vi.mocked(fetch).mock.calls[0][1] as RequestInit
    expect(JSON.parse(String(init.body))).toMatchObject({ workflow })
  })

  it('rejects a response whose workflow differs from the request', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(answeredFixtureByWorkflow.research_gap)))

    await expect(submitQuestion('question', requestId, 'research_question')).rejects.toMatchObject({
      code: 'invalid_response',
    })
  })

  it('rejects a v1 response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ ...answeredFixture, api_version: 'v1' })))

    await expect(submitQuestion('question', requestId)).rejects.toMatchObject({ code: 'invalid_response' })
  })

  it('rejects an answered response with a broken citation id', async () => {
    const body = structuredClone(answeredFixture)
    body.claims[0].citation_chunk_ids = ['not-in-evidence']
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(body)))

    await expect(submitQuestion('question', requestId)).rejects.toMatchObject({
      code: 'invalid_response',
      retryable: false,
    })
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

  it('accepts an error envelope without metadata (422)', async () => {
    const withoutMetadata: Record<string, unknown> = { ...errorEnvelope('invalid_request', false) }
    delete withoutMetadata.metadata
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(withoutMetadata, 422)))

    await expect(submitQuestion('test question', requestId)).rejects.toMatchObject({
      code: 'invalid_request',
      retryable: false,
    })
  })

  it('treats an error envelope with malformed metadata as an invalid response', async () => {
    const body = { ...errorEnvelope('invalid_request', false), metadata: { is_mock: true, is_test_data: true } }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(body, 422)))

    await expect(submitQuestion('test question', requestId)).rejects.toMatchObject({ code: 'invalid_response' })
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

  it.each([
    ['research_question', 30_000],
    ['evidence_comparison', 60_000],
    ['conflicting_evidence', 60_000],
    ['research_gap', 60_000],
  ] as [WorkflowV2, number][])('aborts %s after %i ms with a retryable timeout', async (workflow, limit) => {
    vi.useFakeTimers()
    const fetchMock = hangingFetch()
    vi.stubGlobal('fetch', fetchMock)

    const pending = submitQuestion('test question', requestId, workflow)
    const errorExpectation = expect(pending).rejects.toMatchObject({
      code: 'timeout',
      message: 'The request took too long. Please try again.',
      retryable: true,
      requestId,
    })

    await vi.advanceTimersByTimeAsync(limit - 1)
    expect((fetchMock.mock.calls[0][1] as RequestInit).signal?.aborted).toBe(false)
    await vi.advanceTimersByTimeAsync(1)
    await errorExpectation
    expect((fetchMock.mock.calls[0][1] as RequestInit).signal?.aborted).toBe(true)
  })

  it('exports the expected client error class for state handling', () => {
    expect(QuestionClientError).toBeTypeOf('function')
  })
})

describe('fixture mode (VITE_API_MODE=fixtures)', () => {
  it.each(WORKFLOWS_V2.map((workflow) => [workflow]))('returns the %s fixture without calling fetch', async (workflow) => {
    vi.stubEnv('VITE_API_MODE', 'fixtures')
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    const result = await submitQuestion('question', requestId, workflow)

    expect(result).toEqual({ ...answeredFixtureByWorkflow[workflow], request_id: requestId })
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('returns the health fixture without calling fetch', async () => {
    vi.stubEnv('VITE_API_MODE', 'fixtures')
    const fetchMock = vi.fn()
    vi.stubGlobal('fetch', fetchMock)

    await expect(fetchHealth()).resolves.toMatchObject({ status: 'ok' })
    expect(fetchMock).not.toHaveBeenCalled()
  })
})

describe('fetchHealth', () => {
  const health = {
    status: 'ok',
    api_versions: ['v1', 'v2'],
    workflows: [...WORKFLOWS_V2],
    components: { retrieval: { configured_origin: 'real' }, answer_provider: { configured_origin: 'fake' } },
  }

  it('returns a valid health response from /api/health', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(health)))

    await expect(fetchHealth()).resolves.toEqual(health)
    expect(fetch).toHaveBeenCalledWith('/api/health', expect.any(Object))
  })

  it.each([
    ['network failure', () => vi.fn().mockRejectedValue(new TypeError('refused'))],
    ['HTTP 502', () => vi.fn().mockResolvedValue(new Response('bad gateway', { status: 502 }))],
    ['invalid shape', () => vi.fn().mockResolvedValue(response({ status: 'ok' }))],
  ])('rejects on %s', async (_name, makeFetch) => {
    vi.stubGlobal('fetch', makeFetch())

    await expect(fetchHealth()).rejects.toThrow()
  })

  it('aborts a hanging request after 5 seconds', async () => {
    vi.useFakeTimers()
    vi.stubGlobal('fetch', hangingFetch())

    const expectation = expect(fetchHealth()).rejects.toThrow()
    await vi.advanceTimersByTimeAsync(5_000)
    await expectation
  })
})
