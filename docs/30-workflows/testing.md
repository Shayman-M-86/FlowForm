---
title: Testing workflow
aliases:
  - "Testing workflow"
document_type: workflow
status: draft
authority: canonical
verified_against_commit: null
related_code:
  - "../../backend/scripts/run-tests.sh"
  - "../../backend/scripts/run-tests.py"
  - "../../backend/tests/"
  - "../../backend/pyproject.toml"
  - "../../frontend/apps/*/package.json"
  - "../../.github/workflows/ci.yml"
related_docs:
  - "Local development"
  - "Continuous integration"
  - "Backend implementation"
  - "Frontend implementation"
---

# Testing workflow

Describes the maintained local checks for backend, frontend, API contracts,
infrastructure, and documentation, and how they correspond to CI. Test scope is
selected by the changed ownership boundary rather than by one repository-wide
test command.

## Trigger

Run focused tests while implementing, the affected lint/type/build/contract
checks before review, and the broadest relevant suite before merge. GitHub CI
runs on pushes and pull requests to `main` and `staging`, subject to the path
filters and current limitations in [[continuous-integration|Continuous
integration]].

## Preconditions

- Backend integration and end-to-end tests require Docker Compose v2 and uv.
  The runner starts real PostgreSQL `17` core and response services.
- Run `scripts/secrets/generate-secrets.sh test` for the four local database
  passwords and Flask key. Test Compose supplies an explicit dummy Auth0
  management identity and direct throwaway secret, disables live management
  validation, and never mounts the persistent dev Auth0 secret file. CI replaces
  the local fallback with a masked per-run value.
- Frontend checks require Node `22.12+`, pnpm `10.24.0`, and a frozen workspace
  install. CDK checks require Python `3.14+`, uv, Node, and npm dependencies.
- `backend/on_hold/new_tests/` is outside pytest's configured `tests` root and
  is not part of the maintained suite.

## Ordered steps

1. Run focused backend tests from the repository root:

   ```bash
   bash backend/scripts/run-tests.sh --ai -k 'relevant_expression'
   ```

   The runner fingerprints Compose/env, build, and schema inputs; it reuses a
   healthy stack, rebuilds the backend environment when dependencies change,
   resets PostgreSQL volumes when schema inputs change, and executes pytest in
   `flowform-backend-test`.
2. Run the full maintained backend suite before merge:

   ```bash
   bash backend/scripts/run-tests.sh --ai
   ```

   Add `--clean-rebuild` for a deliberate full reset, `--logs=all` for service
   status after failure, or `--verbose` for uncompressed command output. Raw
   Docker service logs and pytest's captured stdout, stderr, and log sections
   remain suppressed. The runner intentionally leaves a successful stack
   running for the next run.
3. Run backend static/security checks when Python or dependencies change:

   ```bash
   (cd backend && uv run ruff check . && uv run pyright)
   ./backend/scripts/run_backend_security.sh
   ```

4. For Studio changes, run ESLint, Vitest, and the production build. For public
   site changes, run ESLint and its production build; that app defines no test
   script at this baseline:

   ```bash
   (cd frontend && pnpm --filter @flowform/studio-app lint && pnpm --filter @flowform/studio-app test && pnpm run build:studio)
   (cd frontend && pnpm --filter public-site lint && pnpm run build:site)
   ```

5. Run `bash scripts/ci/check-openapi-contracts.sh` when backend routes/schemas
   or generated frontend API code change.
6. Run CDK pytest/Ruff/Pyright/synth for AWS definitions, the relevant
   `infra/tests/` shell checks for container/image/rehearsal contracts, and the
   two documentation validators for documentation changes.

## Inputs and outputs

Inputs include source, lockfiles, SQL schemas, generated API contracts,
configuration, and selected pytest expressions. Local backend outputs include
Docker images/containers/volumes, `.cache/flowform-test-runner/` fingerprint
state, pytest output, and optional coverage/cache files. CI uploads coverage on
pushes; backend failure diagnostics include service status but never raw service
logs. Studio Vitest also suppresses application console output. Frontend builds
write app `dist/`
directories; contract generation can modify tracked generated TypeScript files.

## Failure behaviour

The backend runner exits before pytest if Docker, Compose interpolation, secret
mounts, image build, or database startup fails. Exit code `5` means no pytest
tests matched. Use `--logs=all` to report Compose service status and distinguish
infrastructure failure from an assertion failure without exposing raw service
logs. A stale reused stack is
normally handled by fingerprints; `--clean-rebuild` is the explicit fallback
and destroys only the test project volumes.

The test stack does not require a real Auth0 management credential. The hosted
backend-test job still depends on repository variables plus
`scripts/secrets/generate-env-files.sh`, whose incomplete allowlists can omit
required non-Auth0 settings; only an actual Actions run proves hosted settings
initialization. A passing focused/unit command is not a substitute for the
Docker-backed database suite, frontend build, contract drift check, or deployed
browser verification when those boundaries changed.

## Verification commands

```bash
bash backend/scripts/run-tests.sh --ai
bash scripts/ci/check-openapi-contracts.sh
(cd frontend && pnpm --filter @flowform/studio-app lint && pnpm --filter @flowform/studio-app test && pnpm run build:studio)
(cd frontend && pnpm --filter public-site lint && pnpm run build:site)
bash infra/tests/containers/test-container-invariants.sh
bash infra/tests/deployment/test-localstack-seed.sh
(cd infra/deployment/aws/cdk && uv run pytest -q && uv run ruff check flowform_infra tests app.py && uv run pyright && npx --no-install cdk synth -c env=dev --quiet)
python3 scripts/docs/validate-doc-metadata.py
python3 scripts/docs/validate-doc-links.py
```

Record which commands actually ran and which were skipped for missing external
credentials or services. Command presence in the repository is not evidence of
a successful run.

## Related documents

- [[local-development|Local development]]
- [[continuous-integration|Continuous integration]]
- [[backend|Backend implementation]]
- [[frontend|Frontend implementation]]
