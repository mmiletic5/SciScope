import { useEffect, useState } from 'react'
import { fetchHealth } from './api/client'
import type { QuestionMetadataV2, WorkflowV2 } from './api/types'
import { Header } from './components/Header'
import { Navigation, type ViewId } from './components/Navigation'
import { ExplorerPage } from './features/explorer/ExplorerPage'
import { ComparisonPage } from './features/comparison/ComparisonPage'
import { ConflictsPage } from './features/conflicts/ConflictsPage'
import { GapsPage } from './features/gaps/GapsPage'
import { badgeFromHealth, badgeFromMetadata, OFFLINE_BADGE, type ModeBadge } from './lib/mode'

function App() {
  const [metadata, setMetadata] = useState<QuestionMetadataV2 | null>(null)
  const [healthBadge, setHealthBadge] = useState<ModeBadge | null>(null)
  const [availableWorkflows, setAvailableWorkflows] = useState<readonly WorkflowV2[] | null>(null)
  const [activeView, setActiveView] = useState<ViewId>('research-question')
  const pageTitle = {
    'research-question': 'Research question',
    'evidence-comparison': 'Evidence comparison',
    'conflicting-evidence': 'Potential differences',
    'gaps-hypotheses': 'Research Gaps & Hypotheses',
  }[activeView]

  useEffect(() => {
    let cancelled = false
    fetchHealth().then(
      (health) => {
        if (cancelled) return
        setHealthBadge(badgeFromHealth(health))
        setAvailableWorkflows(health.workflows)
      },
      () => { if (!cancelled) setHealthBadge(OFFLINE_BADGE) },
    )
    return () => { cancelled = true }
  }, [])

  // A question response reports what actually ran, so it overrides the health-based badge.
  const badge = metadata ? badgeFromMetadata(metadata) : healthBadge

  return (
    <div className="app-shell">
      <Header badge={badge} />
      <Navigation activeView={activeView} onNavigate={setActiveView} availableWorkflows={availableWorkflows} />
      <p className="visually-hidden" role="status" aria-live="polite">{pageTitle}</p>
      <main className="app-main">
        <div className="explorer-view" hidden={activeView !== 'research-question'}>
          <ExplorerPage onMetadataChange={setMetadata} />
        </div>
        <div className="explorer-view" hidden={activeView !== 'evidence-comparison'}>
          <ComparisonPage onMetadataChange={setMetadata} />
        </div>
        <div className="explorer-view" hidden={activeView !== 'conflicting-evidence'}>
          <ConflictsPage onMetadataChange={setMetadata} />
        </div>
        <div className="explorer-view" hidden={activeView !== 'gaps-hypotheses'}><GapsPage onMetadataChange={setMetadata} /></div>
      </main>
      <footer className="app-footer">
        SciScope is a research aid and does not replace reading the original papers.
      </footer>
    </div>
  )
}

export default App
