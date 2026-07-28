---
title: AWS IAM database authentication loose threads
aliases: ["AWS IAM database authentication loose threads"]
document_type: planning
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-07-29
tags: [infrastructure, security, configuration]
related_code:
  - "../../../infra/deployment/aws/cdk/flowform_infra/stacks/database_stack.py"
  - "../../../infra/deployment/aws/cdk/flowform_infra/stacks/database_bootstrap_stack.py"
  - "../../../infra/deployment/aws/cdk/flowform_infra/stacks/application_stack.py"
  - "../../../infra/deployment/aws/scripts/bootstrap-database.sh"
  - "../../../infra/database/init/aws/"
  - "../../../backend/app/db/iam_auth.py"
related_docs:
  - "Engineering planning"
  - "AWS staging runtime convergence"
  - "AWS database roles and bootstrap design"
  - "AWS DatabaseStack staging configuration"
---

# AWS IAM database authentication loose threads

> The database-side foundation is complete. This page now tracks only the
> remaining runtime proof and deferred cleanup.

## Completed

- RDS IAM database authentication is enabled.
- `flowform_core_app` and `flowform_response_app` use IAM tokens and have no
  stored runtime password.
- `rds-db:connect` is scoped to those two database identities by RDS resource
  ID.
- The backend can generate a token per physical SQLAlchemy connection.
- The application runtime contract selects IAM mode for both databases.
- The isolated bootstrap helper created and repeat-verified the two databases,
  roles, schemas, baseline tables, ownership, default privileges, and
  `rds_iam` grants.
- Persistent RDS infrastructure is independent from the optional bootstrap
  helper, so a helper failure cannot roll back the database.

## Current blocker

The backend container is not yet healthy on the deployed app host, and access
to that host is currently unavailable through SSM. Consequently, the final
live proof has not happened:

```text
AppTaskRole
    -> RDS IAM token
    -> TLS connection to RDS
    -> flowform_core_app / flowform_response_app
    -> application query
```

Restore app-host access, diagnose the backend, and perform this proof as part
of [[aws-staging-runtime-convergence|AWS staging runtime convergence]].

## Deferred database work

These are not blockers for diagnosing the current host:

- create the separate migration execution identity and release workflow;
- decide when legacy password-mode runtime secrets can be retired;
- remove or clearly isolate shared SQL templates that interpolate passwords;
- backport ownership and privilege improvements to development and rehearsal
  where appropriate;
- decide whether runtime roles should lose default `CONNECT` on unrelated
  databases;
- add a recurring test that exercises token refresh after pooled connections
  are recycled;
- migrate the retained DatabaseBootstrap helper from automatic cross-stack
  exports to stable explicit contracts, then remove the temporary
  `--exclusively` deployment constraint.

## Completion boundary

Close this list when:

- both runtime database identities connect from the deployed backend using IAM;
- no static runtime database password is present in the app environment;
- TLS verification and connection recycling are exercised;
- migrations have a separately authorized execution path;
- the obsolete secret and SQL compatibility paths have an explicit disposition.
