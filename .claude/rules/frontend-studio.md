---
globs: frontend/apps/studio-app/src/**/*.{ts,tsx}
---

# Studio app rules

Studio is an authenticated SPA — not a public site, not a form-filler.

- Never call `fetch` directly — use hooks from `src/api/`
- All API response types go in `src/api/types.ts`
- New API hooks use `useApi()` + `useQuery`/`useMutation` from TanStack Query
- New routes: create a file in `src/routes/` — TanStack Router picks it up automatically
- Never edit `routeTree.gen.ts` by hand
- Prefer components from `@flowform/ui` over raw HTML equivalents
- Styles via Tailwind v4 + `@flowform/styles` tokens
