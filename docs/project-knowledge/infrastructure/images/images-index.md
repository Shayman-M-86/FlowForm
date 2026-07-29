---
title: Machine images
aliases: ["Machine images", "Machine image building", "Packer implementation"]
document_type: architecture
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-30
tags: [infrastructure]
related_code:
  - "../../../../infra/machine-images/README.md"
change_triggers:
  - "../../../../infra/machine-images/"
  - "../../../../infra/contracts/runtime-hosts.json"
related_docs: ["Infrastructure knowledge", "Deployment architecture", "Proxmox rehearsal"]
---

# Machine images

Machine images are reusable host artifacts, distinct from container images and
runtime topology. Packer produces role-specific AWS images and Proxmox
templates; deployment tooling consumes their published identity rather than
building hosts during environment creation.

```text
base host capability
       |
       +--> application role image
       +--> proxy role image
       |
       +--> Proxmox templates and fixtures
```

The image boundary installs host capabilities and role bootstrap assets. It
does not own application secrets, mutable release selection, or the source
Compose topology. Image lineage, publication, retention, and validation are
operator concerns implemented by the machine-image tooling; use that tooling's
documentation for exact workflows.

## Related documents

- [[infrastructure-index|Infrastructure knowledge]]
- [[deployment-index|Deployment architecture]]
- [[proxmox-index|Proxmox rehearsal]]
