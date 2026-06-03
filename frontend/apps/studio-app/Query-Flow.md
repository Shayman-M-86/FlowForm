# Query Storage & Data Flow

## Layer diagram

```text
┌─────────────────────────────────────────────────────────┐
│  Component                                              │
│  const { data } = useMyInvitations()                    │
└────────────────────────┬────────────────────────────────┘
                         │ calls
┌────────────────────────▼────────────────────────────────┐
│  Named hook  src/api/hooks/*.ts                         │
│                                                         │
│  Most hooks call useQuery directly with staleTime/meta. │
│  Hooks needing cooldown/polling use a policy object:   │
│                                                         │
│  const POLICY = {                                       │
│    staleTime:   'SLOW',    ← STALE tier or raw ms       │
│    persist:     true,      ← write to localStorage      │
│    pollMs:      300_000,   ← background refetch         │
│    cooldownMs:  15_000,    ← min ms between fetches     │
│    windowFocus: true,      ← refetch on tab focus       │
│  }                                                      │
│                                                         │
│  useCooldownEnabled(key, POLICY.cooldownMs)             │
│    └─ reads/writes flowform.query-cooldowns             │
│       stamps once on mount; blocks within cooldownMs    │
│                                                         │
│  useQuery({ queryKey, queryFn, enabled,                 │
│             ...buildQueryOptions(POLICY) })             │
└──────────┬──────────────────────────┬───────────────────┘
           │                          │
           │ no data / stale          │ on success + persist: true
           ▼                          ▼
┌──────────────────────┐   ┌──────────────────────────────┐
│  TanStack Query      │   │  PersistQueryClientProvider  │
│  (in-memory cache)   │   │  src/app/providers/          │
│                      │   │  QueryPersistProvider.tsx     │
│  Single queryClient  │   │                              │
│  shared app-wide.    │   │  Serialises queries where    │
│  Deduplicates        │   │  meta.persist === 'local'    │
│  in-flight requests  │   │  into one localStorage key:  │
│  by query key.       │   │  flowform.query-cache        │
│  Returns cached data │   │                              │
│  if within staleTime.│   │  On app start: restores      │
│  Refetches stale     │   │  matching successful entries │
│  data in background. │   │  into the in-memory cache    │
└──────────┬───────────┘   │  while provider starts.      │
           │               │  maxAge: STALE.STATIC (20m)  │
           │ fetch needed  └──────────────────────────────┘
           ▼
┌──────────────────────────────────────────────────────────┐
│  API client  src/api/client.ts                           │
│                                                          │
│  openapi-fetch typed against generated schema.ts        │
│                                                          │
│  Middleware chain (in order):                            │
│                                                          │
│  1. authMiddleware                                       │
│     onRequest: fetches JWT from Auth0 (cached/refresh)  │
│     attaches Authorization: Bearer <token>              │
│                                                          │
│  2. permissionMiddleware                                 │
│     onRequest: reads permission cache; if the user is   │
│     provably denied, throws PermissionDeniedError        │
│     locally — request never leaves the browser.         │
│     onResponse 403: invalidates permission cache        │
│     (gated by 60s cooldown via flowform.perm-cooldowns) │
└──────────────────────────┬───────────────────────────────┘
                           │ HTTP
┌──────────────────────────▼───────────────────────────────┐
│  Flask backend                                           │
│                                                          │
│  before_request:                                         │
│    Rate limiter — default 30 req / 5s per IP             │
│    skips OPTIONS + configured ignored paths              │
│    (429 → frontend does not retry)                       │
│                                                          │
│  @auth.require_auth():                                   │
│    Validates JWT against Auth0 JWKS                      │
│    401 if invalid/expired                                │
│                                                          │
│  Route handler (thin):                                   │
│    parse() → Pydantic request validation                 │
│    delegates to service layer                            │
│    model_dump(mode="json") → JSON response              │
│    some content routes also pass by_alias=True           │
│                                                          │
│  Service layer:                                          │
│    Only layer that touches both databases                │
│    Cross-db orchestration lives here                     │
└──────────────────────────────────────────────────────────┘
```

## Storage locations

| Key | Storage | Contents |
| --- | ------- | -------- |
| `flowform.query-cache` | localStorage | Serialised query snapshot (`persist: true` queries only) |
| `flowform.query-cooldowns` | localStorage | Per-key fetch timestamps (mount rate limiting) |
| `flowform.perm-cooldowns` | localStorage | Per-permission-key timestamps (invalidation rate limiting) |

## Query client defaults

`src/lib/query/queryClient.ts` creates the single app-wide `QueryClient`.

| Setting | Value | Effect |
| --- | --- | --- |
| default `staleTime` | `STALE.SLOW` = 5 min | Hooks inherit a 5 minute freshness window unless they override it. |
| `STALE.STATIC` | 20 min | Used for user profile and permission lookups. |
| `STALE.SLOW` | 5 min | Used for most project/survey/member/role list data. |
| `STALE.ACTIVE` | 30 sec | Used for data expected to change frequently. |
| retry | once for most errors | `RATE_LIMIT_EXCEEDED` is never retried. Other errors retry while `failureCount < 1`. |

## Policy → behaviour

| `staleTime` | `persist` | `pollMs` | `cooldownMs` | Behaviour |
| ----------- | --------- | -------- | ------------ | --------- |
| `STATIC` | `true` | — | — | Restored on refresh, fresh for 20 min |
| `SLOW` | `true` | — | — | Restored on refresh, fresh for 5 min |
| `SLOW` | — | — | `15_000` | Possible policy shape, but no current hook uses cooldown without persistence |
| `SLOW` | `true` | `300_000` | `15_000` | `useMyInvitations`: restored on refresh, mount fetch blocked within 15s, polls every 5 min after data exists, refetches on focus |
| `ACTIVE` | — | — | — | Fresh for 30s, never persisted |

`buildQueryOptions()` maps a `QueryPolicy` to TanStack Query options. In the
current codebase, only `useMyInvitations()` uses this helper. Other hooks set
`staleTime`, `enabled`, and `meta` directly.

## Queries with persist: true

| Hook | Query key | Tier |
| ---- | --------- | ---- |
| `useMyProfile` | `['me', 'profile']` | STATIC |
| `useProjects` | `['projects']` | SLOW |
| `useProjectPermissions` | `['permissions', 'project', id]` | STATIC |
| `useSurveyPermissions` | `['permissions', 'project', id, 'survey', id]` | STATIC |
| `useMyInvitations` | `['me', 'invitations']` | SLOW |

Persistence only writes successful queries: `shouldPersistQuery()` requires
`query.meta.persist === 'local'` and `query.state.status === 'success'`.

## Non-persisted query families

These hooks stay in memory only. They can still be fresh or stale according to
their tier, and mutations invalidate the relevant query keys on success.

| Hook | Query key | Tier |
| ---- | --------- | ---- |
| `useSurveys` | `['surveys', 'project', projectId]` | SLOW |
| `useSurvey` | `['surveys', 'project', projectId, 'id', surveyId]` | SLOW |
| `useProjectMembers` | `['members', 'project', projectId]` | SLOW |
| `useProjectRoles` | `['roles', 'project', projectId]` | SLOW |
| `useSurveyRoles` | `['survey-roles', 'project', projectId]` | SLOW |
| `useSurveyMembers` | `['survey-members', 'project', projectId, 'survey', surveyId]` | SLOW |
| `useProjectInvitations` | `['invitations', 'project', projectId]` | ACTIVE |
| `usePublicLinks` | `['links', 'project', projectId, 'survey', surveyId]` | ACTIVE |
| `useSurveyVersions` | `['versions', 'project', projectId, 'survey', surveyId]` | ACTIVE |
| `useSurveyNodes` | `['nodes', 'project', projectId, 'survey', surveyId, 'version', versionNumber]` | ACTIVE |

## Permission middleware flow

`apiClient` installs middleware in this order:

1. `authMiddleware`
   - Reads the token getter registered by `initApiAuth()`.
   - If a getter exists, awaits a token and attaches `Authorization: Bearer <token>`.
   - If no getter exists, leaves the request unchanged.

2. `permissionMiddleware`
   - Matches protected routes against generated `routePermissions`.
   - Reads permission query data from the `QueryClient` only. It never fetches
     permissions from inside middleware.
   - If the cache is cold, lets the request through and relies on the backend.
   - If cached permissions prove denial, throws `PermissionDeniedError` before
     the request leaves the browser and invalidates the relevant permission key.
   - On backend `403`, invalidates project permission cache and, when the route
     has a `survey_id`, survey permission cache too.
   - Permission invalidation is gated by `flowform.perm-cooldowns` with a 60s
     cooldown per serialized permission query key.

## Current storage backend

`PersistQueryClientProvider` serialises all `meta.persist === 'local'` queries
into one localStorage entry: `flowform.query-cache`. That means the current app
has one persistence backend and one max age (`STALE.STATIC`, 20 min) for every
persisted query.

The installed TanStack packages are v5.100.14. In this version,
`experimental_createQueryPersister` from `@tanstack/query-persist-client-core`
does expose fine-grained per-query persistence via a `persister` option on
`useQuery`/query options, and `@tanstack/query-core` includes that option.
FlowForm is not using that experimental API right now.

`persist: 'session'` is intentionally absent from `QueryPolicy`.
Do not add it as a mapped alias for localStorage — that would silently produce
cross-session and cross-tab behaviour the name explicitly promises to prevent.
