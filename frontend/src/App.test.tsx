import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { answeredFixture, healthFixture } from './api/fixtures'
import App from './App'

function stubBackend(options: { healthOk: boolean; question?: unknown }) {
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    if (url === '/api/health') {
      return options.healthOk
        ? Promise.resolve(new Response(JSON.stringify(healthFixture), { status: 200 }))
        : Promise.reject(new TypeError('connection refused'))
    }
    return Promise.resolve(new Response(JSON.stringify(options.question), { status: 200 }))
  }))
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('Research Question Explorer shell', () => {
  it('renders semantic header, navigation, main content and footer', () => {
    stubBackend({ healthOk: true })
    render(<App />)

    expect(screen.getByRole('banner')).toBeTruthy()
    expect(screen.getByRole('navigation', { name: 'Primary navigation' })).toBeTruthy()
    expect(screen.getByRole('main')).toBeTruthy()
    expect(screen.getByRole('contentinfo')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Research question' })).toBeTruthy()
    expect(screen.getByText('SciScope is a research aid and does not replace reading the original papers.')).toBeTruthy()
    expect(screen.getByRole('region', { name: 'Your results' }).getAttribute('aria-live')).toBe('polite')
  })

  it('announces the active page and keeps preview screens out of the Explorer task', () => {
    stubBackend({ healthOk: true })
    render(<App />)

    const activePageLink = screen.getByRole('link', { name: 'Research question' })
    expect(activePageLink.getAttribute('aria-current')).toBe('page')
    expect(activePageLink.getAttribute('href')).toBe('#research-question')
    expect(document.getElementById('research-question')).toBeTruthy()
    expect(document.querySelectorAll('#research-question')).toHaveLength(1)
    expect(screen.getByRole('textbox', { name: 'Research question' })).toBeTruthy()
    expect(screen.getByRole('status').textContent).toContain('Research question')
    expect(screen.queryByText('Preview — this feature is not connected to the backend yet.')).toBeNull()
  })
})

describe('mode badge', () => {
  it('shows the health-based demo badge on load', async () => {
    stubBackend({ healthOk: true })
    render(<App />)

    expect(await screen.findByText('Demo (fake provider)')).toBeTruthy()
    expect(fetch).toHaveBeenCalledWith('/api/health', expect.any(Object))
  })

  it('shows "Backend offline" without breaking the page when health fails', async () => {
    stubBackend({ healthOk: false })
    render(<App />)

    expect(await screen.findByText('Backend offline')).toBeTruthy()
    expect(screen.getByRole('textbox', { name: 'Research question' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Search' })).toBeTruthy()
  })

  it('switches to Live after a response from two real, executed, non-test components', async () => {
    const real = { configured_origin: 'real', executed: true, is_test_data: false }
    const liveResponse = { ...answeredFixture, metadata: { retrieval: real, answer_provider: real } }
    stubBackend({ healthOk: true, question: liveResponse })
    const user = userEvent.setup()
    render(<App />)
    expect(await screen.findByText('Demo (fake provider)')).toBeTruthy()

    await user.type(screen.getByRole('textbox', { name: 'Research question' }), 'Test question')
    await user.click(screen.getByRole('button', { name: 'Search' }))

    expect(await screen.findByText('Live')).toBeTruthy()
    expect(screen.queryByText('Demo (fake provider)')).toBeNull()
  })

  it('keeps a demo badge after a fake-provider response', async () => {
    stubBackend({ healthOk: false, question: answeredFixture })
    const user = userEvent.setup()
    render(<App />)
    expect(await screen.findByText('Backend offline')).toBeTruthy()

    await user.type(screen.getByRole('textbox', { name: 'Research question' }), 'Test question')
    await user.click(screen.getByRole('button', { name: 'Search' }))

    expect(await screen.findByText('Demo (fake provider)')).toBeTruthy()
    expect(screen.queryByText('Live')).toBeNull()
  })
})
