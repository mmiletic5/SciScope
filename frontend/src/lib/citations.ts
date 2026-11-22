import type { Claim, Evidence } from '../api/types'

export type NumberedEvidence = {
  number: number
  evidence: Evidence
}

export type CitationResolution = {
  numberedEvidence: NumberedEvidence[]
  uncitedEvidence: Evidence[]
}

export function resolveCitations(claims: Claim[], evidence: Evidence[]): CitationResolution {
  const evidenceById = new Map(evidence.map((item) => [item.chunk_id, item]))
  const numberedEvidence: NumberedEvidence[] = []
  const numberById = new Map<string, number>()

  for (const claim of claims) {
    for (const chunkId of claim.citation_chunk_ids) {
      const item = evidenceById.get(chunkId)
      if (!item || numberById.has(chunkId)) continue
      const number = numberedEvidence.length + 1
      numberById.set(chunkId, number)
      numberedEvidence.push({ number, evidence: item })
    }
  }

  const uncitedEvidence = evidence.filter((item) => !numberById.has(item.chunk_id))
  return { numberedEvidence, uncitedEvidence }
}
