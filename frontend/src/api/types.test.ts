import { describe, expect, it } from 'vitest'
import {
  answeredFixture,
  insufficientEvidenceFixture,
  noResultsFixture,
  questionErrorFixture,
} from './fixtures'

describe('offline question-service fixtures', () => {
  it('represents an answered response with response-local evidence and provenance', () => {
    expect(answeredFixture).toMatchObject({
      api_version: 'v1',
      workflow: 'research_question',
      status: 'answered',
      claims: [{ claim_id: expect.any(String), citation_chunk_ids: [expect.any(String)] }],
      evidence: [{
        chunk_id: expect.any(String),
        doi: expect.any(String),
        source_locator: expect.any(String),
        passage: expect.any(String),
        paper_title: expect.any(String),
      }],
      corpus: {
        corpus_version: expect.any(String),
        source_contract_version: expect.any(String),
        delivery_digest: expect.any(String),
      },
      metadata: { is_mock: true, is_test_data: true },
    })
  })

  it('provides both empty and insufficient-evidence success states', () => {
    expect(noResultsFixture).toMatchObject({ status: 'no_results', answer: null, claims: [], evidence: [] })
    expect(insufficientEvidenceFixture).toMatchObject({
      status: 'insufficient_evidence',
      answer: null,
      claims: [],
      metadata: { is_mock: true, is_test_data: true },
    })
  })

  it('provides a typed sanitized error envelope', () => {
    expect(questionErrorFixture).toMatchObject({
      api_version: 'v1',
      error: {
        code: 'provider_unavailable',
        message: expect.any(String),
        retryable: true,
      },
      metadata: { is_mock: true, is_test_data: true },
    })
  })
})
