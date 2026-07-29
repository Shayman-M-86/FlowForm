---
title: Deployment order
aliases: ["Deployment order"]
document_type: planning
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-07-29
tags: [infrastructure, ci-cd]
related_code:
  - "../../../infra/deployment/aws/operations/"
  - "../../../infra/machine-images/"
  - "../../../infra/containers/"
related_docs: ["AWS CDK staging plan"]
---

# Deployment order

## 1. Merge into `staging`

```bash
git switch staging
git pull --ff-only origin staging
git status --short
```

This ensures every AMI and container is built from the exact reviewed commit that was merged into staging. `git status` must be empty because the build tools record the current commit as the artifact source.

## 2. Build the three-level AMIs

```bash
infra/deployment/aws/operations/machine-images/doctor.sh
infra/deployment/aws/operations/machine-images/build.sh all
```

`doctor.sh` checks Packer, AWS credentials, plugins, configuration, and other prerequisites.

`build.sh all` creates:

```text
Base AMI
├── App AMI
└── Proxy AMI
```

The Base contains shared host software. The App and Proxy AMIs add their respective systemd services, Compose topology, and deployment machinery.

## 3. Publish the App and Proxy AMI pointers

First preview:

```bash
infra/deployment/aws/operations/machine-images/publish.sh \
  --environment staging --role app --dry-run

infra/deployment/aws/operations/machine-images/publish.sh \
  --environment staging --role proxy --dry-run
```

Then publish:

```bash
infra/deployment/aws/operations/machine-images/publish.sh \
  --environment staging --role app

infra/deployment/aws/operations/machine-images/publish.sh \
  --environment staging --role proxy
```

This places the verified AMI IDs into:

```text
/flowform/staging/ec2/appAmiId
/flowform/staging/ec2/proxyAmiId
```

CDK resolves these parameters when it creates the EC2 instances. The Base AMI is not deployed directly.

## 4. Publish the container release

```bash
infra/deployment/aws/operations/container-releases/publish-staging.sh validate

infra/deployment/aws/operations/container-releases/publish-staging.sh \
  publish --commit "$(git rev-parse HEAD)"
```

This validates, builds, and pushes immutable Backend, Caddy, Squid, and Alloy images into ECR. Each image is tied to the exact staging commit.

Your GitHub Action can perform this step instead, but it should not also be run locally for the same commit because the ECR tags are immutable.

## 5. Promote the container release

Preview:

```bash
infra/deployment/aws/operations/container-releases/promote.sh \
  --environment staging --dry-run
```

Apply:

```bash
infra/deployment/aws/operations/container-releases/promote.sh \
  --environment staging
```

Promotion writes complete digest-pinned release manifests for the two roles:

```text
/flowform/staging/app/release
/flowform/staging/proxy/release
```

The EC2 hosts read these manifests to determine precisely which containers to run.

## 6. Update the Security stack

```bash
cd infra/deployment/aws/cdk

npx cdk deploy -c env=staging FlowForm-Nonprod-Security
```

This applies the latest IAM changes, particularly the SSM managed-instance permissions required for remotely managing the App host.

It preserves the existing shared secrets and KMS key.

## 7. Recreate the database

```bash
npx cdk deploy -c env=staging FlowForm-Staging-Database
```

This creates the persistent RDS instance, subnet group, security-group integration, master secret, encryption, backups, logs, and IAM database-authentication permissions.

At this point PostgreSQL exists, but the FlowForm databases, roles, schemas, and tables have not yet been created.

## 8. Bootstrap the database

Return to the repository root:

```bash
cd /home/shayman86/my-repos/FlowForm
```

Preview:

```bash
infra/deployment/aws/scripts/bootstrap-database.sh --env staging
```

Apply:

```bash
infra/deployment/aws/scripts/bootstrap-database.sh --env staging --apply
```

This temporarily creates the private Secrets Manager access needed by the bootstrap Lambda, then creates and verifies:

- FlowForm databases;
- owner, migration, and application roles;
- IAM authentication grants;
- schemas and privileges;
- application tables and migrations;
- bootstrap-version records.

The temporary VPC endpoint is removed afterward.

## 9. Deploy the Proxy host

```bash
infra/deployment/aws/operations/stacks/deploy-proxy.sh \
  --environment staging
```

This creates `FlowForm-Staging-Proxy`, containing:

- the Proxy EC2 instance;
- Proxy IAM role;
- Elastic IP;
- public API DNS;
- private Proxy DNS;
- Proxy runtime parameters.

The host uses the published Proxy AMI and starts Caddy, Squid, and Proxy Alloy from the promoted container release.

## 10. Deploy the App host

```bash
infra/deployment/aws/operations/stacks/deploy-app.sh \
  --environment staging
```

This creates `FlowForm-Staging-App`, containing:

- the private App EC2 instance;
- private App DNS;
- database configuration;
- backend runtime parameters;
- App container permissions.

The App has no public address. It uses Squid on the Proxy host for permitted outbound access and connects directly to RDS.

## 11. Explicitly converge both hosts

```bash
infra/deployment/aws/operations/hosts/converge-role.sh \
  --environment staging --role proxy

infra/deployment/aws/operations/hosts/converge-role.sh \
  --environment staging --role app
```

These use SSM Run Command to restart the baked role services. Each host reloads its release manifest, configuration, and secrets, then reconciles its containers.

Running Proxy first ensures Squid and Caddy are ready before the App performs its final convergence.

## 12. Verify the deployment

```bash
curl -fsS \
  https://api.staging.flow-form.com.au/api/v1/system/health/ready
```

A successful response proves the request path is working:

```text
Internet
→ Route 53
→ Proxy EC2
→ Caddy
→ App EC2
→ Backend
→ RDS readiness
```

After basic health passes, the final proof is rebooting each EC2 instance and confirming it returns to the same healthy state automatically.