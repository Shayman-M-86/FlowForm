export type QueryStorage = 'memory' | 'session' | 'local'

export type QueryPolicy = {
  // Where successful query results may be restored from.
  // memory: TanStack Query cache only; session: sessionStorage; local: localStorage.
  storage: QueryStorage

  // How long TanStack Query treats data as fresh before automatic refreshes can run.
  staleTime: number
  // How old persisted data may be before the persister discards it.
  maxAge?: number
  // How long unused in-memory query data stays in TanStack Query's cache.
  gcTime?: number

  // Minimum time between automatic HTTP refreshes for the same query key.
  cooldownMs?: number
  // Background refetch interval once the query has data.
  pollMs?: number

  // Whether stale data refetches when the browser tab regains focus.
  refetchOnWindowFocus?: boolean
  // Whether stale data refetches after network reconnect.
  refetchOnReconnect?: boolean
}

const MINUTE = 60_000
const HOUR = 60 * MINUTE

// Shared storage defaults keep policy rows short while preserving per-family
// overrides for maxAge/gcTime when a query needs different persistence rules.
export const STORAGE_DEFAULTS = {
  // Memory-only queries are intentionally not persisted.
  memory: {},

  // Session queries survive refresh but not browser restart.
  session: {
    maxAge: 20 * MINUTE,
  },

  // Local queries survive browser restart and are scoped by cache owner.
  local: {
    maxAge: 24 * HOUR,
  },
} satisfies Record<QueryStorage, Partial<QueryPolicy>>

// Central registry for every query family. Hooks should reference one of these
// rows by name and keep IDs/slugs in the query key, not in the policy table.
export const QUERY_POLICIES = {
  // Current user profile changes rarely and is useful immediately after reload.
  profile: {
    storage: 'local',
    staleTime: 20 * MINUTE,
  },

  // Project list changes occasionally and accepting invitations invalidates it.
  projects: {
    storage: 'local',
    staleTime: 5 * MINUTE,
    cooldownMs: 15_000,
  },

  // Permissions are session-scoped because role changes should not linger after
  // closing the browser, but refreshes should not create noisy permission fetches.
  projectPermissions: {
    storage: 'session',
    staleTime: 20 * MINUTE,
  },

  surveyPermissions: {
    storage: 'session',
    staleTime: 20 * MINUTE,
  },

  // Sidebar notification data should refresh periodically and on focus, while
  // still avoiding request bursts across rapid mounts.
  myInvitations: {
    storage: 'session',
    staleTime: 5 * MINUTE,
    cooldownMs: 15_000,
    pollMs: 5 * MINUTE,
    refetchOnWindowFocus: true,
  },

  // Survey metadata and management lists are session-persisted so navigation
  // and refreshes feel warm without carrying admin state across browser restarts.
  surveys: {
    storage: 'session',
    staleTime: 5 * MINUTE,
    cooldownMs: 15_000,
  },

  survey: {
    storage: 'session',
    staleTime: 5 * MINUTE,
    cooldownMs: 15_000,
  },

  projectMembers: {
    storage: 'session',
    staleTime: 5 * MINUTE,
    cooldownMs: 15_000,
  },

  projectRoles: {
    storage: 'session',
    staleTime: 5 * MINUTE,
    cooldownMs: 15_000,
  },

  surveyMembers: {
    storage: 'session',
    staleTime: 5 * MINUTE,
    cooldownMs: 15_000,
  },

  surveyRoles: {
    storage: 'session',
    staleTime: 5 * MINUTE,
    cooldownMs: 15_000,
  },

  // Invitation/link/version/node data changes quickly or belongs to builder
  // workflows, so it stays memory-only and fetches fresh after page reload.
  projectInvitations: {
    storage: 'memory',
    staleTime: 30_000,
  },

  publicLinks: {
    storage: 'memory',
    staleTime: 30_000,
  },

  surveyVersions: {
    storage: 'memory',
    staleTime: 30_000,
  },

  surveyNodes: {
    storage: 'memory',
    staleTime: 30_000,
  },

  subjects: {
    storage: 'session',
    staleTime: 2 * MINUTE,
    cooldownMs: 15_000,
  },

  participants: {
    storage: 'session',
    staleTime: 2 * MINUTE,
    cooldownMs: 15_000,
  },

  results: {
    storage: 'memory',
    staleTime: 30_000,
  },

  resultDetail: {
    storage: 'session',
    staleTime: 20 * MINUTE,
  },
} as const satisfies Record<string, QueryPolicy>

export function resolveQueryPolicy(policy: QueryPolicy): QueryPolicy {
  return {
    ...STORAGE_DEFAULTS[policy.storage],
    ...policy,
  }
}
