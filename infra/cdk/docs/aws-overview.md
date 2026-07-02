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
| Amplify | `flowform_infra/stacks/amplify_stack.py` | Stub | Amplify Hosting app for `public-site` |
| Observability | `flowform_infra/stacks/observability_stack.py` | Stub | CloudWatch log groups, alarms, dashboard |

Security is deployed first — every other stack reads from it (KMS key,
task role, secret ARNs).

## What's NOT in CDK

- **Local development** — Flask, React, Postgres, PgBouncer all run in
  Docker Compose (`infra/docker/`), untouched by this. See
  [`infra/docker_secrets_env_setup_flow_form.md`](../../docker_secrets_env_setup_flow_form.md).
- **`studio-app`** — no deploy target confirmed yet at time of writing.
- **Sentry / PostHog** — external SaaS, not AWS resources.

## public-site and Amplify

`public-site` already deploys through AWS Amplify Hosting, configured via
the root-level `amplify.yml` (build spec) and `customHttp.yml` (cache
headers). The `amplify_stack.py` stub is meant to bring that *existing*
deployment under CDK management — not to replace it with something else
(e.g. S3 + CloudFront).

## Regions and accounts

Everything targets `ap-southeast-2`, matching the KMS key and Secrets
Manager secret already referenced by the backend's dev config
(`infra/docker/.backend.env`). See [`environments.md`](environments.md) for
per-environment account details.
