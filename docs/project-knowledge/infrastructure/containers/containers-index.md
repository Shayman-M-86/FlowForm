---
title: Container runtime
aliases: ["Container runtime", "Container runtime documentation", "Runtime containers"]
document_type: architecture
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-08-04
tags: [infrastructure]
related_code:
  - "../../../../infra/containers/README.md"
  - "../../../../infra/containers/runtime/development/compose/compose.yml"
  - "../../../../infra/containers/runtime/development/compose/compose.test.yml"
  - "../../../../infra/containers/runtime/aws/common/compose/app.yml"
  - "../../../../infra/containers/runtime/aws/common/compose/proxy.yml"
  - "../../../../frontend/docker-compose.dev.yml"
change_triggers:
  - "../../../../infra/containers/images/"
  - "../../../../infra/containers/runtime/"
related_docs: ["Infrastructure knowledge", "Deployment architecture", "Local infrastructure", "Runtime infrastructure security"]
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

## Runtime variants

The repository does not apply one Compose topology unchanged everywhere:

| Context | Declared grouping | Boundary being exercised |
| --- | --- | --- |
| Backend development | Backend, core PostgreSQL, response PostgreSQL | Local API development with both persistence models. |
| Backend test | Test backend, disposable core PostgreSQL, disposable response PostgreSQL | Isolated backend test execution; the separate live-test override controls public egress. |
| Frontend development | Public Site, Studio development server, optional Studio preview | Frontend builds and hot-reload independently of the backend Compose project. |
| AWS application role | Backend and app-host Alloy | Private application execution and telemetry relay. |
| AWS proxy role | Caddy, Squid, and proxy-host Alloy | Public ingress, controlled application egress, and the outward telemetry gateway. |
| Proxmox rehearsal | AWS-compatible app/proxy roles plus rehearsal overrides, database, and fixture compositions | Local exercise of the shared host boundary with environment-specific dependencies. |

These definitions establish intended composition and bindings. They do not show
that a container, host firewall, external database, registry, or telemetry
destination is currently reachable.

The checked-in Compose and image definitions specify intended service
boundaries, including constrained privileges, mounts, and logging. They are not
proof that an external telemetry destination, registry, or deployment is live.
The security consequences of host access, workload identity, secret delivery,
and privileged observability integrations belong to
[[runtime-infrastructure-security|Runtime infrastructure security]].

## Related documents

- [[infrastructure-index|Infrastructure knowledge]]
- [[deployment-index|Deployment architecture]]
- [[local-infrastructure|Local infrastructure]]
- [[runtime-infrastructure-security|Runtime infrastructure security]]
