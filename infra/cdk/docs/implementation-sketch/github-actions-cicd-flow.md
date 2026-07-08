# GitHub Actions CI/CD Flow Sketch

This note expands the CI/CD portion of the
[FlowForm Deployment Implementation Plan](core-sketch-plan.md). It describes
the intended GitHub Actions shape after the Amplify-to-CDK deployment migration:
one pull-request gate and one environment deploy flow, both using short-lived AWS
credentials from GitHub OIDC rather than stored AWS keys.

Current repo state: `.github/workflows/ci.yml` already runs on `main` and
`staging`, and currently covers backend security checks, Dockerized backend
tests, and a public-site build. This sketch describes the target expanded flow.

## Workflow Files

Use two primary workflows:

| Workflow | Trigger | Purpose | AWS credentials |
|---|---|---|---|
| `.github/workflows/ci.yml` | pull requests and pushes to `main` / `staging` | Validate code, build artifacts, run tests, preview CDK | None by default; optional read-only/preview OIDC role for CDK lookup/diff |
| `.github/workflows/deploy.yml` | push to `staging`, push to `main`, manual dispatch | Deploy staging/prod infrastructure and application artifacts | Required OIDC assume-role |

Production deploys should run through the GitHub `production` environment with a
required reviewer gate. Staging can auto-deploy from the `staging` branch. Keep
the environment-to-branch mapping separate from CDK's environment names:
`staging -> staging`, `prod -> main`.

## AWS Credential Model

Do not store AWS access keys in GitHub secrets.

The intended chain is:

```text
GitHub Actions job
  |
  | requests OIDC token
  v
GitHub OIDC provider in AWS IAM
  |
  | sts:AssumeRoleWithWebIdentity
  v
Per-environment IAM role
  |
  v
CDK / ECR / S3 / CloudFront / SSM actions
```

Each workflow job that needs AWS access should use:

```yaml
permissions:
  contents: read
  id-token: write
```

Then configure credentials with the environment-specific role:

```yaml
- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::<account-id>:role/<flowform-env-deploy-role>
    aws-region: ap-southeast-2
```

Role trust policies should be pinned to this repository and to the expected
branch or GitHub environment. The main deployment plan's
[Phase 1e](core-sketch-plan.md#phase-1--cdk-restructure-infra-only-nothing-deployed-to-prod-yet)
splits this into infra, frontend, and backend deploy roles. That separation is
still the cleanest target:

- Infra deploy role: CDK deploy permissions for the FlowForm stacks.
- Backend deploy role: ECR push, SSM SendCommand to the app instance, read
  deployment parameters.
- Frontend deploy role: S3 sync and CloudFront invalidation for the specific
  app buckets/distributions.

For a first version, one per-environment deploy role is acceptable if its policy
is still scoped to FlowForm resources and split later before production hardening.

## Pull Request Gate

The PR workflow should prove that a change can be safely merged. It should not
deploy infrastructure or mutate shared AWS state.

Recommended job graph:

```text
security
  |
  +--> backend-tests
  |
  +--> frontend-checks
  |
  +--> infra-preview
```

### 1. Security

Existing shape:

- Check out the repo.
- Run `./backend/scripts/run_backend_security.sh`.

Keep this job early and cheap. Other jobs should depend on it unless there is a
good reason to run them in parallel.

### 2. Backend Tests

Existing shape:

- Set up Docker Buildx.
- Generate temporary test secret files from the GitHub `test` environment.
- Render Docker Compose config.
- Start `infra/docker/docker-compose.test.yml`.
- Run `uv run pytest tests --cov=app`.
- Upload coverage and debug artifacts.
- Always tear down Compose with `docker compose down -v --remove-orphans`.

Target additions:

- Keep failure logs as artifacts.
- Make the test command one repo script once the command stabilizes.
- Keep test secrets scoped to the `test` GitHub environment only.

### 3. Frontend Checks

Current CI builds the public site. The target PR gate should cover both frontend
apps and shared packages:

- Set up `pnpm` and Node using the versions from `frontend/package.json`.
- Run `pnpm install --frozen-lockfile`.
- Generate OpenAPI/client types if the PR gate expects generated files to be
  fresh.
- Run typecheck/lint/test commands once package scripts exist.
- Build the public site with `pnpm run build:site`.
- Build Studio with `pnpm run build:studio`.
- Upload build artifacts only when useful for debugging; deploy should rebuild
  from the checked-out commit rather than trusting a PR artifact.

### 4. Infra Preview

For PRs, the safest baseline is:

- Run `uv sync` in `infra/cdk`.
- Run `uv run pytest` for CDK assertions.
- Run `npx cdk synth -c env=dev`.

For staging/prod previews, the docs currently note that `HostedZone.from_lookup`
can require AWS credentials at synth time unless `cdk.context.json` already has
the lookup cached. If PRs should run `cdk synth -c env=staging` or `cdk diff`,
use a read-only preview role through OIDC. Do not use the deploy role for PRs
from forks.

Optional PR nicety:

- Run `npx cdk diff -c env=staging`.
- Post the diff as a PR comment.
- Never call `cdk deploy` from a pull request.

## Deploy Flow

The deploy workflow should be a visible job chain. Each stage should be
idempotent and should either complete cleanly or leave enough state for the next
run to continue.

Recommended high-level order:

```text
resolve-env
  -> ci-gate
  -> infra-deploy
  -> backend-image
  -> backend-migrations
  -> backend-rollout
  -> frontend-builds
  -> frontend-publish
  -> smoke-checks
  -> record-release
```

### 1. Resolve Environment

Determine deployment target from the ref:

| Ref | CDK env | GitHub environment | Approval |
|---|---|---|---|
| `refs/heads/staging` | `staging` | `staging` | automatic |
| `refs/heads/main` | `prod` | `production` | required reviewer |
| manual dispatch | selected input | selected environment | based on target |

Export environment-specific values for later jobs:

- AWS account ID.
- AWS region, currently `ap-southeast-2` for the main stacks.
- CDK env name.
- ECR repository names.
- Backend image tag, usually the Git SHA.
- Frontend bucket names and CloudFront distribution IDs, preferably read from
  CDK stack outputs or SSM parameters.

### 2. CI Gate

Require the same checks as the PR gate before deployment:

- Backend security.
- Backend tests.
- Frontend builds/checks.
- CDK synth/assertions.

This can be a workflow dependency, a reusable workflow call, or branch
protection that requires the latest `ci.yml` run to be green.

### 3. Infrastructure Deploy

Assume the infra deploy role through OIDC.

Steps:

- `cd infra/cdk`
- `uv sync`
- `npx cdk synth -c env=<env>`
- `npx cdk diff -c env=<env>`
- `npx cdk deploy -c env=<env> --require-approval never`
- Capture stack outputs needed by later jobs.

CDK deploy should happen before app publish so buckets, distributions, ECR
repositories, RDS, the EC2 instance, instance role, SSM access, and Route 53
records exist before artifacts try to use them.

### 4. Backend Image

Assume the backend deploy role through OIDC.

Steps:

- Log in to ECR.
- Build the backend Docker image from `infra/docker/backend.Dockerfile`.
- Tag it with the Git SHA and optionally a mutable environment tag such as
  `staging-latest`.
- Push the immutable Git SHA tag to ECR.
- Push the custom Caddy image too, if it changed or is versioned with the same
  release.

The immutable image tag is the rollback handle. The EC2 host should deploy a
specific tag, not an untracked local image.

### 5. Backend Migrations

Run migrations before replacing the running app container.

Preferred mechanism:

- Use SSM SendCommand against the app EC2 instance.
- Pull the newly pushed backend image.
- Run a one-shot migration command against RDS for both databases.
- Stop the deployment if migrations fail.

Important boundary: migrations should be designed as forward-compatible where
possible. If a migration is not reversible, the workflow should say so clearly
and require manual production approval before that step.

### 6. Backend Rollout

Use SSM SendCommand or an SSM document rather than SSH.

Steps on the EC2 instance:

- Write/update the runtime `.env` file from Secrets Manager/SSM values.
- Update the Compose image tag to the new backend image.
- Run `docker compose pull`.
- Run `docker compose up -d`.
- Check container health and Caddy proxy health.
- Keep the previous image tag recorded locally and/or in SSM.

Rollback handle:

- Re-run the same SSM document with the previous backend image tag.
- `docker compose up -d` should restore the previous app container.
- Database rollback is separate and may be impossible for some migrations, so
  schema changes should be planned with expand/contract discipline.

### 7. Frontend Builds

Assume whichever role can read deployment config. This may be the frontend role
or a config-read role.

Steps:

- Set up `pnpm` and Node.
- `pnpm install --frozen-lockfile`.
- Fetch per-env frontend config from SSM parameters or GitHub environment
  variables. Prefer SSM if CDK owns the parameter names.
- Build public site with the target API/Auth0 config.
- Build Studio with the target API/Auth0 config.
- Verify each `dist/index.html` exists and is non-empty.

Each frontend should be built from the same Git SHA as the backend image.

### 8. Frontend Publish

Assume the frontend deploy role through OIDC.

For each app:

- Upload hashed/static assets first with long cache headers.
- Upload `index.html` last with no-cache or short-cache headers.
- Use `aws s3 sync --delete` only after the destination bucket is confirmed.
- Invalidate CloudFront for `/index.html` first; use `/*` initially if
  simplicity matters more than cost.
- Smoke check the CloudFront URL after invalidation starts.

Rollback handle:

- Keep a small release manifest that records the previous S3 object version set
  or previous artifact bundle.
- If S3 versioning is enabled, rollback can restore the prior `index.html` and
  referenced chunks.
- Without S3 versioning, the deploy workflow should keep the previous build
  artifact somewhere durable before `--delete`.

### 9. Smoke Checks

Run these after backend and frontend publish:

- API health endpoint through Caddy over HTTPS.
- Backend cannot be reached directly on the Flask/Gunicorn port.
- Public site loads through CloudFront.
- Studio loads through CloudFront.
- Auth0 callback/logout URLs match the deployed domains.
- A minimal public submission flow succeeds in staging.
- CloudWatch/SSM command status is clean.

For production, keep smoke checks quick and high-signal. Deeper end-to-end
tests can run against staging before the production approval gate.

### 10. Record Release

Write a release manifest as an artifact and optionally to SSM:

- Git SHA.
- CDK env.
- CDK stack output snapshot.
- Backend image tag.
- Caddy image tag.
- Frontend build artifact IDs or S3 version IDs.
- CloudFront distribution IDs.
- Previous backend/frontend versions used for rollback.

This makes the deployment reversible in practice rather than only in theory.

## Failure and Rollback Rules

Use these rules to keep failed deploys recoverable:

- Before CDK deploy: no environment mutation has happened; stop safely.
- During CDK deploy: let CloudFormation roll back failed stack updates. Do not
  continue to app deploy if infrastructure fails.
- During backend image build/push: no runtime mutation has happened; stop safely.
- During migrations: stop before app rollout if migrations fail.
- During backend rollout: roll back Compose to the previous backend image tag if
  health checks fail.
- During frontend publish: restore previous frontend artifact or S3 object
  versions if smoke checks fail.
- During smoke checks: decide by failure type. Backend health failures should
  roll back backend first; frontend loading failures should roll back frontend
  artifacts; Auth0/CORS failures may be config-only and should not trigger CDK
  destroy.

Avoid automatic `cdk destroy` as a rollback strategy. Roll back to the previous
known-good app artifacts first. Use `cdk destroy` only for deliberate teardown of
throwaway environments.

## Teardown Flow

For staging, a separate manual workflow can destroy the environment when needed:

```text
confirm target == staging
  -> disable deploy concurrency for staging
  -> empty frontend buckets if required
  -> cdk destroy in reverse dependency order
  -> verify retained/manual resources
```

Do not offer automatic production teardown. Production resources use retention
and deletion protection for a reason.

## Open Implementation Decisions

- Whether PR `cdk diff` uses a read-only OIDC role or only runs hermetic CDK
  tests/synth.
- Whether stack outputs are passed through GitHub artifacts, SSM parameters, or
  `aws cloudformation describe-stacks`.
- Whether the first deploy role is split immediately into infra/backend/frontend
  roles or starts as one scoped per-env role.
- Whether S3 versioning is mandatory before first frontend deploy.
- Exact migration command for both FlowForm databases.
- Exact smoke-check endpoints and whether staging gets a full browser E2E test.
