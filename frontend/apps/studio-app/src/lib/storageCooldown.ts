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
    } catch {}
  }

  function isOnCooldown(key: string): boolean {
    return Date.now() - (getAll()[key] ?? 0) < cooldownMs
  }

  function attempt(key: string, fn: () => void): void {
    if (isOnCooldown(key)) return
    set(key, Date.now())
    fn()
  }

  return { isOnCooldown, attempt }
}
