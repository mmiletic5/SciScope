import { describe, expect, it } from 'vitest'
import {
  answeredFixture,
  answeredFixtureByWorkflow,
  healthFixture,
  insufficientEvidenceComparisonFixture,
  insufficientEvidenceFixture,
  invalidRequestErrorFixture,
  noResultsFixture,
  questionErrorFixture,
} from './fixtures'
import { WORKFLOWS_V2 } from './types.v2'
import { isErrorV2, isHealthV2, isSuccessV2 } from './validate'

type Json = Record<string, any> // eslint-disable-line @typescript-eslint/no-explicit-any

function clone(value: unknown): Json {
  return structuredClone(value) as Json
}

describe('contract fixtures', () => {
  it.each(WORKFLOWS_V2.map((workflow) => [workflow]))('the %s answered fixture validates', (workflow) => {
    expect(isSuccessV2(answeredFixtureByWorkflow[workflow], workflow)).toBe(true)
  })

  it('the no_results and insufficient_evidence fixtures validate', () => {
    expect(isSuccessV2(noResultsFixture)).toBe(true)
    expect(isSuccessV2(insufficientEvidenceFixture)).toBe(true)
    expect(isSuccessV2(insufficientEvidenceComparisonFixture)).toBe(true)
  })

  it('the error and health fixtures validate (error without metadata included)', () => {
    expect(isErrorV2(questionErrorFixture)).toBe(true)
    expect(isErrorV2(invalidRequestErrorFixture)).toBe(true)
    expect('metadata' in invalidRequestErrorFixture).toBe(false)
    expect(isHealthV2(healthFixture)).toBe(true)
  })
})

describe('citation invariants', () => {
  it('rejects a claim citing a chunk id missing from evidence', () => {
    const body = clone(answeredFixture)
    body.claims[0].citation_chunk_ids = ['not-in-evidence']
    expect(isSuccessV2(body)).toBe(false)
  })

  it('rejects empty citation_chunk_ids', () => {
    const body = clone(answeredFixture)
    body.claims[0].citation_chunk_ids = []
    expect(isSuccessV2(body)).toBe(false)
  })

  it('rejects duplicated citation_chunk_ids', () => {
    const body = clone(answeredFixture)
    const id = body.evidence[0].chunk_id
    body.claims[0].citation_chunk_ids = [id, id]
    expect(isSuccessV2(body)).toBe(false)
  })

  it.each([
    ['evidence_comparison', (b: Json) => { b.comparison.differences[0].citation_chunk_ids = ['broken'] }],
    ['evidence_comparison', (b: Json) => { b.comparison.subjects[0].citation_chunk_ids = ['broken'] }],
    ['conflicting_evidence', (b: Json) => { b.conflicts.items[0].positions[0].citation_chunk_ids = ['broken'] }],
    ['research_gap', (b: Json) => { b.gap_analysis.gaps[0].citation_chunk_ids = ['broken'] }],
    ['research_gap', (b: Json) => { b.gap_analysis.hypotheses[0].citation_chunk_ids = ['broken'] }],
  ] as const)('rejects a broken payload citation id (%s)', (workflow, mutate) => {
    const body = clone(answeredFixtureByWorkflow[workflow])
    mutate(body)
    expect(isSuccessV2(body, workflow)).toBe(false)
  })
})

describe('status and payload invariants', () => {
  it('rejects answered without an answer, claims or evidence', () => {
    expect(isSuccessV2({ ...clone(answeredFixture), answer: null })).toBe(false)
    expect(isSuccessV2({ ...clone(answeredFixture), claims: [] })).toBe(false)
    expect(isSuccessV2({ ...clone(answeredFixture), claims: [], evidence: [] })).toBe(false)
  })

  it('rejects no_results with evidence', () => {
    expect(isSuccessV2({ ...clone(noResultsFixture), evidence: clone(answeredFixture).evidence })).toBe(false)
  })

  it('rejects insufficient_evidence with an answer or claims', () => {
    expect(isSuccessV2({ ...clone(insufficientEvidenceFixture), answer: 'guess' })).toBe(false)
    expect(isSuccessV2({ ...clone(insufficientEvidenceFixture), claims: clone(answeredFixture).claims })).toBe(false)
  })

  it('rejects an answered new-workflow response without its payload', () => {
    const body = clone(answeredFixtureByWorkflow.evidence_comparison)
    delete body.comparison
    expect(isSuccessV2(body)).toBe(false)
  })

  it('rejects a payload on a non-answered response', () => {
    const body = { ...clone(insufficientEvidenceComparisonFixture), comparison: { subjects: [], similarities: [], differences: [] } }
    expect(isSuccessV2(body)).toBe(false)
  })

  it('rejects a comparison with a single subject', () => {
    const body = clone(answeredFixtureByWorkflow.evidence_comparison)
    body.comparison.subjects.pop()
    expect(isSuccessV2(body)).toBe(false)
  })

  it('rejects a comparison difference citing only one DOI', () => {
    const body = clone(answeredFixtureByWorkflow.evidence_comparison)
    body.comparison.differences[0].citation_chunk_ids = [body.comparison.differences[0].citation_chunk_ids[0]]
    expect(isSuccessV2(body)).toBe(false)
  })

  it('rejects a conflict item with fewer than two positions', () => {
    const body = clone(answeredFixtureByWorkflow.conflicting_evidence)
    body.conflicts.items[0].positions.pop()
    expect(isSuccessV2(body)).toBe(false)
  })

  it('rejects a non-speculative hypothesis', () => {
    const body = clone(answeredFixtureByWorkflow.research_gap)
    body.gap_analysis.hypotheses[0].is_speculative = false
    expect(isSuccessV2(body)).toBe(false)
  })

  it('rejects a hypothesis referencing an unknown gap', () => {
    const body = clone(answeredFixtureByWorkflow.research_gap)
    body.gap_analysis.hypotheses[0].based_on_gap_ids = ['gap-999']
    expect(isSuccessV2(body)).toBe(false)
  })
})

describe('metadata invariants', () => {
  it('rejects the v1 metadata shape', () => {
    expect(isSuccessV2({ ...clone(answeredFixture), metadata: { is_mock: true, is_test_data: true } })).toBe(false)
  })

  it('rejects an unknown component origin', () => {
    const body = clone(answeredFixture)
    body.metadata.retrieval.configured_origin = 'imaginary'
    expect(isSuccessV2(body)).toBe(false)
  })

  it('rejects answered with a provider that did not execute', () => {
    const body = clone(answeredFixture)
    body.metadata.answer_provider.executed = false
    expect(isSuccessV2(body)).toBe(false)
  })

  it('rejects no_results with a provider that executed', () => {
    const body = clone(noResultsFixture)
    body.metadata.answer_provider.executed = true
    expect(isSuccessV2(body)).toBe(false)
  })
})
