import { PreviewBanner } from './PreviewBanner'

const COMPARISON_FIELDS = [
  'Stressor',
  'Control group',
  'Measure',
  'Sample',
  'Result',
  'Claim source',
]

export function ComparisonPreview() {
  return (
    <section className="preview-page" aria-labelledby="comparison-title">
      <PreviewBanner />
      <h1 id="comparison-title">Evidence comparison</h1>
      <p>Choose papers from research results to compare their evidence.</p>
      <div className="comparison-table-wrap">
        <table className="comparison-table">
          <thead>
            <tr>
              <th scope="col">Field</th>
              <th scope="col">Paper 1</th>
              <th scope="col">Paper 2</th>
            </tr>
          </thead>
          <tbody>
            {COMPARISON_FIELDS.map((field) => (
              <tr key={field}>
                <th scope="row">{field}</th>
                <td>[paper selected from results]</td>
                <td>[paper selected from results]</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
