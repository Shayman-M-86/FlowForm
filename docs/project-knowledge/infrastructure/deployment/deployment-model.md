---
title: Deployment model
aliases: ["Deployment model"]
document_type: architecture
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-28
tags: [infrastructure, configuration]
related_code:
  - "../../../../infra/deployment/aws/cdk/app.py"
  - "../../../../infra/deployment/aws/cdk/flowform_infra/config/environments.py"
  - "../../../../infra/deployment/aws/cdk/flowform_infra/stacks/"
  - "../../../../infra/deployment/aws/cdk/flowform_infra/database_bootstrap/"
  - "../../../../infra/deployment/aws/scripts/"
related_docs: ["Deployment documentation", "AWS network topology", "Cloud deployment", "Runtime containers"]
---

# Deployment model

The repository declares three AWS environment names: `dev`, `staging`, and
`prod`. `dev` synthesizes its scope-specific security stack only; the CDK app
constructs registry, network, database, application, frontend-certificate,
frontend, and observability stacks only when the selected environment has
`full_deployment` enabled. That is true for `staging` and `prod` in the typed
environment configuration.

`dev` and `staging` select the shared `nonprod` security scope, while `prod`
selects `prod`. The configuration also sets lifecycle and deletion-protection
values per environment, and gives staging and production distinct public and
private DNS names. These are synthesis inputs, not evidence that the resources
exist in an AWS account.

```text
environment configuration
       |
       +--> dev ------> security scope only
       |
       +--> staging --+
       |              |
       +--> prod -----+--> full deployment
                           |
          +----------------+---------------------------+
          |        |        |        |        |        |
       network  registry  database  app    frontend  observability
```

## Declared AWS topology

For full-deployment environments, the CDK app composes independent stacks for
security, registry, networking, databases, application hosts, frontend
certificate and hosting, and observability. The application stack depends on
network, registry, security, and database stacks; the frontend stack depends on
its certificate and security stacks; observability depends on application.
The frontend certificate stack is explicitly configured for `us-east-1`, while
the remaining environment stacks use the environment region.

[[aws-network-topology|AWS network topology]] owns the full-deployment VPC,
subnet, route, endpoint, private-discovery, management, flow-log, and
security-group structure. Keeping those details in one network page avoids
turning this stack-level model into a second, incomplete network definition.

The infrastructure configuration specifies a Packer-built EC2 base-image
reference through an SSM parameter, with an optional direct AMI override and a
10 GiB root-volume setting. It therefore defines an image-selection contract,
but it does not prove that a matching image has been built or published.

## Host lifecycle boundary

The shared app and proxy bootstrap scripts render runtime configuration from
AWS SSM, materialise required secrets, validate the selected Compose files, and
start them with `docker compose ... up --wait`. App bootstrap requires an
explicit `FLOWFORM_DEPLOYMENT_TARGET`: `aws` requires both rendered database
auth modes to be `iam` and does not materialise database passwords, while
`rehearsal` requires both modes to be `password` and uses its Compose overlay
for the password files. The scripts also support an endpoint override for the
rehearsal path.

The persistent `DatabaseStack` provisions only RDS and its direct supporting
resources. Database bootstrap is an explicit operation outside that stack, so a
bootstrap failure cannot roll back or delete the database. When selected with
the `databaseBootstrap=true` CDK context, a separate
`DatabaseBootstrapStack` deploys an idempotent Lambda in the isolated app
subnet. `infra/deployment/aws/scripts/bootstrap-database.sh` deploys that helper,
creates one temporary Secrets Manager interface endpoint, invokes the Lambda,
checks its sanitized result, and requests endpoint deletion on success,
failure, or interruption.

The Lambda packages AWS-specific SQL from `infra/database/init/aws/` and the
authoritative schema snapshots from `infra/database/init/schema/`. It creates
the logical databases, roles, baseline application tables, grants, and a
bootstrap-history record, then verifies exact table sets, ownership, privileges,
and isolation. Later schema evolution remains a separate migration path. The
helper stack may remain deployed for future bootstrap versions without
retaining the paid interface endpoint. The container entrypoint under
`infra/database/init/templates/` remains the development and rehearsal path.

The CDK application stack does not provide an implementation-backed, complete
release workflow in this document: applying CDK, choosing a published image,
database migration ordering, and host rollout are separate operational steps.
[[cloud-deployment|Cloud deployment]] records the two checked-in publication
workflows; [[runtime-containers|Runtime containers]] owns the resulting host
container boundary.
