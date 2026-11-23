import type { AnsweredResponse } from '../../api/types'
import { CitationMarker } from '../../components/CitationMarker'
import { EvidenceSources } from '../../components/EvidenceSources'
import { resolveCitations } from '../../lib/citations'
import { useSourceHighlight } from '../../lib/useSourceHighlight'

type AnswerViewProps = {
  response: AnsweredResponse
}

export function AnswerView({ response }: AnswerViewProps) {
  const { highlightedChunkId, activateSource } = useSourceHighlight('rq')
  const { numberedEvidence, uncitedEvidence } = resolveCitations(response.claims, response.evidence)
  const numberById = new Map(numberedEvidence.map(({ number, evidence }) => [evidence.chunk_id, number]))

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
      <EvidenceSources
        numberedEvidence={numberedEvidence}
        uncitedEvidence={uncitedEvidence}
        highlightedChunkId={highlightedChunkId}
        idPrefix="rq"
      />
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
