import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import App from '../../App'

describe('static workflow previews', () => {
  it('opens the comparison preview with the required table and one main landmark', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Evidence comparison' }))

    expect(screen.getByRole('heading', { name: 'Evidence comparison' })).toBeTruthy()
    expect(screen.getByText('Preview — this feature is not connected to the backend yet.')).toBeTruthy()
    const table = screen.getByRole('table')
    for (const label of ['Stressor', 'Control group', 'Measure', 'Sample', 'Result', 'Claim source']) {
      expect(within(table).getByText(label)).toBeTruthy()
    }
    expect(within(table).getAllByText('[paper selected from results]')).toHaveLength(12)
    expect(screen.getAllByRole('main')).toHaveLength(1)
    expect(screen.getByRole('button', { name: 'Evidence comparison' }).getAttribute('aria-current')).toBe('page')
  })

  it('opens the conflicting-evidence preview with placeholder-only position and reason cards', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Conflicting evidence' }))

    expect(screen.getByRole('heading', { name: 'Conflicting evidence' })).toBeTruthy()
    expect(screen.getByText('Preview — this feature is not connected to the backend yet.')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Position A' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Position B' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Possible reasons' })).toBeTruthy()
    for (const label of ['Experimental conditions', 'Sample', 'Methods']) {
      expect(screen.getByRole('heading', { name: label })).toBeTruthy()
    }
    expect(screen.getAllByText('[placeholder]')).toHaveLength(5)
    expect(screen.getAllByRole('main')).toHaveLength(1)
  })

  it('opens the gaps preview with the unverified draft and disabled actions', async () => {
    const user = userEvent.setup()
    render(<App />)
    await user.click(screen.getByRole('button', { name: 'Gaps & hypotheses' }))

    expect(screen.getByRole('heading', { name: 'Gaps & hypotheses' })).toBeTruthy()
    expect(screen.getByText('Preview — this feature is not connected to the backend yet.')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'What is missing' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'What was found' })).toBeTruthy()
    expect(screen.getByText('Draft hypothesis · model suggestion · not a verified finding')).toBeTruthy()
    for (const label of ['Save', 'Edit', 'Dismiss']) {
      expect(screen.getByRole('button', { name: label }).hasAttribute('disabled')).toBe(true)
    }
    expect(screen.getAllByRole('main')).toHaveLength(1)
  })
})
