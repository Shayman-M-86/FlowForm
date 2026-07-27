---
title: Local infrastructure
aliases:
  - "Local infrastructure"
document_type: workflow
status: draft
authority: canonical
verified_against_commit: ad26b87e9820
tags: [infrastructure]
related_code:
  - "../../infra/containers/strategies/dev/compose/compose.yml"
  - "../../infra/containers/strategies/dev/compose/compose.test.yml"
  - "../../infra/database/init/"
  - "../../infra/tests/containers/test-container-invariants.sh"
  - "../../frontend/docker-compose.dev.yml"
related_docs:
  - "Local development"
  - "Runtime containers"
  - "Services and ports"
---

# Local infrastructure

Describes the Docker resources used on a developer workstation. Development,
test, frontend-only, split-runtime proof, and rehearsal Compose definitions are
different environments; this workflow covers the first three and does not claim
cloud-equivalent isolation.

## Trigger

Start local infrastructure when backend development needs both PostgreSQL
stores, when the Docker-backed test runner is invoked, or when a containerized
frontend is preferred over the pnpm dev server.

## Preconditions

- Docker Compose v2 is running.
- The gitignored `infra/env/dev/.env` interpolation file and split dev env files
  exist, and the complete secret directory from
  [[secrets-and-configuration|Secrets and configuration]] is available. No
  tracked `.env` template currently bootstraps this from a fresh checkout.
- Ports `5000`, `5432`, and `5433` are free for development. The separate test
  project uses `5010`, `5442`, and `5443`.
- Existing named volumes are understood before any command uses `-v`; removing
  them permanently deletes the local database contents.

## Ordered steps

1. Validate interpolation without starting containers:

   ```bash
   docker compose --env-file infra/env/dev/.env -f infra/containers/strategies/dev/compose/compose.yml config --quiet
   ```

2. Start the development project:

   ```bash
   docker compose --env-file infra/env/dev/.env -f infra/containers/strategies/dev/compose/compose.yml up -d --build
   ```

   Compose creates a `172.30.0.0/16` bridge network, persistent volumes for the
   two PostgreSQL services and backend uv environment, and waits for both
   databases before starting Flask.
3. Run tests through `bash backend/scripts/run-tests.sh --ai`. The runner owns a
   separate Compose project on `172.50.0.0/16`, fingerprints environment/build/
   schema inputs, and resets only the affected test resources. It deliberately
   leaves the healthy test stack running for reuse.
4. Run frontends with pnpm as described in [[local-development|Local
   development]], or use `frontend/docker-compose.dev.yml` for isolated
   frontend containers. That Compose file does not start the backend.
5. Stop development containers while retaining data:

   ```bash
   docker compose --env-file infra/env/dev/.env -f infra/containers/strategies/dev/compose/compose.yml down
   ```

   Add `-v` only for an intentional full database/venv reset.

## Inputs and outputs

The development definition consumes gitignored generated env files, the shared database-init
tree, the backend Dockerfile/source, host AWS login cache, and read-only secret
files. It publishes core PostgreSQL on loopback `5432`, response PostgreSQL on
loopback `5433`, and Flask on host port `5000`. Database initialization creates
separate `core_app` and `response_app` schemas and application roles only on the
first start of each empty volume.

## Failure behaviour

Compose fails early on unresolved variables, invalid mounts, unavailable ports,
or missing secret sources. PostgreSQL init fails on a missing template value or
SQL error; a failed/partial first initialization normally requires inspection
and an intentional disposable-volume reset. The backend health check stays
unhealthy until both databases and required AWS/Auth0 configuration are usable.

The development stack is writable, source-mounted, and co-locates backend and
databases. Passing its health checks does not verify the hardened split-host
runtime, AWS networking, RDS, or the Proxmox rehearsal.

## Verification commands

```bash
docker compose --env-file infra/env/dev/.env -f infra/containers/strategies/dev/compose/compose.yml config --services
docker compose --env-file infra/env/dev/.env -f infra/containers/strategies/dev/compose/compose.yml ps
docker compose --env-file infra/env/dev/.env -f infra/containers/strategies/dev/compose/compose.yml exec -T postgres-core sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
docker compose --env-file infra/env/dev/.env -f infra/containers/strategies/dev/compose/compose.yml exec -T postgres-response sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
curl -fsS http://localhost:5000/api/v1/system/health/ready
bash infra/tests/containers/test-container-invariants.sh
```

The invariant script compares maintained container contracts; it does not start
the stacks or attest a live deployment.

## Related documents

- [[local-development|Local development]]
- [[runtime-containers|Runtime containers]]
- [[services-and-ports|Services and ports]]
