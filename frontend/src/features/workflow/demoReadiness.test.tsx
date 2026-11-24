import { act, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import type { ReactElement } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { answeredFixtureByWorkflow, questionErrorFixture } from '../../api/fixtures'
import { HIGHLIGHT_MS } from '../../lib/useSourceHighlight'
import { ComparisonPage } from '../comparison/ComparisonPage'
import { ConflictsPage } from '../conflicts/ConflictsPage'
import { ExplorerPage } from '../explorer/ExplorerPage'
import { GapsPage } from '../gaps/GapsPage'

const SCREENS: {
  name: string
  element: () => ReactElement
  textbox: string
  examples: string[]
  workflow: keyof typeof answeredFixtureByWorkflow
}[] = [
  {
    name: 'Research Question',
    element: () => <ExplorerPage />,
    textbox: 'Research question',
    workflow: 'research_question',
    examples: [
      'In the experiment where forager bees were injected with a virus and then tracked with tags at the hive entrance, on which days after injection did the proportion of foragers coming back differ significantly from sham-injected controls, and how large was the gap on the first of those days?',
      'Does exposure to a glyphosate-based herbicide change the composition of the bee gut microbiota?',
    ],
  },
  {
    name: 'Evidence Comparison',
    element: () => <ComparisonPage />,
    textbox: 'Comparison question',
    workflow: 'evidence_comparison',
    examples: ['How does sensitivity to sugar water change in foragers exposed to a toxic mineral versus foragers infected with a virus?'],
  },
  {
    name: 'Conflicting Evidence',
    element: () => <ConflictsPage />,
    textbox: 'Question about differences',
    workflow: 'conflicting_evidence',
    examples: ['Is the literature consistent on whether Varroa parasitism suppresses or boosts immune gene expression in developing worker bees?'],
  },
  {
    name: 'Research Gaps',
    element: () => <GapsPage />,
    textbox: 'Question about research gaps',
    workflow: 'research_gap',
    examples: ['What do the authors say their comparison of virus levels in colonies selected for low and high mite growth cannot settle, and what would they do next?'],
  },
]

const NOTE = /Corpus: 17 open-access honey bee papers \(PLOS ONE\)\. Answers are generated from retrieved passages and may be wrong; check the cited sources\./

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
  Reflect.deleteProperty(HTMLElement.prototype, 'scrollIntoView')
})

function stubFetch(body: unknown, status = 200) {
  const fetchMock = vi.fn(() => Promise.resolve(new Response(JSON.stringify(body), { status })))
  vi.stubGlobal('fetch', fetchMock)
  return fetchMock
}

describe.each(SCREENS)('$name screen', ({ element, textbox, examples, workflow }) => {
  it('fills the form from each example chip without submitting', async () => {
    const fetchMock = stubFetch(answeredFixtureByWorkflow[workflow])
    render(element())
    for (const example of examples) {
      await userEvent.setup().click(screen.getByRole('button', { name: example }))
      expect((screen.getByRole('textbox', { name: textbox }) as HTMLTextAreaElement).value).toBe(example)
    }
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('shows the corpus note, and the corpus version once a response arrived', async () => {
    stubFetch(answeredFixtureByWorkflow[workflow])
    render(element())
    expect(screen.getByText(NOTE)).toBeTruthy()
    expect(document.querySelector('.corpus-note code')).toBeNull()

    await userEvent.setup().click(screen.getByRole('button', { name: examples[0] }))
    await userEvent.setup().click(screen.getByRole('button', { name: 'Search' }))
    await screen.findByRole('heading', { name: /Sources/ })
    const version = answeredFixtureByWorkflow[workflow].corpus.corpus_version
    expect(document.querySelector('.corpus-note code')?.textContent).toBe(version)
  })

  it('shows elapsed seconds, the wait note and cancels back to idle', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    let signal: AbortSignal | undefined
    vi.stubGlobal('fetch', vi.fn((_url: string, init: RequestInit) => {
      const requestSignal = init.signal as AbortSignal
      signal = requestSignal
      return new Promise<Response>((_resolve, reject) => {
        requestSignal.addEventListener('abort', () => reject(new Error('aborted')))
      })
    }))
    render(element())
    await userEvent.setup({ advanceTimers: vi.advanceTimersByTime }).click(screen.getByRole('button', { name: examples[0] }))
    fireEvent.click(screen.getByRole('button', { name: 'Search' }))

    expect(screen.getByText('Answers can take up to a minute.')).toBeTruthy()
    expect(screen.getByTestId('elapsed').textContent).toBe('Elapsed: 0 s')
    await act(async () => { await vi.advanceTimersByTimeAsync(3000) })
    expect(screen.getByTestId('elapsed').textContent).toBe('Elapsed: 3 s')

    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect((signal as AbortSignal | undefined)?.aborted).toBe(true)
    expect(screen.queryByRole('button', { name: 'Cancel' })).toBeNull()
    expect(screen.queryByRole('alert')).toBeNull()
    expect((screen.getByRole('button', { name: 'Search' }) as HTMLButtonElement).disabled).toBe(false)
  })

  it('keeps a Try again button for a retryable error', async () => {
    stubFetch(questionErrorFixture, 503)
    render(element())
    await userEvent.setup().click(screen.getByRole('button', { name: examples[0] }))
    await userEvent.setup().click(screen.getByRole('button', { name: 'Search' }))
    expect(await screen.findByRole('button', { name: 'Try again' })).toBeTruthy()
  })

  it('shows paper title and DOI link on evidence cards and highlights briefly on citation click', async () => {
    const scrollIntoView = vi.fn()
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', { value: scrollIntoView, configurable: true })
    stubFetch(answeredFixtureByWorkflow[workflow])
    render(element())
    await userEvent.setup().click(screen.getByRole('button', { name: examples[0] }))
    await userEvent.setup().click(screen.getByRole('button', { name: 'Search' }))
    await screen.findByRole('heading', { name: /Sources/ })

    const evidence = answeredFixtureByWorkflow[workflow].evidence[0]
    const link = screen.getAllByRole('link', { name: evidence.doi })[0]
    expect(link.getAttribute('href')).toBe(`https://doi.org/${evidence.doi}`)
    expect(link.getAttribute('target')).toBe('_blank')
    expect(link.getAttribute('rel')).toContain('noopener')
    expect(screen.getAllByText(evidence.paper_title, { exact: false }).length).toBeGreaterThan(0)

    vi.useFakeTimers({ shouldAdvanceTime: true })
    fireEvent.click(screen.getAllByRole('button', { name: /^Source \d+$/ })[0])
    expect(scrollIntoView).toHaveBeenCalled()
    expect(document.querySelector('[data-highlighted="true"]')).toBeTruthy()
    act(() => { vi.advanceTimersByTime(HIGHLIGHT_MS + 10) })
    expect(document.querySelector('[data-highlighted="true"]')).toBeNull()
  })
})

describe.each(SCREENS)('$name corpus version footer', ({ element, textbox, workflow }) => {
  async function submitAndWait(body: unknown) {
    stubFetch(body)
    render(element())
    const user = userEvent.setup()
    await user.type(screen.getByRole('textbox', { name: textbox }), 'A question about bees?')
    await user.click(screen.getByRole('button', { name: 'Search' }))
  }

  it('shows the corpus version after a no_results response', async () => {
    const answered = answeredFixtureByWorkflow[workflow]
    const body = {
      ...answered,
      status: 'no_results',
      answer: null,
      claims: [],
      evidence: [],
      metadata: { ...answered.metadata, answer_provider: { ...answered.metadata.answer_provider, executed: false } },
    }
    for (const key of ['comparison', 'conflicts', 'gap_analysis']) Reflect.deleteProperty(body, key)
    await submitAndWait(body)
    await vi.waitFor(() => {
      expect(document.querySelector('.corpus-note code')?.textContent).toBe(body.corpus.corpus_version)
    })
  })

  it('shows the corpus version after an insufficient_evidence response', async () => {
    const body = { ...answeredFixtureByWorkflow[workflow], status: 'insufficient_evidence', answer: null, claims: [] }
    for (const key of ['comparison', 'conflicts', 'gap_analysis']) Reflect.deleteProperty(body, key)
    await submitAndWait(body)
    await vi.waitFor(() => {
      expect(document.querySelector('.corpus-note code')?.textContent).toBe(body.corpus.corpus_version)
    })
  })
})
