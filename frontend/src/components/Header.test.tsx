import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Header } from './Header'

describe('Header test-data badge', () => {
  it('shows the badge by default', () => {
    render(<Header />)
    expect(screen.getByText('MOCK · test data')).toBeTruthy()
  })

  it.each([
    [{ is_mock: true, is_test_data: false }],
    [{ is_mock: false, is_test_data: true }],
    [{ is_mock: true, is_test_data: true }],
  ])('shows the badge when either metadata flag is true', (metadata) => {
    render(<Header metadata={metadata} />)
    expect(screen.getByText('MOCK · test data')).toBeTruthy()
  })

  it('hides the badge only when a response explicitly reports both flags false', () => {
    render(<Header metadata={{ is_mock: false, is_test_data: false }} />)
    expect(screen.queryByText('MOCK · test data')).toBeNull()
  })
})
