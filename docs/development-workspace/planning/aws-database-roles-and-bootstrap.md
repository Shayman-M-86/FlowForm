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
  - "../../../infra/database/init/aws/"
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

> Working design note. The AWS path described here is implemented in source but
> has never run against a deployed RDS instance. Outstanding work is tracked in
> [[aws-iam-database-auth-loose-threads|AWS IAM database authentication loose
> threads]].

Most of this document's original proposal has been implemented. What remains
here is the identity model, the reuse boundary that the implementation settled,
and the decisions still open.

## Identity model

| Identity | Purpose | AWS authentication |
| --- | --- | --- |
| `flowform_admin` | RDS administration, bootstrap, recovery | RDS-managed password in Secrets Manager |
| `flowform_owner` | Owns schemas and application objects | `NOLOGIN` |
| `flowform_core_app` | Runtime access to core data | IAM token only; no stored password |
| `flowform_response_app` | Runtime access to response data | IAM token only; no stored password |

```text
CDK / RDS --> flowform_admin
                  |
                  +--> databases, extensions, owner, runtime roles
                  |
                  +--> creates application objects under SET ROLE flowform_owner

flowform_core_app ---------> flowform_core only
flowform_response_app -----> flowform_response only
```

Development and rehearsal keep password authentication against their local
PostgreSQL clusters and use the shared container templates. Only the AWS path
uses IAM.

## Reuse boundary

The implementation settled the question this document originally left open. The
split is not development-versus-AWS; it is **disposable-versus-retained**.
Rehearsal and development can drop and recreate a cluster, so their runner can
assume run-once-on-empty semantics. RDS cannot.

That difference lives entirely in the runner. It does not live in the schema
definitions, which are reused verbatim.

```text
infra/database/init/
  |
  +-- schema/         shared, reused verbatim by both paths
  +-- templates/      container entrypoint path (dev, rehearsal)
  +-- aws/            RDS SQL: roles, databases, schema load, grants, verify

infra/deployment/aws/scripts/bootstrap-database.sh
                      remote runner: endpoint, credentials, ordering, checks
```

Deployment concerns stay under the AWS deployment tree, mirroring how Proxmox
keeps its Terraform and scripts together. Database logic stays beside the other
database assets.

## Constraints the implementation had to satisfy

Recorded because they are not obvious and will resurface in any rework:

- **`flowform_admin` is `rds_superuser`, not a superuser.** It must be granted
  membership of `flowform_owner` to set default privileges on its behalf.
- **`pgcrypto` must be created before `SET ROLE`.** `flowform_owner` cannot
  create extensions.
- **`search_path` must retain `public` during the schema load.** The schema
  files call `gen_random_uuid` and `gen_random_bytes`; dropping `public` fails
  at the first column default that uses one.
- **The shared schema snapshots use unguarded `CREATE TABLE`.** They cannot be
  re-applied to a populated schema, so the AWS runner skips the load when
  application objects already exist. It provisions empty databases; it is not a
  migration path.
- **`REVOKE CONNECT ... FROM PUBLIC` must precede the per-role grants.** While
  `PUBLIC` holds `CONNECT`, every role in the cluster reaches both databases.

## Object ownership

The container templates set `search_path`, load the schema, then reassert
ownership of the *schema* only. Objects inside it stay owned by the
initialization administrator, and `ALTER DEFAULT PRIVILEGES FOR ROLE
flowform_owner` then applies to a role that owns nothing, so future tables
receive no grants.

The AWS runner avoids this by creating objects under `SET ROLE flowform_owner`
and asserting ownership afterwards. Local validation confirmed all core and
response tables and sequences owned by `flowform_owner`.

The container path still has the defect. Backporting it is tracked as a loose
thread.

## Open decisions

- **`flowform_migrator`.** Not implemented. The AWS runner provisions empty
  databases as `flowform_admin`. Under IAM the migrator could be an IAM
  identity rather than a new stored credential, but only if migrations run from
  something holding an AWS identity — a constraint on where migrations execute.
- **Password handling on the container path.** The rendered-SQL mechanism still
  substitutes passwords into generated SQL. IAM removes the AWS runtime
  passwords but not the development or rehearsal ones.
- **Rotation.** Rehearsal drops and recreates its disposable cluster when a
  managed password changes. That must not transfer to retained storage. IAM
  removes the question for the AWS runtime roles; it remains for
  `flowform_admin` and for the container path.

## Verification

The AWS runner proves, against a real PostgreSQL cluster: owner is `NOLOGIN`;
runtime identities are low privilege, hold `rds_iam`, and have no stored
password; `PUBLIC` holds no `CONNECT`; each runtime identity reaches only its
own database; and every step is idempotent. The verifier was negative-tested by
breaking isolation deliberately.

Still unproven: a token-authenticated connection from the application host
through the backend's connection path, which requires deployed infrastructure.

## Related documents

- [[planning-index|Engineering planning]]
- [[aws-iam-database-auth-loose-threads|AWS IAM database authentication loose threads]]
- [[aws-cdk-staging-plan|AWS CDK staging plan]]
- [[database-migrations|Database migrations]]
