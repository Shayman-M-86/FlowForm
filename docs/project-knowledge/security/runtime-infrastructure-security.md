---
title: Runtime infrastructure security
aliases: ["Runtime infrastructure security", "Host and container security"]
document_type: architecture
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-08-04
tags: [infrastructure, security]
related_code: []
change_triggers:
  - "../../../infra/containers/"
  - "../../../infra/deployment/"
  - "../../../infra/machine-images/"
related_docs:
  - "Security knowledge"
  - "Security model"
  - "Trust boundaries"
  - "Container runtime"
  - "Deployment architecture"
  - "Release recovery and readiness"
---

# Runtime infrastructure security

Runtime security is established by several reinforcing boundaries: cloud
networking, host administration, workload identity, container isolation,
secret delivery, outbound policy, and recovery. A strong control at one layer
does not compensate for an unrestricted path at another.

## Durable invariants

- Routine administration does not require a publicly reachable management
  service.
- Public ingress reaches the application only through the intended proxy
  boundary; private service listeners are not made public by convenience.
- Each host and workload receives role-specific authority rather than a shared
  environment-wide identity.
- Secrets arrive after artifact creation and are exposed only to consumers that
  require them.
- Application outbound access follows an explicit policy and cannot silently
  bypass its controlled route.
- Containers receive the minimum host access, kernel capability, writable
  storage, and device access required for their role.
- Hosts and workloads can be replaced from known inputs without preserving
  undocumented repair state.

## Privileged integration points

Management, telemetry, image management, and certificate automation often need
access ordinary application processes do not. These paths require their own
threat review because they can cross several otherwise useful boundaries.

A read-only filesystem view does not make a privileged control interface
read-only. Similarly, a monitoring component that can control workloads or read
all host secrets changes the host trust model even when its purpose is
observability. Prefer narrower adapters, filtered APIs, or duplicated signals
when they preserve the required operational outcome.

## Secret and identity lifetime

Build identity, deployment identity, host identity, and application identity
serve different phases. They should not be interchangeable or persist longer
than their phase requires. Runtime configuration should reference the intended
secret source without copying broad bootstrap authority into environment files,
images, logs, or inspection metadata.

Revocation and rotation need a consumption path: replacing a provider value is
not complete until workloads refresh it and evidence shows the retired value is
no longer required.

## Maintenance and recovery

Host patching, base-image replacement, container release, and application
rollback are separate lifecycles. Security updates should not depend on
in-place manual repair when a role can be rebuilt and reconverged. Recovery
access must remain independent enough to diagnose a failed normal management
path without becoming permanent public access.

Repository checks can verify declared isolation and deny known-dangerous
configurations. Live evidence is still required for host firewall state,
identity policy, management access, secret permissions, outbound enforcement,
patch level, and replacement behaviour.

## Related documents

- [[security-index|Security knowledge]]
- [[security-model|Security model]]
- [[trust-boundaries|Trust boundaries]]
- [[containers-index|Container runtime]]
- [[deployment-index|Deployment architecture]]
- [[release-recovery-and-readiness|Release recovery and readiness]]
