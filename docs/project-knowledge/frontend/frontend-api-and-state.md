---
title: Frontend API and server state
aliases: ["Frontend API and server state", "Studio API client", "Frontend query architecture"]
document_type: architecture
status: verified
authority: canonical
verified_evidence_digest: sha256:ade51b05ccca7f479750def6ae8e015259eaa37f6590f234dba4b35220371057
last_edited: 2026-08-04
tags: [frontend]
related_code:
  - "../../../frontend/apps/studio-app/src/api/client.ts"
  - "../../../frontend/apps/studio-app/src/api/respondentClient.ts"
  - "../../../frontend/apps/studio-app/src/api/middleware/permissionMiddleware.ts"
  - "../../../frontend/apps/studio-app/src/api/hooks/HOOKS.md"
  - "../../../frontend/apps/studio-app/src/lib/query/queryPolicy.ts"
  - "../../../frontend/apps/studio-app/src/lib/query/queryPersistence.ts"
  - "../../../frontend/apps/studio-app/src/lib/query/queryCacheOwner.ts"
  - "../../../frontend/scripts/generate-types.mjs"
change_triggers:
  - "../../../backend/openapi.yaml"
  - "../../../frontend/apps/studio-app/src/api/"
  - "../../../frontend/apps/studio-app/src/lib/query/"
  - "../../../frontend/packages/schema/src/generated/"
related_docs: ["Frontend implementation", "Studio application", "Backend API contracts and errors", "Identity and authentication", "Generated files"]
---

# Frontend API and server state

Studio's backend integration is contract-derived and policy-driven. Generated
OpenAPI types constrain requests and responses; named domain hooks own query
keys and mutation effects; a central query-policy registry decides freshness
and browser persistence; middleware supplies authentication and uses cached
permissions as an optimization.

```text
page or component
       |
       v
named domain hook --------> query policy
       |                         |
       v                         v
typed OpenAPI client       memory/session/local cache
       |
auth + permission middleware
       |
       v
backend authorization and data
```

## Generated contract path

The backend OpenAPI document produces Studio path/schema definitions,
route-permission metadata, and builder-oriented shared schema outputs. The
typed fetch client and its TanStack Query adapter use those generated paths so
method, path, parameter, body, and response types originate from the backend
contract rather than page-local interfaces.

Generated typing does not perform runtime response validation by itself. Zod
output in the shared schema package is invoked only where consuming code
explicitly uses it. Contract synchronization catches checked-in drift; it does
not guarantee that independently deployed frontend and backend revisions are
compatible.

## API client boundaries

The normal Studio client installs two middleware layers:

1. authentication obtains the current Auth0 access token and attaches the
   bearer credential; and
2. permission middleware matches generated route metadata against cached
   project or survey permissions.

Permission middleware never fetches permissions. When the cache is cold, the
request proceeds and the backend decides. When cached data proves a denial, the
browser can stop the request early. A backend `403` invalidates the relevant
permission caches, subject to a short invalidation cooldown. This makes the
client check a responsiveness and request-reduction feature, not an
authorization boundary.

Respondent traffic uses a separate typed client with browser credentials so
recognition and resume cookies participate in requests. An authenticated
variant attaches an Auth0 token only when respondent policy requires identity.

## Named hooks and mutation effects

Reusable domain access lives in named hooks grouped by projects, surveys,
members, roles, links, versions, nodes, subjects, participants, results,
permissions, and account behavior. A hook owns:

- its domain query key;
- parameter and enabled-state rules;
- response shaping needed by consumers;
- the selected query policy; and
- cache invalidation or removal caused by its mutations.

Pages consume these hooks rather than calling `fetch` or recreating request and
response types. One-off direct use of the typed client remains possible, but
shared domain semantics belong in the named hook layer.

## Server-state storage policy

Query policies separate data by volatility and browser lifetime:

| Storage | Intended use |
| --- | --- |
| Memory | Fast-changing builder, invitation/link, and result-list data that should not survive reload. |
| Session storage | Permissions and management data that may survive navigation and refresh within one browser session. |
| Local storage | Selected user/profile or project-list data intended to warm a later browser session. |

Policies also own stale time, garbage-collection age, automatic-fetch
cooldowns, polling, and focus/reconnect behavior. Mutation invalidation remains
beside the mutation because it describes the consequence of a specific write.

Persisted query state is assigned to one Auth0 subject. A subject change clears
the FlowForm query cache before the new owner is recorded, and logout clears
the cache. This ownership marker prevents routine reuse of one user's FlowForm
query snapshots by a later user of the same browser; it is not encryption or an
authorization control. Persisted query families therefore need deliberate data
review. Fast-changing builder and result-list state remains memory-only, while
selected profile, project, permission, and management data can persist for its
declared browser lifetime.

Auth0 maintains its own browser-local token cache outside the query persistence
layer. Query snapshots should not deliberately copy those tokens or become the
only copy of user work, and authoritative permissions remain on the backend.

## Error and retry behavior

The frontend consumes the backend's normalized `{code, message, details?}`
error contract. Pydantic field failures appear under `details.errors`. Query
retries are conservative, and rate-limit errors are not automatically retried.
Feature code should branch on declared error codes rather than parsing display
messages.

## Related documents

- [[frontend-index|Frontend implementation]]
- [[studio-application|Studio application]]
- [[api-contracts-and-errors|Backend API contracts and errors]]
- [[identity-and-authentication|Identity and authentication]]
- [[generated-files|Generated files]]
