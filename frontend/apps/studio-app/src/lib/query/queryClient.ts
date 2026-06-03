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
// Never retry 429s — retrying immediately would double the request burst
// and make rate limiting self-reinforcing.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: STALE.SLOW,
      retry: (failureCount, error) => {
        if ((error as { code?: string })?.code === 'RATE_LIMIT_EXCEEDED') return false
        return failureCount < 1
      },
    },
  },
})

// ─── Query policy ─────────────────────────────────────────────────────────────
// Declare the caching behaviour of a query in one place. Pass to buildQueryOptions
// to get the TanStack Query options object.
//
//   staleTime   — how long data is considered fresh; use a STALE tier by name
//                 ("STATIC" | "SLOW" | "ACTIVE") or a raw ms value for one-offs
//   persist     — write to localStorage and restore on next load
//   pollMs      — background refetch interval (only starts once data exists)
//   cooldownMs  — min ms between fetches across mounts/refreshes (localStorage-backed)
//   windowFocus — refetch when the browser tab regains focus

export type StaleKey = keyof typeof STALE

export interface QueryPolicy {
  staleTime:    StaleKey | number
  persist?:     boolean
  pollMs?:      number
  cooldownMs?:  number
  windowFocus?: boolean
}

type QueryOptions = {
  staleTime:             number
  refetchOnWindowFocus:  boolean
  refetchInterval:       ((query: { state: { data: unknown } }) => number | false) | false
  meta:                  Record<string, unknown>
}

export function buildQueryOptions(policy: QueryPolicy): QueryOptions {
  const staleTime = typeof policy.staleTime === 'string' ? STALE[policy.staleTime] : policy.staleTime
  return {
    staleTime,
    refetchOnWindowFocus: policy.windowFocus ?? false,
    refetchInterval:      policy.pollMs != null
      ? (query) => query.state.data !== undefined ? policy.pollMs! : false
      : false,
    meta: {
      ...(policy.persist     ? { persist: 'local' }        : {}),
      ...(policy.cooldownMs != null ? { cooldownMs: policy.cooldownMs } : {}),
    },
  }
}

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

export function clearQueryCache(): void {
  queryClient.clear()
  window.localStorage.removeItem('flowform.query-cache')
}
