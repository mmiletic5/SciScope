import { PreviewBanner } from './PreviewBanner'

export function GapsPreview() {
  return (
    <section className="preview-page" aria-labelledby="gaps-title">
      <PreviewBanner />
      <h1 id="gaps-title">Gaps &amp; hypotheses</h1>
      <div className="preview-card-grid">
        <article className="preview-card">
          <h2>What is missing</h2>
          <p>[placeholder]</p>
        </article>
        <article className="preview-card">
          <h2>What was found</h2>
          <p>[placeholder]</p>
        </article>
      </div>
      <section className="draft-hypothesis" aria-label="Unverified draft hypothesis">
        <p>Draft hypothesis · model suggestion · not a verified finding</p>
        <div className="draft-hypothesis__actions">
          <button type="button" disabled>Save</button>
          <button type="button" disabled>Edit</button>
          <button type="button" disabled>Dismiss</button>
        </div>
      </section>
    </section>
  )
}
