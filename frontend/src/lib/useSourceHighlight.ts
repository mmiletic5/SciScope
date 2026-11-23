import { useState } from 'react'

/** Highlights and scrolls to a source card when its citation marker is activated. */
export function useSourceHighlight(idPrefix: string) {
  const [highlightedChunkId, setHighlightedChunkId] = useState<string | null>(null)

  function activateSource(chunkId: string) {
    setHighlightedChunkId(chunkId)
    const behavior = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'
    document.getElementById(`${idPrefix}-source-${encodeURIComponent(chunkId)}`)
      ?.scrollIntoView?.({ behavior, block: 'center' })
  }

  return { highlightedChunkId, activateSource }
}
