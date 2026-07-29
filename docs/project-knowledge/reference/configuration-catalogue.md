---
title: Configuration and generated output
aliases: ["Configuration catalogue", "Configuration and generated output"]
document_type: reference
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-30
tags: [configuration]
related_code:
  - "../../../backend/app/core/config.py"
  - "../../../backend/gunicorn.conf.py"
change_triggers:
  - "../../../frontend/"
  - "../../../infra/"
  - "../../../.github/workflows/"
  - "../../../.vscode/"
related_docs: ["Repository ownership and entry points", "Configuration and secrets", "Generated files"]
---

# Configuration and generated output

This page identifies configuration and derived-output owners. It deliberately
does not reproduce variable names, values, ports, commands, credentials, or
runtime procedures. The reader of a setting and the generator of an artifact
are authoritative.

| Concern | Owner |
| --- | --- |
| Application settings and secret handling | Backend settings and the configuration/security documentation branches. |
| Browser build settings | The owning frontend application and workspace configuration. |
| Container, database, environment, and deployment settings | Their relevant `infra/` owner. |
| CI and development tooling | The workflow or tool that reads the setting. |
| API contracts, generated frontend artifacts, and documentation inventories | Their generating script or tool. |

Before adding a setting, identify its reader, delivery path, and whether it is
secret. Before changing generated output, identify its generator and inputs.
Examples describe shape, not live values; local and generated copies are not
canonical secret stores.

## Related documents

- [[repository-map|Repository ownership and entry points]]
- [[configuration|Configuration and secrets]]
- [[generated-files|Generated files]]
