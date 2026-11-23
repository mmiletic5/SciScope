import { useEffect, useState } from 'react'
import { fetchHealth } from './api/client'
import type { QuestionMetadataV2 } from './api/types'
import { Header } from './components/Header'
import { Navigation, type ViewId } from './components/Navigation'
import { ExplorerPage } from './features/explorer/ExplorerPage'
import { ComparisonPreview } from './features/previews/ComparisonPreview'
import { ConflictsPreview } from './features/previews/ConflictsPreview'
import { GapsPreview } from './features/previews/GapsPreview'
import { badgeFromHealth, badgeFromMetadata, OFFLINE_BADGE, type ModeBadge } from './lib/mode'

function App() {
  const [metadata, setMetadata] = useState<QuestionMetadataV2 | null>(null)
  const [healthBadge, setHealthBadge] = useState<ModeBadge | null>(null)
  const [activeView, setActiveView] = useState<ViewId>('research-question')
  const pageTitle = {
    'research-question': 'Research question',
    'evidence-comparison': 'Evidence comparison',
    'conflicting-evidence': 'Conflicting evidence',
    'gaps-hypotheses': 'Gaps & hypotheses',
  }[activeView]

  useEffect(() => {
    let cancelled = false
    fetchHealth().then(
      (health) => { if (!cancelled) setHealthBadge(badgeFromHealth(health)) },
      () => { if (!cancelled) setHealthBadge(OFFLINE_BADGE) },
    )
    return () => { cancelled = true }
  }, [])

  // A question response reports what actually ran, so it overrides the health-based badge.
  const badge = metadata ? badgeFromMetadata(metadata) : healthBadge

  return (
    <div className="app-shell">
      <Header badge={badge} />
      <Navigation activeView={activeView} onNavigate={setActiveView} />
      <p className="visually-hidden" role="status" aria-live="polite">{pageTitle}</p>
      <main className="app-main">
        <div className="explorer-view" hidden={activeView !== 'research-question'}>
          <ExplorerPage onMetadataChange={setMetadata} />
        </div>
        {activeView === 'evidence-comparison' && <ComparisonPreview />}
        {activeView === 'conflicting-evidence' && <ConflictsPreview />}
        {activeView === 'gaps-hypotheses' && <GapsPreview />}
      </main>
      <footer className="app-footer">
        SciScope is a research aid and does not replace reading the original papers.
      </footer>
    </div>
  )
}

export default App
