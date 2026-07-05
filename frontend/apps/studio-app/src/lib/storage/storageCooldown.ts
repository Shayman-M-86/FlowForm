export interface StorageCooldownOptions {
  storageKey: string
  cooldownMs: number
}

export function createStorageCooldown({ storageKey, cooldownMs }: StorageCooldownOptions) {
  function getAll(): Record<string, number> {
    try {
      return JSON.parse(localStorage.getItem(storageKey) ?? '{}') as Record<string, number>
    } catch {
      return {}
    }
  }

  function set(key: string, ts: number): void {
    try {
      const all = getAll()
      all[key] = ts
      localStorage.setItem(storageKey, JSON.stringify(all))
    } catch {
      // Storage cooldowns are best-effort when localStorage is unavailable.
    }
  }

  function isOnCooldown(key: string): boolean {
    return Date.now() - (getAll()[key] ?? 0) < cooldownMs
  }

  function attempt(key: string, fn: () => void): void {
    if (isOnCooldown(key)) return
    set(key, Date.now())
    fn()
  }

  // Stamps the cooldown and returns true if the key was not on cooldown.
  // Use this to gate a query's `enabled` flag: stamp() returns true once,
  // then false for subsequent calls within the cooldown window.
  function stamp(key: string): boolean {
    if (isOnCooldown(key)) return false
    set(key, Date.now())
    return true
  }

  return { isOnCooldown, attempt, stamp }
}
