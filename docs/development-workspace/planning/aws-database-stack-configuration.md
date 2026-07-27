---
title: AWS DatabaseStack staging configuration
aliases: ["AWS DatabaseStack staging configuration"]
document_type: planning
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-07-28
tags: [infrastructure, security, configuration]
related_code:
  - "../../../infra/deployment/aws/cdk/flowform_infra/stacks/database_stack.py"
  - "../../../infra/deployment/aws/cdk/flowform_infra/stacks/network_stack.py"
  - "../../../infra/deployment/aws/cdk/flowform_infra/config/environments.py"
  - "../../../infra/deployment/aws/cdk/tests/"
  - "../../../backend/app/db/manager.py"
  - "../../../backend/app/core/config.py"
  - "../../../backend/gunicorn.conf.py"
related_docs:
  - "Engineering planning"
  - "AWS CDK staging plan"
  - "AWS database roles and bootstrap design"
  - "ADR 0001: AWS staging infrastructure target"
  - "AWS network topology"
---

# AWS DatabaseStack staging configuration

> Working recommendation for the first staging RDS deployment. It records
> proposed settings and gates, not implemented or live infrastructure.

The first staging database should be a small, private, deliberately simple RDS
PostgreSQL instance. The unresolved risk is concentrated in credentials,
migrations, connection limits, TLS verification, and recovery policy rather
than the deployed VPC design.

This note owns the RDS service configuration and its deployment gates.
[[aws-database-roles-and-bootstrap|AWS database roles and bootstrap design]]
owns the PostgreSQL identities, object ownership, grants, and reuse of the
existing initialization assets.

## Recommended staging shape

| Setting | Recommendation |
| --- | --- |
| Service | Amazon RDS for PostgreSQL |
| Engine version | PostgreSQL 17.9, explicitly pinned |
| Instance class | `db.t4g.small` |
| Availability | Single-AZ |
| Placement | `ap-southeast-2a` |
| Logical databases | `flowform_core` and `flowform_response` on one instance |
| Initial storage | 20 GiB gp3 |
| Storage autoscaling | Enabled, capped at 100 GiB |
| Storage encryption | Existing FlowForm nonproduction KMS key |
| Public access | Disabled |
| Security group | Existing RDS security group from `NetworkStack` |
| DB subnet group | Existing RDS subnets in Availability Zones A and B |
| Master username | `flowform_admin` |
| Master credential | RDS-managed Secrets Manager secret |
| Backup retention | Seven days |
| Stack deletion | Final snapshot |
| Deletion protection | Disabled for staging |
| Transport | `rds.force_ssl = 1` |
| Password verifier | SCRAM-SHA-256 |
| Log exports | PostgreSQL and upgrade logs |
| Database monitoring | Database Insights Standard-compatible, seven-day history |
| Enhanced Monitoring | Omit initially |
| RDS Proxy | None |
| Multi-AZ | Disabled |
| Automatic major upgrades | Disabled |
| Automatic minor upgrades | Enabled in a controlled maintenance window |

The intended result is:

```text
NetworkStack
  |
  +-- RDS subnet A, ap-southeast-2a ----+
  |                                     |
  +-- RDS subnet B, ap-southeast-2b ----+--> DB subnet group
                                                |
                                                v
                                     single-AZ RDS in AZ A
                                                |
                              +-----------------+-----------------+
                              |                                   |
                              v                                   v
                       flowform_core                       flowform_response
```

The two-subnet group satisfies the RDS requirement to cover at least two
Availability Zones. It does not enable or incur the instance cost of Multi-AZ.
The actual staging instance remains in Availability Zone A.

## Cost and capacity choices

### Instance class

`db.t4g.small` is the preferred starting point. It keeps staging inexpensive
while giving PostgreSQL, RDS management processes, query memory, caches,
administrative sessions, and the two application connection pools more room
than `db.t4g.micro`.

`db.t4g.micro` remains a possible later cost reduction if measurements show
that staging is mostly idle and the application connection budget has already
been reduced. Starting with `db.t4g.medium` or a non-burstable class is not
justified without evidence such as:

- sustained CPU-credit exhaustion;
- persistent memory pressure;
- query latency linked to insufficient cache;
- connection demand that cannot be solved through pool configuration.

The instance class can be changed later through an RDS modification, accepting
the associated restart or service interruption.

### Application connection budget

The current backend creates two SQLAlchemy pools per Gunicorn worker. Each pool
is currently hard-coded to:

```text
pool_size = 10
max_overflow = 20
```

With two workers and two databases, the theoretical maximum is:

```text
(10 persistent + 20 overflow)
  x 2 databases
  x 2 workers
= 120 connections
```

That is too aggressive for the proposed staging instance. Before the
Application stack is ready, make these values configurable:

```text
DB_POOL_SIZE
DB_MAX_OVERFLOW
DB_POOL_TIMEOUT
DB_POOL_RECYCLE
```

A reasonable first staging ceiling is:

```text
2 Gunicorn workers
2 database pools per worker
5 persistent connections per pool
5 overflow connections per pool

(5 + 5) x 2 x 2 = 40 maximum application connections
```

Forty is a safety ceiling, not an expected steady-state level. Select the final
settings against the live RDS `max_connections` value and reserve capacity for
migrations, administration, monitoring, and recovery operations.

### Storage

Start with:

```text
allocated storage: 20 GiB gp3
maximum allocated storage: 100 GiB
```

The cap prevents ordinary staging growth from expanding to an unnecessarily
large volume. RDS storage autoscaling can increase storage but cannot decrease
it afterward, so the maximum remains an operational and cost boundary rather
than a temporary burst setting.

Monitor `FreeStorageSpace` even with autoscaling. RDS scaling thresholds and
the interval between storage modifications mean autoscaling cannot guarantee
recovery from every sudden large load.

## Availability and isolation

### Single-AZ

Single-AZ is intentional for the first staging environment:

- it matches ADR 0001;
- it avoids paying for a standby;
- it is sufficient for deployment, migration, recovery, and application
  validation;
- downtime during maintenance or an instance failure is acceptable in this
  nonproduction phase.

Multi-AZ should be reconsidered for production availability. It is not required
to validate Caddy, Route 53, TLS, or the staging application path, and its
standby does not normally increase read-query throughput.

### One instance with two logical databases

One instance is the accepted staging choice:

```text
one endpoint
  |-- flowform_core
  +-- flowform_response
```

It preserves separation through database names, credentials, schemas, grants,
and application connections without paying for a second RDS instance.

The following infrastructure remains shared:

- CPU, memory, and storage;
- PostgreSQL processes;
- maintenance and instance failure;
- the master administrator;
- automated backup and point-in-time recovery.

An instance restore returns both logical databases to the selected recovery
point. If independent restore, scaling, maintenance, or failure boundaries
later become necessary, two RDS instances are the stronger design at roughly
twice the base infrastructure. Replacing the two databases with two schemas in
one database is not proposed because it would contradict the existing
application and privacy boundary.

## Credentials and encryption

### Master credential

Prefer an RDS-managed master password:

```text
username: flowform_admin
secret owner: RDS / Secrets Manager
secret encryption: existing nonproduction KMS key
application access: none
```

RDS-managed credentials keep the master password and RDS account synchronized
without a custom rotation Lambda. Confirm during implementation that the
installed CDK version exposes the managed secret cleanly enough for the initial
bootstrap authority and later recovery use.

Do not enable scheduled rotation until bootstrap and recovery access have been
tested. Routine migrations should use `flowform_migrator`, not the master
credential. Only the initial privileged setup or break-glass path should need
`flowform_admin`.

The customer-managed KMS key choice is durable: after RDS manages the secret,
the encryption key for that managed secret cannot be changed in place.

### Runtime credentials

The existing credentials remain separate:

```text
flowform_core_app
flowform_response_app
```

Their passwords continue to come from:

```text
flowform/nonprod/db-secrets
```

They must never reuse the master or migration password. Their grants and
database-connect isolation are specified in
[[aws-database-roles-and-bootstrap|AWS database roles and bootstrap design]].

### Storage encryption

Use the existing FlowForm nonproduction KMS key for RDS storage and the managed
master secret. CDK assertions should prove encryption and the selected key
rather than relying on an account default.

## Backups and deletion

Use:

```text
backup retention: 7 days
copy tags to snapshots: true
deletion protection: false
removal policy: SNAPSHOT
delete automated backups: false
```

This deliberately allows an operator to tear down staging while leaving a
final recovery artifact. Automated backups and point-in-time recovery cover the
whole RDS instance, not an individual logical database.

This recommendation conflicts with the current staging `EnvConfig`, which uses
`RemovalPolicy.DESTROY`. Implementation therefore requires an explicit choice
and config change; it must not silently override the environment contract inside
`DatabaseStack`.

Snapshots continue to incur storage cost until removed. Give snapshots clear
environment tags and establish a later cleanup policy. A snapshot-restore
rehearsal remains part of staging acceptance.

The directional production posture is deletion protection enabled, longer
backup retention, and retain-or-snapshot removal behavior. Exact production
values remain outside this staging implementation.

## TLS and authentication

Use a PostgreSQL 17 parameter group with:

```text
rds.force_ssl = 1
password_encryption = scram-sha-256
rds.accepted_password_auth_method = scram-sha-256
```

Apply the SCRAM transition in a safe order:

1. configure SCRAM password generation;
2. create or reset every login role password;
3. verify that each role has a SCRAM verifier;
4. require SCRAM authentication;
5. test every allowed and denied connection.

`rds.force_ssl = 1` rejects non-TLS sessions. It does not prove that the client
verified the RDS server identity.

Before the Application stack is considered ready for staging use, add client
support for:

```text
sslmode=verify-full
sslrootcert=/path/to/aws-rds-ca-bundle.pem
```

Until then, describe the achieved state as **TLS transport enforced by RDS**,
not full server-certificate verification.

## Logs and monitoring

Enable initially:

- standard RDS CloudWatch metrics;
- PostgreSQL log export;
- upgrade log export;
- explicit CloudWatch log-group retention;
- Database Insights Standard-compatible monitoring with seven-day history.

As of 2026-07-28, AWS has announced that the Performance Insights console
experience reaches end of life on 2026-07-31 and redirects to CloudWatch
Database Insights afterward. Configure the stack for the Standard experience
and verify the exact CDK properties during implementation rather than embedding
an obsolete console assumption.

Omit initially:

- Enhanced Monitoring;
- Database Insights Advanced;
- RDS Proxy;
- detailed statement logging;
- long performance-history retention.

Do not log every SQL statement. FlowForm handles sensitive survey information,
and indiscriminate statement logging can expose values and create unnecessary
volume.

The later Observability stack should own alarms for at least:

```text
CPUUtilization
CPUCreditBalance
FreeableMemory
FreeStorageSpace
DatabaseConnections
ReadLatency
WriteLatency
DiskQueueDepth
```

`CPUCreditBalance` is especially relevant to the burstable T-class instance.
Enhanced Monitoring can be reconsidered at a 60-second interval if standard
metrics do not provide enough evidence.

## Maintenance behavior

Set explicit non-overlapping UTC windows. A candidate is:

```text
backup:      16:00-16:30 UTC
maintenance: Sunday 17:00-18:00 UTC
```

That normally maps to early morning in Melbourne, with a one-hour local shift
between standard and daylight-saving time.

Use:

```text
allow major version upgrades: false
auto minor version upgrade: true
apply immediately: false by default
```

Normal changes should wait for the maintenance window. An urgent change can be
applied immediately only as a deliberate operator action.

## Runtime configuration ownership

`DatabaseStack` may publish or expose only non-secret database values:

```text
endpoint
port
engine
core database name
response database name
core runtime username
response runtime username
```

Do not put passwords in SSM or CloudFormation outputs.

If SSM becomes the configuration contract for several services, prefer a
dedicated environment-configuration construct or stack rather than making
`DatabaseStack` own unrelated backend configuration.

Keep deployment environment and shared security scope distinct:

```text
FLOWFORM_ENVIRONMENT=staging
FLOWFORM_SECURITY_SCOPE=nonprod

runtime parameters: /flowform/staging/backend/
shared DB secret:   flowform/nonprod/db-secrets
```

The backend hardening mode should be production-like while the AWS deployment
environment remains staging:

```text
FlowForm application mode = prod
AWS environment = staging
```

The current bootstrap conflates some of these namespaces. Resolve that before
deploying the Application stack.

## CDK and migration boundary

CDK owns:

- DB instance and explicit subnet group;
- parameter group;
- KMS storage encryption;
- RDS-managed master secret;
- backup and removal behavior;
- log and monitoring capabilities;
- security-group association;
- non-secret endpoint/configuration contracts.

The controlled bootstrap/migration operation owns:

- both logical databases;
- owner, migrator, and runtime roles;
- extensions;
- schemas and application objects;
- grants and default privileges;
- permission and connection-isolation verification.

Do not run schema changes from a CloudFormation custom resource. A failed
migration should not cause opaque CloudFormation retries or couple schema
rollback to infrastructure rollback.

The eventual migration path should be:

```text
GitHub deployment workflow
  |
  v
SSM command on private app EC2
  |
  v
one-off migration container
  |
  +--> retrieve only required bootstrap/migration secrets
  +--> apply ordered changes
  +--> verify ownership, grants, and denied access
```

This path does not require Lambda networking, VPC-enabled CodeBuild, a NAT
Gateway, or paid interface endpoints. It is not required before provisioning
and verifying the empty RDS instance.

## Delivery gates

Keep database infrastructure, database contents, and application deployment as
separate gates:

```text
Gate A: implement and test DatabaseStack
  |
  v
Gate B: deploy and verify private RDS infrastructure
  |
  v
Gate C: bootstrap databases, roles, extensions, and schemas
  |
  v
Gate D: verify ownership, grants, TLS, and denied connections
  |
  v
Gate E: deploy the Application stack
```

The current execution slice ends after Gate B unless a safe private migration
runner is deliberately brought into scope. The Application stack remains
blocked until connection pools, security-scope configuration, client-side TLS
verification, and bootstrap convergence are ready.

## DatabaseStack assertions

CDK tests should establish at least:

- exactly one PostgreSQL 17.9 DB instance;
- `db.t4g.small` in staging;
- single-AZ placement in `ap-southeast-2a`;
- no public accessibility or Multi-AZ;
- an explicit subnet group containing only both RDS subnets;
- only the existing RDS security group;
- 20 GiB gp3 storage with a 100 GiB autoscaling ceiling;
- storage encryption using the FlowForm KMS key;
- an RDS-managed `flowform_admin` secret using the KMS key;
- a PostgreSQL 17 parameter group with TLS and SCRAM requirements;
- seven-day backup retention and tag copying;
- the accepted snapshot/deletion behavior;
- PostgreSQL and upgrade log exports;
- the selected Standard-compatible database monitoring configuration;
- no Enhanced Monitoring, RDS Proxy, or automatic major upgrade;
- environment-specific staging and production lifecycle differences;
- no secret values in outputs or SSM parameters.

## Post-deployment verification

Before database bootstrap, verify:

- the instance is available, private, single-AZ, and in Availability Zone A;
- the subnet group covers Availability Zones A and B;
- the expected security group is attached;
- storage and the master secret use the intended KMS key;
- allocated and maximum storage match the configured bounds;
- backup, maintenance, deletion, and snapshot behavior match the decision;
- TLS, SCRAM, logs, and monitoring parameters are applied;
- the endpoint resolves privately inside the VPC;
- TCP 5432 is not reachable from the public internet;
- CloudFormation drift and CDK diff are clean.

After controlled bootstrap, additionally verify the identity, ownership, grant,
extension, allowed-connection, and denied-connection contracts in
[[aws-database-roles-and-bootstrap|AWS database roles and bootstrap design]].

## Decisions to confirm before implementation

The recommended answers are:

1. Use an RDS-managed master password.
2. Change staging removal behavior from destroy to final snapshot.
3. Pin PostgreSQL 17.9 without making this phase a CDK upgrade.
4. Retain seven days of backups.
5. Start at 20 GiB gp3 and cap autoscaling at 100 GiB.
6. Use Database Insights Standard-compatible seven-day history.
7. Omit Enhanced Monitoring initially.
8. Publish only non-secret connection values from the database boundary.
9. Separate `staging` environment configuration from the `nonprod` security
   scope.
10. Use a one-off migration container on private app EC2 through SSM.
11. Keep bootstrap as a gate after RDS infrastructure verification.
12. Start with an application connection ceiling around 40 and measure it.
13. Add `sslmode=verify-full` before application staging readiness.
14. Defer application-password automation until in-place change, reload, test,
   and rollback behavior are proven.

These remain recommendations until accepted in the staging plan or its owning
decision record.

## AWS references

- [RDS instances in a VPC](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_VPC.WorkingWithRDSInstanceinaVPC.html)
- [RDS DB instance storage](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_Storage.html)
- [RDS storage autoscaling](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PIOPS.Autoscaling.html)
- [RDS-managed master passwords](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-secrets-manager.html)
- [RDS automated backups](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithAutomatedBackups.html)
- [RDS PostgreSQL TLS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/PostgreSQL.Concepts.General.SSL.html)
- [RDS PostgreSQL SCRAM](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/PostgreSQL_Password_Encryption_configuration.html)
- [Performance Insights transition](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PerfInsights.Overview.html)
- [CloudWatch Database Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Database-Insights.html)

## Related documents

- [[planning-index|Engineering planning]]
- [[aws-cdk-staging-plan|AWS CDK staging plan]]
- [[aws-database-roles-and-bootstrap|AWS database roles and bootstrap design]]
- [[0001-aws-staging-infrastructure-target|ADR 0001: AWS staging infrastructure target]]
- [[aws-network-topology|AWS network topology]]
