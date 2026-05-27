---
paths: frontend/apps/studio-app/src/api/**/*.{ts,tsx}
---

# Frontend API module conventions

Every resource group lives under `src/api/<domain>/` and contains exactly
three files. Never put raw fetch calls in components or hooks files.

## File structure

```
src/api/
  generated/
    schema.ts            ← auto-generated, never edit by hand
  me/
    types.ts
    requests.ts
    hooks.ts
  project/
    surveys/
      types.ts
      requests.ts
      hooks.ts
    members/
      types.ts
      requests.ts
      hooks.ts
    ...
```

### `types.ts`
Re-exports types from the generated schema. Nothing else.

```ts
export type { SurveyOut, CreateSurveyRequest, UpdateSurveyRequest } from '../../generated/schema'
```

### `requests.ts`
Pure async functions. Takes `apiClient: OpenApiFetchClient` as the first
argument. Returns typed data or throws the error object. No React, no hooks,
no state.

```ts
import type { OpenApiFetchClient } from '../../openapi'
import type { SurveyOut, CreateSurveyRequest } from './types'

export async function getSurveys(
  apiClient: OpenApiFetchClient,
  project_id: number,
): Promise<SurveyOut[]> {
  const { data, error } = await apiClient.GET('/api/v1/projects/{project_id}/surveys', {
    params: { path: { project_id } },
  })
  if (error) throw error
  return data
}
```

### `hooks.ts`
React Query wrappers. Calls `useOpenApiClient()` internally — callers never
pass an API client. Defines a `*Keys` object for cache invalidation.

```ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useOpenApiClient } from '../../openapi'
import { getSurveys, createSurvey } from './requests'
import type { CreateSurveyRequest, SurveyOut } from './types'

export const surveyKeys = {
  all: () => ['surveys'] as const,
  list: (projectId: number) => [...surveyKeys.all(), 'list', projectId] as const,
}

export function useSurveys(projectId: number) {
  const apiClient = useOpenApiClient()
  return useQuery({
    queryKey: surveyKeys.list(projectId),
    queryFn: () => getSurveys(apiClient, projectId),
  })
}

export function useCreateSurvey(projectId: number) {
  const apiClient = useOpenApiClient()
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateSurveyRequest) => createSurvey(apiClient, projectId, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: surveyKeys.list(projectId) })
    },
  })
}
```

## Step-by-step: adding a new endpoint

1. **Sync the spec** — run this whenever the backend changes:
   ```bash
   bash scripts/shared_script/sync-openapi.sh
   ```
   This regenerates `backend/openapi.yaml` from Python sources, then writes
   `src/api/generated/schema.ts`. Never edit `schema.ts` by hand.

2. **Find the new types** in `schema.ts` — search for the operation name or
   the response/request schema name to confirm the exact field names and
   optionality before writing any code.

3. **Re-export types** in the relevant `types.ts`:
   ```ts
   export type { NewThingOut, CreateNewThingRequest } from '../../generated/schema'
   ```

4. **Add a function** in `requests.ts` using the exact path string from
   `schema.ts` (copy it — do not paraphrase):
   ```ts
   export async function createNewThing(
     apiClient: OpenApiFetchClient,
     project_id: number,
     body: CreateNewThingRequest,
   ): Promise<NewThingOut> {
     const { data, error } = await apiClient.POST('/api/v1/projects/{project_id}/new-things', {
       params: { path: { project_id } },
       body,
     })
     if (error) throw error
     return data
   }
   ```

5. **Add a hook** in `hooks.ts`. Invalidate related query keys in `onSuccess`.

6. **Use the hook** in the component — never import from `requests.ts` directly
   in UI code.

## Rules

- `schema.ts` is generated — never edit it manually
- `types.ts` only re-exports from `schema.ts` — no hand-written types that
  duplicate the schema
- `requests.ts` has no React imports
- `hooks.ts` never imports `fetch` or constructs URLs
- Path strings in `requests.ts` must match `schema.ts` exactly (copy/paste)
- Always invalidate relevant cache keys after mutations
- Run `sync-openapi.sh` before writing frontend code for any changed endpoint
