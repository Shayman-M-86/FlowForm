const CACHE_PREFIX = 'ff.query.'

type CacheEntry<T> = {
  data: T
  cachedAt: number
}

function storageKey(key: readonly unknown[]): string {
  return `${CACHE_PREFIX}${JSON.stringify(key)}`
}

export function loadCachedQuery<T>(key: readonly unknown[], ttlMs: number): T | undefined {
  try {
    const raw = sessionStorage.getItem(storageKey(key))
    if (!raw) return undefined
    const entry = JSON.parse(raw) as CacheEntry<T>
    if (Date.now() - entry.cachedAt > ttlMs) return undefined
    return entry.data
  } catch {
    return undefined
  }
}

export function loadCachedQueryUpdatedAt(key: readonly unknown[]): number | undefined {
  try {
    const raw = sessionStorage.getItem(storageKey(key))
    if (!raw) return undefined
    const entry = JSON.parse(raw) as CacheEntry<unknown>
    return entry.cachedAt
  } catch {
    return undefined
  }
}

export function saveCachedQuery<T>(key: readonly unknown[], data: T) {
  try {
    sessionStorage.setItem(storageKey(key), JSON.stringify({ data, cachedAt: Date.now() }))
  } catch {
    // Storage can be unavailable or full. The network cache still works.
  }
}

export function clearQueryCache() {
  try {
    const toRemove: string[] = []
    for (let i = 0; i < sessionStorage.length; i++) {
      const k = sessionStorage.key(i)
      if (k?.startsWith(CACHE_PREFIX)) toRemove.push(k)
    }
    toRemove.forEach((k) => sessionStorage.removeItem(k))
  } catch {
    // Storage can be unavailable — safe to ignore.
  }
}
