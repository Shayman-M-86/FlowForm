import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import type { QueryKey, QueryFunction, UseQueryResult, UseQueryOptions } from '@tanstack/react-query'
import type { QueryPolicy } from './queryPolicy'
import { resolveQueryPolicy } from './queryPolicy'
import { getPersisterFn } from './queryPersistence'
import { isCoolingDown, getCooldownRemaining, recordFetchStarted } from './queryCooldown'

type PolicyQueryOptions<TData, TKey extends QueryKey> = {
  queryKey: TKey
  queryFn: QueryFunction<TData, TKey>
  policy: QueryPolicy
  enabled?: boolean
  select?: (data: TData) => TData
}

// Derive the refetch flags that TanStack Query exposes on a per-query basis.
// When a cooldown is active, suppress automatic triggers but do not disable
// the query itself so that persisted data can still be restored.
function resolveRefetchFlag(
  policyFlag: boolean | undefined,
  coolingDown: boolean,
): boolean {
  if (!policyFlag) return false
  return !coolingDown
}

export function usePolicyQuery<TData, TKey extends QueryKey>(
  options: PolicyQueryOptions<TData, TKey>,
): UseQueryResult<TData> {
  const { queryKey, queryFn, enabled = true } = options
  const policy = resolveQueryPolicy(options.policy)
  const queryClient = useQueryClient()

  const coolingDown = policy.cooldownMs != null
    ? isCoolingDown(queryKey, policy.cooldownMs)
    : false

  const remaining = policy.cooldownMs != null && coolingDown
    ? getCooldownRemaining(queryKey, policy.cooldownMs)
    : 0

  // Wrap the real queryFn to stamp the cooldown when a network fetch starts.
  const trackedQueryFn: QueryFunction<TData, TKey> = (ctx) => {
    if (policy.cooldownMs != null) {
      recordFetchStarted(queryKey)
    }
    return queryFn(ctx)
  }

  // When a suppressed stale query becomes eligible after the cooldown window,
  // trigger a refetch. Only schedule a timer when data is actually stale and
  // the cooldown is the only thing stopping an automatic refresh.
  useEffect(() => {
    if (remaining <= 0) return
    // Only schedule if the query has cached data that is stale.
    const queryState = queryClient.getQueryState<TData>(queryKey)
    const hasStaleData =
      queryState?.data !== undefined &&
      // eslint-disable-next-line react-hooks/purity
      queryState.dataUpdatedAt + policy.staleTime < Date.now()

    if (!hasStaleData) return

    const timerId = setTimeout(() => {
      void queryClient.invalidateQueries({ queryKey, exact: true })
    }, remaining)

    return () => clearTimeout(timerId)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [remaining, queryClient])

  const persister = getPersisterFn<TData, TKey>(policy.storage, policy.maxAge)

  const queryOptions: UseQueryOptions<TData, Error, TData, TKey> = {
    queryKey,
    queryFn: trackedQueryFn,
    enabled,
    staleTime: policy.staleTime,
    ...(policy.gcTime != null ? { gcTime: policy.gcTime } : {}),
    ...(options.select != null ? { select: options.select } : {}),
    refetchOnMount: !coolingDown,
    refetchOnWindowFocus: resolveRefetchFlag(policy.refetchOnWindowFocus, coolingDown),
    refetchOnReconnect: resolveRefetchFlag(policy.refetchOnReconnect, coolingDown),
    refetchInterval: policy.pollMs != null
      ? (query) => (!coolingDown && query.state.data !== undefined ? policy.pollMs! : false)
      : false,
    meta: {
      storage: policy.storage,
    },
    ...(persister != null ? { persister } : {}),
  }

  return useQuery(queryOptions)
}
