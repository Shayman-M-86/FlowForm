---
title: Continuous integration
aliases: ["Continuous integration"]
document_type: workflow
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-08-03
tags: [ci-cd]
related_code:
  - "../../../.github/workflows/ci.yml"
  - "../../../backend/scripts/run_backend_security.sh"
  - "../../../backend/scripts/run-tests.py"
  - "../../../scripts/ci/check-openapi-contracts.sh"
  - "../../../scripts/tools/typecheck.sh"
change_triggers:
  - "../../../tools/docs/"
related_docs: ["Engineering practices", "Testing workflow", "CI/CD implementation", "CI workflows"]
---

# Continuous integration

Continuous integration is the repository's automated validation workflow. It
checks a proposed or pushed change through documentation, repository Python
tooling, backend, frontend, contract, and infrastructure jobs. Deployment is
separate; a CI definition is not evidence that a particular commit was
validated or released.

```text
push / pull request
        |
        v
documentation + security + changed-path classification
        |
        +--> backend checks
        +--> frontend checks
        +--> contract drift
        +--> infrastructure checks
        |
        v
validation evidence (not deployment)
```

## Lifecycle

Legacy material describes CI for pushes and pull requests targeting `main` and
`staging`, with per-ref concurrency that cancels obsolete runs. It starts with
documentation validation, repository-tooling and development-MCP type checks,
backend security checks, and changed-path classification. Dependent jobs run
backend static checks and Docker-backed tests, selected frontend
audit/lint/test/build work, OpenAPI contract drift checks, and CDK checks
including a template-only staging diff when credentials are available.

## Evidence and boundaries

`.github/workflows/ci.yml` defines the executable job graph. Scripts beside
each implementation own individual checks. The workflow can produce logs,
coverage, and diff output but does not itself publish an application or deploy
CDK stacks. Path-selected jobs can be skipped; a skip proves neither correctness
nor absence of drift. Hosted services, secrets, Docker startup, and cloud access
must be confirmed in an actual Actions run.

## Local correspondence

Use [[testing|Testing workflow]] to choose checks for a changed ownership
boundary. Repository entry points include backend security/tests, OpenAPI
contract checking, frontend package scripts, CDK checks, Docsys validation,
and `scripts/tools/typecheck.sh all` for the complete Python type-check surface.
Their local success is not a hosted-CI result.

## Related documents

- [[engineering-practices-index|Engineering practices]]
- [[testing|Testing workflow]]
- [[ci-cd-implementation|CI/CD implementation]]
- [[ci-workflows|CI workflows]]
