# Studio App Mock API Wiring Plan

## Goal
Replace UI-level hardcoded values and direct `mockData.ts` imports with a single API abstraction layer so every page/button interaction is powered by the same query/mutation contracts we will later point at the real backend.

## Principles
- Keep **all data reads/writes inside `src/api/*` hooks** (TanStack Query + `useApi`), never inside page components.
- Keep a **single runtime switch** (`designPreview.ts`) that selects transport:
  - `mock transport` (current implemented mock API backend)
  - `http transport` (real backend)
- Remove component-local seeded constants as source-of-truth for app state.
- Ensure every button that mutates state calls a `useMutation` hook.

## Current Gaps (Studio)
- Many pages import `@/api/mockData` directly and compute display state in-page.
- Several tabs initialize local React state from static arrays/derived placeholders.
- Some actions are UI-only (open modal, close modal) but others should persist and currently only mutate local arrays.

## Proposed Target Architecture

### 1) API domain modules (single source of truth)
Create/expand domain hooks under `src/api`:
- `projects.ts` (already partly done)
- `surveys.ts` (expand for list/detail/update/delete)
- `members.ts` (project + survey membership)
- `roles.ts` (project roles + survey roles)
- `versions.ts` (survey versions + publish/promote actions)
- `links.ts` (public links create/revoke/copy metadata)
- `responses.ts` (survey response summaries/tables)
- `settings.ts` (project/survey settings)

Each domain file should expose:
- query key factory
- typed query hooks
- typed mutation hooks
- optimistic update policy where safe

### 2) Transport split
Define a transport boundary used by each domain module:
- `src/api/client.ts` for HTTP.
- `src/api/designPreview.ts` (or `mockClient.ts`) for mock transport adapter.
- Domain hooks call transport functions, not `mockData.ts` directly.

### 3) Type normalization
- Move any ad-hoc view types into `src/api/types.ts`.
- Add API DTO types + UI mappers where mock payload and future backend payload differ.
- Keep route/page components consuming normalized view models.

## Route/Tab-by-Tab Wiring Plan

### Project level
1. `ProjectDashboardTabPages/SurveysTab.tsx`
   - Replace direct `getMockSurveysForProject` calls with `useProjectSurveys(projectSlug)`.
   - Wire “Open survey”, “Create survey”, and row actions through mutations/navigation.

2. `ProjectDashboardTabPages/MembersTab.tsx`
   - Replace `mockProjectMembers` local state seed with `useProjectMembers(projectSlug)`.
   - Wire actions:
     - Invite member → `useInviteProjectMember`.
     - Change role → `useUpdateProjectMemberRole`.
     - Remove member → `useRemoveProjectMember`.

3. `ProjectDashboardTabPages/RolesWorkspace.tsx` + `RoleEditorModal.tsx`
   - Replace local custom role arrays with `useProjectRoles(projectSlug)`.
   - Save/create/delete role actions via mutations.

4. `ProjectDashboardTabPages/SettingsTab.tsx`
   - Load project details from `useProject(projectSlug)`.
   - Save rename/url-safe-name via `useUpdateProjectSettings`.
   - Delete flow via `useDeleteProject` with proper invalidation + redirect.

### Survey workspace level
5. `SurveyWorkspaceTabPages/SurveyOverviewTab.tsx`
   - Replace `getMockSurvey` + `getMockVersionsForSurvey` with `useSurvey` + `useSurveyVersions`.

6. `SurveyWorkspaceTabPages/SurveyBuilderTab.tsx`
   - Load current editable draft/version using `useSurveyVersionDraft`.
   - Wire save/publish buttons to mutations.

7. `SurveyWorkspaceTabPages/SurveyVersionsTab.tsx`
   - Replace `mockVersions` usage with `useSurveyVersions`.
   - Wire promote/publish/archive actions via mutations.

8. `SurveyWorkspaceTabPages/SurveyLinksTab.tsx`
   - Replace direct mock link reads with `useSurveyLinks`.
   - Wire create/disable/copy link actions to mutations.

9. `SurveyWorkspaceTabPages/SurveyMembersTab.tsx`
   - Replace mixed `mockProjectMembers` + `mockSurveyMembers` composition with API results:
     - `useProjectMembers`
     - `useSurveyMembers`
   - Wire role assignment/removal with survey membership mutations.

10. `SurveyWorkspaceTabPages/SurveyResponsesTab.tsx`
    - Replace local/mock response list with `useSurveyResponses(surveySlug, filters)`.
    - Wire pagination/filter controls to query params + query key.

11. `SurveyWorkspaceTabPages/SurveySettingsTab.tsx`
    - Replace static booleans and survey lookup with `useSurveySettings`.
    - Save toggles (anonymous, close-date, etc.) via `useUpdateSurveySettings`.

## Button & Action Inventory (Execution Checklist)
For each tab, create a short action matrix:
- Button label
- Intended API operation
- Hook/mutation name
- Success behavior (toast, navigate, invalidate keys)
- Error behavior (message and retry)

This prevents leaving any action bound to local-only state.

## Suggested Implementation Order (low-risk)
1. Build missing API domain hooks + query keys (no page edits yet).
2. Migrate read paths first (queries only) tab by tab.
3. Migrate write paths (mutations/buttons) tab by tab.
4. Remove direct imports from `mockData.ts` in pages.
5. Keep `mockData.ts` only behind transport adapters until replaced by live API.
6. Add loading/empty/error states consistently to all tabs.

## Acceptance Criteria
- No page in `src/pages/**` imports `@/api/mockData`.
- All persistent button actions call query/mutation hooks.
- Toggling design-preview mode swaps data source without page changes.
- Query keys are consistent and invalidate correctly after mutations.
- No user-visible hardcoded project/survey/member/link/version rows remain.

## Verification Commands
- `rg -n "@/api/mockData" frontend/apps/studio-app/src/pages`
- `rg -n "useQuery|useMutation" frontend/apps/studio-app/src/api`
- `npm run -w frontend/apps/studio-app lint`
- `npm run -w frontend/apps/studio-app build`

## Notes for Real API Cutover
When backend endpoints are ready, swap transport implementations in API modules; UI routes/pages should remain unchanged except for any mapper updates.
