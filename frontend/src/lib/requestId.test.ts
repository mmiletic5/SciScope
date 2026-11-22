import { describe, expect, it } from 'vitest'
import { createRequestId, isValidRequestId } from './requestId'

describe('request ID helpers', () => {
  it('creates a valid bounded request ID', () => {
    const requestId = createRequestId()

    expect(isValidRequestId(requestId)).toBe(true)
    expect(requestId.length).toBeLessThanOrEqual(128)
  })

  it.each(['a', 'A0._:-', 'x'.repeat(128)])('accepts valid ID %s', (requestId) => {
    expect(isValidRequestId(requestId)).toBe(true)
  })

  it.each(['', 'x'.repeat(129), 'contains space', 'contains/slash', 'ümlaut'])('rejects invalid ID %s', (requestId) => {
    expect(isValidRequestId(requestId)).toBe(false)
  })
})
