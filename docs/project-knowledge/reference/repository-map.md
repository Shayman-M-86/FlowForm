---
title: Repository ownership and entry points
aliases: ["Repository map", "Repository ownership and entry points"]
document_type: reference
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-30
tags: [meta]
related_code: []
change_triggers:
  - "../../../backend/"
  - "../../../frontend/"
  - "../../../infra/"
  - "../../../scripts/"
  - "../../../tools/mcp/"
  - "../../../.github/workflows/"
related_docs: ["Reference documentation", "Component map", "Configuration and generated output"]
---

# Repository ownership and entry points

This is an orientation map, not a runtime, deployment, or command reference.
Follow the owner of a concern; its maintained entry points define the available
operations and their preconditions.

```text
FlowForm/
|-- backend/            application services and API
|-- frontend/
|   |-- apps/           deployable browser experiences
|   `-- packages/       shared frontend capabilities
|-- infra/
|   |-- containers/     runtime composition
|   |-- database/       schemas and initialization
|   |-- machine-images/ reusable machine images
|   `-- deployment/     AWS, Proxmox, and bootstrap
|-- scripts/            repository automation
|-- docs/               maintained knowledge and workspace
`-- tools/              development integrations
```

| Area | Responsibility |
| --- | --- | --- |
| `backend/` | Application API, policy, persistence, tests, and contract production. |
| `frontend/` | Browser applications and shared UI, builder, schema, and style packages. |
| `infra/` | Container runtime, data setup, environment delivery, machine images, and deployment systems. |
| `scripts/` | Repository-wide development, CI, and local-configuration coordination. |
| `tools/` | Development integrations and documentation tooling. |
| `.github/` | Hosted automation definitions. |

Application and platform subdirectories retain their own ownership. Generated
contracts, documentation, and build artifacts are derived output: change their
source or generator, then regenerate. Historical material is not a source of
current implementation facts.

## Related documents

- [[reference-index|Reference documentation]]
- [[component-map|Component map]]
- [[configuration-catalogue|Configuration and generated output]]
