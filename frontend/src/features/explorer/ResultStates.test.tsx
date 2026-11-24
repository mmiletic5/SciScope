import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { insufficientEvidenceFixture, noResultsFixture } from '../../api/fixtures'
import { QuestionClientError } from '../../api/client'
import { ResultStates } from './ResultStates'

describe('ResultStates', () => {
  it('explains a no-results response and suggests rephrasing', () => {
    render(<ResultStates response={noResultsFixture} onRetry={vi.fn()} />)

    expect(screen.getByText('No relevant passages were found in the corpus.')).toBeTruthy()
    expect(screen.getByText(/Try rephrasing/)).toBeTruthy()
  })

  it('explains insufficient evidence and displays closest passages without numbers', () => {
    const response = {
      ...insufficientEvidenceFixture,
      evidence: [{
        chunk_id: 'synthetic-nearby',
        doi: '10.0000/nearby',
        source_locator: 'synthetic-only',
        passage: 'Synthetic closest passage for this test.',
        paper_title: 'Synthetic closest source',
      }],
    }
    render(<ResultStates response={response} onRetry={vi.fn()} />)

    expect(screen.getByText('Not enough evidence to answer')).toBeTruthy()
    expect(screen.getByText(/declined to answer rather than guess/i)).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Closest passages found' })).toBeTruthy()
    expect(screen.getByText('Synthetic closest passage for this test.')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Source 1' })).toBeNull()
  })

  it.each([
    ['invalid_request', 'Your question could not be accepted. Please check it and try again.', false],
    ['retrieval_unavailable', 'The SciScope API could not retrieve results. Please try again.', true],
    ['provider_unavailable', 'The SciScope API is temporarily unavailable. Please try again.', true],
    ['dependency_timeout', 'The request took too long. Please try again.', true],
    ['response_contract_failure', 'Something went wrong while processing the request.', false],
    ['internal_error', 'Something went wrong while processing the request.', false],
  ])('shows a safe %s message, reference, and correct retry availability', (code, message, retryable) => {
    const onRetry = vi.fn()
    const error = new QuestionClientError(code as never, message, retryable, 'ui-reference-001')
    render(<ResultStates error={error} onRetry={onRetry} />)

    expect(screen.getByText(message)).toBeTruthy()
    expect(screen.getByText('Reference: ui-reference-001')).toBeTruthy()
    expect(Boolean(screen.queryByRole('button', { name: 'Try again' }))).toBe(retryable)
    if (retryable) {
      fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
      expect(onRetry).toHaveBeenCalledOnce()
    }
  })

  it('uses the exact retryable reachability message', () => {
    const error = new QuestionClientError(
      'api_unreachable',
      'Cannot reach the SciScope API. Is the backend running?',
      true,
      'ui-unreachable-001',
    )
    render(<ResultStates error={error} onRetry={vi.fn()} />)

    expect(screen.getByText('Cannot reach the SciScope API. Is the backend running?')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Try again' })).toBeTruthy()
  })

  it('shows the exact retryable timeout copy and retry action', () => {
    const error = new QuestionClientError(
      'timeout',
      'The request took too long. Please try again.',
      true,
      'ui-timeout-001',
    )
    render(<ResultStates error={error} onRetry={vi.fn()} />)

    expect(screen.getByText('The request took too long. Please try again.')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Try again' })).toBeTruthy()
  })

  it('keeps malformed-response errors generic and nonretryable', () => {
    const error = new QuestionClientError(
      'invalid_response',
      'We could not understand the SciScope API response.',
      false,
      'ui-invalid-001',
    )
    render(<ResultStates error={error} onRetry={vi.fn()} />)

    expect(screen.getByText('We could not understand the SciScope API response.')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Try again' })).toBeNull()
  })
})
