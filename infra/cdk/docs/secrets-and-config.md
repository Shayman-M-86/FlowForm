# Secrets and Config

## Three places config can live

| Location | What goes here | Managed by |
|---|---|---|
| Local `.env` / Docker secrets (`infra/docker/`) | Local dev only — never real prod credentials | Manual, gitignored |
| SSM Parameter Store | Non-secret config (KMS key ARN, region) | `security_stack.py` |
| Secrets Manager | Actual secret values (passwords, client secrets) | `security_stack.py` (shape only — see below) |

## What `security_stack.py` creates

Secrets Manager entries, named `flowform/<env>/<name>`:

- `linkage-secret` — HMAC secret deriving opaque locators between the core
  and response databases
- `app-secret-key` — Flask `FLOWFORM_APP_SECRET_KEY`
- `auth0-client-secret` — Auth0 application client secret
- `auth0-mgmt-secret` — Auth0 Management API client secret
- `db-core-app-password` / `db-response-app-password` — Postgres app-user
  passwords

CDK creates each secret with a **generated placeholder value**. The real
value is set out-of-band (AWS Console, CLI `put-secret-value`, or a
rotation Lambda later) — secret values never appear in code, in a
synthesized CloudFormation template, or in git.

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
