import { useEffect, useRef, useState } from 'react'

export const HIGHLIGHT_MS = 2500

/** Scrolls to a source card when its citation marker is activated and highlights it briefly. */
export function useSourceHighlight(idPrefix: string) {
  const [highlightedChunkId, setHighlightedChunkId] = useState<string | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  useEffect(() => () => clearTimeout(timer.current), [])

  function activateSource(chunkId: string) {
    setHighlightedChunkId(chunkId)
    clearTimeout(timer.current)
    timer.current = setTimeout(() => setHighlightedChunkId(null), HIGHLIGHT_MS)
    const behavior = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'
    document.getElementById(`${idPrefix}-source-${encodeURIComponent(chunkId)}`)
      ?.scrollIntoView?.({ behavior, block: 'center' })
  }

  return { highlightedChunkId, activateSource }
}
