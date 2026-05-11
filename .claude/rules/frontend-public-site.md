---
globs: frontend/apps/public-site/src/**/*.{astro,ts,tsx}
---

# Public site rules

This is an **Astro** app, not a React SPA. Key constraints:

- Routing is file-based under `src/pages/` — no TanStack Router here
- Interactive components are React islands rendered with `client:*` directives
- Static `.astro` components ship zero JS by default — only reach for React when interactivity is needed
- Never call `fetch` directly — go through the established API patterns
- Use `@flowform/ui` components rather than raw HTML equivalents
- Do not remove or reorder `@pinegrow/piny-astro` in `astro.config.mjs`
- Do not edit sitemap output files — they are generated at build time
- CSS subpath imports (`@flowform/styles/tokens.css`, `@flowform/builder/node-page.css`) must stay as-is; the aliases are configured in `astro.config.mjs`
