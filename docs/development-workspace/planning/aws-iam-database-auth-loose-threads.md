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
  - "../../../infra/deployment/aws/cdk/flowform_infra/stacks/security_stack.py"
  - "../../../infra/deployment/aws/cdk/flowform_infra/stacks/application_stack.py"
  - "../../../infra/deployment/aws/scripts/bootstrap-database.sh"
  - "../../../infra/deployment/aws/scripts/publish-staging-images.sh"
  - "../../../infra/images/packer/provisioners/common/install-runtime-assets.sh"
  - "../../../infra/database/init/aws/"
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
> authentication function end to end. It records outstanding items and what has
> been implemented in source; nothing here has been deployed to AWS.

The source work is done: the backend, the application bootstrap, the CDK
resources, the golden image, and the RDS bootstrap runner all implement the IAM
path. What remains is deploying it in the right order, an intentional secret
migration, and the shared container-path cleanups.

## Done

Implemented in source and locally validated. None of it is deployed.

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
- **RDS bootstrap runner.** `infra/deployment/aws/scripts/bootstrap-database.sh`
  plus `infra/database/init/aws/` create the databases, roles, schemas, grants,
  and `GRANT rds_iam`. Validated against PostgreSQL 17: all objects owned by
  `flowform_owner`, `PUBLIC` holds no `CONNECT`, neither runtime role has a
  stored password, each reaches only its own database, all steps idempotent,
  and the verifier fails correctly when isolation is broken.
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

The runner also resolves the boundary question the roles design left open: the
SQL is AWS-specific and lives beside the shared assets, while the deployment
concerns (endpoint discovery, credentials, ordering, live checks) live under
the AWS deployment scripts. The shared schema snapshots are reused verbatim.

## Blocking threads

These stop a live IAM-authenticated connection.

### 0. Bring-up ordering

Not a gap in the source, but an ordering the tools do not enforce and nobody
has executed end to end. Each step depends on the previous one having produced
something the next reads.

```text
1. image build && image publish        -> AMI id in /flowform/<env>/ec2/baseAmiId
2. cdk deploy Network, Database        -> VPC and RDS exist
3. bootstrap-database.sh --apply       -> databases, roles, rds_iam grants
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

### 1. Deploy and run the bootstrap against real RDS

`DatabaseStack` has never deployed successfully; the earlier attempt rolled
back on the parameter-group value and the stack was deleted. The runner has
therefore never contacted a real instance. Its AWS-facing logic — endpoint
discovery, admin-secret retrieval, and the live IAM connection checks — is
unexercised.

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

### 5. Decide whether `flowform_migrator` is still wanted

The roles design proposes a dedicated migration identity. The AWS runner does
not create one: it provisions empty databases as `flowform_admin` and is not a
migration path. Under IAM the migrator could be an IAM identity rather than a
new stored credential, but only if migrations run from something holding an AWS
identity. That is a constraint on where migrations execute, not just how they
authenticate, and it should be settled before the role is added.

### 6. Add `REVOKE CONNECT ... FROM PUBLIC` to the container path

The AWS runner revokes it; the shared templates do not. Local development hides
the issue because its two databases live in separate clusters, but rehearsal
runs both in one cluster and is exposed.

## Verification threads

### 7. Prove a token-authenticated connection from the application host

The runner's live checks prove the database accepts IAM tokens. They do not
prove the backend's `do_connect` path works against real RDS from the app
instance. That remains the final integration check and cannot be done in
LocalStack Community.

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
