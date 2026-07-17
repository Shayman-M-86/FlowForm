---
title: Configuration catalogue
document_type: reference
status: scaffold
authority: canonical
verified_against_commit: ac7d021ad3716a68638759df684b9a3c32bb4389
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
| Development container environment | `infra/containers/dev/compose/compose.yml`                                                                                                                           | Integrated local and local-proof container configuration.                                    |
| Test container environment     | `infra/containers/dev/compose/compose.test.yml`, `infra/containers/dev/services/backend/`                                                                            | Test-only Compose stack and Dockerfile.                                                       |
| Frontend-only local containers | `frontend/docker-compose.dev.yml`, frontend app `Dockerfile*` files                                                                                               | Frontend-local container configuration.                                                      |
| Runtime container deployment   | `infra/containers/deployment/compose/`, `infra/containers/deployment/services/`, `infra/deployment/proxmox/terraform/cloud-init/`                                  | Shared runtime Compose, service configuration, and cloud-init templates.                     |
| Rehearsal environment          | `infra/containers/rehearsal/compose/`, `infra/containers/rehearsal/services/`                                                                                        | Rehearsal overrides and fixture configuration.                                               |
| Per-environment values         | `infra/env/dev/`, `infra/env/test/`, `infra/env/live/`                                                                                                            | Environment-specific configuration values and secret files consumed by Compose and bootstrap. |
| PostgreSQL initialization      | `infra/database/init/templates/`, `infra/database/init/schema/`, `infra/database/config/`                                                                         | Database initialization templates, persisted schemas, and PostgreSQL access configuration.   |
| Packer image build             | `infra/images/packer/**/*.pkr.hcl`, `infra/images/packer/variables/*.pkrvars.hcl.example`, `infra/images/scripts/.env.example`                                   | Shared golden and Proxmox fixture definitions plus local examples for source preparation and selected builds. |
| Proxmox Terraform deployment   | `infra/deployment/proxmox/terraform/*.tf`, `infra/deployment/proxmox/terraform/terraform.tfvars.example`                                                           | Proxmox API, clone, cloud-init, and guest-access configuration; real variables and state are local-only. |
| AWS CDK                        | `infra/deployment/aws/cdk/cdk.json`, `infra/deployment/aws/cdk/cdk.context.json`, `infra/deployment/aws/cdk/flowform_infra/config/environments.py`, `infra/deployment/aws/cdk/pyproject.toml`, `infra/deployment/aws/cdk/pyrightconfig.json` | CDK entry configuration, cached lookup context, environment definitions, and Python tooling. |
| MCP tools                      | `tools/mcp/pyproject.toml`, `.mcp.json`                                                                                                                           | MCP server dependencies and repository registration.                                         |
| Docker build context           | `.dockerignore`                                                                                                                                                   | Repository-wide Docker build-context exclusions.                                             |

## Maintained templates and examples

| Path                                                           | Produces or guides                                                                            |
| -------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `infra/deployment/aws/cdk/.env.dev.example`                     | Gitignored `infra/deployment/aws/cdk/.env.<env>` files consumed by CDK configuration and its seeding helper. |
| `infra/images/packer/variables/aws.auto.pkrvars.hcl.example` | Local AWS Packer variable file. |
| `infra/images/packer/variables/proxmox.auto.pkrvars.hcl.example` | Local Proxmox Packer variable file. |
| `infra/images/scripts/.env.example` | Local source-template preparation configuration. |
| `infra/deployment/proxmox/terraform/terraform.tfvars.example` | Local Terraform deployment configuration. |
| `infra/deployment/proxmox/terraform/cloud-init/*.user-data.yaml.template` | Terraform-rendered Proxmox cloud-init payloads. |
| `infra/database/init/templates/**/*.sql`                       | Rendered PostgreSQL initialization SQL.                                                       |

For Proxmox source preparation, `PROXMOX_SOURCE_DISK_SIZE=native`
preserves the pinned QCOW2 virtual size (currently 25 GiB), while
`PROXMOX_DISK_MAX_SIZE=25G` is the independent upper-bound check. Set an
explicit larger source size only when capacity requirements justify it, and
raise the maximum in the same reviewed change.

## Update procedure

Rescan current configuration filenames and directories while excluding dependencies, virtual environments, generated build output, and `old-docs/`. Confirm ownership from direct consumers or adjacent entry points. Add new template families only when their maintained source and consumer can both be identified.

## Related documents

- [[Environment variables]]
- [[Configuration implementation]]
- [[Secrets and configuration]]
- [[Configuration index]]
