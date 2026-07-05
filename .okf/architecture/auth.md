---
type: Architecture Decision
title: Authentication and authorization
description: Auth0-issued RS256 JWTs verified against JWKS on the backend; project/survey-level RBAC layered on top.
tags: [backend, frontend, auth, security]
timestamp: 2026-07-01T00:00:00Z
---

# Overview

FlowForm uses [Auth0](https://auth0.com) as the identity provider on both
sides of the stack.

**Backend:** Flask middleware verifies Bearer tokens against Auth0 JWKS,
stores claims on `flask.g`, and exposes the subject via
`auth.get_current_user_sub()`. Routes are protected with
`@auth.require_auth(scope)` or left public with `@auth.optional_auth()`. See
[backend/app/api/v1/](/backend/api-v1.md) for where these decorators are applied.

**Frontend (Studio):** Auth0 handles the login/session flow; a bootstrap
workflow under `src/auth/bootstrap/` establishes the current-user context
after login. See [Studio app](/apps/studio-app.md).

On top of authentication, FlowForm layers project-level and survey-level
role-based access control (RBAC), so different team members can have
different permissions on the same project or survey.

# Why this matters

Separating authentication (who is this) from RBAC (what can they do on this
project/survey) lets FlowForm support teams where access needs differ per
project — a prerequisite for the [two-database privacy model](/architecture/two-database-model.md)
to be meaningful.

# Citations

[1] [backend/CLAUDE.md — Auth](../../backend/CLAUDE.md)
[2] [frontend/apps/studio-app/CLAUDE.md — auth.md reference](../../frontend/apps/studio-app/CLAUDE.md)
