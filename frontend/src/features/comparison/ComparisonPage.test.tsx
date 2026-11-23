import { act, fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  answeredFixtureByWorkflow,
  insufficientEvidenceComparisonFixture,
  noResultsFixture,
  questionErrorFixture,
} from '../../api/fixtures'
import { ComparisonPage } from './ComparisonPage'

const comparison = answeredFixtureByWorkflow.evidence_comparison
const noResults = { ...noResultsFixture, workflow: 'evidence_comparison' }

function stubFetch(body: unknown, status = 200) {
  const fetchMock = vi.fn(() => Promise.resolve(new Response(JSON.stringify(body), { status })))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

async function search() {
  const user = userEvent.setup()
  render(<ComparisonPage />)
  await user.click(screen.getByRole('button', { name: 'Search' }))
}

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe('ComparisonPage', () => {
  it('prefills a placeholder question and sends the evidence_comparison workflow', async () => {
    const fetchMock = stubFetch(comparison)
    render(<ComparisonPage />)
    const input = screen.getByRole('textbox', { name: 'Comparison question' }) as HTMLTextAreaElement
    expect(input.value.length).toBeGreaterThan(10)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Search' }))

    await screen.findByRole('heading', { name: 'Papers compared' })
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('/api/v2/questions')
    expect(JSON.parse(init.body as string)).toMatchObject({ workflow: 'evidence_comparison', question: input.value })
  })

  it('shows the answer, one card per paper, similarities, differences and sources', async () => {
    stubFetch(comparison)
    await search()

    expect(await screen.findByText(/papers A and B measure the same outcome/)).toBeTruthy()
    const papers = screen.getByRole('region', { name: 'Papers compared' })
    expect(within(papers).getAllByRole('article')).toHaveLength(2)
    expect(within(papers).getByRole('heading', { name: 'Synthetic paper A (not a publication)' })).toBeTruthy()
    expect(within(papers).getByText(/Paper B reports a higher outcome rate under treatment X\./)).toBeTruthy()

    const similarities = screen.getByRole('region', { name: 'Similarities' })
    expect(within(similarities).getByText(/Both papers measured the same synthetic outcome/)).toBeTruthy()
    expect(within(similarities).getAllByRole('button', { name: /^Source \d+$/ })).toHaveLength(2)
    const differences = screen.getByRole('region', { name: 'Differences' })
    expect(within(differences).getAllByRole('button', { name: /^Source \d+$/ })).toHaveLength(2)

    const sources = screen.getByRole('region', { name: 'Sources' })
    expect(within(sources).getAllByRole('article')).toHaveLength(2)
    expect(screen.getByRole('region', { name: 'Other retrieved passages' })).toBeTruthy()
  })

  it('highlights the source card when a citation marker is activated', async () => {
    stubFetch(comparison)
    await search()
    const papers = await screen.findByRole('region', { name: 'Papers compared' })

    await userEvent.setup().click(within(papers).getByRole('button', { name: 'Source 1' }))

    const card = screen.getByRole('region', { name: 'Sources' }).querySelector('[data-highlighted="true"]')
    expect(card?.textContent).toContain('Source 1: Synthetic paper A')
  })

  it('says so when a list is empty', async () => {
    const body = structuredClone(comparison) as typeof comparison & { comparison: { similarities: unknown[] } }
    body.comparison.similarities = []
    stubFetch(body)
    await search()

    const similarities = await screen.findByRole('region', { name: 'Similarities' })
    expect(within(similarities).getByText('None identified in the retrieved passages.')).toBeTruthy()
  })

  it('shows a loading state while the request is pending', async () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))
    await search()

    expect(screen.getByText(/Comparing papers and checking citations/)).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Searching…' }).hasAttribute('disabled')).toBe(true)
  })

  it('shows no_results without comparison content', async () => {
    stubFetch(noResults)
    await search()

    expect(await screen.findByRole('heading', { name: 'No results' })).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Papers compared' })).toBeNull()
  })

  it('shows insufficient_evidence with the retrieved passages', async () => {
    stubFetch(insufficientEvidenceComparisonFixture)
    await search()

    expect(await screen.findByRole('heading', { name: 'Not enough evidence to answer' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Closest passages found' })).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Papers compared' })).toBeNull()
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

  it('times out after 60 s, not 30 s', async () => {
    vi.useFakeTimers()
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))
    render(<ComparisonPage />)
    fireEvent.click(screen.getByRole('button', { name: 'Search' }))

    await act(async () => { await vi.advanceTimersByTimeAsync(30_000) })
    expect(screen.queryByRole('alert')).toBeNull()
    await act(async () => { await vi.advanceTimersByTimeAsync(30_001) })
    expect(screen.getByRole('alert').textContent).toContain('took too long')
  })

  it('reports response metadata to the parent', async () => {
    stubFetch(comparison)
    const onMetadataChange = vi.fn()
    render(<ComparisonPage onMetadataChange={onMetadataChange} />)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Search' }))

    await screen.findByRole('heading', { name: 'Papers compared' })
    expect(onMetadataChange).toHaveBeenCalledWith(comparison.metadata)
  })
})
