export type Workflow = 'research_question'

export type QuestionRequest = {
  workflow: Workflow
  /** Trimmed by the client and limited to 1–2,000 characters. */
  question: string
  /** Must match /^[A-Za-z0-9._:-]{1,128}$/. */
  request_id: string
}

export type MockMetadata = {
  is_mock: boolean
  is_test_data: boolean
}

export type Claim = {
  claim_id: string
  text: string
  citation_chunk_ids: string[]
}

export type Evidence = {
  chunk_id: string
  doi: string
  source_locator: string
  passage: string
  paper_title: string
}

export type CorpusProvenance = {
  corpus_version: string
  source_contract_version: string
  delivery_digest: string
}

type QuestionSuccessBase = {
  api_version: 'v1'
  request_id: string
  workflow: Workflow
  corpus: CorpusProvenance
  metadata: MockMetadata
}

export type AnsweredResponse = QuestionSuccessBase & {
  status: 'answered'
  answer: string
  claims: Claim[]
  evidence: Evidence[]
}

export type NoResultsResponse = QuestionSuccessBase & {
  status: 'no_results'
  answer: null
  claims: []
  evidence: []
}

export type InsufficientEvidenceResponse = QuestionSuccessBase & {
  status: 'insufficient_evidence'
  answer: null
  claims: []
  evidence: Evidence[]
}

export type QuestionSuccess =
  | AnsweredResponse
  | NoResultsResponse
  | InsufficientEvidenceResponse

export type QuestionErrorCode =
  | 'invalid_request'
  | 'retrieval_unavailable'
  | 'provider_unavailable'
  | 'dependency_timeout'
  | 'response_contract_failure'
  | 'internal_error'

export type QuestionErrorResponse = {
  api_version: 'v1'
  request_id: string
  error: {
    code: QuestionErrorCode
    message: string
    retryable: boolean
  }
  metadata: MockMetadata
}

