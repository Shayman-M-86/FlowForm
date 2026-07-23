---
description: Wire a backend endpoint change into the Studio frontend — syncs the OpenAPI spec, identifies affected types, and scaffolds or updates types.ts / requests.ts / hooks.ts
allowed-tools: Bash, Read, Edit, Write
---

Wire a new or changed backend endpoint into the Studio frontend API layer.

## What you were asked to wire

$ARGUMENTS

## Steps

### 1. Sync the spec

Run this first, always — even if the user says the spec is up to date:

```bash
bash scripts/ci/sync-openapi.sh
```

This runs two things in sequence:

- Exports `backend/openapi.yaml` from the Python sources
- Generates `frontend/apps/studio-app/src/api/generated/schema.ts`

### 2. Locate the types in schema.ts

Search `src/api/generated/schema.ts` for the operation name, request schema,
and response schema. Note the exact field names, types, and optionality.
Do not guess — copy field names from the generated file.

### 3. Identify the right module directory

Match the endpoint to its domain folder under `src/api/`:

| Endpoint prefix | Module |
|---|---|
| `/api/v1/me/...` | `src/api/me/` |
| `/api/v1/projects/{id}/surveys/...` | `src/api/project/surveys/` |
| `/api/v1/projects/{id}/members/...` | `src/api/project/members/` |
| `/api/v1/projects/{id}/roles/...` | `src/api/project/roles/` |
| `/api/v1/projects/...` | `src/api/project/projects/` |

If no module exists yet, create the directory with empty `types.ts`,
`requests.ts`, and `hooks.ts` files following the conventions in
`.claude/rules/frontend-api-modules.md`.

### 4. Update types.ts

Add the new request/response types to the re-export list. Only re-export
from `../generated/schema` — no hand-written types.

### 5. Update requests.ts

Add a function for the new endpoint. Rules:

- First argument is always `apiClient: OpenApiFetchClient`
- Path string copied exactly from `schema.ts`
- `if (error) throw error` after every call
- No React, no hooks, no state

### 6. Update hooks.ts

Add a `useQuery` or `useMutation` wrapper:

- Call `useOpenApiClient()` internally
- For mutations, call `queryClient.invalidateQueries` for all affected keys
  in `onSuccess`
- Add new keys to the `*Keys` object if needed

### 7. Verify TypeScript

```bash
cd frontend/apps/studio-app && npx tsc --noEmit 2>&1 | grep -v "node_modules"
```

Fix any type errors before finishing.

### 8. Report

List every file changed and the hook name(s) the caller should import.
