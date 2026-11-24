import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Header } from './Header'

describe('Header mode badge', () => {
  it('shows no badge until a mode is known', () => {
    render(<Header />)
    expect(document.querySelector('.mode-badge')).toBeNull()
  })

  it.each(['Live', 'Demo (fake provider)', 'Demo (synthetic data)', 'Backend offline'])('shows the %s badge', (label) => {
    render(<Header badge={{ kind: 'demo', label }} />)
    expect(screen.getByText(label)).toBeTruthy()
  })
})
