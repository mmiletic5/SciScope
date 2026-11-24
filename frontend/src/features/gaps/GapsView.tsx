import type { AnsweredResponse } from '../../api/types'
import { CitedText } from '../../components/CitedText'
import { EvidenceSources } from '../../components/EvidenceSources'
import { stripChunkIds } from '../../lib/stripChunkIds'
import { resolveCitations } from '../../lib/citations'
import { useSourceHighlight } from '../../lib/useSourceHighlight'

export type GapsAnswered = Extract<AnsweredResponse, { workflow: 'research_gap' }>

const ID_PREFIX = 'gap'
export const SPECULATIVE_LABEL = 'Suggested, not a finding'

const gapAnchorId = (gapId: string) => `gap-item-${gapId}`

export function GapsView({ response }: { response: GapsAnswered }) {
  const { gaps, hypotheses } = response.gap_analysis
  const { highlightedChunkId, activateSource } = useSourceHighlight(ID_PREFIX)
  // Number sources in the order they are shown: gaps first, then hypotheses.
  const shown = [...gaps, ...hypotheses].map((item) => ({
    claim_id: '',
    text: '',
    citation_chunk_ids: item.citation_chunk_ids,
  }))
  const { numberedEvidence, uncitedEvidence } = resolveCitations(shown, response.evidence)
  const numberById = new Map(numberedEvidence.map(({ number, evidence }) => [evidence.chunk_id, number]))
  const gapNumber = new Map(gaps.map((gap, index) => [gap.gap_id, index + 1]))

  return (
    <div className="answer-view gaps-view">
      <section aria-labelledby="gap-answer-title">
        <h2 id="gap-answer-title">Summary</h2>
        <p>{stripChunkIds(response.answer)}</p>
      </section>
      <section aria-labelledby="gap-gaps-title">
        <h2 id="gap-gaps-title">Gaps in the retrieved evidence</h2>
        <ol className="gap-list">
          {gaps.map((gap, index) => (
            <li className="gap-card" key={gap.gap_id} id={gapAnchorId(gap.gap_id)}>
              <h3>Gap {index + 1}</h3>
              <CitedText
                text={gap.text}
                citationChunkIds={gap.citation_chunk_ids}
                numberById={numberById}
                onActivate={activateSource}
              />
            </li>
          ))}
        </ol>
      </section>
      <section aria-labelledby="gap-hyp-title">
        <h2 id="gap-hyp-title">Suggested hypotheses</h2>
        {hypotheses.length === 0 ? (
          <p>No hypotheses were suggested for these gaps.</p>
        ) : (
          <ul className="gap-list">
            {hypotheses.map((hypothesis, index) => (
              <li
                className="hypothesis-card"
                key={hypothesis.hypothesis_id}
                aria-labelledby={`gap-${hypothesis.hypothesis_id}-title`}
              >
                <h3 id={`gap-${hypothesis.hypothesis_id}-title`}>Hypothesis {index + 1}</h3>
                <p className="speculative-label">{SPECULATIVE_LABEL}</p>
                <CitedText
                  text={hypothesis.text}
                  citationChunkIds={hypothesis.citation_chunk_ids}
                  numberById={numberById}
                  onActivate={activateSource}
                />
                <p className="hypothesis-rationale"><strong>Rationale:</strong> {stripChunkIds(hypothesis.rationale)}</p>
                <p className="hypothesis-gaps">
                  Based on:{' '}
                  {hypothesis.based_on_gap_ids.map((gapId, linkIndex) => (
                    <span key={gapId}>
                      {linkIndex > 0 && ', '}
                      <a href={`#${gapAnchorId(gapId)}`}>Gap {gapNumber.get(gapId) ?? gapId}</a>
                    </span>
                  ))}
                </p>
              </li>
            ))}
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
