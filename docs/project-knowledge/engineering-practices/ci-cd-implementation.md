---
title: CI/CD implementation
aliases: ["CI/CD implementation"]
document_type: implementation
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-27
tags: [ci-cd]
related_code:
  - "../../../.github/workflows/ci.yml"
  - "../../../.github/workflows/deploy.yml"
  - "../../../.github/workflows/publish-staging-images.yml"
  - "../../../scripts/ci/"
  - "../../../tools/docs/docsys/ci.py"
  - "../../../infra/deployment/aws/"
related_docs: ["Engineering practices", "Continuous integration", "Cloud deployment", "CI workflows"]
---

# CI/CD implementation

This page maps continuous-integration and delivery responsibilities to checked-in
locations. It does not attest to a successful hosted run, deployed environment,
or production release; those claims need workflow-run and deployment evidence.

```text
                           repository change
                                  |
                    +-------------+-------------+
                    |                           |
                    v                           v
              CI validation              delivery workflows
       tests / lint / contracts       frontend / images / infra
                    |                           |
                    v                           v
             validation evidence          remote side effects
```

## Ownership map

`.github/workflows/ci.yml` owns pull-request and branch validation.
`deploy.yml` owns frontend publication, while `publish-staging-images.yml` owns
manual runtime-image publication. Shared contract checks live in `scripts/ci/`;
backend, frontend, CDK, and Docsys each keep detailed validation beside the
implementation they exercise. AWS image and deployment helpers under
`infra/deployment/aws/` provide the infrastructure delivery boundary.

## Dependency direction

Legacy material describes security checks gating dependent validation jobs and
contracts consuming backend and frontend generation paths. Automatic staging
frontend publication consumes a green CI result for a recorded commit; CI does
not itself deploy an application. Repository workflows use scoped AWS OIDC roles
rather than repository AWS access keys. Confirm current role trust, environment
protections, and dispatch constraints in workflow and CDK definitions before use.

## Handwritten and generated outputs

Workflow YAML, image-source input, and helpers are handwritten. CI can produce
coverage, CDK diff, and documentation-debt output; frontend delivery produces
build artifacts and remote side effects; image publication produces registry
manifests and a release record. OpenAPI and frontend contract artifacts are
checked-in generated output whose drift should be tested, not treated as source.

## Delivery boundary to recheck

The legacy account said CI did not itself promote runtime digests, deploy CDK,
bootstrap hosts, run database migrations, provision observability, or release
production. This remains a draft investigation point, not a current guarantee.

## Related documents

- [[engineering-practices-index|Engineering practices]]
- [[continuous-integration|Continuous integration]]
- [[cloud-deployment|Cloud deployment]]
- [[ci-workflows|CI workflows]]
