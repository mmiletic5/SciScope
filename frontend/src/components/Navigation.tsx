export type ViewId = 'research-question' | 'evidence-comparison' | 'conflicting-evidence' | 'gaps-hypotheses'

type NavigationProps = {
  activeView: ViewId
  onNavigate: (view: ViewId) => void
}

const PREVIEW_ITEMS: Array<{ id: ViewId; label: string }> = [
  { id: 'evidence-comparison', label: 'Evidence comparison' },
  { id: 'conflicting-evidence', label: 'Conflicting evidence' },
  { id: 'gaps-hypotheses', label: 'Gaps & hypotheses' },
]

export function Navigation({ activeView, onNavigate }: NavigationProps) {
  return (
    <nav className="primary-navigation" aria-label="Primary navigation">
      <a
        href="#research-question"
        aria-current={activeView === 'research-question' ? 'page' : undefined}
        onClick={(event) => {
          event.preventDefault()
          onNavigate('research-question')
        }}
      >
        Research question
      </a>
      {PREVIEW_ITEMS.map(({ id, label }) => (
        <button
          key={id}
          type="button"
          aria-current={activeView === id ? 'page' : undefined}
          onClick={() => onNavigate(id)}
        >
          {label}
        </button>
      ))}
    </nav>
  )
}
