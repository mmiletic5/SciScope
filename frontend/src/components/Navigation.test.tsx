import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { Navigation } from './Navigation'

const ALL = ['research_question', 'evidence_comparison', 'conflicting_evidence', 'research_gap'] as const

describe('Navigation availability', () => {
  it('enables every entry when workflows are unknown (fixture mode or health failed)', () => {
    render(<Navigation activeView="research-question" onNavigate={vi.fn()} availableWorkflows={null} />)
    expect(screen.queryByText('Not available on this backend yet')).toBeNull()
    for (const name of ['Evidence comparison', 'Potential differences', 'Gaps & hypotheses']) {
      expect(screen.getByRole('button', { name }).hasAttribute('disabled')).toBe(false)
    }
  })

  it('enables every entry when health lists all workflows', () => {
    render(<Navigation activeView="research-question" onNavigate={vi.fn()} availableWorkflows={ALL} />)
    expect(screen.queryByText('Not available on this backend yet')).toBeNull()
  })

  it('disables an unlisted workflow with a note and does not navigate', async () => {
    const onNavigate = vi.fn()
    render(
      <Navigation
        activeView="research-question"
        onNavigate={onNavigate}
        availableWorkflows={['research_question', 'evidence_comparison']}
      />,
    )

    const button = screen.getByRole('button', { name: 'Potential differences' })
    expect(button.hasAttribute('disabled')).toBe(true)
    expect(button.getAttribute('aria-describedby')).toBeTruthy()
    expect(screen.getAllByText('Not available on this backend yet')).toHaveLength(2)
    await userEvent.setup().click(button)
    expect(onNavigate).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: 'Evidence comparison' }).hasAttribute('disabled')).toBe(false)
  })
})
