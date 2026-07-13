# Environments

Defined in [`infra/cdk/flowform_infra/config/environments.py`](../flowform_infra/config/environments.py).

| Env | Account | Deployment | Removal policy | Deletion protection | DB instance |
|---|---|---|---|---|---|
| `dev` | `908123139858` | Security stack only | Destroy | Off | *n/a (local Postgres)* |
| `staging` | `908123139858` | Full | Destroy | Off | `db.t4g.small` |
| `prod` | `908123139858` | Full | Retain | On | `db.t4g.medium` |

All environments share one AWS account — the one already visible in the KMS
key / Secrets Manager ARNs the backend uses locally
(`infra/docker/.backend.env`).

## Deployment shapes

**dev is local-first.** The Flask API, both Postgres databases, and the
frontends all run locally (Docker Compose in `infra/docker/`, Vite dev
servers). The only AWS resources dev needs are the ones the backend can't
fake locally — the KMS key, the Secrets Manager entries, and SES send
permission — so `-c env=dev` synthesizes the Security stack and nothing
else (`full_deployment=False` in `environments.py`). No VPC, RDS, ECS,
ALB, or Amplify apps exist for dev.

**staging is the shared integration environment.** It's the single
non-prod cloud deployment: full stack set including Amplify hosting for
both frontends, served at `staging.flow-form.com.au` (public site) and
`studio.staging.flow-form.com.au` (studio) — DNS records are created
automatically by Amplify's domain association. Anything that would otherwise justify a "deployed dev"
(branch previews, integration testing against real ECS/RDS) happens in
staging rather than in a second paid-for environment.

**prod matches staging's shape**, with `RemovalPolicy.RETAIN` on the KMS
key/secrets and RDS deletion protection.

The Amplify stack fails synth with a clear error for any full-deployment
env whose `auth0_public` config is still `None`. Those values load at
synth time from the gitignored `infra/cdk/.env.<env>` file
(`AUTH0_DOMAIN`, `AUTH0_CLIENT_ID`, `AUTH0_AUDIENCE` — see
`.env.dev.example`), the same per-env file `seed-secrets.sh` reads its
secret values from.

**Decision (resolved): single account for all environments.** Isolation
comes from per-env resource naming (`flowform/<env>/...` secrets and
params, per-env stacks and KMS keys), not account boundaries. AWS
Organizations + a separate prod member account is the standard
blast-radius answer, but for a solo developer it was judged more
operational overhead than it's worth right now. Revisit when the project
grows — member accounts can be added to an Organization later without
disturbing existing resources, though note a new prod account would need
its own SES domain verification + production-access request and a plan
for the (single-account) Route 53 hosted zone.

## Selecting an environment

```bash
cd infra/cdk
npx cdk synth -c env=dev       # or staging / prod
npx cdk deploy -c env=dev
```

Defaults to `dev` if `-c env=` is omitted (see `cdk.json` context and
`app.py`).

## Removal policy behavior

- `dev` / `staging`: KMS keys, secrets, and (once built) RDS instances are
  destroyed on `cdk destroy` — fine for throwaway environments.
- `prod`: KMS keys and secrets are retained even if the stack is destroyed;
  RDS has deletion protection enabled. This is intentional — production
  data and encryption keys should never be removable by a single
  `cdk destroy` command.
