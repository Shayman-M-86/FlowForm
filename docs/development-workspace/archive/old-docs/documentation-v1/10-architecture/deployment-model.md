---
title: Deployment model
aliases:
  - "Deployment model"
document_type: architecture
status: draft
authority: canonical
verified_against_commit: null
tags: [infrastructure, configuration, ci-cd]
related_code:
  - "../../infra/deployment/aws/cdk/app.py"
  - "../../infra/deployment/aws/cdk/flowform_infra/config/environments.py"
  - "../../infra/deployment/aws/cdk/flowform_infra/stacks/"
  - "../../infra/deployment/aws/cdk/flowform_infra/constructs/static_site_construct.py"
  - "../../infra/containers/"
  - "../../infra/containers/strategies/rehearsal/"
  - "../../infra/deployment/bootstrap/"
  - "../../infra/images/packer/"
  - "../../infra/images/scripts/"
  - "../../infra/deployment/proxmox/"
  - "../../.github/workflows/deploy.yml"
related_docs:
  - "System context"
  - "AWS staging infrastructure target"
  - "Runtime containers"
  - "Trust boundaries"
  - "Cloud deployment"
  - "Machine image building"
  - "Proxmox rehearsal implementation"
  - "Secrets and configuration"
  - "Infrastructure implementation"
  - "Infrastructure resources"
---

# Deployment model

Describes the checked-in environment model, intended AWS topology, and the
boundary between implemented infrastructure and an operational deployment. It
does not claim that synthesized resources are deployed or healthy.

## Environment model

| Environment or context | Declared shape | Evidence boundary |
| --- | --- | --- |
| Local development | Backend and two PostgreSQL services use development Compose; frontends run through their workspace tooling or frontend Compose. AWS `dev` synthesizes only the shared non-production security stack. | Local definitions; current process state is not checked in. |
| Automated test | A separate backend test Compose project with two PostgreSQL services runs locally and in CI. | CI proves this variant when the job succeeds, not a deployed application environment. |
| Split-runtime local proof | One workstation runs proxy, app, and local database containers together. | Tests communication and hardening assumptions without reproducing host or AWS isolation. |
| Proxmox rehearsal | Packer builds a shared Amazon Linux golden template plus isolated LocalStack and PostgreSQL fixtures; Terraform clones proxy, app, LocalStack, and DB VMs and uploads role-specific cloud-init. | The checked-in fixture paths support offline startup; successful image builds and an applied rehearsal are still required to prove live health. |
| AWS staging | Configuration requests the full CDK stack set and shares the `nonprod` security scope with dev. | Declared and partly synthesizable; the checkout does not prove a complete or running staging backend. |
| AWS production | Configuration requests the same full stack classes with production domains, retained lifecycle policy, and a separate `prod` security scope. | Declared target only; the deploy workflow explicitly does not deploy production. |

Environment differences are data in the typed CDK configuration rather than
separate stack implementations. Dev intentionally differs by omitting cloud
compute, databases, and frontend hosting. Staging and prod select the same stack
classes, but resource lifecycle, sizing, domains, and security scope differ.

## Cross-platform host lifecycle

The intended cross-platform boundary is the shared, idempotent host bootstrap,
not the workstation-side Proxmox build script. A newly created or replaced
application host should be able to reach a healthy runtime without an operator
issuing a second command after machine provisioning:

1. Release automation publishes the immutable container image and prepares any
   configuration, secrets, and compatible database state required by that
   image.
2. The platform provisioner supplies its native first-boot payload: EC2 user
   data in AWS or cloud-init attached by Terraform in Proxmox.
3. First boot installs and invokes the same host bootstrap used by the systemd
   reboot-recovery unit.
4. The bootstrap renders configuration, materialises secrets, pulls images,
   starts Compose, waits for health, and fails closed when a prerequisite is
   unavailable.

Release orchestration remains a separate responsibility. It coordinates image
publication, migrations, rollout health, and rollback, but a permanently
running custom orchestration service should not be required merely to wake a
fresh host. The AWS implementation sketches propose GitHub Actions plus SSM
Run Command for controlled releases; that mechanism is not yet implemented or
accepted as a completed deployment boundary.

The Proxmox rehearsal currently has one deliberate exception. Its private
registry starts empty, and the app VM is itself used as the relay that publishes
the backend and Alloy images. Guest cloud-init therefore installs and enables
the bootstrap units without starting them during the creation boot; the
workstation orchestrator publishes the images and owns first convergence.
Ordinary VM reboots remain self-starting through systemd. This ordering is a
rehearsal-fixture constraint and must not be generalized into the AWS host
lifecycle.

## Proxmox image and deployment boundary

The local Proxmox rehearsal uses separate tools for separate lifecycle scopes:

```text
shared provisioning contract
├── minimal AL2023 EC2 base -> AWS AMI with 10 GiB root
└── AL2023 KVM base -> Proxmox golden template 9000 with 25 GiB root
    ├── Terraform -> proxy 210, app 220
    ├── Packer LocalStack fixture 9001 -> Terraform -> LocalStack 230
    └── Packer PostgreSQL fixture 9002 -> Terraform -> database 240
```

Packer owns source-template preparation and the reusable operating-system
image: Amazon Linux, Docker, Compose, AWS CLI, and shared host configuration.
Terraform owns the deployment topology: full clones, VM networking, cloud-init
snippets, and Terraform state. Terraform does not invoke Packer, and Packer
does not deploy the rehearsal VMs.

The golden template excludes runtime container images. Two Proxmox-only
fixtures derive from it: template `9001` preloads exactly the LocalStack,
registry, and TLS-shim images declared by rehearsal Compose, while template
`9002` preloads only the PostgreSQL image declared by DB Compose. VMs `230` and
`240` therefore need no runtime registry access. Terraform and cloud-init own IPs, SSH keys,
Compose files, TLS material, service units, and seed data. The workstation
orchestrator owns first service startup; enabled systemd units own later reboot
recovery. Terraform consumes all completed template VMIDs and never invokes
Packer.

LocalStack is not exposed to the development LAN for provisioning. Terraform
validates the non-secret rehearsal seed values against the shared runtime
parameter contract and delivers them through cloud-init. After LocalStack is
healthy, the fixture VM creates its own throwaway secrets and local KMS
resources, then seeds SSM locally. AWS CDK consumes the same contract for
scoped SSM names while supplying real AWS-derived values; application code
continues to use the normal AWS SDK contract in both environments.

Shared provisioning does not imply a shared source disk. AWS uses Amazon's
native minimal EC2 AMI so its encrypted gp3 root can remain 10 GiB; Proxmox
preserves the official KVM QCOW2's native 25 GiB XFS disk. CDK explicitly
declares the AWS size, and the AWS build verifies its AMI snapshot before the
artifact is published.

## Intended AWS topology

The implemented and planned definitions collectively describe the target below.
Its accepted hard boundaries are declared in
[[0001-aws-staging-infrastructure-target|AWS staging infrastructure target]].
This section continues to distinguish those decisions from implemented and
deployed state.

```text
public-site and Studio users
  -> Route 53 aliases
  -> CloudFront
  -> private S3 origins

API clients
  -> public API DNS (not yet created by CDK)
  -> Elastic IP on public proxy EC2
  -> Caddy
  -> private app EC2
  -> Gunicorn / Flask
  -> core and response PostgreSQL on RDS (not yet created by CDK)

private app outbound HTTP(S)
  -> Squid on proxy EC2
  -> allow-listed external services
```

The VPC definition provides one public proxy subnet and one isolated app subnet
in the primary runtime AZ. RDS receives one isolated subnet in that AZ and a
second isolated subnet in another AZ to satisfy the DB subnet-group contract;
the staging database itself remains single-AZ. No NAT gateway is created.
Security groups restrict public ingress to the proxy, proxy-to-app traffic to
the backend port, app-to-proxy traffic to Squid, app-to-proxy telemetry traffic
to Alloy, and app-to-database traffic to PostgreSQL. An S3 gateway endpoint
supplies the declared direct path for container image layers, and an EC2
Instance Connect Endpoint supplies the private app management path. VPC flow
logs target an environment-owned CloudWatch log group, and a private Route 53
zone gives the proxy and app stable VPC-only names that follow instance
replacement. See
[[trust-boundaries|Trust boundaries]] for the security interpretation and
[[runtime-containers|Runtime containers]] for host service roles.

The two static frontends use separate private S3 buckets and CloudFront
distributions. A certificate stack lives in `us-east-1`, while DNS aliases,
distributions, buckets, and build-time SSM parameters are assembled in the main
environment region.

## CDK implementation boundary

The stack names in `infra/deployment/aws/cdk/app.py` do not all represent completed resource
sets.

| Stack area | Current implementation state |
| --- | --- |
| Security | Creates scoped KMS, Secrets Manager, SSM, IAM, and GitHub OIDC resources, including a branch-restricted image-publisher role with no embedded repository policy; imports the existing Route 53 zone and SES identity by reference. |
| Registry | Creates separate KMS-encrypted, immutable, scan-on-push Backend, Caddy, Squid, and Alloy repositories with staging cleanup rules and exact publisher access. A manual OIDC workflow publishes all four and retains their digest manifest without promoting it. |
| Network | Creates the four-subnet VPC (one proxy, one app, and two RDS subnets across the minimum two AZs), security groups, S3 gateway endpoint, EC2 Instance Connect Endpoint, private hosted zone, and VPC flow-log destination for the split-host model. |
| Application | Creates proxy and app EC2 instances, an Elastic IP, host roles, and VPC-only A records using a Packer AMI reference. Its policies restrict the app host to Backend/Alloy pulls and the proxy host to Caddy/Squid/Alloy pulls. It does not attach runtime bootstrap/user data or create the public API DNS record. |
| Database | Is a placeholder and creates no RDS resources. Consequently the app stack's declared PostgreSQL destination is absent from CDK. |
| Frontend certificate and hosting | Create the cross-region certificate, private S3 origins, CloudFront distributions, DNS aliases, cache policies, deployment permissions, and frontend SSM parameters. |
| Observability | Is a placeholder and creates no log groups, alarms, or dashboard. |

Because the database, application bootstrap, runtime image promotion, API DNS,
and observability pieces are incomplete, a successful synth is not evidence of
a functional full deployment.

## Deployment automation boundary

The checked-in deployment workflow builds and publishes both frontend artifacts
to the staging S3 buckets, then invalidates their CloudFront distributions. It
uses GitHub OIDC. A `workflow_run` deploys the exact commit from a successful
staging CI run; manual dispatch deploys its selected ref without itself requiring
a successful CI run. It does not publish or restart the backend,
run database provisioning or migrations, deploy CDK stacks, or deploy
production. Those procedures remain gaps for [[cloud-deployment|Cloud deployment]].

The repository contains shared host bootstrap scripts, but CDK and the deploy
workflow do not yet connect those scripts to EC2 provisioning or release
rollout. [[machine-image-building|Machine image building]] owns the base-image path; the application
stack consumes a configured AMI ID or SSM AMI parameter rather than selecting a
generic latest image.

## External and manual dependencies

The Route 53 hosted zone and SES identity are imported rather than created by
the security stack. Full frontend synthesis also requires environment-specific
Auth0 public configuration and hosted-zone lookup context. These dependencies
mean a clean source checkout alone is insufficient to reproduce or verify a
live deployment. Configuration and secret ownership belong in
[[secrets-and-configuration|Secrets and configuration]], while exact resource locations belong in
[[infrastructure|Infrastructure implementation]] and [[infrastructure-resources|Infrastructure resources]].

## Open questions

- Which checked-in topology, if any, matches the currently running production
  system?
- How will `DatabaseStack` create and verify the accepted single-instance,
  two-database layout, separate application users, migration credential, TLS
  policy, backups, and restore path?
- What process will provision runtime files, invoke bootstrap, publish container
  images, migrate databases, and roll back a backend release?
- Which AWS release mechanism will invoke the already-running host for a
  controlled rollout: SSM Run Command, an SSM document, or another managed
  deployment facility?
- When will the public API DNS record and certificate path be implemented and
  verified end to end?
- Which observability resources and release-health signals are required before
  staging or production can be considered operational?

## Related documents

- [[system-context|System context]]
- [[0001-aws-staging-infrastructure-target|AWS staging infrastructure target]]
- [[runtime-containers|Runtime containers]]
- [[trust-boundaries|Trust boundaries]]
- [[cloud-deployment|Cloud deployment]]
- [[machine-image-building|Machine image building]]
- [[proxmox-rehearsal|Proxmox rehearsal implementation]]
- [[secrets-and-configuration|Secrets and configuration]]
- [[infrastructure|Infrastructure implementation]]
- [[infrastructure-resources|Infrastructure resources]]
