---
title: Infrastructure implementation
aliases:
  - "Infrastructure implementation"
document_type: implementation
status: draft
authority: canonical
verified_against_commit: ad26b87e9820
tags: [infrastructure]
related_code:
  - "../../infra/containers/"
  - "../../infra/database/"
  - "../../infra/images/"
  - "../../infra/deployment/"
  - "../../infra/tests/"
related_docs:
  - "Repository map"
  - "Deployment model"
  - "Machine image building"
  - "Local infrastructure"
  - "Infrastructure resources"
---

# Infrastructure implementation

Maps infrastructure concepts to verified repository implementation.

## Directory ownership

- `infra/containers/images/` owns buildable application images;
  `containers/runtime/` owns shared app/proxy Compose and service configuration;
  `containers/strategies/` owns AWS, development, and rehearsal differences.
- `infra/database/` owns PostgreSQL configuration, initialization templates,
  maintained core/response schemas, and local mock data.
- `infra/images/` owns the shared Packer image contract, AWS/Proxmox builders,
  bounded fixture images, and image-build wrappers.
- `infra/deployment/aws/` owns the CDK application and stack definitions;
  `deployment/proxmox/` owns host preparation, Terraform VMs, cloud-init, and
  rehearsal operator scripts.
- `infra/deployment/bootstrap/` owns runtime host bootstrap shared by deployment
  strategies, while `infra/env/` holds local environment material.

## Entry points

- Development and test stacks start from
  `containers/strategies/dev/compose/compose.yml` and `compose.test.yml`.
- Deployed app and proxy hosts consume `containers/runtime/compose/app.yml` and
  `proxy.yml`, normally through the role-specific bootstrap scripts.
- `deployment/aws/cdk/app.py` synthesizes the selected environment's CDK stack
  graph.
- `deployment/proxmox/terraform/` is the rehearsal deployment entry; host setup
  and verify/rebuild/log helpers live beside it.
- `images/scripts/build-*.sh` prepare or build machine images before either
  deployment path consumes them.

## Important modules

The runtime Compose boundary separates a private backend/collector host from a
Caddy, Squid, and Alloy proxy host. Development Compose combines backend and two
PostgreSQL services for iteration; rehearsal adds isolated LocalStack, registry,
TLS-shim, and PostgreSQL fixtures.

AWS CDK separates security, network, application, frontend certificate,
frontend hosting, database, and observability stacks. Proxmox Terraform creates
full clones for proxy, app, LocalStack, and database roles and uploads
role-specific cloud-init assembled from the shared runtime assets and parameter
contract.

## Dependency direction

Packer produces reusable images; CDK or Terraform consumes image identifiers.
Terraform owns VM topology and cloud-init and does not invoke Packer. Bootstrap
consumes environment configuration, the runtime parameter contract, and shared
Compose definitions to start host services. Application containers consume
database, identity, AWS, and proxy services but do not define infrastructure.

## Generated versus handwritten code

Dockerfiles, Compose, service configuration, SQL templates/schemas, Packer HCL,
CDK Python, Terraform HCL, cloud-init templates, bootstrap, and test scripts are
maintained source. Packer manifests, CDK assembly, Terraform state and provider
data, rendered cloud-init, temporary Compose files, and local credential/value
files are generated or machine-local artifacts. Generated documentation under
`docs/90-generated/` is refreshed separately and is not an infrastructure
source.

## Tests and validation

- `infra/deployment/aws/cdk/tests/` contains synth-time assertions for
  environments, security, network/application shape, frontend, and parameter
  contracts.
- `infra/tests/containers/test-container-invariants.sh` checks intended sharing
  across runtime strategies.
- `infra/tests/deployment/test-localstack-seed.sh` checks rehearsal seed,
  fixture, TLS, firewall, and database-bootstrap invariants.
- `infra/tests/images/validate.sh` validates Packer builds and source/image
  guards without creating live artifacts.
- `terraform fmt/validate`, Compose config rendering, and shell syntax checks
  cover additional static boundaries; an applied rehearsal or deployed AWS
  environment remains separate live evidence.

## Known gaps

AWS `DatabaseStack` and `ObservabilityStack` create no substantive resources.
`ApplicationStack` creates hosts but does not attach runtime bootstrap, publish
backend/proxy images, or create the public API DNS path. The deploy workflow
publishes only staging frontends. Consequently CDK synthesis is not evidence of
a complete backend deployment, database, observability path, or production
release.

## Related documents

- [[repository-map|Repository map]]
- [[deployment-model|Deployment model]]
- [[machine-image-building|Machine image building]]
- [[local-infrastructure|Local infrastructure]]
- [[infrastructure-resources|Infrastructure resources]]
