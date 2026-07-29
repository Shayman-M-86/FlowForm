---
title: Container runtime
aliases: ["Container runtime", "Container runtime documentation", "Runtime containers"]
document_type: architecture
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-30
tags: [infrastructure]
related_code:
  - "../../../../infra/containers/README.md"
change_triggers:
  - "../../../../infra/containers/images/"
  - "../../../../infra/containers/runtime/"
related_docs: ["Infrastructure knowledge", "Deployment architecture", "Local infrastructure"]
---

# Container runtime

The container tree separates independently published service images from the
runtime definitions that compose them. Image contexts own service software and
configuration templates; runtime definitions own topology, role composition,
and environment adapters. Secrets are selected at runtime and are not part of
an image build.

```text
container image contexts
          |
          v
 shared runtime roles and helpers
          |
     +----+----+
     v         v
  AWS roles  local/rehearsal adapters
```

The deployed runtime separates proxy and application roles. Local development,
tests, and the Proxmox rehearsal adapt that shared model without establishing a
claim that every service runs in every environment. Database placement and
credentials are supplied by the selected environment.

The checked-in Compose and image definitions specify intended service
boundaries, including constrained privileges, mounts, and logging. They are not
proof that an external telemetry destination, registry, or deployment is live.

## Related documents

- [[infrastructure-index|Infrastructure knowledge]]
- [[deployment-index|Deployment architecture]]
- [[local-infrastructure|Local infrastructure]]
