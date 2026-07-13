# AWS Overview

FlowForm's AWS infrastructure is managed as code under
[`infra/platforms/aws/cdk/`](..), using AWS CDK (Python). Goal: if the AWS account
disappeared, `cdk deploy` rebuilds everything except database contents and
secret values.

## Stacks

| Stack | File | Status | Envs | Purpose |
|---|---|---|---|---|
| Security | `flowform_infra/stacks/security_stack.py` | Built | per scope: nonprod (dev+staging), prod | KMS key, Secrets Manager entries, SSM params, app IAM role — dev and staging share one `FlowForm-Nonprod-Security` stack (cost: no duplicate keys/secrets for simulation envs) |
| Network | `flowform_infra/stacks/network_stack.py` | Stub | staging/prod | VPC, subnets, security groups |
| Database | `flowform_infra/stacks/database_stack.py` | Stub | staging/prod | RDS PostgreSQL (core + response) |
| Application | `flowform_infra/stacks/application_stack.py` | Stub | staging/prod | EC2 + Docker Compose (Caddy + Gunicorn) running the Flask API |
| FrontendCert | `flowform_infra/stacks/frontend_cert_stack.py` | Built | staging/prod | ACM cert for CloudFront (us-east-1) |
| Frontend | `flowform_infra/stacks/frontend_stack.py` | Built | staging/prod | S3 + CloudFront hosting for `public-site` and `studio-app` |
| Observability | `flowform_infra/stacks/observability_stack.py` | Stub | staging/prod | CloudWatch log groups, alarms, dashboard |

Security is deployed first — every other stack reads from it (KMS key,
app role, secret ARNs). **dev deploys the Security stack only**: the app,
databases, and frontends run locally, so dev's AWS footprint is just the
resources the backend can't fake locally (KMS, secrets, SES send access).
See [`environments.md`](environments.md).

The overall shape — single public EC2 with Caddy instead of ALB/ECS, no
NAT Gateway, one small RDS instance — is a deliberate budget decision,
not a stopgap. [`cost-model.md`](cost-model.md) records the monthly
target, the isolation trade-off accepted, and the triggers for upgrading
past it.

## What's NOT in CDK

- **Local development** — Flask, React, Postgres, PgBouncer all run in
  Docker Compose (`infra/environments/development/compose/`), untouched by this. See
  the development environment README at `infra/environments/development/README.md`.
- **Sentry / PostHog** — external SaaS, not AWS resources.
- **Everything hand-done that CDK assumes exists** (domain/hosted zone,
  SES identity + sandbox exit, Auth0, secret seeding, bootstrap) — the
  full checklist with reasons lives in
  [`manual-prerequisites.md`](manual-prerequisites.md).

## public-site and studio-app on S3 + CloudFront

`frontend_stack.py` hosts each frontend as a `StaticSiteApp`
(`flowform_infra/constructs/static_site_construct.py`): a private S3
bucket (all public access blocked, reachable only through CloudFront's
Origin Access Control) behind a CloudFront distribution with SPA fallback
(origin 403/404 → `/index.html`). Route 53 aliases point each domain at
its distribution: staging gets `staging.flow-form.com.au` +
`studio.staging.flow-form.com.au`; prod is configured as the apex
(+`www`) + `studio.flow-form.com.au`. The ACM certificate lives in
`frontend_cert_stack.py`, pinned to us-east-1 (a CloudFront requirement)
and handed across via `cross_region_references`. These stacks only exist
for full deployments — dev's frontends run on local Vite dev servers.

This replaced an earlier Amplify Hosting approach; the earlier CDK-managed
Amplify apps were destroyed and the original hand-made Amplify app still
serves the prod apex until the cutover. Caveat for the first prod deploy:
remove that app's domain association first so the CDK Route 53 aliases
can claim the apex.

**Deploys** happen from GitHub Actions (`.github/workflows/deploy.yml`):
the job assumes `flowform-<env>-frontend-deploy` via OIDC (created by
`security_stack.py` — no AWS keys stored in GitHub), reads build config
(`VITE_*` values, distribution IDs) from `/flowform/<env>/frontend/*` SSM
parameters published by the frontend stack, builds both apps, then
`aws s3 sync` (assets before `index.html`) and a CloudFront invalidation.
The Auth0 values come from `EnvConfig.auth0_public`, loaded at synth time
from the gitignored `infra/platforms/aws/cdk/.env.<env>` file — the frontend stack fails
synth with a clear error if that file (or its `AUTH0_*` keys) is missing.
**`VITE_API_BASE_URL` points at the planned API hostname**
(`api.<public-site-domain>`) which doesn't resolve until
`application_stack.py`'s EC2 instance and Route 53 record exist.

## Regions and accounts

Everything targets `ap-southeast-2`, matching the KMS key and Secrets
Manager secret already referenced by the backend's dev config
(`infra/environments/development/compose/.backend.env`). See [`environments.md`](environments.md) for
per-environment account details.
