import { act, fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  answeredFixtureByWorkflow,
  insufficientEvidenceComparisonFixture,
  noResultsFixture,
  questionErrorFixture,
} from '../../api/fixtures'
import { ConflictsPage, NO_DIFFERENCES_MESSAGE } from './ConflictsPage'

const conflicts = answeredFixtureByWorkflow.conflicting_evidence
const noResults = { ...noResultsFixture, workflow: 'conflicting_evidence' }
const insufficient = { ...insufficientEvidenceComparisonFixture, workflow: 'conflicting_evidence' }

function stubFetch(body: unknown, status = 200) {
  const fetchMock = vi.fn(() => Promise.resolve(new Response(JSON.stringify(body), { status })))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

async function search() {
  const user = userEvent.setup()
  render(<ConflictsPage />)
  await user.click(screen.getByRole('button', { name: 'Search' }))
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe('ConflictsPage', () => {
  it('sends the conflicting_evidence workflow', async () => {
    const fetchMock = stubFetch(conflicts)
    await search()
    await screen.findByRole('heading', { name: 'Potential differences for review' })
    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(JSON.parse(init.body as string)).toMatchObject({ workflow: 'conflicting_evidence' })
  })

  it('shows the review note first as a labelled note', async () => {
    stubFetch(conflicts)
    await search()

    const note = await screen.findByRole('note', { name: 'Review note' })
    expect(note.textContent).toContain('They are not verified contradictions.')
    const results = screen.getByRole('region', { name: 'Review results' })
    expect(results.querySelector('.conflicts-view')?.firstElementChild).toBe(note)
  })

  it('shows one card per item with topic, summary and positions side by side', async () => {
    stubFetch(conflicts)
    await search()

    const section = await screen.findByRole('region', { name: 'Potential differences for review' })
    expect(within(section).getAllByRole('article')).toHaveLength(2)
    const card = within(section).getByRole('article', { name: 'Effect of treatment X on the measured outcome' })
    expect(within(card).getByText('Passages A1 and B1 point in opposite directions.')).toBeTruthy()
    expect(within(card).getAllByRole('heading', { level: 4 }).map((h) => h.textContent)).toEqual(['Position 1', 'Position 2'])
    expect(within(card).getByText(/Paper A reports a lower outcome rate/)).toBeTruthy()
    expect(within(card).getByText(/Paper B reports a higher outcome rate/)).toBeTruthy()
    expect(within(card).getAllByRole('button', { name: /^Source \d+$/ })).toHaveLength(2)
  })

  it('highlights the source card when a citation marker is activated', async () => {
    stubFetch(conflicts)
    await search()
    const section = await screen.findByRole('region', { name: 'Potential differences for review' })

    await userEvent.setup().click(within(section).getAllByRole('button', { name: 'Source 1' })[0])

    const card = screen.getByRole('region', { name: 'Sources' }).querySelector('[data-highlighted="true"]')
    expect(card?.textContent).toContain('Source 1: Synthetic paper A')
  })

  it('never presents a difference as a verdict', async () => {
    stubFetch(conflicts)
    await search()
    await screen.findByRole('note', { name: 'Review note' })

    const headings = screen.getAllByRole('heading').map((h) => h.textContent ?? '')
    expect(headings.some((text) => /contradiction|proven conflict/i.test(text))).toBe(false)
    expect(screen.getByRole('heading', { level: 1 }).textContent).toBe('Potential differences')
  })

  it('shows the exact no-differences message and retrieved passages on insufficient_evidence', async () => {
    stubFetch(insufficient)
    await search()

    expect(await screen.findByText(NO_DIFFERENCES_MESSAGE)).toBeTruthy()
    expect(NO_DIFFERENCES_MESSAGE).toBe(
      'No potential differences were identified in the retrieved passages. This does not show that none exist.',
    )
    expect(screen.getByRole('heading', { name: 'Retrieved passages' })).toBeTruthy()
    expect(screen.queryByRole('note')).toBeNull()
    expect(screen.queryByRole('heading', { name: 'Potential differences for review' })).toBeNull()
  })

  it('shows no_results without difference content', async () => {
    stubFetch(noResults)
    await search()

    expect(await screen.findByRole('heading', { name: 'No results' })).toBeTruthy()
    expect(screen.queryByRole('note')).toBeNull()
  })

  it('shows a loading state while the request is pending', async () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))
    await search()

    expect(screen.getByText(/Looking for potential differences/)).toBeTruthy()
    expect(screen.getByRole('button', { name: /Searching/ }).hasAttribute('disabled')).toBe(true)
  })

  it('shows a retryable error with a reference and retries', async () => {
    const fetchMock = stubFetch(questionErrorFixture, 503)
    await search()

    expect(await screen.findByRole('alert')).toBeTruthy()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Try again' }))
    await screen.findByRole('alert')
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('rejects a response for another workflow as invalid', async () => {
    stubFetch(answeredFixtureByWorkflow.research_gap)
    await search()

    expect((await screen.findByRole('alert')).textContent).toContain('could not understand')
  })

  it('times out after 60 s', async () => {
    vi.useFakeTimers()
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))
    render(<ConflictsPage />)
    fireEvent.click(screen.getByRole('button', { name: 'Search' }))

    await act(async () => { await vi.advanceTimersByTimeAsync(30_000) })
    expect(screen.queryByRole('alert')).toBeNull()
    await act(async () => { await vi.advanceTimersByTimeAsync(30_001) })
    expect(screen.getByRole('alert').textContent).toContain('took too long')
  })

  it('reports response metadata to the parent', async () => {
    stubFetch(conflicts)
    const onMetadataChange = vi.fn()
    render(<ConflictsPage onMetadataChange={onMetadataChange} />)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Search' }))

    await screen.findByRole('note', { name: 'Review note' })
    expect(onMetadataChange).toHaveBeenCalledWith(conflicts.metadata)
  })
})
