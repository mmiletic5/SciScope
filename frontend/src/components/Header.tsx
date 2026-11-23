import type { MockMetadata } from '../api/types'

type HeaderProps = {
  metadata?: MockMetadata | null
}

export function Header({ metadata }: HeaderProps) {
  const showMockBadge = metadata === undefined
    || metadata === null
    || metadata.is_mock
    || metadata.is_test_data

  return (
    <header className="app-header">
      <a className="brand" href="/" aria-label="SciScope home">
        <svg className="brand__mark" viewBox="0 0 32 32" aria-hidden="true" focusable="false">
          <path d="M16 2.5 27.7 9.25v13.5L16 29.5 4.3 22.75V9.25L16 2.5Z" />
          <path d="M10 12h12M10 16h8M10 20h12" />
        </svg>
        <span>SciScope</span>
      </a>
      {showMockBadge && <span className="mock-badge">MOCK · test data</span>}
    </header>
  )
}
