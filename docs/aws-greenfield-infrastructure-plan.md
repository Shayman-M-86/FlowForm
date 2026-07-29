# AWS greenfield infrastructure overhaul

## Purpose

Build a new AWS-only FlowForm infrastructure system in one branch as though no
previous infrastructure implementation exists.

This is not a compatibility migration. The implementation may reuse application
knowledge, but it must not preserve an old file layout, universal host image,
Proxmox seam, rehearsal shim, or deployment script merely because one existed
before.

The outcome must be understandable directly from the repository:

- every file has one clear owner;
- every change has one clear release unit;
- build, publication, promotion, deployment, and rollback remain distinct;
- staging is deployable from a reviewed commit without workstation-specific
  state;
- production uses the same artefacts with different runtime configuration.

## Scope

### Included

- AWS account and environment configuration.
- CDK infrastructure for staging and production.
- ECR repositories and immutable container publication.
- Three-level machine-image lineage:
  - base AMI;
  - app AMI;
  - proxy AMI.
- Role-specific EC2 bootstrap and deployment commands.
- Backend, Caddy, Squid, and Alloy container images.
- SSM Parameter Store and Secrets Manager contracts.
- Private networking, controlled Squid egress, RDS, DNS, IAM, KMS, SES, and
  observability foundations.
- Database initialization as an explicit operation.
- Versioned database migrations as a separately authorized operation.
- GitHub Actions identities and workflows.
- Operator commands, diagnostics, rollback, validation, and AMI retirement.
- A staging deployment and end-to-end verification.

### Excluded

- Proxmox, LocalStack, rehearsal VMs, TLS shims, local registries, and any
  compatibility code for them.
- Migration of retained production data.
- Multi-AZ, horizontal application scaling, an Application Load Balancer, ECS,
  EKS, RDS Proxy, NAT Gateway, or permanent paid VPC interface endpoints.
- Reorganizing backend and frontend source merely to match a new top-level
  aesthetic.
- Importing or adapting deleted documentation as an implementation authority.

## Non-negotiable design rules

1. **Machine images, container images, and CDK are separate release units.**
2. **The base AMI is never launched by CDK.** It is an intermediate parent for
   the app and proxy AMIs.
3. **Role AMIs contain host machinery, not service behaviour or environment
   state.**
4. **Container images contain service software, templates, entrypoints, and
   service validation.**
5. **CDK declares AWS resources and supplies only minimal instance identity.**
6. **SSM contains non-secret runtime and release state.**
7. **Secrets Manager contains confidential runtime values.**
8. **Runtime containers are selected by immutable ECR digest.**
9. **No secret, current digest, environment address, or static AWS credential is
   baked into an AMI or container image.**
10. **A failed container release rolls back containers; it does not replace the
    EC2 host.**
11. **A failed database bootstrap cannot roll back persistent RDS.**
12. **Shared code must represent a stable contract or genuinely identical
    mechanism, not a large conditional workflow.**
13. **Bootstrap and migrations are different operations.** Bootstrap creates a
    verified empty-environment baseline; migrations evolve retained schemas.

## Target repository structure

Keep application code at its established roots. Build the new infrastructure
beside it:

During the experimental migration, place all of the target infrastructure,
database, operations, and infrastructure-test areas beneath `infra-new/`. This
keeps every existing repository entry point unchanged while the replacement is
assembled. The eventual cutover may rename or promote those ownership areas to
their final locations in one change.

```text
FlowForm/
├── backend/
├── frontend/
│
├── database/
│   ├── contracts/
│   ├── schema/
│   ├── bootstrap/
│   ├── migrations/
│   ├── development/
│   └── tests/
│
├── infrastructure/
│   ├── contracts/
│   │   ├── instance-context.schema.json
│   │   ├── app-runtime.schema.json
│   │   ├── proxy-runtime.schema.json
│   │   ├── app-release.schema.json
│   │   ├── proxy-release.schema.json
│   │   └── naming.json
│   │
│   ├── containers/
│   │   ├── backend/
│   │   ├── caddy/
│   │   ├── squid/
│   │   └── alloy/
│   │
│   ├── images/
│   │   └── machine/
│   │       ├── packer/
│   │       ├── base/
│   │       ├── app/
│   │       └── proxy/
│   │
│   └── cdk/
│       ├── app.py
│       ├── cdk.json
│       ├── pyproject.toml
│       ├── flowform_infra/
│       │   ├── config/
│       │   ├── contracts/
│       │   ├── constructs/
│       │   ├── stacks/
│       │   └── user_data/
│       └── tests/
│
├── operations/
│   ├── bin/
│   │   └── flowform
│   ├── lib/
│   │   ├── common/
│   │   ├── containers/
│   │   ├── machine_images/
│   │   ├── infrastructure/
│   │   ├── runtime/
│   │   ├── database/
│   │   └── diagnostics/
│   └── README.md
│
├── tests/
│   └── infrastructure/
├── docs/
└── .github/workflows/
```

### Why the application roots remain unchanged

Moving `backend/` and `frontend/` under an `application/` directory would alter
Docker build contexts, Python and Node tooling, editor configuration, CI paths,
and developer commands without improving the ownership of AWS infrastructure.
The overhaul therefore begins at the infrastructure boundary.

### Why CDK remains Python

FlowForm already depends heavily on Python. Python CDK avoids adding a
TypeScript toolchain solely for infrastructure and keeps stack tests, contract
loading, and database helpers in one language. CDK constructs must still be
small, typed, and separated by responsibility.

### Why database is a top-level package

Database definitions are consumed by application development, initial AWS
bootstrap, later migrations, verification, and recovery. They are not owned
solely by CDK and should not be hidden inside a Lambda asset or a container
build context.

The top-level `database/` package is therefore the authoritative home for
PostgreSQL identities, baseline schemas, migrations, development fixtures, and
database tests. CDK creates RDS and packages the bootstrap runner; it does not
own application schema files.

## Release-unit ownership

| File or behaviour | Owner | Rebuild or action |
| --- | --- | --- |
| Linux packages, Docker, SSM Agent, host hardening | Base AMI | Rebuild base, app, and proxy AMIs |
| App host systemd and deployment machinery | App AMI | Rebuild app AMI |
| Proxy host systemd and deployment machinery | Proxy AMI | Rebuild proxy AMI |
| Backend code and process health | Backend container | Publish backend digest |
| Caddy binary, Route 53 module, Caddyfile template | Caddy container | Publish Caddy digest |
| Squid binary, ACL template, entrypoint, validation | Squid container | Publish Squid digest |
| Alloy configuration and entrypoint | Alloy container | Publish Alloy digest |
| VPC, RDS, EC2, IAM, DNS, KMS, ECR, SSM declarations | CDK | Diff and deploy affected stack |
| Empty-database identities, ownership, grants, and baseline | Database bootstrap package | Publish and invoke bootstrap helper |
| Schema evolution after the baseline | Database migration package | Run controlled migration operation |
| Development-only PostgreSQL initialization and mock data | Database development package | Recreate local development databases |
| Domains, ports, endpoints, allowed destinations | Runtime configuration | Update configuration and reconcile role |
| Container digest set | Role release manifest | Promote and deploy role |
| Confidential values | Secrets Manager | Seed or rotate secret |
| Operator orchestration | `operations/` | No AMI or container rebuild |

## Runtime contracts

Contracts are the only intentional coupling between CDK, machine images,
container images, and operator tooling.

### Instance context

CDK writes a small root-owned file:

```text
/etc/flowform/instance.json
```

It contains only:

```json
{
  "environment": "staging",
  "role": "app",
  "region": "ap-southeast-2",
  "parameter_root": "/flowform/staging",
  "proxy_url": "http://proxy.internal.staging.flow-form.com.au:3128"
}
```

The proxy context omits `proxy_url`. User data writes this file and starts the
baked role bootstrap service. User data must not install packages, render
service configuration, fetch repository files, or contain secrets.

### Runtime configuration

Use role-specific paths:

```text
/flowform/staging/app/config/*
/flowform/staging/proxy/config/*
```

The app group contains database endpoints and names, Auth0 public values, SES
configuration, CORS, observability endpoints, proxy settings, and application
flags.

The proxy group contains the public API domain, private backend DNS name,
telemetry endpoints, Squid destination policy, and proxy service settings.

Each role retrieves only its own path. IAM permissions use exact parameter
ARNs.

### Release manifests

Promote one atomic JSON manifest per role rather than independently changing
several digest parameters:

```text
/flowform/staging/app/release
/flowform/staging/proxy/release
```

Example app release:

```json
{
  "schema_version": 1,
  "commit": "git-sha",
  "images": {
    "backend": "account.dkr.ecr.region.amazonaws.com/backend@sha256:...",
    "alloy": "account.dkr.ecr.region.amazonaws.com/alloy@sha256:..."
  }
}
```

Example proxy release:

```json
{
  "schema_version": 1,
  "commit": "git-sha",
  "images": {
    "caddy": "account.dkr.ecr.region.amazonaws.com/caddy@sha256:...",
    "squid": "account.dkr.ecr.region.amazonaws.com/squid@sha256:...",
    "alloy": "account.dkr.ecr.region.amazonaws.com/alloy@sha256:..."
  }
}
```

The host stores the last successful manifest locally so rollback does not
depend on guessing from mutable tags.

### Secrets

Use separate secrets according to consumer and lifecycle. Materialize required
values into a root-owned tmpfs directory:

```text
/run/flowform/secrets/
```

Container secrets are file-mounted. They must not appear in instance user data,
SSM String parameters, Docker environment inspection, CloudFormation outputs,
command arguments, or logs.

## Database package

Use a first-class database tree:

```text
database/
├── README.md
│
├── contracts/
│   ├── identities.json
│   └── README.md
│
├── schema/
│   ├── core/
│   │   ├── baseline.sql
│   │   └── verify.sql
│   ├── response/
│   │   ├── baseline.sql
│   │   └── verify.sql
│   └── constraint-naming.md
│
├── bootstrap/
│   ├── sql/
│   │   ├── 001-cluster-identities.sql
│   │   ├── 010-databases.sql
│   │   ├── 020-schema-ownership.sql
│   │   ├── 030-runtime-grants.sql
│   │   └── 090-bootstrap-verification.sql
│   ├── runner/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── flowform_db_bootstrap/
│   │       ├── handler.py
│   │       ├── models.py
│   │       ├── postgres.py
│   │       └── services.py
│   └── tests/
│
├── migrations/
│   ├── core/
│   ├── response/
│   ├── manifest.json
│   ├── runner/
│   └── tests/
│
├── development/
│   ├── compose.yml
│   ├── init/
│   ├── postgres/
│   │   └── pg_hba.conf
│   └── fixtures/
│       ├── core/
│       └── response/
│
└── tests/
    ├── test_baseline.py
    ├── test_identities.py
    ├── test_isolation.py
    └── test_migration_chain.py
```

### Database ownership boundaries

`database/contracts/` defines stable names and properties:

- `flowform_admin`;
- `flowform_owner`;
- `flowform_migrator`;
- `flowform_core_app`;
- `flowform_response_app`;
- logical database and application-schema names;
- required authentication mode and privilege expectations.

CDK and the bootstrap runner load this contract rather than independently
declaring database-user strings.

`database/schema/` contains the authoritative empty-database baseline. It
contains no AWS API logic, passwords, Lambda handler, or local mock data.

`database/bootstrap/` owns one idempotent transition:

```text
empty RDS PostgreSQL instance
→ identities
→ logical databases
→ baseline schemas
→ ownership and default privileges
→ IAM grants
→ bootstrap version and checksum
→ verification
```

It refuses to overwrite a populated database whose recorded baseline or
checksum is incompatible.

`database/migrations/` owns every schema transition after the baseline.
Migrations are ordered, immutable after publication, independently authorized,
and applied by `flowform_migrator`. A migration is never run automatically by
CloudFormation or ordinary application startup.

`database/development/` owns disposable local PostgreSQL composition,
password-mode initialization, and mock data. Those fixtures may consume the
same baseline and migrations, but they never become inputs to the AWS bootstrap
asset.

### Relationship to the current database files

The existing database implementation should be reorganized, not replaced with
an unrelated framework:

| Current responsibility | Target location |
| --- | --- |
| Core and response schema snapshots | `database/schema/core/baseline.sql` and `database/schema/response/baseline.sql` |
| SQLAlchemy constraint naming rules | `database/schema/constraint-naming.md` |
| AWS roles, database creation, grants, and verification SQL | `database/bootstrap/sql/` |
| AWS bootstrap Lambda Python and Dockerfile | `database/bootstrap/runner/` |
| Local template renderer and password-based initialization | `database/development/init/` |
| Development `pg_hba.conf` | `database/development/postgres/pg_hba.conf` |
| Core and response mock data | `database/development/fixtures/core/` and `database/development/fixtures/response/` |
| Future post-baseline changes | `database/migrations/core/` and `database/migrations/response/` |

Keep the existing SQL-first approach. Do not introduce an ORM migration
framework merely as part of the directory move. First establish one
authoritative baseline per logical database, reuse those files directly from
local initialization and AWS bootstrap, and add the small manifest-driven
migration mechanism only when the first post-baseline change is required.

The move must also eliminate duplication: bootstrap SQL creates identities,
databases, ownership, and privileges, but it must not contain a second copy of
the core or response schema. The bootstrap runner applies the authoritative
files from `database/schema/` and then records their checksums.

### Database release stream

The three infrastructure artefact classes remain machine images, container
images, and CDK. Database changes form a separate controlled data-operation
stream:

```text
bootstrap package
    used once per empty environment, safely repeatable

migration package
    versioned changes after bootstrap

development fixtures
    disposable and never promoted to AWS
```

This distinction prevents a backend container rollout or CDK update from
silently altering retained data.

## Container images

### Backend

The Backend image contains the application runtime and a container-level
healthcheck. It must support IAM-authenticated RDS connections without a stored
database password.

### Caddy

The Caddy image contains:

- a pinned Caddy binary;
- the pinned Route 53 DNS provider;
- one environment-neutral Caddyfile template;
- the request-ID, redaction, headers, tracing, health-check, and reverse-proxy
  behaviour;
- an entrypoint and `caddy validate` check.

Runtime values supply the API domain and backend private DNS name. Caddy
configuration changes publish a new container digest, not a new AMI.

### Squid

The Squid image becomes a custom FlowForm image containing:

- a pinned Squid base;
- the FlowForm ACL template;
- an entrypoint that renders only approved runtime values;
- `squid -k parse` validation;
- bounded logs and a container healthcheck.

The destination list is runtime policy. The template defines how it is applied.
The EC2 security group remains the primary source restriction; Squid also
limits the admitted private subnet as defence in depth.

### Alloy

Use one custom FlowForm Alloy image with both app and proxy configurations
baked into the image. The role is selected explicitly by Compose. A change to
either telemetry configuration publishes a new Alloy digest; it does not
require an AMI rebuild.

### Compose ownership

Generic role Compose definitions belong in their role AMIs because they define
host topology:

```text
App AMI:
    backend + app Alloy + local Valkey

Proxy AMI:
    Caddy + Squid + proxy Alloy
```

Compose supplies image references and runtime-generated files but does not
bind-mount repository configuration into containers.

## Machine-image architecture

### Base AMI

The base AMI contains only:

- Amazon Linux 2023;
- approved OS updates;
- Docker Engine, Buildx, and Compose;
- AWS CLI;
- SSM Agent;
- EC2 Instance Connect support;
- common certificates and host tools;
- common filesystem, logging, hardening, and cleanup;
- a small shared host utility library.

It explicitly excludes:

- role bootstrap scripts;
- Compose files;
- service configuration;
- container images;
- environment values;
- runtime release manifests;
- secrets;
- Packer SSH keys and machine identity.

### App AMI

Built from the exact base AMI recorded in the build manifest. It adds:

- app bootstrap, deployment, health, and rollback commands;
- the app Compose definition;
- app-specific systemd units;
- proxy-first SSM Agent and Docker configuration;
- runtime contract validation.

### Proxy AMI

Built from the same base AMI. It adds:

- proxy bootstrap, deployment, health, and rollback commands;
- the proxy Compose definition;
- proxy-specific systemd units;
- runtime contract validation.

### Build and publication

The repository operator command supports:

```text
flowform machine validate
flowform machine build base
flowform machine build app
flowform machine build proxy
flowform machine build all
flowform machine publish app staging
flowform machine publish proxy staging
flowform machine prune staging --dry-run
flowform machine prune staging --apply
```

`build all` performs:

```text
build base
→ verify base
→ record base ID
→ build app and proxy from that exact ID
→ verify lineage and role contents
```

Only role AMIs are published for CDK:

```text
/flowform/staging/ec2/appAmiId
/flowform/staging/ec2/proxyAmiId
```

Pruning protects:

- every AMI referenced by an environment parameter;
- every AMI used by a live instance;
- the parent of a protected role AMI;
- the current and one previous successful role AMI.

## Host deployment behaviour

Each role AMI installs a single idempotent deployment command:

```text
/usr/local/sbin/flowform-deploy-app
/usr/local/sbin/flowform-deploy-proxy
```

The command:

1. acquires a single-host deployment lock;
2. validates instance context;
3. retrieves and validates runtime configuration;
4. retrieves and validates the promoted release manifest;
5. materializes secrets without logging them;
6. authenticates Docker to the exact ECR registries;
7. pulls candidate digests;
8. renders the local runtime environment;
9. validates Compose and service configuration;
10. starts or replaces the affected containers;
11. waits for bounded health checks;
12. records the successful manifest;
13. restores the previous manifest and containers on failure;
14. emits sanitized diagnostics and a non-zero result.

Normal releases invoke this command through SSM Run Command. Container changes
do not redeploy CDK or replace the host.

## Networking target

Use the minimal four-subnet staging topology:

```text
Availability Zone A
├── public proxy subnet
├── isolated app subnet
└── isolated RDS subnet

Availability Zone B
└── isolated RDS subnet
```

Hard boundaries:

- one proxy EC2 with an Elastic IP;
- one private app EC2 with no public address;
- one private, encrypted, single-AZ RDS instance;
- no NAT Gateway;
- no load balancer;
- no permanent paid interface endpoints;
- one S3 gateway endpoint for ECR layer traffic;
- app AWS and external HTTPS traffic travels through Squid;
- RDS traffic remains direct inside the VPC;
- management uses SSM through Squid;
- EC2 Instance Connect Endpoint is the recovery path.

### Use private DNS, not fixed instance IPs

Create stable records:

```text
proxy.internal.staging.flow-form.com.au
app.internal.staging.flow-form.com.au
```

The app uses the proxy record. Caddy uses the app record. EC2 instances may use
dynamic private addresses, allowing CloudFormation replacement without the
current address collision.

Security groups authorize role-to-role traffic:

- public internet to Proxy on 80 and 443;
- App security group to Proxy on 3128;
- Proxy security group to App on the backend port;
- App security group to RDS on 5432;
- EICE security group to App on 22;
- selected telemetry paths between App and Proxy.

## CDK application

### Stack boundaries

```text
SecurityStack
    KMS, secrets, host roles, GitHub OIDC roles

RegistryStack
    Backend, Caddy, Squid and Alloy ECR repositories

NetworkStack
    VPC, four subnets, routes, S3 gateway endpoint,
    private hosted zone, EICE and security groups

DatabaseStack
    RDS PostgreSQL, subnet group, parameter group,
    log groups, administrative secret and IAM DB grants

ProxyStack
    Proxy EC2, role AMI, EIP, public/private DNS,
    role runtime parameters and user data

DatabaseBootstrapStack
    Operator-invoked private bootstrap Lambda and its exact access

DatabaseMigrationStack
    Operator-invoked private migration Lambda using the migrator identity

ApplicationStack
    App EC2, role AMI, private DNS, runtime parameters and user data

FrontendStack
    Private S3 origins, CloudFront, certificates and public DNS

ObservabilityStack
    CloudWatch alarms and deployment-health signals not owned by Alloy
```

Pass constructs directly between stacks. Do not reconstruct ARNs or rely on
manually copied output names.

### Mutable release state

CDK must not continuously own promoted release-manifest values. It declares IAM
access to the documented paths; the release operation owns their mutable
contents. This prevents a later infrastructure deployment from reverting a
container promotion.

### IAM identities

Create distinct GitHub OIDC roles for:

- CDK deployment;
- container image publication;
- machine-image build and publication;
- runtime release promotion;
- frontend publication;
- database migration.

Instance roles are separate:

- Proxy role: exact ECR repositories, proxy SSM path, observability secret,
  Route 53 DNS challenge actions, SSM managed-instance permissions.
- App role: exact ECR repositories, app SSM path, application secrets, KMS,
  SES, RDS IAM users, SSM managed-instance permissions.
- Bootstrap role: database administrative secret and RDS access only for the
  explicit bootstrap operation.
- Migration role: `rds-db:connect` for `flowform_migrator`, migration package
  access, and no administrative-secret permission.

## Database initialization

Persistent RDS deployment and PostgreSQL initialization remain separate.

`DatabaseStack` succeeds or fails solely on persistent AWS infrastructure.
`DatabaseBootstrapStack` supplies an idempotent Lambda in the private network.
An operator command invokes it after Proxy is available:

```text
flowform database bootstrap staging --dry-run
flowform database bootstrap staging --apply
```

The Lambda:

- obtains AWS service access through Squid;
- reads the RDS-managed administrative secret;
- connects directly to RDS;
- creates and verifies databases, roles, schemas, baseline tables, ownership,
  privileges, IAM grants, and a bootstrap version;
- returns only sanitized results.

Bootstrap failure cannot delete or roll back RDS. Later schema changes use the
separate migration identity and operation.

`DatabaseMigrationStack` packages `database/migrations/runner/` as a separate
private Lambda. It connects with an RDS IAM token as `flowform_migrator` and
assumes `flowform_owner` only for the objects it must change. It never reads the
RDS administrative secret.

Migration commands are explicit:

```text
flowform database migrate staging --plan
flowform database migrate staging --apply
flowform database verify staging
```

Plan mode compares the database migration ledger with the immutable repository
manifest and reports pending, applied, checksum-mismatched, or out-of-order
entries without changing the database. Apply mode refuses checksum drift,
records each successful migration transactionally, and runs database
verification afterward.

The initial runner is Lambda-based and each migration must fit inside the
bounded Lambda execution window. A migration expected to exceed that boundary
requires an explicitly designed maintenance job; it must not silently increase
the Lambda timeout or move migration execution into the application container.

## Operator interface

Provide one repository entry point:

```text
operations/bin/flowform
```

It dispatches focused commands without hiding the underlying AWS or Packer
actions:

```text
flowform validate
flowform container build <backend|caddy|squid|alloy>
flowform container publish <name> staging
flowform release promote <app|proxy> staging
flowform release deploy <app|proxy> staging
flowform release rollback <app|proxy> staging
flowform machine build <base|app|proxy|all>
flowform machine publish <app|proxy> staging
flowform machine prune staging --dry-run|--apply
flowform infra synth staging
flowform infra diff staging [stack]
flowform infra deploy staging [stack]
flowform database bootstrap staging --dry-run|--apply
flowform database migrate staging --plan|--apply
flowform database verify staging
flowform diagnose <app|proxy> staging
flowform verify staging
```

The dispatcher is thin. Each command lives in an ownership-specific module
under `operations/lib/`; do not create an untestable monolithic shell script.

## GitHub Actions

Start with five workflows, not one file per artefact:

```text
.github/workflows/
├── validate.yml
├── publish-containers.yml
├── publish-machine-images.yml
├── deploy-infrastructure.yml
└── promote-release.yml
```

- `validate.yml` runs contracts, containers, Packer, CDK, shell, and policy
  validation.
- `publish-containers.yml` uses a matrix for changed container contexts.
- `publish-machine-images.yml` performs the base-to-role lineage and publishes
  verified role AMIs.
- `deploy-infrastructure.yml` diffs and deploys approved CDK stacks.
- `promote-release.yml` promotes role manifests and invokes the matching SSM
  deployment command.

Path filtering decides which release unit changed. Reusable workflow jobs avoid
copying build logic.

The repository workflow remains:

```text
feature branch
→ reviewed pull request
→ merge into staging
→ build from the exact merged commit
→ publish immutable artefacts
→ promote reviewed manifests
→ deploy and verify staging
```

No workflow stores long-lived AWS access keys.

## One-shot implementation sequence

All work occurs in the overhaul branch, but implementation follows this order
so contracts exist before consumers.

### Phase 1: Establish the skeleton and contracts

- Create the target directories.
- Add the operator dispatcher and validation entry point.
- Define naming, instance context, runtime, and release schemas.
- Define database identity, bootstrap, and migration contracts.
- Add schema fixtures for staging.
- Add repository ownership READMEs.

Exit:

- Every planned file category has one documented owner.
- Contract fixtures validate.
- No Proxmox or rehearsal concept exists in the new tree.

### Phase 2: Build container images

- Implement Backend, Caddy, Squid, and Alloy contexts.
- Move all service behaviour and templates into their images.
- Add entrypoint and configuration validation.
- Add container healthchecks and non-root/read-only constraints where
  supported.
- Produce a deterministic source manifest for all bases and modules.

Exit:

- All four images build for `linux/amd64`.
- Caddy contains the Route 53 provider and validates its template.
- Squid renders and parses an approved policy.
- Alloy starts in both explicit roles.
- No container depends on a repository bind mount.

### Phase 3: Build the machine-image lineage

- Implement base, app, and proxy Packer builds.
- Implement role scripts and systemd units.
- Implement image manifests and lineage verification.
- Configure SSM Agent and EICE.
- Remove build credentials, cloud-init state, logs, and machine identity.

Exit:

- Base contains no role assets.
- App and Proxy share the exact recorded base.
- Cross-role assets are absent.
- Role services validate but do not require environment data at build time.

### Phase 4: Implement CDK foundations

- Implement environment config and contract loading.
- Implement Security, Registry, and Network stacks.
- Bootstrap CDK and deploy those stacks to staging.
- Publish exact ECR repository and role permissions.

Exit:

- Network has the four intended subnets and no NAT or paid interface endpoint.
- Registry and OIDC roles exist.
- Security-group and IAM assertions pass.
- CDK diff matches the declared target.

### Phase 5: Implement persistent data

- Implement and deploy DatabaseStack.
- Establish the authoritative core and response baseline schemas.
- Implement DatabaseBootstrapStack and the explicit operator command.
- Implement DatabaseMigrationStack, its plan/apply operation, and an empty
  initial migration chain after the baseline.
- Validate the bootstrap package and helper infrastructure without invoking it.
- Defer the live invocation until Proxy is deployed and Squid is available.

Exit:

- RDS is private, encrypted, single-AZ, and requires TLS.
- Bootstrap failure cannot roll back RDS.
- The helper is ready to create and verify both databases, IAM runtime roles,
  baseline tables, ownership, and privileges after Proxy deployment.
- Migration planning can distinguish an up-to-date schema from pending or
  incompatible changes without mutating RDS.

### Phase 6: Publish artefacts and runtime state

- Push all four container images and resolve digests.
- Build and publish App and Proxy AMIs.
- Seed non-secret runtime configuration.
- Seed secrets through file-based operator inputs.
- Promote initial role release manifests.

Exit:

- Every runtime image reference is a digest.
- Both role AMI parameters resolve to verified AMIs.
- No placeholder secret remains.
- Runtime contracts validate from AWS values.

### Phase 7: Deploy Proxy

- Implement and deploy ProxyStack.
- Start the baked proxy bootstrap service.
- Pull and validate Caddy, Squid, and Alloy.
- Obtain the public certificate through Route 53 DNS-01.

Exit:

- Proxy is online in SSM.
- Squid permits approved and denies unapproved destinations.
- Caddy serves a valid public certificate.
- Proxy deployment and rollback commands work without replacing EC2.

### Phase 8: Bootstrap data and deploy App

- Invoke database bootstrap through Squid and prove that repeat invocation is
  safe.
- Deploy DatabaseMigrationStack, run migration plan, and apply only the
  intended pending migrations before the application starts.
- Implement and deploy ApplicationStack.
- Configure app SSM Agent and Docker through private proxy DNS.
- Pull and start Backend, Alloy, and Valkey.
- Prove IAM-authenticated RDS connections.

Exit:

- App has no public route or address.
- App is online in SSM.
- Backend and Alloy are healthy.
- Backend opens both RDS connections with IAM tokens.
- Proxy reaches backend readiness through private DNS.

### Phase 9: Observability, frontend, and release automation

- Add deployment-health metrics and alarms.
- Prove Alloy logs and traces from both hosts.
- Implement and deploy FrontendStack.
- Complete GitHub publication, promotion, deployment, and rollback workflows.

Exit:

- Operators can distinguish EC2 health from FlowForm deployment health.
- Logs and traces are remotely queryable.
- Frontends and API use the intended domains.
- A container-only release and rollback complete without an AMI or CDK update.

### Phase 10: Acceptance and cleanup

- Run the full staging verification command.
- Reboot both hosts and prove self-convergence.
- Replace App and Proxy independently using their role AMIs.
- Exercise container rollback and AMI rollback.
- Run AMI pruning in dry-run and apply modes.
- Remove superseded infrastructure directories and scripts.
- Write concise current-state documentation from the verified result.

Exit:

- The new tree is the only supported AWS implementation.
- No runtime dependency points to a deleted or legacy path.
- Staging can be recreated from the reviewed repository and AWS prerequisites.

## Validation matrix

| Layer | Required validation |
| --- | --- |
| Contracts | JSON Schema validation, required/unknown key checks, fixtures |
| Shell | ShellCheck, formatting, strict-mode tests, secret-output tests |
| Containers | Build, vulnerability report, entrypoint test, config parse, healthcheck, Compose validation |
| Base AMI | Packer fmt/validate, package verification, hardening, cleanup, no role assets |
| Role AMIs | Parent lineage, exact scripts/units, no cross-role assets, SSM/EICE readiness |
| CDK | Ruff, Pyright, pytest assertions, synth, diff review |
| IAM | Exact resource assertions and negative permissions review |
| Network | Route, subnet, endpoint, DNS and security-group inspection |
| Database | Encryption, TLS, IAM auth, roles, ownership, grants, repeat bootstrap |
| Migrations | Immutable ordering, checksum verification, plan mode, migrator authorization, rollback policy |
| Runtime | SSM registration, release validation, container health, rollback |
| Public path | DNS, certificate, headers, Caddy readiness, API response |
| Recovery | EICE, reboot convergence, role AMI rollback, snapshot restore plan |

Image scanning is enabled and findings are recorded. Vulnerability remediation
may be deferred during early staging construction, but unresolved material
findings remain a production-readiness gate.

## Staging deployment order

```text
1. CDK bootstrap
2. SecurityStack
3. RegistryStack
4. NetworkStack
5. Publish container images
6. Build base, app and proxy AMIs
7. Publish role AMI parameters
8. DatabaseStack
9. Seed runtime configuration and secrets
10. Promote proxy release
11. ProxyStack
12. DatabaseBootstrapStack
13. Database bootstrap dry-run and apply
14. DatabaseMigrationStack
15. Database migration plan and apply
16. Promote app release
17. ApplicationStack
18. ObservabilityStack
19. FrontendStack
20. End-to-end verification
```

## Final acceptance criteria

The overhaul is complete only when:

- one command validates the complete infrastructure repository;
- three machine-image artefacts have verifiable lineage;
- CDK launches only App and Proxy AMIs;
- container configurations are owned by container images;
- normal container releases do not rebuild an AMI or deploy CDK;
- App and Proxy can be replaced independently;
- no host uses a fixed private address;
- private DNS is the host-to-host contract;
- App has no public network path;
- SSM and EICE management paths work;
- Squid is the enforced external egress path;
- RDS is private, encrypted, TLS-required, single-AZ, and bootstrapped;
- database bootstrap, migration, and development fixtures have separate
  physical ownership and execution authorities;
- the complete migration chain is verified against a fresh baseline;
- backend database access uses IAM tokens without runtime passwords;
- Caddy obtains and renews a public certificate;
- runtime releases automatically roll back on failed health checks;
- secrets never appear in source, user data, SSM String values, process
  arguments, Docker inspection, or logs;
- AMI and container publication use immutable artefacts;
- staging can be recreated from the exact reviewed commit;
- no implementation or test depends on Proxmox or rehearsal compatibility.

## Implementation discipline

- Build forward from the contracts and target structure.
- Do not copy a legacy file until its responsibility has been consciously
  assigned to the new model.
- Prefer a small amount of role-specific duplication over a universal script
  with environment and host branching.
- Do not introduce code generation in the first implementation. Load canonical
  JSON contracts directly and add generation only if repetition becomes a
  demonstrated problem.
- Do not create convenience wrappers until the underlying command has run
  successfully.
- Keep every phase deployable or testable inside the overhaul branch.
- Record unresolved decisions in this plan rather than hiding them in TODO
  comments.
