---
title: Repository map
document_type: overview
status: scaffold
authority: canonical
verified_against_commit: ac7d021ad3716a68638759df684b9a3c32bb4389
related_code:
  [
    "../../backend/",
    "../../frontend/",
    "../../infra/",
    "../../scripts/",
    "../../tools/mcp/",
    "../../.github/workflows/",
  ]
related_docs:
  [
    "../README.md",
    "documentation-model.md",
    "../40-implementation/backend.md",
    "../40-implementation/frontend.md",
    "../40-implementation/infrastructure.md",
    "../60-reference/repository-tree.md",
    "../60-reference/scripts-catalogue.md",
    "../60-reference/configuration-catalogue.md",
    "../60-reference/generated-files.md",
  ]
---

# Repository map

Provides a concise guide to the major areas of the FlowForm repository and directs readers to more detailed documentation.

## Scope

This map identifies applications, shared packages, infrastructure, automation, tests, and primary entry points. It does not describe detailed runtime behaviour or domain rules; those belong in architecture, domain, workflow, and implementation documents.

## Major areas

| Area                                                                         | Contents                                                                                                          | Start here                                                                                                                    |
| ---------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `backend/`                                                                   | Python backend application, schemas, repositories, services, scripts, tests, and the checked-in OpenAPI document. | `backend/wsgi.py`, `backend/app/core/factory.py`, `backend/app/api/v1/`, `backend/tests/`                                     |
| `frontend/apps/public-site/`                                                 | Astro public website application.                                                                                 | `frontend/apps/public-site/src/pages/`, `frontend/apps/public-site/astro.config.mjs`                                          |
| `frontend/apps/studio-app/`                                                  | React and Vite Studio application and its frontend tests.                                                         | `frontend/apps/studio-app/src/main.tsx`, `frontend/apps/studio-app/src/lib/router.ts`, `frontend/apps/studio-app/src/routes/` |
| `frontend/packages/`                                                         | Shared workspace packages: `builder`, `schema`, `site-shell`, `styles`, and `ui`.                                 | Each package's `package.json` and exported `src/` entry point                                                                 |
| `infra/cdk/`                                                                 | AWS CDK application, reusable constructs, stacks, environment configuration, and synth-time tests.                | `infra/cdk/app.py`, `infra/cdk/flowform_infra/`, `infra/cdk/tests/`                                                           |
| `infra/docker/`                                                              | Dockerfiles and Compose definitions used for local and test environments.                                         | `infra/docker/docker-compose.dev.yml`, `infra/docker/docker-compose.test.yml`                                                 |
| `infra/postgres/`                                                            | PostgreSQL initialization, schema SQL, configuration, and local mock data.                                        | `infra/postgres/init/`, `infra/postgres/init/schema/`                                                                         |
| `infra/runtime/`                                                             | Host bootstrap, cloud-init templates, runtime Compose definitions, and proxy configuration.                       | `infra/runtime/bootstrap/`, `infra/runtime/compose/`, `infra/runtime/config/`                                                 |
| `infra/images/`, `infra/proxmox/`, `infra/rehearsal/`, `infra/environments/` | Machine-image definitions and provisioning, Proxmox tooling, rehearsal assets, and environment-specific overlays. | The README or top-level scripts in each area                                                                                  |
| `scripts/`                                                                   | Repository-level CI, development, documentation, secret-management, and utility scripts.                          | `scripts/ci/`, `scripts/dev/`, `scripts/docs/`, `scripts/secrets/`, `scripts/tools/`                                          |
| `tools/mcp/`                                                                 | Development MCP server and helpers that expose the backend OpenAPI surface to MCP clients.                        | `tools/mcp/flowform_dev.py`, `tools/mcp/README.md`                                                                            |
| `.github/workflows/`                                                         | Continuous-integration and frontend-deployment workflows.                                                         | `.github/workflows/ci.yml`, `.github/workflows/deploy.yml`                                                                    |
| `docs/`                                                                      | Layered canonical, reference, planning, and generated documentation.                                              | `docs/README.md`                                                                                                              |

## Workspace and test boundaries

`frontend/pnpm-workspace.yaml` defines the frontend workspace as `apps/*` and `packages/*`. Backend tests are grouped under `backend/tests/unit/`, `backend/tests/integration/`, and `backend/tests/e2e/`; Studio tests are under `frontend/apps/studio-app/tests/`; infrastructure checks are under `infra/cdk/tests/` and `infra/tests/`.

## Generated and historical areas

Checked-in generated contracts and types include `backend/openapi.yaml`, `frontend/apps/studio-app/src/api/generated/`, `frontend/apps/studio-app/src/routeTree.gen.ts`, and `frontend/packages/schema/src/generated/`. See [Generated files](../60-reference/generated-files.md) for regeneration ownership.

`old-docs/` is historical and untrusted. It is not an implementation source and its claims must be re-verified before use.

## Where to look next

Use the [repository tree](../60-reference/repository-tree.md) for a compact structural reference, the implementation maps for code locations, the workflow documents for executable processes, and the reference catalogues for scripts and configuration.

## Verification notes

This map was checked against tracked source, manifests, tests, infrastructure definitions, and GitHub workflows at commit `ac7d021ad3716a68638759df684b9a3c32bb4389`. The layered documentation restructure and `scripts/docs/` tooling are uncommitted Stage 1 working-tree work and are not part of that commit.
