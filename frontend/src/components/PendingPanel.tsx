type PendingPanelProps = {
  message: string
  elapsedSeconds: number
  onCancel: () => void
}

/** Long-wait indicator: elapsed seconds, expected duration note and a Cancel button. */
export function PendingPanel({ message, elapsedSeconds, onCancel }: PendingPanelProps) {
  return (
    <div className="results-loading">
      <p>{message}</p>
      <p className="pending-elapsed" data-testid="elapsed">Elapsed: {elapsedSeconds} s</p>
      <p className="pending-note">Answers can take up to a minute.</p>
      <button type="button" onClick={onCancel}>Cancel</button>
      <div className="results-skeleton" aria-hidden="true" />
    </div>
  )
}
