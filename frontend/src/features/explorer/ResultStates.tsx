import type { InsufficientEvidenceResponse, NoResultsResponse } from '../../api/types'
import { QuestionClientError } from '../../api/client'
import { SourceCard } from '../../components/SourceCard'

type ResultStatesProps = {
  response?: NoResultsResponse | InsufficientEvidenceResponse
  error?: QuestionClientError
  onRetry: () => void
}

export function ResultStates({ response, error, onRetry }: ResultStatesProps) {
  if (response?.status === 'no_results') {
    return (
      <section className="empty-result" aria-labelledby="no-results-title">
        <h2 id="no-results-title">No results</h2>
        <p>No relevant passages were found in the corpus.</p>
        <p>Try rephrasing your question with different terms or a narrower focus.</p>
      </section>
    )
  }

  if (response?.status === 'insufficient_evidence') {
    return (
      <section className="insufficient-result" aria-labelledby="insufficient-title">
        <h2 id="insufficient-title">Not enough evidence to answer</h2>
        <p>The system declined to answer rather than guess because the available passages do not support a reliable answer.</p>
        {response.evidence.length > 0 && (
          <div>
            <h3>Closest passages found</h3>
            {response.evidence.map((evidence) => (
              <SourceCard key={evidence.chunk_id} evidence={evidence} highlighted={false} />
            ))}
          </div>
        )}
      </section>
    )
  }

  if (!error) return null

  return (
    <section className="status-panel status-panel--error" role="alert" aria-labelledby="error-title">
      <h2 id="error-title">We could not complete that request</h2>
      <p>{error.message}</p>
      <p className="request-reference">Reference: {error.requestId}</p>
      {error.retryable && <button type="button" onClick={onRetry}>Try again</button>}
    </section>
  )
}
