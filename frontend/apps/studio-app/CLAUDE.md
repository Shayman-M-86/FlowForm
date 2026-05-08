# FlowForm Studio — Claude Code Guide

## What this app is

Studio is the management dashboard for the FlowForm platform. It is where authenticated users create and manage projects, configure surveys, manage team members, and track responses. It is a React 19 + Vite SPA — not a public-facing site, not a form-filler. Think of it as the back-office admin interface.

---

## Tech stack

| Concern | Library |
|---|---|
| Routing | TanStack Router v1 (file-based, `src/routes/`) |
| Server state | TanStack Query v5 (`src/api/`) |
| Authentication | Auth0 (`@auth0/auth0-react`) |
| Forms | react-hook-form + zod |
| Styles | Tailwind v4 + `@flowform/styles` tokens |
| UI components | `@flowform/ui` |
| Build | Vite 8, port 5174 |

---

## Directory layout

```
src/
├── api/              # HTTP client + React Query hooks
│   ├── client.ts     # Fetch-based client (get, post, patch, del)
│   ├── useApi.ts     # Hook that injects Auth0 bearer token into every request
│   ├── projects.ts   # useProjects, useProject, useCreateProject, useDeleteProject
│   ├── types.ts      # All API response TypeScript interfaces
│   └── mockData.ts   # Dev / design-preview mock responses
├── auth/             # Auth0 integration and user context
│   ├── ProtectedApp.tsx    # Auth guard: Auth0 provider → bootstrap → render app
│   ├── UserContext.tsx     # React Context for current user (email, name, avatar)
│   ├── redirect.ts         # Post-login redirect handling
│   └── testing.ts          # Auth bypass for dev environments
├── components/       # Shared presentational components
│   └── SiteHeader.tsx      # Top nav: logo, project selector, user menu
├── lib/              # App-level configuration
│   ├── router.ts     # TanStack Router instance + routeTree.gen.ts
│   ├── queryClient.ts # React Query config (1 min stale, 1 retry)
│   └── activeProject.ts # localStorage helper for selected project slug
├── pages/            # Full-page view components (one per route)
│   ├── ProjectsPage.tsx
│   ├── ProjectDashboardPage.tsx
│   └── ProjectSurveysPage.tsx
└── routes/           # File-based route definitions (TanStack Router)
    ├── __root.tsx          # Root layout: ProtectedApp + SiteHeader + <Outlet />
    ├── index.tsx           # / → redirect to active project or /projects
    └── projects/
        ├── index.tsx       # /projects
        └── $slug/
            ├── index.tsx   # /projects/:slug
            └── surveys.tsx # /projects/:slug/surveys
```

---

## Routing

Routes are file-based under `src/routes/`. TanStack Router generates `routeTree.gen.ts` automatically — **never edit that file by hand**. Add a new route by creating a new file in `src/routes/` following the existing naming pattern.

The root route (`__root.tsx`) wraps everything in:
1. `ProtectedApp` — Auth0 guard, user bootstrap
2. `SiteHeader` — persistent top nav
3. `<Outlet />` — page content

Dynamic segments use `$param` syntax (e.g. `$slug`). Access them via `Route.useParams()`.

---

## Authentication flow

1. `ProtectedApp` initialises Auth0 with `openid profile email` scope.
2. On first load, if the user is new, calls `POST /api/v1/auth/bootstrap` with the Auth0 ID token to create the user record in the backend.
3. User info is stored in `UserContext` and available anywhere via `useUser()`.
4. Every API request gets a bearer token injected by `useApi.ts` via `getAccessTokenSilently()`.
5. Auth bypass is available in dev via an env var (`VITE_AUTH_BYPASS`) — see `src/auth/testing.ts`.

---

## API layer

**Never call `fetch` directly.** Use the hooks in `src/api/`.

```
useApi()            → returns an executor() function with auth token baked in
useProjects()       → GET /api/v1/projects  (list)
useProject(ref)     → GET /api/v1/projects/:ref
useCreateProject()  → POST /api/v1/projects
useDeleteProject()  → DELETE /api/v1/projects/:ref
```

The base URL comes from `VITE_API_BASE_URL` (defaults to `http://localhost:5000`).

All API response shapes are typed in `src/api/types.ts`. Add new endpoint types there.

Design-preview mode (`src/api/designPreview.ts`) switches the query hooks to return mock data from `mockData.ts` instead of hitting the network — useful for building UI without a running backend.

---

## Adding a new page

1. Create `src/routes/your-path/index.tsx` (or `src/routes/your-path.tsx` for a leaf route).
2. Export a `Route` using `createFileRoute('/your-path')({ component: YourPage })`.
3. Create the page component in `src/pages/YourPage.tsx`.
4. TanStack Router picks up the route automatically on next dev server start.
5. Link to it using `<Link to="/your-path" />` from `@tanstack/react-router`.

---

## Adding a new API hook

1. Add the response type to `src/api/types.ts`.
2. Add the hook to the appropriate file in `src/api/` (or create a new one).
3. Use `useApi()` to get the executor, then wrap it in `useQuery` or `useMutation` from TanStack Query.

Pattern:
```ts
export function useMyThing(id: string) {
  const execute = useApi();
  return useQuery({
    queryKey: ["my-thing", id],
    queryFn: () => execute((token) => client.get<MyThing>(`/api/v1/my-thing/${id}`, token)),
  });
}
```

---

## Workspace packages

| Package | What it provides |
|---|---|
| `@flowform/ui` | Button, Card, Modal, Badge, Spinner, DropdownMenu, Input, etc. |
| `@flowform/styles` | Design tokens, Tailwind config, component utility classes |
| `@flowform/site-shell` | SiteHeader CSS and nav link constants |
| `@flowform/builder` | Survey/question builder (imported but lightly used in Studio) |

Always prefer components from `@flowform/ui` over writing raw HTML equivalents.

---

## Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `VITE_API_BASE_URL` | Backend base URL | `http://localhost:5000` |
| `VITE_AUTH0_DOMAIN` | Auth0 tenant domain | required |
| `VITE_AUTH0_CLIENT_ID` | Auth0 client ID | required |
| `VITE_AUTH_BYPASS` | Skip Auth0 in dev | unset |

---

## Current state / known stubs

- `ProjectSurveysPage` — mostly unimplemented; stub UI only.
- `SurveysPage` — stub.
- `ProjectDashboardPage` — members and permissions sections use mock data.
- Survey editing is done in the separate `public-site` builder, not yet integrated into Studio.
