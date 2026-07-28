---
title: Configuration catalogue
aliases: ["Configuration catalogue"]
document_type: reference
status: verified
authority: canonical
verified_evidence_digest: sha256:2273687d6f2fc4202bbda646c88fadd823c28644125a556fe60b033c2067603a
last_edited: 2026-07-28
tags: [configuration]
related_code: ["../../../backend/app/core/config.py", "../../../backend/gunicorn.conf.py", "../../../frontend/", "../../../infra/", "../../../.github/workflows/", "../../../.vscode/"]
related_docs: ["Environment variables", "Configuration implementation", "Secrets and configuration", "Configuration index"]
---

# Configuration catalogue

This catalogue identifies maintained configuration families and their owners.
It does not enumerate variable values, credentials, service ports, or runtime
procedures. Configuration files, settings modules, Compose definitions,
infrastructure definitions, and CI workflows are authoritative for their area;
examples define file shape only and local/generated copies are not canonical.

| Family | Primary owner/location |
| --- | --- |
| Repository automation and tooling | `.github/workflows/`, `.githooks/`, `.vscode/`, `.claude/`, `.codex/`, `.mcp.json` |
| Backend settings and tooling | `backend/app/core/config.py`, `backend/gunicorn.conf.py`, `backend/pyproject.toml` |
| Frontend workspace and applications | `frontend/package.json`, workspace/package/app configuration |
| Development/test containers | `infra/containers/strategies/dev/compose/` |
| Runtime and rehearsal containers | `infra/containers/runtime/`, `infra/containers/strategies/` |
| Environment and database setup | `infra/env/`, `infra/database/` |
| AWS, Proxmox, and image builds | `infra/deployment/`, `infra/images/` |
| MCP tools | `tools/mcp/` and `.mcp.json` |

Before adding a setting, identify the reader and delivery path. Do not place
secret values in examples, state, generated environment files, or this
catalogue.

## Related documents

- [[environment-variables|Environment variables]]
- [[configuration|Configuration implementation]]
- [[secrets-and-configuration|Secrets and configuration]]
- [[configuration-index|Configuration index]]
