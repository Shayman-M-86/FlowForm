---
title: AWS staging bring-up
aliases: ["AWS staging bring-up"]
document_type: workflow
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-29
tags: [infrastructure, configuration]
related_code:
  - "../../../../infra/images/scripts/image"
  - "../../../../infra/deployment/aws/cdk/"
  - "../../../../infra/deployment/aws/scripts/"
  - "../../../../infra/deployment/bootstrap/"
related_docs:
  - "Deployment documentation"
  - "Deployment model"
  - "AWS network topology"
  - "Cloud deployment"
---

# AWS staging bring-up

This is the ordered run sheet for creating FlowForm staging in an AWS account
that already has the manually managed public Route 53 zone, SES identity,
external Auth0/Grafana configuration, and operator AWS access.

Use the exact reviewed `staging` commit with a clean worktree. Runtime
containers and the Packer AMI both contain commit-specific application assets.

## Build order

| Order | Output | Why it is here |
| --- | --- | --- |
| 1 | CDK bootstrap | CloudFormation needs the CDK asset roles and bucket. |
| 2 | Security and Registry | Later stacks need the KMS key, IAM roles, secrets, and ECR repositories. |
| 3 | Runtime container images | Hosts fail closed unless their digest-pinned images are promoted in SSM. |
| 4 | Network | RDS and hosts need their subnets, routes, DNS, and security groups. |
| 5 | RDS and database bootstrap | The backend must start against prepared databases and IAM roles. |
| 6 | Packer AMI | The Application stack resolves a published AMI ID and the AMI must bake the reviewed bootstrap assets. |
| 7 | Runtime secret seeding | The proxy must receive a real Grafana token rather than the generated placeholder. |
| 8 | Application | Only now do the proxy and app hosts have every dependency required to converge. |
| 9 | Frontend | Publish the browser applications after the API path is healthy. |
| 10 | Verification | CloudFormation success alone does not prove service readiness. |

## 0. Prepare the reviewed checkout

```sh
git switch staging
git pull --ff-only
git status --short
aws sts get-caller-identity
```

This establishes the source and AWS identity used by every later command.
`git status --short` should be empty.

Prepare the CDK environment file and ignored Packer variables before
continuing:

```sh
cd infra/deployment/aws/cdk
uv sync
cd ../../../..

cp infra/images/packer/variables/aws.auto.pkrvars.hcl.example \
  infra/images/packer/variables/aws.auto.pkrvars.hcl
```

Fill the ignored files with the approved non-secret environment identifiers
and AWS builder settings. Never commit them or place secret values in them.

## 1. Bootstrap CDK

Run once per account and region:

```sh
cd infra/deployment/aws/cdk
npx cdk bootstrap aws://908123139858/ap-southeast-2
cd ../../../..
```

This creates the shared CDK staging bucket and deployment roles. Every CDK
deployment below depends on them.

## 2. Deploy Security and Registry

```sh
cd infra/deployment/aws/cdk
npx cdk diff -c env=staging \
  FlowForm-Nonprod-Security FlowForm-Staging-Registry
npx cdk deploy -c env=staging \
  FlowForm-Nonprod-Security FlowForm-Staging-Registry
cd ../../../..
```

Security creates the shared nonproduction KMS key, IAM roles, and secret
containers. Registry creates the four ECR repositories. Images cannot be
published before their repositories and publisher role exist.

Seed the required application and linkage secrets through the approved
out-of-band secret procedure before launching a host. Generated values are
placeholders, not staging credentials.

## 3. Publish and promote runtime container images

Run the manual **Publish staging images** GitHub workflow against `staging`.
It builds or mirrors Backend, Caddy, Squid, and Alloy into ECR and produces
`staging-image-release.json`.

Download that workflow artifact, then review and promote it:

```sh
RELEASE_MANIFEST_PATH=/path/to/staging-image-release.json \
  DRY_RUN=1 \
  infra/deployment/aws/scripts/publish-staging-images.sh promote

RELEASE_MANIFEST_PATH=/path/to/staging-image-release.json \
  FLOWFORM_SCOPE=nonprod \
  infra/deployment/aws/scripts/publish-staging-images.sh promote
```

Promotion writes five digest-pinned image references under
`/flowform/nonprod/backend/` and `/flowform/nonprod/proxy/`. Publication creates
artifacts; promotion selects what new hosts will run.

## 4. Deploy Network

```sh
cd infra/deployment/aws/cdk
npx cdk diff -c env=staging --exclusively FlowForm-Staging-Network
npx cdk deploy -c env=staging --exclusively FlowForm-Staging-Network
cd ../../../..
```

This creates the VPC, four-subnet layout, Internet/S3 routing, private DNS,
Instance Connect Endpoint, flow logs, and security groups. RDS must consume
these network contracts.

## 5. Deploy and bootstrap the database

```sh
cd infra/deployment/aws/cdk
npx cdk diff -c env=staging --exclusively FlowForm-Staging-Database
npx cdk deploy -c env=staging --exclusively FlowForm-Staging-Database
cd ../../../..
```

This creates persistent encrypted RDS infrastructure only. It deliberately
does not make schema failure part of the RDS lifecycle.

Run the separate idempotent bootstrap:

```sh
infra/deployment/aws/scripts/bootstrap-database.sh --env staging
infra/deployment/aws/scripts/bootstrap-database.sh --env staging --apply
```

The apply step deploys the helper Lambda, temporarily creates a Secrets Manager
interface endpoint, creates and verifies the databases, roles, tables, and IAM
grants, then removes the paid endpoint. It must finish before the backend
attempts its first connection.

## 6. Build and publish the Packer AMI

Run from the repository root on the exact reviewed commit:

```sh
infra/images/scripts/image doctor aws
infra/images/scripts/image build aws
infra/images/scripts/image publish aws --environment staging --dry-run
infra/images/scripts/image publish aws --environment staging
```

- `doctor` checks Packer, AWS, `jq`, the ignored variables, AWS authentication,
  and the CDK AMI-parameter contract.
- `build` launches a temporary EC2 builder, installs the host dependencies,
  bakes the bootstrap/Compose/AWS strategy assets, creates an encrypted AMI and
  snapshot, cleans the builder resources, and verifies the AMI contract.
- `publish --dry-run` verifies the artifact and destination without changing
  SSM.
- `publish` writes the verified AMI ID to
  `/flowform/staging/ec2/baseAmiId`.

The AMI is built after the runtime and database contracts have settled so it
bakes the final reviewed host-convergence assets. It must be published before
Application deployment because CDK resolves this SSM parameter while creating
the EC2 instances.

## 7. Seed the observability token

Security created `flowform/nonprod/observability-secrets` with a placeholder.
Replace it before launching the proxy:

```sh
chmod 600 /path/to/grafana-cloud-token

GRAFANA_CLOUD_TOKEN_FILE=/path/to/grafana-cloud-token \
  infra/deployment/aws/scripts/seed-observability-secret.sh

GRAFANA_CLOUD_TOKEN_FILE=/path/to/grafana-cloud-token \
  infra/deployment/aws/scripts/seed-observability-secret.sh --apply
```

The first command is a dry run. The apply command adds the real token as a new
Secrets Manager version without placing it in CDK, SSM, or CLI arguments.

## 8. Deploy Application

```sh
cd infra/deployment/aws/cdk
npx cdk diff -c env=staging \
  --exclusively FlowForm-Staging-Application
npx cdk deploy -c env=staging \
  --exclusively FlowForm-Staging-Application
```

This creates the proxy and application instances, proxy Elastic IP, public API
record, private host records, runtime parameters, and host permissions. The
hosts boot from the published AMI, authenticate to ECR, materialise their
runtime configuration, and start the Compose projects. The proxy role can read
only its `/flowform/nonprod/proxy/*` runtime parameter path. After Squid is
reachable, app bootstrap writes the SSM Agent systemd proxy configuration for
`http://10.42.0.4:3128`, keeps instance metadata direct, and restarts the agent
before continuing host convergence.

`--exclusively` is currently required because the retained
`FlowForm-Staging-DatabaseBootstrap` stack imports automatic Network and
Database outputs. A normal dependency-inclusive deployment would propose
removing exports that the helper still uses.

## 9. Verify the backend path

Before publishing the frontend, verify:

1. Both EC2 instances are running and managed by Systems Manager.
2. Proxy bootstrap read `/flowform/nonprod/proxy/*`, and app bootstrap
   configured SSM Agent through `10.42.0.4:3128`.
3. Proxy and app bootstrap logs completed successfully.
4. Both Compose projects are healthy.
5. Private host records resolve inside the VPC.
6. `api.staging.flow-form.com.au` resolves and presents a valid certificate.
7. Caddy reaches backend readiness.
8. The backend opens both RDS connections with IAM tokens.
9. Logs and traces reach Grafana.

## 10. Deploy and publish the frontend

```sh
cd infra/deployment/aws/cdk
npx cdk diff -c env=staging \
  FlowForm-Staging-FrontendCert FlowForm-Staging-Frontend
npx cdk deploy -c env=staging \
  FlowForm-Staging-FrontendCert FlowForm-Staging-Frontend
```

This creates the certificate, private buckets, CloudFront distributions, DNS,
and frontend deployment parameters. Then run the checked-in frontend
publication workflow against the exact staging commit.

Finish with a post-deployment CDK diff, CloudFormation drift checks, public
browser/API checks, and a reboot or explicit reconvergence test.

## Related documents

- [[deployment-index|Deployment documentation]]
- [[deployment-model|Deployment model]]
- [[aws-network-topology|AWS network topology]]
- [[cloud-deployment|Cloud deployment]]
