import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { answeredFixtureByWorkflow, healthFixture, noResultsFixture } from './api/fixtures'
import App from './App'

const real = { configured_origin: 'real', executed: true, is_test_data: false }

function stubBackend(health: unknown | null, question?: unknown) {
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    if (url === '/api/health') {
      return health
        ? Promise.resolve(new Response(JSON.stringify(health), { status: 200 }))
        : Promise.reject(new TypeError('connection refused'))
    }
    return Promise.resolve(new Response(JSON.stringify(question), { status: 200 }))
  }))
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('workflow availability from /api/health', () => {
  it('disables workflows missing from health with a short note', async () => {
    stubBackend({ ...healthFixture, workflows: ['research_question', 'evidence_comparison'] })
    render(<App />)

    expect(await screen.findAllByText('Not available on this backend yet')).toHaveLength(2)
    expect(screen.getByRole('button', { name: 'Conflicting evidence' }).hasAttribute('disabled')).toBe(true)
    expect(screen.getByRole('button', { name: 'Gaps & hypotheses' }).hasAttribute('disabled')).toBe(true)
    expect(screen.getByRole('button', { name: 'Evidence comparison' }).hasAttribute('disabled')).toBe(false)
  })

  it('keeps every entry enabled when health failed', async () => {
    stubBackend(null)
    render(<App />)

    expect(await screen.findByText('Backend offline')).toBeTruthy()
    expect(screen.queryByText('Not available on this backend yet')).toBeNull()
    expect(screen.getByRole('button', { name: 'Conflicting evidence' }).hasAttribute('disabled')).toBe(false)
  })

  it('keeps every entry enabled when health lists every workflow', async () => {
    stubBackend(healthFixture)
    render(<App />)

    expect(await screen.findByText('Demo (fake provider)')).toBeTruthy()
    expect(screen.queryByText('Not available on this backend yet')).toBeNull()
  })
})

describe('Evidence comparison screen in the app', () => {
  it('replaces the preview with a working screen that uses the shared form', async () => {
    stubBackend(healthFixture, answeredFixtureByWorkflow.evidence_comparison)
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Evidence comparison' }))

    expect(screen.getByRole('heading', { name: 'Evidence comparison', level: 1 })).toBeTruthy()
    expect(screen.queryByText('Preview — this feature is not connected to the backend yet.')).toBeNull()
    expect(screen.getByRole('button', { name: 'Evidence comparison' }).getAttribute('aria-current')).toBe('page')
    expect(screen.getAllByRole('main')).toHaveLength(1)

    await user.click(screen.getByRole('button', { name: 'Search' }))
    expect(await screen.findByRole('heading', { name: 'Papers compared' })).toBeTruthy()
  })

  it('shows Live for no_results with real components (executed is ignored)', async () => {
    const noResults = {
      ...noResultsFixture,
      workflow: 'evidence_comparison',
      metadata: {
        retrieval: real,
        answer_provider: { ...real, executed: false },
      },
    }
    stubBackend(healthFixture, noResults)
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Evidence comparison' }))
    await user.click(screen.getByRole('button', { name: 'Search' }))

    expect(await screen.findByRole('heading', { name: 'No results' })).toBeTruthy()
    expect(screen.getByText('Live')).toBeTruthy()
  })

  it('shows Live from health before the first question when both components are real', async () => {
    stubBackend({
      ...healthFixture,
      components: { retrieval: { configured_origin: 'real' }, answer_provider: { configured_origin: 'real' } },
    })
    render(<App />)

    expect(await screen.findByText('Live')).toBeTruthy()
  })
})
