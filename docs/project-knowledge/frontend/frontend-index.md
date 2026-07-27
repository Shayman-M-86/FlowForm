---
title: Frontend implementation
aliases: ["Frontend implementation"]
document_type: implementation
status: draft
authority: canonical
verified_against_commit: null
tags: [frontend]
related_code:
  - "../../../frontend/package.json"
  - "../../../frontend/pnpm-workspace.yaml"
  - "../../../frontend/apps/public-site/src/"
  - "../../../frontend/apps/studio-app/src/"
  - "../../../frontend/packages/"
  - "../../../frontend/scripts/generate-types.mjs"
related_docs: ["Builder and rules", "Product knowledge"]
---

# Frontend implementation

The frontend workspace has two applications and shared packages. The public
site is an Astro application with interactive shared components where needed;
Studio is a React/Vite application that owns authenticated application screens,
backend client integration, and the respondent experience. Shared builder,
schema, UI, style, and site-shell packages provide reusable capabilities without
depending back on application modules.

Studio mounts identity, query, theme, and routing providers at its entry point.
It owns protected application navigation and typed API access. The builder
package provides authoring and form-filler surfaces used across frontend
experiences, while the schema package exposes generated contracts derived from
the backend OpenAPI definition. Generated route and API/schema output should be
refreshed through their generators rather than edited as handwritten code.

Application manifests provide lint and build workflows, and Studio has focused
tests around API, identity bootstrap, query, and persisted draft behaviour. The
public site and shared packages need separate evidence before claiming broader
automated test coverage.

## Related documents

- [[builder-and-rules|Builder and rules]]
- [[product-index|Product knowledge]]
