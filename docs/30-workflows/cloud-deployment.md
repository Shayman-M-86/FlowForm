---
title: Cloud deployment
aliases:
  - "Cloud deployment"
document_type: workflow
status: draft
authority: canonical
verified_against_commit: ad26b87e9820
tags: [infrastructure, ci-cd]
related_code:
  - "../../.github/workflows/deploy.yml"
  - "../../.github/workflows/ci.yml"
  - "../../infra/deployment/aws/cdk/flowform_infra/stacks/frontend_stack.py"
  - "../../infra/deployment/aws/cdk/flowform_infra/config/environments.py"
related_docs:
  - "Deployment model"
  - "Continuous integration"
  - "Machine image building"
  - "Infrastructure implementation"
---

# Cloud deployment

Describes the cloud release path that is implemented at this baseline: building
and publishing the two static frontends to the staging S3 and CloudFront
resources. It is not a full application deployment. CDK deployment, backend
image publication, host bootstrap, database provisioning or migration, and
production release are not wired into this workflow.

## Trigger

- A completed `CI` workflow on `staging` triggers `.github/workflows/deploy.yml`.
  The deploy job runs only when that CI run concluded successfully and checks
  out the exact `workflow_run.head_sha` that CI tested.
- `workflow_dispatch` starts the same staging job for the selected ref. This
  manual path does not require a successful CI run; the environment, role, and
  bucket names remain hard-coded to staging.

## Preconditions

- The staging frontend CDK resources must already exist: the two private S3
  buckets, CloudFront distributions, Route 53 aliases, frontend SSM parameters,
  and `flowform-staging-frontend-deploy` role. The workflow does not create or
  update them.
- GitHub OIDC must be trusted by that role, and the role must retain the S3,
  CloudFront, and `/flowform/staging/frontend/*` SSM permissions granted by the
  security and frontend stacks.
- The SSM path must contain Auth0 domain, client ID, audience, API base URL, and
  both distribution IDs. These are browser-visible build settings, not
  application secrets.
- The selected commit must have a consistent `frontend/pnpm-lock.yaml`; the job
  installs pnpm `10.24.0` and uses a frozen lockfile.

## Ordered steps

1. Check out the CI-tested SHA for an automatic run, or the selected ref for a
   manual run.
2. Install Node `22.12.0`, pnpm `10.24.0`, and frontend dependencies.
3. Exchange the GitHub OIDC token for the staging frontend-deploy role in
   `ap-southeast-2`.
4. Read frontend build configuration and distribution IDs from SSM into the
   job environment.
5. Run `pnpm run build:site` and `pnpm run build:studio` from `frontend/`.
6. For each application, sync content-hashed assets to its S3 bucket with
   `--delete` while excluding `index.html`, upload `index.html` last, then
   invalidate `/*` on the matching CloudFront distribution.

## Inputs and outputs

The input is one repository commit plus the six SSM values read by the job.
Build output is produced under `frontend/apps/public-site/dist/` and
`frontend/apps/studio-app/dist/` on the runner. The durable side effects are
replacement of the staging bucket contents and creation of two CloudFront
invalidations. No build artifact is committed and no backend or infrastructure
resource is changed.

## Failure behaviour

The job stops on dependency, OIDC, SSM, build, S3, or CloudFront command
failure. Publication is not transactional: one site or some assets may already
be updated when a later command fails, and there is no checked-in automatic
rollback. Re-run the same known-good commit to restore its frontend build.

`--delete` intentionally removes bucket objects absent from the selected build.
Review manual-dispatch refs carefully because that path bypasses CI. The SSM API
base URL is currently derived from a planned API hostname, while the CDK
application/database/bootstrap path remains incomplete; a green frontend
deployment therefore does not prove a usable end-to-end staging application.

## Verification commands

Confirm the Actions run deployed the intended checkout SHA, then verify both
objects and public distributions:

```bash
aws s3api head-object --bucket flowform-staging-public-site --key index.html
aws s3api head-object --bucket flowform-staging-studio-app --key index.html
curl -fsSI https://staging.flow-form.com.au/
curl -fsSI https://studio.staging.flow-form.com.au/
```

These checks prove that the frontend objects are present and reachable. They do
not verify backend health, database state, or which source commit produced an
object; retain the GitHub Actions run as the release record.

## Related documents

- [[deployment-model|Deployment model]]
- [[continuous-integration|Continuous integration]]
- [[machine-image-building|Machine image building]]
- [[infrastructure|Infrastructure implementation]]
