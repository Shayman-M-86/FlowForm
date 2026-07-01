---
type: Service
title: Studio app
description: The authenticated React 19 + Vite SPA where survey creators manage projects, surveys, versions, links, members, and responses.
resource: frontend/apps/studio-app/
tags: [frontend, react, studio]
timestamp: 2026-07-01T00:00:00Z
---

# Overview

Studio is the back-office dashboard, not the respondent-facing app (that is
[public-site](/apps/public-site.md)). Stack: React 19, TypeScript, Vite 8,
TanStack Router v1, TanStack Query v5, Tailwind v4, Auth0.

# Folder ownership

| Folder            | Responsibility                                                       |
|-------------------|------------------------------------------------------------------------|
| `src/app/`        | Application shell and top-level providers                            |
| `src/api/`        | HTTP infra, generated schemas, middleware, domain hooks (see below)  |
| `src/auth/`       | Auth0 integration, bootstrap workflow, session storage (see [Auth](/architecture/auth.md)) |
| `src/components/` | Shared application-level components                                  |
| `src/pages/`      | Page components mounted by routes                                    |
| `src/routes/`     | TanStack Router file-based route definitions                         |
| `src/lib/`        | Framework-independent helpers and shared configuration               |

# API layer (src/api/)

Centralises all backend communication. `client.ts` defines `ApiRequestError`
(wrapping HTTP status + typed `ApiError`); `errors.ts` translates backend
`ErrorResponse` codes (see [OpenAPI contract](/architecture/openapi-contract.md))
into user-facing strings. Resource modules are grouped under `auth/`, `me/`,
`project/` (with `projects/`, `surveys/`, `members/`, `permissions/`,
`roles/`), and `survey/` (with `links/`, `members/`, `roles/`, `versions/`),
each exposing `hooks.ts` (React Query wrappers) and `requests.ts` (raw
fetch calls). `generated/` holds OpenAPI-derived schema types — never
hand-edited.

Use `$api` for all queries/mutations except the raw bootstrap request; never
call `fetch` directly. Create a named hook under `src/api/hooks/` when a
call is reused, needs cache invalidation, custom stale time, persistence, or
`enabled` logic.

# Routing (src/routes/)

`__root.tsx` wraps the app in `ProtectedApp` (Auth0 guard) and renders
`StudioSidebar` persistently with an `<Outlet />` for page content.
`index.tsx` redirects to the last active project or `/projects`. Route
files stay small — they mount page components from `src/pages/`. TanStack
Router generates `routeTree.gen.ts`, which must never be hand-edited; run
`pnpm run routes` after adding/removing/renaming route files.

# Key shared components (src/components/)

`StudioSidebar.tsx` is the primary nav shell, reading active project/survey
via `useProject`/`useSurvey` and gating links with `useHasProjectPermission`.
`SiteHeader.tsx` renders the top bar (brand, nav, active-project pill, theme
toggle, Auth0 user-avatar dropdown). `SurveyAccess.tsx`,
`CreateProjectForm.tsx`, `CreateSurveyForm.tsx`, `MemberRoleActions.tsx`,
`PermissionBadge.tsx`, and `ProjectPermissionGate.tsx` support project/survey
access management.

# Hard rules

1. Use an existing [`@flowform/ui`](/packages/ui.md) component before building a new UI primitive.
2. Use Tailwind for layout/spacing/sizing; use [design tokens](/packages/styles.md) for color — never hardcode colors.
3. Never edit generated files (`schema.ts`, `rbac.gen.ts`, `routeTree.gen.ts`) by hand.
4. Never call `fetch` directly — use `$api`.
5. Do not create separate request/response type files — infer from the generated OpenAPI schema.

# Known incomplete areas

* `ProjectSurveysPage` is mostly a stub.
* `ProjectDashboardPage` still uses mock data for members and permissions.
* The [survey builder](/packages/builder.md) has not yet been integrated into Studio.

# Citations

[1] [frontend/apps/studio-app/CLAUDE.md](../../frontend/apps/studio-app/CLAUDE.md)
[2] [.claude/rules/repomap/frontend-apps-studio-app-src-api.md](../../.claude/rules/repomap/frontend-apps-studio-app-src-api.md)
[3] [.claude/rules/repomap/frontend-apps-studio-app-src-components.md](../../.claude/rules/repomap/frontend-apps-studio-app-src-components.md)
[4] [.claude/rules/repomap/frontend-apps-studio-app-src-routes.md](../../.claude/rules/repomap/frontend-apps-studio-app-src-routes.md)
