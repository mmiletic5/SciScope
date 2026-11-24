import { useEffect, useRef, useState } from 'react'
import { QuestionClientError, submitQuestion } from '../../api/client'
import type { QuestionMetadataV2, QuestionSuccess, WorkflowV2 } from '../../api/types'
import { createRequestId } from '../../lib/requestId'

/**
 * Request state for one workflow screen: pending flag, elapsed seconds, last
 * response or last error. `cancel` aborts the running request and returns to idle.
 */
export function useWorkflowQuestion(
  workflow: WorkflowV2,
  onMetadataChange?: (metadata: QuestionMetadataV2) => void,
) {
  const [isPending, setIsPending] = useState(false)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [response, setResponse] = useState<QuestionSuccess | null>(null)
  const [error, setError] = useState<QuestionClientError | null>(null)
  const controllerRef = useRef<AbortController | null>(null)

  useEffect(() => {
    if (!isPending) return
    const startedAt = Date.now()
    const id = setInterval(() => setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000)), 1000)
    return () => clearInterval(id)
  }, [isPending])

  useEffect(() => () => controllerRef.current?.abort(), [])

  async function submit(question: string) {
    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller
    setIsPending(true)
    setElapsedSeconds(0)
    setResponse(null)
    setError(null)
    try {
      const result = await submitQuestion(question, createRequestId(), workflow, controller.signal)
      if (controller.signal.aborted) return
      setResponse(result)
      onMetadataChange?.(result.metadata)
    } catch (caught) {
      if (controller.signal.aborted) return
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
      if (controllerRef.current === controller) {
        controllerRef.current = null
        setIsPending(false)
      }
    }
  }

  function cancel() {
    controllerRef.current?.abort()
    controllerRef.current = null
    setIsPending(false)
  }

  return { isPending, elapsedSeconds, response, error, submit, cancel }
}
