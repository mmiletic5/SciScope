import { useState } from 'react'
import type { QuestionMetadataV2 } from '../../api/types'
import { QuestionForm } from '../explorer/QuestionForm'
import { ResultStates } from '../explorer/ResultStates'
import { useWorkflowQuestion } from '../workflow/useWorkflowQuestion'
import { ComparisonView } from './ComparisonView'

const EXAMPLES = [
  'How do the retrieved papers differ in their findings on Varroa mite effects on honey bee immune gene expression?',
]

type ComparisonPageProps = {
  onMetadataChange?: (metadata: QuestionMetadataV2) => void
}

export function ComparisonPage({ onMetadataChange }: ComparisonPageProps) {
  const [question, setQuestion] = useState(EXAMPLES[0])
  const { isPending, response, error, submit } = useWorkflowQuestion('evidence_comparison', onMetadataChange)
  const retry = () => void submit(question)

  return (
    <div className="explorer-page explorer-page--wide" id="evidence-comparison">
      <section className="explorer-page__intro" aria-labelledby="comparison-title">
        <h1 id="comparison-title">Evidence comparison</h1>
        <p>Ask how papers in the corpus compare. Results cover at most the 17 indexed papers.</p>
        <QuestionForm
          question={question}
          onQuestionChange={setQuestion}
          onSubmit={(value) => void submit(value)}
          isPending={isPending}
          label="Comparison question"
          inputId="comparison-question-input"
          examples={EXAMPLES}
        />
      </section>
      <section
        className="results-region"
        aria-labelledby="comparison-results-title"
        aria-live="polite"
        aria-busy={isPending}
      >
        <h2 id="comparison-results-title">Comparison results</h2>
        {isPending ? (
          <div className="results-loading" aria-live="polite">
            <p>Comparing papers and checking citations. This can take up to a minute…</p>
            <div className="results-skeleton" aria-hidden="true" />
          </div>
        ) : response?.status === 'answered' && response.workflow === 'evidence_comparison' ? (
          <ComparisonView response={response} />
        ) : response && response.status !== 'answered' ? (
          <ResultStates response={response} onRetry={retry} idPrefix="cmp-" />
        ) : error ? (
          <ResultStates error={error} onRetry={retry} idPrefix="cmp-" />
        ) : (
          <p>Your comparison and source passages will appear here after a search.</p>
        )}
      </section>
    </div>
  )
}
