---
title: Scripts catalogue
document_type: reference
status: scaffold
authority: canonical
verified_against_commit: null
tags: [tooling]
related_code:
  - "../../scripts/"
  - "../../backend/scripts/"
  - "../../frontend/scripts/"
  - "../../infra/"
  - "../../tools/mcp/"
  - "../../.githooks/"
related_docs:
  - "Commands"
  - "Generated files"
  - "Scripts implementation"
---

# Scripts catalogue

Lists maintained script entry points and package-script aliases without duplicating their operational instructions.

## Reference scope

This catalogue covers repository helper scripts, application-specific helpers, infrastructure automation, developer-tool wrappers, and `package.json` script names. Application modules, test cases, generated outputs, dependency code, and lockfiles are outside its scope.

## Canonical sources

Script files are authoritative for shell, Python, and Node helpers. Each `package.json` is authoritative for its package-script aliases. Executable mode alone is not used to determine inclusion because several maintained scripts are invoked through `bash`, `python3`, or `node`.

## Repository helpers

| Area                         | Paths                                                                                                                                                             | Responsibility                                                                |
| ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| CI contracts                 | `scripts/ci/check-openapi-contracts.sh`, `scripts/ci/sync-openapi.sh`                                                                                             | OpenAPI drift checking and synchronized backend/frontend contract generation. |
| Local development            | `scripts/dev/bootstrap-dev-and-load-mocks.sh`, `scripts/dev/install-git-hooks.sh`, `scripts/dev/load-core-mock-data.sh`, `scripts/dev/load-response-mock-data.sh` | Local bootstrap, repository hook installation, and mock-data loading.         |
| Documentation                | `scripts/docs/generate-repository-tree.py`, `scripts/docs/validate-doc-links.py`, `scripts/docs/validate-doc-metadata.py`                                         | Repository-tree generation and documentation validation.                      |
| Local configuration material | `scripts/secrets/fetch-dev-secrets.sh`, `scripts/secrets/generate-env-files.sh`, `scripts/secrets/generate-secrets.sh`, `scripts/secrets/generate_secrets.py`     | Development and test configuration-file preparation.                          |
| Repository utilities         | `scripts/tools/count_lines.sh`, `scripts/tools/lint-md.sh`                                                                                                        | Source line counting and Markdown linting.                                    |

## Application helpers

| Area     | Paths                                                                                                        | Responsibility                                                                 |
| -------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ |
| Backend  | `backend/scripts/run-tests.sh`, `backend/scripts/run-tests.py`                                               | Backend Docker test runner and its Python implementation.                      |
| Backend  | `backend/scripts/check-integrity-rule-constraints.sh`, `backend/scripts/check_integrity_rule_constraints.py` | Database-constraint and integrity-rule cross-check wrapper and implementation. |
| Backend  | `backend/scripts/export-openapi.sh`                                                                          | Backend OpenAPI export and drift-check wrapper.                                |
| Backend  | `backend/scripts/run_backend_security.sh`                                                                    | Backend dependency and source security checks.                                 |
| Backend  | `backend/scripts/healthcheck.py`                                                                             | Container health-check helper.                                                 |
| Frontend | `frontend/scripts/generate-types.mjs`                                                                        | Generates frontend contract artifacts from `backend/openapi.yaml`.             |

## Infrastructure helpers

| Area                    | Paths                                                                                                                                             | Responsibility                                                          |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| Database initialization | `infra/postgres/init/00-render-and-run.sh`                                                                                                        | Renders and runs PostgreSQL initialization templates.                   |
| Runtime bootstrap       | `infra/runtime/bootstrap/bootstrap-app.sh`, `infra/runtime/bootstrap/bootstrap-proxy.sh`                                                          | App-host and proxy-host bootstrap entry points.                         |
| CDK support             | `infra/platforms/aws/scripts/seed-secrets.sh`                                                                                                    | AWS CDK environment seeding helper.                                     |
| Image factory           | `infra/image-factory/build-proxmox-template.sh`, `infra/image-factory/prepare-proxmox-source.sh`, `infra/image-factory/provisioners/**/*.sh`, `infra/image-factory/manifests/extract-aws-ami-id.sh` | Source preparation, candidate builds, Packer provisioners, and manifest extraction. |
| Image validation        | `infra/tests/images/inspect-layout.sh`, `infra/tests/images/validate.sh`                                                                          | Image-layout and Packer validation helpers.                             |
| Proxmox orchestration   | `infra/platforms/proxmox/*.sh`, `infra/platforms/proxmox/lib/cloud-init-snippets.sh`                                                             | Source import, template smoke checks, and Proxmox host/VM lifecycle.    |
| Rehearsal lifecycle     | `infra/environments/rehearsal/prepare-artifacts.sh`, `infra/environments/rehearsal/activate.sh`, `infra/environments/rehearsal/verify.sh`, `infra/environments/rehearsal/fixtures/localstack/seed-localstack.sh` | Offline artifact preparation, ordered activation, verification, and fixture seeding. |

## Tool-owned helpers

| Path                                                                     | Responsibility                                                    |
| ------------------------------------------------------------------------ | ----------------------------------------------------------------- |
| `.githooks/pre-commit`                                                   | Repository pre-commit entry point for the OpenAPI contract check. |
| `tools/mcp/run.sh`                                                       | FlowForm development MCP launcher.                                |
| `tools/mcp/repomap_run.sh`                                               | Repository-map MCP launcher.                                      |
| `tools/mcp/flowform_dev.py`, `tools/mcp/repomap.py`, `tools/mcp/auth.py` | MCP server entry modules and authentication support.              |
| `.claude/workflows/scripts/new-workflow.sh`                              | Developer-workflow scaffolding helper.                            |
| `.claude/workflows/_template/scripts/session-start.sh`                   | Session-start template for developer workflows.                   |

Instantiated `.claude/workflows/*/scripts/` copies are excluded from this catalogue; the maintained generic scaffolder and template are listed instead.

## Frontend package scripts

### `frontend/package.json`

| Name             | Command                                    |
| ---------------- | ------------------------------------------ |
| `dev:studio`     | `pnpm --filter @flowform/studio-app dev`   |
| `dev:site`       | `pnpm --filter public-site dev`            |
| `build:studio`   | `pnpm --filter @flowform/studio-app build` |
| `build:site`     | `pnpm --filter public-site build`          |
| `generate:types` | `node scripts/generate-types.mjs`          |

### `frontend/apps/studio-app/package.json`

| Name               | Command                                                                                                                                                                    |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `dev`              | `vite`                                                                                                                                                                     |
| `build`            | `tsc -b && vite build`                                                                                                                                                     |
| `lint`             | `eslint .`                                                                                                                                                                 |
| `openapi:export`   | `bash ../../../backend/scripts/export-openapi.sh`                                                                                                                          |
| `openapi:types`    | `openapi-typescript ../../../backend/openapi.yaml -o src/api/generated/schema.ts --root-types --root-types-no-schema-prefix`                                               |
| `openapi:generate` | `pnpm run openapi:export && pnpm run openapi:types && pnpm --dir ../.. run generate:types`                                                                                 |
| `openapi:check`    | `pnpm run openapi:export -- --check && openapi-typescript ../../../backend/openapi.yaml -o src/api/generated/schema.ts --root-types --root-types-no-schema-prefix --check` |
| `preview`          | `vite preview`                                                                                                                                                             |
| `routes`           | `tsr generate`                                                                                                                                                             |
| `test`             | `vitest run`                                                                                                                                                               |
| `test:watch`       | `vitest`                                                                                                                                                                   |
| `test:ui`          | `vitest --ui`                                                                                                                                                              |

### `frontend/apps/public-site/package.json`

| Name      | Command                                         |
| --------- | ----------------------------------------------- |
| `dev`     | `astro dev`                                     |
| `build`   | `astro build`                                   |
| `lint`    | `eslint .`                                      |
| `preview` | `astro preview`                                 |
| `serve`   | `serve dist --config "$PWD/serve.json" --debug` |
| `astro`   | `astro`                                         |

The shared frontend package manifests and `infra/platforms/aws/cdk/package.json` currently define no `scripts` entries.

## Update procedure

Rescan maintained shell, Python, and Node entry points outside dependency and generated directories. Extract package aliases directly from every current `package.json`. Verify descriptions against script headers and invoked commands, then update `verified_against_commit`.

The `scripts/docs/` entries are uncommitted Stage 1 working-tree additions at the recorded implementation baseline. Advance `verified_against_commit` after the documentation tooling is committed and re-verified.

## Related documents

- [[Commands]]
- [[Generated files]]
- [[Scripts implementation]]
