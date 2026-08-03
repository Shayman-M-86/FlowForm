---
title: Frontend implementation
aliases: ["Frontend implementation"]
document_type: implementation
status: verified
authority: canonical
verified_evidence_digest: sha256:1ab54ef812b8957b44bfe95162b94aa7e3f29ef284f07274e425a3f9046fbee8
last_edited: 2026-08-04
tags: [frontend]
related_code:
  - "../../../frontend/package.json"
  - "../../../frontend/pnpm-workspace.yaml"
  - "../../../frontend/apps/studio-app/src/main.tsx"
  - "../../../frontend/apps/public-site/astro.config.mjs"
  - "../../../frontend/scripts/generate-types.mjs"
change_triggers:
  - "../../../frontend/apps/public-site/src/"
  - "../../../frontend/apps/studio-app/src/"
  - "../../../frontend/packages/"
related_docs: ["Studio application", "Public Site application", "Shared frontend packages", "Frontend API and server state", "Builder and rules", "Product knowledge", "System context"]
---

# Frontend implementation

The frontend is a pnpm workspace containing two applications and five shared
packages. [[studio-application|Studio]] is a React/Vite single-page application
for authenticated management and the current respondent routes.
[[public-site-application|Public Site]] is an Astro application for static-first
marketing and documentation plus an interactive, browser-local builder
demonstration.

Shared builder, schema, UI, style, and site-shell packages provide reusable
capabilities without depending back on application modules. They are consumed
directly from source through TypeScript and bundler aliases rather than being
built and published between local workspace applications.

```text
                         frontend workspace
                                |
              +-----------------+-----------------+
              |                                   |
          Studio app                         Public Site
 management + respondent routes         public product/docs
              |                                   |
              +-----------------+-----------------+
                                |
       builder / schema / UI / styles / site-shell packages
                                |
                     generated API contracts
                                |
                            Backend API
```

## Ownership boundaries

| Boundary | Owns | Does not own |
| --- | --- | --- |
| Studio application | Authenticated shell, account/project/survey management, typed API integration, persisted server state, authoring adapter, and respondent routes | Backend authorization, durable survey/response storage, or the public marketing content tree |
| Public Site application | Static pages, public documentation, metadata, sitemap, and explicitly hydrated interactive islands | Authenticated management or production respondent-session coordination |
| Shared packages | Portable builder/filler components, generated domain contracts, UI primitives, design tokens, and common navigation vocabulary | Application routing, provider setup, backend calls, or environment-specific persistence policy |
| Generated contracts | Types, runtime schemas/constraints, and route-permission metadata derived from backend OpenAPI | Runtime validation or authorization unless consuming code explicitly invokes it |

Studio mounts identity, query, theme, and routing providers at its entry point.
Its route tree separates public invitation flows, respondent entry, and the
protected Studio shell. API calls use generated OpenAPI types, named domain
hooks, and query policies rather than page-local request definitions.

The builder package exposes controlled authoring and form-filler surfaces. The
applications decide where nodes come from, how changes are persisted, and what
happens when an answer or completed flow is emitted. This keeps the portable
interaction model separate from Studio's server adapter and the Public Site's
local demonstration storage.

## Generated and handwritten boundaries

The frontend consumes three important generated surfaces:

- Studio's OpenAPI path/schema definitions;
- route-permission metadata derived from backend RBAC annotations; and
- builder-oriented TypeScript, Zod, and constraint output in the schema
  package.

The TanStack route tree is generated separately from Studio route files.
Generated route and API/schema output is refreshed through its owning generator
rather than edited as handwritten code. [[frontend-api-and-state|Frontend API
and server state]] describes the contract and cache path in more detail.

Application manifests provide lint and build workflows, and Studio has focused
tests around API, identity bootstrap, query, and persisted draft behaviour. The
public site and shared packages need separate evidence before claiming broader
automated test coverage.

## Topics

- [[studio-application|Studio application]]
- [[public-site-application|Public Site application]]
- [[shared-frontend-packages|Shared frontend packages]]
- [[frontend-api-and-state|Frontend API and server state]]
- [[builder-and-rules|Builder and rules]]

## Related documents

- [[builder-and-rules|Builder and rules]]
- [[studio-application|Studio application]]
- [[public-site-application|Public Site application]]
- [[shared-frontend-packages|Shared frontend packages]]
- [[frontend-api-and-state|Frontend API and server state]]
- [[product-index|Product knowledge]]
- [[system-context|System context]]
