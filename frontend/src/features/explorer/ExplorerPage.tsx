import { useState } from 'react'
import type { QuestionMetadataV2 } from '../../api/types'
import { CorpusNote } from '../../components/CorpusNote'
import { PendingPanel } from '../../components/PendingPanel'
import { useWorkflowQuestion } from '../workflow/useWorkflowQuestion'
import { AnswerView } from './AnswerView'
import { QuestionForm } from './QuestionForm'
import { ResultStates } from './ResultStates'

type ExplorerPageProps = {
  onMetadataChange?: (metadata: QuestionMetadataV2) => void
}

const EXAMPLES = [
  'In the experiment where forager bees were injected with a virus and then tracked with tags at the hive entrance, on which days after injection did the proportion of foragers coming back differ significantly from sham-injected controls, and how large was the gap on the first of those days?',
  'Does exposure to a glyphosate-based herbicide change the composition of the bee gut microbiota?',
]

export function ExplorerPage({ onMetadataChange }: ExplorerPageProps) {
  const [question, setQuestion] = useState('')
  const { isPending, elapsedSeconds, response, error, submit, cancel } =
    useWorkflowQuestion('research_question', onMetadataChange)
  const retry = () => void submit(question)

  return (
    <div className="explorer-page" id="research-question">
      <section className="explorer-page__intro" aria-labelledby="explorer-title">
        <h1 id="explorer-title">Research question</h1>
        <p>Ask a focused question to explore the passages available in the current corpus.</p>
        <QuestionForm
          question={question}
          onQuestionChange={setQuestion}
          onSubmit={(value) => void submit(value)}
          isPending={isPending}
          examples={EXAMPLES}
        />
      </section>
      <section
        className="results-region"
        aria-labelledby="results-title"
        aria-live="polite"
        aria-busy={isPending}
      >
        <h2 id="results-title">Your results</h2>
        {isPending ? (
          <PendingPanel
            message="Retrieving passages and checking citations…"
            elapsedSeconds={elapsedSeconds}
            onCancel={cancel}
          />
        ) : response?.status === 'answered' ? (
          <AnswerView response={response} />
        ) : response ? (
          <ResultStates response={response} onRetry={retry} />
        ) : error ? (
          <ResultStates error={error} onRetry={retry} />
        ) : (
          <p>Your answer and source passages will appear here after a search.</p>
        )}
      </section>
      <CorpusNote corpusVersion={response?.corpus.corpus_version} />
    </div>
  )
}
