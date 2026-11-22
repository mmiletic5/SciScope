import { act, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { answeredFixture } from '../../api/fixtures'
import { ExplorerPage } from './ExplorerPage'

describe('ExplorerPage answered flow', () => {
  it('renders the answer and its claim-linked source after a successful request', async () => {
    const user = userEvent.setup()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(answeredFixture), { status: 200 })))
    render(<ExplorerPage />)

    await user.type(screen.getByRole('textbox', { name: 'Research question' }), 'Test question')
    await user.click(screen.getByRole('button', { name: 'Search' }))

    expect(await screen.findByText(answeredFixture.answer)).toBeTruthy()
    expect(screen.getByText(answeredFixture.claims[0].text)).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Source 1' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: /Source 1:/ })).toBeTruthy()
  })

  it('restores the synthetic-data notice for each new response after dismissal', async () => {
    const user = userEvent.setup()
    const secondResponse = { ...answeredFixture, request_id: 'synthetic-second-response' }
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(answeredFixture), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(secondResponse), { status: 200 })))
    render(<ExplorerPage />)
    const field = screen.getByRole('textbox', { name: 'Research question' })
    await user.type(field, 'Test question')
    await user.click(screen.getByRole('button', { name: 'Search' }))

    const notice = await screen.findByText('Responses are synthetic test data from the fake backend, not real literature.')
    await user.click(screen.getByRole('button', { name: 'Dismiss' }))
    expect(notice.isConnected).toBe(false)

    await user.click(screen.getByRole('button', { name: 'Search' }))
    expect(await screen.findByText('Responses are synthetic test data from the fake backend, not real literature.')).toBeTruthy()
  })

  it('retains the editable question and retries an API-unreachable request', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn()
      .mockRejectedValueOnce(new TypeError('backend is stopped'))
      .mockResolvedValueOnce(new Response(JSON.stringify(answeredFixture), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    render(<ExplorerPage />)
    const field = screen.getByRole('textbox', { name: 'Research question' })
    await user.type(field, 'Keep this question')
    await user.click(screen.getByRole('button', { name: 'Search' }))

    expect(await screen.findByText('Cannot reach the SciScope API. Is the backend running?')).toBeTruthy()
    expect(field).toHaveProperty('value', 'Keep this question')
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText(answeredFixture.answer)).toBeTruthy()
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it('retries with the current field value after the question is edited', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn()
      .mockRejectedValueOnce(new TypeError('backend is stopped'))
      .mockResolvedValueOnce(new Response(JSON.stringify(answeredFixture), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    render(<ExplorerPage />)
    const field = screen.getByRole('textbox', { name: 'Research question' })
    await user.type(field, 'Original question')
    await user.click(screen.getByRole('button', { name: 'Search' }))
    expect(await screen.findByText('Cannot reach the SciScope API. Is the backend running?')).toBeTruthy()

    fireEvent.change(field, { target: { value: 'Edited question' } })
    await user.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText(answeredFixture.answer)).toBeTruthy()

    const secondRequest = fetchMock.mock.calls[1][1] as RequestInit
    expect(JSON.parse(String(secondRequest.body))).toMatchObject({ question: 'Edited question' })
  })

  it('keeps the question editable after the 30-second request timeout', async () => {
    vi.useFakeTimers()
    vi.stubGlobal('fetch', vi.fn((_url: string, init: RequestInit) => new Promise<Response>((_resolve, reject) => {
      init.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
    })))
    render(<ExplorerPage />)
    const field = screen.getByRole('textbox', { name: 'Research question' })
    fireEvent.change(field, { target: { value: 'Keep this question editable' } })
    fireEvent.click(screen.getByRole('button', { name: 'Search' }))

    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000)
    })

    expect(screen.getByText('The request took too long. Please try again.')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Try again' })).toBeTruthy()
    expect(field).toHaveProperty('value', 'Keep this question editable')
    expect(field).toHaveProperty('disabled', false)
    vi.useRealTimers()
  })
})
