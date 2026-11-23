import type { AnsweredResponse } from '../../api/types'
import { CitedText } from '../../components/CitedText'
import { EvidenceSources } from '../../components/EvidenceSources'
import { resolveCitations } from '../../lib/citations'
import { useSourceHighlight } from '../../lib/useSourceHighlight'

export type ConflictsAnswered = Extract<AnsweredResponse, { workflow: 'conflicting_evidence' }>

const ID_PREFIX = 'cfl'

export function ConflictsView({ response }: { response: ConflictsAnswered }) {
  const { review_note: reviewNote, items } = response.conflicts
  const { highlightedChunkId, activateSource } = useSourceHighlight(ID_PREFIX)
  // Number sources in the order they are shown: item by item, position by position.
  const shown = items.flatMap((item) => item.positions).map((position) => ({
    claim_id: '',
    text: '',
    citation_chunk_ids: position.citation_chunk_ids,
  }))
  const { numberedEvidence, uncitedEvidence } = resolveCitations(shown, response.evidence)
  const numberById = new Map(numberedEvidence.map(({ number, evidence }) => [evidence.chunk_id, number]))

  return (
    <div className="answer-view conflicts-view">
      <aside className="review-note" role="note" aria-labelledby="cfl-note-title">
        <h2 id="cfl-note-title">Review note</h2>
        <p>{reviewNote}</p>
      </aside>
      <section aria-labelledby="cfl-answer-title">
        <h2 id="cfl-answer-title">Summary</h2>
        <p>{response.answer}</p>
      </section>
      <section aria-labelledby="cfl-items-title">
        <h2 id="cfl-items-title">Potential differences for review</h2>
        <div className="conflict-list">
          {items.map((item) => (
            <article className="conflict-card" key={item.item_id} aria-labelledby={`cfl-${item.item_id}-title`}>
              <h3 id={`cfl-${item.item_id}-title`}>{item.topic}</h3>
              <p>{item.summary}</p>
              <div className="conflict-positions">
                {item.positions.map((position, index) => (
                  <section
                    className="conflict-position"
                    key={position.position_id}
                    aria-label={`${item.topic}: position ${index + 1}`}
                  >
                    <h4>Position {index + 1}</h4>
                    <CitedText
                      text={position.text}
                      citationChunkIds={position.citation_chunk_ids}
                      numberById={numberById}
                      onActivate={activateSource}
                    />
                  </section>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>
      <EvidenceSources
        numberedEvidence={numberedEvidence}
        uncitedEvidence={uncitedEvidence}
        highlightedChunkId={highlightedChunkId}
        idPrefix={ID_PREFIX}
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
