---
title: Local infrastructure
aliases: ["Local infrastructure"]
document_type: workflow
status: verified
authority: canonical
verified_evidence_digest: sha256:4502de4900ed8b8f89b88e4fb7f6fea232838cb77c86db6a5a6f458c97850206
tags: [infrastructure, configuration]
related_code:
  - "../../../infra/containers/strategies/dev/compose/"
  - "../../../infra/database/"
  - "../../../frontend/docker-compose.dev.yml"
related_docs:
  - "Infrastructure knowledge"
  - "Secrets and configuration"
---

# Local infrastructure

The development and test Compose definitions are separate from the shared
runtime and rehearsal stacks. Development starts two PostgreSQL services and a
source-mounted backend; the frontend Compose definition starts frontend
containers only.

```text
development
  |
  +--> Compose: backend + core PostgreSQL + response PostgreSQL
  |
  +--> separate frontend Compose/dev servers
  |
  +--> named volumes: database data + backend environment

test
  |
  +--> isolated Compose network and disposable test services
```

## Development stack

Validate and start the stack with its ignored environment file:

```sh
docker compose --env-file infra/env/dev/.env \
  -f infra/containers/strategies/dev/compose/compose.yml config --quiet
docker compose --env-file infra/env/dev/.env \
  -f infra/containers/strategies/dev/compose/compose.yml up -d --build
```

The development services bind PostgreSQL to loopback ports 5432 and 5433 and
the backend to port 5000. PostgreSQL data and the backend development virtual
environment use named volumes. Both database services mount the shared init
tree and read password files from a read-only `/run/secrets` directory. The
backend waits for database health checks and also mounts the host AWS login
configuration/cache.

Stop containers without deleting named volumes with the matching `down`
command. Adding `-v` removes those volumes and is an intentional local database
reset.

## Test and frontend stacks

`compose.test.yml` is a separate internal network and uses loopback ports 5442,
5443, and 5010. Its backend sets `FLOWFORM_ENV=test`, uses a direct throwaway
Auth0 management secret, clears the inherited file setting, and disables
management validation. It must not be used as evidence that the development or
deployed stack is healthy.

`frontend/docker-compose.dev.yml` defines public-site and Studio containers;
it does not start the backend or databases.

## Related documents

- [[infrastructure-index|Infrastructure knowledge]]
- [[secrets-and-configuration|Secrets and configuration]]
