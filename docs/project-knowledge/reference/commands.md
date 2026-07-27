---
title: Commands
aliases: ["Commands"]
document_type: reference
status: draft
authority: canonical
verified_against_commit: null
tags: [tooling]
related_code: ["../../../backend/scripts/", "../../../frontend/package.json", "../../../scripts/", "../../../.github/workflows/"]
related_docs: ["Scripts catalogue", "Local development", "Testing workflow"]
---

# Commands

This reference points to supported repository entry commands. It does not copy
every option: inspect the owning script or package alias before destructive,
deployment, or credential-handling work. Commands remain draft until each
invocation and precondition is reverified against the current checkout.

| Purpose | Entry point |
| --- | --- |
| Backend tests | `bash backend/scripts/run-tests.sh --ai` |
| Backend security checks | `bash backend/scripts/run_backend_security.sh` |
| Development secret retrieval | `scripts/secrets/fetch-dev-secrets.sh` |
| Development Compose | `docker compose -f infra/containers/strategies/dev/compose/compose.yml up -d` |
| Frontend development | `cd frontend && pnpm run dev:studio` / `pnpm run dev:site` |
| Frontend builds | `cd frontend && pnpm run build:studio` / `pnpm run build:site` |
| Studio tests | `cd frontend && pnpm --filter @flowform/studio-app test` |
| API contract generation/check | `bash scripts/ci/sync-openapi.sh` / `--check` |
| Documentation output | `PYTHONPATH=scripts/docs python3 -m docsys index` and `... docsys health` |

Shell/Python entry points under `scripts/`, `backend/scripts/`, and `infra/`
own their behaviour; package aliases are owned by the nearest `package.json`;
and CI invocations are owned by `.github/workflows/`.

## Related documents

- [[scripts-catalogue|Scripts catalogue]]
- [[local-development|Local development]]
- [[testing|Testing workflow]]
