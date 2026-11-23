import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import App from '../../App'

describe('static workflow previews', () => {
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
