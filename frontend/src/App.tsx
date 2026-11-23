import { useState } from 'react'
import type { MockMetadata } from './api/types'
import { Header } from './components/Header'
import { Navigation, type ViewId } from './components/Navigation'
import { ExplorerPage } from './features/explorer/ExplorerPage'
import { ComparisonPreview } from './features/previews/ComparisonPreview'
import { ConflictsPreview } from './features/previews/ConflictsPreview'
import { GapsPreview } from './features/previews/GapsPreview'

function App() {
  const [metadata, setMetadata] = useState<MockMetadata | null>(null)
  const [activeView, setActiveView] = useState<ViewId>('research-question')
  const pageTitle = {
    'research-question': 'Research question',
    'evidence-comparison': 'Evidence comparison',
    'conflicting-evidence': 'Conflicting evidence',
    'gaps-hypotheses': 'Gaps & hypotheses',
  }[activeView]

  return (
    <div className="app-shell">
      <Header metadata={metadata} />
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
