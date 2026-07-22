---
title: Local development
aliases:
  - "Local development"
document_type: workflow
status: draft
authority: canonical
verified_against_commit: ad26b87e9820
related_code:
  - "../../infra/containers/strategies/dev/compose/compose.yml"
  - "../../infra/env/dev/"
  - "../../scripts/secrets/fetch-dev-secrets.sh"
  - "../../scripts/dev/load-*-mock-data.sh"
  - "../../frontend/package.json"
related_docs:
  - "Local infrastructure"
  - "Secrets and configuration"
  - "Testing workflow"
  - "Commands"
---

# Local development

Describes the current workstation loop for the Flask backend, split PostgreSQL
databases, Studio, and public site. The backend/database Compose project and the
two frontend dev servers are separate processes.

## Trigger

Run this workflow after a fresh checkout, after a reboot clears the runtime
secret tmpfs, or whenever local backend, database, or frontend work needs the
corresponding service running.

## Preconditions

- Docker with Compose v2, AWS CLI v2, Git, Node `22.12+`, and pnpm `10.24.0`
  are available. uv is required for host-side backend checks and the test
  runner.
- `XDG_RUNTIME_DIR` exists on tmpfs. The secret-fetch script refuses `/tmp` or
  any disk-backed destination.
- The gitignored `infra/env/dev/.env` Compose interpolation file and the split
  `.backend.env`/`.db.*.env` files exist. There is no tracked `.env` template;
  `generate-env-files.sh` emits only the three split files and is incomplete
  for a fresh local setup at this baseline.
- `aws login --profile flowform-dev` can read
  `flowform/nonprod/app-secrets`; machine-local generated dev configuration
  identifies the Auth0, KMS, linkage-secret, email, and database settings.
- Local database password files remain paired with the PostgreSQL volumes they
  initialized. Rotating those throwaway passwords requires recreating the
  corresponding volumes.

## Ordered steps

1. Authenticate and assemble persistent AWS values plus machine-local database
   passwords into runtime tmpfs:

   ```bash
   export AWS_PROFILE=flowform-dev
   aws login --profile "$AWS_PROFILE"
   scripts/secrets/fetch-dev-secrets.sh
   export FLOWFORM_SECRET_DIR="${XDG_RUNTIME_DIR}/flowform-secrets"
   ```

2. Render-check and start the backend plus core and response databases:

   ```bash
   docker compose --env-file infra/env/dev/.env -f infra/containers/strategies/dev/compose/compose.yml config --quiet
   docker compose --env-file infra/env/dev/.env -f infra/containers/strategies/dev/compose/compose.yml up -d --build
   ```

3. On a freshly initialized, disposable database, optionally load the maintained
   fixture rows once:

   ```bash
   scripts/dev/load-core-mock-data.sh
   scripts/dev/load-response-mock-data.sh
   ```

4. Install frontend dependencies once, then start either or both dev servers in
   separate terminals. Set an explicit API URL when Studio should call the
   local backend instead of any machine-local `.env` configuration:

   ```bash
   cd frontend
   pnpm install --frozen-lockfile
   VITE_API_BASE_URL=http://localhost:5000 pnpm run dev:studio
   pnpm run dev:site
   ```

5. Edit backend or frontend source. Compose bind-mounts `backend/` into the
   debug Flask container; Vite/Astro watch their application and workspace
   package sources.

## Inputs and outputs

Inputs are gitignored generated dev env files, AWS login state, runtime secret
files, source, and optional mock SQL. Durable local outputs include Docker images, PostgreSQL
volumes, the backend uv volume, frontend `node_modules`, and build-tool caches.
Fetched application/Auth0 secrets live only in the selected tmpfs; local
database passwords remain in gitignored `infra/env/dev/secrets/` so they survive
reboots with their volumes.

## Failure behaviour

- Re-run `aws login` and the fetch script when AWS login expires or after a
  reboot. The fetch script fails closed if its destination is not tmpfs or any
  expected value is missing.
- Missing/mismatched secret files prevent Compose or application startup.
  Inspect `docker compose ... logs <service>` before recreating volumes.
- Initialization SQL runs only for empty PostgreSQL volumes. Use the destructive
  `down -v` reset only for confirmed disposable data; see
  [[database-migrations|Database migrations]].
- `frontend/apps/studio-app/.env` is machine-local and gitignored. Confirm its
  `VITE_API_BASE_URL` or use the explicit local override above.
- The checked-in VS Code Compose tasks and
  `scripts/dev/bootstrap-dev-and-load-mocks.sh` do not supply the current
  canonical env-file/path combination. Use the commands above at this baseline.

## Verification commands

```bash
docker compose --env-file infra/env/dev/.env -f infra/containers/strategies/dev/compose/compose.yml ps
curl -fsS http://localhost:5000/api/v1/system/health/ready
curl -fsSI http://localhost:5174/
curl -fsSI http://localhost:4321/
```

Verify only the services started for the current task. The backend readiness
route checks application reachability and both configured databases; frontend HTTP
checks do not prove authentication or API integration.

## Related documents

- [[local-infrastructure|Local infrastructure]]
- [[secrets-and-configuration|Secrets and configuration]]
- [[testing|Testing workflow]]
- [[commands|Commands]]
