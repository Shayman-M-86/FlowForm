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
`infra/scripts/cdk/seed-secrets.sh` for the seeding workflow.

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

Dev cutover steps (one-time, after the first `cdk deploy -c env=dev`) —
**completed 2026-07-07**: secrets seeded, `.backend.env` repointed at the
CDK KMS key and linkage secret, dev data reseeded, legacy secret
force-deleted and legacy KMS key scheduled for deletion (2026-07-14).
Note the linkage secret is a **standalone versioned secret**
(`flowform/<env>/linkage-secret`), not a key inside `app-secrets` — the
backend rotates it by Secrets Manager version (AWSCURRENT = active), so
it must own its version history.

Prod's "never recreate" guarantee doesn't need an import path: it comes
from `RemovalPolicy.RETAIN` plus never renaming the KMS/secret construct
IDs in `security_stack.py` (a rename forces CloudFormation to replace the
resource).

## Flagged follow-up: rotate old local secrets

`infra/docker/.backend.env` no longer stores raw secret values for the
Auth0 Management API client. It still carries live resource identifiers
such as the KMS key ARN and Secrets Manager secret ARN referenced above.

The local Auth0 Management API client secret now follows the same Docker
secret-file convention as DB passwords and the Flask secret key:
`FLOWFORM_AUTH0_MGMT_SECRET_FILE` points at
`/run/secrets/FLOWFORM_AUTH0_MGMT_SECRET`.

## Dev secrets: fetched or generated, assembled in tmpfs

Dev secret values are split by ownership — Secrets Manager holds only
what must persist or cannot be generated; machine-local throwaways are
generated, never uploaded:

| Value | Source | Why |
|---|---|---|
| `app_secret_key`, `auth0_mgmt_secret` | `flowform/nonprod/app-secrets` (Secrets Manager) | must persist / external value |
| 4 local-Postgres passwords | `scripts/secrets/generate-secrets.sh` → gitignored `infra/docker/secrets/` | dev-only throwaways; must survive reboots alongside the Postgres volume they initialised |

`scripts/secrets/fetch-dev-secrets.sh` assembles both into one place:

```text
app-secrets (SM, via aws login)  ─┐
                                  ├→ $XDG_RUNTIME_DIR/flowform-secrets/  (tmpfs, 0600)
generated DB passwords (local)   ─┘      ↓ FLOWFORM_SECRET_DIR
                                    compose file-secrets → /run/secrets/* in containers
```

The script refuses to run if `XDG_RUNTIME_DIR` is unset or not tmpfs.
tmpfs empties on reboot — re-run the script. `flowform/nonprod/db-secrets`
deliberately holds empty placeholders: its real values only matter for
staging RDS.

**Security scopes:** dev and staging share the `nonprod` security scope —
one `FlowForm-Nonprod-Security` stack, one KMS key, one secret set
(`flowform/nonprod/...`), one app role. They are simulation environments;
duplicating paid resources between them bought nothing. Prod gets its own
isolated `prod` scope. See `SecurityScopeConfig` in
`flowform_infra/config/environments.py`. To rotate the local DB passwords, delete the
`*.dev.secret.txt` files, re-run the fetch script, and reset the DB
volumes (`docker compose down -v`) since Postgres was initialised with
the old values.

The env and secret files are gitignored and have never been committed —
nothing has leaked. After moving a secret out of `.backend.env`, rotate the
old local value when practical and keep using mounted secret files for local
Docker parity with EC2.

## EC2 Compose bootstrap contract

The split EC2 runtime keeps the same secret-file convention. The proxy
instance runs `infra/docker/docker-compose.proxy.yml` from a bootstrap-written
proxy env file; the private app instance runs
`infra/docker/docker-compose.app.yml` with
`--env-file /opt/flowform/backend.env`. That backend env file must contain
only non-secret config, image refs, private IPs, proxy settings, and logging
settings. Keep production logging on stdout JSON
(`FLOWFORM_LOGGING_LOG_JSON=true`) and leave `FLOWFORM_LOGGING_LOG_FILE`
unset so `read_only: true` remains honest.
