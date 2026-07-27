---
title: Container runtime documentation
aliases: ["Container runtime documentation"]
document_type: overview
status: verified
authority: canonical
verified_against_commit: 0edae9082dc3381cc1376e8a81276bf5c7bebf88
tags: [infrastructure, backend]
related_code:
  - "../../../../infra/containers/"
related_docs: ["Infrastructure knowledge", "Runtime containers"]
---

# Container runtime documentation

FlowForm's container layer separates reusable images, shared host roles, and
environment-specific composition. Buildable base images provide application
software or supporting services. Shared runtime Compose files define the
deployed application and proxy roles. Strategy directories adapt those roles
for development, test, AWS-oriented deployment, and the Proxmox rehearsal.

```text
buildable container images
           |
           v
shared runtime definitions
     /              \
    v                v
 app host role    proxy host role
    |                |
    +--------+-------+
             |
   environment strategy overlays
   dev / test / AWS / rehearsal
```

## Runtime shape

The shared deployment model uses two host-level Compose projects. The
application role runs the backend and its local telemetry collector; the proxy
role runs ingress, restricted egress, and the telemetry gateway. PostgreSQL is
not part of either shared host composition. Database placement and credentials
are supplied by the selected environment.

Development and tests deliberately use different compositions. Development
combines a source-mounted backend with two PostgreSQL services for iteration.
The rehearsal preserves the split roles and adds isolated fixture services,
local TLS, and registry overlays. These variants share contracts where useful
without implying that every service runs in every environment.

## Security and state boundaries

Runtime services receive confidential values through file-backed secrets where
the shared contract requires them. Compose definitions constrain privileges,
writable paths, and log growth; individual collectors regain only the host
access needed for their role. Persistent application data belongs to database
or explicitly named volumes, not to the container image.

[[runtime-containers|Runtime containers]] provides the detailed service,
network, mount, secret, and overlay mapping behind this model.

## Related documents

- [[infrastructure-index|Infrastructure knowledge]]
- [[runtime-containers|Runtime containers]]
- [[deployment-index|Deployment documentation]]
- [[local-infrastructure|Local infrastructure]]
