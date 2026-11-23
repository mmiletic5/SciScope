// A bracket or parenthesis group holding only 64-hex ids and separators.
const ID_GROUP = /[[(][\s,;]*(?:[0-9a-fA-F]{64}[\s,;]*)+[\])]/g
// A bare id that is not part of a longer hexadecimal run.
const BARE_ID = /(?<![0-9a-fA-F])[0-9a-fA-F]{64}(?![0-9a-fA-F])/g
const EMPTY_BRACKETS = /[[(]\s*[\])]/g

/**
 * Remove leaked 64-hex chunk ids (with their brackets) from model-written text.
 * Defense in depth: the backend strips them too. Short bracketed numbers such as
 * "[20]" are kept.
 */
export function stripChunkIds(text: string): string {
  return text
    .replace(ID_GROUP, ' ')
    .replace(BARE_ID, ' ')
    .replace(EMPTY_BRACKETS, ' ')
    .replace(/\s*\n\s*/g, ' ')
    .replace(/[ \t\f\v]+/g, ' ')
    .replace(/[ \t]+([.,;:!?])/g, '$1')
    .trim()
}
