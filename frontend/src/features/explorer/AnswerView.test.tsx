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

    const doiLink = screen.getAllByRole('link', { name: /10\.0000\/synthetic\.0001/ })[0]
    expect(doiLink.getAttribute('href')).toBe('https://doi.org/10.0000/synthetic.0001')
    expect(doiLink.getAttribute('target')).toBe('_blank')
    expect(doiLink.getAttribute('rel')).toBe('noopener noreferrer')
    const summary = screen.getAllByText('Details')[0]
    const details = summary.closest('details')
    expect(details?.open).toBe(false)
    fireEvent.click(summary)
    expect(details?.open).toBe(true)
    expect(screen.getByText('jats:v1:/article/body/sec[2]/p[1]')).toBeTruthy()
  })

  it('displays corpus provenance in its disclosure', () => {
    render(<AnswerView response={answeredFixture} />)

    fireEvent.click(screen.getByText('About this result'))
    expect(screen.getByText('synthetic-fixture-v2')).toBeTruthy()
    expect(screen.getByText('synthetic-contract-v2')).toBeTruthy()
    expect(screen.getByText('synthetic-digest-not-a-real-corpus')).toBeTruthy()
  })
})

describe('AnswerView leaked ids', () => {
  it('does not render chunk ids in the answer or in claim texts', () => {
    const id = 'cd'.repeat(32)
    const leaked = {
      ...answeredFixture,
      answer: `${answeredFixture.answer} [${id}]`,
      claims: answeredFixture.claims.map((claim) => ({ ...claim, text: `${claim.text} [${id}]` })),
    }
    render(<AnswerView response={leaked} />)
    expect(document.body.textContent).not.toContain(id)
  })
})
