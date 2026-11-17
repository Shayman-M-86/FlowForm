---
title: AWS staging infrastructure target
aliases:
  - "AWS staging infrastructure target"
document_type: decision
status: verified
authority: canonical
verified_against_commit: 40476a8ea79dd07822d51daffcd8e2caf6174e3e
tags: [infrastructure, security, configuration, ci-cd]
related_code:
  - "../../infra/deployment/aws/cdk/app.py"
  - "../../infra/deployment/aws/cdk/flowform_infra/config/environments.py"
  - "../../infra/deployment/aws/cdk/flowform_infra/stacks/"
  - "../../infra/deployment/bootstrap/"
  - "../../infra/containers/runtime/"
  - "../../infra/images/"
  - "../../.github/workflows/"
related_docs:
  - "Architecture decision records"
  - "AWS CDK staging plan"
  - "Deployment model"
  - "Runtime containers"
  - "Trust boundaries"
  - "Secrets and configuration"
---

# AWS staging infrastructure target

Declares the accepted, normative infrastructure target for FlowForm staging.

## Status

**Accepted — 2026-07-23.**

This decision governs the staging implementation unless it is superseded by a
later ADR. It declares what the infrastructure shall become; it does not attest
that every resource is already implemented, deployed, or healthy. Current
implementation state remains documented in
[[deployment-model|Deployment model]], and delivery work remains in
[[aws-cdk-staging-plan|AWS CDK staging plan]].

## Context

FlowForm needs one AWS staging environment that exercises the production-shaped
security and runtime boundaries without paying for production availability.
The Proxmox rehearsal already establishes the useful separation between public
proxy, private application, databases, controlled egress, bootstrap,
configuration, secrets, and observability. AWS staging shall preserve those
responsibilities while replacing LocalStack, local registry, TLS shims,
fixture VMs, and workstation-owned convergence with native AWS facilities.

## Decision

FlowForm staging shall have this structure:

```text
public site and Studio
  -> Route 53
  -> CloudFront
  -> separate private S3 origins

API clients
  -> Route 53
  -> Elastic IP
  -> public proxy EC2: Caddy + Squid + Alloy
  -> private app EC2: Gunicorn/Flask + Alloy + Valkey
  -> private RDS PostgreSQL
       -> flowform_core database and app user
       -> flowform_response database and app user

private app outbound HTTPS
  -> Squid on proxy EC2
  -> approved AWS public endpoints and external services

ECR image layers
  -> regional S3 gateway endpoint

private ECR repositories
  -> Backend
  -> custom Caddy
  -> mirrored Squid
  -> mirrored Alloy
```

### Required boundaries

- CDK and CloudFormation shall own the staging AWS resource topology.
- The proxy EC2 instance shall be the only public runtime host.
- The application EC2 instance shall have no public address and no direct
  internet route.
- RDS shall be private and accept PostgreSQL only from the application security
  group.
- Caddy shall terminate public API TLS and forward only to the private
  application host.
- Squid shall be the application host's only general HTTP(S) egress route and
  shall allow only approved destination hostnames.
- The initial VPC shall have no NAT Gateway and no paid VPC interface
  endpoints.
- The only planned endpoints are the no-additional-charge S3 gateway endpoint
  and EC2 Instance Connect Endpoint.
- SSM Agent, host AWS CLI, Docker, backend containers, and migration containers
  shall use Squid for approved public AWS service endpoints.
- Regional ECR layer downloads shall bypass Squid and use the S3 gateway
  endpoint.
- EC2 instance roles shall provide AWS credentials. Static AWS credentials
  shall not be used.
- Non-secret staging runtime configuration shall use an environment-specific
  SSM namespace. File-backed secrets shall come from the `nonprod` Secrets
  Manager scope and be materialised into host tmpfs.
- Hosts shall converge from a Packer-built AMI, immutable ECR image digests,
  SSM configuration, Secrets Manager values, and idempotent systemd bootstrap.
- Backend, Caddy, Squid, and Alloy runtime images shall come from
  environment-owned private ECR repositories. Third-party Squid and Alloy
  images shall be mirrored rather than pulled from public registries at host
  convergence time.
- GitHub Actions shall use short-lived OIDC credentials with separate
  deployment, image-publication, frontend-publication, preview, and
  migration/release authority. Long-lived GitHub AWS credentials shall not be
  used.
- Image publishers and runtime hosts shall receive repository access only to
  their declared image set. The unavoidable account-wide
  `ecr:GetAuthorizationToken` action does not permit repository operations by
  itself.
- GitHub deployment identities shall not receive direct RDS connectivity or
  database-secret reads. Migration authority shall cross the controlled
  SSM/app-host boundary.
- Routine deployment control shall use SSM Run Command after its Squid path is
  proven. EC2 Instance Connect Endpoint shall provide the recovery path.
- Application logs and traces shall use Alloy and Grafana. AWS-native metrics
  and alarms shall cover the AWS infrastructure.

### Explicit exclusions

Initial staging shall not include:

- an Application Load Balancer;
- a NAT Gateway;
- ECS, EKS, or another container orchestrator;
- RDS Proxy;
- paid SSM, Secrets Manager, KMS, ECR, CloudWatch, or SES interface endpoints;
- public access to the application host or RDS;
- multi-AZ application or database capacity;
- two separate RDS instances for core and response data;
- ElastiCache while staging has only one application host;
- LocalStack, rehearsal TLS shims, fake service endpoints, or static AWS
  credentials;
- direct database access or database-secret retrieval from GitHub Actions; or
- a workstation command as a prerequisite for recovery after an ordinary host
  reboot or replacement.

These exclusions are deliberate constraints, not omissions to be filled
silently.

## Consequences

The design keeps staging close to the rehearsed FlowForm runtime and provides
real AWS identity, networking, storage, DNS, certificates, and service
integration at a controlled cost.

It also accepts single points of failure in the proxy, application host, and
single-AZ RDS instance. Squid availability and allowlist maintenance become
operational dependencies. Local Valkey rate-limit state is lost with the
application host. These consequences are acceptable for staging and are not a
claim of production-grade availability.

The architecture must be revisited before horizontal application scaling,
stronger environment isolation, production availability, or retained-data
cutover. Interface endpoints may be introduced individually only when evidence
shows that proxy reliability, compliance, or operating cost justifies them.

## Alternatives considered

- **ECS plus ALB:** deferred because it adds cost and orchestration that the
  initial single-application staging environment does not need.
- **NAT Gateway:** rejected because it adds material cost and gives the private
  app a broader egress path than the allowlisted proxy design.
- **Full PrivateLink endpoint set:** rejected for initial staging because the
  hourly endpoint cost exceeds the value while Squid can carry the required
  public AWS API traffic.
- **Two RDS instances or multi-AZ RDS:** deferred because one staging instance
  with separate databases and users preserves the logical boundary at lower
  cost.
- **ElastiCache:** deferred until more than one application host or durable
  shared rate-limit state is required.

## Change control

Changing a required boundary or adding an explicitly excluded service requires
a superseding ADR that records the new driver and consequences. Instance sizes,
retention periods, alarm thresholds, exact resource names, and other
implementation details may change without a new ADR when they preserve this
decision.

## References

- [[aws-cdk-staging-plan|AWS CDK staging plan]]
- [[deployment-model|Deployment model]]
- [[runtime-containers|Runtime containers]]
- [[trust-boundaries|Trust boundaries]]
- [[secrets-and-configuration|Secrets and configuration]]
- `infra/deployment/aws/cdk/`
- `infra/deployment/bootstrap/`
- `infra/containers/runtime/`

## Related documents

- [[50-decisions/README|Architecture decision records]]
- [[aws-cdk-staging-plan|AWS CDK staging plan]]
- [[deployment-model|Deployment model]]
- [[runtime-containers|Runtime containers]]
- [[trust-boundaries|Trust boundaries]]
- [[secrets-and-configuration|Secrets and configuration]]
