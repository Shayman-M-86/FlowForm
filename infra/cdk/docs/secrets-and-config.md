# Secrets and Config

## Three places config can live

| Location | What goes here | Managed by |
|---|---|---|
| Local `.env` / Docker secrets (`infra/docker/`) | Local dev only — never real prod credentials | Manual, gitignored |
| `infra/cdk/.env.<env>` | Per-env Auth0 public config (read at synth) + secret values staged for `seed-secrets.sh` | Manual, gitignored (`.env.dev.example` is the template) |
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
(`route53.HostedZone.from_lookup`) and grants the app IAM role
`ses:SendEmail` / `ses:SendRawEmail` scoped to that domain's SES identity
ARN. (The app role is assumed by ECS tasks in staging/prod; in dev it's
assumable by principals in the dev account, so the locally hosted backend
can `sts:AssumeRole` into the same scoped access.) Unlike the KMS key/secret decision below, this is **not** a
create-vs-import choice — CDK never creates or modifies the hosted zone or
SES verification, only references them by domain name. The hosted zone ID
is published as an SSM parameter (`/flowform/<env>/hosted-zone-id`) for
later stacks (e.g. an ALB alias record in `application_stack.py`).

Note: `HostedZone.from_lookup` performs a real AWS API call at synth time
(cached in `cdk.context.json` after the first successful lookup), so
`cdk synth`/`cdk deploy` need valid AWS credentials for the target account.
Tests pre-seed a fake lookup result via CDK's context so `pytest` stays
hermetic — see `tests/test_security_stack.py`.

## Resolved: existing dev KMS key / secret → create fresh

`infra/docker/.backend.env` references a hand-created KMS key and Secrets
Manager secret for dev (`FLOWFORM_ENCRYPTION_KMS_KEY_ARN`,
`FLOWFORM_ENCRYPTION_LINKAGE_SECRET_ARN`). Decision: `security_stack.py`
always **creates fresh** resources — there is no import-by-ARN path, so a
brand-new AWS account bootstraps with zero special cases.

Dev cutover steps (one-time, after the first `cdk deploy -c env=dev`):

1. Seed the new secrets (`scripts/seed-secrets.sh --env dev --send`).
2. Update `.backend.env`'s `FLOWFORM_ENCRYPTION_*` ARNs to the new
   resources.
3. **Reseed local dev data** — existing rows' opaque locators were derived
   from the old linkage HMAC secret, so cross-DB lookups on them break.
   Dev data is disposable; this is expected.
4. Delete the old hand-created key and secret.

Prod's "never recreate" guarantee doesn't need an import path: it comes
from `RemovalPolicy.RETAIN` plus never renaming the KMS/secret construct
IDs in `security_stack.py` (a rename forces CloudFormation to replace the
resource).

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
