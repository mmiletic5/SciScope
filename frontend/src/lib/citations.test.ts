import { describe, expect, it } from 'vitest'
import type { Claim, Evidence } from '../api/types'
import { resolveCitations } from './citations'

const evidence: Evidence[] = [
  { chunk_id: 'chunk-a', doi: '10.0000/a', source_locator: 'loc-a', passage: 'Synthetic passage A.', paper_title: 'Synthetic source A' },
  { chunk_id: 'chunk-b', doi: '10.0000/b', source_locator: 'loc-b', passage: 'Synthetic passage B.', paper_title: 'Synthetic source B' },
  { chunk_id: 'chunk-uncited', doi: '10.0000/c', source_locator: 'loc-c', passage: 'Synthetic passage C.', paper_title: 'Synthetic source C' },
]

describe('resolveCitations', () => {
  it('numbers evidence in first claim-citation order and removes duplicate/unknown IDs', () => {
    const claims: Claim[] = [
      { claim_id: 'claim-a', text: 'Synthetic claim A.', citation_chunk_ids: ['chunk-b', 'missing', 'chunk-a'] },
      { claim_id: 'claim-b', text: 'Synthetic claim B.', citation_chunk_ids: ['chunk-b', 'chunk-a'] },
    ]

    const resolved = resolveCitations(claims, evidence)

    expect(resolved.numberedEvidence.map(({ number, evidence: item }) => [number, item.chunk_id]))
      .toEqual([[1, 'chunk-b'], [2, 'chunk-a']])
    expect(resolved.uncitedEvidence.map((item) => item.chunk_id)).toEqual(['chunk-uncited'])
  })

  it('leaves every evidence item unnumbered if there are no claims', () => {
    const resolved = resolveCitations([], evidence)

    expect(resolved.numberedEvidence).toEqual([])
    expect(resolved.uncitedEvidence).toEqual(evidence)
  })
})
