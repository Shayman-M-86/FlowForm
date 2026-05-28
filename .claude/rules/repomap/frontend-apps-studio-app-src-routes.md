---
paths: frontend/apps/studio-app/src/routes/**
---

# frontend/apps/studio-app/src/routes/

_Last updated: 2026-05-27 by /repomap_

Implements TanStack Router file-based routing. `__root.tsx` defines the root layout: it wraps the entire app in `ProtectedApp` (Auth0 guard), renders `StudioSidebar` persistently, and places an `<Outlet />` for page content. `index.tsx` is a redirect-only route that sends users to their last active project slug (via `getActiveProjectSlug()`) or to the `/projects` list. Nested segments under `projects/` include a `$slug.tsx` layout route and a `$slug/` directory for per-project child pages; an `account/` segment handles account settings; `ui-test` and `ui-test-2` are development-only sandbox routes.
