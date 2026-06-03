import { useRef } from 'react'

const STORAGE_KEY = 'flowform.query-cooldowns'

function getStamps(): Record<string, number> {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}') as Record<string, number>
  } catch {
    return {}
  }
}

function writeStamp(key: string): void {
  try {
    const all = getStamps()
    all[key] = Date.now()
    localStorage.setItem(STORAGE_KEY, JSON.stringify(all))
  } catch {}
}

function checkAndStamp(key: string, cooldownMs: number): boolean {
  const last = getStamps()[key] ?? 0
  if (Date.now() - last < cooldownMs) return false
  writeStamp(key)
  return true
}

/**
 * Returns an `enabled` boolean for a useQuery call gated by a per-key cooldown.
 *
 * Stamps once on mount. Returns true if the cooldown has expired (or never fired),
 * false if we're still within the cooldown window. The stamp persists across
 * page refreshes via localStorage, so the cooldown survives a reload.
 *
 * Usage:
 *   const enabled = useCooldownEnabled('my-invitations', 15_000)
 *   useQuery({ ..., enabled, refetchOnWindowFocus: true, staleTime: 60_000 })
 */
export function useCooldownEnabled(key: string, cooldownMs: number): boolean {
  const allowed = useRef<boolean | null>(null)
  if (allowed.current === null) {
    allowed.current = checkAndStamp(key, cooldownMs)
  }
  return allowed.current
}
