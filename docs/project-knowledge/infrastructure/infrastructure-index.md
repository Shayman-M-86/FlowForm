---
title: Infrastructure knowledge
aliases: ["Infrastructure knowledge"]
document_type: overview
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-08-04
tags: [infrastructure]
related_code: []
change_triggers:
  - "../../../infra/containers/"
  - "../../../infra/contracts/"
  - "../../../infra/deployment/"
  - "../../../infra/machine-images/"
related_docs: ["Deployment architecture", "Deployment design forces", "External platform boundaries", "Container runtime", "Machine images", "Proxmox rehearsal", "Configuration and secrets", "Local infrastructure"]
---

# Infrastructure knowledge

FlowForm separates reusable artifacts from the environments that consume them.
Machine images and containers provide repeatable host and service inputs;
platform deployment code declares an environment and converges its roles.
Contracts carry the non-secret identity between those layers. Checked-in
definitions describe intended behaviour, not the health or existence of a
particular environment.

```text
machine images + container images
              |
              v
     contracts and release selection
              |
       +------+------+
       v             v
 AWS deployment   Proxmox rehearsal
       |             |
       +------> host/runtime convergence
```

## Ownership map

- [[images-index|Machine images]] owns Packer-built role images and templates.
- [[containers-index|Container runtime]] owns service image
  contexts and runtime composition; [[deployment-index|Deployment
  architecture]] owns environment topology and the centralized AWS
  operator-facing workflow boundary.
- [[proxmox-index|Proxmox rehearsal]] owns the local isolated rehearsal.
- [[configuration|Configuration and secrets]] explains how typed application
  settings and sensitive values cross the runtime boundary.
- [[external-platform-boundaries|External platform boundaries]] distinguishes
  declared infrastructure from imported foundations, configured providers,
  and human-authorized capabilities.
- [[design-forces-and-evolution|Deployment design forces]] records the durable
  cost, isolation, availability, and operating-effort pressures that shape an
  environment without freezing transient cloud selections.
- [[local-infrastructure|Local infrastructure]] describes the distinct
  development and test environment.

`infra/contracts/` is the platform-neutral interface between these owners.
`infra/tests/` validates structural contracts but does not replace live
environment checks.

## Related documents

- [[deployment-index|Deployment architecture]]
- [[containers-index|Container runtime]]
- [[images-index|Machine images]]
- [[proxmox-index|Proxmox rehearsal]]
- [[configuration|Configuration and secrets]]
- [[external-platform-boundaries|External platform boundaries]]
- [[design-forces-and-evolution|Deployment design forces]]
- [[local-infrastructure|Local infrastructure]]
