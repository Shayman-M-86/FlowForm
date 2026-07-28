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
  - "../../../infra/deployment/aws/cdk/flowform_infra/database_bootstrap/"
  - "../../../infra/deployment/aws/cdk/flowform_infra/stacks/database_bootstrap_stack.py"
  - "../../../infra/database/init/aws/"
  - "../../../infra/database/init/schema/"
  - "../../../infra/database/init/templates/"
  - "../../../infra/deployment/aws/scripts/bootstrap-database.sh"
  - "../../../infra/deployment/bootstrap/bootstrap-db.sh"
related_docs:
  - "Engineering planning"
  - "AWS IAM database authentication loose threads"
  - "AWS CDK staging plan"
  - "Database migrations"
---

# AWS database roles and bootstrap design

> Working design note. The AWS bootstrap path is implemented and has run
> successfully against staging RDS. Outstanding runtime IAM and later-migration
> work is tracked in [[aws-iam-database-auth-loose-threads|AWS IAM database
> authentication loose threads]].

Most of this document's original proposal has been implemented. What remains
here is the identity model, the reuse boundary that the implementation settled,
and the decisions still open.

## Identity model

| Identity | Purpose | AWS authentication |
| --- | --- | --- |
| `flowform_admin` | RDS administration, bootstrap, recovery | RDS-managed password in Secrets Manager |
| `flowform_owner` | Owns schemas and application objects | `NOLOGIN` |
| `flowform_migrator` | Owns migration sessions and assumes `flowform_owner` | IAM token only; no stored password |
| `flowform_core_app` | Runtime access to core data | IAM token only; no stored password |
| `flowform_response_app` | Runtime access to response data | IAM token only; no stored password |

```text
RDS master secret --> bootstrap Lambda --> flowform_admin
                                            |
                                            +--> databases, extensions, roles
                                            +--> baseline tables, schemas, grants

flowform_migrator --------> assumes flowform_owner for later schema changes

flowform_core_app ---------> flowform_core only
flowform_response_app -----> flowform_response only
```

Development and rehearsal keep password authentication against their local
PostgreSQL clusters and use the shared container templates. Only the AWS path
uses IAM.

## Reuse boundary

The implementation settled the question this document originally left open.
Development and rehearsal can drop and recreate a cluster and continue to use
the shared container templates. The retained RDS path uses a small, versioned
bootstrap package that loads the authoritative core and response schema
snapshots when their application schemas are empty. Subsequent schema evolution
remains migration work.

```text
infra/database/init/templates/
                      container entrypoint path (development and rehearsal)

infra/database/init/aws/
                      AWS role, grant, and verification SQL

infra/database/init/schema/
                      shared authoritative core and response baseline schemas

infra/deployment/aws/cdk/flowform_infra/database_bootstrap/bootstrap/
                      Lambda orchestration that packages both SQL inputs

infra/deployment/aws/scripts/bootstrap-database.sh
                      helper deployment, temporary endpoint, invocation, cleanup
```

Deployment concerns stay under the AWS deployment tree, mirroring how Proxmox
keeps its Terraform and scripts together. AWS bootstrap logic stays with the
helper that executes it.

## Constraints the implementation had to satisfy

Recorded because they are not obvious and will resurface in any rework:

- **`flowform_admin` is `rds_superuser`, not a superuser.** It must be granted
  membership of `flowform_owner` to set default privileges on its behalf.
- **`REVOKE CONNECT ... FROM PUBLIC` must precede the per-role grants.** While
  `PUBLIC` holds `CONNECT`, every role in the cluster reaches both databases.
- **Baseline bootstrap and later migrations are separate.** Bootstrap creates
  extensions, roles, databases, schemas, the current baseline application
  tables, default privileges, and its own version record. A migration runner
  must evolve an already-bootstrapped schema.
- **The RDS master secret is bootstrap-only.** The Lambda reads it through a
  temporary Secrets Manager interface endpoint. Runtime and migration
  identities use IAM authentication.

## Object ownership

The bootstrap creates each application schema with `flowform_owner` as owner,
loads the authoritative baseline while executing as that role, and grants
`flowform_migrator` membership of it. It records default table and sequence
privileges for the runtime identity in each schema. The later migration runner
must assume `flowform_owner` before changing application objects so those
ownership and default-privilege rules continue to take effect.

The container path still creates application objects as its initialization
administrator rather than under `flowform_owner`. Backporting the ownership
model remains a loose thread.

## Open decisions

- **Migration execution identity.** The PostgreSQL `flowform_migrator` role is
  implemented, has no password, holds `rds_iam`, and can assume
  `flowform_owner`. No AWS principal yet has `rds-db:connect` permission for
  that database role, so the migration execution environment still needs to be
  chosen.
- **Password handling on the container path.** The rendered-SQL mechanism still
  substitutes passwords into generated SQL. IAM removes the AWS runtime
  passwords but not the development or rehearsal ones.
- **Rotation.** Rehearsal drops and recreates its disposable cluster when a
  managed password changes. That must not transfer to retained storage. IAM
  removes the question for the AWS runtime roles; it remains for
  `flowform_admin` and for the container path.

## Verification

The bootstrap implementation and its CDK boundaries are locally tested and have
run successfully against staging RDS. Its packaged verifier checks role
properties, `rds_iam` membership, database ownership, removal of public
`CONNECT`, exact baseline table sets, table ownership, runtime table and
sequence privileges, schema ownership, and cross-schema access.

Still unproven: a token-authenticated connection from the application host
through the backend's connection path and the later migration runner.

## Related documents

- [[planning-index|Engineering planning]]
- [[aws-iam-database-auth-loose-threads|AWS IAM database authentication loose threads]]
- [[aws-cdk-staging-plan|AWS CDK staging plan]]
- [[database-migrations|Database migrations]]
