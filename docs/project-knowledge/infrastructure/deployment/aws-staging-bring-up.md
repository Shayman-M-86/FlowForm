---
title: AWS staging bring-up
aliases: ["AWS staging bring-up"]
document_type: workflow
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-28
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

This is the operator sequence for introducing the FlowForm application hosts
into the existing AWS staging environment. It separates artifact publication,
secret seeding, infrastructure deployment, and live verification so a failure
in one concern does not disguise the state of another.

The current delivery boundary is:

```text
feature branch -> reviewed PR -> staging branch
                                  |
                                  +-> build and publish AMI
                                  +-> deploy shared security addition
                                  +-> seed observability token
                                  +-> deploy application hosts
                                  +-> verify convergence and IAM DB auth
```

Do not run the deployment from an unmerged feature checkout. The AMI bakes
repository bootstrap and container assets, and the CDK deployment must consume
the same reviewed source lineage.

## Preconditions

Before starting this slice:

- `FlowForm-Staging-Network`, `FlowForm-Staging-Database`, and the database
  bootstrap are complete.
- The five nonproduction runtime image parameters contain digest-pinned ECR
  references.
- The feature work is merged into `staging`, the local checkout is clean, and
  AWS authentication targets account `908123139858` in `ap-southeast-2`.
- A Grafana Cloud token is available through a protected local file. It must
  not be committed or placed in a CDK environment file.

## 1. Build and publish the base AMI

From the repository root on the exact merged staging commit:

```sh
infra/images/scripts/image doctor aws
infra/images/scripts/image build aws
infra/images/scripts/image publish aws --environment staging --dry-run
infra/images/scripts/image publish aws --environment staging
```

The dispatcher derives the AMI `source_commit` tag from Git. Publication
verifies the artifact and writes its identifier to
`/flowform/staging/ec2/baseAmiId`. It does not deploy EC2 instances.

## 2. Deploy the security addition

The proxy needs a KMS-encrypted observability secret before it is created:

```sh
cd infra/deployment/aws/cdk
npx cdk diff -c env=staging FlowForm-Nonprod-Security
npx cdk deploy -c env=staging FlowForm-Nonprod-Security
cd ../../../..
```

This creates `flowform/nonprod/observability-secrets` with a generated
placeholder. The placeholder is not a usable Grafana credential.

## 3. Seed the Grafana token

Prefer a mode-restricted file and run the script's dry-run first:

```sh
chmod 600 /path/to/grafana-cloud-token
GRAFANA_CLOUD_TOKEN_FILE=/path/to/grafana-cloud-token \
  infra/deployment/aws/scripts/seed-observability-secret.sh

GRAFANA_CLOUD_TOKEN_FILE=/path/to/grafana-cloud-token \
  infra/deployment/aws/scripts/seed-observability-secret.sh --apply
```

The script verifies the AWS account and secret, writes a new secret version
through a temporary mode-0600 JSON file, and does not place the token in CLI
arguments or output.

## 4. Deploy the application stack

Review the complete change before applying it:

```sh
cd infra/deployment/aws/cdk
npx cdk diff -c env=staging --exclusively FlowForm-Staging-Application
npx cdk deploy -c env=staging --exclusively FlowForm-Staging-Application
```

The deployment creates the proxy and application instances, proxy Elastic IP,
public API record, private service records, runtime parameters, and exact host
permissions. Each host authenticates Docker to the required ECR registries and
then runs its baked bootstrap. The private app reaches public service APIs
through Squid and reaches RDS directly.

`--exclusively` is required for this slice because the retained
`FlowForm-Staging-DatabaseBootstrap` helper still imports automatic outputs
from the deployed Network and Database stacks. The default CDK assembly omits
that context-gated helper and would otherwise propose removing those still-used
exports from its dependency templates. The exclusive deployment leaves the
already-deployed dependencies untouched. Replace this operator constraint with
stable explicit stack contracts in a later bootstrap-stack migration.

## 5. Verify the live path

CloudFormation success proves resource creation, not application readiness.
Verify:

1. Both instances are running and managed by Systems Manager.
2. Proxy and app bootstrap logs completed without missing parameters, secrets,
   image authentication, or Compose health failures.
3. `proxy.internal.staging.flow-form.com.au` and
   `app.internal.staging.flow-form.com.au` resolve inside the VPC.
4. `api.staging.flow-form.com.au` resolves to the proxy Elastic IP and presents
   a valid certificate.
5. Caddy readiness reaches the backend.
6. The backend opens both PostgreSQL connections with IAM tokens and no stored
   database password.
7. Logs and traces arrive in the intended Grafana destinations.
8. A reboot or explicit reconvergence succeeds without workstation help.
9. A post-deployment CDK diff and CloudFormation drift check are clean.

Do not deploy the frontend or describe staging as ready until these checks have
evidence. RDS server-certificate identity verification and the remaining
database loose threads are separate readiness gates.

## Related documents

- [[deployment-index|Deployment documentation]]
- [[deployment-model|Deployment model]]
- [[aws-network-topology|AWS network topology]]
- [[cloud-deployment|Cloud deployment]]
