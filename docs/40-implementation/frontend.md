---
title: Frontend implementation
aliases:
  - "Frontend implementation"
document_type: implementation
status: draft
authority: canonical
verified_against_commit: ad26b87e9820
tags: [frontend]
related_code:
  - "../../frontend/package.json"
  - "../../frontend/pnpm-workspace.yaml"
  - "../../frontend/apps/public-site/src/"
  - "../../frontend/apps/studio-app/src/"
  - "../../frontend/packages/"
  - "../../frontend/scripts/generate-types.mjs"
  - "../../frontend/apps/studio-app/tests/"
related_docs:
  - "Repository map"
  - "Component map"
  - "Builder and rules"
  - "Testing workflow"
  - "Generated files"
---

# Frontend implementation

Maps frontend concepts to verified repository implementation.

## Directory ownership

- `frontend/apps/public-site/` is the Astro static site. Pages, content,
  layouts, and Astro integrations live below `src/`; its interactive builder
  demonstration hydrates shared React components in the browser.
- `frontend/apps/studio-app/` is the React/Vite application. It owns Auth0
  bootstrap, file-based routes, backend clients and query hooks, protected
  Studio screens, and the token-based respondent screen.
- `frontend/packages/builder/` owns reusable survey editing and filling;
  `schema/` owns generated builder types and validators; `ui/`, `styles/`, and
  `site-shell/` own shared presentation and navigation primitives.

## Entry points

- `apps/public-site/src/pages/index.astro` and `src/pages/docs/[...slug].astro`
  are the public site's principal page entries; `astro.config.mjs` assembles
  React, Tailwind, sitemap, font, and workspace aliases.
- `apps/studio-app/src/main.tsx` mounts Auth0, TanStack Query, theme, and router
  providers. `src/lib/router.ts` consumes the generated route tree built from
  `src/routes/`.
- Each shared package publishes its maintained surface through its
  `package.json` exports and `src/index.*` entry point.
- Workspace commands in `frontend/package.json` dispatch local development and
  production builds to each application.

## Important modules

- `studio-app/src/auth/` and `src/app/ProtectedApp.tsx` own login bootstrap and
  the protected Studio shell.
- `studio-app/src/api/client.ts`, `respondentClient.ts`, middleware, and
  `api/hooks/` form the typed backend-access boundary.
- `studio-app/src/routes/` owns URL structure; route components delegate page
  behavior to `src/pages/` and shared builder components.
- `packages/builder/src/index.ts` exposes the editor, form filler, ordering,
  preview, and draft-storage surfaces used by both applications.
- `packages/schema/src/index.ts` exposes generated TypeScript and Zod contracts
  derived from backend OpenAPI schemas.

## Dependency direction

Applications import shared workspace packages as source dependencies. Builder
depends on schema and UI; UI depends on shared styles; schema does not depend on
either application. Shared packages do not import application modules. Studio
alone currently owns Auth0 and backend API access; the public site builds static
pages and a browser-local builder demonstration.

## Generated versus handwritten code

Routes under `studio-app/src/routes/`, API hooks, pages, components, and shared
package source are handwritten. The following checked-in files are generated:

- `studio-app/src/routeTree.gen.ts` by the TanStack Router plugin;
- `studio-app/src/api/generated/schema.ts` by `openapi-typescript`;
- `studio-app/src/api/generated/rbac.gen.ts` and
  `packages/schema/src/generated/` by `frontend/scripts/generate-types.mjs`.

The generator reads `backend/openapi.yaml`. If builder schema output changes it
also warns that the handcrafted AI-import prompt requires review; that prompt
is not generated.

## Tests and validation

`apps/studio-app/tests/` contains Vitest coverage for API middleware, Auth0
bootstrap, query behavior, persisted storage, and builder drafts. Studio and
public-site manifests expose lint and production-build commands; only Studio
currently exposes a test command. `scripts/ci/check-openapi-contracts.sh`
validates backend OpenAPI export, generated frontend files, and Redocly lint.

## Known gaps

The public site has no checked-in automated test suite, so its current gates are
lint and build. The shared packages also have no package-local test commands;
their exercised coverage comes through Studio tests and application builds.

## Related documents

- [[repository-map|Repository map]]
- [[component-map|Component map]]
- [[builder-and-rules|Builder and rules]]
- [[testing|Testing workflow]]
- [[generated-files|Generated files]]
