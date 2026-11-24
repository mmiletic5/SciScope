import type { Evidence } from '../api/types'

type SourceCardProps = {
  evidence: Evidence
  number?: number
  highlighted: boolean
  /** DOM id prefix; use a distinct one per screen so ids stay unique across mounted screens. */
  idPrefix?: string
}

export function SourceCard({ evidence, number, highlighted, idPrefix = 'source' }: SourceCardProps) {
  const sourceId = `${idPrefix}-${encodeURIComponent(evidence.chunk_id)}`
  const doiHref = evidence.doi
    ? `https://doi.org/${encodeURIComponent(evidence.doi).replaceAll('%2F', '/')}`
    : null

  return (
    <article
      className={`source-card${highlighted ? ' source-card--highlighted' : ''}`}
      id={sourceId}
      data-highlighted={highlighted}
    >
      <h3>{number ? `Source ${number}: ${evidence.paper_title}` : evidence.paper_title}</h3>
      {doiHref && <a href={doiHref} target="_blank" rel="noopener noreferrer">{evidence.doi}</a>}
      <blockquote>{evidence.passage}</blockquote>
      <details>
        <summary>Details</summary>
        <p>{evidence.source_locator}</p>
      </details>
    </article>
  )
}
