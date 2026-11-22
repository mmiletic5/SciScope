import type {
  AnsweredResponse,
  InsufficientEvidenceResponse,
  NoResultsResponse,
  QuestionErrorResponse,
} from './types'

const mockMetadata = {
  is_mock: true,
  is_test_data: true,
} as const

const corpus = {
  corpus_version: 'synthetic-fixture-v1',
  source_contract_version: 'synthetic-contract-v1',
  delivery_digest: 'synthetic-digest-not-a-real-corpus',
} as const

export const answeredFixture = {
  api_version: 'v1',
  request_id: 'test-answered-001',
  workflow: 'research_question',
  status: 'answered',
  answer: 'Synthetic demonstration answer for offline UI tests.',
  claims: [
    {
      claim_id: 'synthetic-claim-1',
      text: 'Synthetic demonstration claim; this is not a scientific finding.',
      citation_chunk_ids: ['synthetic-chunk-1'],
    },
  ],
  evidence: [
    {
      chunk_id: 'synthetic-chunk-1',
      doi: '10.0000/test-only',
      source_locator: 'Synthetic locator for offline UI tests.',
      passage: 'Synthetic passage for offline UI tests; no source is represented.',
      paper_title: 'Synthetic test source (not a publication)',
    },
  ],
  corpus,
  metadata: mockMetadata,
} satisfies AnsweredResponse

export const noResultsFixture = {
  api_version: 'v1',
  request_id: 'test-no-results-001',
  workflow: 'research_question',
  status: 'no_results',
  answer: null,
  claims: [],
  evidence: [],
  corpus,
  metadata: mockMetadata,
} satisfies NoResultsResponse

export const insufficientEvidenceFixture = {
  api_version: 'v1',
  request_id: 'test-insufficient-001',
  workflow: 'research_question',
  status: 'insufficient_evidence',
  answer: null,
  claims: [],
  evidence: [],
  corpus,
  metadata: mockMetadata,
} satisfies InsufficientEvidenceResponse

export const questionErrorFixture = {
  api_version: 'v1',
  request_id: 'test-error-001',
  error: {
    code: 'provider_unavailable',
    message: 'Synthetic provider outage for offline UI tests.',
    retryable: true,
  },
  metadata: mockMetadata,
} satisfies QuestionErrorResponse
