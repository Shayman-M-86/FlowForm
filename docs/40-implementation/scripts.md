---
title: Scripts implementation
aliases:
  - "Scripts implementation"
document_type: implementation
status: draft
authority: canonical
verified_against_commit: ad26b87e9820
tags: [tooling]
related_code:
  - "../../scripts/"
  - "../../backend/scripts/"
  - "../../frontend/scripts/"
  - "../../infra/images/scripts/"
  - "../../infra/deployment/bootstrap/"
  - "../../infra/deployment/proxmox/scripts/"
  - "../../tools/mcp/"
related_docs:
  - "Scripts catalogue"
  - "Commands"
  - "Repository map"
  - "Generated files"
---

# Scripts implementation

Maps scripts concepts to verified repository implementation.

## Directory ownership

- `scripts/ci/` coordinates OpenAPI contract generation and drift checks;
  `scripts/dev/` owns local bootstrap and mock-data loading;
  `scripts/secrets/` owns local configuration material; `scripts/docs/` owns
  documentation generation, validation, Docsys, and vault synchronization.
- `backend/scripts/` owns backend tests, health, security, OpenAPI export, and
  database-rule checks. `frontend/scripts/` owns frontend contract generation.
- Infrastructure-local scripts remain with their lifecycle owner under
  `infra/images/`, `infra/deployment/`, `infra/containers/strategies/`, and
  `infra/tests/` rather than moving into the repository-level directory.
- `tools/mcp/` owns development MCP launchers and server entry modules;
  `.githooks/pre-commit` is the repository hook entry point.

## Entry points

The primary coordination entries are `scripts/ci/sync-openapi.sh`,
`scripts/dev/bootstrap-dev-and-load-mocks.sh`,
`scripts/secrets/fetch-dev-secrets.sh`, and the validators under
`scripts/docs/`. Application-specific entries include
`backend/scripts/run-tests.sh` and `frontend/scripts/generate-types.mjs`.
Image build, host bootstrap, Proxmox verification, and rehearsal image-push
scripts are operator-facing and can change external state; their headers and
linked workflows define their preconditions.

## Important modules

- `scripts/ci/check-openapi-contracts.sh` coordinates a drift check;
  `sync-openapi.sh` exports the backend contract, regenerates
  TypeScript/RBAC/schema files in the worktree, checks their diff, and runs
  Redocly lint. Check mode can therefore leave generated files modified when
  drift exists.
- `backend/scripts/run-tests.py` fingerprints schema, build, and environment
  inputs and manages the persistent Docker test stack behind a small shell
  wrapper.
- `scripts/secrets/generate_secrets.py` creates non-overwriting dev/test
  throwaways; `fetch-dev-secrets.sh` assembles the development runtime secret
  directory from local and AWS-owned sources.
- `scripts/docs/docsys/` is both a Python CLI/module and MCP server for focused
  context, impact, freshness, search, and health queries; it does not edit docs.
- `infra/images/scripts/lib/packer-build.sh` assembles nested Packer source into
  temporary flat projects for selected builders.

## Dependency direction

Repository workflow scripts call application or infrastructure entry points;
thin shell wrappers commonly locate the repository and delegate to Python,
Node, Docker, Packer, Terraform, CDK, or AWS CLI. Scripts consume maintained
source and configuration but do not become application runtime modules. Keep
side-effectful platform operations with the platform that owns their state.

## Generated versus handwritten code

The scripts are handwritten. Their outputs include `backend/openapi.yaml`,
frontend generated contracts, local env/secret files, repository-tree output,
Packer manifests, Terraform/cloud-init artifacts, test reports, and deployment
side effects. Generated outputs must be changed through their owning script;
Docsys queries and documentation validators are read-only.

## Tests and validation

CI invokes the backend security/lint/test helpers, OpenAPI contract check, and
documentation validators. Infrastructure scripts have executable assertions in
`infra/tests/`; Packer validation also runs shell syntax checks. No focused tests
were found for the Python test runner or integrity-rule checker, and there is no
single test harness for every operator script. `bash -n` and each script's documented dry-run or
validation mode are the minimum static checks where available.

## Known gaps

Several Proxmox, Packer, bootstrap, and AWS helpers require external systems and
are not executed end to end by CI. The repository also has no single command
dispatcher covering every script family, so the [[scripts-catalogue|Scripts
catalogue]] remains the navigation boundary and each entry point owns its own
argument contract.

## Related documents

- [[scripts-catalogue|Scripts catalogue]]
- [[commands|Commands]]
- [[repository-map|Repository map]]
- [[generated-files|Generated files]]
