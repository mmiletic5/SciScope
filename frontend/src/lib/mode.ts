import type { HealthResponse, QuestionMetadataV2 } from '../api/types.v2'
import { isLiveMode } from '../api/types.v2'

export type ModeBadge = { kind: 'live' | 'demo' | 'offline'; label: string }

export const OFFLINE_BADGE: ModeBadge = { kind: 'offline', label: 'Backend offline' }

function demoBadge(answerProviderOrigin: string): ModeBadge {
  return {
    kind: 'demo',
    label: answerProviderOrigin === 'fake' ? 'Demo (fake provider)' : 'Demo (synthetic data)',
  }
}

/** Badge for a question response: Live only when `isLiveMode` says so (contract rule). */
export function badgeFromMetadata(metadata: QuestionMetadataV2): ModeBadge {
  if (isLiveMode(metadata)) return { kind: 'live', label: 'Live' }
  return demoBadge(metadata.answer_provider.configured_origin)
}

/** Badge before any question: health only reports configured origins. */
export function badgeFromHealth(health: HealthResponse): ModeBadge {
  const { retrieval, answer_provider: provider } = health.components
  if (retrieval.configured_origin === 'real' && provider.configured_origin === 'real') {
    return { kind: 'live', label: 'Live' }
  }
  return demoBadge(provider.configured_origin)
}
