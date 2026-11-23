import { act, fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  answeredFixtureByWorkflow,
  insufficientEvidenceComparisonFixture,
  noResultsFixture,
  questionErrorFixture,
} from '../../api/fixtures'
import { GapsPage, NO_GAPS_MESSAGE } from './GapsPage'

const gaps = answeredFixtureByWorkflow.research_gap as unknown as {
  metadata: unknown
  gap_analysis: { gaps: unknown[]; hypotheses: unknown[] }
}
const noResults = { ...noResultsFixture, workflow: 'research_gap' }
const insufficient = { ...insufficientEvidenceComparisonFixture, workflow: 'research_gap' }
const noHypotheses = { ...gaps, gap_analysis: { ...gaps.gap_analysis, hypotheses: [] } }

function stubFetch(body: unknown, status = 200) {
  const fetchMock = vi.fn(() => Promise.resolve(new Response(JSON.stringify(body), { status })))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

async function search() {
  const user = userEvent.setup()
  render(<GapsPage />)
  await user.click(screen.getByRole('button', { name: 'Search' }))
  return user
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe('GapsPage', () => {
  it('sends the research_gap workflow', async () => {
    const fetchMock = stubFetch(gaps)
    await search()
    await screen.findByRole('heading', { name: 'Gaps in the retrieved evidence' })
    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(JSON.parse(init.body as string)).toMatchObject({ workflow: 'research_gap' })
  })

  it('shows the two sections with cited gaps', async () => {
    stubFetch(gaps)
    await search()

    const section = await screen.findByRole('region', { name: 'Gaps in the retrieved evidence' })
    expect(within(section).getAllByRole('listitem')).toHaveLength(2)
    expect(within(section).getByText(/limited to one season and one site/)).toBeTruthy()
    expect(within(section).getAllByRole('button', { name: /^Source \d+$/ })).toHaveLength(2)
    expect(screen.getByRole('region', { name: 'Suggested hypotheses' })).toBeTruthy()
  })

  it('labels every hypothesis "Suggested, not a finding" and shows rationale and citations', async () => {
    stubFetch(gaps)
    await search()

    const section = await screen.findByRole('region', { name: 'Suggested hypotheses' })
    const card = within(section).getByRole('listitem')
    expect(within(card).getByText('Suggested, not a finding')).toBeTruthy()
    expect(within(card).getByText(/Treatment X effects may differ across seasons/)).toBeTruthy()
    expect(within(card).getByText(/Paper A covers a single season/)).toBeTruthy()
    expect(within(card).getAllByRole('button', { name: /^Source \d+$/ })).toHaveLength(1)
  })

  it('links each hypothesis to the gap it is based on', async () => {
    stubFetch(gaps)
    await search()

    const section = await screen.findByRole('region', { name: 'Suggested hypotheses' })
    const link = within(section).getByRole('link', { name: 'Gap 1' })
    expect(link.getAttribute('href')).toBe('#gap-item-gap-1')
    expect(document.getElementById('gap-item-gap-1')?.textContent).toContain('one season and one site')
    expect(within(section).queryByRole('link', { name: 'Gap 2' })).toBeNull()
  })

  it('highlights the source card when a citation marker is activated', async () => {
    stubFetch(gaps)
    const user = await search()
    const section = await screen.findByRole('region', { name: 'Gaps in the retrieved evidence' })

    await user.click(within(section).getAllByRole('button', { name: 'Source 1' })[0])

    const card = screen.getByRole('region', { name: 'Sources' }).querySelector('[data-highlighted="true"]')
    expect(card?.textContent).toContain('Source 1: Synthetic paper A')
  })

  it('accepts zero hypotheses when gaps exist', async () => {
    stubFetch(noHypotheses)
    await search()

    expect(await screen.findByRole('region', { name: 'Gaps in the retrieved evidence' })).toBeTruthy()
    expect(screen.getByText('No hypotheses were suggested for these gaps.')).toBeTruthy()
    expect(screen.queryByText('Suggested, not a finding')).toBeNull()
  })

  it('shows the no-gaps message and retrieved passages on insufficient_evidence', async () => {
    stubFetch(insufficient)
    await search()

    expect(await screen.findByText(NO_GAPS_MESSAGE)).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Retrieved passages' })).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Gaps in the retrieved evidence' })).toBeNull()
  })

  it('shows no_results without gap content', async () => {
    stubFetch(noResults)
    await search()

    expect(await screen.findByRole('heading', { name: 'No results' })).toBeTruthy()
    expect(screen.queryByText('Suggested, not a finding')).toBeNull()
  })

  it('shows a loading state while the request is pending', async () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))
    await search()

    expect(screen.getByText(/Looking for research gaps/)).toBeTruthy()
    expect(screen.getByRole('button', { name: /Searching/ }).hasAttribute('disabled')).toBe(true)
  })

  it('shows a retryable error with a reference and retries', async () => {
    const fetchMock = stubFetch(questionErrorFixture, 503)
    const user = await search()

    expect(await screen.findByRole('alert')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    await screen.findByRole('alert')
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('rejects a response for another workflow as invalid', async () => {
    stubFetch(answeredFixtureByWorkflow.conflicting_evidence)
    await search()

    expect((await screen.findByRole('alert')).textContent).toContain('could not understand')
  })

  it('times out after 60 s', async () => {
    vi.useFakeTimers()
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))
    render(<GapsPage />)
    fireEvent.click(screen.getByRole('button', { name: 'Search' }))

    await act(async () => { await vi.advanceTimersByTimeAsync(30_000) })
    expect(screen.queryByRole('alert')).toBeNull()
    await act(async () => { await vi.advanceTimersByTimeAsync(30_001) })
    expect(screen.getByRole('alert').textContent).toContain('took too long')
  })

  it('reports response metadata to the parent', async () => {
    stubFetch(gaps)
    const onMetadataChange = vi.fn()
    render(<GapsPage onMetadataChange={onMetadataChange} />)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Search' }))

    await screen.findByRole('region', { name: 'Gaps in the retrieved evidence' })
    expect(onMetadataChange).toHaveBeenCalledWith(gaps.metadata)
  })
})
