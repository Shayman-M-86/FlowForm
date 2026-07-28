---
title: Cloud deployment
aliases: ["Cloud deployment"]
document_type: workflow
status: verified
authority: canonical
verified_evidence_digest: sha256:53840efe2a91d399c7e34841e460fd63235f3fa6aa135b4a0c3515e1a1df9db4
last_edited: 2026-07-28
tags: [infrastructure, ci-cd]
related_code:
  - "../../../../.github/workflows/deploy.yml"
  - "../../../../.github/workflows/publish-staging-images.yml"
  - "../../../../infra/deployment/aws/scripts/publish-staging-images.sh"
  - "../../../../infra/containers/strategies/aws/image-sources.json"
related_docs: ["Deployment documentation", "Deployment model"]
---

# Cloud deployment

Two AWS publication workflows are checked in. Neither is a full application
deployment: neither applies CDK, changes active runtime image parameters, runs
database migrations, or restarts an application host.

```text
green CI on staging ------------------> frontend publication
manual staging dispatch --------------> runtime-image publication
        |                                      |
        v                                      v
S3 + CloudFront assets                 ECR images + digest manifest

Neither path performs host rollout or full environment convergence.
```

## Staging frontend publication

`.github/workflows/deploy.yml` deploys the two frontend builds to the staging
S3 buckets and invalidates their CloudFront distributions. It runs after a
successful `CI` workflow completion on `staging`, or through manual dispatch.
For a workflow-run trigger it checks out the CI run's `head_sha`; manual
dispatch checks out the selected ref.

The workflow assumes the staging frontend-deploy role through GitHub OIDC,
reads six build values from the staging frontend SSM path, installs the pinned
Node and pnpm versions, builds the public site and Studio, then publishes
assets before each `index.html`. The S3 sync uses `--delete`, so a successful
run can remove objects absent from the selected build. A workflow success is
evidence of that publication path only, not of backend or database health.

## Staging runtime-image publication

`.github/workflows/publish-staging-images.yml` is manual-only and its publish
job is restricted to the `staging` branch and staging environment. It calls
`publish-staging-images.sh` to validate the immutable source manifest and
publish the selected four image sources. The workflow uploads the resulting
`staging-image-release.json` digest manifest as a 30-day artifact.

This workflow produces ECR images and a retained release manifest, but does
not promote those digests to a runtime host. Repeating an already-published
commit is governed by the publication script and immutable ECR repository
contract rather than a host rollout step.

Promotion is a separate `promote` subcommand of the same script, invoked by an
operator rather than the workflow. It reads a release manifest and writes the
digest-pinned image references into the runtime parameter groups, so hosts pick
them up at their next bootstrap. Keeping publication and promotion apart means
republishing an image never moves a running environment, and promoting never
rebuilds one.
