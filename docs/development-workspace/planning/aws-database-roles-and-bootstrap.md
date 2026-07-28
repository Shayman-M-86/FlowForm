---
title: AWS database roles and bootstrap design
aliases: ["AWS database roles and bootstrap design"]
document_type: planning
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-07-28
tags: [infrastructure, security, configuration]
related_code:
  - "../../../infra/database/init/"
  - "../../../infra/containers/strategies/dev/compose/"
  - "../../../infra/containers/strategies/rehearsal/compose/db.yml"
  - "../../../infra/deployment/bootstrap/bootstrap-db.sh"
  - "../../../infra/deployment/proxmox/scripts/lib/cmd_verify.sh"
  - "../../../infra/deployment/aws/cdk/flowform_infra/stacks/database_stack.py"
  - "../../../infra/deployment/aws/cdk/flowform_infra/stacks/security_stack.py"
related_docs:
  - "Engineering planning"
  - "AWS CDK staging plan"
  - "AWS DatabaseStack staging configuration"
  - "ADR 0001: AWS staging infrastructure target"
  - "Database migrations"
  - "Secrets and configuration"
---

# AWS database roles and bootstrap design

> Working design note for the staging Database stack and later database
> bootstrap. It describes proposed reuse and corrections; it does not claim
> that RDS, the roles, or a retained-data migration path have been implemented.

FlowForm already has most of the recommended PostgreSQL identity model. The AWS
path should evolve the maintained database initialization assets rather than
create a separate AWS-only role and schema system.

The Proxmox rehearsal is the closest structural source because it already runs
one PostgreSQL cluster containing both logical databases. Local development
uses two PostgreSQL containers, so it proves the individual core and response
contracts but does not expose every cross-database privilege issue that exists
when both databases share one cluster.

## Intended identity model

| Identity | Purpose | Current state | AWS treatment |
| --- | --- | --- | --- |
| `flowform_admin` | RDS administration and emergency recovery | Local and rehearsal use environment-specific initialization administrators | Create as the RDS master identity; do not expose it to the application |
| `flowform_owner` | Stable owner of schemas and application objects | Already created as `NOLOGIN` | Reuse, but ensure migrations actually create objects as this role |
| `flowform_migrator` | Bootstrap and ordered schema changes | Missing | Add with a dedicated secret and permission to assume `flowform_owner` |
| `flowform_core_app` | Runtime access to core data | Implemented | Reuse with the existing managed password |
| `flowform_response_app` | Runtime access to response data | Implemented | Reuse with the existing managed password |

The authority flow should be:

```text
CDK / RDS
  |
  +--> flowform_admin
         |
         +--> creates databases, extensions, owner, and migrator
                  |
                  v
             flowform_migrator
                  |
                  +--> SET ROLE flowform_owner
                            |
                            +--> owns schemas and application objects

flowform_core_app ---------> flowform_core.core_app only
flowform_response_app -----> flowform_response.response_app only
```

## Existing assets to preserve

### Application identities

The shared initialization target already creates `flowform_core_app` and
`flowform_response_app` with independent passwords. Both roles are explicitly
kept low privilege:

```sql
LOGIN
NOSUPERUSER
NOCREATEDB
NOCREATEROLE
NOREPLICATION
NOBYPASSRLS
```

These names are already consumed by local configuration, rehearsal Compose,
backend settings, and verification. They should remain the staging runtime
identities.

### Owner and schema boundaries

The templates already create `flowform_owner` as `NOLOGIN`, create the
`core_app` and `response_app` schemas with that authorization, and revoke
public access to both the default `public` schema and each application schema.

The grant templates already provide the runtime roles with:

- `USAGE` on their intended schema;
- `SELECT`, `INSERT`, `UPDATE`, and `DELETE` on its tables;
- `USAGE`, `SELECT`, and `UPDATE` on its sequences;
- an application-specific `search_path`;
- default-privilege intent for future tables and sequences.

They do not grant routine schema creation, extension management, role
management, or blanket `ALL PRIVILEGES`.

### Password and SCRAM handling

Local development already generates separate 32-character initialization and
application passwords. Rehearsal uses an ephemeral initialization password and
retrieves the two managed application passwords from
`flowform/nonprod/db-secrets`.

The rehearsal bootstrap materialises those values in tmpfs-backed files and
avoids putting their values on the host command line. The PostgreSQL runtime
generates SCRAM-SHA-256 verifiers, and rehearsal verification checks that both
application roles are low privilege and SCRAM-backed.

The reusable contract is:

```text
flowform/nonprod/db-secrets
  |-- db_core_app_password
  +-- db_response_app_password
```

The AWS application bootstrap should continue to deliver those values through
separate read-only secret files.

### Schema SQL and verification

The maintained core and response schema files remain the canonical
initialization snapshots. Rehearsal verification already proves:

- both logical databases exist;
- `flowform_owner` is `NOLOGIN`;
- both application identities use SCRAM and lack elevated attributes;
- both application schemas exist;
- schema ownership is assigned to `flowform_owner`;
- schema objects and application grants exist;
- both application identities can authenticate to their intended database.

These checks are a strong base for an RDS post-bootstrap verifier.

## Required adaptations

### Add a migration identity

Introduce `flowform_migrator` as a separate login identity:

```sql
CREATE ROLE flowform_migrator
WITH
    LOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    NOBYPASSRLS;

GRANT flowform_owner TO flowform_migrator;
```

Its password should live in a separate secret such as:

```text
flowform/nonprod/db-migration-secrets
```

Only the controlled migration runner and its deployment identity should read
that secret. The application instance role should not.

Configure the membership so migrations explicitly use:

```sql
SET ROLE flowform_owner;
```

Normal migrator sessions should not silently inherit owner authority before
that deliberate role change.

### Correct application-object ownership

The current templates assign each schema to `flowform_owner`, then load the
schema SQL after setting only `search_path`. They do not set the effective role
to `flowform_owner`.

Consequently, tables, functions, sequences, and other objects are likely
created as the initialization administrator even though their containing
schema is owner-owned. Reasserting schema ownership afterward does not transfer
ownership of the contained objects.

The RDS bootstrap should separate elevated setup from application-object
creation:

1. `flowform_admin` creates both databases, required extensions, the owner, and
   the migrator.
2. `flowform_migrator` connects to each database.
3. The migrator runs `SET ROLE flowform_owner`.
4. The maintained schema SQL creates application objects.
5. Grants and default privileges are applied for the matching runtime role.

The verifier must check representative table, sequence, and function ownership,
not only schema ownership.

### Enforce database connection isolation

PostgreSQL grants database `CONNECT` to `PUBLIC` by default. Granting each
runtime role access to its intended database does not remove that default.

The shared-cluster path must first run:

```sql
REVOKE CONNECT ON DATABASE flowform_core FROM PUBLIC;
REVOKE CONNECT ON DATABASE flowform_response FROM PUBLIC;
```

It can then grant the intended access:

| Identity | `flowform_core` | `flowform_response` |
| --- | ---: | ---: |
| `flowform_core_app` | Allow | Deny |
| `flowform_response_app` | Deny | Allow |
| `flowform_migrator` | Allow | Allow |
| `flowform_admin` | Allow | Allow |

Local development's two independent clusters conceal this issue because the
other logical database does not exist in the same cluster. Rehearsal and RDS
must include explicit negative connection tests.

### Provision the administrator through RDS

Local development uses `flowform-admin`, and rehearsal uses
`flowform_rehearsal_init`. Their purpose resembles the planned administrator,
but their provisioning mechanism does not.

The Database stack should ask RDS to create `flowform_admin` and manage or
generate its password in Secrets Manager using the FlowForm KMS key. SQL
bootstrap must not attempt to create the RDS master identity.

The credential is reserved for:

- initial database and role setup;
- required extension creation;
- emergency recovery;
- permission repair;
- management of the migration identity.

The backend, Gunicorn, SQLAlchemy runtime sessions, and routine migrations must
not receive it.

### Replace destructive password reconciliation

Rehearsal deliberately drops and recreates its disposable cluster when a
managed application password changes. That is appropriate for its tmpfs data
and must not transfer to retained RDS storage.

An RDS rotation changes the PostgreSQL role and Secrets Manager together:

```text
generate replacement
  |
  +--> ALTER ROLE ... PASSWORD
  |
  +--> update Secrets Manager
  |
  +--> restart or reload the affected application connection
  |
  +--> verify new connections and expire old pooled connections
```

Core and response credentials should rotate independently. Automation should
wait until this two-system operation has a tested rollback path.

### Strengthen credential-bearing execution

The existing renderer substitutes passwords into temporary generated SQL. It
suppresses credential-bearing role SQL from normal output, but the generated
file still contains the password and assumes values are safe for direct SQL
quoting.

Retain the database, schema, and grant SQL, but use a safer mechanism for role
creation and password changes. Candidate approaches are:

- a small Psycopg bootstrap program using safe identifier composition and
  bound values where supported;
- carefully quoted `psql` variables read from files;
- a purpose-built migration container that reads mounted secret files.

Do not put credentials in retained SQL, shell arguments, logs, user data,
CloudFormation outputs, or plain-text SSM parameters.

## Reuse boundary

The repository should continue to have one canonical set of names, schema SQL,
role invariants, and grants, with environment-specific runners around it:

```text
infra/database/init/
  |
  +-- schema/
  |     +-- core schema snapshot                 reuse
  |     +-- response schema snapshot             reuse
  |
  +-- templates/
  |     +-- database creation                    adapt
  |     +-- PUBLIC CONNECT revocation            add
  |     +-- owner and runtime roles              reuse/adapt
  |     +-- migrator role and membership         add
  |     +-- schema creation under owner role     adapt
  |     +-- runtime grants/default privileges    reuse/adapt
  |
  +-- runners
        +-- empty local PostgreSQL entrypoint     retain
        +-- remote retained-RDS migration path   add
```

Do not fork the schema and grant definitions into an unrelated AWS-only SQL
tree. RDS needs a different execution path because it is a remote retained
service, not a different data model.

## DatabaseStack boundary

`DatabaseStack` should provision the RDS service and infrastructure credential:

- one private, encrypted, single-AZ PostgreSQL instance;
- its subnet group, security group association, parameter group, backups, and
  logs;
- an RDS-created `flowform_admin` credential;
- non-secret endpoint/configuration contracts.

It should not mutate application schemas through a CloudFormation custom
resource. The later controlled migration/bootstrap operation should create:

- `flowform_core` and `flowform_response`;
- `flowform_owner` and `flowform_migrator`;
- both application roles or their current passwords;
- `pgcrypto`;
- schemas, application objects, grants, and default privileges.

This preserves the authority boundary:

```text
CDK deployment --> database service
migration authority --> database contents
application authority --> runtime data operations
```

## Verification additions

Extend the rehearsal and future RDS verification to prove:

- `flowform_owner` is `NOLOGIN` and owns representative application objects;
- `flowform_migrator` is low privilege and can explicitly assume the owner;
- the migrator can connect to both databases;
- the core identity cannot connect to the response database;
- the response identity cannot connect to the core database;
- neither runtime identity can create databases, roles, schemas, extensions,
  or tables;
- neither runtime identity can use the default `public` schema;
- current tables have the intended CRUD grants;
- new owner-created tables and sequences inherit the intended default grants;
- all login identities use SCRAM-SHA-256;
- secrets do not appear in output or retained rendered files;
- password rotation updates retained PostgreSQL roles without destroying data.

## Recommended implementation direction

Preserve the existing three-role foundation and add the missing authority
boundary:

1. Keep `flowform_owner`, `flowform_core_app`, and
   `flowform_response_app`.
2. Add `flowform_migrator` with its own secret.
3. Provision `flowform_admin` as the RDS master identity.
4. Revoke `PUBLIC CONNECT` from both databases.
5. Run schema creation as `flowform_owner` through the migrator.
6. Adapt the existing schema and grant assets instead of copying them.
7. Replace rehearsal's destructive password resynchronization with a retained
   in-place process.
8. Keep RDS provisioning and database-content migration as separate release
   authorities.

This retains parity across development, rehearsal, and staging while giving
the retained AWS database a safer operational lifecycle.

## Related documents

- [[planning-index|Engineering planning]]
- [[aws-cdk-staging-plan|AWS CDK staging plan]]
- [[aws-database-stack-configuration|AWS DatabaseStack staging configuration]]
- [[0001-aws-staging-infrastructure-target|ADR 0001: AWS staging infrastructure target]]
- [[database-migrations|Database migrations]]
- [[secrets-and-configuration|Secrets and configuration]]
