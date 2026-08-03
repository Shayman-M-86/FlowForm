---
title: Public Site application
aliases: ["Public Site application", "FlowForm Public Site", "Public Site frontend architecture"]
document_type: architecture
status: verified
authority: canonical
verified_evidence_digest: sha256:1c93dbb7e8ed19989245029daa743c3775699b320ac46352d5daae100bc0b4fd
last_edited: 2026-08-04
tags: [frontend]
related_code:
  - "../../../frontend/apps/public-site/astro.config.mjs"
  - "../../../frontend/apps/public-site/src/pages/index.astro"
  - "../../../frontend/apps/public-site/src/components/NodePageIsland.tsx"
  - "../../../frontend/apps/public-site/src/layouts/DocsLayout.astro"
change_triggers:
  - "../../../frontend/apps/public-site/src/"
  - "../../../frontend/packages/builder/src/"
  - "../../../frontend/packages/ui/src/"
  - "../../../frontend/packages/styles/src/"
  - "../../../frontend/packages/site-shell/src/"
related_docs: ["Frontend implementation", "Studio application", "Shared frontend packages", "Builder and rules", "System context"]
---

# Public Site application

The Public Site is an Astro application for the marketing surface and public
product documentation. Its default model is static-first: Astro pages and
components render without shipping a client application unless an interaction
is explicitly mounted as a React island.

```text
Astro pages and content collections
             |
        static output
             |
      +------+------+
      |             |
      v             v
marketing/docs   explicit React island
                       |
                 builder demonstration
```

## Static and interactive boundaries

File-based Astro pages own the marketing home and generated documentation
routes. The documentation route enumerates the content collection at build
time, renders each entry, and passes its headings and current path to the docs
layout. Sitemap and site metadata are part of the Astro configuration.

Interactive React is reserved for islands. The home page's builder island is
hydrated client-side and wraps shared builder components in a memory router so
preview navigation does not become Public Site routing. The form filler and AI
import validator are lazy-loaded behind their interactions to keep them out of
the initial builder chunk.

## Builder demonstration boundary

The live builder on the marketing page is a standalone demonstration. It does
not authenticate, call the backend, create a project or survey version, or
persist a response. Its node state is controlled inside the island, the draft
is saved to browser `localStorage`, and preview state is passed through browser
`sessionStorage`.

This demonstration proves that the shared authoring and form-filler surfaces
can run outside Studio. It does not establish that a visitor's draft is durable,
private from other users of the browser, synchronized between devices, or part
of the FlowForm account model.

The production respondent experience currently lives in
[[studio-application|Studio application]] under `/respond/{token}` and public
slug routes. Moving that responsibility would require preserving the backend
session, cookie, Auth0, generated-contract, and form-filler integration—not
simply copying the demonstration island.

## Shared visual system

The Public Site consumes the UI, styles, site-shell, builder, and schema
packages directly from source. Astro/Vite aliases define those package and CSS
subpath boundaries, while static Astro components remain free to use Astro-native
icons and layouts. Shared design tokens provide the common colour, typography,
surface, and theme vocabulary across applications.

## Validation boundary

The application manifest provides Astro build, preview, and ESLint entry
points. A successful static build establishes that pages and content can be
rendered; it does not exercise the builder demonstration in a real browser,
prove every public link, or attest the deployed CDN and domain.

## Related documents

- [[frontend-index|Frontend implementation]]
- [[studio-application|Studio application]]
- [[shared-frontend-packages|Shared frontend packages]]
- [[builder-and-rules|Builder and rules]]
- [[system-context|System context]]
