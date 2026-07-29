---
title: Local infrastructure
aliases: ["Local infrastructure"]
document_type: overview
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-30
tags: [infrastructure, configuration]
related_code:
  - "../../../infra/containers/runtime/development/compose/compose.yml"
  - "../../../frontend/docker-compose.dev.yml"
change_triggers:
  - "../../../infra/env/"
  - "../../../infra/database/"
related_docs: ["Infrastructure knowledge", "Configuration and secrets", "Container runtime"]
---

# Local infrastructure

Local development and testing are intentionally separate from the deployed
split-host runtime. Development combines a source-oriented backend with its
local database services; frontend tooling is a separate concern. Test
composition uses isolated disposable services and is not evidence that a
development or deployed environment is healthy.

Persistent local volumes and ignored inputs are part of the developer-machine
boundary. Resetting them is an explicit recovery action, not a normal startup
step. The current Compose definitions and their helper scripts are the source
for exact commands and port mappings.

## Related documents

- [[configuration|Configuration and secrets]]
- [[containers-index|Container runtime]]
- [[infrastructure-index|Infrastructure knowledge]]
