---
title: Testing workflow
aliases: ["Testing workflow"]
document_type: workflow
status: draft
authority: canonical
verified_against_commit: null
tags: [tooling]
related_code:
  - "../../../backend/scripts/run-tests.sh"
  - "../../../backend/scripts/run-tests.py"
  - "../../../backend/tests/"
  - "../../../backend/pyproject.toml"
  - "../../../frontend/apps/*/package.json"
  - "../../../.github/workflows/ci.yml"
related_docs: ["Engineering practices", "Local development", "Continuous integration", "Backend implementation documentation", "Frontend implementation"]
---

# Testing workflow

Testing is selected by the ownership boundary changed rather than a single
repository-wide command. It joins focused local checks during implementation
with the broadest relevant backend, frontend, contract, infrastructure, and
documentation gates before review or merge.

## Test layers

- Backend tests run through `backend/scripts/run-tests.sh`, which prepares a
  Docker-backed PostgreSQL environment before pytest.
- Backend lint, type, and security checks are owned beside the backend.
- Studio has lint, Vitest, and production-build checks; public-site checks use
  its defined package scripts.
- OpenAPI contract changes use `scripts/ci/check-openapi-contracts.sh`.
- CDK, container/image/rehearsal, and documentation changes each have
  implementation-owned validation commands.

Legacy material distinguished normal isolated backend testing from an explicit
local live-external mode. Treat external credentials, egress, and provider calls
as opt-in; do not infer their availability from this draft.

## Choosing and interpreting checks

Run focused checks while changing code, then affected lint/type/build or
contract checks before review, and the broadest applicable suite before merge.
Docker, Compose, Node, pnpm, uv, credentials, generated configuration, and
disposable state can be prerequisites. A command's presence is not evidence it
ran successfully. Backend failure can happen before pytest during service
construction, interpolation, builds, secret mounts, or database startup.

## Relationship to CI

[[continuous-integration|Continuous integration]] defines which checks run in
GitHub Actions and under what conditions. A successful focused local test is
not a substitute for Docker-backed tests, contract drift checks, hosted CI, or
deployed-browser verification when those boundaries changed.

## Related documents

- [[engineering-practices-index|Engineering practices]]
- [[local-development|Local development]]
- [[continuous-integration|Continuous integration]]
- [[implementation-index|Backend implementation documentation]]
- [[frontend-index|Frontend implementation]]
