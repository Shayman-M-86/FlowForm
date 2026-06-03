# Hook migration guide

This document describes the process for implementing a domain hook file under `src/api/hooks/`.

---

## Step 1 — Find all call sites

Grep for every import of the hook file you're about to write. This tells you exactly what the file needs to export before you write a single line.

```bash
grep -rn 'from.*@/api/hooks/members' src --include='*.ts' --include='*.tsx'
```

Note:
- Named hooks (`useProjectMembers`, `useDeleteProjectMember`, …)
- Named types (`ProjectMemberOut`, `ProjectInvitationOut`, …)
- Which files import them (so you know where to fix call sites later)

---

## Step 2 — Read the call sites

For each importing file, check how the hooks are actually called:

- What arguments does the hook take? (`projectId`, `surveyId`, both, neither)
- What does `mutateAsync` / `mutate` receive? (bare ID, `{ id, body }`, full object)
- What fields are read off `.data`?

This gives you the exact function signatures before you look at the backend.

---

## Step 3 — Query the OpenAPI MCP server

Use the MCP tools to get the authoritative endpoint shapes. **Do not infer from existing code or the generated schema grep — the MCP is the source of truth.**

### Find endpoints by keyword

```
find_endpoints("member")
find_endpoints("link")
find_endpoints("role")
```

This returns operation IDs, methods, and paths for everything matching the keyword.

### Describe each endpoint

```
describe_endpoint(operation_id: "listMembers")
describe_endpoint(operation_id: "sendInvitation")
describe_endpoint(operation_id: "removeMember")
```

Returns: path params, request body schema ref, success response schema ref, error codes.

### Describe the request/response schemas

```
describe_schema("ProjectMemberResponses")
describe_schema("SendInvitationRequest")
describe_schema("UpdateMemberRequest")
```

Returns: all fields with types, which are required vs optional, defaults.

Key things to check:
- Fields that are `required` in the schema even when they default to `null` — TypeScript will require them at the call site even for partial updates
- Whether a list response is a bare array or wrapped (`{ links: [] }` vs `[]`)
- Whether a delete/action returns a body (`200`) or is empty (`204`)

---

## Step 4 — Write the hook file

File location: `src/api/hooks/<domain>.ts`

### Template

```ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { STALE } from '@/lib/query/queryClient'
import type { components } from '@/api/generated/schema'

// Export types that call sites reference directly
export type DomainOut = components['schemas']['DomainResponses']

// Query keys — keep local to the file
const domainKeys = {
  list: (projectId: number) => ['domain', 'project', projectId] as const,
}

export function useDomainList(projectId: number | null) {
  return useQuery({
    queryKey: domainKeys.list(projectId ?? 0),
    enabled: projectId != null && projectId > 0,
    queryFn: async () => {
      const { data, error } = await apiClient.GET('/api/v1/projects/{project_id}/domain', {
        params: { path: { project_id: projectId! } },
      })
      if (error) throw error
      return data              // unwrap wrapper objects here if needed: data.items
    },
    staleTime: STALE.SLOW,
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

### Stale time tiers

| Tier | Value | Use for |
|---|---|---|
| `STALE.STATIC` | 20 min | Permissions, role definitions, user profile |
| `STALE.SLOW` | 5 min | Project/survey lists, members, roles |
| `STALE.ACTIVE` | 30 sec | Links, invitations, submissions, versions |

### Invalidation rules

- A mutation that creates, updates, or deletes a resource invalidates that resource's list key
- If the mutation updates a specific item that also has a detail key, invalidate both
- `accept invitation` invalidates both `myInvitations` and `['projects']` (because accepting gives you a new project)

---

## Step 5 — Fix call sites

After writing the hook file, update every importing file:

1. Change dead import paths (`@/api/survey/links/hooks` → `@/api/hooks/links`)
2. Fix any type mismatches at call sites — especially for update mutations where all patch fields may be required as `string | null` even though only one is changing:

```ts
// Wrong — TypeScript error if schema requires all fields
updateLink.mutate({ linkId, body: { is_active: true } })

// Correct — fill required nullable fields explicitly
updateLink.mutate({ linkId, body: { is_active: true, name: null, assigned_email: null, requires_auth: null, expires_at: null } })
```

---

## Step 6 — Verify the build

```bash
# from frontend/apps/studio-app/
npm run build
```

Filter errors by domain to distinguish new failures from pre-existing ones:

```bash
npm run build 2>&1 | grep 'error TS' | grep -v 'mockData\|@/api/survey\|@/api/errors\|UITestPage\|builder/src'
```

---

## Domains completed

| File | Hooks | Notes |
|---|---|---|
| `hooks/projects.ts` | `useProjects`, `useProject`, `useCreateProject`, `useUpdateProject`, `useDeleteProject` | Slug lookup derived from list — no backend slug endpoint |
| `hooks/surveys.ts` | `useSurveys`, `useSurvey`, `useCreateSurvey`, `useUpdateSurvey` | `useSurvey` resolves project ID from cached list |
| `hooks/members.ts` | `useProjectMembers`, `useUpdateProjectMember`, `useDeleteProjectMember`, `useProjectInvitations`, `useSendInvitation`, `useRevokeInvitation`, `useMyInvitations`, `useAcceptInvitation`, `useDeclineInvitation` | `useAcceptInvitation` also invalidates `['projects']` |
| `hooks/roles.ts` | `useProjectRoles`, `useCreateProjectRole`, `useUpdateProjectRole`, `useDeleteProjectRole` | |
| `hooks/links.ts` | `usePublicLinks`, `useCreatePublicLink`, `useUpdatePublicLink`, `useDeletePublicLink` | List response is wrapped `{ links: [] }` — unwrapped in hook |
| `hooks/me.ts` | `useMyProfile`, `useUpdateProfile`, `useChangePassword`, `useResendVerification`, `useDeleteAccount` | `useDeleteAccount` clears cache + localStorage on success |
| `hooks/permissions/index.ts` | `useProjectPermissions`, `useHasProjectPermission`, `useSurveyPermissions`, `useHasSurveyPermission` | `STALE.STATIC`; also exports `PERMISSION_REQUIRED_TOOLTIP` |

## Domains remaining

| File | Needed exports |
|---|---|
| `hooks/survey-members.ts` | `useSurveyMembers`, `useAssignSurveyMemberRole`, `useUpdateSurveyMemberRole`, `useRemoveSurveyMemberRole` |
| `hooks/survey-roles.ts` | `useSurveyRoles`, `useCreateSurveyRole`, `useUpdateSurveyRole`, `useDeleteSurveyRole` |
| `hooks/versions.ts` | Survey version hooks for builder |
| `hooks/nodes.ts` | Survey node hooks for builder |
