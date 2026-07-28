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
  - "../../../infra/deployment/aws/cdk/flowform_infra/stacks/database_bootstrap_stack.py"
  - "../../../infra/deployment/aws/scripts/bootstrap-database.sh"
  - "../../../infra/deployment/aws/cdk/flowform_infra/stacks/network_stack.py"
  - "../../../infra/deployment/aws/cdk/flowform_infra/config/environments.py"
  - "../../../infra/deployment/aws/cdk/tests/"
  - "../../../backend/app/db/manager.py"
  - "../../../backend/app/core/config.py"
  - "../../../backend/gunicorn.conf.py"
related_docs:
  - "Engineering planning"
  - "AWS CDK staging plan"
  - "AWS stack specifications"
  - "AWS database roles and bootstrap design"
  - "ADR 0001: AWS staging infrastructure target"
  - "AWS network topology"
---

# AWS DatabaseStack staging configuration

> Working design and execution note for the first staging RDS deployment. The
> CDK source is implemented; the RDS resources are not yet deployed or live
> verified.

The first staging database should be a small, private, deliberately simple RDS
PostgreSQL instance. The unresolved risk is concentrated in credentials,
migrations, connection limits, TLS verification, and recovery policy rather
than the deployed VPC design.

This note owns the RDS service configuration and its deployment gates.
[[aws-database-roles-and-bootstrap|AWS database roles and bootstrap design]]
owns the PostgreSQL identities, object ownership, grants, and the boundary
between the AWS bootstrap package and the existing container initialization
assets.

## Implementation checkpoint

`DatabaseStack` now implements the recommended persistent RDS infrastructure
boundary. Its assertions cover staging and production lifecycle differences.
The stack creates:

- one explicit DB subnet group;
- one PostgreSQL 17 parameter group;
- PostgreSQL and upgrade CloudWatch log groups;
- one private RDS DB instance;
- only the Network stack exports required to consume its existing RDS subnets
  and security group.

It deliberately contains no Lambda, custom resource, Step Functions state
machine, or interface endpoint. The first deployment attempt reached an
available RDS instance but failed in the former custom-resource bootstrap and
rolled back. The encrypted final snapshot completed successfully. The failed
stack record was removed, so the current source is ready for a fresh deployment
but is not yet live.

The optional `DatabaseBootstrapStack` is a separate operator tool. It owns one
idempotent private Lambda and dedicated security groups. The deployment script
creates a tagged Secrets Manager interface endpoint only for the invocation,
deletes it afterward, and never makes bootstrap success a condition of the
persistent database stack.

The RDS console's automatic Lambda connection wizard is not part of this
design. It automates security-group wiring only, is console-driven, and does not
authenticate the privileged PostgreSQL session. CDK keeps the same
Lambda-to-RDS path explicit, while the bootstrap Lambda reads the RDS-managed
master credential through the temporary endpoint.

## Recommended staging shape

| Setting | Recommendation |
| --- | --- |
| Service | Amazon RDS for PostgreSQL |
| Engine version | PostgreSQL 17.9, explicitly pinned |
| RDS Extended Support | Enrollment disabled |
| Instance class | `db.t4g.small` |
| Availability | Single-AZ |
| Placement | `ap-southeast-2a` |
| Logical databases | `flowform_core` and `flowform_response` on one instance |
| Initial storage | 20 GiB gp3 |
| Storage autoscaling | Enabled, capped at 40 GiB |
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
| Password verifier | `password_encryption = scram-sha-256`; `rds.accepted_password_auth_method = scram` |
| Runtime authentication | IAM tokens; no stored password for the app roles |
| Log exports | PostgreSQL and upgrade logs |
| Database monitoring | Database Insights Standard with no-additional-cost seven-day Performance Insights history |
| Enhanced Monitoring | Disabled (`MonitoringInterval: 0`) |
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
maximum allocated storage: 40 GiB
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

FlowForm's current infrastructure target is deliberately Single-AZ in staging
and production. The second RDS subnet exists only to satisfy the DB subnet-group
coverage requirement. Multi-AZ is not a latent environment switch in the CDK;
adopting it later would require an explicit availability and cost decision.

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

The environment contract now separates general resource removal from database
removal. Staging keeps `RemovalPolicy.DESTROY` for ordinary disposable
resources while `database_removal_policy` is `SNAPSHOT`. `DatabaseStack` does
not silently reinterpret the general lifecycle setting.

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
rds.accepted_password_auth_method = scram
```

The two settings do not share a value vocabulary. `password_encryption` is the
PostgreSQL parameter and takes `md5` or `scram-sha-256`. The RDS-specific
`rds.accepted_password_auth_method` accepts only `scram` or `md5+scram`; use
`md5+scram` only while older clients still need MD5 compatibility.

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
- Database Insights Standard with the no-additional-cost seven-day Performance
  Insights history.

RDS Extended Support enrollment is explicitly disabled. FlowForm must upgrade
PostgreSQL before standard support ends; creating or restoring an unsupported
major version should fail rather than silently incur Extended Support charges.

As of 2026-07-28, AWS has announced that the Performance Insights console
experience reaches end of life on 2026-07-31 and redirects to CloudWatch
Database Insights afterward. Configure the stack for the Standard experience
and verify the exact CDK properties during implementation rather than embedding
an obsolete console assumption.

Keep disabled initially:

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

The controlled bootstrap operation owns:

- both logical databases;
- owner, migrator, and runtime roles;
- extensions;
- application schemas and the authoritative baseline table snapshots;
- grants and default privileges;
- bootstrap-version, table, ownership, privilege, and catalog verification.

The later migration operation owns every schema change after the baseline.

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

This normal migration path does not require Lambda networking, VPC-enabled
CodeBuild, a NAT Gateway, or paid interface endpoints. The initial control-plane
bootstrap is separate: it uses the optional helper Lambda and one temporary
Secrets Manager endpoint, then removes the endpoint.

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
Gate C: deploy/update the optional bootstrap helper stack
  |
  v
Gate D: invoke bootstrap through a temporary Secrets Manager endpoint
  |
  v
Gate E: verify baseline tables, ownership, grants, TLS, and denied connections
  |
  v
Gate F: deploy the Application stack
```

The helper stack is selected only with the explicit
`databaseBootstrap=true` CDK context. Ordinary `cdk list`, `cdk synth`, and
database deployment exclude it. Bootstrap failure leaves RDS and the helper
available for diagnosis and retry; it cannot trigger database rollback.

## DatabaseStack assertions

CDK tests should establish at least:

- exactly one PostgreSQL 17.9 DB instance;
- `db.t4g.small` in staging;
- single-AZ placement in `ap-southeast-2a`;
- no public accessibility or Multi-AZ;
- an explicit subnet group containing only both RDS subnets;
- only the existing RDS security group;
- 20 GiB gp3 storage with a 40 GiB autoscaling ceiling;
- storage encryption using the FlowForm KMS key;
- an RDS-managed `flowform_admin` secret using the KMS key;
- a PostgreSQL 17 parameter group with TLS and SCRAM requirements;
- seven-day backup retention and tag copying;
- the accepted snapshot/deletion behavior;
- PostgreSQL and upgrade log exports;
- the selected Standard-compatible database monitoring configuration;
- no Enhanced Monitoring, RDS Proxy, or automatic major upgrade;
- RDS Extended Support enrollment disabled;
- environment-specific staging and production lifecycle differences;
- no Lambda, custom resource, Step Functions state machine, or interface
  endpoint in `DatabaseStack`;
- no secret values in outputs or SSM parameters.

## Post-deployment verification

After `DatabaseStack` reaches `CREATE_COMPLETE`, verify:

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

Then run `infra/deployment/aws/scripts/bootstrap-database.sh --env staging
--apply`. The script deploys or updates `FlowForm-Staging-DatabaseBootstrap`,
creates one tagged Secrets Manager endpoint, invokes the Lambda with the
version and checksum emitted by that stack, validates the sanitized result, and
requests endpoint deletion in its exit path. Also verify the identity,
ownership, grant, extension, allowed-connection, and denied-connection
contracts in
[[aws-database-roles-and-bootstrap|AWS database roles and bootstrap design]].

The operator identity, rather than the Lambda role, owns the bounded
`CreateVpcEndpoint`, `CreateTags`, `DescribeVpcEndpoints`,
`DeleteVpcEndpoints`, and `InvokeFunction` permissions. The Lambda role can
read only the managed database secret, decrypt it with the environment KMS key,
write its log group, manage its VPC attachment, and connect to RDS.

## Implemented decisions and remaining gates

The infrastructure source now implements:

1. Use an RDS-managed master password.
2. Change staging removal behavior from destroy to final snapshot.
3. Pin PostgreSQL 17.9 without making this phase a CDK upgrade.
4. Retain seven days of backups.
5. Start at 20 GiB gp3 and cap autoscaling at 40 GiB.
6. Use Database Insights Standard-compatible seven-day history.
7. Disable Enhanced Monitoring explicitly.
8. Disable RDS Extended Support enrollment.
9. Expose the managed secret and non-secret endpoint as CDK construct
   properties without publishing secret values to outputs or SSM.
10. Keep bootstrap outside `DatabaseStack`; invoke a separate private helper
    Lambda through an operator-managed temporary Secrets Manager endpoint.

The remaining application and database-content gates are:

1. Separate `staging` runtime configuration from the `nonprod` security scope.
2. Build the normal schema-migration execution path for every change after the
   baseline loaded by control-plane bootstrap.
3. Start with an application connection ceiling around 40 and measure it.
4. Add `sslmode=verify-full` before application staging readiness.
5. Defer application-password automation until in-place change, reload, test,
   and rollback behavior are proven.

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
- [[aws-stack-specifications|AWS stack specifications]]
- [[aws-database-roles-and-bootstrap|AWS database roles and bootstrap design]]
- [[0001-aws-staging-infrastructure-target|ADR 0001: AWS staging infrastructure target]]
- [[aws-network-topology|AWS network topology]]
