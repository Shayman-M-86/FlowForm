---
title: Studio application
aliases: ["Studio application", "FlowForm Studio", "Studio frontend architecture"]
document_type: architecture
status: verified
authority: canonical
verified_evidence_digest: sha256:4deaff0a7c54138f66d54b855192ec0bb28c3e27571f2a048e4a7415b1b1b6b2
last_edited: 2026-08-04
tags: [frontend]
related_code:
  - "../../../frontend/apps/studio-app/src/main.tsx"
  - "../../../frontend/apps/studio-app/src/app/ProtectedApp.tsx"
  - "../../../frontend/apps/studio-app/src/routes/_studio.tsx"
  - "../../../frontend/apps/studio-app/src/routes/_respondent.tsx"
  - "../../../frontend/apps/studio-app/src/auth/bootstrap/useBootstrap.ts"
  - "../../../frontend/apps/studio-app/src/pages/SurveyWorkspaceTabPages/useSurveyBuilderController.ts"
  - "../../../frontend/apps/studio-app/src/pages/RespondPage.tsx"
change_triggers:
  - "../../../frontend/apps/studio-app/src/app/"
  - "../../../frontend/apps/studio-app/src/routes/"
  - "../../../frontend/apps/studio-app/src/auth/"
  - "../../../frontend/apps/studio-app/src/pages/"
related_docs: ["Frontend implementation", "Frontend API and server state", "Shared frontend packages", "Builder and rules", "Identity and authentication", "Respondent access and continuity"]
---

# Studio application

Studio is the React/Vite single-page application for FlowForm's authenticated
management experience. It also currently hosts the respondent routes for link
and public-slug entry. Those respondent routes share generated contracts and
the builder form-filler package, but they sit outside the protected Studio
shell.

```text
Studio browser entry
        |
Auth0 -> query provider -> theme -> TanStack Router
                                  /       |       \
                                 v        v        v
                          public routes respondent protected Studio
```

## Application and route composition

The root mounts Auth0, the shared TanStack Query client, the theme provider,
and TanStack Router. Development-only query and router tools are lazy-loaded so
they do not become production dependencies.

The file-based route tree has three conceptual groups:

| Route group | Boundary |
| --- | --- |
| Public | Account-independent entry such as invitation-token resolution. |
| Respondent | Survey entry and submission through a link token or public slug, with optional Auth0 identity when the entry policy requires it. |
| Studio | Protected management shell containing navigation and project, survey, account, access, member, result, and builder screens. |

Only the Studio group is wrapped by `ProtectedApp`. Authentication and
respondent access are different policy paths; a respondent route may be public,
optionally authenticated, or require a specific authenticated participant.

## Authentication bootstrap

Auth0 establishes the browser identity, but Studio does not consider the
protected application ready until backend bootstrap resolves or creates the
corresponding FlowForm user. Bootstrap also installs the access-token provider
used by the API client, assigns persisted query state to the current Auth0
subject, and restores permitted query snapshots.

The Auth0 provider is configured for refresh-token use and browser-local token
caching. This supports continuity across reloads, but makes protection of the
browser origin and script supply chain part of the credential boundary. The
FlowForm query-cache owner check is separate from Auth0's token cache and must
not be treated as token protection.

If another Auth0 subject previously owned the browser's persisted query cache,
that cache is cleared before the new owner is recorded. Logout clears FlowForm
query state, ownership metadata, browser storage, and browser Cache Storage
before redirecting through Auth0. These measures limit accidental cross-account
reuse in one browser; they are not substitutes for backend authorization or
protection against a compromised browser origin.

## Management and authoring boundary

Pages consume named API hooks and application components. Route modules remain
small and mount page components rather than accumulating feature logic.
Permissions control available actions in the interface, while the backend
remains authoritative for every protected operation.

Studio integrates the shared builder through a controller that owns the
server-facing concerns:

- selecting a survey version and checking edit/publish/archive permissions;
- loading ordered nodes through domain hooks;
- recovering unsaved browser drafts for a draft version;
- diffing controlled builder state against backend state;
- coordinating node create, update, delete, and cache replacement; and
- blocking a save when required authoring fields are incomplete.

The shared `NodePage` does not know about projects, versions, TanStack Query, or
backend endpoints. It receives nodes and change callbacks. This narrow contract
allows the Public Site demonstration to reuse the authoring surface with a
completely different persistence adapter.

## Respondent boundary

The respondent page first attempts to resume a browser submission for the
current entry descriptor. If no matching session exists, it resolves the link
or public slug, handles any required participant authentication, starts a
session, and renders the published compiled nodes through the shared form
filler. Answer commits are mapped to generated backend request shapes, and all
in-flight saves are awaited before session completion.

The browser route coordinates the interaction, but the backend remains
authoritative for entry policy, subject identity, session continuity, answer
validation and encryption, and completion state.

## Validation boundary

Studio provides lint, TypeScript/Vite production build, and Vitest entry
points. The present tests concentrate on API middleware, authentication
bootstrap, query/cache behavior, browser storage, survey-access definitions,
and selected UI layout behavior. This is useful focused coverage, not evidence
that every route and builder interaction has an end-to-end browser test.

## Related documents

- [[frontend-index|Frontend implementation]]
- [[frontend-api-and-state|Frontend API and server state]]
- [[shared-frontend-packages|Shared frontend packages]]
- [[builder-and-rules|Builder and rules]]
- [[identity-and-authentication|Identity and authentication]]
- [[respondent-access-and-continuity|Respondent access and continuity]]
