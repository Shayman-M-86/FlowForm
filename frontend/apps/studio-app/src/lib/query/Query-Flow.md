# Query Storage & Data Flow

This folder owns the Studio app's TanStack Query configuration. Query behaviour is centralized in `queryPolicy.ts`; hook files choose a named policy row instead of hand-rolling stale times, persistence, polling, or cooldowns.

## Layer Diagram

```text
Component
  const { data } = useSurveys(projectId)
        |
        v
Named hook  src/api/hooks/*.ts
  - owns query keys for its domain
  - calls apiClient.GET/POST/PATCH/DELETE
  - passes policy: QUERY_POLICIES.<family>
        |
        v
usePolicyQuery()
  - resolves STORAGE_DEFAULTS + selected policy
  - chooses memory/session/local persistence
  - applies staleTime, gcTime, polling, focus/reconnect flags
  - applies automatic-fetch cooldowns
        |
        v
TanStack Query
  - in-memory app cache
  - request dedupe by query key
  - stale/fresh decisions
  - per-query persister restore/write when storage is session/local
        |
        v
apiClient + middleware
  - authMiddleware attaches Auth0 bearer token
  - permissionMiddleware can deny locally from cached permissions
        |
        v
Flask API
```

## Files In This Folder

| File | Responsibility |
| --- | --- |
| `queryClient.ts` | Creates the single app-wide `QueryClient` and default retry/stale behaviour. |
| `queryPolicy.ts` | Defines `QueryStorage`, `QueryPolicy`, `STORAGE_DEFAULTS`, `QUERY_POLICIES`, and `resolveQueryPolicy()`. |
| `usePolicyQuery.ts` | Shared hook wrapper around `useQuery`; applies policy options and selects the correct persister. |
| `queryPersistence.ts` | Creates local/session storage adapters and TanStack per-query persisters. |
| `queryCooldown.ts` | Stores per-query automatic-fetch timestamps in `localStorage`. |
| `queryCacheOwner.ts` | Clears persisted query state when a different Auth0 subject uses the same browser. |

## Policy Registry

`QUERY_POLICIES` is the source of truth for query-family cache behaviour.

| Policy | Storage | Freshness | Extra behaviour |
| --- | --- | --- | --- |
| `profile` | local | 20 min | Restores across browser sessions. |
| `projects` | local | 5 min | 15s automatic-fetch cooldown. |
| `projectPermissions` | session | 20 min | Restores during the current browser session. |
| `surveyPermissions` | session | 20 min | Restores during the current browser session. |
| `myInvitations` | session | 5 min | 15s cooldown, 5 min polling, refetch on focus. |
| `surveys` | session | 5 min | 15s cooldown. |
| `survey` | session | 5 min | 15s cooldown. |
| `projectMembers` | session | 5 min | 15s cooldown. |
| `projectRoles` | session | 5 min | 15s cooldown. |
| `surveyMembers` | session | 5 min | 15s cooldown. |
| `surveyRoles` | session | 5 min | 15s cooldown. |
| `projectInvitations` | memory | 30 sec | No storage persistence. |
| `publicLinks` | memory | 30 sec | No storage persistence. |
| `surveyVersions` | memory | 30 sec | No storage persistence. |
| `surveyNodes` | memory | 30 sec | No storage persistence. |

`STORAGE_DEFAULTS` supplies default persisted max ages:

| Storage | Default `maxAge` |
| --- | --- |
| `memory` | none |
| `session` | 20 min |
| `local` | 24 hours |

Override `maxAge`, `gcTime`, polling, cooldown, focus, or reconnect behaviour in a policy row only when that query family needs different behaviour.

## Hook Usage

Domain hooks pass a named policy and keep dynamic IDs in the query key:

```ts
export function useSurveys(projectId: number) {
  return usePolicyQuery({
    queryKey: surveyKeys.list(projectId),
    enabled: projectId > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/projects/{project_id}/surveys', {
        params: { path: { project_id: projectId } },
      })
      if (error) throw error
      return data
    },
    policy: QUERY_POLICIES.surveys,
  })
}
```

Do not put IDs, slugs, mutation invalidation rules, backend rate limits, or permission middleware logic in `QUERY_POLICIES`.

## Persistence Flow

`queryPersistence.ts` uses `experimental_createQueryPersister` from `@tanstack/query-persist-client-core`.

- `memory` returns no persister; data lives only in TanStack Query's in-memory cache.
- `session` stores individual query snapshots in `sessionStorage` with the `flowform.query.session-` prefix.
- `local` stores individual query snapshots in `localStorage` with the `flowform.query.local-` prefix.
- `getPersisterFn(storage, maxAge)` creates or reuses a persister for the resolved storage/maxAge pair.
- Query restoration happens through the per-query `persister` option when `useQuery` mounts and has no in-memory data.
- App startup runs persister garbage collection so expired or busted entries are removed.

## Storage Locations

| Key or prefix | Storage | Contents |
| --- | --- | --- |
| `flowform.query.local-*` | localStorage | Per-query snapshots for `storage: 'local'`. |
| `flowform.query.session-*` | sessionStorage | Per-query snapshots for `storage: 'session'`. |
| `flowform.query-cooldowns` | localStorage | Per-query automatic-fetch timestamps. |
| `flowform.perm-cooldowns` | localStorage | Permission invalidation timestamps. |
| `flowform.query-cache-owner` | localStorage | Auth0 subject that owns the persisted query cache. |
| `flowform.query-cache` | localStorage | Legacy cache key removed during cache clearing. |

## Cooldown Flow

Cooldowns suppress automatic refresh triggers; they do not disable the query.

1. `usePolicyQuery()` checks `flowform.query-cooldowns` for the serialized query key.
2. If the query is cooling down, automatic mount/focus/reconnect/poll refetches are suppressed.
3. When a real query function starts, `recordFetchStarted(queryKey)` stamps the cooldown.
4. If stale cached data is waiting behind a cooldown, `usePolicyQuery()` schedules an invalidation when the cooldown ends.

Manual mutation invalidation still belongs beside the mutation hook.

## Query Client Defaults

`queryClient.ts` sets a default stale time of 5 minutes. Named policies normally override that value through `usePolicyQuery()`.

Retries are intentionally conservative:

- `RATE_LIMIT_EXCEEDED` is never retried.
- Other errors retry while `failureCount < 1`.

## Permission Middleware Flow

`apiClient` installs middleware in this order:

1. `authMiddleware`
   - Reads the token getter registered by `initApiAuth()`.
   - If a getter exists, awaits a token and attaches `Authorization: Bearer <token>`.
   - If no getter exists, leaves the request unchanged.

2. `permissionMiddleware`
   - Matches protected routes against generated `routePermissions`.
   - Reads permission query data from the `QueryClient` only.
   - If the cache is cold, lets the request through and relies on the backend.
   - If cached permissions prove denial, throws `PermissionDeniedError` before the request leaves the browser.
   - On backend `403`, invalidates project permission cache and, when the route has a `survey_id`, survey permission cache too.
   - Permission invalidation is gated by `flowform.perm-cooldowns` with a 60s cooldown per serialized permission query key.
