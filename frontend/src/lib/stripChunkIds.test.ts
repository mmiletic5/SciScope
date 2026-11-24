import { describe, expect, it } from 'vitest'
import { stripChunkIds } from './stripChunkIds'

const ID1 = '866145e0' + 'a1'.repeat(28)
const ID2 = 'DE3EB5A9' + 'B2'.repeat(28)

describe('stripChunkIds', () => {
  it('removes a bracketed id at the end of a sentence', () => {
    expect(stripChunkIds(`No difference from controls. [${ID1}]`)).toBe('No difference from controls.')
  })
  it('removes several bracketed ids on separate lines', () => {
    expect(stripChunkIds(`Same.\n[${ID1}]\n[${ID2}]`)).toBe('Same.')
  })
  it('removes ids inside a comma/semicolon separated group, either case', () => {
    expect(stripChunkIds(`Same. [${ID1}, ${ID2}; ${ID1}]`)).toBe('Same.')
    expect(stripChunkIds(`Same. (${ID2})`)).toBe('Same.')
  })
  it('removes a bare id and fixes spacing before punctuation', () => {
    expect(stripChunkIds(`As in ${ID1} the data agree .`)).toBe('As in the data agree.')
  })
  it('keeps short bracketed numbers and longer hex runs', () => {
    expect(stripChunkIds('Earlier work [20] and [3, 4] agrees.')).toBe('Earlier work [20] and [3, 4] agrees.')
    const longer = 'a'.repeat(65)
    expect(stripChunkIds(longer)).toBe(longer)
  })
  it('returns an empty string when only ids remain', () => {
    expect(stripChunkIds(`[${ID1}] [${ID2}]`)).toBe('')
  })
})
