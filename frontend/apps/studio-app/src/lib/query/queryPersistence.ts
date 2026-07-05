import { experimental_createQueryPersister } from '@tanstack/query-persist-client-core'
import type { QueryClient, QueryKey, QueryFunction, QueryFunctionContext } from '@tanstack/react-query'
import type { QueryStorage } from './queryPolicy'

const CACHE_BUSTER = 'flowform-query-cache-v1'
const DEFAULT_LOCAL_MAX_AGE = 24 * 60 * 60 * 1000
const DEFAULT_SESSION_MAX_AGE = 20 * 60 * 1000

function createStorageAdapter(storage: Storage) {
  return {
    getItem: (key: string) => storage.getItem(key),
    setItem: (key: string, value: string) => storage.setItem(key, value),
    removeItem: (key: string) => storage.removeItem(key),
    entries: (): Array<[string, string]> => {
      const result: Array<[string, string]> = []
      for (let i = 0; i < storage.length; i++) {
        const key = storage.key(i)
        if (!key) continue
        const value = storage.getItem(key)
        if (value !== null) result.push([key, value])
      }
      return result
    },
  }
}

const localStorageAdapter =
  typeof window === 'undefined' ? undefined : createStorageAdapter(window.localStorage)

const sessionStorageAdapter =
  typeof window === 'undefined' ? undefined : createStorageAdapter(window.sessionStorage)

export const localQueryPersister = experimental_createQueryPersister({
  storage: localStorageAdapter,
  prefix: 'flowform.query.local',
  buster: CACHE_BUSTER,
  maxAge: DEFAULT_LOCAL_MAX_AGE,
})

export const sessionQueryPersister = experimental_createQueryPersister({
  storage: sessionStorageAdapter,
  prefix: 'flowform.query.session',
  buster: CACHE_BUSTER,
  maxAge: DEFAULT_SESSION_MAX_AGE,
})

const localQueryPersisters = new Map<number, typeof localQueryPersister>([
  [DEFAULT_LOCAL_MAX_AGE, localQueryPersister],
])

const sessionQueryPersisters = new Map<number, typeof sessionQueryPersister>([
  [DEFAULT_SESSION_MAX_AGE, sessionQueryPersister],
])

function getStoragePersister(storage: Exclude<QueryStorage, 'memory'>, maxAge?: number) {
  if (storage === 'local') {
    const resolvedMaxAge = maxAge ?? DEFAULT_LOCAL_MAX_AGE
    const existing = localQueryPersisters.get(resolvedMaxAge)
    if (existing) return existing

    const persister = experimental_createQueryPersister({
      storage: localStorageAdapter,
      prefix: 'flowform.query.local',
      buster: CACHE_BUSTER,
      maxAge: resolvedMaxAge,
    })
    localQueryPersisters.set(resolvedMaxAge, persister)
    return persister
  }

  const resolvedMaxAge = maxAge ?? DEFAULT_SESSION_MAX_AGE
  const existing = sessionQueryPersisters.get(resolvedMaxAge)
  if (existing) return existing

  const persister = experimental_createQueryPersister({
    storage: sessionStorageAdapter,
    prefix: 'flowform.query.session',
    buster: CACHE_BUSTER,
    maxAge: resolvedMaxAge,
  })
  sessionQueryPersisters.set(resolvedMaxAge, persister)
  return persister
}

// Returns the correct persisterFn typed to match TData/TKey so that
// useQuery's TData inference is preserved. Call this inside usePolicyQuery
// only — not directly in useQuery spreads at hook call sites.
export function getPersisterFn<TData, TKey extends QueryKey>(
  storage: QueryStorage,
  maxAge?: number,
): ((fn: QueryFunction<TData, TKey>, ctx: QueryFunctionContext<TKey>, query: unknown) => Promise<TData>) | undefined {
  switch (storage) {
    case 'local':
      return getStoragePersister('local', maxAge).persisterFn as (fn: QueryFunction<TData, TKey>, ctx: QueryFunctionContext<TKey>, query: unknown) => Promise<TData>
    case 'session':
      return getStoragePersister('session', maxAge).persisterFn as (fn: QueryFunction<TData, TKey>, ctx: QueryFunctionContext<TKey>, query: unknown) => Promise<TData>
    case 'memory':
      return undefined
  }
}

export async function clearFlowFormQueryCache(queryClient: QueryClient): Promise<void> {
  queryClient.clear()
  await Promise.all([
    localQueryPersister.removeQueries({}),
    sessionQueryPersister.removeQueries({}),
  ])
  window.localStorage.removeItem('flowform.query-cache')
  window.localStorage.removeItem('flowform.query-cooldowns')
  window.localStorage.removeItem('flowform.perm-cooldowns')
  window.localStorage.removeItem('flowform.query-cache-owner')
}

export async function persistUpdatedQuery(
  storage: Exclude<QueryStorage, 'memory'>,
  queryKey: QueryKey,
  queryClient: QueryClient,
): Promise<void> {
  const persister = getStoragePersister(storage)
  await persister.persistQueryByKey(queryKey, queryClient)
}

export async function restorePersistedQueries(): Promise<void> {
  // Individual query persisters restore with their resolved policy maxAge.
  // Startup only prunes the default stores so bootstrap does not hydrate data
  // with broader storage-level rules than the query family selected.
  await Promise.all([
    localQueryPersister.persisterGc(),
    sessionQueryPersister.persisterGc(),
  ])
}
