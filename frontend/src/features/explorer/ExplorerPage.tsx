import { useState } from 'react'
import { submitQuestion } from '../../api/client'
import { QuestionClientError } from '../../api/client'
import { createRequestId } from '../../lib/requestId'
import type { MockMetadata, QuestionSuccess } from '../../api/types'
import { MockNotice } from '../../components/MockNotice'
import { AnswerView } from './AnswerView'
import { QuestionForm } from './QuestionForm'
import { ResultStates } from './ResultStates'

type ExplorerPageProps = {
  onMetadataChange?: (metadata: MockMetadata) => void
}

export function ExplorerPage({ onMetadataChange }: ExplorerPageProps) {
  const [isPending, setIsPending] = useState(false)
  const [response, setResponse] = useState<QuestionSuccess | null>(null)
  const [clientError, setClientError] = useState<QuestionClientError | null>(null)
  const [question, setQuestion] = useState('')
  const [dismissedNoticeFor, setDismissedNoticeFor] = useState<string | null>(null)

  async function handleSubmit(question: string) {
    setIsPending(true)
    setResponse(null)
    setClientError(null)
    try {
      const result = await submitQuestion(question, createRequestId())
      setResponse(result)
      onMetadataChange?.(result.metadata)
    } catch (error) {
      const requestError = error instanceof QuestionClientError
        ? error
        : new QuestionClientError(
          'api_unreachable',
          'Cannot reach the SciScope API. Is the backend running?',
          true,
          createRequestId(),
        )
      setClientError(requestError)
      if (requestError.response) onMetadataChange?.(requestError.response.metadata)
    } finally {
      setIsPending(false)
    }
  }

  const latestMetadata = response?.metadata ?? clientError?.response?.metadata ?? null
  const latestResponseId = response?.request_id ?? clientError?.requestId ?? null

  return (
    <div className="explorer-page" id="research-question">
      <section className="explorer-page__intro" aria-labelledby="explorer-title">
        <h1 id="explorer-title">Research question</h1>
        <p>Ask a focused question to explore the passages available in the current corpus.</p>
        <QuestionForm
          question={question}
          onQuestionChange={setQuestion}
          onSubmit={handleSubmit}
          isPending={isPending}
        />
      </section>
      <section
        className="results-region"
        aria-labelledby="results-title"
        aria-live="polite"
        aria-busy={isPending}
      >
        <h2 id="results-title">Your results</h2>
        {latestMetadata && latestResponseId && (
          <MockNotice
            metadata={latestMetadata}
            dismissed={dismissedNoticeFor === latestResponseId}
            onDismiss={() => setDismissedNoticeFor(latestResponseId)}
          />
        )}
        {isPending ? (
          <div className="results-loading" aria-live="polite">
            <p>Retrieving passages and checking citations…</p>
            <div className="results-skeleton" aria-hidden="true" />
          </div>
        ) : response?.status === 'answered' ? (
          <AnswerView response={response} />
        ) : response ? (
          <ResultStates response={response} onRetry={() => void handleSubmit(question)} />
        ) : clientError ? (
          <ResultStates error={clientError} onRetry={() => void handleSubmit(question)} />
        ) : (
          <p>Your answer and source passages will appear here after a search.</p>
        )}
      </section>
    </div>
  )
}
