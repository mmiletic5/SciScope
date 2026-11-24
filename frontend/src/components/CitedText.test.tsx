import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { CitedText } from './CitedText'

describe('CitedText', () => {
  it('renders the text with one marker per distinct known source', async () => {
    const onActivate = vi.fn()
    render(
      <CitedText
        text="A cited statement."
        citationChunkIds={['a', 'b', 'a', 'unknown']}
        numberById={new Map([['a', 1], ['b', 2]])}
        onActivate={onActivate}
      />,
    )

    expect(screen.getByText(/A cited statement\./)).toBeTruthy()
    expect(screen.getAllByRole('button')).toHaveLength(2)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Source 2' }))
    expect(onActivate).toHaveBeenCalledWith('b')
  })

  it('renders plain text when nothing resolves', () => {
    render(<CitedText text="Only text." citationChunkIds={['x']} numberById={new Map()} onActivate={vi.fn()} />)
    expect(screen.queryAllByRole('button')).toHaveLength(0)
  })
})

describe('CitedText leaked ids', () => {
  it('never renders raw chunk ids found in the text', () => {
    const id = 'ab'.repeat(32)
    render(<CitedText text={`No difference. [${id}]`} citationChunkIds={['a']} numberById={new Map([['a', 1]])} onActivate={vi.fn()} />)
    expect(document.body.textContent).not.toContain(id)
    expect(screen.getByText(/No difference\./)).toBeTruthy()
  })
})
