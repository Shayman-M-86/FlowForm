# Hook Guide

This folder contains named API hooks for the Studio app. Domain hooks own query keys, request/response shaping, enabled logic, and mutation invalidation. Cache behaviour comes from `src/lib/query/queryPolicy.ts`, and request-time auth/permission behaviour comes from `src/api/middleware/`.

## How The Pieces Fit

`src/api/client.ts` creates the shared OpenAPI client and installs middleware in this order:

1. `authMiddleware`
2. `createPermissionMiddleware(queryClient)`

The hooks in this folder call `apiClient.GET/POST/PATCH/DELETE` inside named hooks. Query hooks should use `usePolicyQuery()` so storage, stale time, cooldowns, polling, refetch triggers, and optional persistence come from a named `QUERY_POLICIES` row. Mutation hooks should use `useMutation()` directly and invalidate the query keys affected by the write.

Use `$api` only for direct OpenAPI React Query calls outside these named hooks. New reusable domain access should live here so cache keys and invalidation stay in one place.

## Before Writing A Hook

Find all call sites for the domain you are changing:

```bash
rg "from.*@/api/hooks/members" src
```

Note:

- Named hooks the file must export.
- Named types call sites import directly.
- Hook arguments such as `projectId`, `surveyId`, or nullable IDs.
- What `.data` shape consumers expect.
- What mutation payload shape consumers pass.

## Endpoint Contracts

Use the OpenAPI MCP tools when endpoint details are unclear.

Useful calls:

```text
find_endpoints("member")
describe_endpoint(operation_id: "listMembers")
describe_schema("ProjectMemberResponses")
```

Check:

- Required nullable fields in request schemas.
- Whether list responses are bare arrays or wrapped objects.
- Whether deletes/actions return a response body or no content.
- Path parameter names and request body schema names.

Do not create separate request/response type files. Infer types from `components['schemas']` in `src/api/generated/schema.ts`.

## Request Middleware

Middleware is installed once in `src/api/client.ts`; hooks do not attach auth headers or perform permission checks manually.

### Auth Middleware

`authMiddleware` reads the current token getter from `tokenProvider`. If a getter exists, it awaits the access token and sets:

```text
Authorization: Bearer <token>
```

If no token getter has been initialized yet, the request is passed through unchanged.

### Permission Middleware

`permissionMiddleware` uses generated `routePermissions` from `src/api/generated/rbac.gen.ts` to match protected API routes by method and path.

On request:

- Extracts `project_id` and optional `survey_id` from the matched route.
- Reads cached permissions from `permissionKeys.project(projectId)` and, when available, `permissionKeys.survey(projectId, surveyId)`.
- Never fetches permissions from middleware. A cold permission cache lets the request continue and trusts the backend to allow or deny.
- Checks survey-scoped cache first when a survey cache exists, then falls back to project permissions.
- Throws `PermissionDeniedError` locally when cached permissions prove the user lacks the required permission.

On backend `403` responses:

- Invalidates the project permission query.
- Also invalidates the survey permission query when the matched route contains a `survey_id`.
- Gates those invalidations with `flowform.perm-cooldowns`, currently 60 seconds per serialized permission query key.

## Query Hook Template

Use `usePolicyQuery()` for server-state queries in this folder.

```ts
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { usePolicyQuery } from '@/lib/query/usePolicyQuery'
import { QUERY_POLICIES } from '@/lib/query/queryPolicy'
import type { components } from '@/api/generated/schema'

export type DomainOut = components['schemas']['DomainResponses']

const domainKeys = {
  list: (projectId: number) => ['domain', 'project', projectId] as const,
}

export function useDomainList(projectId: number | null) {
  return usePolicyQuery({
    queryKey: domainKeys.list(projectId ?? 0),
    enabled: projectId != null && projectId > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/projects/{project_id}/domain', {
        params: { path: { project_id: projectId! } },
      })
      if (error) throw error
      return data
    },
    policy: QUERY_POLICIES.projectMembers,
  })
}

export function useCreateDomain(projectId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async (body: components['schemas']['CreateDomainRequest']) => {
      const { data, error } = await apiClient.POST('/api/v1/projects/{project_id}/domain', {
        params: { path: { project_id: projectId } },
        body,
      })
      if (error) throw error
      return data
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: domainKeys.list(projectId) })
    },
  })
}
```

## Query Policies

Every hook that creates a TanStack server-state query should pass one named policy row from `QUERY_POLICIES`. Derived hooks such as `useProject()` can reuse another hook's cached data instead of creating a new query.

| Policy | Current hook family |
| --- | --- |
| `profile` | `useMyProfile` |
| `verificationCheck` | `useCheckVerification` |
| `projects` | `useProjects` |
| `projectPermissions` | `useProjectPermissions` |
| `surveyPermissions` | `useSurveyPermissions` |
| `myInvitations` | `useMyInvitations` |
| `surveys` | `useSurveys` |
| `survey` | `useSurvey` |
| `projectMembers` | `useProjectMembers` |
| `projectRoles` | `useProjectRoles` |
| `surveyMembers` | `useSurveyMembers` |
| `surveyRoles` | `useSurveyRoles` |
| `projectInvitations` | `useProjectInvitations`, `useResolveInvitationByToken` |
| `publicLinks` | `usePublicLinks` |
| `surveyVersions` | `useSurveyVersions` |
| `surveyNodes` | `useSurveyNodes` |
| `subjects` | `useSubjects`, `useSubject` |
| `participants` | `useParticipants` |
| `results` | `useSurveyResultSubjects` |
| `resultDetail` | `useSubjectTree` |

Current policy behaviour:

| Policy group | Storage | Stale time | Notes |
| --- | --- | --- | --- |
| `profile` | `local` | 20 min | Persists across browser restarts. |
| `verificationCheck` | `memory` | 1 min | 1 min cooldown, refetch on focus; only enabled while unverified. |
| `projects` | `local` | 5 min | 15s automatic-fetch cooldown. |
| `projectPermissions`, `surveyPermissions` | `session` | 20 min | Permission checks read these caches; middleware does not fetch them. |
| `myInvitations` | `session` | 5 min | 15s cooldown, 5 min polling, refetch on focus. |
| `surveys`, `survey`, `projectMembers`, `projectRoles`, `surveyMembers`, `surveyRoles` | `session` | 5 min | 15s automatic-fetch cooldown. |
| `projectInvitations`, `publicLinks`, `surveyVersions`, `surveyNodes` | `memory` | 30s | Fast-changing management or builder data; not persisted. |
| `subjects`, `participants` | `session` | 2 min | 15s automatic-fetch cooldown. |
| `results` | `memory` | 30s | Fast-changing result data; not persisted. |
| `resultDetail` | `session` | 20 min | Per-subject result detail. |

When adding a new query family, add a policy row first, then reference it from the hook. Dynamic IDs stay in query keys, not in policy rows.

`usePolicyQuery()` applies the resolved policy, picks the matching persister, records automatic fetch starts in `flowform.query-cooldowns`, and suppresses focus/reconnect/polling refetches while a cooldown is active. If stale cached data is waiting behind a cooldown, it schedules an exact query invalidation when the cooldown expires.

`queryClient.ts` still provides global defaults: 5 minute default `staleTime`, one retry for most query failures, and no retry for `RATE_LIMIT_EXCEEDED`.

## Choosing A Policy

Use the existing policy whose behaviour matches the query family. If no row fits, add a new one.

| Data shape | Typical storage |
| --- | --- |
| User profile or project list that should survive browser restart | `local` |
| Permissions and management lists that should survive refresh only | `session` |
| Fast-changing builder or invitation/link state | `memory` |

Policy rows control storage, `staleTime`, persisted `maxAge`, `gcTime`, cooldown, polling, and automatic refetch triggers.

Default persisted `maxAge` values live in `queryPersistence.ts`: session-backed queries default to 20 minutes, and local-backed queries default to 24 hours unless the policy overrides them.

Mutation invalidation stays in the mutation hook because it describes the consequence of a specific write.

## Query Keys

Keep query keys local to the domain file.

```ts
const surveyKeys = {
  list: (projectId: number) => ['surveys', 'project', projectId] as const,
  detail: (projectId: number, surveyId: number) =>
    ['surveys', 'project', projectId, 'id', surveyId] as const,
}
```

For disabled nullable IDs, use a stable fallback key and set `enabled: false`:

```ts
queryKey: surveyMemberKeys.list(projectId ?? 0, surveyId ?? 0),
enabled: projectId != null && projectId > 0 && surveyId != null && surveyId > 0,
```

## Mutation Invalidation

- Creates, updates, and deletes invalidate the affected list key.
- Mutations that update a detail view invalidate both list and detail keys.
- Deletions may also remove detail queries when the item can no longer exist.
- `useAcceptInvitation()` invalidates both `myInvitations` and `['projects']`.
- `useAcceptInvitationByToken()` invalidates `myInvitations`, `['projects']`, and its own `resolveByToken` query key.

Example:

```ts
onSuccess: () => {
  void queryClient.invalidateQueries({ queryKey: surveyKeys.list(projectId) })
  void queryClient.invalidateQueries({ queryKey: surveyKeys.detail(projectId, surveyId) })
}
```

## Current Domains

| File | Hooks | Notes |
| --- | --- | --- |
| `projects.ts` | `useProjects`, `useProject`, `useCreateProject`, `useUpdateProject`, `useDeleteProject` | `useProject` derives slug lookup from the project list. `useProjects` takes an optional `enabled` flag for routes that may not be authenticated yet. |
| `surveys.ts` | `useSurveys`, `useSurvey`, `useCreateSurvey`, `useUpdateSurvey`, `useDeleteSurvey` | `useSurvey` resolves project ID from cached project list. |
| `members.ts` | `useProjectMembers`, `useUpdateProjectMember`, `useDeleteProjectMember`, `useProjectInvitations`, `useSendInvitation`, `useRevokeInvitation`, `useMyInvitations`, `useAcceptInvitation`, `useResolveInvitationByToken`, `useAcceptInvitationByToken`, `useDeclineInvitation` | Accepting an invitation also invalidates `['projects']`. `useResolveInvitationByToken` is the public token-resolve query used pre-login; `useAcceptInvitationByToken` also invalidates its resolve query key on success. `useMyInvitations` takes an optional `enabled` flag for routes that may not be authenticated yet. |
| `roles.ts` | `useProjectRoles`, `useCreateProjectRole`, `useUpdateProjectRole`, `useDeleteProjectRole` | Project-role management. |
| `survey-roles.ts` | `useSurveyRoles`, `useCreateSurveyRole`, `useUpdateSurveyRole`, `useDeleteSurveyRole` | Survey-role management. |
| `survey-members.ts` | `useSurveyMembers`, `useAssignSurveyMemberRole`, `useUpdateSurveyMemberRole`, `useRemoveSurveyMemberRole` | Survey-level member role assignments. |
| `links.ts` | `usePublicLinks`, `useCreatePublicLink`, `useUpdatePublicLink`, `useDeletePublicLink` | List response is wrapped as `{ links: [] }` and unwrapped by the hook. |
| `versions.ts` | `useSurveyVersions`, `useCreateSurveyVersion`, `usePublishSurveyVersion`, `useArchiveSurveyVersion`, `useCopyVersionToDraft` | Builder version lifecycle. |
| `nodes.ts` | `useSurveyNodes`, `useCreateNode`, `useUpdateNode`, `useDeleteNode` | Builder node lifecycle. |
| `subjects.ts` | `useSubjects`, `useSubject`, `useUpdateSubject`, `useParticipants`, `useCreateParticipant`, `useUpdateParticipant`, `useDeleteParticipant` | Subject/participant management. |
| `results.ts` | `useSurveyResultSubjects`, `useSubjectTree`, `useDeleteSession`, `useExportResults` | Survey results browsing. |
| `me.ts` | `useMyProfile`, `useUpdateProfile`, `useChangePassword`, `useResendVerification`, `useCheckVerification`, `useDeleteAccount` | Deleting an account clears FlowForm query cache. `useCheckVerification(enabled)` re-checks Auth0 live and invalidates `profile` when newly verified. |
| `permissions/index.ts` | `useProjectPermissions`, `useHasProjectPermission`, `useSurveyPermissions`, `useHasSurveyPermission` | Also exports `PERMISSION_REQUIRED_TOOLTIP`. |

## Verify

From `frontend/apps/studio-app/`:

```bash
pnpm run build
```

For focused lint on hook/query edits:

```bash
pnpm exec eslint -- src/api/hooks src/lib/query
```
