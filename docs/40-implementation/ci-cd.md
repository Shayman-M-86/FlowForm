---
title: CI/CD implementation
aliases:
  - "CI/CD implementation"
document_type: implementation
status: draft
authority: canonical
verified_against_commit: null
tags: [ci-cd]
related_code:
  - "../../.github/workflows/ci.yml"
  - "../../.github/workflows/deploy.yml"
  - "../../scripts/ci/"
  - "../../backend/scripts/run_backend_security.sh"
  - "../../infra/deployment/aws/cdk/flowform_infra/stacks/registry_stack.py"
  - "../../infra/deployment/aws/cdk/flowform_infra/stacks/security_stack.py"
  - "../../infra/deployment/aws/cdk/tests/"
  - "../../scripts/docs/docsys/ci.py"
related_docs:
  - "Continuous integration"
  - "Cloud deployment"
  - "CI workflows"
---

# CI/CD implementation

Maps ci cd concepts to verified repository implementation.

## Directory ownership

`.github/workflows/ci.yml` owns pull-request and branch validation for backend,
frontend, contracts, CDK, and documentation impact. `deploy.yml` owns the
staging frontend publication path. `scripts/ci/` owns the shared OpenAPI drift
contract; backend, frontend, CDK, and Docsys keep their detailed checks beside
the implementation they validate.

## Entry points

- CI runs for pushes and pull requests targeting `main` or `staging` and
  cancels older runs for the same ref.
- Frontend deployment runs after a completed successful `CI` workflow on
  `staging`, checking out the exact validated SHA. Manual dispatch is also
  allowed and checks out the selected ref without an additional CI gate.
- `.githooks/pre-commit` reuses the OpenAPI contract check locally.

## Important modules

- Backend jobs run dependency/source security checks, Ruff/Pyright, and the
  Docker-based pytest suite with coverage.
- A path-filter job controls frontend audit, Studio lint/test/build, public-site
  lint/build, and contract checks.
- The contract job verifies backend OpenAPI export and all checked-in frontend
  contract artifacts.
- The CDK job runs tests, lint, types, hermetic dev synth, then assumes a
  read-only staging preview role for template diff on pushes and same-repository
  pull requests.
- The PR-only documentation job validates metadata/links and publishes Docsys
  impact output; it is advisory unless configured critical documents are
  impacted without updates.
- Deployment builds both frontends, reads public build configuration from SSM,
  publishes content-hashed assets before `index.html`, and invalidates both
  CloudFront distributions through GitHub OIDC credentials.

## Dependency direction

Backend security gates backend lint, tests, contracts, and CDK. Frontend
security gates the path-selected application jobs. Contracts consume both
backend and frontend generators. Automatic staging deployment consumes a green
CI result and its recorded commit; CI does not invoke deployment directly.
GitHub assumes scoped AWS roles through OIDC rather than storing AWS access
keys in repository secrets.

## Generated versus handwritten code

Workflow YAML and helper scripts are handwritten. CI produces coverage, CDK
diff, and documentation-impact artifacts; frontend deployment produces
application `dist/` trees and remote S3/CloudFront side effects. OpenAPI and
frontend contract files are checked-in generated artifacts whose drift is
tested. The linked generated CI-workflow page is still a scaffold and does not
replace direct workflow inspection.

## Tests and validation

Each job invokes the implementation-owned command: backend pytest/Ruff/Pyright
and security helpers, frontend pnpm audit/ESLint/Vitest/builds, OpenAPI drift,
CDK pytest/Ruff/Pyright/synth/diff, and documentation metadata/link/impact
checks. Backend and CDK pytest suppress captured output in CI. Disposable test
credentials are masked before services start, only explicitly allowlisted
non-secret repository variables reach the backend-test environment, backend
failures report Compose service status without printing or uploading raw
service logs, and the test stack is always torn down. Backend tests marked
`live_external` are excluded explicitly; real Auth0/AWS smoke tests remain a
local opt-in and the runner rejects that mode whenever `CI` is set. The normal
test Compose network is internal-only; only the local live-test override enables
public egress.

## Known gaps

The backend-test job now uses the maintained
`infra/containers/strategies/dev/` paths. Its environment generation remains
incomplete because `scripts/secrets/generate-env-files.sh` omits several
required non-Auth0 backend settings, so only a hosted run can attest successful
settings initialization.

CI does not run the checked-in container, rehearsal-deployment, or Packer
invariant suites under `infra/tests/`. Deployment publishes only staging
frontends: it does not deploy CDK stacks, backend images/runtime, database
migrations, observability, or production. CDK now declares a
branch-restricted image-publisher role and exact ECR push policy, but no
workflow assumes it. Manual frontend deployment is not conditioned on a
preceding successful CI run.

## Related documents

- [[continuous-integration|Continuous integration]]
- [[cloud-deployment|Cloud deployment]]
- [[ci-workflows|CI workflows]]
