---
title: Runtime containers
aliases: ["Runtime containers"]
document_type: architecture
status: verified
authority: canonical
verified_evidence_digest: sha256:91b6754c7fa5ba494dc8bf963bdbbf7ba13662d4a4cfca74a2539a47fe40c737
last_edited: 2026-07-27
tags: [infrastructure, backend]
related_code:
  - "../../../../infra/containers/runtime/compose/"
  - "../../../../infra/containers/strategies/"
  - "../../../../infra/deployment/bootstrap/"
related_docs: ["Container runtime documentation", "Deployment model"]
---

# Runtime containers

FlowForm uses distinct Compose definitions for local development and tests,
the shared split-host runtime, and the Proxmox rehearsal. Their differing
networks, mounts, and credentials are intentional variants rather than proof
of a common live deployment.

```text
internet/LAN
    |
    v
Proxy host: Caddy + Squid + Alloy
    | ingress       | egress/telemetry
    v               ^
App host: backend + Alloy
    |
    v
external database placement supplied by environment
```

## Shared host runtime

The shared runtime is split into two Compose projects. The proxy project runs
Caddy, Squid, and Alloy; Caddy publishes HTTP and HTTPS, while Squid binds to a
configured private proxy address. The app project runs the Gunicorn backend
and Alloy; the backend binds port 5000 to its configured private app address.
Neither shared Compose file creates a PostgreSQL service.

The backend is configured to use the proxy host for HTTP and HTTPS egress and
gets database, application, and Auth0-management values through file-backed
Docker secrets. The proxy Alloy service receives its Grafana token as a
file-backed Docker secret. The Compose files use read-only filesystems or
bounded writable volumes as applicable, drop capabilities, set
`no-new-privileges`, and configure bounded JSON-file log rotation. Alloy has
the narrowly restored capabilities and host mounts required to read the Docker
socket and system journal.

## Strategy overlays and bootstrap

The AWS proxy overlay supplies the Route 53 Caddy configuration and AWS Squid
allow-list. The rehearsal overlays replace those with local TLS, LocalStack,
and test-network inputs while retaining the shared base services. The rehearsal
app overlay supplies per-service AWS endpoint overrides and disables EC2
metadata lookup; those settings are absent from the shared app file.

Host bootstrap writes the environment files consumed by Compose, materialises
secrets under a runtime secret directory, validates the merged configuration,
and waits for Compose startup. Therefore image references and other required
runtime values must be available before a host can converge. See
[[deployment-model|Deployment model]] for the CDK and host-lifecycle boundary.

## Local variants

The development Compose file defines a backend with separate core and response
PostgreSQL services. The test Compose variant provides a separate backend and
the same two database roles; its live-test override is a distinct opt-in file.
These local definitions do not establish the shared host database topology or
cloud network behaviour.
