---
title: Technology stack
aliases: ["Technology stack", "Tech stack"]
document_type: reference
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-30
tags: [backend, frontend, infrastructure, tooling]
related_code:
  - "../../../backend/pyproject.toml"
  - "../../../frontend/package.json"
  - "../../../infra/deployment/aws/cdk/pyproject.toml"
change_triggers:
  - "../../../frontend/"
  - "../../../infra/"
  - "../../../tools/"
  - "../../../.github/workflows/"
related_docs:
  - "Reference documentation"
  - "Repository ownership and entry points"
  - "Generated reference documentation"
  - "Deployment architecture"
---

# Technology stack

This is a durable technology-family guide, not a version inventory. Dependency
manifests and generated dependency output are authoritative for exact packages,
constraints, action versions, and image selections.

## Core application

Python and Flask provide the backend API. Typed configuration, validation,
database access, migrations, OpenAPI generation, authentication, encryption,
and telemetry are maintained alongside it. PostgreSQL supplies the core and
response-data stores; AWS services support selected identity, key-management,
email, and deployment concerns.

## Frontend

The browser workspace uses Node, pnpm, TypeScript, Vite, Astro, and React.
Studio adds routing, query, form, authentication, and typed API-client
capabilities; shared packages provide builder, schema, UI, style, and shell
building blocks. OpenAPI and route artifacts are generated rather than
hand-maintained.

## Infrastructure

Container composition supports development, runtime, and rehearsal contexts.
Caddy and related network services supply edge concerns. AWS deployment uses
CDK and managed cloud services; machine-image and Proxmox tooling support the
other supported deployment paths. Telemetry flows through OpenTelemetry and
the configured logging, metrics, and tracing pipeline.

## Automation and development tooling

Git-hosted workflows coordinate automated checks and deployment. Repository
tools support source control, documentation validation, development
integrations, and contract generation. Use the owning manifest, lockfile,
infrastructure source, or generated inventory when compatibility or upgrade
work needs exact information.

## Related documents

- [[reference-index|Reference documentation]]
- [[repository-map|Repository ownership and entry points]]
- [[generated-index|Generated reference documentation]]
- [[deployment-index|Deployment architecture]]
