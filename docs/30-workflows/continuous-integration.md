---
title: Continuous integration
aliases:
  - "Continuous integration"
document_type: workflow
status: draft
authority: canonical
verified_against_commit: ad26b87e9820
tags: [ci-cd]
related_code:
  - "../../.github/workflows/ci.yml"
  - "../../backend/scripts/run_backend_security.sh"
  - "../../backend/scripts/run-tests.py"
  - "../../scripts/ci/check-openapi-contracts.sh"
  - "../../scripts/docs/"
related_docs:
  - "Testing workflow"
  - "Cloud deployment"
  - "CI/CD implementation"
  - "CI workflows"
---

# Continuous integration

Describes the validation graph declared by `.github/workflows/ci.yml`. The
workflow is a set of quality gates and previews; deployment is owned by
[[cloud-deployment|Cloud deployment]].

## Trigger

CI starts for pushes and pull requests targeting `main` or `staging`. Runs share
a `ci-<git-ref>` concurrency group, so a newer run for the same ref cancels the
older one. There is no manual-dispatch trigger.

## Preconditions

- GitHub-hosted Ubuntu runners must be able to install uv, Node `22`, pnpm
  `10.24.0`, Docker Buildx, and the CDK CLI dependencies.
- The GitHub `test` environment supplies backend configuration variables and
  `FLOWFORM_AUTH0_MGMT_SECRET`; other test secrets are generated per run.
- Staging Auth0 public values must exist as repository variables for CDK synth.
- Internal pushes and pull requests need GitHub OIDC access to the read-only
  staging preview role for `cdk diff`. Fork pull requests deliberately skip
  credentials and diff.

## Ordered steps

1. Run backend dependency and Bandit checks. In parallel, classify changed
   frontend and API-contract paths.
2. After backend security passes, run backend Ruff and Pyright in one job and
   the Docker/PostgreSQL pytest suite with coverage in another.
3. When frontend paths changed, install with lifecycle scripts disabled and run
   `pnpm audit --audit-level high`. After that gate, Studio runs ESLint, Vitest,
   and a production build; the public site runs ESLint and a production build.
4. When API-contract paths changed, export/check OpenAPI, lint the specification,
   regenerate TypeScript contracts, and fail on tracked drift.
5. Run CDK pytest, Ruff, and Pyright; synthesize dev and perform a template-only
   staging diff. Internal pull requests receive an updated diff comment.
6. On pull requests, validate documentation metadata and links, calculate
   impacted documents, upload the JSON report, and update a PR comment.

## Inputs and outputs

Inputs are the checked-out commit, lockfiles, GitHub variables/secrets, and the
changed-path set. Outputs are job logs, push-only backend coverage artifacts,
failure diagnostics, a staging CDK diff comment when credentials are available,
and the pull-request documentation-impact report. CI does not publish an
application or deploy CDK stacks.

## Failure behaviour

Security jobs gate their dependent lint/test/build jobs. Conditional frontend
and contract jobs are skipped when their path filters do not match; a skipped
fork CDK diff is not evidence that staging has no infrastructure drift. The
documentation impact report is advisory unless an impacted path matches the
configured critical-document policy.

At this baseline the backend-test job still references the removed
`infra/containers/dev/...` Compose and Dockerfile paths at lines 43, 224, and
240 of `ci.yml`; the maintained files are under
`infra/containers/strategies/dev/...`. The job is therefore expected to fail
before starting its test stack until those workflow paths are corrected. Do not
treat this CI definition as a currently green backend-test attestation.

## Verification commands

The closest local equivalents, run from the repository root, are:

```bash
./backend/scripts/run_backend_security.sh
(cd backend && uv sync --extra dev && uv run ruff check . && uv run pyright)
bash backend/scripts/run-tests.sh --ai
bash scripts/ci/check-openapi-contracts.sh
(cd frontend && pnpm install --frozen-lockfile && pnpm audit --audit-level high)
(cd frontend && pnpm --filter @flowform/studio-app lint && pnpm --filter @flowform/studio-app test && pnpm run build:studio)
(cd frontend && pnpm --filter public-site lint && pnpm run build:site)
(cd infra/deployment/aws/cdk && uv sync --frozen --extra dev && npm ci && uv run pytest -q && uv run ruff check flowform_infra tests app.py && uv run pyright && npx --no-install cdk synth -c env=dev --quiet)
python3 scripts/docs/validate-doc-metadata.py
python3 scripts/docs/validate-doc-links.py
```

The local commands need their own credentials, configuration, and test-secret
preconditions. Only the GitHub run proves the actual Actions graph and hosted
runner environment.

## Related documents

- [[testing|Testing workflow]]
- [[cloud-deployment|Cloud deployment]]
- [[ci-cd|CI/CD implementation]]
- [[ci-workflows|CI workflows]]
