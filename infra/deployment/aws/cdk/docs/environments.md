# Environments

Defined in [`infra/deployment/aws/cdk/flowform_infra/config/environments.py`](../flowform_infra/config/environments.py).

| Env | Account | Deployment | Removal policy | Deletion protection | DB instance |
|---|---|---|---|---|---|
| `dev` | `908123139858` | Security stack only | Destroy | Off | *n/a (local Postgres)* |
| `staging` | `908123139858` | Proxmox runtime and AWS frontends | Per stack | Off | Proxmox PostgreSQL |
| `prod` | `908123139858` | Full AWS deployment | Retain | On | `db.t4g.small` |

All environments share one AWS account — the one already visible in the KMS
key / Secrets Manager ARNs the backend uses locally
(`infra/env/dev/.backend.env`).

## Deployment shapes

**dev is local-first.** The Flask API, both Postgres databases, and the
frontends all run locally (Docker Compose in
`infra/containers/runtime/development/compose/`, Vite dev servers). The only
AWS resources dev needs are the ones the backend can't
fake locally — the KMS key, the Secrets Manager entries, and SES send
permission — so `-c env=dev` synthesizes the Security stack and nothing
else (`full_deployment=False` in `environments.py`). No VPC, RDS, ECS,
ALB, or Amplify apps exist for dev.

**staging is the shared integration environment.** The proxy, app and
PostgreSQL run on Proxmox. S3 and CloudFront host both frontends at
`staging.flow-form.com.au` and `studio.staging.flow-form.com.au`.
AWS also supplies ECR, Parameter Store, Roles Anywhere, and the shared
security services. See the [hybrid runbook](../../../hybrid/README.md).

**prod uses the AWS runtime**, with `RemovalPolicy.RETAIN` on the KMS
key and secrets and with RDS deletion protection.

The frontend stack fails synth with a clear error for any full-deployment
env whose `auth0_public` config is still `None`. Those values load at
synth time from the gitignored `infra/deployment/aws/cdk/.env.<env>` file
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
cd infra/deployment/aws/cdk
npx cdk synth -c env=dev       # or staging / prod
npx cdk deploy -c env=dev
```

Defaults to `dev` if `-c env=` is omitted (see `cdk.json` context and
`app.py`).

## Removal policy behavior

- `dev` and `staging` share the nonprod Security stack. Staging's
  `HybridRuntime` stack retains the Parameter Store entries on deletion.
- `prod`: KMS keys and secrets are retained even if the stack is destroyed;
  RDS has deletion protection enabled. This is intentional — production
  data and encryption keys should never be removable by a single
  `cdk destroy` command.
