---
title: Commands
aliases:
  - "Commands"
document_type: reference
status: draft
authority: canonical
verified_against_commit: ad26b87e9820
tags: [tooling]
related_code:
  - "../../backend/scripts/"
  - "../../frontend/package.json"
  - "../../frontend/apps/*/package.json"
  - "../../scripts/"
  - "../../.github/workflows/"
related_docs:
  - "Scripts catalogue"
  - "Local development"
  - "Testing workflow"
---

# Commands
Provides concise verified reference facts for commands.

## Reference scope

This page lists stable, repository-supported entry commands. It does not copy every script option; consult the owning script's help or header before using destructive, deployment, or credential-handling operations.

## Canonical source

Shell and Python entry points under `scripts/`, `backend/scripts/`, and `infra/` own their command behaviour. Package aliases are owned by the nearest `package.json`, while CI invocations are owned by `.github/workflows/`.

## Entries

Run these from the repository root unless the command starts by changing directory.

| Purpose | Command | Owning source |
| --- | --- | --- |
| Run the backend test orchestrator with compact agent output | `bash backend/scripts/run-tests.sh --ai` | `backend/scripts/run-tests.sh`, `backend/scripts/run-tests.py` |
| Select backend tests | `bash backend/scripts/run-tests.sh --ai -k "test_name"` | `backend/scripts/run-tests.py` |
| Run backend dependency and Bandit checks | `bash backend/scripts/run_backend_security.sh` | `backend/scripts/run_backend_security.sh` |
| Start the integrated development stack and load mock data | `bash scripts/dev/bootstrap-dev-and-load-mocks.sh` | `scripts/dev/bootstrap-dev-and-load-mocks.sh` |
| Assemble development secrets in the runtime tmpfs | `scripts/secrets/fetch-dev-secrets.sh` | `scripts/secrets/fetch-dev-secrets.sh` |
| Start the development Compose stack directly | `docker compose -f infra/containers/strategies/dev/compose/compose.yml up -d` | development Compose definition |
| Install frontend dependencies | `cd frontend && corepack enable && pnpm install` | `frontend/package.json`, `frontend/pnpm-lock.yaml` |
| Run Studio or the public site locally | `cd frontend && pnpm run dev:studio` / `pnpm run dev:site` | `frontend/package.json` |
| Build Studio or the public site | `cd frontend && pnpm run build:studio` / `pnpm run build:site` | `frontend/package.json` |
| Run Studio tests | `cd frontend && pnpm --filter @flowform/studio-app test` | `frontend/apps/studio-app/package.json` |
| Regenerate OpenAPI and frontend contract files | `bash scripts/ci/sync-openapi.sh` | `scripts/ci/sync-openapi.sh` |
| Check generated API contracts without accepting drift | `bash scripts/ci/sync-openapi.sh --check` | `scripts/ci/sync-openapi.sh` |
| Regenerate the repository-tree snapshot | `python3 scripts/docs/generate-repository-tree.py` | `scripts/docs/generate-repository-tree.py` |
| Validate documentation links and metadata | `python3 scripts/docs/validate-doc-links.py` then `python3 scripts/docs/validate-doc-metadata.py` | `scripts/docs/` |
| Rebuild the documentation index/dashboard | `PYTHONPATH=scripts/docs python3 -m docsys index` then `PYTHONPATH=scripts/docs python3 -m docsys health` | `scripts/docs/docsys/` |

## Update procedure

Confirm each command against the invoked script or package alias, including its expected working directory. Prefer linking to the owning workflow page for sequencing and keep one-off operator commands out of this catalogue until they have a maintained entry point.

## Related documents

- [[scripts-catalogue|Scripts catalogue]]
- [[local-development|Local development]]
- [[testing|Testing workflow]]
