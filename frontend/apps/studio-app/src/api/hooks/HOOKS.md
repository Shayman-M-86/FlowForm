# Hook Guide

This folder contains named API hooks for the Studio app. Domain hooks own query keys, request/response shaping, enabled logic, and mutation invalidation. Cache behaviour comes from `src/lib/query/queryPolicy.ts`.

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

Every query hook should pass one named policy row from `QUERY_POLICIES`.

| Policy | Current hook family |
| --- | --- |
| `profile` | `useMyProfile` |
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
| `projectInvitations` | `useProjectInvitations` |
| `publicLinks` | `usePublicLinks` |
| `surveyVersions` | `useSurveyVersions` |
| `surveyNodes` | `useSurveyNodes` |

When adding a new query family, add a policy row first, then reference it from the hook. Dynamic IDs stay in query keys, not in policy rows.

## Choosing A Policy

Use the existing policy whose behaviour matches the query family. If no row fits, add a new one.

| Data shape | Typical storage |
| --- | --- |
| User profile or project list that should survive browser restart | `local` |
| Permissions and management lists that should survive refresh only | `session` |
| Fast-changing builder or invitation/link state | `memory` |

Policy rows control storage, `staleTime`, persisted `maxAge`, `gcTime`, cooldown, polling, and automatic refetch triggers.

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
| `projects.ts` | `useProjects`, `useProject`, `useCreateProject`, `useUpdateProject`, `useDeleteProject` | `useProject` derives slug lookup from the project list. |
| `surveys.ts` | `useSurveys`, `useSurvey`, `useCreateSurvey`, `useUpdateSurvey`, `useDeleteSurvey` | `useSurvey` resolves project ID from cached project list. |
| `members.ts` | `useProjectMembers`, `useUpdateProjectMember`, `useDeleteProjectMember`, `useProjectInvitations`, `useSendInvitation`, `useRevokeInvitation`, `useMyInvitations`, `useAcceptInvitation`, `useDeclineInvitation` | Accepting an invitation also invalidates `['projects']`. |
| `roles.ts` | `useProjectRoles`, `useCreateProjectRole`, `useUpdateProjectRole`, `useDeleteProjectRole` | Project-role management. |
| `survey-roles.ts` | `useSurveyRoles`, `useCreateSurveyRole`, `useUpdateSurveyRole`, `useDeleteSurveyRole` | Survey-role management. |
| `survey-members.ts` | `useSurveyMembers`, `useAssignSurveyMemberRole`, `useUpdateSurveyMemberRole`, `useRemoveSurveyMemberRole` | Survey-level member role assignments. |
| `links.ts` | `usePublicLinks`, `useCreatePublicLink`, `useUpdatePublicLink`, `useDeletePublicLink` | List response is wrapped as `{ links: [] }` and unwrapped by the hook. |
| `versions.ts` | `useSurveyVersions`, `useCreateSurveyVersion`, `usePublishSurveyVersion`, `useArchiveSurveyVersion`, `useCopyVersionToDraft` | Builder version lifecycle. |
| `nodes.ts` | `useSurveyNodes`, `useCreateNode`, `useUpdateNode`, `useDeleteNode` | Builder node lifecycle. |
| `me.ts` | `useMyProfile`, `useUpdateProfile`, `useChangePassword`, `useResendVerification`, `useDeleteAccount` | Deleting an account clears FlowForm query cache. |
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
