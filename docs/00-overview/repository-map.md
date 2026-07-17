---
title: Repository map
document_type: overview
status: draft
authority: canonical
verified_against_commit: null
related_code:
  - "../../backend/"
  - "../../frontend/"
  - "../../infra/"
  - "../../scripts/"
  - "../../tools/mcp/"
  - "../../.github/workflows/"
related_docs:
  - "FlowForm documentation home"
  - "Documentation model"
  - "Backend implementation"
  - "Frontend implementation"
  - "Infrastructure implementation"
  - "Repository tree"
  - "Scripts catalogue"
  - "Configuration catalogue"
  - "Generated files"
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
| `infra/containers/`                                                          | Docker and Compose service definitions, split by stage: `dev/`, `deployment/` (shared proxy/app host runtime), and `rehearsal/` (LocalStack, registry, TLS shim). | `infra/containers/dev/compose/`, `infra/containers/deployment/compose/`, `infra/containers/rehearsal/compose/`                |
| `infra/database/`                                                            | PostgreSQL initialization, schema SQL, configuration, and local mock data.                                        | `infra/database/init/`, `infra/database/init/schema/`                                                                         |
| `infra/images/`                                                             | Packer machine-image construction: shared AWS/Proxmox golden builds, a Proxmox LocalStack fixture, build scripts, and the image contract. | `infra/images/packer/README.md`, `infra/images/scripts/`, `infra/images/IMAGE-CONTRACT.md`                                  |
| `infra/deployment/`                                                          | Platform deployment: `aws/cdk/` (AWS CDK app, constructs, stacks, synth-time tests), `proxmox/` (Terraform VMs, host bootstrap, cloud-init), and shared `bootstrap/` host scripts. | `infra/deployment/aws/cdk/app.py`, `infra/deployment/proxmox/README.md`, `infra/deployment/bootstrap/`                       |
| `infra/env/`                                                                 | Per-environment (`dev`, `test`, `live`) configuration values and secret files consumed by Compose and bootstrap. | `infra/env/dev/`, `infra/env/<env>/secrets/`                                                                                  |
| `scripts/`                                                                   | Repository-level CI, development, documentation, secret-management, and utility scripts.                          | `scripts/ci/`, `scripts/dev/`, `scripts/docs/`, `scripts/secrets/`, `scripts/tools/`                                          |
| `tools/mcp/`                                                                 | Development MCP server and helpers that expose the backend OpenAPI surface to MCP clients.                        | `tools/mcp/flowform_dev.py`, `tools/mcp/README.md`                                                                            |
| `.github/workflows/`                                                         | Continuous-integration and frontend-deployment workflows.                                                         | `.github/workflows/ci.yml`, `.github/workflows/deploy.yml`                                                                    |
| `docs/`                                                                      | Layered canonical, reference, planning, and generated documentation.                                              | `docs/README.md`                                                                                                              |

## Workspace and test boundaries

`frontend/pnpm-workspace.yaml` defines the frontend workspace as `apps/*` and `packages/*`. Backend tests are grouped under `backend/tests/unit/`, `backend/tests/integration/`, and `backend/tests/e2e/`; Studio tests are under `frontend/apps/studio-app/tests/`; infrastructure checks are under `infra/deployment/aws/cdk/tests/` and `infra/tests/`.

## Generated and historical areas

Checked-in generated contracts and types include `backend/openapi.yaml`, `frontend/apps/studio-app/src/api/generated/`, `frontend/apps/studio-app/src/routeTree.gen.ts`, and `frontend/packages/schema/src/generated/`. See [[Generated files]] for regeneration ownership.

`old-docs/` is historical and untrusted. It is not an implementation source and its claims must be re-verified before use.

## Where to look next

Use the [[Repository tree|repository tree]] for a compact structural reference, the implementation maps for code locations, the workflow documents for executable processes, and the reference catalogues for scripts and configuration.

## Verification notes

The `infra/` rows were rechecked against the current working tree after the
capability-first infrastructure reorganization (`containers/`, `database/`,
`images/`, `deployment/`, `env/`). The remainder of this map still needs a
complete repository-wide verification before this document can return to
`verified` status.
