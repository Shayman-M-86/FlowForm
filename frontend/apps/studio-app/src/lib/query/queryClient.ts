import { QueryClient } from '@tanstack/react-query'
import { createAsyncStoragePersister } from '@tanstack/query-async-storage-persister'

// ─── Stale time tiers ────────────────────────────────────────────────────────
// STATIC  — profile, role definitions, permissions (rarely change mid-session)
// SLOW    — project/survey lists, member lists (change occasionally)
// ACTIVE  — nodes, versions, invitations, submissions (expect frequent changes)

export const STALE = {
  STATIC: 1000 * 60 * 20,  // 20 min
  SLOW:   1000 * 60 * 5,   // 5 min
  ACTIVE: 1000 * 30,       // 30 sec
} as const

// Default staleTime is SLOW — most list queries fall here unless overridden.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: STALE.SLOW,
      retry: 1,
    },
  },
})

// ─── Persistence ──────────────────────────────────────────────────────────────
// Queries tagged with meta.persist: 'local' are written to localStorage and
// restored on next load. ACTIVE-tier data is intentionally excluded — we never
// want stale canvas or version state restored from a previous session.

const localStorageAdapter = {
  getItem: (key: string) => Promise.resolve(window.localStorage.getItem(key)),
  setItem: (key: string, value: string) => Promise.resolve(window.localStorage.setItem(key, value)),
  removeItem: (key: string) => Promise.resolve(window.localStorage.removeItem(key)),
}

export const localPersister = createAsyncStoragePersister({
  storage: localStorageAdapter,
  key: 'flowform.query-cache',
})

export function shouldPersistQuery(query: { meta?: Record<string, unknown>; state: { status: string } }): boolean {
  return query.meta?.persist === 'local' && query.state.status === 'success'
}
