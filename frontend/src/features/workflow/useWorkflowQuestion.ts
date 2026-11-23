import { useState } from 'react'
import { QuestionClientError, submitQuestion } from '../../api/client'
import type { QuestionMetadataV2, QuestionSuccess, WorkflowV2 } from '../../api/types'
import { createRequestId } from '../../lib/requestId'

/** Request state for one workflow screen: pending flag, last response or last error. */
export function useWorkflowQuestion(
  workflow: WorkflowV2,
  onMetadataChange?: (metadata: QuestionMetadataV2) => void,
) {
  const [isPending, setIsPending] = useState(false)
  const [response, setResponse] = useState<QuestionSuccess | null>(null)
  const [error, setError] = useState<QuestionClientError | null>(null)

  async function submit(question: string) {
    setIsPending(true)
    setResponse(null)
    setError(null)
    try {
      const result = await submitQuestion(question, createRequestId(), workflow)
      setResponse(result)
      onMetadataChange?.(result.metadata)
    } catch (caught) {
      const requestError = caught instanceof QuestionClientError
        ? caught
        : new QuestionClientError(
          'api_unreachable',
          'Cannot reach the SciScope API. Is the backend running?',
          true,
          createRequestId(),
        )
      setError(requestError)
      if (requestError.response?.metadata) onMetadataChange?.(requestError.response.metadata)
    } finally {
      setIsPending(false)
    }
  }

  return { isPending, response, error, submit }
}
