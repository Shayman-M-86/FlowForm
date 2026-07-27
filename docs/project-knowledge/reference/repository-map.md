---
title: Repository map
aliases: ["Repository map"]
document_type: reference
status: draft
authority: canonical
verified_against_commit: null
tags: [meta]
related_code:
  - "../../../backend/"
  - "../../../frontend/"
  - "../../../infra/"
  - "../../../scripts/"
  - "../../../tools/mcp/"
  - "../../../.github/workflows/"
related_docs:
  - "Reference documentation"
  - "Component map"
---

# Repository map

This draft is an orientation map, not a runtime or deployment specification.

| Area | Responsibility | Useful entry points |
| --- | --- | --- |
| `backend/` | Python/Flask application, API, services, persistence mappings, tests, and OpenAPI contract | `wsgi.py`, `app/core/factory.py`, `app/api/v1/`, `tests/` |
| `frontend/apps/` | Astro public site and React/Vite Studio application | each application's `src/` and package configuration |
| `frontend/packages/` | Shared builder, schema, site-shell, styles, and UI packages | package `src/` entry points |
| `infra/containers/` | Images, runtime containers, and dev/rehearsal strategies | ownership-specific subdirectories |
| `infra/database/` | Database initialisation, schemas, configuration, and mock data | `init/` and `init/schema/` |
| `infra/images/` | Packer image construction and image contracts | `README.md`, `packer/`, `IMAGE-CONTRACT.md` |
| `infra/deployment/` | AWS CDK, Proxmox, and bootstrap deployment material | `aws/cdk/`, `proxmox/`, `bootstrap/` |
| `infra/env/` | Environment-specific configuration and secrets layout | environment directories |
| `scripts/` | CI, development, docs, secret-management, and utility scripts | category directories |
| `tools/mcp/` | Development MCP server and helpers | `flowform_dev.py`, README |
| `.github/workflows/` | CI and deployment workflows | workflow YAML files |

Frontend workspace membership is defined by `frontend/pnpm-workspace.yaml`.
Generated contracts and types are derived artifacts; use their generator rather
than editing them directly. `old-docs/` is historical material and not a source
of current implementation facts.

## Related documents

- [[reference-index|Reference documentation]]
- [[component-map|Component map]]
