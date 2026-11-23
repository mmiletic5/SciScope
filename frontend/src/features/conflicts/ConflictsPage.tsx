import { useState } from 'react'
import type { InsufficientEvidenceResponse, QuestionMetadataV2 } from '../../api/types'
import { SourceCard } from '../../components/SourceCard'
import { QuestionForm } from '../explorer/QuestionForm'
import { ResultStates } from '../explorer/ResultStates'
import { useWorkflowQuestion } from '../workflow/useWorkflowQuestion'
import { ConflictsView } from './ConflictsView'

const EXAMPLES = [
  'Do the retrieved papers report differing findings on Varroa mite effects on honey bee immune gene expression?',
]

export const NO_DIFFERENCES_MESSAGE =
  'No potential differences were identified in the retrieved passages. This does not show that none exist.'

type ConflictsPageProps = {
  onMetadataChange?: (metadata: QuestionMetadataV2) => void
}

function NoDifferencesFound({ response }: { response: InsufficientEvidenceResponse }) {
  return (
    <section className="insufficient-result" aria-labelledby="cfl-insufficient-title">
      <h2 id="cfl-insufficient-title">No potential differences identified</h2>
      <p>{NO_DIFFERENCES_MESSAGE}</p>
      {response.evidence.length > 0 && (
        <div>
          <h3>Retrieved passages</h3>
          {response.evidence.map((evidence) => (
            <SourceCard key={evidence.chunk_id} evidence={evidence} highlighted={false} idPrefix="cfl-source" />
          ))}
        </div>
      )}
    </section>
  )
}

export function ConflictsPage({ onMetadataChange }: ConflictsPageProps) {
  const [question, setQuestion] = useState(EXAMPLES[0])
  const { isPending, response, error, submit } = useWorkflowQuestion('conflicting_evidence', onMetadataChange)
  const retry = () => void submit(question)

  return (
    <div className="explorer-page explorer-page--wide" id="conflicting-evidence">
      <section className="explorer-page__intro" aria-labelledby="conflicts-title">
        <h1 id="conflicts-title">Potential differences</h1>
        <p>
          Find statements in the indexed papers that may differ, for you to review. Results cover at most
          the 17 indexed papers.
        </p>
        <QuestionForm
          question={question}
          onQuestionChange={setQuestion}
          onSubmit={(value) => void submit(value)}
          isPending={isPending}
          label="Question about differences"
          inputId="conflicts-question-input"
          examples={EXAMPLES}
        />
      </section>
      <section
        className="results-region"
        aria-labelledby="conflicts-results-title"
        aria-live="polite"
        aria-busy={isPending}
      >
        <h2 id="conflicts-results-title">Review results</h2>
        {isPending ? (
          <div className="results-loading" aria-live="polite">
            <p>Looking for potential differences and checking citations. This can take up to a minute…</p>
            <div className="results-skeleton" aria-hidden="true" />
          </div>
        ) : response?.status === 'answered' && response.workflow === 'conflicting_evidence' ? (
          <ConflictsView response={response} />
        ) : response?.status === 'insufficient_evidence' ? (
          <NoDifferencesFound response={response} />
        ) : response?.status === 'no_results' ? (
          <ResultStates response={response} onRetry={retry} idPrefix="cfl-" />
        ) : error ? (
          <ResultStates error={error} onRetry={retry} idPrefix="cfl-" />
        ) : (
          <p>Potential differences and their source passages will appear here after a search.</p>
        )}
      </section>
    </div>
  )
}
