---
title: AWS stack specifications
aliases: ["AWS stack specifications"]
document_type: planning
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-07-28
tags: [infrastructure, configuration, security, ci-cd]
related_code:
  - "../../../infra/deployment/aws/cdk/app.py"
  - "../../../infra/deployment/aws/cdk/flowform_infra/config/"
  - "../../../infra/deployment/aws/cdk/flowform_infra/constructs/"
  - "../../../infra/deployment/aws/cdk/flowform_infra/stacks/"
  - "../../../infra/deployment/aws/cdk/tests/"
  - "../../../infra/deployment/bootstrap/"
  - "../../../.github/workflows/"
related_docs:
  - "Engineering planning"
  - "AWS CDK staging plan"
  - "ADR 0001: AWS staging infrastructure target"
  - "AWS DatabaseStack staging configuration"
  - "Deployment model"
  - "AWS network topology"
  - "Cloud deployment"
---

# AWS stack specifications

> Working source specification, not a live AWS inventory.

This document is the consolidated settings itinerary for FlowForm's AWS CDK
application. It records the resources and contracts currently declared in
source, the differences between environments, the last recorded deployment
state, and the gaps that still prevent a complete release.

The CDK source and its tests remain authoritative for synthesis behavior.
CloudFormation and live AWS inspection remain authoritative for deployed
state. A resource described as implemented here is not necessarily deployed.

## Status language

| Label | Meaning |
| --- | --- |
| Implemented | The current CDK source synthesizes the resource or setting. |
| Asserted | A CDK test checks the material contract. |
| Recorded deployed | An active working document records a successful deployment, but this page did not re-query AWS. |
| Live verified | The active documentation records post-deployment inspection and drift evidence. |
| Source only | Implemented or partly implemented, with no accepted live-deployment evidence. |
| Placeholder | A stack class exists but creates no functional resources. |
| Planned | The intended behavior is documented but not implemented in the stack. |

CDK-generated support resources, such as custom-resource Lambda functions,
provider roles, metadata, and cross-region export helpers, are not treated as
independent FlowForm service components below. They are called out where they
affect deployment permissions or lifecycle.

## Environment composition

All environments currently target AWS account `908123139858`. The normal
application region is `ap-southeast-2`.

| Setting | Development | Staging | Production |
| --- | --- | --- | --- |
| CDK environment name | `dev` | `staging` | `prod` |
| Full deployment | No | Yes | Yes |
| Security scope | `nonprod` | `nonprod` | `prod` |
| General removal policy | Destroy | Destroy | Retain |
| Deletion protection input | Disabled | Disabled | Enabled |
| Environment tag | `flowform:env=dev` | `flowform:env=staging` | `flowform:env=prod` |
| Application region | `ap-southeast-2` | `ap-southeast-2` | `ap-southeast-2` |
| Frontend certificate region | Not created | `us-east-1` | `us-east-1` |
| Public site domain | Local only | `staging.flow-form.com.au` | `flow-form.com.au`, plus `www.flow-form.com.au` |
| Studio domain | Local only | `studio.staging.flow-form.com.au` | `studio.flow-form.com.au` |
| Private hosted zone | Not created | `internal.staging.flow-form.com.au` | `internal.flow-form.com.au` |
| Packer AMI parameter | Unused | `/flowform/staging/ec2/baseAmiId` | `/flowform/prod/ec2/baseAmiId` |
| EC2 root volume | Unused | 10 GiB encrypted GP3 | 10 GiB encrypted GP3 |

Development synthesizes only `FlowForm-Nonprod-Security`. Its application,
PostgreSQL services, and frontends remain local. Staging and production
construct the complete stack graph.

The Auth0 public domain, client ID, and audience are loaded from the gitignored
`infra/deployment/aws/cdk/.env.<environment>` file. A full frontend synthesis
fails closed when any of those values is absent.

## Stack names and current delivery status

| Stack role | Development | Staging | Production | Current evidence |
| --- | --- | --- | --- | --- |
| Security | `FlowForm-Nonprod-Security` | Same shared nonproduction stack | `FlowForm-Prod-Security` | Nonproduction recorded deployed on 2026-07-24; production source only |
| Registry | Not created | `FlowForm-Staging-Registry` | `FlowForm-Prod-Registry` | Staging recorded deployed on 2026-07-24; production source only |
| Network | Not created | `FlowForm-Staging-Network` | `FlowForm-Prod-Network` | Staging deployed and live verified on 2026-07-27; production source only |
| Database | Not created | `FlowForm-Staging-Database` | `FlowForm-Prod-Database` | Source implemented and asserted; neither environment recorded deployed |
| Application | Not created | `FlowForm-Staging-Application` | `FlowForm-Prod-Application` | Resource skeleton only; bootstrap is incomplete and deployment is not ready |
| Frontend certificate | Not created | `FlowForm-Staging-FrontendCert` | `FlowForm-Prod-FrontendCert` | Source implemented; live state is not established by the active plan |
| Frontend | Not created | `FlowForm-Staging-Frontend` | `FlowForm-Prod-Frontend` | Source implemented; live CDK state is not established by the active plan |
| Observability | Not created | `FlowForm-Staging-Observability` | `FlowForm-Prod-Observability` | Placeholder only |

The production apex currently has a hand-made Amplify association. That
association is not part of these CDK stacks and must be handled as an explicit
cutover before the production CloudFront aliases can own the domain.

## Stack dependency and construct contracts

```text
Security
  |-- KMS key ----------------> Registry, Database, Application
  |-- image publisher role ---> Registry
  |-- application role -------> Application
  |-- hosted-zone reference --> Application
  `-- frontend deploy role ---> Frontend

Network
  |-- VPC/subnets/SGs --------> Database
  `-- VPC/subnets/SGs/zone ---> Application

Registry
  `-- repository references --> Application

Database
  `-- deployment dependency --> Application

Frontend certificate
  `-- ACM certificate --------> Frontend

Application
  `-- deployment dependency --> Observability
```

The application stack currently depends on the database stack only through an
explicit deployment dependency. It does not yet consume the RDS endpoint or
managed administrative secret. The database exposes those as construct
properties for later wiring.

Prefer construct references such as the KMS key, role, subnet, security group,
repository, and certificate objects over reconstructing names or ARNs. Stable
names are used only where an external workflow or operator must address a
resource without first reading a CloudFormation output.

## Security stack

### Ownership and scope

`SecurityStack` is scope-based rather than environment-based:

| Setting | Nonproduction scope | Production scope |
| --- | --- | --- |
| Stack | `FlowForm-Nonprod-Security` | `FlowForm-Prod-Security` |
| Consumers | Development and staging | Production |
| KMS alias | `alias/flowform-nonprod` | `alias/flowform-prod` |
| Removal policy | Destroy | Retain |
| Local account assume-role access | Enabled | Disabled |
| Creates GitHub OIDC provider | Yes | No; imports the account provider ARN |
| CI environment subject | `environment:staging` | `environment:prod` |
| CI preview branch subject | `refs/heads/staging` | `refs/heads/main` |

All SecurityStack inputs derive from `SecurityScopeConfig`. Synthesizing the
nonproduction stack through `dev` or `staging` must produce an identical
template.

### Implemented resources

- One customer-managed KMS key with automatic rotation.
- One stable KMS alias.
- Three KMS-encrypted Secrets Manager secrets:
  - `flowform/<scope>/app-secrets`, containing `app_secret_key` and
    `auth0_mgmt_secret`;
  - `flowform/<scope>/db-secrets`, containing
    `db_core_app_password` and `db_response_app_password`;
  - `flowform/<scope>/linkage-secret`, containing the versioned linkage HMAC
    material.
- Five non-secret SSM parameters:
  - `/flowform/<scope>/kms-key-arn`;
  - `/flowform/<scope>/aws-region`;
  - `/flowform/<scope>/linkage-secret-arn`;
  - `/flowform/<scope>/hosted-zone-id`;
  - `/flowform/<scope>/app-role-arn`.
- One application EC2 role.
- Three named GitHub OIDC roles:
  - `flowform-<ci-env>-frontend-deploy`;
  - `flowform-<ci-env>-ci-preview`;
  - `flowform-<ci-env>-image-publisher`.
- The account-level GitHub OIDC provider in the nonproduction stack.
- Imported references to the manually managed `flow-form.com.au` Route 53
  hosted zone and SES domain identity.

The generated secret values are placeholders. Required operational values are
seeded out of band so plaintext values do not enter source or CloudFormation
templates.

### Permissions

The application role:

- is assumable by EC2;
- is also assumable by account principals in nonproduction for local
  development;
- can read the three scope secrets;
- can encrypt and decrypt with the FlowForm KMS key;
- can send email through the imported SES domain identity;
- can read `/flowform/<scope>/*` and `/flowform/<ci-env>/*` SSM parameters.

The frontend and image-publisher roles trust only the matching protected GitHub
environment subject. The preview role trusts only the configured protected
branch and carries AWS `ReadOnlyAccess`. Repository, bucket, distribution, and
frontend-parameter permissions are attached by their owning consumer stacks.

### Boundaries and gaps

- The public hosted zone remains permanently manual because replacing it would
  change registrar nameservers.
- The SES identity is imported and remains manual for now.
- No general-purpose GitHub CDK deployment role is implemented.
- No observability secret is created despite the runtime parameter contract
  reserving an `observability-secrets` name.
- Secret rotation automation is not implemented here.

## Registry stack

### Implemented resources

Each full-deployment environment receives four private ECR repositories:

| Image | Staging repository | Production repository |
| --- | --- | --- |
| Backend | `flowform-staging-backend` | `flowform-prod-backend` |
| Caddy | `flowform-staging-caddy` | `flowform-prod-caddy` |
| Squid | `flowform-staging-squid` | `flowform-prod-squid` |
| Alloy | `flowform-staging-alloy` | `flowform-prod-alloy` |

Every repository uses:

- immutable tags;
- scan-on-push;
- KMS encryption with the environment security-scope key;
- expiry of untagged images after seven days;
- digest-compatible publication and consumption.

| Lifecycle setting | Staging | Production |
| --- | --- | --- |
| Retained image count | 30 | 100 |
| CloudFormation removal | Destroy | Retain |
| Empty repository during stack deletion | Yes | No |

The image-publisher policy permits account-wide
`ecr:GetAuthorizationToken`, as required by ECR, and upload/describe operations
only on these four repository ARNs. The current publication workflow produces
a four-image digest manifest but does not promote those digests to hosts.

### Boundaries and gaps

- Basic ECR scan findings are currently deferred as a release-readiness task.
- Repository creation and image publication are separate authorities.
- The stack does not decide which digest is active in an environment.
- Cross-region or cross-account replication is not configured.

## Network stack

### VPC and subnet specification

The staging and production source use the same low-cost topology:

| Resource | CIDR | Placement | Route intent |
| --- | --- | --- | --- |
| VPC | `10.42.0.0/16` | `ap-southeast-2` | Environment boundary |
| Proxy public A | `10.42.0.0/24` | Availability Zone A | Internet Gateway default route |
| Application isolated A | `10.42.1.0/24` | Availability Zone A | S3 gateway route and local VPC routes |
| RDS isolated A | `10.42.2.0/24` | Availability Zone A | Local VPC routes only |
| RDS isolated B | `10.42.3.0/24` | Availability Zone B | Local VPC routes only; DB subnet-group requirement |

The second RDS subnet does not represent a Multi-AZ design. Application,
proxy, and database resources are intended to run in Availability Zone A.

### Implemented resources and routing

- One VPC with no generated subnet layout.
- One Internet Gateway attached to the VPC.
- Four explicit subnets and route tables.
- Exactly one `0.0.0.0/0` route, on the proxy subnet.
- No NAT Gateway.
- One free S3 gateway endpoint associated only with the application subnet.
- An endpoint policy allowing `s3:GetObject` only from the regional ECR
  starport layer bucket.
- One environment-specific private Route 53 hosted zone.
- One EC2 Instance Connect Endpoint in the application subnet, with client IP
  preservation disabled.
- One VPC flow log covering accepted and rejected traffic, with a ten-minute
  aggregation interval.

| Environment | Private zone | Flow-log group | Retention |
| --- | --- | --- | --- |
| Staging | `internal.staging.flow-form.com.au` | `/flowform/staging/vpc-flow` | 7 days |
| Production | `internal.flow-form.com.au` | `/flowform/prod/vpc-flow` | 90 days |

The environment removal policy is explicitly applied to the flow-log group.
The VPC, subnets, gateways, endpoint, hosted zone, and security groups otherwise
use their constructs' normal CloudFormation lifecycle.

### Security-group paths

All four security groups disable default unrestricted egress.

| Source | Destination | Port | Purpose |
| --- | --- | --- | --- |
| Public IPv4 | Proxy | TCP `80`, `443` | Caddy ingress |
| Application SG | Proxy SG | TCP `3128` | Squid forward proxy |
| Application SG | Proxy SG | TCP `3500`, `4317` | Alloy log and trace gateways |
| Proxy SG | Application SG | TCP `5000` | Caddy to backend |
| Application SG | RDS SG | TCP `5432` | PostgreSQL |
| EICE SG | Application SG | TCP `22` | Private recovery access |
| Application SG | Regional S3 prefix list | TCP `443` | ECR layer downloads |
| Proxy SG | Public IPv4 | TCP `443` | Approved external HTTPS egress |

Proxy and application hosts also receive the bounded DNS and Amazon Time Sync
paths declared in `NetworkStack`. Squid owns destination allowlisting; the
security groups only establish reachability.

### Exclusions

- No NAT Gateway.
- No paid VPC interface endpoints.
- No Application Load Balancer.
- No public application or RDS route.
- No duplicate proxy or application subnets for high availability.
- No Multi-AZ database design.

## Database stack

### Shared implemented specification

- One private RDS PostgreSQL instance.
- PostgreSQL `17.9`, explicitly pinned.
- PostgreSQL parameter family `postgres17`.
- `db.t4g.small`.
- Single-AZ placement in `ap-southeast-2a`.
- `MultiAZ: false`.
- IPv4 and TCP `5432`.
- No public accessibility.
- A DB subnet group containing RDS subnets A and B.
- Only the NetworkStack RDS security group.
- Encrypted GP3 storage using the environment FlowForm KMS key.
- Master username `flowform_admin`.
- RDS-managed master password, with its secret encrypted by the FlowForm KMS
  key.
- `rds.force_ssl = 1`.
- SCRAM-SHA-256 password encryption and accepted authentication.
- PostgreSQL and upgrade log exports.
- Database Insights Standard and Performance Insights with seven-day history.
- Tag copying to snapshots.
- Automatic minor-version upgrades during maintenance.
- No automatic major-version upgrade and no immediate application of changes.
- Backup window `16:00-16:30` UTC.
- Maintenance window `sun:17:00-sun:18:00` UTC.

### Environment differences

| Setting | Staging | Production |
| --- | --- | --- |
| Identifier | `flowform-staging-postgres` | `flowform-prod-postgres` |
| Instance class | `db.t4g.small` | `db.t4g.small` |
| Initial storage | 20 GiB | 20 GiB |
| Storage autoscaling ceiling | 40 GiB | 50 GiB |
| Backup retention | 7 days | 30 days |
| PostgreSQL/upgrade log retention | 7 days | 90 days |
| Deletion protection | Disabled | Enabled |
| DB removal policy | Snapshot | Retain |
| Log-group removal policy | Destroy | Retain |

Staging retains automated backups and takes a final snapshot on deletion or
replacement. Production retains the DB resource and enables deletion
protection. Neither environment is designed for Multi-AZ.

### Exclusions and later bootstrap

The stack does not create:

- the `flowform_core` and `flowform_response` logical databases;
- migration, owner, or application PostgreSQL roles;
- grants, schemas, tables, or extensions;
- application connection-pool settings;
- IAM database authentication;
- RDS Proxy;
- Enhanced Monitoring;
- a dedicated Performance Insights KMS key.

Those database-content responsibilities remain a controlled migration/bootstrap
operation. The CDK stack exposes the managed administrative secret and
non-secret endpoint as constructs but does not publish secret values.

## Application stack

### Currently implemented resource skeleton

The application stack creates two EC2 instances in Availability Zone A:

| Host | Current instance class | Subnet | Public address | Workload intent |
| --- | --- | --- | --- | --- |
| Proxy | `t3.small` | Proxy public A | Deliberate Elastic IP | Caddy, Squid, Alloy |
| Application | `t3.small` | Application isolated A | None | Backend, Alloy, local Valkey |

The source currently emits `t3.small` through CDK's `BURSTABLE3` instance
class. Older comments describing `t4g.small` are an intended direction, not
the synthesized setting.

Both instances use:

- the Packer-built AMI selected through the environment SSM parameter, unless
  an explicit break-glass AMI ID override is supplied;
- one 10 GiB encrypted GP3 root volume;
- deletion of the root volume on instance termination;
- required IMDSv2 tokens;
- an IMDS response hop limit of two for container credential access;
- the NetworkStack security group for their host role.

The application host explicitly has no public IP. The proxy subnet also
disables automatic public-IP assignment; the stack attaches one explicit
Elastic IP to the proxy instance.

The stack publishes one-minute private A records:

| Environment | Proxy record | Application record |
| --- | --- | --- |
| Staging | `proxy.internal.staging.flow-form.com.au` | `app.internal.staging.flow-form.com.au` |
| Production | `proxy.internal.flow-form.com.au` | `app.internal.flow-form.com.au` |

### IAM and ECR access

The proxy role:

- is EC2-assumable;
- carries `AmazonSSMManagedInstanceCore`;
- can update records only in the imported `flow-form.com.au` hosted zone;
- can query Route 53 change status and locate the hosted zone;
- can pull Caddy, Squid, and Alloy repositories.

The application instance uses the SecurityStack application role and can pull
only the backend and Alloy repositories. Both host policies use the
account-wide ECR authorization action and repository-specific layer and image
reads.

### Incomplete behavior

The stack is not ready to deploy because it does not yet:

- attach user data or invoke the shared host bootstrap;
- configure the Docker daemon, AWS CLI, SSM Agent, or containers to use Squid;
- render proxy or backend environment files;
- materialize file-backed secrets into tmpfs;
- select and promote active image digests;
- start or health-check either Compose project;
- enforce proxy-before-application convergence;
- consume the database endpoint or application database credentials;
- create the public `api.<domain>` Route 53 record;
- prove reboot or replacement convergence;
- apply an explicit production retention policy to the EC2 instances or EIP.

The `kms_key` input is stored on the stack object but is not directly consumed
by an ApplicationStack resource. KMS access instead arrives through the shared
application role.

## Frontend certificate stack

The certificate stack is created only for staging and production and is pinned
to `us-east-1`, as required by CloudFront. It imports the manually managed
`flow-form.com.au` hosted zone and creates one DNS-validated ACM certificate.

| Environment | Primary name | Subject alternative names |
| --- | --- | --- |
| Staging | `staging.flow-form.com.au` | `studio.staging.flow-form.com.au` |
| Production | `flow-form.com.au` | `www.flow-form.com.au`, `studio.flow-form.com.au` |

CDK cross-region references pass the certificate to FrontendStack and synthesize
support custom resources in both regions. No explicit certificate removal
policy is set. The stack does not create the API certificate used by Caddy.

## Frontend stack

### Static applications

Each environment receives two private S3/CloudFront applications:

| Application | Staging bucket/domain | Production bucket/domain |
| --- | --- | --- |
| Public site | `flowform-staging-public-site` / `staging.flow-form.com.au` | `flowform-prod-public-site` / `flow-form.com.au`, `www.flow-form.com.au` |
| Studio | `flowform-staging-studio-app` / `studio.staging.flow-form.com.au` | `flowform-prod-studio-app` / `studio.flow-form.com.au` |

Each site has:

- a private S3 bucket with all public access blocked;
- S3-managed encryption and enforced TLS;
- CloudFront Origin Access Control;
- a CloudFront distribution that redirects viewers to HTTPS;
- TLS policy `TLSv1.2_2021`;
- Route 53 aliases for every declared domain;
- `index.html` as the default root;
- 403 and 404 SPA fallback to `/index.html`;
- bucket-name and distribution-ID CloudFormation outputs.

Staging buckets are destroyed and emptied with the stack. Production buckets
are retained and are not automatically emptied.

### Shared cache policy

| Tier | Paths | Browser header | Edge defaults |
| --- | --- | --- | --- |
| Immutable | `/_astro/*`, `/assets/*`, `*.woff2`, `*.woff` | One year, immutable | One year |
| Media | Common image extensions | One day with one-week stale-while-revalidate | One day, maximum one week |
| HTML/default | `index.html` and unmatched paths | `no-cache` | Five minutes, maximum one hour |

The two applications share one set of three CloudFront cache policies and three
response-header policies per environment stack.

### Build-time parameters and deployment authority

FrontendStack publishes six SSM parameters under
`/flowform/<environment>/frontend/`:

- `vite-auth0-domain`;
- `vite-auth0-client-id`;
- `vite-auth0-audience`;
- `vite-api-base-url`;
- `public-site-distribution-id`;
- `studio-app-distribution-id`.

The API base URL is `https://api.<public-site-domain>`. The frontend deployment
role can read those parameters, synchronize only the two environment buckets,
and invalidate only the two distributions.

### Gaps

- The API DNS record and reachable Caddy endpoint do not yet exist.
- A complete backend release is not coordinated with frontend publication.
- CloudFront access logging, WAF, and explicit security-header policies beyond
  the declared cache-control headers are not configured here.
- Production requires an explicit Amplify-to-CloudFront domain cutover.
- Full app synthesis requires the external Auth0 public configuration.

## Observability stack

`ObservabilityStack` is currently a placeholder. Its synthesized template
contains no functional observability resources.

The source TODO still refers to ECS and an ALB, which no longer match the
accepted EC2/Caddy topology. It must be rewritten before implementation.

The intended boundary is:

- AWS-native CloudWatch log groups, metrics, alarms, health checks, and a
  dashboard where useful;
- RDS connection, storage, backup, and availability signals;
- EC2 and host health for the proxy and application instances;
- public API and private readiness checks;
- preservation of the existing Alloy-to-Grafana Cloud logs and traces path;
- file-backed Grafana credentials outside CloudFormation, SSM plaintext, user
  data, and logs;
- snapshot and recovery evidence.

No alarm thresholds, dashboard widgets, notification destinations, synthetic
checks, or retention policies are accepted in source yet.

## Cross-stack exclusions and deferred infrastructure

The current target deliberately excludes:

- NAT Gateway;
- Application Load Balancer;
- ECS, EKS, or another orchestrator;
- horizontal application scaling;
- RDS Proxy;
- Multi-AZ RDS;
- paid VPC interface endpoints;
- public application or database instances;
- static GitHub AWS credentials;
- automatic schema creation through CloudFormation custom resources.

Image publication, infrastructure deployment, runtime digest promotion,
database migration, host convergence, and frontend publication remain distinct
authorities. The existing GitHub workflows publish runtime images and
frontends; they do not deploy CDK, migrate the database, or converge the
application hosts.

## Verification itinerary

For every material stack change:

1. Run the relevant CDK assertions and the complete CDK test suite.
2. Run Ruff and Pyright for the CDK package.
3. Synthesize the exact environment with required context and external public
   configuration.
4. Review `cdk diff`, including IAM and replacement behavior.
5. Merge through the protected deployment branch.
6. Deploy the exact reviewed commit.
7. Inspect CloudFormation status and outputs.
8. Query the created AWS resources directly.
9. Run CloudFormation drift detection.
10. Exercise the stack-specific runtime and recovery checks.
11. Update the live-status column here only when evidence exists.

An implemented or synthesized stack must not be described as live. A deployed
stack must not be described as verified until its material settings and runtime
paths have been inspected.

## Related documents

- [[planning-index|Engineering planning]]
- [[aws-cdk-staging-plan|AWS CDK staging plan]]
- [[0001-aws-staging-infrastructure-target|ADR 0001: AWS staging infrastructure target]]
- [[aws-database-stack-configuration|AWS DatabaseStack staging configuration]]
- [[deployment-model|Deployment model]]
- [[aws-network-topology|AWS network topology]]
- [[cloud-deployment|Cloud deployment]]
