---
title: Testing workflow
aliases: ["Testing workflow"]
document_type: workflow
status: verified
authority: canonical
verified_evidence_digest: sha256:f954afd7b0bef30ebf0479442b9deee3e3ec2c7f3b19aa9331a2c4fae4082022
last_edited: 2026-08-04
tags: [tooling]
related_code:
  - "../../../backend/scripts/run-tests.sh"
  - "../../../backend/scripts/run-tests.py"
  - "../../../backend/pyproject.toml"
  - "../../../backend/tests/conftest.py"
  - "../../../backend/tests/e2e/conftest.py"
  - "../../../.github/workflows/ci.yml"
  - "../../../scripts/tools/typecheck.sh"
  - "../../../pyrightconfig.json"
change_triggers:
  - "../../../backend/tests/"
  - "../../../frontend/apps/*/package.json"
related_docs: ["Engineering practices", "Local development", "Continuous integration", "Backend implementation documentation", "Frontend implementation"]
---

# Testing workflow

Testing is selected by the ownership boundary changed rather than a single
repository-wide command. It joins focused local checks during implementation
with the broadest relevant backend, frontend, contract, infrastructure, and
documentation gates before review or merge.

```text
changed ownership boundary
           |
           v
focused unit / component check
           |
           v
lint / types / build / contract check
           |
           v
broadest applicable integration suite
           |
           v
hosted CI or deployed verification where required
```

## Test layers

- Backend tests run through `backend/scripts/run-tests.sh`, which prepares a
  Docker-backed PostgreSQL environment before pytest.
- Repository Python type checking runs through
  `scripts/tools/typecheck.sh all`; its project targets provide the same pinned
  checker for focused work.
- Backend lint and security checks are owned beside the backend.
- Studio has lint, Vitest, and production-build checks; public-site checks use
  its defined package scripts.
- OpenAPI contract changes use `scripts/ci/check-openapi-contracts.sh`.
- CDK, container/image/rehearsal, and documentation changes each have
  implementation-owned validation commands.

Legacy material distinguished normal isolated backend testing from an explicit
local live-external mode. Treat external credentials, egress, and provider calls
as opt-in; do not infer their availability from this draft.

## Backend test model

The backend suite separates fast unit tests, database or service integration
tests, route-level end-to-end tests, and opt-in live-provider tests. Pytest uses
strict marker and configuration handling, excludes `live_external` by default,
and promotes unexpected warnings to errors except for a narrowly declared
compatibility warning. Coverage records branches as well as statements; the
configuration does not itself declare a minimum percentage.

Database tests preserve the core/response split. Each test opens an outer
transaction for each store, then binds SQLAlchemy sessions in savepoint mode so
application commits can execute without making the test's data durable.
Cross-store tests can request the two sessions explicitly. Route-level tests
replace the request-session factories with non-closing proxies around those
savepoint-bound sessions, allowing real request teardown and commit behavior to
be exercised while retaining isolation.

```text
core test transaction       response test transaction
          |                           |
       savepoint                    savepoint
          \                           /
           +---- service or HTTP test
                         |
                  rollback outer state
```

Live-provider tests are both opt-in and excluded from normal CI-oriented test
runs. A passing isolated test therefore does not attest Auth0, KMS, Secrets
Manager, SES, deployed networking, or any other external service.

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
