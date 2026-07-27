---
title: Proxmox rehearsal observability
aliases: ["Proxmox rehearsal observability"]
document_type: implementation
status: verified
authority: canonical
verified_evidence_digest: sha256:9394b4e8f66c45800bba03fa2dd3122d142a94ab6f645d13260de84e5fe3e44c
last_edited: 2026-07-27
tags: [infrastructure, tooling]
related_code:
  - "../../../../infra/deployment/proxmox/scripts/lib/cmd_logs.sh"
  - "../../../../infra/containers/runtime/services/alloy/"
  - "../../../../infra/containers/runtime/services/alloy-app/"
  - "../../../../infra/containers/runtime/compose/"
related_docs:
  - "Proxmox rehearsal"
  - "Proxmox rehearsal fixtures and egress"
  - "Proxmox rehearsal setup"
---

# Proxmox rehearsal observability

Owns the checked-in log access and Alloy configuration for the Proxmox
rehearsal. It does not attest that Grafana Cloud credentials are available or
that signals are currently being delivered.

```text
App backend logs/traces
          |
      app Alloy
          |
          v
Proxy Alloy <----- proxy/container/host logs
    |    |
    |    +----> configured trace endpoint
    +---------> configured log endpoint

operator --> rehearsal logs --> selected guest/container
```

## Operator log access

`rehearsal logs` reaches a selected guest through the temporary private-bridge
path and tails a chosen container. It supports `proxy`, `app`, `fixtures`, and
`db` targets, plus listing, follow, tail count, error, request-ID, and raw
output options. By default it parses JSON log records to one line and omits a
full traceback; `--raw` retains Docker's original output.

## Alloy signal path

The proxy Compose stack runs `infra/containers/runtime/services/alloy`, which
collects proxy-host and container logs and exports logs and OTLP traces to the
configured Grafana Cloud endpoints. It also receives app-side logs on port
`3500` and OTLP/gRPC traces on the private network.

The app Compose stack runs the separate `alloy-app` configuration. It collects
backend logs, forwards them to the proxy Alloy receiver, and relays backend
OTLP/gRPC traces to the proxy gateway. This keeps the app VM without an
independent internet route. The app configuration promotes a small set of
fields to Loki labels while leaving request-specific values in the log record.

Grafana token material is supplied through the rehearsal secret path, not as a
Terraform variable. The proxy Compose file mounts the rendered token file on
tmpfs. The non-secret endpoints and user identifiers are Terraform seed values.

## Related documents

- [[proxmox-index|Proxmox rehearsal]]
- [[rehearsal-fixtures|Proxmox rehearsal fixtures and egress]]
- [[rehearsal-setup|Proxmox rehearsal setup]]
