import type { QueryKey } from '@tanstack/react-query'
import { hashKey } from '@tanstack/react-query'

const STORAGE_KEY = 'flowform.query-cooldowns'

function readStore(): Record<string, number> {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}') as Record<string, number>
  } catch {
    return {}
  }
}

function writeStore(store: Record<string, number>): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(store))
  } catch {}
}

// Returns the ms remaining in the cooldown window (0 if none).
export function getCooldownRemaining(queryKey: QueryKey, cooldownMs: number): number {
  const hash = hashKey(queryKey)
  const last = readStore()[hash] ?? 0
  const remaining = cooldownMs - (Date.now() - last)
  return remaining > 0 ? remaining : 0
}

export function isCoolingDown(queryKey: QueryKey, cooldownMs: number): boolean {
  return getCooldownRemaining(queryKey, cooldownMs) > 0
}

// Call this when a real HTTP request is about to start.
export function recordFetchStarted(queryKey: QueryKey): void {
  const hash = hashKey(queryKey)
  const store = readStore()
  store[hash] = Date.now()
  writeStore(store)
}

export function clearQueryCooldowns(): void {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {}
}
