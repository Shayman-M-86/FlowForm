---
title: AWS IAM database authentication loose threads
aliases: ["AWS IAM database authentication loose threads"]
document_type: planning
status: draft
authority: working
verified_evidence_digest: null
last_edited: 2026-07-28
tags: [infrastructure, security, configuration]
related_code:
  - "../../../infra/deployment/aws/cdk/flowform_infra/stacks/database_stack.py"
  - "../../../infra/deployment/aws/cdk/flowform_infra/stacks/database_bootstrap_stack.py"
  - "../../../infra/deployment/aws/cdk/flowform_infra/database_bootstrap/"
  - "../../../infra/deployment/aws/cdk/flowform_infra/stacks/security_stack.py"
  - "../../../infra/deployment/aws/cdk/flowform_infra/stacks/application_stack.py"
  - "../../../infra/deployment/aws/scripts/bootstrap-database.sh"
  - "../../../infra/deployment/aws/scripts/publish-staging-images.sh"
  - "../../../infra/images/packer/provisioners/common/install-runtime-assets.sh"
  - "../../../infra/database/init/aws/"
  - "../../../infra/database/init/schema/"
  - "../../../infra/database/init/templates/"
  - "../../../backend/app/db/iam_auth.py"
related_docs:
  - "Engineering planning"
  - "AWS CDK staging plan"
  - "AWS database roles and bootstrap design"
  - "AWS DatabaseStack staging configuration"
  - "AWS stack specifications"
---

# AWS IAM database authentication loose threads

> Working checklist for the work still required to make RDS IAM database
> authentication function end to end. Network, RDS, and the baseline database
> bootstrap are deployed; application-host IAM authentication and later
> migration execution remain outstanding.

The source work is largely done: the backend, application bootstrap, CDK
resources, golden image, and RDS bootstrap runner implement the IAM path. The
database bootstrap has run against staging. What remains is the application
host connection, later migration execution, an intentional secret migration,
and shared container-path cleanup.

## Done

Implemented in source and locally validated. Network, RDS, and database
bootstrap items in this list are deployed to staging.

- **Backend auth mode.** `DatabaseSettings.auth_mode` selects `password` or
  `iam` per database, rejects a static credential supplied alongside `iam`, and
  is not derived from `FLOWFORM_ENV`.
- **Token provider.** `backend/app/db/iam_auth.py` signs a token per physical
  connection and injects it through SQLAlchemy's `do_connect` hook, leaving
  pooling behaviour unchanged.
- **App bootstrap.** Requires an explicit `FLOWFORM_DEPLOYMENT_TARGET`,
  validates both auth modes against it, and branches its database-secret
  handling. The runtime parameter contract names both auth-mode parameters.
- **RDS IAM authentication enabled.** `enable_iam_database_authentication` is
  set on the instance, and the DB resource ID is published to SSM.
- **`rds-db:connect` granted.** Scoped to exactly `flowform_core_app` and
  `flowform_response_app` by resource ID. The policy is created in
  `DatabaseStack` rather than added to the role in `SecurityStack`, because the
  reverse forms a stack dependency cycle.
- **RDS bootstrap boundary.** `DatabaseStack` now owns only persistent RDS
  infrastructure. The context-gated `DatabaseBootstrapStack` owns one
  idempotent VPC Lambda and its security groups. The operator script deploys
  that helper, creates one tagged temporary Secrets Manager interface endpoint,
  invokes the Lambda, checks its sanitized result, and requests endpoint
  deletion. A helper failure cannot roll back RDS.
- **RDS bootstrap contents.** The Lambda's packaged SQL creates
  `flowform_owner`, `flowform_migrator`, both runtime roles, both logical
  databases, application schemas, the current authoritative baseline tables,
  default privileges, and `GRANT rds_iam`. It records a version/checksum and
  verifies the exact table sets, ownership, privileges, isolation, and catalog
  state. Later schema evolution remains a separate migration operation.
- **Backend SSM parameters.** `ApplicationStack` publishes the backend runtime
  group under `/flowform/<scope>/backend/`, including both auth modes set to
  `iam`, the RDS endpoint, and explicit CORS origins. Parameter names come from
  the shared contract, and synth fails if a published value is not declared
  there.
- **Image reference promotion.** `publish-staging-images.sh promote` reads a
  release manifest and writes the five digest-pinned image parameters the
  runtime groups declare. Promotion is a separate subcommand from publication,
  so republishing an image never moves a running environment.
- **Host convergence assets and user data.** The golden image installs the
  bootstrap scripts and Compose files to `/opt/flowform/repo`; both instances
  carry user data that writes the bootstrap inputs and execs the host's script,
  with the app host passing `FLOWFORM_DEPLOYMENT_TARGET=aws`. Both hosts hold
  static private addresses, because deriving each from the other's instance
  forms a CloudFormation cycle.

The runner also resolves the boundary question the roles design left open:
AWS-specific database SQL lives under `infra/database/init/aws/`, shared
application schema snapshots live under `infra/database/init/schema/`, and the
Lambda packages both. Helper deployment, temporary endpoint management,
invocation, and cleanup remain under the AWS deployment scripts.

## Blocking threads

These stop a live IAM-authenticated connection.

### 0. Bring-up ordering

Not a gap in the source, but an ordering the tools do not enforce and nobody
has executed end to end. Each step depends on the previous one having produced
something the next reads.

```text
1. image build && image publish        -> AMI id in /flowform/<env>/ec2/baseAmiId
2. cdk deploy Network, Database        -> VPC and persistent RDS exist
3. bootstrap-database.sh --apply       -> helper, temporary endpoint,
                                          databases, roles, rds_iam grants
4. publish-staging-images.sh publish
   publish-staging-images.sh promote   -> BACKEND_IMAGE / ALLOY_IMAGE in SSM
5. cdk deploy Application              -> hosts boot and converge
```

Packer runs *before* CDK, not after: `ApplicationStack` resolves the base AMI
from SSM at deployment time, so that parameter must already hold a real AMI id.

Step 4 must precede step 5. App bootstrap requires non-empty `BACKEND_IMAGE`
and `ALLOY_IMAGE` and stops without them, so an instance launched before
promotion fails in user data. That is fail-closed rather than silently broken,
but it means promotion is a prerequisite of the first application deployment,
not a later release step.

Do not automate this sequence before running it manually. Wrapping an
unexecuted ordering in a script fixes assumptions that have never been tested;
the release pipeline in Phase 8 of the staging plan is where it belongs once
proven.

### 1. Deploy and run the bootstrap against real RDS — resolved

The retired CloudFormation custom-resource attempt rolled RDS back after its
controller failed. The replacement persistent `DatabaseStack` and separate
operator-invoked helper are now deployed. Temporary endpoint creation, secret
retrieval, baseline schema load, PostgreSQL verification, repeat invocation,
and endpoint cleanup have all completed successfully against staging.

## Non-blocking threads

Required for a defensible end state, but they do not stop a connection.

### 2. Retire the AWS `db-secrets` resource

`security_stack.py` still provisions `db-secrets` and still grants the
application role access to it, although AWS bootstrap no longer consumes it.
The rehearsal path still needs its LocalStack equivalent, so this is an
intentional migration with an ordering constraint, not a deletion.

### 3. Remove password interpolation from the shared templates

Four `PASSWORD '${...}'` substitutions remain across
`infra/database/init/templates/`. IAM removes the AWS runtime passwords but not
the development or rehearsal ones, so the rendered-SQL mechanism still needs
replacing on the container path.

### 4. Backport the ownership fix to the container path

The container templates still set `search_path`, load the schema, then reassert
ownership of the schema only, leaving objects owned by the initialization
administrator. The AWS runner proves the correct ordering — create objects
under `SET ROLE flowform_owner`. Development and rehearsal remain affected until
this is carried across.

### 5. Choose the AWS migration execution identity

Bootstrap now creates `flowform_migrator` as a passwordless IAM-authenticated
database role and grants it membership of `flowform_owner`. No AWS principal
yet has `rds-db:connect` permission for that role. Choose where migrations run,
then grant that one AWS identity the exact database-user permission. This is a
constraint on the execution environment, not merely on PostgreSQL.

### 6. Add `REVOKE CONNECT ... FROM PUBLIC` to the container path

The AWS runner revokes it; the shared templates do not. Local development hides
the issue because its two databases live in separate clusters, but rehearsal
runs both in one cluster and is exposed.

## Verification threads

### 7. Prove a token-authenticated connection from the application host

The bootstrap verifier checks `rds_iam` membership and the PostgreSQL catalog;
it does not open an IAM-token connection. The backend's `do_connect` path must
be exercised against real RDS from the app instance. That remains the final
integration check and cannot be done in LocalStack Community.

### 8. Correct the SCRAM acceptance-gate wording

The staging acceptance gate requires that "all login identities use
SCRAM-SHA-256". Roles granted `rds_iam` do not use SCRAM, so the gate as
written contradicts the intended AWS end state. Reword it to distinguish the
password-authenticated identities from the IAM-authenticated ones, and adjust
the verification checks that assert SCRAM for every login role.

## Sequencing

```text
0 bring-up ordering ---> 1 deploy + run bootstrap ---+--> 7 app-host connection
                                                     |
                                                     +--> 8 gate wording

2 db-secrets retirement  \
3 template passwords      \
4 ownership backport       >  independent of the connection path
5 migrator decision       /
6 template REVOKE CONNECT/
```

Thread 1 is the whole critical path now that the source work is done, and
thread 0 is the order it has to happen in. Thread 7 is only meaningful once
both are complete. Threads 2 through 6 can proceed in parallel; 4 and 6 are
correctness fixes for development and rehearsal rather than AWS work.

## Related documents

- [[planning-index|Engineering planning]]
- [[aws-cdk-staging-plan|AWS CDK staging plan]]
- [[aws-database-roles-and-bootstrap|AWS database roles and bootstrap design]]
- [[aws-database-stack-configuration|AWS DatabaseStack staging configuration]]
- [[aws-stack-specifications|AWS stack specifications]]
