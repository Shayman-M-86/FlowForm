---
paths: frontend/apps/studio-app/src/components/**
---

# frontend/apps/studio-app/src/components/

_Last updated: 2026-05-27 by /repomap_

Contains shared UI components used across Studio routes. `StudioSidebar.tsx` is the primary navigation shell — it reads the active project and survey from API hooks (`useProject`, `useSurvey`), checks permissions with `useHasProjectPermission`, and renders contextual nav links (Projects, Surveys, Overview, Versions, Access, Responses) with tooltips on disabled items. `SiteHeader.tsx` renders the top bar with brand logo, primary nav links, an active-project pill, theme toggle, and a user-avatar dropdown (Auth0-backed). Supporting components include `SurveyAccess.tsx` (access management UI), `CreateProjectForm.tsx`, `CreateSurveyForm.tsx`, `MemberRoleActions.tsx`, `PermissionBadge.tsx`, `ProjectPermissionGate.tsx`, and an `auth/` subdirectory housing `ProtectedApp`.
