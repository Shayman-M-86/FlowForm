# Test Suite and Validation Commands

Last scanned: 2026-06-24.

This is a command-level map of the test suites, validation scripts, and common
checks in this repo. It intentionally lists ways of running checks rather than
individual test cases.

## Backend Tests

- `bash backend/scripts/run-tests.sh --ai` - primary local backend test runner.
  It starts or reuses the Docker test stack, runs pytest in the backend test
  container, and keeps the stack/volumes alive for faster follow-up runs.
- `bash backend/scripts/run-tests.sh --ai -k "test_or_keyword"` - focused
  backend pytest run. The backend guide prefers `-k` filters for targeted runs.
- `bash backend/scripts/run-tests.sh --clean-rebuild --ai` - same runner, but
  forces a clean rebuild before pytest.
- `bash backend/scripts/run-tests.sh --ai --logs=all --log-tail=250` - same
  runner with Docker service logs printed on failure.
- Backend pytest categories live under `backend/tests/unit`,
  `backend/tests/integration`, and `backend/tests/e2e`.
- Backend pytest markers configured in `backend/pyproject.toml` are `unit` and
  `integration`.
- CI backend coverage command, after the Docker test stack is running:
  `docker exec flowform-backend-test uv run pytest tests --cov=app --cov-report=xml:/app/coverage.xml`.

## Backend Static Checks

- `cd backend && uv run ruff check .` - backend lint check.
- `cd backend && uv run ruff format .` - backend formatter.
- `cd backend && uv run mypy .` - backend type check named by the backend guide.
- `git diff --check` - repo-wide whitespace/conflict-marker check before
  finishing schema or generated-file-heavy edits.

## Backend Database Validation

- `bash backend/scripts/check-integrity-rule-constraints.sh` - cross-checks
  `app/db/error_handling/integrity_rules.py` against real PostgreSQL constraint
  names loaded from the SQL schema files.
- `bash backend/scripts/check-integrity-rule-constraints.sh --keep` - leaves the
  ephemeral Postgres container running for debugging.
- `bash backend/scripts/check-integrity-rule-constraints.sh --details` - prints
  more detail about matched, dead, mismatched, and unmapped constraints.
- `bash backend/scripts/check-integrity-rule-constraints.sh --show-advisory` -
  includes advisory unmapped constraints in the report.

## OpenAPI and Generated Contracts

- `bash scripts/shared_script/sync-openapi.sh` - preferred repo-level OpenAPI
  sync. It runs from anywhere and drives the Studio `openapi:generate` script,
  which regenerates `backend/openapi.yaml`, Studio OpenAPI types, and shared
  generated frontend contract files.
- `bash backend/scripts/export-openapi.sh` - backend-only OpenAPI export to
  `backend/openapi.yaml`.
- `bash backend/scripts/export-openapi.sh --check` - backend-only OpenAPI drift
  check for CI-style validation.
- `bash backend/scripts/export-openapi.sh --output /tmp/snapshot.yaml` - export
  the current backend spec to another file for comparison.
- `cd frontend/apps/studio-app && pnpm run openapi:check` - checks backend
  OpenAPI export drift and generated Studio `schema.ts` drift.
- `npx @redocly/cli lint backend/openapi.yaml` - Redocly lint pass over the
  generated OpenAPI YAML.
- `cd frontend && pnpm run generate:types` - lower-level generated contract file
  update. Usually run through `sync-openapi.sh`, not directly.

## Frontend Tests and Checks

- `cd frontend/apps/studio-app && pnpm run test` - Studio Vitest suite using
  jsdom and `tests/**/*.test.ts(x)`.
- `cd frontend/apps/studio-app && pnpm run test:watch` - Studio Vitest watch
  mode.
- `cd frontend/apps/studio-app && pnpm run test:ui` - Studio Vitest UI.
- `cd frontend/apps/studio-app && pnpm run lint` - Studio ESLint check.
- `cd frontend/apps/studio-app && pnpm run routes` - regenerates the TanStack
  Router `routeTree.gen.ts` file after route changes.
- `cd frontend && pnpm run build:studio` - Studio TypeScript project build plus
  Vite production build.
- `cd frontend && pnpm run build:site` - Public Site Astro production build.
  This is the frontend build used by GitHub Actions and Amplify.
- `cd frontend/apps/public-site && pnpm run astro build` - app-local equivalent
  of the Public Site build.

## Security Checks

- `./scripts/backend/run_backend_security.sh` - backend security wrapper used by
  CI. It compiles backend requirements, runs `pip-audit`, then runs Bandit over
  `backend/app` and `backend/tests`.

## CI and Support Tasks

- `.github/workflows/ci.yml` runs three main validation jobs: backend security,
  backend pytest with coverage in Docker, and Public Site frontend build.
- `amplify.yml` installs frontend dependencies and runs
  `cd frontend && pnpm run build:site` for the Public Site deployment build.
- VS Code task `test-env: setup` starts the Docker test stack, syncs backend dev
  and test dependencies inside the backend test container, and verifies the
  container Python.
- VS Code task `test-env: up` starts the Docker test stack with build.
- VS Code task `test-env: down` stops the Docker test stack.
