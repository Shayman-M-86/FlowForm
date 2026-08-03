---
title: Shared frontend packages
aliases: ["Shared frontend packages", "Frontend workspace packages", "Frontend design system"]
document_type: architecture
status: verified
authority: canonical
verified_evidence_digest: sha256:285a55c73bef7858c4586b9a0183ed1fd542d6feb68d1d4ff6f9be63598910af
last_edited: 2026-08-04
tags: [frontend]
related_code:
  - "../../../frontend/packages/builder/src/index.ts"
  - "../../../frontend/packages/schema/src/index.ts"
  - "../../../frontend/packages/ui/src/index.tsx"
  - "../../../frontend/packages/styles/src/tokens.css"
  - "../../../frontend/packages/site-shell/src/index.ts"
  - "../../../frontend/apps/studio-app/vite.config.ts"
  - "../../../frontend/apps/public-site/astro.config.mjs"
change_triggers:
  - "../../../frontend/packages/"
  - "../../../frontend/apps/studio-app/vite.config.ts"
  - "../../../frontend/apps/public-site/astro.config.mjs"
related_docs: ["Frontend implementation", "Studio application", "Public Site application", "Frontend API and server state", "Builder and rules"]
---

# Shared frontend packages

Five private workspace packages hold frontend capabilities that are useful in
more than one application. Applications depend on packages; packages do not
import application routes, providers, API clients, or environment-specific
persistence.

```text
Studio --------------------+
                           |
Public Site ---------------+--> builder --> schema
                           |       |
                           +------ UI --> styles
                           |
                           +--> site shell
```

## Package responsibilities

| Package | Responsibility |
| --- | --- |
| `@flowform/builder` | Controlled survey authoring, rule editing, form-filling runtime, preview storage helpers, and an optional AI-import subpath. |
| `@flowform/schema` | Generated builder TypeScript interfaces, Zod runtime schemas, and backend-derived constraint metadata. |
| `@flowform/ui` | Generic React controls, layout primitives, theme provider, table behavior, form-field styles, and reusable feedback components. |
| `@flowform/styles` | CSS design tokens and shared component/font styling. |
| `@flowform/site-shell` | Shared brand/navigation constants and site-shell assets used to align public and Studio navigation. |

## Source-consumption model

Packages are consumed as source through TypeScript paths and Vite/Astro aliases.
There is no intermediate package build or publication step inside the
workspace. This shortens the local feedback loop, but makes both application
configurations part of the package integration contract. New package roots or
CSS/feature subpaths must remain resolvable in each consuming application.

A change to a shared package can affect both applications even when only one
call site is obvious. Validation should therefore include the package's
consumers in proportion to the changed surface.

## Portable component contracts

The builder's primary authoring component is controlled: callers supply the
node collection, disabled/validation state, and change callback. Its form
filler similarly receives a survey and emits answer-commit and completion
events. Neither component owns backend calls or application navigation.

That narrow contract allows:

- Studio to adapt builder changes to versioned backend mutations and query
  cache updates;
- the Public Site to adapt the same component to browser-local demonstration
  storage; and
- the respondent route to adapt form-filler events to submission APIs.

The builder package root exports supported authoring, filler, model, and storage
surfaces. Heavier AI-import functionality is an explicit subpath and is
lazy-loadable. Internal debug components are not part of the root export
contract merely because they exist in the package source.

## Design-system boundary

The UI package owns reusable interaction primitives rather than Studio- or
Public-Site-specific workflows. The styles package owns CSS custom properties
for colour, typography, borders, surfaces, focus treatment, and theme values.
Application and builder components combine those primitives with Tailwind
layout and responsive utilities.

Shared components and labelled move controls provide accessibility building
blocks, but package reuse does not by itself prove keyboard, screen-reader,
contrast, or responsive conformance for every composed application screen.

## Generated schema boundary

The schema package is downstream of backend OpenAPI metadata. Its generated
interfaces give the builder compile-time request shapes, its Zod schemas allow
selected runtime validation such as imported node data, and its constraint
objects make backend limits available to UI code. These files are regenerated,
not hand-maintained.

## Related documents

- [[frontend-index|Frontend implementation]]
- [[studio-application|Studio application]]
- [[public-site-application|Public Site application]]
- [[frontend-api-and-state|Frontend API and server state]]
- [[builder-and-rules|Builder and rules]]
