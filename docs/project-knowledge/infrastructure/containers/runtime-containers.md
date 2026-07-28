---
title: Runtime containers
aliases: ["Runtime containers"]
document_type: architecture
status: draft
authority: canonical
verified_evidence_digest: null
last_edited: 2026-07-29
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

The backend is configured to use the proxy host for HTTP and HTTPS egress.
Application and Auth0-management values use file-backed Docker secrets in both
deployment strategies. The shared AWS app definition is passwordless for its
databases; the rehearsal app overlay adds the two local database password
files. The proxy Alloy service receives its Grafana token as a file-backed
Docker secret. The Compose files use read-only filesystems or bounded writable
volumes as applicable, drop capabilities, set
`no-new-privileges`, and configure bounded JSON-file log rotation. Alloy has
the narrowly restored capabilities and host mounts required to read the Docker
socket and system journal.

## Strategy overlays and bootstrap

The AWS proxy overlay supplies the Route 53 Caddy configuration and AWS Squid
allow-list. The rehearsal overlays replace those with local TLS, LocalStack,
and test-network inputs while retaining the shared base services. The rehearsal
app overlay supplies database password files, per-service AWS endpoint
overrides, and disabled EC2 metadata lookup; those settings are absent from the
shared app file.

App bootstrap requires `FLOWFORM_DEPLOYMENT_TARGET` to select `aws` or
`rehearsal`. It validates that the rendered database auth modes are respectively
`iam` or `password`, then materialises only the secrets required by that
strategy. The AWS path removes stale database password files instead of
retrieving them. Before Compose starts, each AWS host obtains an ECR
authorization token and logs Docker into every distinct private registry named
by its configured image references. The token is piped through standard input
and is not written into runtime configuration. On the private AWS app host,
bootstrap also writes an idempotent SSM Agent systemd proxy drop-in after Squid
becomes reachable; AWS service traffic uses the private Squid address while
instance metadata remains direct. Host bootstrap then validates the merged
configuration and waits for Compose startup. Therefore image references and
other required runtime values must be available before a host can converge. See
[[deployment-model|Deployment model]] for the CDK and host-lifecycle boundary.

## Local variants

The development Compose file defines a backend with separate core and response
PostgreSQL services. The test Compose variant provides a separate backend and
the same two database roles; its live-test override is a distinct opt-in file.
These local definitions do not establish the shared host database topology or
cloud network behaviour.
