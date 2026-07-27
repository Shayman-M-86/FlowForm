---
title: Scripts implementation
aliases:
  - "Scripts implementation"
document_type: implementation
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-27
tags: [tooling]
related_code:
  - "../../../scripts/"
  - "../../../backend/scripts/"
  - "../../../frontend/scripts/"
  - "../../../infra/images/scripts/"
  - "../../../infra/deployment/bootstrap/"
  - "../../../infra/deployment/proxmox/scripts/"
  - "../../../tools/mcp/"
related_docs:
  - "Scripts catalogue"
  - "Commands"
  - "Repository map"
  - "Generated files"
---

# Scripts implementation

Maps script families to their implementation ownership and execution
boundaries. The scripts themselves remain the source of truth for arguments,
preconditions, and side effects.

```text
repository workflows
   |
   +--> scripts/            shared CI, dev, docs, and secret tasks
   +--> backend/scripts/    backend checks and contracts
   +--> frontend/scripts/   frontend contract generation
   +--> infra/**/scripts/   platform-owned operator actions
   +--> tools/mcp/          development integrations
   |
   v
language/runtime tools --> generated artifacts or external side effects
```

## Directory ownership

- `scripts/ci/` coordinates OpenAPI contract generation and drift checks;
  `scripts/dev/` owns local bootstrap and mock-data loading;
  `scripts/secrets/` owns local configuration material; `scripts/docs/` owns
  documentation generation, validation, Docsys, and vault synchronization.
- `backend/scripts/` owns backend tests, health, security, OpenAPI export, and
  database-rule checks. `frontend/scripts/` owns frontend contract generation.
- Infrastructure-local scripts remain with their lifecycle owner under
  `infra/images/`, `infra/deployment/`, `infra/containers/strategies/`, and
  `infra/tests/`.
- `tools/mcp/` owns development MCP launchers and server entry modules;
  `.githooks/pre-commit` is the repository hook entry point.

## Entry points

Primary coordination entries include `scripts/ci/sync-openapi.sh`,
`scripts/dev/bootstrap-dev-and-load-mocks.sh`,
`scripts/secrets/fetch-dev-secrets.sh`, and the validators under
`scripts/docs/`. Application-specific entries include
`backend/scripts/run-tests.sh` and `frontend/scripts/generate-types.mjs`.
Image build, host bootstrap, Proxmox verification, and rehearsal image-push
scripts can change external state; their headers and linked workflows define
their preconditions.

## Important modules

- `scripts/ci/check-openapi-contracts.sh` coordinates the contract drift check.
  `sync-openapi.sh` exports the backend contract, regenerates frontend
  contracts, checks their diff, and runs Redocly lint.
- `backend/scripts/run-tests.py` fingerprints schema, build, and environment
  inputs and manages the persistent Docker test stack behind a shell wrapper.
- `scripts/secrets/generate_secrets.py` creates non-overwriting development and
  test values; `fetch-dev-secrets.sh` assembles the development runtime secret
  directory from local and AWS-owned sources.
- `scripts/docs/docsys/` supplies the CLI and MCP server for context, impact,
  freshness, search, validation, and health queries.
- `infra/images/scripts/image` is the image operator entry point, while
  `infra/images/scripts/lib/packer-project.sh` assembles selected Packer sources
  into temporary projects.

## Dependency direction

Repository workflow scripts call application or infrastructure entry points.
Thin shell wrappers commonly locate the repository and delegate to Python,
Node, Docker, Packer, Terraform, CDK, or AWS CLI. Scripts consume maintained
source and configuration but do not become application runtime modules. Keep
side-effectful platform operations with the platform that owns their state.

## Generated versus handwritten code

The scripts are handwritten. Their outputs include `backend/openapi.yaml`,
frontend generated contracts, local environment and secret files, repository
tree output, Packer manifests, Terraform or cloud-init artifacts, test reports,
and deployment side effects. Generated outputs must be changed through their
owning script; Docsys queries and documentation validators are read-only.

## Tests and validation

CI invokes backend security, lint, and test helpers, the OpenAPI contract check,
and documentation validators. Infrastructure scripts have executable
assertions in `infra/tests/`; Packer validation also runs shell syntax checks.
There is no single test harness for every operator script, so `bash -n` and
each script's documented dry-run or validation mode remain the minimum static
checks where available.

## Known gaps

Several Proxmox, Packer, bootstrap, and AWS helpers require external systems and
are not exercised end to end by CI. There is also no single dispatcher for
every script family, so the [[scripts-catalogue|Scripts catalogue]] is the
navigation boundary and each entry point owns its argument contract.

## Related documents

- [[scripts-catalogue|Scripts catalogue]]
- [[commands|Commands]]
- [[repository-map|Repository map]]
- [[generated-files|Generated files]]
