type CitationMarkerProps = {
  number: number
  onActivate: () => void
}

export function CitationMarker({ number, onActivate }: CitationMarkerProps) {
  return (
    <button
      className="citation-marker"
      type="button"
      aria-label={`Source ${number}`}
      onClick={onActivate}
    >
      {number}
    </button>
  )
}
