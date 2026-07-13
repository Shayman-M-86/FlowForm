---
title: Repository map
document_type: overview
status: verified
authority: canonical
verified_against_commit: ed0fb65df856e18807ee243b4bca512a8d0442b0
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
| `infra/platforms/aws/cdk/`                                                   | AWS CDK application, reusable constructs, stacks, environment configuration, and synth-time tests.                | `infra/platforms/aws/cdk/app.py`, `infra/platforms/aws/cdk/flowform_infra/`, `infra/platforms/aws/cdk/tests/`               |
| `infra/environments/development/`, `infra/tests/compose/`                   | Development and test container definitions.                                                                        | Development and test Compose files within their respective execution contexts.                                                  |
| `infra/postgres/`                                                            | PostgreSQL initialization, schema SQL, configuration, and local mock data.                                        | `infra/postgres/init/`, `infra/postgres/init/schema/`                                                                         |
| `infra/runtime/`                                                             | Host bootstrap, cloud-init templates, runtime Compose definitions, and proxy configuration.                       | `infra/runtime/bootstrap/`, `infra/runtime/compose/`, `infra/runtime/config/`                                                 |
| `infra/image-factory/`, `infra/platforms/`, `infra/runtime/`, `infra/environments/` | Image construction, platform orchestration, post-boot runtime, and environment-specific topology. | `infra/README.md` and the README in each ownership area |
| `scripts/`                                                                   | Repository-level CI, development, documentation, secret-management, and utility scripts.                          | `scripts/ci/`, `scripts/dev/`, `scripts/docs/`, `scripts/secrets/`, `scripts/tools/`                                          |
| `tools/mcp/`                                                                 | Development MCP server and helpers that expose the backend OpenAPI surface to MCP clients.                        | `tools/mcp/flowform_dev.py`, `tools/mcp/README.md`                                                                            |
| `.github/workflows/`                                                         | Continuous-integration and frontend-deployment workflows.                                                         | `.github/workflows/ci.yml`, `.github/workflows/deploy.yml`                                                                    |
| `docs/`                                                                      | Layered canonical, reference, planning, and generated documentation.                                              | `docs/README.md`                                                                                                              |

## Workspace and test boundaries

`frontend/pnpm-workspace.yaml` defines the frontend workspace as `apps/*` and `packages/*`. Backend tests are grouped under `backend/tests/unit/`, `backend/tests/integration/`, and `backend/tests/e2e/`; Studio tests are under `frontend/apps/studio-app/tests/`; infrastructure checks are under `infra/platforms/aws/cdk/tests/` and `infra/tests/`.

## Generated and historical areas

Checked-in generated contracts and types include `backend/openapi.yaml`, `frontend/apps/studio-app/src/api/generated/`, `frontend/apps/studio-app/src/routeTree.gen.ts`, and `frontend/packages/schema/src/generated/`. See [[Generated files]] for regeneration ownership.

`old-docs/` is historical and untrusted. It is not an implementation source and its claims must be re-verified before use.

## Where to look next

Use the [[Repository tree|repository tree]] for a compact structural reference, the implementation maps for code locations, the workflow documents for executable processes, and the reference catalogues for scripts and configuration.

## Verification notes

This map was checked against tracked source, manifests, tests, infrastructure definitions, and GitHub workflows at commit `ed0fb65df856e18807ee243b4bca512a8d0442b0`. The layered documentation restructure and current `scripts/docs/` tooling are uncommitted Stage 1 working-tree work and are not part of that commit.
