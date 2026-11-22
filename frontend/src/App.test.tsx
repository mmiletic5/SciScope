import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'

describe('Research Question Explorer shell', () => {
  it('renders semantic header, navigation, main content, footer, and default mock badge', () => {
    render(<App />)

    expect(screen.getByRole('banner')).toBeTruthy()
    expect(screen.getByRole('navigation', { name: 'Primary navigation' })).toBeTruthy()
    expect(screen.getByRole('main')).toBeTruthy()
    expect(screen.getByRole('contentinfo')).toBeTruthy()
    expect(screen.getByText('MOCK · test data')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Research question' })).toBeTruthy()
    expect(screen.getByText('SciScope is a research aid and does not replace reading the original papers.')).toBeTruthy()
    expect(screen.getByRole('region', { name: 'Your results' }).getAttribute('aria-live')).toBe('polite')
  })

  it('announces the active page and keeps preview screens out of the Explorer task', () => {
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
