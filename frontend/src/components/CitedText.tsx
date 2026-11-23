import { stripChunkIds } from '../lib/stripChunkIds'
import { CitationMarker } from './CitationMarker'

type CitedTextProps = {
  text: string
  citationChunkIds: string[]
  /** chunk_id -> displayed source number; ids without a number are skipped. */
  numberById: ReadonlyMap<string, number>
  onActivate: (chunkId: string) => void
}

/** A statement followed by one citation marker per distinct cited source. */
export function CitedText({ text, citationChunkIds, numberById, onActivate }: CitedTextProps) {
  const chunkIds = [...new Set(citationChunkIds)].filter((chunkId) => numberById.has(chunkId))
  return (
    <p className="cited-text">
      {stripChunkIds(text)}{' '}
      {chunkIds.map((chunkId) => (
        <CitationMarker key={chunkId} number={numberById.get(chunkId)!} onActivate={() => onActivate(chunkId)} />
      ))}
    </p>
  )
}
