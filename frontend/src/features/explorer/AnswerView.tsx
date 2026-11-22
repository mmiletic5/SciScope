import { useState } from 'react'
import type { AnsweredResponse } from '../../api/types'
import { CitationMarker } from '../../components/CitationMarker'
import { SourceCard } from '../../components/SourceCard'
import { resolveCitations } from '../../lib/citations'

type AnswerViewProps = {
  response: AnsweredResponse
}

export function AnswerView({ response }: AnswerViewProps) {
  const [highlightedChunkId, setHighlightedChunkId] = useState<string | null>(null)
  const { numberedEvidence, uncitedEvidence } = resolveCitations(response.claims, response.evidence)
  const numberById = new Map(numberedEvidence.map(({ number, evidence }) => [evidence.chunk_id, number]))

  function activateSource(chunkId: string) {
    setHighlightedChunkId(chunkId)
    const behavior = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'
    document.getElementById(`source-${encodeURIComponent(chunkId)}`)
      ?.scrollIntoView({ behavior, block: 'center' })
  }

  return (
    <div className="answer-view">
      <section aria-labelledby="answer-title">
        <h2 id="answer-title">Answer</h2>
        <p>{response.answer}</p>
      </section>
      <section aria-labelledby="claims-title">
        <h2 id="claims-title">Claims</h2>
        <ol>
          {response.claims.map((claim) => {
            const seen = new Set<string>()
            const citationNumbers = claim.citation_chunk_ids
              .filter((chunkId) => {
                if (seen.has(chunkId) || !numberById.has(chunkId)) return false
                seen.add(chunkId)
                return true
              })
              .map((chunkId) => ({ chunkId, number: numberById.get(chunkId)! }))
            return (
              <li key={claim.claim_id}>
                <p>{claim.text}</p>
                {citationNumbers.map(({ chunkId, number }) => (
                  <CitationMarker key={chunkId} number={number} onActivate={() => activateSource(chunkId)} />
                ))}
              </li>
            )
          })}
        </ol>
      </section>
      {numberedEvidence.length > 0 && (
        <section aria-labelledby="sources-title">
          <h2 id="sources-title">Sources</h2>
          {numberedEvidence.map(({ number, evidence }) => (
            <SourceCard
              key={evidence.chunk_id}
              evidence={evidence}
              number={number}
              highlighted={highlightedChunkId === evidence.chunk_id}
            />
          ))}
        </section>
      )}
      {uncitedEvidence.length > 0 && (
        <section aria-labelledby="uncited-title">
          <h2 id="uncited-title">Other retrieved passages</h2>
          {uncitedEvidence.map((evidence) => (
            <SourceCard
              key={evidence.chunk_id}
              evidence={evidence}
              highlighted={highlightedChunkId === evidence.chunk_id}
            />
          ))}
        </section>
      )}
      <details className="provenance">
        <summary>About this result</summary>
        <dl>
          <dt>Corpus version</dt><dd>{response.corpus.corpus_version}</dd>
          <dt>Source contract version</dt><dd>{response.corpus.source_contract_version}</dd>
          <dt>Delivery digest</dt><dd>{response.corpus.delivery_digest}</dd>
        </dl>
      </details>
    </div>
  )
}
