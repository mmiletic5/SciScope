import type { WorkflowV2 } from '../api/types'

export type ViewId = 'research-question' | 'evidence-comparison' | 'conflicting-evidence' | 'gaps-hypotheses'

type NavigationProps = {
  activeView: ViewId
  onNavigate: (view: ViewId) => void
  /** Workflows the backend lists in /api/health; null (unknown) keeps every entry enabled. */
  availableWorkflows?: readonly WorkflowV2[] | null
}

const VIEW_WORKFLOW: Record<ViewId, WorkflowV2> = {
  'research-question': 'research_question',
  'evidence-comparison': 'evidence_comparison',
  'conflicting-evidence': 'conflicting_evidence',
  'gaps-hypotheses': 'research_gap',
}

const UNAVAILABLE_NOTE = 'Not available on this backend yet'

const ITEMS: Array<{ id: ViewId; label: string }> = [
  { id: 'research-question', label: 'Research question' },
  { id: 'evidence-comparison', label: 'Evidence comparison' },
  { id: 'conflicting-evidence', label: 'Potential differences' },
  { id: 'gaps-hypotheses', label: 'Gaps & hypotheses' },
]

export function Navigation({ activeView, onNavigate, availableWorkflows = null }: NavigationProps) {
  return (
    <nav className="primary-navigation" aria-label="Primary navigation">
      {ITEMS.map(({ id, label }) => {
        const available = !availableWorkflows || availableWorkflows.includes(VIEW_WORKFLOW[id])
        const noteId = `nav-note-${id}`
        if (!available) {
          return (
            <span key={id} className="primary-navigation__unavailable">
              <button type="button" disabled aria-describedby={noteId}>{label}</button>
              <small id={noteId}>{UNAVAILABLE_NOTE}</small>
            </span>
          )
        }
        if (id === 'research-question') {
          return (
            <a
              key={id}
              href="#research-question"
              aria-current={activeView === id ? 'page' : undefined}
              onClick={(event) => {
                event.preventDefault()
                onNavigate(id)
              }}
            >
              {label}
            </a>
          )
        }
        return (
          <button
            key={id}
            type="button"
            aria-current={activeView === id ? 'page' : undefined}
            onClick={() => onNavigate(id)}
          >
            {label}
          </button>
        )
      })}
    </nav>
  )
}
