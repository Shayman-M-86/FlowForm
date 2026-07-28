---
title: AWS CDK staging plan
aliases: ["AWS CDK staging plan"]
document_type: planning
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-07-28
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
  - "AWS stack specifications"
  - "AWS database roles and bootstrap design"
  - "AWS DatabaseStack staging configuration"
---

# AWS CDK staging plan

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
| Network | Four-subnet design implemented and covered by CDK assertions | Deployed and verified on 2026-07-27 |
| Database | RDS infrastructure and IAM authentication implemented, asserted, synthesized, and diff-reviewed | Not deployed; first attempt rolled back |
| Database contents | Remote RDS bootstrap runner implemented and validated against PostgreSQL 17 | Never run against RDS |
| Application compute | EC2 resources and backend SSM parameters exist; user data and image references are missing | Not ready to deploy |
| Frontend | Substantial CDK and deployment support exists | Outside the immediate infrastructure slice |
| Observability | Placeholder CDK stack | Not deployed |

`FlowForm-Staging-Network` reached `CREATE_COMPLETE` on 2026-07-27. Live AWS
inspection confirmed its subnets, routes, endpoint boundary, private zone, flow
logs, Instance Connect Endpoint, and security groups. A post-deployment CDK
diff reported no differences, and CloudFormation drift detection reported
`IN_SYNC` with zero drifted resources.

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
- No NAT Gateway, Application Load Balancer, orchestrator, RDS Proxy, or
  continuously deployed paid VPC interface endpoints in the initial staging
  environment. The explicit database-bootstrap operation may create one
  temporary, tagged Secrets Manager endpoint and must remove it afterward.
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

The Network portion of Phase 3 is complete. `DatabaseStack` now also carries
RDS IAM database authentication, the `rds-db:connect` grant, and a remote
bootstrap runner for the database contents; the backend and app bootstrap
implement the matching IAM path.

The next slice is still to deploy `DatabaseStack` and prove the live RDS
infrastructure, then run the bootstrap runner against it. A first deployment
attempt failed and rolled back on an invalid parameter-group value, which has
since been corrected; the stack was deleted, so this is a fresh create.

Do not begin application-host deployment merely because the EC2 resources
synthesize: user data, convergence, and image references are still missing.
Outstanding work is tracked in
[[aws-iam-database-auth-loose-threads|AWS IAM database authentication loose
threads]].

### 1. Land the source through the staging workflow

Continue the established branch boundary:

1. Work and commit on `feature`.
2. Open a pull request into `staging`.
3. Review and approve the pull request.
4. Deploy the exact merged staging commit rather than an unmerged feature
   checkout.

The image-publication workflow already uses the protected staging identity.
Creating a general CDK deployment workflow is not required before the Database
deployment; operator deployment remains the controlled path for this slice.

### Completed Network deployment evidence

Live inspection on 2026-07-27 confirmed:

- `FlowForm-Staging-Network` is `CREATE_COMPLETE`.
- The four intended subnets exist:
  - proxy public A: `10.42.0.0/24` in `ap-southeast-2a`
  - app isolated A: `10.42.1.0/24` in `ap-southeast-2a`
  - RDS isolated A: `10.42.2.0/24` in `ap-southeast-2a`
  - RDS isolated B: `10.42.3.0/24` in `ap-southeast-2b`
- Only the proxy route table has a `0.0.0.0/0` Internet Gateway route.
- The app route table alone has the S3 prefix-list route through the available
  S3 gateway endpoint.
- No NAT Gateway or paid interface endpoint exists.
- The S3 endpoint policy grants only `s3:GetObject` on the regional ECR
  starport layer bucket.
- The private Route 53 zone is associated only with the staging VPC.
- The VPC flow log is active, delivery is successful, all traffic is selected,
  and `/flowform/staging/vpc-flow` has seven-day retention.
- The EC2 Instance Connect Endpoint is complete in the app subnet.
- Public ingress is limited to proxy TCP 80/443; app, RDS, Squid, Alloy, and
  management paths use the intended peer security groups.
- A post-deployment CDK diff found no differences.
- CloudFormation drift detection reported `IN_SYNC` with zero drifted
  resources.

Private DNS resolution, actual ECR layer routing, Squid service access, and
emitted cross-host flow records still require the real runtime instances and
remain Phase 4 checks.

### 2. Review, deploy, and verify `DatabaseStack`

The source now declares:

- one PostgreSQL 17.9 `db.t4g.small` instance, single-AZ in Availability Zone A;
- an explicit DB subnet group containing both isolated RDS subnets;
- only the existing RDS security group;
- 20 GiB encrypted gp3 storage with a 40 GiB autoscaling ceiling;
- an RDS-managed `flowform_admin` credential encrypted with the FlowForm KMS
  key;
- seven-day backups, retained automated backups, and a final snapshot on
  replacement or deletion;
- TLS and SCRAM requirements in a PostgreSQL 17 parameter group, using the
  RDS-specific `scram` value rather than PostgreSQL's `scram-sha-256` spelling;
- IAM database authentication, with `rds-db:connect` granted to the app role
  for exactly the two runtime database users;
- PostgreSQL and upgrade log exports with seven-day log retention;
- Standard database insights with seven-day performance history;
- explicit backup and maintenance windows, automatic minor updates, and no
  automatic major upgrade.

CDK tests, Pyright, synth, and a read-only AWS diff pass. The diff adds only the
DB subnet group, parameter group, two log groups, RDS instance, and the Network
stack outputs required for its existing subnets and security group. Review and
merge this source through the staging workflow, then deploy and verify the live
stack before marking the data portion of Phase 3 complete.

The database host is not the schema. The separate controlled bootstrap step now
creates the two logical databases, separate core and response users, baseline
application tables, grants, and `pgcrypto`, then verifies ownership,
privileges, and cross-database isolation. Later schema evolution remains an
explicit migration operation.

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
- RDS requires TLS; the two application identities authenticate with IAM tokens
  and hold no stored password; they are isolated from each other's database;
  `pgcrypto` works; migrations succeed.
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

Production availability, retained-data migration, and production cutover remain
separate work. Multi-AZ is not part of the current FlowForm infrastructure
target.

## Related documents

- [[planning-index|Engineering planning]]
- [[0001-aws-staging-infrastructure-target|ADR 0001: AWS staging infrastructure target]]
- [[aws-stack-specifications|AWS stack specifications]]
- [[aws-database-roles-and-bootstrap|AWS database roles and bootstrap design]]
- [[aws-database-stack-configuration|AWS DatabaseStack staging configuration]]
