import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

// Each new screen must be reachable from the navigation and render its fixture without a backend.
const SCREENS = [
  { nav: 'Evidence comparison', title: 'Evidence comparison', heading: 'Papers compared' },
  { nav: 'Potential differences', title: 'Potential differences', heading: 'Potential differences for review' },
  { nav: 'Gaps & hypotheses', title: 'Research Gaps & Hypotheses', heading: 'Suggested hypotheses' },
] as const

describe('fixture mode (VITE_API_MODE=fixtures)', () => {
  it.each(SCREENS)('renders the $nav fixture end to end', async ({ nav, title, heading }) => {
    vi.stubEnv('VITE_API_MODE', 'fixtures')
    const fetchMock = vi.fn(() => Promise.reject(new Error('network must not be used')))
    vi.stubGlobal('fetch', fetchMock)
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: nav }))
    expect(screen.getByRole('button', { name: nav }).getAttribute('aria-current')).toBe('page')
    expect(screen.getByRole('heading', { level: 1, name: title })).toBeTruthy()
    // Hidden views are excluded from the role queries, so this is the active screen's button.
    await user.click(screen.getByRole('button', { name: 'Search' }))

    const results = await screen.findByRole('heading', { name: heading })
    // Fixture content is synthetic; it must be what is on screen.
    expect(within(results.closest('main')!).getAllByText(/synthetic/i).length).toBeGreaterThan(0)
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
