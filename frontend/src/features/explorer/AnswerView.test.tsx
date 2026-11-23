import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { answeredFixture } from '../../api/fixtures'
import { AnswerView } from './AnswerView'

afterEach(() => {
  Reflect.deleteProperty(HTMLElement.prototype, 'scrollIntoView')
})

describe('AnswerView', () => {
  it('shows answer and claims separately, with numbered and uncited evidence', () => {
    render(<AnswerView response={{
      ...answeredFixture,
      claims: [
        ...answeredFixture.claims,
        { claim_id: 'synthetic-claim-2', text: 'Second synthetic claim.', citation_chunk_ids: ['unknown-id'] },
      ],
      evidence: [
        ...answeredFixture.evidence,
        { chunk_id: 'synthetic-uncited', doi: '10.0000/uncited', source_locator: 'synthetic:uncited', passage: 'Synthetic uncited passage.', paper_title: 'Synthetic uncited source' },
      ],
    }} />)

    expect(screen.getByRole('heading', { name: 'Answer' })).toBeTruthy()
    expect(screen.getByText(answeredFixture.answer)).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Claims' })).toBeTruthy()
    expect(screen.getByText('Second synthetic claim.')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Source 1' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Other retrieved passages' })).toBeTruthy()
    expect(screen.getByText('Synthetic uncited passage.')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Source 2' })).toBeNull()
  })

  it('scrolls to and highlights the source activated by a citation', () => {
    const scrollIntoView = vi.fn()
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', { value: scrollIntoView, configurable: true })
    render(<AnswerView response={answeredFixture} />)

    fireEvent.click(screen.getByRole('button', { name: 'Source 1' }))

    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: 'smooth', block: 'center' })
    expect(document.querySelector('[data-highlighted="true"]')).toBeTruthy()
  })

  it('uses a safe DOI link and discloses source location only in Details', () => {
    render(<AnswerView response={answeredFixture} />)

    const doiLink = screen.getByRole('link', { name: /10\.0000\/test-only/ })
    expect(doiLink.getAttribute('href')).toBe('https://doi.org/10.0000/test-only')
    expect(doiLink.getAttribute('target')).toBe('_blank')
    expect(doiLink.getAttribute('rel')).toBe('noopener noreferrer')
    const details = screen.getByText('Details').closest('details')
    expect(details?.open).toBe(false)
    fireEvent.click(screen.getByText('Details'))
    expect(details?.open).toBe(true)
    expect(screen.getByText('Synthetic locator for offline UI tests.')).toBeTruthy()
  })

  it('displays corpus provenance in its disclosure', () => {
    render(<AnswerView response={answeredFixture} />)

    fireEvent.click(screen.getByText('About this result'))
    expect(screen.getByText('synthetic-fixture-v1')).toBeTruthy()
    expect(screen.getByText('synthetic-contract-v1')).toBeTruthy()
    expect(screen.getByText('synthetic-digest-not-a-real-corpus')).toBeTruthy()
  })
})
