import { useState } from 'react'
import type { InsufficientEvidenceResponse, QuestionMetadataV2 } from '../../api/types'
import { SourceCard } from '../../components/SourceCard'
import { PendingPanel } from '../../components/PendingPanel'
import { CorpusNote } from '../../components/CorpusNote'
import { QuestionForm } from '../explorer/QuestionForm'
import { ResultStates } from '../explorer/ResultStates'
import { useWorkflowQuestion } from '../workflow/useWorkflowQuestion'
import { GapsView } from './GapsView'

const EXAMPLES = [
  'What do the authors say their comparison of virus levels in colonies selected for low and high mite growth cannot settle, and what would they do next?',
]

export const NO_GAPS_MESSAGE =
  'No gaps could be identified from the retrieved passages. This does not show that none exist.'

type GapsPageProps = {
  onMetadataChange?: (metadata: QuestionMetadataV2) => void
}

function NoGapsFound({ response }: { response: InsufficientEvidenceResponse }) {
  return (
    <section className="insufficient-result" aria-labelledby="gap-insufficient-title">
      <h2 id="gap-insufficient-title">No gaps identified</h2>
      <p>{NO_GAPS_MESSAGE}</p>
      {response.evidence.length > 0 && (
        <div>
          <h3>Retrieved passages</h3>
          {response.evidence.map((evidence) => (
            <SourceCard key={evidence.chunk_id} evidence={evidence} highlighted={false} idPrefix="gap-source" />
          ))}
        </div>
      )}
    </section>
  )
}

export function GapsPage({ onMetadataChange }: GapsPageProps) {
  const [question, setQuestion] = useState(EXAMPLES[0])
  const { isPending, elapsedSeconds, response, error, submit, cancel } = useWorkflowQuestion('research_gap', onMetadataChange)
  const retry = () => void submit(question)

  return (
    <div className="explorer-page explorer-page--wide" id="research-gap">
      <section className="explorer-page__intro" aria-labelledby="gaps-title">
        <h1 id="gaps-title">Research Gaps &amp; Hypotheses</h1>
        <p>
          Find what the retrieved papers leave open, plus hypotheses suggested by the model. Results cover
          at most the 17 indexed papers.
        </p>
        <QuestionForm
          question={question}
          onQuestionChange={setQuestion}
          onSubmit={(value) => void submit(value)}
          isPending={isPending}
          label="Question about research gaps"
          inputId="gaps-question-input"
          examples={EXAMPLES}
        />
      </section>
      <section
        className="results-region"
        aria-labelledby="gaps-results-title"
        aria-live="polite"
        aria-busy={isPending}
      >
        <h2 id="gaps-results-title">Gap analysis</h2>
        {isPending ? (
          <PendingPanel message="Looking for research gaps and checking citations.…" elapsedSeconds={elapsedSeconds} onCancel={cancel} />
        ) : response?.status === 'answered' && response.workflow === 'research_gap' ? (
          <GapsView response={response} />
        ) : response?.status === 'insufficient_evidence' ? (
          <NoGapsFound response={response} />
        ) : response?.status === 'no_results' ? (
          <ResultStates response={response} onRetry={retry} idPrefix="gap-" />
        ) : error ? (
          <ResultStates error={error} onRetry={retry} idPrefix="gap-" />
        ) : (
          <p>Gaps, suggested hypotheses and their source passages will appear here after a search.</p>
        )}
      </section>
      <CorpusNote corpusVersion={response?.corpus.corpus_version} />
    </div>
  )
}
