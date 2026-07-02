# AWS Overview

FlowForm's AWS infrastructure is managed as code under
[`infra/cdk/`](..), using AWS CDK (Python). Goal: if the AWS account
disappeared, `cdk deploy` rebuilds everything except database contents and
secret values.

## Stacks

| Stack | File | Status | Purpose |
|---|---|---|---|
| Security | `flowform_infra/stacks/security_stack.py` | Built | KMS key, Secrets Manager entries, SSM params, ECS task role |
| Network | `flowform_infra/stacks/network_stack.py` | Stub | VPC, subnets, security groups |
| Database | `flowform_infra/stacks/database_stack.py` | Stub | RDS PostgreSQL (core + response) |
| Application | `flowform_infra/stacks/application_stack.py` | Stub | ECS/Fargate + ALB running the Flask API |
| Amplify | `flowform_infra/stacks/amplify_stack.py` | Built | Amplify Hosting apps for `public-site` and `studio-app` |
| Observability | `flowform_infra/stacks/observability_stack.py` | Stub | CloudWatch log groups, alarms, dashboard |

Security is deployed first — every other stack reads from it (KMS key,
task role, secret ARNs).

## What's NOT in CDK

- **Local development** — Flask, React, Postgres, PgBouncer all run in
  Docker Compose (`infra/docker/`), untouched by this. See
  [`infra/docker_secrets_env_setup_flow_form.md`](../../docker_secrets_env_setup_flow_form.md).
- **Sentry / PostHog** — external SaaS, not AWS resources.
- **The GitHub repo connection for both Amplify apps** — see below.

## public-site and studio-app on Amplify

`amplify_stack.py` creates two separate, fully CDK-managed Amplify Hosting
apps — one per frontend (`flowform_infra/constructs/amplify_app_construct.py`
holds the shared `AppAmplifyApp` construct they're both built from):

- **public-site** — build spec mirrors the root-level `amplify.yml`
  (now superseded by this stack) and `customHttp.yml`'s cache headers.
- **studio-app** — same pnpm/Node toolchain, `pnpm run build:studio`. Needs
  four `VITE_*` build-time env vars (Auth0 domain/client ID/audience, API
  base URL) set as plain `environment_variables` on the app, since they're
  non-secret client-side config, not something Secrets Manager/SSM needs to
  own. **`VITE_API_BASE_URL` is still a placeholder** (empty string) until
  `application_stack.py`'s ALB exists and has a stable dev URL — fill it in
  before the first real dev deploy.

Each app is created with no `source_code_provider`, so it exists in AWS but
isn't wired to a Git repo yet. There's no GitHub OAuth/PAT token anywhere in
this repo — the existing public-site Amplify app was connected via the
newer console-authorized GitHub App integration, which the CDK L2 construct
can't drive. **After `cdk deploy`, connect each app's repository by hand**
once: Amplify console → the app → App settings → connect the `flow-form`
GitHub repo → branch `main`.

## Regions and accounts

Everything targets `ap-southeast-2`, matching the KMS key and Secrets
Manager secret already referenced by the backend's dev config
(`infra/docker/.backend.env`). See [`environments.md`](environments.md) for
per-environment account details.
