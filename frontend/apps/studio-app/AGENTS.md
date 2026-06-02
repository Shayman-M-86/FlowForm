# FlowForm Studio — Claude Code Guide

FlowForm Studio is the authenticated management dashboard for FlowForm. Users create projects, configure surveys, manage members and roles, publish versions, create links, and review responses.

It is a React 19 + Vite SPA. It is not the public survey-filler application.

---

## Read the relevant reference before editing

| Area                                                      | Reference                |
| --------------------------------------------------------- | ------------------------ |
| UI components, Tailwind, tokens, and themes               | `docs/studio/styling.md` |
| Authentication, bootstrap, session storage, and logout    | `docs/studio/auth.md`    |
| API client, named hooks, permissions, errors, and caching | `docs/studio/api.md`     |

---

## Hard rules

1. Use an existing component from `@flowform/ui` before building a new UI primitive.
2. Use Tailwind for layout, spacing, sizing, and responsive behaviour.
3. Use FlowForm design tokens for colours, surfaces, and shadows. Never hardcode colour values.
4. Never edit generated files by hand.
5. Never call `fetch` directly. Use `$api`, except for the raw bootstrap request.
6. Keep route files small. Route files should mount page components from `src/pages/`.
7. Put reusable API hooks under `src/api/hooks/`, grouped by domain.
8. Do not create separate request or response type files. Infer API types from the generated OpenAPI schema.

---

## Tech stack

| Concern        | Library                                 |
| -------------- | --------------------------------------- |
| Routing        | TanStack Router v1                      |
| Server state   | TanStack Query v5                       |
| API client     | `openapi-fetch` + `openapi-react-query` |
| Authentication | Auth0                                   |
| Forms          | `react-hook-form` + Zod                 |
| Styles         | Tailwind v4 + `@flowform/styles`        |
| Components     | `@flowform/ui`                          |
| Build          | Vite 8, port 5174                       |

---

## Folder ownership

| Folder            | Responsibility                                                                              |
| ----------------- | ------------------------------------------------------------------------------------------- |
| `src/app/`        | Application shell and top-level providers                                                   |
| `src/api/`        | Shared HTTP infrastructure, generated schemas, middleware, and domain hooks                 |
| `src/auth/`       | Auth0 integration, bootstrap workflow, current-user context, redirects, and session storage |
| `src/components/` | Shared application-level components                                                         |
| `src/pages/`      | Page components mounted by routes                                                           |
| `src/routes/`     | TanStack Router file-based route definitions                                                |
| `src/lib/`        | Framework-independent helpers and shared configuration                                      |

---

## Key file structure

```text
src/
├── app/
│   ├── ProtectedApp.tsx
│   └── providers/
│       └── QueryPersistProvider.tsx
│
├── api/
│   ├── client.ts
│   ├── tokenProvider.ts
│   ├── middleware/
│   │   ├── authMiddleware.ts
│   │   └── permissionMiddleware.ts
│   ├── hooks/
│   └── generated/
│       ├── schema.ts
│       └── rbac.gen.ts
│
├── auth/
│   ├── bootstrap/
│   │   ├── api.ts
│   │   ├── session.ts
│   │   └── useBootstrap.ts
│   ├── UserContext.tsx
│   └── redirect.ts
│
├── components/
├── lib/
├── pages/
└── routes/
```

---

## Routing

Routes are file-based under `src/routes/`.

TanStack Router generates `routeTree.gen.ts`. Never edit that file manually. Run `npm run routes` after adding, removing, or renaming route files.

Dynamic segments use `$param` syntax. Read them with `Route.useParams()`.

A route file should remain small:

```ts
import { createFileRoute } from '@tanstack/react-router'
import { ProjectsPage } from '@/pages/ProjectsPage'

export const Route = createFileRoute('/projects/')({
  component: ProjectsPage,
})
```

---

## API usage

Use `$api` for normal queries and mutations:

```ts
import { $api } from '@/api/client'

const profile = $api.useQuery('get', '/api/v1/me/profile')

const updateProfile = $api.useMutation('patch', '/api/v1/me/profile')
updateProfile.mutate({
  body: { display_name: 'Alice' },
})
```

Create a named hook under `src/api/hooks/` when a call:

* is reused in more than one place
* requires cache invalidation
* uses custom stale time
* uses persistence
* requires `enabled` logic

Use the cache tiers from `src/lib/query/queryClient.ts`:

```ts
STALE.STATIC
STALE.SLOW
STALE.ACTIVE
```

Only persist `STATIC` and `SLOW` data. Never persist rapidly changing builder data.

---

## Generated files

Never manually edit:

```text
src/api/generated/schema.ts
src/api/generated/rbac.gen.ts
src/routeTree.gen.ts
```

Regenerate them from their source definitions.

---

## Environment variables

| Variable               | Purpose             | Default                 |
| ---------------------- | ------------------- | ----------------------- |
| `VITE_API_BASE_URL`    | Backend base URL    | `http://localhost:5000` |
| `VITE_AUTH0_DOMAIN`    | Auth0 tenant domain | required                |
| `VITE_AUTH0_CLIENT_ID` | Auth0 client ID     | required                |
| `VITE_AUTH0_AUDIENCE`  | Auth0 API audience  | required                |

---

## Known incomplete areas

* `ProjectSurveysPage` is mostly a stub.
* `ProjectDashboardPage` still uses mock data for members and permissions.
* The survey builder has not yet been integrated into Studio.
