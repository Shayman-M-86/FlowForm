# AWS Overview

FlowForm's AWS infrastructure is managed as code under
[`infra/cdk/`](..), using AWS CDK (Python). Goal: if the AWS account
disappeared, `cdk deploy` rebuilds everything except database contents and
secret values.

## Stacks

| Stack | File | Status | Envs | Purpose |
|---|---|---|---|---|
| Security | `flowform_infra/stacks/security_stack.py` | Built | all | KMS key, Secrets Manager entries, SSM params, app IAM role |
| Network | `flowform_infra/stacks/network_stack.py` | Stub | staging/prod | VPC, subnets, security groups |
| Database | `flowform_infra/stacks/database_stack.py` | Stub | staging/prod | RDS PostgreSQL (core + response) |
| Application | `flowform_infra/stacks/application_stack.py` | Stub | staging/prod | ECS/Fargate + ALB running the Flask API |
| Amplify | `flowform_infra/stacks/amplify_stack.py` | Built | staging/prod | Amplify Hosting apps for `public-site` and `studio-app` |
| Observability | `flowform_infra/stacks/observability_stack.py` | Stub | staging/prod | CloudWatch log groups, alarms, dashboard |

Security is deployed first — every other stack reads from it (KMS key,
app role, secret ARNs). **dev deploys the Security stack only**: the app,
databases, and frontends run locally, so dev's AWS footprint is just the
resources the backend can't fake locally (KMS, secrets, SES send access).
See [`environments.md`](environments.md).

## What's NOT in CDK

- **Local development** — Flask, React, Postgres, PgBouncer all run in
  Docker Compose (`infra/docker/`), untouched by this. See
  [`infra/docker_secrets_env_setup_flow_form.md`](../../docker_secrets_env_setup_flow_form.md).
- **Sentry / PostHog** — external SaaS, not AWS resources.
- **The GitHub repo connection for both Amplify apps** — see below.
- **Everything hand-done that CDK assumes exists** (domain/hosted zone,
  SES identity + sandbox exit, Auth0, secret seeding, bootstrap) — the
  full checklist with reasons lives in
  [`manual-prerequisites.md`](manual-prerequisites.md).

## public-site and studio-app on Amplify

`amplify_stack.py` creates two separate, fully CDK-managed Amplify Hosting
apps — one per frontend (`flowform_infra/constructs/amplify_app_construct.py`
holds the shared `AppAmplifyApp` construct they're both built from). The
stack only exists for full deployments (staging/prod) — dev's frontends run
on local Vite dev servers, so dev has no Amplify apps.

- **public-site** — build spec and cache headers carried over from the
  former root-level `amplify.yml`/`customHttp.yml`. Those files were
  **deleted from the repo**: Amplify gives committed build-config files
  precedence over App-resource settings, which silently shadowed every
  CDK-deployed build-settings change. Don't reintroduce them.
- **studio-app** — same pnpm/Node toolchain, `pnpm run build:studio`. Needs
  four `VITE_*` build-time env vars (Auth0 domain/client ID/audience, API
  base URL) set as plain `environment_variables` on the app, since they're
  non-secret client-side config, not something Secrets Manager/SSM needs to
  own. The Auth0 values come from `EnvConfig.auth0_public`, loaded at synth
  time from the gitignored `infra/cdk/.env.<env>` file — the stack fails
  synth with a clear error if that file (or its `AUTH0_*` keys) is
  missing. **`VITE_API_BASE_URL` is still a
  placeholder** (empty string) until `application_stack.py`'s ALB exists
  and has a stable URL.

**Custom domains** are CDK-managed via Amplify domain associations
(`EnvConfig.public_site_domain` / `studio_domain`): staging gets
`staging.flow-form.com.au` + `studio.staging.flow-form.com.au`; prod is
configured as the apex (+`www`) + `studio.flow-form.com.au`. The hosted
zone is in Route 53 in the same account, so Amplify creates the DNS and
ACM-validation records itself — no manual DNS step. Caveat: a hostname
can only be attached to one Amplify app at a time, and the apex currently
belongs to the hand-made public-site app — the first prod deploy requires
detaching it there first (the cutover).

The GitHub repo connection (`Shayman-M-86/FlowForm`, branch `main`) is
CDK-managed too, using the GitHub App flow: a PAT stored in Secrets
Manager (`flowform/shared/github-pat`) is supplied at app creation via
the CFN `AccessToken` property, after which webhooks run through the
already-installed Amplify GitHub App rather than the token. The secret
must exist before the first deploy — see
[`manual-prerequisites.md`](manual-prerequisites.md).

## Regions and accounts

Everything targets `ap-southeast-2`, matching the KMS key and Secrets
Manager secret already referenced by the backend's dev config
(`infra/docker/.backend.env`). See [`environments.md`](environments.md) for
per-environment account details.
