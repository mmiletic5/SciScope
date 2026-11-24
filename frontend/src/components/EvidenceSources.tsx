import type { Evidence } from '../api/types'
import type { NumberedEvidence } from '../lib/citations'
import { SourceCard } from './SourceCard'

type EvidenceSourcesProps = {
  numberedEvidence: NumberedEvidence[]
  uncitedEvidence: Evidence[]
  highlightedChunkId: string | null
  idPrefix: string
}

/** "Sources" (cited, numbered) and "Other retrieved passages" (uncited) sections. */
export function EvidenceSources({ numberedEvidence, uncitedEvidence, highlightedChunkId, idPrefix }: EvidenceSourcesProps) {
  return (
    <>
      {numberedEvidence.length > 0 && (
        <section aria-labelledby={`${idPrefix}-sources-title`}>
          <h2 id={`${idPrefix}-sources-title`}>Sources</h2>
          {numberedEvidence.map(({ number, evidence }) => (
            <SourceCard
              key={evidence.chunk_id}
              evidence={evidence}
              number={number}
              idPrefix={`${idPrefix}-source`}
              highlighted={highlightedChunkId === evidence.chunk_id}
            />
          ))}
        </section>
      )}
      {uncitedEvidence.length > 0 && (
        <section aria-labelledby={`${idPrefix}-uncited-title`}>
          <h2 id={`${idPrefix}-uncited-title`}>Other retrieved passages</h2>
          {uncitedEvidence.map((evidence) => (
            <SourceCard
              key={evidence.chunk_id}
              evidence={evidence}
              idPrefix={`${idPrefix}-source`}
              highlighted={highlightedChunkId === evidence.chunk_id}
            />
          ))}
        </section>
      )}
    </>
  )
}
