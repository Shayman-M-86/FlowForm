---
title: Configuration implementation
aliases:
  - "Configuration implementation"
document_type: implementation
status: draft
authority: canonical
verified_against_commit: null
tags: [configuration]
related_code:
  - "../../backend/app/core/config.py"
  - "../../infra/deployment/config/runtime-parameter-contract.json"
  - "../../infra/deployment/aws/cdk/flowform_infra/config/environments.py"
  - "../../infra/deployment/bootstrap/"
  - "../../infra/containers/runtime/"
  - "../../infra/containers/strategies/dev/"
  - "../../scripts/secrets/"
related_docs:
  - "Secrets and configuration"
  - "Configuration catalogue"
  - "Environment variables"
  - "Configuration index"
---

# Configuration implementation

Maps configuration concepts to verified repository implementation.

## Directory ownership

- `backend/app/core/config.py` owns the typed backend runtime model, nested
  environment-variable mapping, defaults, validation errors, and mounted-file
  loading for application and database secrets.
- `infra/deployment/config/runtime-parameter-contract.json` owns the shared
  parameter names consumed by AWS CDK, Proxmox Terraform, LocalStack seeding,
  and host bootstrap.
- `infra/deployment/aws/cdk/flowform_infra/config/environments.py` owns typed
  dev, staging, production, and shared security-scope deployment data.
- `infra/env/` holds local per-environment values and gitignored secret files;
  maintained examples live beside CDK, Packer, Terraform, and image scripts.
- Compose, cloud-init, bootstrap scripts, and frontend build commands own the
  final mapping from maintained configuration into each process.

## Entry points

- `get_settings()` is called by the Flask application factory and requires a
  valid `FLOWFORM_ENV` before constructing nested Pydantic settings.
- `get_env_config()` is called by `infra/deployment/aws/cdk/app.py` for the CDK
  context selected by `-c env=<name>` or `CDK_ENV`.
- Proxmox `terraform/locals.tf` reads the runtime-parameter contract, checks the
  exact rehearsal seed-key set, and renders role-specific cloud-init.
- `bootstrap-app.sh`, `bootstrap-proxy.sh`, and `bootstrap-db.sh` fetch runtime
  parameters or secrets and materialize the files consumed by shared Compose.
- `scripts/secrets/` generates local throwaways, fetches persistent development
  secrets, and builds the development environment files.

## Important modules

`DatabaseSettings` accepts either a full PostgreSQL URL or validated parts and
supports password files. `Auth0Settings`, `AppSettings`, `AwsSettings`,
`EncryptionSettings`, `EmailSettings`, and logging/server/rate-limit models form
the remaining backend boundary. `EnvConfig` controls which CDK stacks exist and
their environment-specific lifecycle; `SecurityScopeConfig` separates the
shared non-production security namespace from production.

The runtime-parameter contract separates scoped values, backend/proxy runtime
groups, and secret resource names. Its rehearsal seed-key set is non-secret;
managed secret values use the separate deploy-time sync path. Consumers derive
paths from the contract instead of maintaining independent SSM name lists.

## Dependency direction

Maintained models, contracts, examples, and templates feed generators or
bootstrap steps; generated local env files, mounted secret files, SSM values,
and cloud-init then feed application and container consumers. Runtime code does
not write back to the canonical models. Confidential values are generally
intended to travel through secret files or Secrets Manager, while identifiers
and ordinary runtime settings use environment files or SSM parameters. The
Grafana token follows the proxy's file-backed observability secret path; only
its URL and user remain in the proxy SSM parameter group.

## Generated versus handwritten code

Settings models, the runtime contract, Compose files, Terraform/CDK source, and
`.example` files are handwritten. Local `.env*`, `*.secret.txt`, Packer variable
files, Terraform variables/state, rendered cloud-init, and CDK output are local
or generated artifacts and are not configuration authority. Terraform state and
rendered user data must be treated as sensitive because they can contain
materialized configuration.

## Tests and validation

- Backend unit and integration tests exercise settings validation and
  environment assembly through the application factory.
- `infra/deployment/aws/cdk/tests/test_environments.py` and
  `test_runtime_parameter_contract.py` cover typed deployment configuration and
  contract-derived parameter names.
- `infra/tests/deployment/test-localstack-seed.sh` checks that Terraform,
  bootstrap, and LocalStack agree on the contract and rehearsal boundaries.
- `docker compose ... config`, `terraform validate`, and CDK synth are the
  executable validation boundaries for their respective consumers.

## Known gaps

The generated [[configuration-index|Configuration index]] remains a scaffold;
the maintained [[environment-variables|Environment variables]] reference is a
curated draft rather than an exhaustive generated inventory. No single generated
catalogue currently proves that every consumer is represented. Configuration
is also split across local development, Proxmox rehearsal, and incomplete AWS
deployment paths; a valid configuration for one path is not proof that another
path is operational.

## Related documents

- [[secrets-and-configuration|Secrets and configuration]]
- [[configuration-catalogue|Configuration catalogue]]
- [[environment-variables|Environment variables]]
- [[configuration-index|Configuration index]]
