# Secrets and Config

## Three places config can live

| Location | What goes here | Managed by |
|---|---|---|
| Local `.env` / Docker secrets (`infra/docker/`) | Local dev only — never real prod credentials | Manual, gitignored |
| SSM Parameter Store | Non-secret config (KMS key ARN, region) | `security_stack.py` |
| Secrets Manager | Actual secret values (passwords, client secrets) | `security_stack.py` (shape only — see below) |

## What `security_stack.py` creates

Two Secrets Manager entries, named `flowform/<env>/<name>`, each holding
multiple values as a JSON blob (grouped by what's consumed together at
runtime). ECS can still map an individual JSON key back out to its own env
var via the `secretName:jsonKey::` ARN suffix, so application code reads
each value the same way it would from a single-value secret.

- `app-secrets` — `app_secret_key` (Flask `FLOWFORM_APP_SECRET_KEY`),
  `auth0_mgmt_secret` (Auth0 Management API client secret), and
  `linkage_secret` (HMAC secret deriving opaque locators between the core
  and response databases). There's no `auth0_client_secret` — the
  user-facing Auth0 application (`FLOWFORM_AUTH0_CLIENT_ID`) is a
  public/PKCE client with no client secret; only the Management API client
  is confidential.
- `db-secrets` — `db_core_app_password` / `db_response_app_password`,
  Postgres app-user passwords

CDK creates each secret with **generated placeholder values** for every
key. The real values are set out-of-band (AWS Console, CLI
`put-secret-value`, or a rotation Lambda later) — secret values never
appear in code, in a synthesized CloudFormation template, or in git. See
`scripts/seed-secrets.sh` for the seeding workflow.

## Route53 + SES (imported, not created)

`security_stack.py` also imports the already hand-configured Route53
hosted zone for `flow-form.com.au`
(`route53.HostedZone.from_lookup`) and grants the ECS task role
`ses:SendEmail` / `ses:SendRawEmail` scoped to that domain's SES identity
ARN. Unlike the KMS key/secret decision below, this is **not** a
create-vs-import choice — CDK never creates or modifies the hosted zone or
SES verification, only references them by domain name. The hosted zone ID
is published as an SSM parameter (`/flowform/<env>/hosted-zone-id`) for
later stacks (e.g. an ALB alias record in `application_stack.py`).

Note: `HostedZone.from_lookup` performs a real AWS API call at synth time
(cached in `cdk.context.json` after the first successful lookup), so
`cdk synth`/`cdk deploy` need valid AWS credentials for the target account.
Tests pre-seed a fake lookup result via CDK's context so `pytest` stays
hermetic — see `tests/test_security_stack.py`.

## Open decision: existing dev KMS key / secret

`infra/docker/.backend.env` already references a live KMS key and a
Secrets Manager secret for dev
(`FLOWFORM_ENCRYPTION_KMS_KEY_ARN`, `FLOWFORM_ENCRYPTION_LINKAGE_SECRET_ARN`).
`security_stack.py` currently creates a **new** key and secrets rather than
importing those. Before deploying this stack to the real `dev` account,
decide:

- **Import** the existing ARNs (`kms.Key.from_key_arn`,
  `secretsmanager.Secret.from_secret_complete_arn`) so CDK adopts what's
  already running, or
- **Create fresh** resources here and decommission/rotate off the old ones.

This is flagged with a `# TODO(decision)` comment at the top of
`security_stack.py`.

## Flagged follow-up: rotate what's currently on disk

`infra/docker/.backend.env` currently contains, in plaintext:

- A live AWS IAM access key + secret key
- The Auth0 Management API client secret
- The KMS key ARN and Secrets Manager secret ARN referenced above

This file is gitignored and has never been committed — nothing has leaked.
But long-lived plaintext IAM credentials on a developer's disk are exactly
what Secrets Manager + scoped IAM roles are meant to replace. Once
`security_stack.py` is deployed and the application stack's ECS task role
is live, plan to rotate the IAM access key and Auth0 management secret and
stop needing static AWS credentials in local `.env` files at all (the local
Docker backend can keep using them for now, since it isn't running as an
ECS task).
