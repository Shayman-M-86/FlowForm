# Generated API Layer

## Where it comes from

The backend is a Flask app that uses **Pydantic** models for request and
response validation. Flask-OpenAPI3 reads those models and emits a fully
typed `backend/openapi.yaml` spec at startup. Everything in
`src/api/generated/` is derived from that single file — no types are written
by hand.

The generator is `frontend/scripts/generate-types.mjs`. Run it from
`frontend/` whenever the backend spec changes:

```bash
node scripts/generate-types.mjs
```

Never edit any file under `src/api/generated/` by hand — it will be
overwritten on the next run.

---

## What gets generated

```
src/api/generated/
  schema.ts                          ← openapi-typescript output (path types for openapi-fetch)
  object-schema/
    requests.gen.ts                  ← interfaces + Constraints for *Request / *In schemas
    requests.zod.gen.ts              ← Zod schemas for request types
    responses.gen.ts                 ← interfaces + Constraints for *Responses schemas
    responses.zod.gen.ts             ← Zod schemas for response types
    subtypes.gen.ts                  ← interfaces + Constraints for everything else
    subtypes.zod.gen.ts              ← Zod schemas for subtypes
  endpoints/
    <tag>/
      types.gen.ts                   ← re-exports the types used by this tag
      requests.gen.ts                ← typed async functions (one per operation)
      hooks.gen.ts                   ← React Query hooks (one per operation)
```

Tags map to backend route groups (e.g. `surveys`, `me`, `members`).

### `requests.gen.ts`

Pure async functions that call `openapi-fetch`. They take `apiClient` as the
first argument, throw the raw error on failure, and return typed data.

```ts
export async function listSurveys(
  apiClient: OpenApiFetchClient,
  project_id: number,
): Promise<SurveyResponses[]>
```

### `hooks.gen.ts`

Minimal React Query wrappers over the request functions. They call
`useOpenApiClient()` internally, define a `*Keys` cache key object, and
invalidate the list key on mutation success. No staleTime, no localStorage
cache, no optimistic updates, no cross-key invalidation.

```ts
export const surveysKeys = {
  all: () => ["surveys"] as const,
  list: (project_id: number) => [...surveysKeys.all(), "list", project_id] as const,
  detail: (project_id: number) => [...surveysKeys.all(), "detail", project_id] as const,
}

export function useListSurveys(project_id: number) { ... }
export function useCreateSurvey(project_id: number) { ... }
```

---

## Three-tier usage pattern

### Tier 1 — use the generated hook directly

For endpoints where the defaults are fine (no caching policy, no design
preview, no optimistic updates), import the generated hook straight into the
component.

```ts
import { useListSurveys } from '@/api/generated/endpoints/surveys/hooks.gen'
```

### Tier 2 — thin hand-crafted hook over the generated request function

When you need custom caching, `staleTime`, `initialData`, `setQueryData`,
cross-key invalidation, or design-preview mock data, write a hook in
`src/api/<domain>/hooks.ts` that imports from `requests.gen.ts` and adds
only what the generated version cannot provide. Do not duplicate the request
function — call the generated one.

```ts
// src/api/project/surveys/hooks.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useOpenApiClient } from '../../openapi'
import {
  getSurveys,
  updateSurvey,
} from '../../generated/endpoints/surveys/requests.gen'
import type { SurveyResponses, UpdateSurveyRequest } from '../../generated/endpoints/surveys/types.gen'

const FIVE_MINUTES = 5 * 60 * 1000

export const surveyKeys = {
  all: () => ['surveys'] as const,
  list: (projectId: number) => [...surveyKeys.all(), 'list', projectId] as const,
  detail: (projectId: number, surveyId: number) =>
    [...surveyKeys.all(), 'detail', projectId, surveyId] as const,
}

export function useSurveys(projectId: number) {
  const apiClient = useOpenApiClient()
  return useQuery({
    queryKey: surveyKeys.list(projectId),
    queryFn: () => getSurveys(apiClient, projectId),
    enabled: projectId > 0,
    staleTime: FIVE_MINUTES,
  })
}

export function useUpdateSurvey(projectId: number, surveyId: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: UpdateSurveyRequest) => updateSurvey(apiClient, projectId, surveyId, body),
    onSuccess: (updated) => {
      // optimistic cache write + cross-key invalidation — not in the generated hook
      queryClient.setQueryData(surveyKeys.detail(projectId, surveyId), updated)
      void queryClient.invalidateQueries({ queryKey: surveyKeys.list(projectId) })
    },
  })
}
```

When a hand-crafted hook exists for a resource, components should import from
it rather than the generated hook — one consistent import location per domain.

### Tier 3 — types only

For Zod validation in forms or anywhere you just need the type, import
directly from `object-schema/`:

```ts
import type { UpdateSurveyRequest } from '@/api/generated/object-schema/requests.gen'
import { zUpdateSurveyRequest } from '@/api/generated/object-schema/requests.zod.gen'
```

---

## Decision guide

| Situation | What to do |
|---|---|
| New endpoint, no special caching needed | Use generated hook directly |
| Need `staleTime`, `initialData`, or localStorage cache | Write hand-crafted hook, call `requests.gen.ts` |
| Need `setQueryData` or cross-key invalidation on mutation | Write hand-crafted hook |
| Need design-preview mock data | Write hand-crafted hook |
| Need a Zod schema for a form | Import from `object-schema/*.zod.gen.ts` |
| Backend adds a new field to a response | Re-run the generator — type updates automatically |
| Backend adds a new endpoint | Re-run the generator — new functions and hooks appear |

---

## What the generated hooks do NOT do

- No `staleTime` — data is considered stale immediately
- No `initialData` from localStorage (`queryStorage.ts`)
- No design-preview mode (`designPreview.ts` / `mockData.ts`)
- No optimistic `setQueryData` on mutation success
- No cross-tag cache invalidation (e.g. invalidating `projectKeys` when a survey changes)
- Mutation `onSuccess` only invalidates the tag's own list key
- Error is the raw `openapi-fetch` error object, not `ApiRequestError`

If any of these matter for a given endpoint, write a hand-crafted hook.
