const REQUEST_ID_PATTERN = /^[A-Za-z0-9._:-]{1,128}$/

export function isValidRequestId(value: string): boolean {
  return REQUEST_ID_PATTERN.test(value)
}

export function createRequestId(): string {
  const randomPart = globalThis.crypto?.randomUUID?.() ?? Math.random().toString(36).slice(2)
  const value = `ui-${Date.now()}-${randomPart}`
  return value.slice(0, 128)
}
