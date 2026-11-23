import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { QuestionForm } from './QuestionForm'
import { ExplorerPage } from './ExplorerPage'

describe('QuestionForm', () => {
  it('shows the editable question field and live character count', () => {
    render(<QuestionForm onSubmit={vi.fn()} isPending={false} />)

    expect(screen.getByRole('textbox', { name: 'Research question' })).toBeTruthy()
    expect(screen.getByText('0 / 2,000')).toBeTruthy()
    expect(screen.getByRole('group', { name: 'Example questions' })).toBeTruthy()
  })

  it('fills an example without submitting it', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()
    render(<QuestionForm onSubmit={onSubmit} isPending={false} />)

    const example = 'Did younger and older worker pupae respond in the same direction, in terms of immune gene expression, when they were parasitized by Varroa mites?'
    expect(screen.getByRole('button', { name: example }).textContent).toBe(example)
    await user.click(screen.getByRole('button', { name: example }))

    expect(screen.getByRole('textbox', { name: 'Research question' })).toHaveProperty('value', example)
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it.each([
    ['whitespace only', '   '],
    ['over 2,000 characters', 'x'.repeat(2001)],
  ])('rejects %s and shows an inline validation message', async (_label, value) => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()
    render(<QuestionForm onSubmit={onSubmit} isPending={false} />)

    fireEvent.change(screen.getByRole('textbox', { name: 'Research question' }), { target: { value } })
    await user.click(screen.getByRole('button', { name: 'Search' }))

    expect(screen.getByText('Enter a question between 1 and 2,000 characters.')).toBeTruthy()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('submits the trimmed valid question and accepts the 2,000 character limit', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()
    render(<QuestionForm onSubmit={onSubmit} isPending={false} />)
    const field = screen.getByRole('textbox', { name: 'Research question' })

    fireEvent.change(field, { target: { value: '  What does this test?  ' } })
    await user.click(screen.getByRole('button', { name: 'Search' }))
    expect(onSubmit).toHaveBeenCalledWith('What does this test?')

    await user.clear(field)
    fireEvent.change(field, { target: { value: 'x'.repeat(2000) } })
    await user.click(screen.getByRole('button', { name: 'Search' }))
    expect(onSubmit).toHaveBeenLastCalledWith('x'.repeat(2000))
  })

  it('prevents edits and duplicate submissions while pending and announces loading', () => {
    render(<QuestionForm onSubmit={vi.fn()} isPending />)

    expect(screen.getByRole('textbox', { name: 'Research question' })).toHaveProperty('disabled', true)
    expect(screen.getByRole('button', { name: 'Searching…' })).toHaveProperty('disabled', true)
    expect(screen.getByRole('status').textContent).toContain('Retrieving passages and checking citations…')
  })
})

describe('ExplorerPage', () => {
  it('shows the initial instructions and empty results area', () => {
    render(<ExplorerPage />)

    expect(screen.getByRole('heading', { name: 'Your results' })).toBeTruthy()
    expect(screen.getByText('Your answer and source passages will appear here after a search.')).toBeTruthy()
  })

  it('shows an accessible busy results area while the request is pending', async () => {
    const user = userEvent.setup()
    let resolveRequest: ((response: Response) => void) | undefined
    vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>((resolve) => {
      resolveRequest = resolve
    })))
    render(<ExplorerPage />)

    await user.type(screen.getByRole('textbox', { name: 'Research question' }), 'Test question')
    await user.click(screen.getByRole('button', { name: 'Search' }))

    const results = screen.getByRole('region', { name: 'Your results' })
    expect(results).toHaveProperty('ariaBusy', 'true')
    expect(results.textContent).toContain('Retrieving passages and checking citations…')

    resolveRequest?.(new Response(JSON.stringify({
      api_version: 'v1',
      request_id: 'test-page-001',
      workflow: 'research_question',
      status: 'no_results',
      answer: null,
      claims: [],
      evidence: [],
      corpus: {
        corpus_version: 'synthetic-v1',
        source_contract_version: 'synthetic-v1',
        delivery_digest: 'synthetic-only',
      },
      metadata: { is_mock: true, is_test_data: true },
    }), { status: 200 }))
  })
})
