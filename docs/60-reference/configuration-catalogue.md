---
title: Configuration catalogue
document_type: reference
status: scaffold
authority: canonical
verified_against_commit: null
tags: [configuration]
related_code:
  - "../../backend/app/core/config.py"
  - "../../backend/gunicorn.conf.py"
  - "../../backend/pyproject.toml"
  - "../../.dockerignore"
  - "../../frontend/"
  - "../../infra/"
  - "../../.github/workflows/"
  - "../../.vscode/"
related_docs:
  - "Environment variables"
  - "Configuration implementation"
  - "Secrets and configuration"
  - "Configuration index"
---

# Configuration catalogue

Lists the maintained configuration families, templates, and repository areas that own them.

## Reference scope

This catalogue records configuration locations and ownership boundaries. It does not enumerate individual environment variables, credentials, service ports, or runtime procedures.

## Canonical sources

Configuration files, application settings modules, Compose definitions, infrastructure definitions, and CI workflows are authoritative for their own area. Example and template files define file shape only; generated or local copies are not canonical.

## Configuration families

| Family                         | Canonical locations                                                                                                                                               | Owner                                                                                        |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Repository automation          | `.github/workflows/*.yml`, `.cfnlintrc.yaml`, `.githooks/`                                                                                                        | Repository CI and validation.                                                                |
| Repository developer tools     | `.vscode/`, `.claude/`, `.codex/`, `.mcp.json`                                                                                                                    | Repository-local editor, agent, workflow, and MCP tooling.                                   |
| Backend application settings   | `backend/app/core/config.py`                                                                                                                                      | Backend runtime configuration model.                                                         |
| Backend process server         | `backend/gunicorn.conf.py`                                                                                                                                        | Gunicorn server configuration consumed by container runtime definitions.                     |
| Backend Python tooling         | `backend/pyproject.toml`, `backend/pyrightconfig.json`                                                                                                            | Backend dependencies, tests, linting, formatting, and type checking.                         |
| OpenAPI linting                | `backend/.redocly.yaml`                                                                                                                                           | Backend OpenAPI lint policy.                                                                 |
| Frontend workspace             | `frontend/package.json`, `frontend/pnpm-workspace.yaml`, `frontend/tsconfig.base.json`                                                                            | Frontend workspace ownership and shared TypeScript defaults.                                 |
| Frontend applications          | `frontend/apps/*/package.json`, app `tsconfig*.json`, `vite.config*.ts`, `astro.config.mjs`, `eslint.config.js`, `serve.json`, `components.json`                  | Application-specific build and development tooling.                                          |
| Shared frontend packages       | `frontend/packages/*/package.json`, package `tsconfig.json`, `frontend/packages/ui/components.json`                                                               | Package metadata and package-specific TypeScript/component configuration.                    |
| Development container environment | `infra/environments/development/compose/`                                                                                                                            | Integrated local and local-proof container configuration.                                    |
| Test container environment     | `infra/tests/compose/`                                                                                                                                               | Test-only Compose stack and Dockerfile.                                                       |
| Frontend-only local containers | `frontend/docker-compose.dev.yml`, frontend app `Dockerfile*` files                                                                                               | Frontend-local container configuration.                                                      |
| Runtime container deployment   | `infra/runtime/compose/`, `infra/runtime/config/`, `infra/runtime/cloud-init/`                                                                                    | Shared runtime Compose, service configuration, and cloud-init templates.                     |
| Rehearsal environment          | `infra/environments/rehearsal/compose/`, `infra/environments/rehearsal/fixtures/`, `infra/environments/rehearsal/artifacts/images.lock`                             | Rehearsal overrides, fixture configuration, and digest-pinned offline image inputs.           |
| PostgreSQL initialization      | `infra/postgres/init/templates/`, `infra/postgres/init/schema/`, `infra/postgres/config/`                                                                         | Database initialization templates, persisted schemas, and PostgreSQL access configuration.   |
| Image factory                  | `infra/image-factory/packer/*.pkr.hcl`, `infra/image-factory/packer/variables/*.example`, `infra/image-factory/sources/*.lock`                                      | Packer definitions, local variable examples, and pinned source-image inputs.                  |
| AWS CDK                        | `infra/platforms/aws/cdk/cdk.json`, `infra/platforms/aws/cdk/cdk.context.json`, `infra/platforms/aws/cdk/flowform_infra/config/environments.py`, `infra/platforms/aws/cdk/pyproject.toml`, `infra/platforms/aws/cdk/pyrightconfig.json` | CDK entry configuration, cached lookup context, environment definitions, and Python tooling. |
| MCP tools                      | `tools/mcp/pyproject.toml`, `.mcp.json`                                                                                                                           | MCP server dependencies and repository registration.                                         |
| Docker build context           | `.dockerignore`                                                                                                                                                   | Repository-wide Docker build-context exclusions.                                             |

## Maintained templates and examples

| Path                                                           | Produces or guides                                                                            |
| -------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `infra/platforms/aws/cdk/.env.dev.example`                     | Gitignored `infra/platforms/aws/cdk/.env.<env>` files consumed by CDK configuration and its seeding helper. |
| `infra/image-factory/packer/variables/aws.auto.pkrvars.hcl.example` | Local AWS Packer variable file.                                                           |
| `infra/image-factory/packer/variables/proxmox.auto.pkrvars.hcl.example` | Local Proxmox Packer variable file.                                                 |
| `infra/runtime/cloud-init/*.user-data.yaml.template`           | Rendered runtime cloud-init user data.                                                        |
| `infra/postgres/init/templates/**/*.sql`                       | Rendered PostgreSQL initialization SQL.                                                       |

## Update procedure

Rescan current configuration filenames and directories while excluding dependencies, virtual environments, generated build output, and `old-docs/`. Confirm ownership from direct consumers or adjacent entry points. Add new template families only when their maintained source and consumer can both be identified.

## Related documents

- [[Environment variables]]
- [[Configuration implementation]]
- [[Secrets and configuration]]
- [[Configuration index]]
