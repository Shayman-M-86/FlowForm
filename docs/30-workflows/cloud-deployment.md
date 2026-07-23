---
title: Cloud deployment
aliases:
  - "Cloud deployment"
document_type: workflow
status: draft
authority: canonical
verified_against_commit: null
tags: [infrastructure, ci-cd]
related_code:
  - "../../.github/workflows/deploy.yml"
  - "../../.github/workflows/publish-staging-images.yml"
  - "../../.github/workflows/ci.yml"
  - "../../infra/containers/strategies/aws/image-sources.json"
  - "../../infra/deployment/aws/scripts/publish-staging-images.sh"
  - "../../infra/deployment/aws/cdk/flowform_infra/stacks/frontend_stack.py"
  - "../../infra/deployment/aws/cdk/flowform_infra/stacks/application_stack.py"
  - "../../infra/deployment/aws/cdk/flowform_infra/stacks/registry_stack.py"
  - "../../infra/deployment/aws/cdk/flowform_infra/stacks/security_stack.py"
  - "../../infra/deployment/aws/cdk/flowform_infra/config/environments.py"
  - "../../infra/deployment/bootstrap/"
related_docs:
  - "Deployment model"
  - "Continuous integration"
  - "Machine image building"
  - "Infrastructure implementation"
---

# Cloud deployment

Describes the two bounded cloud publication paths implemented at this baseline:
publishing the static frontends to staging S3 and CloudFront, and manually
publishing the four staging runtime images to ECR. Neither path is a full
application deployment. CDK deployment, runtime image promotion, host
bootstrap/rollout, database provisioning or migration, and production release
are not wired into either workflow.

The CDK now declares private Backend, Caddy, Squid, and Alloy repositories plus
a branch-restricted image-publisher role with exact push permissions. The
application stack also declares exact app-host and proxy-host pull policies.
The manual image workflow assumes that publisher role, builds or mirrors exactly
the checked-in linux/amd64 sources, and retains a four-image digest manifest as
a workflow artifact. It deliberately cannot select the active runtime
parameters or roll either host.

## Target backend lifecycle (not implemented)

The target backend path separates machine boot from release rollout:

- CDK/CloudFormation must attach EC2 user data that installs and invokes the
  shared app bootstrap. A newly created or replaced instance must start itself
  once its declared ECR image, SSM parameters, secrets, and database are ready;
  it must not wait for a workstation or a permanently running custom
  orchestrator to issue its first start command.
- The systemd unit must invoke the same idempotent bootstrap on later reboots.
- Release automation must publish an immutable backend image before selecting
  it for a host, run compatible migrations before application replacement, and
  verify health after rollout.
- The current implementation sketches propose GitHub Actions with OIDC for
  release ordering and SSM Run Command or an SSM document for executing the
  rollout on the private app host. This is a proposal, not checked-in backend
  deployment automation.

The Proxmox rehearsal's workstation-owned first convergence is not the cloud
target. It exists because the rehearsal registry starts empty and uses the app
VM as its image-publication relay. See [[deployment-model|Deployment model]] for
the cross-platform boundary and the current implementation gaps.

## Trigger

- A completed `CI` workflow on `staging` triggers `.github/workflows/deploy.yml`.
  The deploy job runs only when that CI run concluded successfully and checks
  out the exact `workflow_run.head_sha` that CI tested.
- `workflow_dispatch` starts the same staging job for the selected ref. This
  manual path does not require a successful CI run; the environment, role, and
  bucket names remain hard-coded to staging.
- `.github/workflows/publish-staging-images.yml` is manual-only and its publish
  job runs only for the `staging` branch. The operator must verify that the
  selected staging commit has green CI; this first version does not query
  Actions state or automatically run after CI.

## Runtime image publication

`infra/containers/strategies/aws/image-sources.json` is the checked-in source
contract for one `linux/amd64` Backend, Caddy, Squid, and Alloy image. Backend
and Caddy are built from their pinned Dockerfiles. Squid and Alloy are copied
from declared upstream platform manifests, not rebuilt or resolved from a
floating tag.

The manual workflow:

1. checks out the selected staging commit;
2. assumes `flowform-staging-image-publisher` through GitHub OIDC;
3. validates that every upstream index still contains the declared amd64
   manifest and that each build Dockerfile uses its declared digest pins;
4. proves the `git-<full-commit-sha>` tag is absent in all four immutable ECR
   repositories before the first push;
5. builds Backend and the Route 53-enabled Caddy image, and mirrors the selected
   Squid and Alloy manifests;
6. compares each publisher-reported digest with `ecr:DescribeImages`; and
7. uploads `staging-image-release.json`, containing four complete
   `repository-uri@sha256:<digest>` references.

Publication is intentionally not promotion. The workflow has no SSM,
CloudFormation, EC2, RDS, Secrets Manager, migration, or frontend authority.
The runtime parameter contract has image fields for both hosts, but a later
release action must explicitly choose a retained manifest and write those
values.

The repositories use immutable tags. A repeated publication of the same commit
fails during the all-repository preflight rather than partially overwriting
images. A later build or mirror failure may leave a subset of new images in
ECR; those images are inert until a separate promotion selects their digests.

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

The frontend input is one repository commit plus the six SSM values read by the job.
Build output is produced under `frontend/apps/public-site/dist/` and
`frontend/apps/studio-app/dist/` on the runner. The durable side effects are
replacement of the staging bucket contents and creation of two CloudFront
invalidations. No build artifact is committed and no backend or infrastructure
resource is changed. Runtime image publication instead outputs a retained
GitHub artifact and four inert ECR images; it does not change active runtime
configuration.

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
