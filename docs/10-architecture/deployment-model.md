---
title: Deployment model
document_type: architecture
status: draft
authority: canonical
verified_against_commit: ed0fb65df856e18807ee243b4bca512a8d0442b0
tags: [infrastructure, configuration, ci-cd]
related_code:
  - "../../infra/platforms/aws/cdk/app.py"
  - "../../infra/platforms/aws/cdk/flowform_infra/config/environments.py"
  - "../../infra/platforms/aws/cdk/flowform_infra/stacks/"
  - "../../infra/platforms/aws/cdk/flowform_infra/constructs/static_site_construct.py"
  - "../../infra/runtime/"
  - "../../infra/environments/rehearsal/"
  - "../../.github/workflows/deploy.yml"
related_docs:
  - "System context"
  - "Runtime containers"
  - "Trust boundaries"
  - "Cloud deployment"
  - "Machine image building"
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
| Proxmox rehearsal | Separate proxy and app VMs consume shared runtime/bootstrap files; local fixtures replace AWS, RDS, and public TLS dependencies. | Rehearses the host contract but intentionally does not prove managed cloud services. |
| AWS staging | Configuration requests the full CDK stack set and shares the `nonprod` security scope with dev. | Declared and partly synthesizable; the checkout does not prove a complete or running staging backend. |
| AWS production | Configuration requests the same full stack classes with production domains, retained lifecycle policy, and a separate `prod` security scope. | Declared target only; the deploy workflow explicitly does not deploy production. |

Environment differences are data in the typed CDK configuration rather than
separate stack implementations. Dev intentionally differs by omitting cloud
compute, databases, and frontend hosting. Staging and prod select the same stack
classes, but resource lifecycle, sizing, domains, and security scope differ.

## Intended AWS topology

The implemented and planned definitions collectively describe this target:

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

The VPC definition provides public proxy, isolated app, and isolated database
subnets without a NAT gateway. Security groups restrict public ingress to the
proxy, proxy-to-app traffic to the backend port, app-to-proxy traffic to Squid,
and app-to-database traffic to PostgreSQL. An S3 gateway endpoint supplies the
declared direct path for container image layers, and an EC2 Instance Connect
Endpoint supplies the private app management path. See [[Trust boundaries]] for
the security interpretation and [[Runtime containers]] for host service roles.

The two static frontends use separate private S3 buckets and CloudFront
distributions. A certificate stack lives in `us-east-1`, while DNS aliases,
distributions, buckets, and build-time SSM parameters are assembled in the main
environment region.

## CDK implementation boundary

The stack names in `infra/platforms/aws/cdk/app.py` do not all represent completed resource
sets.

| Stack area | Current implementation state |
| --- | --- |
| Security | Creates scoped KMS, Secrets Manager, SSM, IAM, and GitHub OIDC resources; imports the existing Route 53 zone and SES identity by reference. |
| Network | Creates the VPC, subnet groups, security groups, S3 gateway endpoint, and EC2 Instance Connect Endpoint for the split-host model. |
| Application | Creates proxy and app EC2 instances, an Elastic IP, and host roles, using a Packer AMI reference. It does not attach runtime bootstrap/user data, create backend or proxy ECR repositories, or create the public API DNS record. |
| Database | Is a placeholder and creates no RDS resources. Consequently the app stack's declared PostgreSQL destination is absent from CDK. |
| Frontend certificate and hosting | Create the cross-region certificate, private S3 origins, CloudFront distributions, DNS aliases, cache policies, deployment permissions, and frontend SSM parameters. |
| Observability | Is a placeholder and creates no log groups, alarms, or dashboard. |

Because the database, application bootstrap, image repositories, API DNS, and
observability pieces are incomplete, a successful synth is not evidence of a
functional full deployment.

## Deployment automation boundary

The checked-in deployment workflow builds and publishes both frontend artifacts
to the staging S3 buckets, then invalidates their CloudFront distributions. It
uses GitHub OIDC. A `workflow_run` deploys the exact commit from a successful
staging CI run; manual dispatch deploys its selected ref without itself requiring
a successful CI run. It does not publish or restart the backend,
run database provisioning or migrations, deploy CDK stacks, or deploy
production. Those procedures remain gaps for [[Cloud deployment]].

The repository contains shared host bootstrap scripts, but CDK and the deploy
workflow do not yet connect those scripts to EC2 provisioning or release
rollout. [[Machine image building]] owns the base-image path; the application
stack consumes a configured AMI ID or SSM AMI parameter rather than selecting a
generic latest image.

## External and manual dependencies

The Route 53 hosted zone and SES identity are imported rather than created by
the security stack. Full frontend synthesis also requires environment-specific
Auth0 public configuration and hosted-zone lookup context. These dependencies
mean a clean source checkout alone is insufficient to reproduce or verify a
live deployment. Configuration and secret ownership belong in
[[Secrets and configuration]], while exact resource locations belong in
[[Infrastructure implementation]] and [[Infrastructure resources]].

## Open questions

- Which checked-in topology, if any, matches the currently running production
  system?
- Will core and response storage use separate RDS instances or two databases on
  one instance? The database stack leaves this undecided.
- What process will provision runtime files, invoke bootstrap, publish container
  images, migrate databases, and roll back a backend release?
- When will the public API DNS record and certificate path be implemented and
  verified end to end?
- Which observability resources and release-health signals are required before
  staging or production can be considered operational?

## Related documents

- [[System context]]
- [[Runtime containers]]
- [[Trust boundaries]]
- [[Cloud deployment]]
- [[Machine image building]]
- [[Secrets and configuration]]
- [[Infrastructure implementation]]
- [[Infrastructure resources]]
