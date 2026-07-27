---
title: AWS CDK staging plan
aliases: ["AWS CDK staging plan"]
document_type: planning
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-07-27
tags: [infrastructure, configuration, ci-cd]
related_code:
  - "../../../infra/deployment/aws/cdk/"
  - "../../../infra/deployment/bootstrap/"
  - "../../../infra/containers/"
  - "../../../infra/images/"
  - "../../../.github/workflows/"
related_docs:
  - "Engineering planning"
  - "ADR 0001: AWS staging infrastructure target"
---

# AWS CDK staging plan
wwa
> Working execution plan, not current architecture or live-deployment truth.

This plan sequences the first empty-data AWS staging environment around the
boundaries in [[0001-aws-staging-infrastructure-target|ADR 0001]]. It was
restored into the Development Workspace from the historical documentation
after the documentation reorganisation, then reconciled with the current CDK
source on 2026-07-27.

It covers CDK resources, host bootstrap, runtime configuration, release
ordering, and acceptance evidence. It does not claim production availability,
a retained-data cutover, or that a source-complete stack has been deployed.

## Current checkpoint

| Area | Source status | Live status |
| --- | --- | --- |
| Target decision | Recorded in ADR 0001 | Not applicable |
| Security and registry | Implemented | Last recorded as deployed on 2026-07-24 |
| Image publication | Implemented and exercised through GitHub OIDC | Four-image digest manifest recorded by the earlier execution slice |
| Network | Four-subnet design implemented and covered by CDK assertions | Deployment and live verification not confirmed |
| Database | Placeholder only | Not deployed |
| Application compute | EC2 resource skeleton exists; convergence/bootstrap is incomplete | Not ready to deploy |
| Frontend | Substantial CDK and deployment support exists | Outside the immediate infrastructure slice |
| Observability | Placeholder CDK stack | Not deployed |

The live network status could not be refreshed on 2026-07-27 because the local
AWS CLI session had expired. Re-authenticate and inspect CloudFormation before
treating the Network stack as absent or present.

Image vulnerability triage is deliberately deferred while the staging
infrastructure is assembled. It remains a release-readiness gate and must not
be interpreted as accepted risk for production.

## Hard decisions

The staging target deliberately resembles the Proxmox rehearsal by preserving
responsibility boundaries rather than copying its shims:

- One public proxy EC2 host running Caddy, Squid, and Alloy.
- One private application EC2 host running the backend, Alloy, and local
  Valkey.
- One private, encrypted, single-AZ RDS PostgreSQL instance containing separate
  logical core and response databases.
- One public proxy subnet, one isolated application subnet, and one isolated
  RDS subnet in Availability Zone A.
- A second isolated RDS subnet in Availability Zone B only because an RDS DB
  subnet group must span two Availability Zones.
- No NAT Gateway, Application Load Balancer, orchestrator, RDS Proxy, or paid
  VPC interface endpoints in the initial staging environment.
- One S3 gateway endpoint for ECR layer traffic.
- AWS service API traffic from the private app host travels through the Squid
  allowlist and the proxy host's Internet Gateway path.
- The application instance and RDS are never publicly reachable.
- GitHub uses short-lived OIDC identities; static AWS credentials are not part
  of the deployment design.
- Images are published independently from release promotion and are deployed
  by complete ECR digest.
- Secrets remain file-backed at runtime. Non-secret runtime configuration is
  stored in SSM Parameter Store.
- CDK creates infrastructure and credentials. Database schema creation and
  migrations remain explicit release operations, not CloudFormation custom
  resources.

```text
Internet
   |
   v
Proxy EC2 in public subnet A
   |  Caddy -> backend:5000
   |  Squid <- app:3128
   v
App EC2 in isolated subnet A ----> RDS in isolated subnet A
   |                                  |
   +----> S3 gateway endpoint         +-- DB subnet group also includes
   |                                      isolated RDS subnet B
   +----> approved public services through Squid
```

## Immediate next execution slice

The next slice is to deploy and prove `FlowForm-Staging-Network`, then implement
`DatabaseStack`. Do not begin application-host deployment merely because the
EC2 resources synthesize: their bootstrap and convergence path is incomplete.

### 1. Land the source through the staging workflow

Continue the established branch boundary:

1. Work and commit on `feature`.
2. Open a pull request into `staging`.
3. Review and approve the pull request.
4. Deploy the exact merged staging commit rather than an unmerged feature
   checkout.

The image-publication workflow already uses the protected staging identity.
Creating a general CDK deployment workflow is not required before the first
Network deployment; operator deployment remains the controlled path for this
slice.

### 2. Re-authenticate and inspect before deploying

From `infra/deployment/aws/cdk/`:

```bash
aws login
aws cloudformation describe-stacks \
  --region ap-southeast-2 \
  --stack-name FlowForm-Staging-Network
```

If the stack does not exist, review and deploy it:

```bash
npx cdk diff -c env=staging FlowForm-Staging-Network
npx cdk deploy -c env=staging FlowForm-Staging-Network
```

Keep approval enabled and inspect the CloudFormation change set. If the stack
already exists, compare it with the merged staging source before deciding
whether an update is required.

### 3. Prove the deployed network boundary

Record deployed evidence for:

- Exactly four subnets with the intended CIDRs:
  - proxy public A: `10.42.0.0/24`
  - app isolated A: `10.42.1.0/24`
  - RDS isolated A: `10.42.2.0/24`
  - RDS isolated B: `10.42.3.0/24`
- Only the proxy subnet has a default Internet Gateway route.
- No NAT Gateway and no paid interface endpoint exist.
- The S3 gateway endpoint is associated only with the application subnet route
  table and has the intended ECR layer-bucket read policy.
- The private Route 53 zone is associated with the staging VPC.
- The VPC flow log is active and targets
  `/flowform/staging/vpc-flow`.
- Security-group paths match the declared proxy, application, RDS, Alloy, DNS,
  NTP, S3, and EC2 Instance Connect Endpoint flows.

Do not create temporary hosts solely to prove runtime behaviour. Private DNS
resolution, actual ECR layer routing, Squid service access, and emitted
cross-host flow records belong to the compute phase when the real instances
exist.

### 4. Implement `DatabaseStack`

After network proof, replace the placeholder with:

- One single-AZ staging RDS PostgreSQL instance using a supported PostgreSQL
  version compatible with the application.
- A DB subnet group containing the two RDS subnets.
- Placement in Availability Zone A without enabling Multi-AZ.
- Ingress on TCP 5432 only from the application security group.
- Storage encryption using the FlowForm KMS key.
- A generated administrative credential in Secrets Manager.
- Automated backups with an explicit staging retention period.
- TLS enforcement and SCRAM authentication.
- PostgreSQL and upgrade log exports.
- Staging removal and deletion-protection behaviour from `EnvConfig`.
- CDK assertions for placement, encryption, credentials, networking, backup,
  logging, and removal behaviour.

The database host is not the schema. A later controlled migration/bootstrap
step must create the two logical databases, separate core and response users,
their grants, and `pgcrypto`, then prove that neither application user can
access the other database.

## Completed phases

### Phase 1: Accept the target

The target topology, exclusions, availability trade-offs, management model,
database shape, and scope boundaries are recorded in ADR 0001. Reopen the ADR
if one of those hard decisions changes; do not quietly change them in an
implementation phase.

### Phase 2: Establish registry and security contracts

The current source provides:

- Backend, custom Caddy, Squid mirror, and Alloy mirror ECR repositories.
- Immutable tags, scan-on-push, KMS encryption, and lifecycle controls.
- Exact publisher and runtime repository grants, apart from the account-wide
  ECR authorization action required by AWS.
- A staging-branch GitHub OIDC image-publisher role.
- Pinned, reproducible image inputs.
- A dedicated image-publication workflow that does not deploy infrastructure
  or promote a release.
- A machine-readable four-image digest handoff.

Security continues to evolve with its consumers. Database work adds only its
credential/KMS grants; compute adds its exact SSM, ECR, Route 53, and release
permissions; observability adds only the permissions its selected signals
need.

## Remaining phases

### Phase 3: Finish network and data

Complete the immediate execution slice above. Phase 3 exits only after the
Network stack has deployed evidence and the RDS infrastructure and credential
contracts are implemented, deployed, and checked.

### Phase 4: Make compute self-converging

Complete the proxy and application path:

- Consume the Packer-built Amazon Linux 2023 AMI through its SSM parameter.
- Attach only user data and bootstrap inputs needed to select host,
  environment, scope, region, and release.
- Run the shared Compose bases with AWS strategy configuration.
- Configure the proxy host first and signal readiness only after Squid and the
  proxy services are healthy.
- Configure the app host's AWS CLI, Docker daemon, backend/migration
  containers, and SSM Agent to use Squid.
- Bypass Squid for IMDS, local/direct VPC services, RDS, and the regional S3
  path used by the gateway endpoint.
- Materialise secrets into root-owned tmpfs files and render non-secret runtime
  configuration from SSM.
- Pull all images by digest and converge after first boot, reboot, and host
  replacement without a workstation.

The local Valkey container is acceptable for authoritative rate limits across
multiple Gunicorn workers on this single app host. Revisit ElastiCache before
horizontal application scaling or when limiter state must survive host
replacement.

### Phase 5: Complete runtime configuration

Publish a complete staging contract for image digests, URLs, CORS, Auth0, RDS,
KMS, SES, rate limiting, trusted proxies, observability, and the proxy
destination allowlist.

Keep environment configuration under `/flowform/staging/...` and shared
non-production security material under the `nonprod` scope. Staging must not
contain LocalStack endpoints, fake DNS, TLS-shim configuration, registry
rewrites, or static AWS credentials.

### Phase 6: Integrate frontend and public DNS

Finish the existing frontend/certificate support with API DNS, Caddy DNS-01
TLS, staging API URLs, explicit CORS origins, matching Auth0 callback/origin
configuration, and coordinated frontend publication.

### Phase 7: Add observability and recovery

Implement the placeholder Observability stack. Preserve the Alloy/Grafana log
and trace path while adding selected CloudWatch alarms, public/private health
checks, VPC-flow visibility, and a tested recovery path. Keep Grafana
credentials file-backed and out of SSM, user data, logs, and CloudFormation
outputs.

### Phase 8: Build the staging release pipeline

Automate the already-proven manual boundaries in order:

1. Require green CI for the exact staging commit.
2. Build/publish changed AMIs and immutable images.
3. Deploy foundation stacks.
4. Seed required secrets and promote reviewed runtime parameters/digests.
5. Converge the proxy, then the application.
6. Run controlled database migrations.
7. Prove private readiness and public API health.
8. Publish both frontends from the same commit.
9. Run smoke/E2E checks and record the release.

Keep infrastructure deployment, image publication, runtime promotion, and
database migration as distinct authorities even if one release workflow later
orchestrates them.

## Staging acceptance gate

Staging is ready for application use only when:

- CDK tests, synth, diff review, and deployment pass.
- Both hosts self-converge after reboot and app-host replacement.
- API HTTPS and DNS work through Caddy.
- App and RDS have no direct public path.
- No NAT Gateway or paid interface endpoints exist.
- Required AWS and external service access from the app works through Squid,
  while ECR S3 layers use the S3 gateway endpoint.
- Squid rejects an unapproved destination and IMDS bypasses Squid.
- RDS requires TLS; the two application identities are isolated; `pgcrypto`
  works; migrations succeed.
- Auth0, explicit staging CORS, legitimate SES sending, and public survey flows
  pass end to end.
- The removed test-email route returns `404`.
- Rate limits remain authoritative across Gunicorn workers and spoofed
  forwarding headers do not bypass them.
- Logs and traces arrive without secrets, selected alarms are exercised, and
  snapshot restore is rehearsed.
- A known-good backend digest can be rolled back.
- Deferred image vulnerabilities have been triaged before staging is described
  as release-ready.

Production availability, retained-data migration, Multi-AZ resources, and
production cutover remain separate work.

## Related documents

- [[planning-index|Engineering planning]]
- [[0001-aws-staging-infrastructure-target|ADR 0001: AWS staging infrastructure target]]
