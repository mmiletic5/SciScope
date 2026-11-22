import type { MockMetadata } from '../api/types'

type MockNoticeProps = {
  metadata: MockMetadata
  dismissed: boolean
  onDismiss: () => void
}

export function MockNotice({ metadata, dismissed, onDismiss }: MockNoticeProps) {
  const isMockResult = metadata.is_mock || metadata.is_test_data
  if (!isMockResult || dismissed) return null

  return (
    <aside className="mock-notice" aria-label="Synthetic data notice">
      <p>Responses are synthetic test data from the fake backend, not real literature.</p>
      <button type="button" onClick={onDismiss}>Dismiss</button>
    </aside>
  )
}
