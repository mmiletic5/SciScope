import { PreviewBanner } from './PreviewBanner'

const POSSIBLE_REASONS = ['Experimental conditions', 'Sample', 'Methods']

export function ConflictsPreview() {
  return (
    <section className="preview-page" aria-labelledby="conflicts-title">
      <PreviewBanner />
      <h1 id="conflicts-title">Conflicting evidence</h1>
      <div className="preview-card-grid">
        <article className="preview-card">
          <h2>Position A</h2>
          <p>[placeholder]</p>
        </article>
        <article className="preview-card">
          <h2>Position B</h2>
          <p>[placeholder]</p>
        </article>
      </div>
      <section aria-labelledby="possible-reasons-title">
        <h2 id="possible-reasons-title">Possible reasons</h2>
        <div className="preview-card-grid preview-card-grid--three">
          {POSSIBLE_REASONS.map((reason) => (
            <article className="preview-card" key={reason}>
              <h3>{reason}</h3>
              <p>[placeholder]</p>
            </article>
          ))}
        </div>
      </section>
    </section>
  )
}
