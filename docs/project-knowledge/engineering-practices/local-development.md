---
title: Local development
aliases: ["Local development"]
document_type: workflow
status: draft
authority: canonical
verified_against_commit: null
tags: [tooling, infrastructure]
related_code:
  - "../../../infra/containers/strategies/dev/compose/compose.yml"
  - "../../../infra/env/dev/"
  - "../../../scripts/secrets/fetch-dev-secrets.sh"
  - "../../../scripts/dev/load-*-mock-data.sh"
  - "../../../frontend/package.json"
related_docs: ["Engineering practices", "Local infrastructure", "Secrets and configuration", "Testing workflow"]
---

# Local development

Local development is the workstation workflow for running and changing the
backend, split PostgreSQL databases, Studio, and public site. It combines a
backend/database Compose project with separate frontend development servers.
The exact setup remains draft until commands and secret-delivery assumptions
are rechecked against the current checkout.

```text
source + local configuration + runtime secrets
                    |
          +---------+---------+
          |                   |
          v                   v
 backend + databases    frontend dev servers
      in Compose         Studio / Public Site
          |                   |
          +---------+---------+
                    v
              local smoke checks
```

## Working model

Legacy workflow first obtains an AWS login and assembles required development
values into a runtime secret directory, then render-checks and starts
`infra/containers/strategies/dev/compose/compose.yml`. Disposable mock data may
be loaded into fresh databases. Frontend dependencies are installed from
`frontend/`, and Studio/public-site servers run separately. Backend source is
bind-mounted into the development container while frontend tools watch their
application and shared-package sources.

## Inputs, state, and recovery

Inputs include gitignored development environment files, login state, runtime
secret files, source, and optional mock SQL. Durable local state can include
images, database volumes, dependencies, and build caches. Treat a volume reset
as destructive and use it only for confirmed disposable data.

When login expires or runtime secrets disappear, refresh the login and rerun
the repository secret-fetch workflow. Diagnose configuration and service
failures through rendered Compose configuration and targeted service logs before
recreating state. Infrastructure pages own the current secret and container
boundary rather than this workflow duplicating it.

## Validation boundary

The retained workflow uses Compose status, backend readiness, and frontend HTTP
checks as smoke checks. They establish selected process reachability, not
authentication correctness, end-to-end integration, or production equivalence.
Use [[testing|Testing workflow]] for broader component checks.

## Related documents

- [[engineering-practices-index|Engineering practices]]
- [[local-infrastructure|Local infrastructure]]
- [[secrets-and-configuration|Secrets and configuration]]
- [[testing|Testing workflow]]
