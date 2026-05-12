# FlowForm Studio — Claude Code Guide

Studio is the management dashboard for FlowForm. Authenticated users create
and manage projects, configure surveys, manage team members, and track
responses. It is a React 19 + Vite SPA — not a public-facing site, not a
form-filler.

---

## Tech stack

| Concern | Library |
| --- | --- |
| Routing | TanStack Router v1 (file-based, `src/routes/`) |
| Server state | TanStack Query v5 (`src/api/`) |
| Authentication | Auth0 (`@auth0/auth0-react`) |
| Forms | react-hook-form + zod |
| Styles | Tailwind v4 + `@flowform/styles` tokens |
| UI components | `@flowform/ui` |
| Build | Vite 8, port 5174 |

---

## Styling rules

**Priority order — follow this strictly:**

1. **`@flowform/ui` component first.** If a component exists in the library,
   use it. Do not recreate `Button`, `Card`, `Modal`, `Input`, `Badge`,
   `Spinner`, `Tooltip`, `DropdownMenu`, `Select`, `Toggle`, `TabSelector`,
   etc. from scratch.

2. **Tailwind for layout and scale.** Use Tailwind utilities for positioning,
   spacing, sizing, flex/grid, and responsive behaviour. This is Tailwind's
   primary job in this app.

3. **Design tokens for colour, surface, and shadow.** When you need colour
   or surface values that aren't covered by a `@flowform/ui` component, use
   CSS custom properties from `@flowform/styles/tokens.css` directly:

   ```css
   /* Colour */
   var(--primary)               var(--primary-hover)
   var(--accent)                var(--accent-muted)
   var(--destructive)           var(--destructive-foreground)
   var(--foreground)            var(--muted-foreground)
   var(--background)            var(--card)
   var(--border)                var(--input)
   var(--success)               var(--warning)

   /* Surface interactions */
   var(--bg-hover-highlight)    var(--transparent-hover)
   var(--transparent-press)     var(--transparent-active)

   /* Shadows */
   var(--app-shadow-xs)   var(--app-shadow-sm)  var(--app-shadow)
   var(--app-shadow-md)   var(--app-shadow-lg)  var(--app-shadow-xl)
   ```

   Tokens work in both light (`:root`) and dark (`.dark`) themes
   automatically — never hardcode colour values.

4. **No custom CSS for things Tailwind or tokens cover.** Only reach for a
   `<style>` block or a `.css` file when you genuinely cannot express
   something with the above tools (e.g. complex animations, pseudo-elements).

---

## Routing

Routes are file-based under `src/routes/`. TanStack Router generates
`routeTree.gen.ts` automatically — **never edit that file by hand**. Run
`npm run routes` to regenerate after adding or renaming a route file.

The root route (`__root.tsx`) wraps everything in `ProtectedApp` → `SiteHeader`
→ `<Outlet />`. Dynamic segments use `$param` syntax; access them via
`Route.useParams()`.

**Adding a new page:**

1. Create `src/routes/your-path/index.tsx` (or `your-path.tsx` for a leaf).
2. `export const Route = createFileRoute('/your-path')({ component: YourPage })`
3. Create `src/pages/YourPage.tsx`.
4. Link with `<Link to="/your-path" />` from `@tanstack/react-router`.

---

## Authentication flow

1. `ProtectedApp` initialises Auth0 with `openid profile email` scope.
2. On first load for a new user, calls `POST /api/v1/auth/bootstrap` with the
   Auth0 ID token to create the backend user record.
3. User info is in `UserContext` — access it via `useUser()`.
4. Every API request gets a bearer token injected by `useApi.ts` via
   `getAccessTokenSilently()`.
5. Dev bypass: set `VITE_AUTH_BYPASS` — see `src/auth/testing.ts`.

---

## API layer

**Never call `fetch` directly.** Use hooks from `src/api/`.

```ts
useApi()            // returns executor() with auth token baked in
useProjects()       // GET /api/v1/projects
useProject(ref)     // GET /api/v1/projects/:ref
useCreateProject()  // POST /api/v1/projects
useDeleteProject()  // DELETE /api/v1/projects/:ref
```

Add new response types to `src/api/types.ts`. New hooks pattern:

```ts
export function useMyThing(id: string) {
  const execute = useApi();
  return useQuery({
    queryKey: ["my-thing", id],
    queryFn: () => execute((token) => client.get<MyThing>(`/api/v1/my-thing/${id}`, token)),
  });
}
```

Design-preview mode (`src/api/designPreview.ts`) returns mock data from
`mockData.ts` without hitting the network — useful for building UI without a
running backend.

---

## Environment variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `VITE_API_BASE_URL` | Backend base URL | `http://localhost:5000` |
| `VITE_AUTH0_DOMAIN` | Auth0 tenant domain | required |
| `VITE_AUTH0_CLIENT_ID` | Auth0 client ID | required |
| `VITE_AUTH_BYPASS` | Skip Auth0 in dev | unset |

---

## Current state / known stubs

- `ProjectSurveysPage` — mostly unimplemented; stub UI only.
- `ProjectDashboardPage` — members and permissions sections use mock data.
- Survey editing is in the `public-site` builder, not yet integrated into Studio.
