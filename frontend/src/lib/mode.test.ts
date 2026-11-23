import { describe, expect, it } from 'vitest'
import { answeredFixture, healthFixture } from '../api/fixtures'
import type { ComponentMetadata, QuestionMetadataV2 } from '../api/types.v2'
import { badgeFromHealth, badgeFromMetadata } from './mode'

const real: ComponentMetadata = { configured_origin: 'real', executed: true, is_test_data: false }

function metadata(retrieval: Partial<ComponentMetadata>, provider: Partial<ComponentMetadata>): QuestionMetadataV2 {
  return { retrieval: { ...real, ...retrieval }, answer_provider: { ...real, ...provider } }
}

describe('badgeFromMetadata', () => {
  it('is Live when both components are real and not test data', () => {
    expect(badgeFromMetadata(metadata({}, {}))).toEqual({ kind: 'live', label: 'Live' })
  })

  it('shows Demo (fake provider) when the provider is fake', () => {
    expect(badgeFromMetadata(answeredFixture.metadata).label).toBe('Demo (fake provider)')
    expect(badgeFromMetadata(metadata({}, { configured_origin: 'fake', is_test_data: true })).label)
      .toBe('Demo (fake provider)')
  })

  it.each([
    ['synthetic retrieval', metadata({ configured_origin: 'synthetic' }, {})],
    ['retrieval test data', metadata({ is_test_data: true }, {})],
    ['provider test data', metadata({}, { is_test_data: true })],
  ])('shows Demo (synthetic data) and never Live for %s', (_name, value) => {
    expect(badgeFromMetadata(value)).toEqual({ kind: 'demo', label: 'Demo (synthetic data)' })
  })
})

describe('badgeFromMetadata ignores executed (rev 2)', () => {
  it('shows Live for no_results with real components and an unexecuted provider', () => {
    expect(badgeFromMetadata(metadata({}, { executed: false }))).toEqual({ kind: 'live', label: 'Live' })
    expect(badgeFromMetadata(metadata({ executed: false }, { executed: false })).kind).toBe('live')
  })
})

describe('badgeFromHealth', () => {
  it('shows a demo badge for fake components', () => {
    expect(badgeFromHealth(healthFixture).label).toBe('Demo (fake provider)')
  })

  it('shows Live only for two real components', () => {
    const live = {
      ...healthFixture,
      components: { retrieval: { configured_origin: 'real' as const }, answer_provider: { configured_origin: 'real' as const } },
    }
    expect(badgeFromHealth(live).kind).toBe('live')
    const mixed = { ...live, components: { ...live.components, retrieval: { configured_origin: 'synthetic' as const } } }
    expect(badgeFromHealth(mixed).label).toBe('Demo (synthetic data)')
  })
})
