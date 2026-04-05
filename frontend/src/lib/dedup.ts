export function dedup<T extends { created_at: string }>(
  items: T[],
  keyFn: (item: T) => string,
): T[] {
  const map = new Map<string, T>()
  for (const item of items) {
    const key = keyFn(item)
    const existing = map.get(key)
    if (!existing || item.created_at > existing.created_at) {
      map.set(key, item)
    }
  }
  return [...map.values()]
}
