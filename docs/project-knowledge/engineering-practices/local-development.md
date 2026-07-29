---
title: Local development
aliases: ["Local development"]
document_type: workflow
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-30
tags: [tooling, infrastructure]
related_code:
  - "../../../scripts/dev/start-dev-stack.sh"
  - "../../../scripts/secrets/fetch-dev-secrets.sh"
  - "../../../frontend/package.json"
change_triggers:
  - "../../../infra/containers/runtime/development/compose/compose.yml"
  - "../../../infra/env/dev/"
  - "../../../scripts/dev/load-*-mock-data.sh"
related_docs: ["Engineering practices", "Local infrastructure", "Configuration and secrets", "Testing workflow"]
---

# Local development

Local development is the workstation workflow for running and changing the
backend, split PostgreSQL databases, Studio, and public site. It combines a
backend/database Compose project with separate frontend development servers.
Exact commands and secret-delivery details live with the scripts and
infrastructure pages that own them rather than being restated here.

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

The repository development entry point prepares the required local identity,
configuration, and secrets before starting the backend and database runtime.
Frontend development servers run separately against that runtime, and optional
fixtures can populate disposable local data. The owning scripts and Compose
definitions document the exact sequence, mounts, and prerequisites.

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
- [[configuration|Configuration and secrets]]
- [[testing|Testing workflow]]
