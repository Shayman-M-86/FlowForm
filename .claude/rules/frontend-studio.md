---
paths: frontend/apps/studio-app/src/**/*.{ts,tsx}
---

# Studio app rules

Studio is an authenticated SPA — not a public site, not a form-filler.

- Never call `fetch` directly — use `$api` from `src/api/client.ts`
- `$api` is an `openapi-react-query` client; use `$api.useQuery('get', '/path/...')` and `$api.useMutation('post', '/path/...')`
- No `types.ts` or `requests.ts` files — types are inferred from the generated schema
- Thin named hooks in `src/api/<domain>/hooks.ts` are optional but preferred when a hook is reused or needs cache invalidation logic
- Before writing any API call, query the OpenAPI MCP tool (`list_operations`, `find_operations`, `describe_schema`) for the authoritative endpoint shape — do not infer from existing code or guess
- New routes: create a file in `src/routes/` — TanStack Router picks it up automatically
- Never edit `routeTree.gen.ts` by hand
- Prefer components from `@flowform/ui` over raw HTML equivalents
- Styles via Tailwind v4 + `@flowform/styles` tokens
