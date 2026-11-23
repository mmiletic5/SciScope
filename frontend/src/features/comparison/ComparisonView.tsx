import type { AnsweredResponse } from '../../api/types'
import { CitedText } from '../../components/CitedText'
import { EvidenceSources } from '../../components/EvidenceSources'
import { stripChunkIds } from '../../lib/stripChunkIds'
import { resolveCitations } from '../../lib/citations'
import { useSourceHighlight } from '../../lib/useSourceHighlight'

export type ComparisonAnswered = Extract<AnsweredResponse, { workflow: 'evidence_comparison' }>

const ID_PREFIX = 'cmp'
const NONE_FOUND = 'None identified in the retrieved passages.'

export function ComparisonView({ response }: { response: ComparisonAnswered }) {
  const { subjects, similarities, differences } = response.comparison
  const { highlightedChunkId, activateSource } = useSourceHighlight(ID_PREFIX)
  // Number sources in the order they are shown: papers, similarities, differences.
  const shown = [...subjects, ...similarities, ...differences].map((item) => ({
    claim_id: '',
    text: '',
    citation_chunk_ids: item.citation_chunk_ids,
  }))
  const { numberedEvidence, uncitedEvidence } = resolveCitations(shown, response.evidence)
  const numberById = new Map(numberedEvidence.map(({ number, evidence }) => [evidence.chunk_id, number]))

  function cited(text: string, ids: string[]) {
    return <CitedText text={text} citationChunkIds={ids} numberById={numberById} onActivate={activateSource} />
  }

  return (
    <div className="answer-view comparison-view">
      <section aria-labelledby="cmp-answer-title">
        <h2 id="cmp-answer-title">Answer</h2>
        <p>{stripChunkIds(response.answer)}</p>
      </section>
      <section aria-labelledby="cmp-papers-title">
        <h2 id="cmp-papers-title">Papers compared</h2>
        <div className="comparison-grid">
          {subjects.map((subject) => (
            <article className="comparison-card" key={subject.subject_id}>
              <h3>{subject.paper_title}</h3>
              <p className="comparison-card__doi">{subject.doi}</p>
              {cited(subject.summary, subject.citation_chunk_ids)}
            </article>
          ))}
        </div>
      </section>
      <section aria-labelledby="cmp-similarities-title">
        <h2 id="cmp-similarities-title">Similarities</h2>
        {similarities.length === 0 ? <p>{NONE_FOUND}</p> : (
          <ul className="cited-list">
            {similarities.map((item) => <li key={item.item_id}>{cited(item.text, item.citation_chunk_ids)}</li>)}
          </ul>
        )}
      </section>
      <section aria-labelledby="cmp-differences-title">
        <h2 id="cmp-differences-title">Differences</h2>
        {differences.length === 0 ? <p>{NONE_FOUND}</p> : (
          <ul className="cited-list">
            {differences.map((item) => <li key={item.item_id}>{cited(item.text, item.citation_chunk_ids)}</li>)}
          </ul>
        )}
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
