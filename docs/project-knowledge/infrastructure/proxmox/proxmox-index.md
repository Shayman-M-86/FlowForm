---
title: Proxmox rehearsal
aliases: ["Proxmox rehearsal", "Proxmox rehearsal setup", "Proxmox rehearsal fixtures and egress", "Proxmox rehearsal observability"]
document_type: architecture
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-30
tags: [infrastructure]
related_code:
  - "../../../../infra/deployment/proxmox/README.md"
change_triggers:
  - "../../../../infra/deployment/proxmox/"
  - "../../../../infra/containers/runtime/proxmox/"
related_docs: ["Infrastructure knowledge", "Deployment architecture", "Machine images", "Operations knowledge"]
---

# Proxmox rehearsal

The Proxmox rehearsal is an isolated local environment used to exercise the
runtime shape outside AWS. Its platform code owns VM declaration, cloud-init,
fixture setup, and the workstation lifecycle. It is not evidence that a
rehearsal or cloud deployment is currently healthy.

```text
operator
   |
proxy role --- controlled external access
   |
private rehearsal network
   +--> application role
   +--> local fixture services
   `--> database role
```

Machine-image preparation and VM creation are distinct boundaries: templates
are built before the platform consumes them. The rehearsal's isolated fixtures
support testing platform interactions while intentional external dependencies
remain subject to their own configuration and availability. Runtime telemetry
uses the same broad collection boundary as other deployments, but repository
configuration cannot prove delivery to an external observability service.

Exact provisioning, secret handling, log access, verification, and destructive
replacement procedures live with the rehearsal command and platform scripts.

## Related documents

- [[infrastructure-index|Infrastructure knowledge]]
- [[deployment-index|Deployment architecture]]
- [[images-index|Machine images]]
- [[operations-index|Operations knowledge]]
