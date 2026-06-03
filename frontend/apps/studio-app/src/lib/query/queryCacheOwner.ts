import type { QueryClient } from '@tanstack/react-query'
import { clearFlowFormQueryCache } from './queryPersistence'

const CACHE_OWNER_KEY = 'flowform.query-cache-owner'

export async function ensureCacheOwner(
  queryClient: QueryClient,
  authSubject: string,
): Promise<void> {
  const currentOwner = window.localStorage.getItem(CACHE_OWNER_KEY)
  if (currentOwner && currentOwner !== authSubject) {
    await clearFlowFormQueryCache(queryClient)
  }
  window.localStorage.setItem(CACHE_OWNER_KEY, authSubject)
}

export function clearCacheOwner(): void {
  window.localStorage.removeItem(CACHE_OWNER_KEY)
}
