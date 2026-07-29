---
title: Configuration catalogue
aliases: ["Configuration catalogue"]
document_type: reference
status: verified
authority: canonical
verified_evidence_digest: sha256:bac5d454acea38b465faa5c4a3303499bd66636f81a22235eebc6a882e00a2c9
last_edited: 2026-07-29
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
| Development/test containers | `infra/containers/runtime/development/compose/` |
| Runtime and rehearsal containers | `infra/containers/runtime/`, `infra/containers/images/` |
| Environment and database setup | `infra/env/`, `infra/database/` |
| AWS, Proxmox, and image builds | `infra/deployment/`, `infra/machine-images/` |
| MCP tools | `tools/mcp/` and `.mcp.json` |

Before adding a setting, identify the reader and delivery path. Do not place
secret values in examples, state, generated environment files, or this
catalogue.

## Related documents

- [[environment-variables|Environment variables]]
- [[configuration|Configuration implementation]]
- [[secrets-and-configuration|Secrets and configuration]]
- [[configuration-index|Configuration index]]
